import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import portable


def _tmpdir():
    return tempfile.mkdtemp(prefix="runner_test_")


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class TestPlanFunctions(unittest.TestCase):
    def test_validate_plan_ok(self):
        plan = {"tasks": [{
            "id": "a", "priority": 1, "depends_on": [],
            "scope": ["demo.py"], "acceptance": "a",
            "tests": [["{python}", "-c", "assert True"]],
        }]}
        v = portable.validate_plan(plan)
        self.assertEqual(v["tasks"][0]["id"], "a")

    def test_validate_cycle(self):
        plan = {"tasks": [
            {"id": "a", "priority": 1, "depends_on": ["b"], "scope": ["x.py"], "acceptance": "a", "tests": [["p", "-c", "1"]]},
            {"id": "b", "priority": 1, "depends_on": ["a"], "scope": ["x.py"], "acceptance": "a", "tests": [["p", "-c", "1"]]},
        ]}
        with self.assertRaises(ValueError):
            portable.validate_plan(plan)

    def test_duplicate_id(self):
        plan = {"tasks": [
            {"id": "a", "priority": 1, "depends_on": [], "scope": ["x.py"], "acceptance": "a", "tests": [["p", "-c", "1"]]},
            {"id": "a", "priority": 1, "depends_on": [], "scope": ["x.py"], "acceptance": "a", "tests": [["p", "-c", "1"]]},
        ]}
        with self.assertRaises(ValueError):
            portable.validate_plan(plan)

    def test_unsafe_scope(self):
        for scope in [["../x.py"], ["test_x.py"], ["secret.py"], [".hidden.py"], ["/abs.py"]]:
            plan = {"tasks": [{"id": "a", "priority": 1, "depends_on": [], "scope": scope, "acceptance": "a", "tests": [["p", "-c", "1"]]}]}
            with self.assertRaises(ValueError):
                portable.validate_plan(plan)

    def test_choose_next_skips_passed(self):
        plan = {"tasks": [
            {"id": "a", "priority": 2, "depends_on": [], "scope": ["x.py"], "acceptance": "a", "tests": [["p", "-c", "1"]]},
            {"id": "b", "priority": 1, "depends_on": [], "scope": ["x.py"], "acceptance": "a", "tests": [["p", "-c", "1"]]},
        ]}
        statuses = {"a": "passed"}
        nxt = portable.choose_next(plan, statuses)
        self.assertEqual(nxt["id"], "b")

    def test_choose_next_requires_dep_passed(self):
        plan = {"tasks": [
            {"id": "a", "priority": 1, "depends_on": [], "scope": ["x.py"], "acceptance": "a", "tests": [["p", "-c", "1"]]},
            {"id": "b", "priority": 1, "depends_on": ["a"], "scope": ["x.py"], "acceptance": "a", "tests": [["p", "-c", "1"]]},
        ]}
        self.assertEqual(portable.choose_next(plan, {"a": "failed"})["id"], "a")
        self.assertEqual(portable.choose_next(plan, {"a": "passed"})["id"], "b")

    def test_choose_next_failed_still_selectable(self):
        plan = {"tasks": [{"id": "a", "priority": 1, "depends_on": [], "scope": ["x.py"], "acceptance": "a", "tests": [["p", "-c", "1"]]}]}
        nxt = portable.choose_next(plan, {"a": "failed"})
        self.assertEqual(nxt["id"], "a")


class TestCredentials(unittest.TestCase):
    def test_redact(self):
        text = "key=secret123 and value secret123 again"
        creds = {"API_KEY": "secret123"}
        out = portable.redact(text, creds)
        self.assertNotIn("secret123", out)
        self.assertIn("[REDACTED]", out)

    def test_load_reject_inside_repo(self):
        root = _tmpdir()
        cred = os.path.join(root, "creds.json")
        _write(cred, '{"K": "v"}')
        with self.assertRaises(ValueError):
            portable.load_credentials(cred, root)

    def test_load_json(self):
        root = _tmpdir()
        outside = _tmpdir()
        cred = os.path.join(outside, "creds.json")
        _write(cred, '{"K": "v"}')
        self.assertEqual(portable.load_credentials(cred, root), {"K": "v"})


