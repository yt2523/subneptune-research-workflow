#!/usr/bin/env python3
"""Portable research workflow runner.

A Python standard-library implementation of an autonomous coding loop:
- plan validation and deterministic next-task selection
- isolated staged source workspace (copy context + scoped files only)
- DeepSeek coder + independent reviewer (codex CLI or OpenAI-compatible API)
- budget/deadline accounting, durable atomic state, safe resume

Usage:
    python workflow/portable.py doctor|run|status --config CONFIG \
        [--credentials EXTERNAL] [--offline] [--allow-tests]

Only workflow/portable.py is imported by fixed acceptance tests; the module is
standalone and uses no third-party packages.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None


def _rel(p: str) -> str:
    return p.replace("\\", "/").lstrip("/")


class _Pause(Exception):
    """Raised to pause a run at a controlled exit point with a reason."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject ALL redirects so Authorization is never forwarded off-endpoint."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Do not follow any 3xx: an Authorization header must not be sent to a
        # location outside the configured endpoint. Raising HTTPError without a
        # response body fails the request closed.
        raise urllib.error.HTTPError(
            newurl, code, "api_redirect_rejected", headers, fp
        )


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# --------------------------------------------------------------------------- #
# Public functions required by fixed acceptance tests                         #
# --------------------------------------------------------------------------- #


def validate_plan(plan) -> dict:
    """Validate a plan object. Returns the normalized plan dict.

    Raises ValueError on cycle/missing deps/duplicate ids/unsafe scope/bad argv.
    """
    if not isinstance(plan, dict) or not isinstance(plan.get("tasks"), list):
        raise ValueError("plan must be {tasks: [...]}")
    tasks = []
    seen = set()
    for t in plan["tasks"]:
        if not isinstance(t, dict):
            raise ValueError("task must be object")
        tid = t.get("id")
        if not isinstance(tid, str) or not tid:
            raise ValueError("task id required")
        if tid in seen:
            raise ValueError("duplicate task id: %s" % tid)
        seen.add(tid)
        if not isinstance(t.get("priority", 0), int):
            raise ValueError("priority must be int")
        deps = t.get("depends_on", [])
        if not isinstance(deps, list) or not all(isinstance(d, str) for d in deps):
            raise ValueError("depends_on must be list[str]")
        scope = t.get("scope", [])
        if not isinstance(scope, list) or not all(isinstance(s, str) for s in scope):
            raise ValueError("scope must be list[str]")
        for s in scope:
            _check_scope_token(s)
        acceptance = t.get("acceptance")
        if not isinstance(acceptance, str) or not acceptance.strip():
            raise ValueError("acceptance required")
        tests = t.get("tests", [])
        if not isinstance(tests, list):
            raise ValueError("tests must be list")
        if not tests:
            raise ValueError("tests empty")
        for argv in tests:
            if not isinstance(argv, list) or not argv or not all(
                isinstance(a, str) for a in argv
            ):
                raise ValueError("bad argv")
        # validate offline_files keys now (before any staging/write)
        offline = t.get("offline_files", {})
        if not isinstance(offline, dict):
            raise ValueError("offline_files must be object")
        for rel in offline:
            _check_safe_path(rel, "offline_files")
        nt = dict(t)
        nt["id"] = tid
        nt["depends_on"] = deps
        nt["scope"] = [ _check_scope_token(s) for s in scope ]
        nt["acceptance"] = acceptance
        nt["tests"] = [ list(a) for a in tests ]
        tasks.append(nt)
    idset = set(t["id"] for t in tasks)
    for t in tasks:
        for d in t["depends_on"]:
            if d not in idset:
                raise ValueError("missing dep: %s" % d)
            if d == t["id"]:
                raise ValueError("self dep: %s" % d)
    # cycle detection
    adj = {t["id"]: t["depends_on"] for t in tasks}
    state = {}
    def visit(n, stack):
        state[n] = 1
        for m in adj[n]:
            if state.get(m) == 1:
                raise ValueError("cycle: %s" % " -> ".join(stack + [m]))
            if state.get(m) != 2:
                visit(m, stack + [m])
        state[n] = 2
    for n in adj:
        if state.get(n) != 2:
            visit(n, [n])
    return {"tasks": tasks}


def _check_safe_path(s, what="scope"):
    """Single safe-path guard shared by scope + context + offline files.

    Rejects empty, drive letters/absolute paths (POSIX or Windows), backslashes,
    traversal, any empty/`.`/`..` component, and every hidden (dot-prefixed)
    component. Returns the normalized *-relative* form of the token.
    """
    if not isinstance(s, str) or not s:
        raise ValueError("empty %s" % what)
    raw = s
    # reject backslash immediately (Windows separator / escape)
    if "\\" in raw:
        raise ValueError("backslash in %s" % what)
    # reject absolute / drive-letter forms before any stripping
    if raw.startswith("/"):
        raise ValueError("absolute %s: %s" % (what, raw))
    if re.match(r"^[A-Za-z]:", raw):
        raise ValueError("drive path in %s: %s" % (what, raw))
    if raw.startswith("//"):
        raise ValueError("unc path in %s: %s" % (what, raw))
    # normalize forward-slash relative form; reject leading slash again
    rel = raw.replace("\\", "/").lstrip("/")
    if rel != raw.replace("\\", "/"):
        raise ValueError("absolute %s: %s" % (what, raw))
    parts = rel.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise ValueError("unsafe %s: %s" % (what, raw))
    if any(p.startswith(".") for p in parts):
        raise ValueError("dot/hidden component in %s: %s" % (what, raw))
    if any(p == ".." for p in parts):
        raise ValueError("traversal in %s: %s" % (what, raw))
    return rel


def _check_scope_token(s):
    rel = _check_safe_path(s, "scope")
    low = rel.lower()
    if "test_" in low or low.startswith("test") or "/tests/" in low or low.endswith("tests"):
        raise ValueError("scope overlaps test")
    if "acceptance" in low:
        raise ValueError("scope overlaps acceptance (immutable)")
    if re.search(r"(secret|token|key|credential|password)", low):
        raise ValueError("secret-ish scope")
    return rel