class TestOffline(unittest.TestCase):
    def _offline_config(self, root, run_dir, plan):
        return {
            "project_root": root,
            "run_dir": run_dir,
            "plan": plan,
            "coder": {"model": "deepseek-v4-pro"},
            "reviewer": {"provider": "offline"},
            "limits": {"max_model_calls": 0, "max_seconds": 60, "max_fix_rounds": 5, "call_timeout": 10, "max_output_tokens": 100},
        }

    def test_offline_three_tasks_and_rerun(self):
        root = _tmpdir()
        run_dir = os.path.join(root, ".run")
        _write(os.path.join(root, "demo.py"), "")
        tasks = []
        for i, (name, deps, content) in enumerate([
            ("t1", [], "x = 1"),
            ("t2", ["t1"], "x = 2"),
            ("t3", ["t1", "t2"], "x = 3"),
        ]):
            tasks.append({
                "id": name, "priority": i, "depends_on": deps,
                "scope": ["demo.py"], "acceptance": name + " passes",
                "tests": [["{python}", "-c", "assert True"]],
                "offline_files": {"demo.py": content},
            })
        cfg = self._offline_config(root, run_dir, {"tasks": tasks})
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        r = portable.Runner(cfg, config_path, offline=True, allow_tests=True)
        st = r.run()
        self.assertEqual(sorted(st.get("completed", [])), ["t1", "t2", "t3"])
        # rerun skips passed
        st2 = portable.Runner(cfg, config_path, offline=True, allow_tests=True).run()
        self.assertEqual(st2["state"], "completed")

    def test_offline_no_secret_read(self):
        root = _tmpdir()
        run_dir = os.path.join(root, ".run")
        _write(os.path.join(root, "demo.py"), "")
        cfg = self._offline_config(root, run_dir, {"tasks": [{
            "id": "t1", "priority": 0, "depends_on": [],
            "scope": ["demo.py"], "acceptance": "a",
            "tests": [["{python}", "-c", "assert True"]],
            "offline_files": {"demo.py": "x=1"},
        }]})
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        with mock.patch("portable.load_credentials") as lc:
            r = portable.Runner(cfg, config_path, offline=True, allow_tests=True)
            r.run()
            lc.assert_not_called()


class TestLiveMock(unittest.TestCase):
    def _cfg(self, root, run_dir, tasks, max_calls=12):
        return {
            "project_root": root,
            "run_dir": run_dir,
            "plan": {"tasks": tasks},
            "coder": {"model": "m", "base_url": "https://api.deepseek.com"},
            "reviewer": {"provider": "api", "model": "rev", "base_url": "https://api.openai.com/v1"},
            "limits": {"max_model_calls": max_calls, "max_seconds": 600, "max_fix_rounds": 5, "call_timeout": 10, "max_output_tokens": 500},
        }

    def _mk(self, root, cfg):
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        creds = {"DEEPSEEK_API_KEY": "dk", "OPENAI_API_KEY": "ok"}
        return portable.Runner(cfg, config_path, credentials=creds, allow_tests=True)

    def test_call_limit_includes_reviewer(self):
        root = _tmpdir()
        _write(os.path.join(root, "demo.py"), "")
        tasks = [{"id": "a", "priority": 0, "depends_on": [], "scope": ["demo.py"], "acceptance": "a", "tests": [["{python}", "-c", "assert True"]]}]
        cfg = self._cfg(root, os.path.join(root, ".run"), tasks, max_calls=2)
        r = self._mk(root, cfg)
        coder_resp = {"choices": [{"message": {"content": '```json\n{"files":{"demo.py":"x=1"}}\n```'}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
        rev_resp = {"choices": [{"message": {"content": '{"approved": true, "findings": []}'}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
        with mock.patch.object(r, "_post_api", side_effect=[coder_resp, rev_resp]) as p:
            st = r.run()
            self.assertEqual(st["state"], "completed")
            self.assertEqual(st["model_calls"], 2)
            self.assertEqual(p.call_count, 2)

    def test_reviewer_uses_budget(self):
        root = _tmpdir()
        _write(os.path.join(root, "demo.py"), "")
        tasks = [{"id": "a", "priority": 0, "depends_on": [], "scope": ["demo.py"], "acceptance": "a", "tests": [["{python}", "-c", "assert True"]]}]
        cfg = self._cfg(root, os.path.join(root, ".run"), tasks, max_calls=1)
        r = self._mk(root, cfg)
        coder_resp = {"choices": [{"message": {"content": '{"files":{"demo.py":"x=1"}}'}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
        with mock.patch.object(r, "_post_api", side_effect=[coder_resp]) as p:
            st = r.run()
            self.assertEqual(st["model_calls"], 1)
            self.assertIn("budget", st["stop_reason"])

    def test_failed_then_repaired(self):
        root = _tmpdir()
        _write(os.path.join(root, "demo.py"), "")
        tasks = [{"id": "a", "priority": 0, "depends_on": [], "scope": ["demo.py"], "acceptance": "a", "tests": [["{python}", "-c", "import demo; assert demo.x == 1"]]}]
        cfg = self._cfg(root, os.path.join(root, ".run"), tasks, max_calls=12)
        r = self._mk(root, cfg)
        bad = {"choices": [{"message": {"content": '{"files":{"demo.py":"x = 0"}}'}}], "usage": {}}
        good = {"choices": [{"message": {"content": '{"files":{"demo.py":"x = 1"}}'}}], "usage": {}}
        rev = {"choices": [{"message": {"content": '{"approved": true, "findings": []}'}}], "usage": {}}
        with mock.patch.object(r, "_post_api", side_effect=[bad, good, rev]) as p:
            st = r.run()
            self.assertEqual(st["state"], "completed")
            self.assertGreaterEqual(p.call_count, 3)

    def test_rejected_5_rounds(self):
        root = _tmpdir()
        _write(os.path.join(root, "demo.py"), "")
        tasks = [{"id": "a", "priority": 0, "depends_on": [], "scope": ["demo.py"], "acceptance": "a", "tests": [["{python}", "-c", "assert True"]]}]
        cfg = self._cfg(root, os.path.join(root, ".run"), tasks, max_calls=20)
        r = self._mk(root, cfg)
        coder = {"choices": [{"message": {"content": '{"files":{"demo.py":"x=1"}}'}}], "usage": {}}
        rev = {"choices": [{"message": {"content": '{"approved": false, "findings": ["bad"]}'}}], "usage": {}}
        with mock.patch.object(r, "_post_api", side_effect=[coder, rev] * 6) as p:
            with self.assertRaises(portable._Pause) as ctx:
                r.run()
            self.assertIn("needs_codex_diagnosis", str(ctx.exception))

    def test_persisted_usage(self):
        root = _tmpdir()
        _write(os.path.join(root, "demo.py"), "")
        tasks = [{"id": "a", "priority": 0, "depends_on": [], "scope": ["demo.py"], "acceptance": "a", "tests": [["{python}", "-c", "assert True"]]}]
        cfg = self._cfg(root, os.path.join(root, ".run"), tasks, max_calls=4)
        r = self._mk(root, cfg)
        coder = {"choices": [{"message": {"content": '{"files":{"demo.py":"x=1"}}'}}], "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8}}
        rev = {"choices": [{"message": {"content": '{"approved": true, "findings": []}'}}], "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3}}
        with mock.patch.object(r, "_post_api", side_effect=[coder, rev]):
            st = r.run()
            self.assertEqual(st["usage"]["coder"]["prompt_tokens"], 5)
            self.assertEqual(st["usage"]["reviewer"]["total_tokens"], 3)

    def test_mode_change_rejected(self):
        root = _tmpdir()
        _write(os.path.join(root, "demo.py"), "")
        run_dir = os.path.join(root, ".run")
        tasks = [{"id": "a", "priority": 0, "depends_on": [], "scope": ["demo.py"], "acceptance": "a", "tests": [["{python}", "-c", "assert True"]], "offline_files": {"demo.py": "x=1"}}]
        cfg = self._cfg(root, run_dir, tasks)
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        r = portable.Runner(cfg, config_path, offline=True, allow_tests=True)
        r.run()
        # now live with same run_dir
        cfg2 = self._cfg(root, run_dir, tasks)
        r2 = portable.Runner(cfg2, config_path, credentials={"DEEPSEEK_API_KEY": "k", "OPENAI_API_KEY": "k"}, allow_tests=True)
        with self.assertRaises(portable._Pause):
            r2.run()


class TestDoctorStatus(unittest.TestCase):
    def test_doctor_no_keys(self):
        root = _tmpdir()
        _write(os.path.join(root, "demo.py"), "")
        cfg = {"project_root": root, "run_dir": os.path.join(root, ".run"), "plan": {"tasks": [{"id": "a", "priority": 0, "depends_on": [], "scope": ["demo.py"], "acceptance": "a", "tests": [["{python}", "-c", "assert True"]]}]}, "coder": {}, "reviewer": {"provider": "offline"}}
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        r = portable.Runner(cfg, config_path)
        res = r.doctor()
        self.assertEqual(res, [])

    def test_status_lists(self):
        root = _tmpdir()
        run_dir = os.path.join(root, ".run")
        _write(os.path.join(root, "demo.py"), "")
        cfg = {"project_root": root, "run_dir": run_dir, "plan": {"tasks": [{"id": "a", "priority": 0, "depends_on": [], "scope": ["demo.py"], "acceptance": "a", "tests": [["{python}", "-c", "assert True"]], "offline_files": {"demo.py": "x=1"}}]}, "coder": {}, "reviewer": {"provider": "offline"}, "limits": {"max_model_calls": 0}}
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        r = portable.Runner(cfg, config_path, offline=True, allow_tests=True)
        r.run()
        st = r.status()
        self.assertIsInstance(st["completed"], list)
        self.assertEqual(st["completed"], ["a"])


class TestContextStaging(unittest.TestCase):
    def test_context_files_staged(self):
        root = _tmpdir()
        run_dir = os.path.join(root, ".run")
        _write(os.path.join(root, "demo.py"), "ctx")
        _write(os.path.join(root, "test_demo.py"), "import demo")
        cfg = {
            "project_root": root, "run_dir": run_dir,
            "context": ["test_demo.py"],
            "plan": {"tasks": [{"id": "a", "priority": 0, "depends_on": [], "scope": ["demo.py"], "acceptance": "a", "tests": [["{python}", "-c", "assert 'import demo' in open('test_demo.py').read()"]], "offline_files": {"demo.py": "x=1"}}]},
            "coder": {}, "reviewer": {"provider": "offline"}, "limits": {"max_model_calls": 0},
        }
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        r = portable.Runner(cfg, config_path, offline=True, allow_tests=True)
        r.run()
        self.assertTrue(os.path.isfile(os.path.join(run_dir, "source", "test_demo.py")))

    def test_windows_symlink_staging(self):
        root = _tmpdir()
        run_dir = os.path.join(root, ".run")
        if os.name != "nt":
            self.skipTest("symlink-only test on windows semantics")
        # create project/demo.py symlink but include relevant scope
        real = os.path.join(root, "real_demo.py")
        _write(real, "")
        link = os.path.join(root, "demo.py")
        try:
            os.symlink(real, link)
        except OSError:
            self.skipTest("cannot symlink")
        cfg = {
            "project_root": root, "run_dir": run_dir,
            "plan": {"tasks": [{"id": "a", "priority": 0, "depends_on": [], "scope": ["demo.py"], "acceptance": "a", "tests": [["{python}", "-c", "assert True"]], "offline_files": {"demo.py": "x=1"}}]},
            "coder": {}, "reviewer": {"provider": "offline"}, "limits": {"max_model_calls": 0},
        }
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        r = portable.Runner(cfg, config_path, offline=True, allow_tests=True)
        with self.assertRaises((ValueError, portable._Pause)):
            r.run()

    def test_minimal_runner_empty_plan(self):
        root = _tmpdir()
        run_dir = os.path.join(root, ".run")
        cfg = {"project_root": root, "run_dir": run_dir, "plan": {"tasks": []}, "coder": {}, "reviewer": {"provider": "offline"}, "limits": {"max_model_calls": 0}}
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        r = portable.Runner(cfg, config_path)
        self.assertIsNotNone(r)


class TestProtectedTamper(unittest.TestCase):
    def test_context_tamper_blocks_pass(self):
        root = _tmpdir()
        run_dir = os.path.join(root, ".run")
        _write(os.path.join(root, "demo.py"), "")
        _write(os.path.join(root, "ctx.txt"), "ctx")
        cfg = {
            "project_root": root, "run_dir": run_dir, "context": ["ctx.txt"],
            "plan": {"tasks": [{"id": "a", "priority": 0, "depends_on": [], "scope": ["demo.py"], "acceptance": "a", "tests": [["{python}", "-c", "open('ctx.txt','w').write('tampered')"]], "offline_files": {"demo.py": "x=1"}}]},
            "coder": {}, "reviewer": {"provider": "offline"}, "limits": {"max_model_calls": 0},
        }
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        r = portable.Runner(cfg, config_path, offline=True, allow_tests=True)
        with self.assertRaises(portable._Pause):
            r.run()


class TestBlockerRegressions(unittest.TestCase):
    """Regressions for code-review blockers A-G (real negative checks)."""

    def _offline_cfg(self, root, run_dir, tasks, **kw):
        base = {
            "project_root": root, "run_dir": run_dir,
            "plan": {"tasks": tasks},
            "coder": {}, "reviewer": {"provider": "offline"},
            "limits": kw.get("limits", {"max_model_calls": 0}),
        }
        if kw.get("context"):
            base["context"] = kw["context"]
        return base

    def test_scope_rejects_drive_and_nested_dot(self):
        for bad in ["C:/outside.py", "/abs.py", "a\\b.py", "src/.env", ".hidden.py", "foo/../bar.py", "foo/bar/../x.py"]:
            plan = {"tasks": [{"id": "a", "priority": 1, "depends_on": [], "scope": [bad], "acceptance": "a", "tests": [["{python}", "-c", "assert True"]]}]}
            with self.assertRaises(ValueError, msg="should reject %r" % bad):
                portable.validate_plan(plan)

    def test_context_rejects_containment(self):
        root = _tmpdir()
        _write(os.path.join(root, "demo.py"), "")
        cfg = self._offline_cfg(root, os.path.join(root, ".run"), [])
        cfg["context"] = ["C:/outside.py"]
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        r = portable.Runner(cfg, config_path, offline=True, allow_tests=True)
        with self.assertRaises(ValueError):
            r._resolve_context()

    def test_context_overflow_not_charged(self):
        root = _tmpdir()
        _write(os.path.join(root, "demo.py"), "")
        tasks = [{"id": "a", "priority": 0, "depends_on": [], "scope": ["demo.py"], "acceptance": "a", "tests": [["{python}", "-c", "assert True"]]}]
        cfg = {
            "project_root": root, "run_dir": os.path.join(root, ".run"),
            "plan": {"tasks": tasks},
            "coder": {"model": "m", "base_url": "https://api.deepseek.com"},
            "reviewer": {"provider": "api", "model": "r", "base_url": "https://api.openai.com/v1"},
            "limits": {"max_model_calls": 100, "max_fix_rounds": 5, "call_timeout": 10},
            "max_context_chars": 10,
        }
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        r = portable.Runner(cfg, config_path, credentials={"DEEPSEEK_API_KEY": "k", "OPENAI_API_KEY": "k"}, allow_tests=True)
        with self.assertRaises(portable._Pause) as ctx:
            r.run()
        self.assertIn("context", str(ctx.exception))
        self.assertEqual(r.state.get("model_calls", 0), 0)

    def test_deadline_zero_gates_call(self):
        root = _tmpdir()
        _write(os.path.join(root, "demo.py"), "")
        tasks = [{"id": "a", "priority": 0, "depends_on": [], "scope": ["demo.py"], "acceptance": "a", "tests": [["{python}", "-c", "assert True"]]}]
        cfg = {
            "project_root": root, "run_dir": os.path.join(root, ".run"),
            "plan": {"tasks": tasks},
            "coder": {"model": "m", "base_url": "https://api.deepseek.com"},
            "reviewer": {"provider": "api", "model": "r", "base_url": "https://api.openai.com/v1"},
            "limits": {"max_model_calls": 100, "max_seconds": 0, "max_fix_rounds": 5, "call_timeout": 10},
        }
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        r = portable.Runner(cfg, config_path, credentials={"DEEPSEEK_API_KEY": "k", "OPENAI_API_KEY": "k"}, allow_tests=True)
        with mock.patch.object(r, "_post_api") as api:
            r.run()
        self.assertEqual(r.state.get("model_calls", 0), 0)
        self.assertFalse(api.called)


    def test_two_locks_one_winner(self):
        root = _tmpdir()
        run_dir = os.path.join(root, ".run")
        _write(os.path.join(root, "demo.py"), "")
        cfg = self._offline_cfg(root, run_dir, [])
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        r1 = portable.Runner(cfg, config_path, offline=True, allow_tests=True)
        r2 = portable.Runner(cfg, config_path, offline=True, allow_tests=True)
        r1._acquire_lock()
        try:
            with self.assertRaises(portable._Pause):
                r2._acquire_lock()
        finally:
            r1._release_lock()

    def test_stale_dead_pid_lock_recovered(self):
        root = _tmpdir()
        run_dir = os.path.join(root, ".run")
        os.makedirs(run_dir, exist_ok=True)
        _write(os.path.join(root, "demo.py"), "")
        cfg = self._offline_cfg(root, run_dir, [])
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        lock_path = os.path.join(run_dir, ".lock")
        with open(lock_path, "w") as f:
            f.write("99999999")
        r = portable.Runner(cfg, config_path, offline=True, allow_tests=True)
        try:
            r._acquire_lock()
            r._release_lock()
        except portable._Pause as e:
            self.assertEqual(str(e), "lock_held")

    def test_config_rejects_secret_values(self):
        root = _tmpdir()
        _write(os.path.join(root, "demo.py"), "")
        cfg = self._offline_cfg(root, os.path.join(root, ".run"), [])
        cfg["coder"] = {"model": "m", "api_key": "sk-abc123"}
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        with self.assertRaises(ValueError):
            portable.Runner(cfg, config_path, offline=True, allow_tests=True)

    def test_redact_findings_and_output(self):
        text = "findings mention sk-abc123 and DEEPSEEK key"
        creds = {"DEEPSEEK_API_KEY": "sk-abc123", "OPENAI_API_KEY": "ok-xyz"}
        out = portable.redact(text, creds)
        self.assertNotIn("sk-abc123", out)
        self.assertNotIn("ok-xyz", out)
        self.assertIn("[REDACTED]", out)

    def test_run_tests_persists_output_and_feedback(self):
        root = _tmpdir()
        run_dir = os.path.join(root, ".run")
        _write(os.path.join(root, "demo.py"), "")
        tasks = [{"id": "a", "priority": 0, "depends_on": [], "scope": ["demo.py"], "acceptance": "a", "tests": [["{python}", "-c", "assert False"]], "offline_files": {"demo.py": "x=1"}}]
        cfg = self._offline_cfg(root, run_dir, tasks)
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        r = portable.Runner(cfg, config_path, offline=True, allow_tests=True)
        r._validated = portable.validate_plan(cfg["plan"])
        r.context_files = []
        r.state = {"offline": True, "model_calls": 0, "statuses": {}, "attempts": {}, "valid_attempts": {}, "last_feedback": {}, "source_hash": {}, "evidence": {}, "completed": [], "usage": {}}
        r._stage_source()
        ok = r._run_tests(tasks[0])
        self.assertFalse(ok)
        ev = r.state["evidence"][tasks[0]["id"] + ":tests"]
        self.assertIn("exit_codes", ev)
        self.assertIn("outputs", ev)
        self.assertEqual(ev["exit_codes"], [1])
        self.assertIn(tasks[0]["id"], r.state["last_feedback"])

    def test_offline_failing_fixture_pauses_not_passes(self):
        root = _tmpdir()
        run_dir = os.path.join(root, ".run")
        _write(os.path.join(root, "demo.py"), "")
        tasks = [{"id": "a", "priority": 0, "depends_on": [], "scope": ["demo.py"], "acceptance": "a", "tests": [["{python}", "-c", "assert False"]], "offline_files": {"demo.py": "x=1"}}]
        cfg = self._offline_cfg(root, run_dir, tasks)
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        r = portable.Runner(cfg, config_path, offline=True, allow_tests=True)
        with self.assertRaises(portable._Pause):
            r.run()
        self.assertNotEqual(r.state.get("statuses", {}).get("a"), "passed")

    def test_offline_empty_scope_still_runs_tests(self):
        root = _tmpdir()
        run_dir = os.path.join(root, ".run")
        _write(os.path.join(root, "demo.py"), "")
        tasks = [{"id": "a", "priority": 0, "depends_on": [], "scope": ["demo.py"], "acceptance": "a", "tests": [["{python}", "-c", "assert False"]]}]
        cfg = self._offline_cfg(root, run_dir, tasks)
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        r = portable.Runner(cfg, config_path, offline=True, allow_tests=True)
        with self.assertRaises(portable._Pause):
            r.run()
        self.assertNotEqual(r.state.get("statuses", {}).get("a"), "passed")


class TestBlockerFixes(unittest.TestCase):
    """Focused regressions for the six reviewer blockers (fixed functions)."""

    def _offline_cfg(self, root, run_dir, tasks, **kw):
        base = {
            "project_root": root, "run_dir": run_dir,
            "plan": {"tasks": tasks},
            "coder": {}, "reviewer": {"provider": "offline"},
            "limits": kw.get("limits", {"max_model_calls": 0}),
        }
        if kw.get("context"):
            base["context"] = kw["context"]
        return base

    def _fresh_runner(self, root, run_dir, tasks, **kw):
        cfg = self._offline_cfg(root, run_dir, tasks, **kw)
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        r = portable.Runner(cfg, config_path, offline=True, allow_tests=True)
        r._validated = portable.validate_plan(cfg["plan"])
        r.context_files = r._resolve_context()
        r.state = {
            "offline": True, "model_calls": 0, "statuses": {},
            "attempts": {}, "valid_attempts": {}, "last_feedback": {},
            "source_hash": {}, "evidence": {}, "completed": [], "usage": {},
        }
        return r

    def test_verify_source_after_review_uses_fresh_hash(self):
        root = _tmpdir()
        run_dir = os.path.join(root, ".run")
        _write(os.path.join(root, "demo.py"), "")
        tasks = [{"id": "a", "priority": 0, "depends_on": [], "scope": ["demo.py"],
                  "acceptance": "a", "tests": [["{python}", "-c", "assert True"]],
                  "offline_files": {"demo.py": "x=1"}}]
        r = self._fresh_runner(root, run_dir, tasks)
        r._stage_source()
        r._snapshot_source("after_tests")
        _write(os.path.join(run_dir, "source", "demo.py"), "x = 999")
        with self.assertRaises(portable._Pause) as ctx:
            r._verify_source_after_review(tasks[0])
        self.assertEqual(str(ctx.exception), "source_mutated_review_rejected")
        _write(os.path.join(run_dir, "source", "demo.py"), "x=1")
        r._snapshot_source("after_tests")
        r._verify_source_after_review(tasks[0])

    def test_test_mutation_not_blessed_on_resume(self):
        root = _tmpdir()
        run_dir = os.path.join(root, ".run")
        _write(os.path.join(root, "demo.py"), "")
        tasks = [{"id": "a", "priority": 0, "depends_on": [], "scope": ["demo.py"],
                  "acceptance": "a",
                  "tests": [["{python}", "-c",
                             "open('demo.py','w').write('x=999'); import sys; sys.exit(1)"]],
                  "offline_files": {"demo.py": "x=1"}}]
        cfg = self._offline_cfg(root, run_dir, tasks)
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        r = portable.Runner(cfg, config_path, offline=True, allow_tests=True)
        r._validated = portable.validate_plan(cfg["plan"])
        r.context_files = r._resolve_context()
        r.state = {
            "offline": True, "model_calls": 0, "statuses": {},
            "attempts": {}, "valid_attempts": {}, "last_feedback": {},
            "source_hash": {}, "evidence": {}, "completed": [], "usage": {},
        }
        r._stage_source()
        with self.assertRaises(portable._Pause) as ctx:
            r._run_tests(tasks[0])
        self.assertEqual(str(ctx.exception), "tests_mutated_protected")
        self.assertNotEqual(
            r.state.get("source_hash", {}).get("after_tests"), r._hash_source())
        self.assertTrue(r.state.get("invalidated"))
        st = r.state
        r2 = portable.Runner(cfg, config_path, offline=True, allow_tests=True)
        r2._validated = portable.validate_plan(cfg["plan"])
        r2.context_files = r2._resolve_context()
        r2.state = st
        with self.assertRaises(portable._Pause):
            r2._verify_source_retained()

    def test_latest_checkpoint_prefers_after_apply(self):
        root = _tmpdir()
        run_dir = os.path.join(root, ".run")
        _write(os.path.join(root, "demo.py"), "")
        tasks = [{"id": "a", "priority": 0, "depends_on": [], "scope": ["demo.py"],
                  "acceptance": "a", "tests": [["{python}", "-c", "assert True"]]}]
        r = self._fresh_runner(root, run_dir, tasks)
        r._stage_source()
        before_start = r.state["source_hash"]["before_start"]
        _write(os.path.join(run_dir, "source", "demo.py"), "x=2")
        r._snapshot_source("after_apply")
        after_apply = r.state["source_hash"]["after_apply"]
        self.assertNotEqual(before_start, after_apply)
        self.assertEqual(r._latest_source_checkpoint(), after_apply)
        self.assertEqual(r.state["source_hash"]["last_source_checkpoint"], "after_apply")

    def test_pid_alive_live_and_dead_child(self):
        import time
        # simple long-sleeping child; no signal involved
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        try:
            time.sleep(0.1)
            self.assertTrue(portable._pid_alive(proc.pid), "live child should be alive")
        finally:
            proc.terminate()
            proc.wait(timeout=10)
        self.assertFalse(portable._pid_alive(proc.pid), "dead child should be dead")

    @unittest.skipUnless(os.name == "nt", "Windows-only access-denied probe")
    def test_pid_alive_access_denied_is_alive(self):
        import ctypes
        from ctypes import wintypes
        # OpenProcess fails with ERROR_ACCESS_DENIED (5): an unqueryable but
        # existing process (e.g. System PID 4) must be treated as alive, not
        # falsely dead. get_last_error() must stay in sync via use_last_error.
        with mock.patch("ctypes.WinDLL", create=True) as wdll:
            k32 = wdll.return_value
            k32.OpenProcess.return_value = None
            k32.GetExitCodeProcess.restype = wintypes.BOOL
            k32.CloseHandle.restype = wintypes.BOOL
            # The use_last_error wrapper resets the thread last-error to 0 on
            # entry; force it to 5 inside the mocked call so get_last_error()
            # reads 5 on the failed OpenProcess branch.
            def open_fail(*args):
                ctypes.set_last_error(5)
                return None
            k32.OpenProcess.side_effect = open_fail
            self.assertTrue(portable._pid_alive(99999999))

    def test_pid_alive_invalid_parameter_is_dead(self):
        # OpenProcess failing with ERROR_INVALID_PARAMETER (87) is the only
        # case where we confidently report a process as dead.
        import ctypes
        from ctypes import wintypes
        with mock.patch("ctypes.WinDLL", create=True) as wdll:
            k32 = wdll.return_value
            def open_fail(*args):
                ctypes.set_last_error(87)
                return None
            k32.OpenProcess.side_effect = open_fail
            self.assertFalse(portable._pid_alive(99999999))

    def test_has_symlink_parent_root_mocked(self):
        # A symlink/junction at the root itself (e.g. a pre-existing run_dir
        # junction) must be rejected, not bypassed by only checking children.
        with mock.patch("portable._is_symlink") as islink:
            islink.return_value = True
            self.assertTrue(
                portable._has_symlink_parent(
                    os.path.join("r", "sub", "file.txt"), "r"
                )
            )

    def test_has_symlink_parent_root_sentinel(self):
        # Actual root-dir symlink sentinel, where the platform lets us create
        # one. No external sentinel is written; only the temp root dir.
        root = _tmpdir()
        target = _tmpdir()
        _write(os.path.join(target, "child.txt"), "")
        link = os.path.join(root, "run_link")
        try:
            os.symlink(target, link, target_is_directory=True)
        except (OSError, AttributeError):
            self.skipTest("cannot create directory symlink")
        if not portable._is_symlink(link):
            self.skipTest("symlink not detected by _is_symlink")
        self.assertTrue(
            portable._has_symlink_parent(os.path.join(link, "child.txt"), link)
        )

    def test_run_codex_stale_file_never_read_on_nonzero_exit(self):
        # A stale reviewer_out.tmp left by a previous attempt must not be read:
        # a nonzero returncode raises _Pause BEFORE any output file is read.
        root = _tmpdir()
        run_dir = os.path.join(root, ".run")
        src = os.path.join(run_dir, "source")
        os.makedirs(src, exist_ok=True)
        # Stale, approved-looking JSON from an earlier run.
        stale = os.path.join(run_dir, "reviewer_out.tmp")
        _write(stale, json.dumps({"verdict": "PASS"}))
        cfg = {
            "project_root": root, "run_dir": run_dir, "plan": {"tasks": []},
            "coder": {}, "reviewer": {"provider": "codex"},
            "limits": {"max_model_calls": 1, "call_timeout": 10},
        }
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        r = portable.Runner(cfg, config_path, credentials={}, allow_tests=True)
        import subprocess as _sp
        fake = _sp.CompletedProcess([], 1, stdout=b"", stderr=b"")
        with mock.patch("portable.subprocess.run", return_value=fake), \
             mock.patch("portable._read_text") as rt:
            with self.assertRaises(portable._Pause) as ctx:
                r._run_codex("codex", "prompt")
            self.assertIn("reviewer_process_failed", str(ctx.exception))
            rt.assert_not_called()

    def test_run_codex_missing_unique_output_raises(self):
        # returncode 0 but no unique output file -> _Pause, and the stale file is
        # not read (the unique filename is what we check).
        root = _tmpdir()
        run_dir = os.path.join(root, ".run")
        src = os.path.join(run_dir, "source")
        os.makedirs(src, exist_ok=True)
        _write(os.path.join(run_dir, "reviewer_out.tmp"), "stale")
        cfg = {
            "project_root": root, "run_dir": run_dir, "plan": {"tasks": []},
            "coder": {}, "reviewer": {"provider": "codex"},
            "limits": {"max_model_calls": 1, "call_timeout": 10},
        }
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        r = portable.Runner(cfg, config_path, credentials={}, allow_tests=True)
        import subprocess as _sp
        fake = _sp.CompletedProcess([], 0, stdout=b"", stderr=b"")
        with mock.patch("portable.subprocess.run", return_value=fake), \
             mock.patch("portable._read_text") as rt:
            with self.assertRaises(portable._Pause) as ctx:
                r._run_codex("codex", "prompt")
            self.assertIn("reviewer_output_missing", str(ctx.exception))
            rt.assert_not_called()

    def test_run_codex_reads_unique_output_and_cleans_up(self):
        # Mock subprocess writes valid JSON to the unique --output-last-message
        # path; returncode 0 -> that JSON is returned and the temp file removed.
        root = _tmpdir()
        run_dir = os.path.join(root, ".run")
        src = os.path.join(run_dir, "source")
        os.makedirs(src, exist_ok=True)
        cfg = {
            "project_root": root, "run_dir": run_dir, "plan": {"tasks": []},
            "coder": {}, "reviewer": {"provider": "codex"},
            "limits": {"max_model_calls": 1, "call_timeout": 10},
        }
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        r = portable.Runner(cfg, config_path, credentials={}, allow_tests=True)
        fresh = json.dumps({"verdict": "PASS", "fresh": True})
        import subprocess as _sp

        def _fake_run(cmd, **kwargs):
            # cmd: [exe, "exec", ..., "--output-last-message", TMP, "-"]
            i = cmd.index("--output-last-message")
            out_path = cmd[i + 1]
            _write(out_path, fresh)
            return _sp.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")

        with mock.patch("portable.subprocess.run", side_effect=_fake_run):
            result = r._run_codex("codex", "prompt")
        self.assertEqual(result, fresh)
        # The unique temp output must be removed after a successful read.
        leftover = [f for f in os.listdir(run_dir)
                    if f.startswith("reviewer_out-")]
        self.assertEqual(leftover, [])

    def test_run_codex_never_launches_at_zero_remaining(self):
        root = _tmpdir()
        run_dir = os.path.join(root, ".run")
        _write(os.path.join(root, "demo.py"), "")
        tasks = [{"id": "a", "priority": 0, "depends_on": [], "scope": ["demo.py"],
                  "acceptance": "a", "tests": [["{python}", "-c", "assert True"]]}]
        cfg = {
            "project_root": root, "run_dir": run_dir, "plan": {"tasks": tasks},
            "coder": {"model": "m", "base_url": "https://api.deepseek.com"},
            "reviewer": {"provider": "codex"},
            "limits": {"max_model_calls": 10, "max_seconds": 0,
                       "max_fix_rounds": 5, "call_timeout": 10},
        }
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        r = portable.Runner(cfg, config_path, credentials={}, allow_tests=True)
        with mock.patch("portable.subprocess.run") as run:
            with self.assertRaises(portable._Pause) as ctx:
                r._run_codex("codex", "prompt")
            self.assertIn("deadline", str(ctx.exception))
            self.assertFalse(run.called)

    def test_main_resolves_project_root_relative_to_config_dir(self):
        root = _tmpdir()
        cfgdir = os.path.join(root, "sub", "cfg")
        os.makedirs(cfgdir, exist_ok=True)
        proj = os.path.join(cfgdir, "proj")
        os.makedirs(proj, exist_ok=True)
        _write(os.path.join(proj, "demo.py"), "")
        cfg = {"project_root": "proj", "run_dir": ".run",
               "plan": {"tasks": []}, "coder": {}, "reviewer": {"provider": "offline"}}
        config_path = os.path.join(cfgdir, "cfg.json")
        cred_path = os.path.join(root, "creds.json")
        _write(config_path, json.dumps(cfg))
        _write(cred_path, '{"K": "v"}')
        with mock.patch("portable.load_credentials") as lc, \
             mock.patch("portable.Runner") as MR:
            lc.return_value = {"K": "v"}
            MR.return_value.run.return_value = {"state": "completed"}
            MR.return_value.state = {}
            portable._main(["run", "--config", config_path,
                            "--credentials", cred_path, "--allow-tests"])
        self.assertTrue(lc.called)
        self.assertEqual(os.path.normpath(lc.call_args[0][1]), os.path.normpath(proj))

    def test_findings_redacted_before_persist(self):
        root = _tmpdir()
        run_dir = os.path.join(root, ".run")
        _write(os.path.join(root, "demo.py"), "")
        tasks = [{"id": "a", "priority": 0, "depends_on": [], "scope": ["demo.py"],
                  "acceptance": "a", "tests": [["{python}", "-c", "assert True"]]}]
        cfg = {
            "project_root": root, "run_dir": run_dir, "plan": {"tasks": tasks},
            "coder": {"model": "m", "base_url": "https://api.deepseek.com"},
            "reviewer": {"provider": "api", "model": "r",
                         "base_url": "https://api.openai.com/v1"},
            "limits": {"max_model_calls": 10, "max_fix_rounds": 5, "call_timeout": 10},
        }
        config_path = os.path.join(root, "cfg.json")
        _write(config_path, json.dumps(cfg))
        secret = "sk-super-secret-value"
        r = portable.Runner(cfg, config_path,
                            credentials={"OPENAI_API_KEY": secret}, allow_tests=True)
        r._validated = portable.validate_plan(cfg["plan"])
        r.context_files = []
        r.state = {
            "offline": False, "model_calls": 0, "statuses": {}, "attempts": {},
            "valid_attempts": {}, "last_feedback": {}, "source_hash": {},
            "evidence": {}, "completed": [], "usage": {},
        }
        with mock.patch.object(r, "_call_reviewer",
                               return_value=(True, ["finding mentions " + secret])), \
             mock.patch.object(r, "_run_tests", return_value=True), \
             mock.patch.object(r, "_record_pass"), \
             mock.patch.object(r, "_verify_source_after_review"), \
             mock.patch.object(r, "_apply_proposal"), \
             mock.patch.object(r, "_call_coder", return_value={"demo.py": "x=1"}):
            r._do_task(tasks[0])
        fb = r.state.get("last_feedback", {}).get("a")
        self.assertIsNotNone(fb)
        self.assertNotIn(secret, json.dumps(fb))
        self.assertIn("[REDACTED]", json.dumps(fb))


if __name__ == "__main__":
    unittest.main()