def choose_next(plan, statuses):
    """Return highest-priority ready task dict or None.

    A task is ready when all deps are 'passed'. Passed tasks are skipped;
    failed/in_flight tasks remain selectable (but the runner itself handles
    resume/selection; this mirrors the rule that only 'passed' skips).
    """
    tasks = validate_plan(plan)["tasks"]
    ready = [
        t for t in tasks
        if all(statuses.get(d) == "passed" for d in t["depends_on"])
        and statuses.get(t["id"]) != "passed"
    ]
    if not ready:
        return None
    ready.sort(key=lambda t: (t["priority"], t["id"]))
    return ready[0]


def load_credentials(path, repo_root):
    """Load external credentials from UTF-8 JSON or dotenv.

    Reject credential files inside repo (lexically and after realpath
    resolution, in both directions), rejecting any symlink that points into or
    out of the repo.
    """
    if not path:
        return {}
    p = os.path.abspath(path)
    root = os.path.abspath(repo_root)
    # lexical containment
    if _within(root, p):
        raise ValueError("credentials must be outside repo")
    if not os.path.isfile(p):
        raise ValueError("credentials not found")
    # resolved containment: reject symlink pointing into OR from the repo
    rp = os.path.realpath(p)
    rroot = os.path.realpath(root)
    if _within(rroot, rp):
        raise ValueError("credentials resolve inside repo (symlink rejected)")
    if _within(rp, rroot) and _within(rroot, rp) is False and os.path.isdir(rp):
        raise ValueError("repo resolves inside credential dir (symlink rejected)")
    # reject any symlink component in the credential path itself
    if os.path.islink(p) or _has_symlink_parent(p, os.path.dirname(p)):
        raise ValueError("credential symlink rejected")
    data = _read_text(p)
    s = data.strip()
    creds = {}
    if s.startswith("{"):
        obj = json.loads(s)
        if not isinstance(obj, dict):
            raise ValueError("credentials JSON must be object")
        creds = {k: (v if isinstance(v, str) else str(v)) for k, v in obj.items() if v != ""}
    else:
        for line in data.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if v:
                    creds[k] = v
    if not creds:
        raise ValueError("no credentials found")
    return creds


def redact(text, credentials):
    """Replace all nonempty credential values with [REDACTED]."""
    if text is None:
        return text
    out = str(text)
    vals = sorted(
        (v for v in credentials.values() if v and isinstance(v, str)),
        key=len, reverse=True,
    )
    for v in vals:
        out = out.replace(v, "[REDACTED]")
    for k in credentials:
        if k:
            out = re.sub(
                r"(?i)\b" + re.escape(k) + r"\b\s*[:=]\s*\S+", k + "=[REDACTED]", out
            )
    return out


def _pid_alive(pid):
    """Return True if a process with the given PID exists.

    POSIX uses os.kill(pid, 0). On Windows, os.kill(pid, 0) actually delivers
    a signal (CTRL_C_EVENT) so we use a non-signaling ctypes process query:
    OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION) + GetExitCodeProcess; a
    STILL_ACTIVE (259) exit code means alive, access denied is conservatively
    treated as alive, a genuinely exited process returns its exit code.
    """
    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return True
        return True
    # Windows: non-signaling existence query.
    import ctypes
    from ctypes import wintypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    ERROR_INVALID_PARAMETER = 87

    # Use WinDLL(..., use_last_error=True) so ctypes.get_last_error() stays in
    # sync with the Win32 error code, and set explicit argtypes/restype so the
    # 64-bit HANDLE is not truncated to a 32-bit c_int.
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = (
        wintypes.DWORD, wintypes.BOOL, wintypes.DWORD,
    )
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetExitCodeProcess.argtypes = (
        wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD),
    )
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL

    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid)
    if not handle:
        err = ctypes.get_last_error()
        # invalid parameter (87) is the classic "no such PID" result on Windows;
        # only then are we confident the process does not exist. Anything else
        # (access denied 5, unknown) is conservatively treated as alive.
        return err != ERROR_INVALID_PARAMETER
    try:
        code = wintypes.DWORD(0)
        ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        if not ok:
            return True
        # STILL_ACTIVE -> alive; a real exit code -> process has terminated
        return code.value == STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def _within(root, p):
    try:
        return os.path.commonpath([root, p]) == root
    except ValueError:
        return False


def _read_text(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def _is_symlink(p):
    if os.path.islink(p):
        return True
    # Windows directory junction / reparse point (os.path.islink is False for
    # junctions on older Python). Path.is_junction when available, else fall
    # back to the FILE_ATTRIBUTE_REPARSE_POINT stat flag.
    if os.path.isdir(p) and not os.path.islink(p):
        try:
            pp = Path(p)
            if hasattr(pp, "is_junction") and pp.is_junction():
                return True
        except (OSError, ValueError):
            pass
        try:
            if os.name == "nt" and (
                os.stat(p).st_file_attributes & 0x400  # FILE_ATTRIBUTE_REPARSE_POINT
            ):
                return True
        except (OSError, AttributeError):
            pass
    return False


def _has_symlink_parent(path, root):
    # reject symlink/junction/reparse-point anywhere in path up to root
    p = os.path.abspath(path)
    r = os.path.abspath(root)
    rel = os.path.relpath(p, r)
    cur = r
    if rel == os.pardir or rel.startswith(os.pardir + os.sep):
        raise ValueError("path escapes root")
    # the root itself may be a symlink/junction (e.g. a pre-existing run_dir
    # junction); reject it before walking any children.
    if _is_symlink(r):
        return True
    for part in rel.split(os.sep):
        cur = os.path.join(cur, part)
        if _is_symlink(cur):
            return True
    return False


# --------------------------------------------------------------------------- #
# Runner                                                                      #
# --------------------------------------------------------------------------- #


class Runner:
    def __init__(self, config, config_path, credentials=None, offline=False, allow_tests=False):
        self.config = config
        self.config_path = os.path.abspath(config_path)
        self.config_dir = os.path.dirname(self.config_path)
        self.credentials = credentials or {}
        # gather active environment secret values into the credentials map so
        # they are redacted everywhere (never persisted/staged).
        for _k, _v in os.environ.items():
            _kl = _k.lower()
            if any(s in _kl for s in ("api_key", "apikey", "token", "secret", "password", "auth")):
                if _v and _k not in self.credentials:
                    self.credentials[_k] = _v
        self.offline = offline
        self.allow_tests = allow_tests or offline
        self.context_files = []
        self.project_root = Path(os.path.abspath(
            os.path.join(self.config_dir, config.get("project_root", "."))
        ))
        if not self.project_root.is_dir():
            raise ValueError("project_root does not exist")
        self.run_dir = Path(os.path.abspath(
            os.path.join(self.config_dir, config.get("run_dir", ".run"))
        ))
        self.source_dir = self.run_dir / "source"
        self.coder = config.get("coder", {})
        self.reviewer = config.get("reviewer", {})
        self._reject_config_secrets()
        limits = config.get("limits", {})
        self.max_model_calls = int(limits.get("max_model_calls", 12))
        self.max_seconds = float(limits.get("max_seconds", 7200))
        self.max_fix_rounds = int(limits.get("max_fix_rounds", 5))
        self.call_timeout = float(limits.get("call_timeout", 180))
        self.max_output_tokens = int(limits.get("max_output_tokens", 6000))
        self.max_context_chars = int(config.get("max_context_chars", 32000))
        self.plan = self.config["plan"]
        self.context = config.get("context", [])
        self.state_path = os.path.join(self.run_dir, "state.json")
        self.lock_path = os.path.join(self.run_dir, ".lock")
        self.state = {"offline": self.offline}
        self._started = time.time()

    # -- public -------------------------------------------------------------

    def _reject_config_secrets(self):
        # config/coder/reviewer must not embed actual credential material.
        secret_keys = ("api_key", "apikey", "token", "secret", "password", "auth", "key")
        for section in (self.config, self.coder, self.reviewer):
            for k, v in section.items():
                kl = k.lower()
                if any(s in kl for s in secret_keys) and isinstance(v, str) and v.strip():
                    raise ValueError("config must not contain credential values (%s)" % k)

    def doctor(self):
        out = []
        self.doctor_warnings = []
        if not self.project_root.is_dir():
            out.append("ERROR project_root missing")
        if os.path.normcase(str(self.project_root)) == os.path.normcase(str(self.run_dir)):
            out.append("ERROR run_dir overlaps project root")
        if _within(self.project_root, self.run_dir):
            pass  # run_dir inside project is okay only if not overlapping
        elif _within(self.run_dir, self.project_root):
            out.append("ERROR run_dir inside project source")
        # validate plan (does not require keys)
        try:
            self._validated = validate_plan(self.plan)
        except ValueError as e:
            out.append("ERROR plan: %s" % e)
        # live dependencies reported separately as warnings, never as failures
        if not self.offline:
            if not shutil.which("codex") and self.reviewer.get("provider") == "codex":
                self.doctor_warnings.append("WARNING codex CLI not found (live reviewer unavailable)")
            if self.reviewer.get("provider") == "api" and not self.reviewer.get("model"):
                out.append("ERROR live api reviewer requires model")
        return out

    def status(self):
        if not os.path.isfile(self.state_path):
            return {"state": "not_started", "next": "run"}
        st = self._load_state()
        statuses = st.get("statuses", {})
        done = [k for k, v in statuses.items() if v == "passed"]
        nxt = choose_next(self.plan, statuses)
        return {
            "state": st.get("state", "unknown"),
            "completed": done,
            "next": nxt["id"] if nxt else None,
            "stop_reason": st.get("stop_reason"),
            "model_calls": st.get("model_calls", 0),
        }

    def run(self):
        self._acquire_lock()
        try:
            return self._run_locked()
        finally:
            self._release_lock()

    # -- internals ----------------------------------------------------------

    def _run_locked(self):
        validated = validate_plan(self.plan)
        self._validated = validated
        tasks = validated["tasks"]

        # resolve context files (configured only)
        self.context_files = self._resolve_context()

        # load or init state
        is_new = not os.path.isfile(self.state_path)
        if os.path.isfile(self.state_path):
            st = self._load_state()
            self.state = st
            # restore accumulated wall-clock so the deadline persists across resume
            self._started = time.time() - float(st.get("elapsed_seconds", 0.0))
            if st.get("offline") is not None and bool(st.get("offline")) != bool(self.offline):
                raise _Pause("mode_change_rejected")
            if self._objects_dirty(st):
                raise _Pause("source_tampered")
            if self._config_dirty(st):
                raise _Pause("config_changed_resume_rejected")
            statuses = st.get("statuses", {})
        else:
            statuses = {}
            self.state = {
                "offline": self.offline,
                "state": "in_flight",
                "statuses": {},
                "completed": [],
                "model_calls": 0,
                "usage": {},
                "attempts": {},
                "valid_attempts": {},
                "last_feedback": {},
                "source_hash": {},
                "evidence": {},
                "stop_reason": None,
                "config_sha": self._config_sha(),
            }
            self._persist()  # persist initial state BEFORE any network

        os.makedirs(os.path.join(self.run_dir, "source"), exist_ok=True)
        if is_new:
            # stage on NEW state only; resume retains verified source snapshots
            self._stage_source()
        else:
            # resume: verify source still matches last snapshot (do not re-stage)
            self._verify_source_retained()

        start = time.time()
        # main loop
        while True:
            if time.time() - start > self.max_seconds or self.remaining_seconds() <= 0:
                self._set_stop("deadline_reached")
                break
            nxt = choose_next(self.plan, self.state.get("statuses", statuses))
            if nxt is None:
                self.state["state"] = "completed"
                self.state["stop_reason"] = "completed"
                self._persist()
                break
            self.state["state"] = "in_flight"
            self.state["current_task"] = nxt["id"]
            if not self.offline and self._call_budget_exhausted():
                # if final allowed reviewer completed final task, completed wins
                if self._all_passed():
                    self.state["state"] = "completed"
                    self.state["stop_reason"] = "completed"
                    self._persist()
                    break
                self._set_stop("budget_exhausted")
                break
            self._persist()
            try:
                self._do_task(nxt)
            except _Pause as e:
                if e.reason.startswith("budget_exhausted"):
                    # budget/deadline exhaustion is a graceful stop, not a crash
                    self._set_stop("budget_exhausted")
                    break
                self._set_stop("paused:" + e.reason)
                self.state["elapsed_seconds"] = time.time() - self._started
                self._persist()
                raise

        self.state["elapsed_seconds"] = time.time() - self._started
        self._persist()
        return self.state

    def _all_passed(self):
        statuses = self.state.get("statuses", {})
        return all(statuses.get(t["id"]) == "passed" for t in self._validated["tasks"])

    def _do_task(self, task):
        tid = task["id"]
        if self.offline:
            self._do_offline(task)
            return
        # live flow: retry rejected/test-failed tasks up to max_fix_rounds
        # VALID fix attempts. Transport/parse errors pause (via _Pause) and do
        # not count as repair rounds.
        while True:
            # checkpoint: if we already exhausted valid fix rounds (e.g. resume),
            # stop with zero extra coder calls.
            if self._valid_attempt(tid) >= self.max_fix_rounds:
                self.state["statuses"][tid] = "failed"
                self.state.setdefault("needs_codex_diagnosis", [])
                if tid not in self.state["needs_codex_diagnosis"]:
                    self.state["needs_codex_diagnosis"].append(tid)
                self._set_stop("needs_codex_diagnosis:%s" % tid)
                raise _Pause("needs_codex_diagnosis:%s" % tid)
            feedback = self.state.setdefault("last_feedback", {}).get(tid)
            proposal = self._call_coder(task, feedback)
            if proposal is None:
                raise _Pause("coder_failed")
            self._apply_proposal(task, proposal)
            # tests
            ok = self._run_tests(task)
            if ok:
                # reviewer
                approved, findings = self._call_reviewer(task)
                # redact actual secret values from reviewer findings before they
                # are persisted to state/feedback or embedded in any prompt.
                findings = [redact(f, self.credentials) for f in findings]
                self.state.setdefault("last_feedback", {})[tid] = findings
                # re-verify source hashes after reviewer too (tests cannot mutate
                # implementation/protected input and still obtain approval)
                self._verify_source_after_review(task)
                if approved:
                    self._record_pass(task)
                    return
            # a valid (non-transport, non-parse) failed fix round
            self._inc_valid_attempt(tid)
            self._persist()
            if self._valid_attempt(tid) >= self.max_fix_rounds:
                self.state["statuses"][tid] = "failed"
                self.state.setdefault("needs_codex_diagnosis", [])
                if tid not in self.state["needs_codex_diagnosis"]:
                    self.state["needs_codex_diagnosis"].append(tid)
                self._set_stop("needs_codex_diagnosis:%s" % tid)
                raise _Pause("needs_codex_diagnosis:%s" % tid)

    def _do_offline(self, task):
        tid = task["id"]
        mapping = task.get("offline_files", {})
        scope = task["scope"]
        # validate every proposed offline file path BEFORE any write
        for rel, content in mapping.items():
            safe = _check_safe_path(rel, "offline_files")
            if safe not in scope:
                raise ValueError("offline_files outside scope: %s" % rel)
        # genuinely stage the offline fixture files
        src_root = os.path.join(self.run_dir, "source")
        for rel, content in mapping.items():
            safe = _check_safe_path(rel, "offline_files")
            target = os.path.join(src_root, safe)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            if _has_symlink_parent(target, src_root) or os.path.islink(target):
                raise ValueError("offline destination symlink rejected: %s" % rel)
            _write_text(target, content)
        # always genuinely run the predeclared tests (no empty fast-pass)
        ok = self._run_tests(task)
        self._set_offline_evidence(tid)
        if ok:
            self.state["statuses"][tid] = "passed"
            self.state["completed"] = [x for x in self.state.get("completed", []) if x != tid] + [tid]
            self.state["state"] = "in_flight"
        else:
            self.state["statuses"][tid] = "failed"
            self._persist()
            # stop after ONE fixed fixture failure (no network / no retry)
            raise _Pause("offline_test_failed:%s" % tid)
        self._persist()

    def _set_offline_evidence(self, tid):
        ev = self.state.setdefault("evidence", {})
        ev[tid] = {"origin": "OFFLINE_FIXTURE_NOT_LLM", "type": "fixture"}
        ev[tid + ":review"] = {"origin": "OFFLINE_FIXTURE_NOT_LLM", "type": "reviewer_pass"}

    def _verify_source_after_review(self, task):
        # Re-check after reviewer: tests must not have mutated implementation or
        # protected inputs. The recorded after_tests hash (persisted as evidence
        # after the tests ran) is the blessed, tested baseline. ALWAYS re-hash
        # the source freshly here and compare against that expected tested hash;
        # never trust a cached in-memory snapshot that could equal itself.
        blessed = self.state.get("source_hash", {}).get("after_tests")
        if blessed is None:
            ev = self.state.get("evidence", {}).get(task["id"] + ":tests", {})
            blessed = ev.get("after_hash")
        if blessed is None:
            # no tested checkpoint recorded; fall back to a fresh comparison of
            # the latest controlled checkpoint.
            blessed = self._latest_source_checkpoint()
        if blessed is None:
            return
        cur = self._hash_source()
        if cur != blessed:
            raise _Pause("source_mutated_review_rejected")


    def _record_pass(self, task):
        tid = task["id"]
        self.state["statuses"][tid] = "passed"
        cl = [x for x in self.state.get("completed", []) if x != tid]
        cl.append(tid)
        self.state["completed"] = cl
        self._persist()

    def _check_budget(self, role):
        if self._call_budget_exhausted():
            raise _Pause("budget_exhausted_before_%s" % role)
        # deadline gates every provider call: no work at <=0 remaining
        if self.remaining_seconds() <= 0:
            raise _Pause("deadline_reached_before_%s" % role)
        # persist/consume the model-call budget BEFORE the actual call so a
        # crash mid-call does not lose the consumed budget.
        self.state["model_calls"] = self.state.get("model_calls", 0) + 1
        self._persist()

    def _call_budget_exhausted(self):
        return self.state.get("model_calls", 0) >= self.max_model_calls

    def _record_call(self, role, usage):
        u = self.state.setdefault("usage", {})
        c = u.setdefault(role, {"calls": 0})
        c["calls"] = c.get("calls", 0) + 1
        if usage is not None:
            for k, v in usage.items():
                c[k] = c.get(k, 0) + (v if isinstance(v, (int, float)) else 0)
        self._persist()

    def _inc_valid_attempt(self, tid):
        self.state.setdefault("attempts", {})[tid] = self.state.setdefault("attempts", {}).get(tid, 0) + 1
        self.state.setdefault("valid_attempts", {})[tid] = self.state.setdefault("valid_attempts", {}).get(tid, 0) + 1

    def _valid_attempt(self, tid):
        return self.state.get("valid_attempts", {}).get(tid, 0)

    def _call_coder(self, task, feedback):
        files = self._source_content_for(task)
        prompt = self._build_coder_prompt(task, files, feedback)
        # local context overflow / config errors are NOT charged as model calls
        if len(prompt) > self.max_context_chars:
            raise _Pause("context_too_large")
        self._check_budget("coder")
        body = {
            "model": self.coder.get("model", "deepseek-chat"),
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_output_tokens,
        }
        base = self.coder.get("base_url", "https://api.deepseek.com")
        resp = self._post_api(base, "/chat/completions", body, "DEEPSEEK_API_KEY")
        self._record_call("coder", self._extract_usage(resp))
        text = self._extract_text(resp)
        ok, data = _json_fence(text)
        if not ok:
            raise _Pause("coder_parse_error")
        return data.get("files", {})

    def _call_reviewer(self, task):
        provider = self.reviewer.get("provider", "codex")
        evidence = self._current_evidence(task)
        prompt = self._build_reviewer_prompt(task, evidence)
        if len(prompt) > self.max_context_chars:
            raise _Pause("context_too_large")
        self._check_budget("reviewer")
        if provider == "codex":
            exe = shutil.which("codex")
            if not exe:
                raise _Pause("codex_not_found")
            out = self._run_codex(exe, prompt)
        else:
            if not self.reviewer.get("model"):
                raise _Pause("reviewer_model_required")
            body = {
                "model": self.reviewer["model"],
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": min(2000, self.max_output_tokens),
            }
            base = self.reviewer.get("base_url", "https://api.openai.com/v1")
            resp = self._post_api(base, "/chat/completions", body, "OPENAI_API_KEY")
            self._record_call("reviewer", self._extract_usage(resp))
            out = self._extract_text(resp)
        # strict bool review JSON (raises on non-bool approved / bad findings)
        data = self._parse_reviewer_json(out)
        return data["approved"], data.get("findings", [])

    def _parse_reviewer_json(self, text):
        """Parse and strictly validate reviewer JSON. Returns the dict.

        Raises ValueError/_Pause when the JSON is unparseable or when the
        ``approved`` field is not a strict boolean (or ``findings`` is not a
        list of strings). Used directly by fixed acceptance tests.
        """
        ok, data = _json_fence(text)
        if not ok:
            raise _Pause("reviewer_parse_error")
        approved = data.get("approved")
        findings = data.get("findings", [])
        if not isinstance(approved, bool):
            raise ValueError("approved must be a boolean")
        if not isinstance(findings, list) or not all(isinstance(f, str) for f in findings):
            raise _Pause("reviewer_findings_not_list")
        return data

    def _post_api(self, base_url, path, body, key_name):
        key = self.credentials.get(key_name)
        if key_name == "DEEPSEEK_API_KEY" and self.coder.get("api_key"):
            key = self.coder["api_key"]
        if key_name == "OPENAI_API_KEY" and self.reviewer.get("api_key"):
            key = self.reviewer["api_key"]
        # env fallback (optional)
        if not key:
            key = os.environ.get(key_name)
        if not key:
            # budget=0 requires no key; otherwise pause before call
            if self._call_budget_exhausted():
                raise _Pause("budget_exhausted")
            raise _Pause("missing_key_%s" % key_name.lower())
        url = base_url.rstrip("/") + path
        if not url.startswith("https://"):
            raise _Pause("non_https_url")
        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload, headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + key,
            }
        )
        try:
            timeout = min(self.call_timeout, self.remaining_seconds())
            if timeout <= 0:
                raise _Pause("deadline_reached")
            opener = urllib.request.build_opener(_NoRedirectHandler)
            with opener.open(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.reason == "api_redirect_rejected":
                raise _Pause("api_redirect_rejected")
            raise _Pause("http_%d" % e.code)
        except urllib.error.URLError as e:
            raise _Pause("network_error")

    def _extract_usage(self, resp):
        if not isinstance(resp, dict):
            return None
        u = resp.get("usage")
        if not isinstance(u, dict):
            return None
        return {
            "prompt_tokens": u.get("prompt_tokens"),
            "completion_tokens": u.get("completion_tokens"),
            "total_tokens": u.get("total_tokens"),
        }

    def _extract_text(self, resp):
        if not isinstance(resp, dict):
            return ""
        try:
            return resp["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return ""

    def _run_codex(self, exe, prompt):
        # Unique per-run output file so a stale reviewer_out.tmp from an
        # earlier attempt is never read. Written only by codex on success.
        tmp = os.path.join(
            self.run_dir, "reviewer_out-%s.tmp" % uuid.uuid4().hex
        )
        src = os.path.join(self.run_dir, "source")
        cmd = [
            exe, "exec", "--sandbox", "read-only", "--ephemeral",
            "--skip-git-repo-check", "--cd", src,
            "--output-last-message", tmp, "-",
        ]
        env = _scrubbed_env(self.credentials)
        # Bound the reviewer subprocess by whichever is smaller: the configured
        # call timeout or the positive remaining time. Never launch at zero.
        remaining = self.remaining_seconds()
        if remaining <= 0:
            raise _Pause("deadline_reached_before_reviewer")
        timeout = min(self.call_timeout, remaining)
        try:
            proc = subprocess.run(
                cmd, input=prompt.encode("utf-8"), env=env,
                capture_output=True, timeout=timeout, cwd=src, shell=False,
            )
        except subprocess.TimeoutExpired:
            raise _Pause("reviewer_timeout")
        try:
            # Only trust output produced by a clean (returncode 0) run.
            if proc.returncode != 0:
                raise _Pause("reviewer_process_failed")
            if not os.path.isfile(tmp) or os.path.getsize(tmp) == 0:
                raise _Pause("reviewer_output_missing")
            return _read_text(tmp)
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass

    # -- staging ------------------------------------------------------------

    def _resolve_context(self):
        files = []
        for c in self.context:
            rel = _check_safe_path(c, "context")
            src = os.path.join(self.project_root, rel)
            if not os.path.isfile(src):
                raise ValueError("context file missing: %s" % rel)
            if _is_symlink(src) or _has_symlink_parent(src, self.project_root):
                raise ValueError("context symlink rejected: %s" % rel)
            files.append(rel)
        return files

    def _stage_source(self):
        if getattr(self, "_validated", None) is None:
            self._validated = validate_plan(self.plan)
        src_root = str(self.source_dir)
        # copy context files
        for rel in self.context_files:
            dst = os.path.join(src_root, rel)
            _write_staged(src_root, rel, os.path.join(self.project_root, rel), dst)
        # copy scoped files if exist
        for t in self._validated["tasks"]:
            for rel in t["scope"]:
                src = os.path.join(self.project_root, rel)
                if os.path.isfile(src):
                    if _is_symlink(src) or _has_symlink_parent(src, self.project_root):
                        raise ValueError("staged source symlink rejected: %s" % rel)
                    dst = os.path.join(src_root, rel)
                    _write_staged(src_root, rel, src, dst)
        self._snapshot_source("before_start")

    def _verify_source_retained(self):
        # Resume must keep the latest controlled source snapshot intact.
        before = self._latest_source_checkpoint()
        if before is None:
            return
        cur = self._hash_source()
        if cur != before:
            raise _Pause("source_tampered")

    def _snapshot_source(self, tag):
        h = self._hash_source()
        sh = self.state.setdefault("source_hash", {})
        sh[tag] = h
        # Record the LATEST controlled checkpoint so resume can select the
        # newest known-good source (after_tests > after_apply > before_start).
        # This is a checkpoint tag, not part of verification.
        sh["last_source_checkpoint"] = tag
        self._persist()

    def _latest_source_checkpoint(self, st=None):
        """Return the latest controlled checkpoint hash for resume selection.

        Order of precedence when a ``last_source_checkpoint`` tag is absent
        (older state files): after_tests, then after_apply, then before_start.
        """
        st = st if st is not None else self.state
        sh = st.get("source_hash", {}) if isinstance(st, dict) else {}
        tag = sh.get("last_source_checkpoint")
        if tag and sh.get(tag) is not None:
            return sh[tag]
        for fallback in ("after_tests", "after_apply", "before_start"):
            if sh.get(fallback) is not None:
                return sh[fallback]
        return None

    def _hash_source(self):
        h = hashlib.sha256()
        files = set(self.context_files)
        for t in self._validated["tasks"]:
            files.update(t["scope"])
        for rel in sorted(files):
            p = os.path.join(self.run_dir, "source", rel)
            if not os.path.isfile(p):
                continue
            if _is_symlink(p):
                raise ValueError("unexpected symlink in source: %s" % rel)
            data = _read_bytes(p)
            h.update(rel.encode("utf-8"))
            h.update(b"\x00")
            h.update(_sha(data).encode("utf-8"))
            h.update(b"\x00")
        return h.hexdigest()

    def _objects_dirty(self, st):
        # protected context/acceptance/implementation tamper check on resume
        before = self._latest_source_checkpoint(st)
        if before is None:
            return False
        cur = self._hash_source()
        return cur != before

    def _config_dirty(self, st):
        return st.get("config_sha") != self._config_sha()

    def _config_sha(self):
        # hash the full config (plan, context, coder, reviewer, limits, roots).
        # Secrets never belong in config; credentials come only from the external
        # credentials map/file, so hashing config never hashes secret values.
        blob = json.dumps(self.config, sort_keys=True, default=str)
        return _sha(blob.encode("utf-8"))

    # -- source helpers -----------------------------------------------------

    def _source_content_for(self, task):
        out = {}
        src_root = os.path.join(self.run_dir, "source")
        for rel in task["scope"]:
            p = os.path.join(src_root, rel)
            if os.path.isfile(p):
                out[rel] = _read_text(p)
        return out

    def _apply_proposal(self, task, proposal):
        if not isinstance(proposal, dict) or not proposal:
            raise _Pause("empty_proposal")
        scope = set(task["scope"])
        # validate all destinations BEFORE any write
        for rel, content in proposal.items():
            rel = _check_safe_path(rel, "proposal")
            if rel not in scope:
                if rel.lower() in {s.lower() for s in scope}:
                    raise _Pause("scope_case_collision:%s" % rel)
                raise _Pause("outside_scope:%s" % rel)
            if rel in self.context_files or rel.lower() in {c.lower() for c in self.context_files}:
                raise _Pause("context_collision:%s" % rel)
            if any(rel.lower() == t.lower() for t in self._protected_names(task)):
                raise _Pause("protected_collision:%s" % rel)
            # reject test/acceptance names case-insensitively
            low = rel.lower()
            if "test_" in low or low.endswith(".py") and False:
                pass
            if re.search(r"test_", low):
                raise _Pause("writes_test:%s" % rel)
            if not isinstance(content, str):
                raise _Pause("bad_content_type")
            if len(content) > 100000:
                raise _Pause("file_too_large")
            # reject credential values in content
            for v in self.credentials.values():
                if v and v in content:
                    raise _Pause("credential_in_content")
            # reject symlink/junction parent
            dst = os.path.join(self.run_dir, "source", rel)
            if _has_symlink_parent(dst, os.path.join(self.run_dir, "source")):
                raise _Pause("symlink_destination")
        if len(proposal) > 10:
            raise _Pause("too_many_files")
        # now apply
        src_root = os.path.join(self.run_dir, "source")
        for rel, content in proposal.items():
            rel = _check_safe_path(rel, "proposal")
            dst = os.path.join(src_root, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if _has_symlink_parent(dst, src_root) or os.path.islink(dst):
                raise _Pause("symlink_destination")
            _write_text(dst, content)
        self._snapshot_source("after_apply")

    def _protected_names(self, task):
        names = set()
        for t in self._validated["tasks"]:
            for argv in t["tests"]:
                for a in argv:
                    if a.endswith(".py") or a.endswith(".json"):
                        names.add(_rel(a))
        return names

    # -- tests --------------------------------------------------------------

    def _run_tests(self, task):
        src_root = os.path.join(self.run_dir, "source")
        env = _scrubbed_env(self.credentials)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        pycache = os.path.join(self.run_dir, "pycache_%s" % uuid.uuid4().hex[:8])
        os.makedirs(pycache, exist_ok=True)
        env["PYTHONPYCACHEPREFIX"] = pycache
        before = self._hash_source()
        ok = True
        outputs = []
        for argv in task["tests"]:
            if not argv:
                ok = False
                continue
            cmd = [a.replace("{python}", sys.executable) for a in argv]
            timeout = min(self.call_timeout, self.remaining_seconds())
            if timeout <= 0:
                ok = False
                outputs.append({"argv": cmd, "exit_code": 124, "stdout_tail": "", "stderr_tail": "DEADLINE_NO_TIME"})
                continue
            try:
                proc = subprocess.run(
                    cmd, cwd=src_root, env=env, capture_output=True,
                    timeout=timeout, shell=False,
                )
            except subprocess.TimeoutExpired:
                ok = False
                outputs.append({"argv": cmd, "exit_code": 124, "stdout_tail": "", "stderr_tail": "TIMEOUT"})
                continue
            tail_out = proc.stdout.decode("utf-8", "replace")[-4000:]
            tail_err = proc.stderr.decode("utf-8", "replace")[-4000:]
            outputs.append({
                "argv": [redact(a, self.credentials) for a in cmd],
                "exit_code": proc.returncode,
                "stdout_tail": redact(tail_out, self.credentials),
                "stderr_tail": redact(tail_err, self.credentials),
            })
            if proc.returncode != 0:
                ok = False
        after = self._hash_source()
        # persist full redacted evidence (argv, exit codes, output tails) + hashes
        self.state.setdefault("evidence", {})[task["id"] + ":tests"] = {
            "exit_codes": [o.get("exit_code") if isinstance(o, dict) else 1 for o in outputs],
            "outputs": outputs,
            "before_hash": before,
            "after_hash": after,
            "source_hash": before,
            "test_hash": _sha(json.dumps(task["tests"], sort_keys=True).encode("utf-8")),
        }
        # on failure give the coder useful feedback
        if not ok:
            self.state.setdefault("last_feedback", {})[task["id"]] = {
                "exit_codes": [o.get("exit_code") if isinstance(o, dict) else 1 for o in outputs],
                "outputs": outputs,
            }
        # Detect protected/source mutation BEFORE persisting any new accepted
        # checkpoint, regardless of command exit code. If the tests mutated the
        # implementation or protected context, the pre-test hash must remain the
        # blessed baseline so a resume rejects the altered source instead of
        # silently accepting it.
        mutated = (after != before) and not self._only_expected_changes(task, before, after)
        if mutated:
            # permanently invalidate this run; do NOT bless after_tests.
            self.state["invalidated"] = True
            self.state["invalidated_reason"] = "tests_mutated_protected:%s" % task["id"]
            self._persist()
            raise _Pause("tests_mutated_protected")
        self._persist()
        self._snapshot_source("after_tests")
        return ok

    def _only_expected_changes(self, task, before, after):
        # hash ignores caches; any change to declared source/context is mutation
        if after == before:
            return True
        # recompute hashes limited to protected set
        return self._hash_protected() == before

    def _hash_protected(self):
        h = hashlib.sha256()
        files = set(self.context_files)
        for rel in sorted(files):
            p = os.path.join(self.run_dir, "source", rel)
            if os.path.isfile(p) and not _is_symlink(p):
                d = _read_bytes(p)
                h.update(rel.encode())
                h.update(b"\x00")
                h.update(_sha(d).encode())
                h.update(b"\x00")
        return h.hexdigest()

    def remaining_seconds(self):
        return max(0.0, self.max_seconds - (time.time() - self._started))

    # -- reviewer prompt ----------------------------------------------------

    def _current_evidence(self, task):
        ev = self.state.get("evidence", {})
        tests = ev.get(task["id"] + ":tests", {})
        return {
            "acceptance": task["acceptance"],
            "tests": task["tests"],
            "exit_codes": tests.get("exit_codes"),
            "output": tests,  # evidence includes real exit codes
        }

    def _build_coder_prompt(self, task, files, feedback):
        parts = []
        parts.append("You are a coding agent. Write files to satisfy this task.")
        parts.append("TASK: " + task["id"])
        parts.append("ACCEPTANCE: " + task["acceptance"])
        parts.append("SCOPE (writable): " + json.dumps(task["scope"]))
        parts.append("CURRENT FILES:")
        for rel, content in files.items():
            parts.append("--- %s ---\n%s" % (rel, redact(content, self.credentials)))
        if feedback:
            parts.append("LAST FEEDBACK (only recent):")
            parts.append(redact(json.dumps(feedback), self.credentials))
        parts.append("Respond with JSON: {\"files\": {relative_path: complete_text}}")
        return "\n".join(parts)

    def _build_reviewer_prompt(self, task, evidence):
        parts = []
        parts.append("You are an independent reviewer. Approve or reject.")
        parts.append("TASK: " + task["id"])
        parts.append("ACCEPTANCE: " + task["acceptance"])
        parts.append("TESTS (immutable argv): " + json.dumps(task["tests"]))
        parts.append("EVIDENCE (exit codes, output, fixture origin): " + redact(json.dumps(evidence), self.credentials))
        parts.append("CURRENT FILES:")
        for rel, content in self._source_content_for(task).items():
            parts.append("--- %s ---\n%s" % (rel, redact(content, self.credentials)))
        parts.append("Respond with JSON: {\"approved\": bool, \"findings\": [str]}")
        return "\n".join(parts)

    # -- state --------------------------------------------------------------

    def _persist(self):
        os.makedirs(self.run_dir, exist_ok=True)
        tmp = self.state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, sort_keys=True)
        os.replace(tmp, self.state_path)

    def _load_state(self):
        with open(self.state_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _set_stop(self, reason):
        self.state["state"] = "paused" if reason.startswith("paused") else "stopped"
        self.state["stop_reason"] = reason
        self.state["elapsed_seconds"] = time.time() - self._started
        self._persist()

    def _acquire_lock(self):
        os.makedirs(self.run_dir, exist_ok=True)
        if fcntl:
            self._lock_fd = open(self.lock_path, "w")
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                self._lock_fd.close()
                self._lock_fd = None
                raise _Pause("lock_held")
            self._owns_lock = True
            return
        # Windows / no fcntl: exclusive create with PID; recover only dead owner.
        my_pid = os.getpid()
        try:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            # a live lock exists; only recover if the owning PID is dead
            owner = self._read_lock_pid()
            if owner is not None and owner != my_pid and not _pid_alive(owner):
                try:
                    os.remove(self.lock_path)
                except OSError:
                    pass
                try:
                    fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                except FileExistsError:
                    raise _Pause("lock_held")
            else:
                raise _Pause("lock_held")
        os.write(fd, str(my_pid).encode("ascii"))
        os.close(fd)
        self._owns_lock = True

    def _read_lock_pid(self):
        try:
            with open(self.lock_path, "r", encoding="ascii") as f:
                return int(f.read().strip())
        except (OSError, ValueError):
            return None

    def _release_lock(self):
        if fcntl and getattr(self, "_owns_lock", False) and getattr(self, "_lock_fd", None):
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                self._lock_fd.close()
            except OSError:
                pass
            self._lock_fd = None
        elif getattr(self, "_owns_lock", False) and os.path.exists(self.lock_path):
            # only remove if we still own it (same PID)
            if self._read_lock_pid() == os.getpid():
                try:
                    os.remove(self.lock_path)
                except OSError:
                    pass
        self._owns_lock = False

    # -- helpers for staging test (minimal runner with empty plan) ----------


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _json_fence(text):
    """Strict JSON parse with markdown-fence trim. Returns (ok, obj)."""
    if text is None:
        return False, {}
    s = text.strip()
    # fence trim only
    m = re.match(r"^```(?:json)?\s*\n(.*?)\n```\s*$", s, re.DOTALL)
    if m:
        s = m.group(1).strip()
    try:
        obj = json.loads(s)
    except (ValueError, TypeError):
        return False, {}
    if not isinstance(obj, dict):
        return False, {}
    return True, obj


def _scrubbed_env(credentials):
    env = dict(os.environ)
    secret_names = {
        "api_key", "apikey", "token", "secret", "password", "passwd",
        "key", "credential", "auth", "deepseek_api_key", "openai_api_key",
    }
    secret_values = {v for v in credentials.values() if v}
    for k in list(env.keys()):
        low = k.lower()
        if any(s in low for s in secret_names):
            env.pop(k, None)
        elif env[k] in secret_values:
            env.pop(k, None)
    return env


def _write_text(p, content):
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)


def _write_staged(src_root, rel, src, dst):
    """Copy a source file into the staged tree, guarding against symlink/junction
    in the destination path (including nonexistent parent components)."""
    parent = os.path.dirname(dst)
    os.makedirs(parent, exist_ok=True)
    if _has_symlink_parent(dst, src_root):
        raise ValueError("staged destination symlink rejected: %s" % rel)
    if os.path.islink(dst):
        raise ValueError("staged destination is symlink: %s" % rel)
    shutil.copyfile(src, dst)


def _read_bytes(p):
    with open(p, "rb") as f:
        return f.read()


def _read_source_file(p):
    return _read_text(p)


# --------------------------------------------------------------------------- #
# CLI                                                                         #
# --------------------------------------------------------------------------- #


def _load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _main(argv=None):
    p = argparse.ArgumentParser(prog="portable", description="Portable workflow runner")
    p.add_argument("command", choices=["doctor", "run", "status"])
    p.add_argument("--config", required=True)
    p.add_argument("--credentials")
    p.add_argument("--offline", action="store_true")
    p.add_argument("--allow-tests", action="store_true")
    a = p.parse_args(argv)
    config = _load_config(a.config)
    creds = {}
    # Only a live RUN reads credentials; doctor/status/offline never read them.
    if a.credentials and a.command == "run" and not a.offline:
        # Resolve project_root relative to the CONFIG FILE DIRECTORY (not cwd),
        # so a relative project_root always lands against the same base as the
        # Runner itself uses.
        config_dir = os.path.dirname(os.path.abspath(a.config))
        proj_root = os.path.join(config_dir, config.get("project_root", "."))
        creds = load_credentials(a.credentials, proj_root)
    r = Runner(
        config, a.config, credentials=creds,
        offline=a.offline, allow_tests=a.allow_tests,
    )
    try:
        if a.command == "doctor":
            res = r.doctor()
            print(json.dumps({"ok": not any(x.startswith("ERROR") for x in res), "checks": res}))
        elif a.command == "status":
            print(json.dumps(r.status()))
        elif a.command == "run":
            if not a.offline and not a.allow_tests:
                print(json.dumps({"error": "--allow-tests required for live run"}))
                return 1
            st = r.run()
            print(json.dumps(st, default=str))
    except _Pause as e:
        print(json.dumps({"error": "paused", "reason": e.reason}))
        return 1
    except ValueError as e:
        print(json.dumps({"error": str(e)}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main())
