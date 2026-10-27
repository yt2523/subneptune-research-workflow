"""Small, local, serial research workflow. No solver is launched by this module."""
import argparse, datetime as dt, hashlib, json, os, re, subprocess, sys, uuid
from pathlib import Path, PurePosixPath
BASE=Path(__file__).resolve().parent
ALLOWED_SUFFIXES={'.py','.md','.csv','.json','.txt','.cpp','.cc','.c','.h','.hpp','.f','.f90','.f95','.jl','.toml','.yaml','.yml','.cfg','.ini'}
GIT=r'C:\Program Files\Git\cmd\git.exe'
def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def write_json(path,data):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    os.replace(tmp,path)
def validate_files(files):
    if not isinstance(files,dict) or not files or len(files)>10: raise ValueError('1..10 files required')
    for name,content in files.items():
        p=PurePosixPath(name)
        if not isinstance(content,str) or len(content)>100000: raise ValueError('invalid file content')
        if not name or '\\' in name or ':' in name or p.is_absolute() or '..' in p.parts or any(x.startswith('.') for x in p.parts): raise ValueError('unsafe path')
        if p.suffix.lower() not in ALLOWED_SUFFIXES: raise ValueError('file type not allowed')
def fingerprint(root):
    h=hashlib.sha256()
    for p in sorted(root.rglob('*')):
        if '.git' in p.relative_to(root).parts or '__pycache__' in p.parts: continue
        if p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()): raise ValueError('symlink/junction forbidden')
        if p.is_file():
            name=p.relative_to(root).as_posix().encode('utf-8'); h.update(len(name).to_bytes(8,'big')); h.update(name); h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()
class Store:
    def __init__(self,root): self.root=Path(root).resolve(); self.source=self.root/'source'
    def digest(self):
        contract={'source':fingerprint(self.source),'task':(self.root/'TASK.md').read_text(encoding='utf-8'),'scope':(self.root/'scope.json').read_text(encoding='utf-8') if (self.root/'scope.json').exists() else None}
        return hashlib.sha256(json.dumps(contract,sort_keys=True,ensure_ascii=False).encode('utf-8')).hexdigest()
    def state(self):
        s=json.loads((self.root/'state.json').read_text(encoding='utf-8'))
        try:
            lines=(self.root/'audit.jsonl').read_text(encoding='utf-8').splitlines()
            seq=json.loads(lines[-1]).get('seq',0) if lines else 0
            if seq!=s.get('_audit_seq',0):
                s.update(status='recovery_required',human_run_approved=False,_pending_audit_seq=seq)
        except (ValueError,OSError):
            s.update(status='recovery_required',human_run_approved=False)
        return s
    def save(self,s,event,**details):
        # Single writer only. Audit is written first; interrupted transitions fail closed on resume.
        seq=max(s.get('_audit_seq',0),s.pop('_pending_audit_seq',0))+1
        row={'time':now(),'seq':seq,'event':event,'run_id':self.root.name,**details}
        with (self.root/'audit.jsonl').open('a',encoding='utf-8') as f:
            f.write(json.dumps(row,ensure_ascii=False)+'\n'); f.flush(); os.fsync(f.fileno())
        s['_audit_seq']=seq; s['updated_at']=now(); write_json(self.root/'state.json',s)
    def initialize(self,task):
        self.root.mkdir(parents=True,exist_ok=True)
        if (self.root/'state.json').exists(): raise ValueError('run already exists')
        self.source.mkdir(exist_ok=True)
        (self.root/'TASK.md').write_text(task,encoding='utf-8')
        self.save({'status':'ready','iteration':0,'human_run_approved':False},'initialized')
    def propose(self,proposal):
        if proposal.get('model')!='deepseek': raise ValueError('coder must be DeepSeek')
        validate_files(proposal['files']); self.digest()
        if (self.root/'scope.json').exists():
            allowed=json.loads((self.root/'scope.json').read_text(encoding='utf-8'))
            if not isinstance(allowed,list) or not set(proposal['files']).issubset(allowed): raise ValueError('proposal outside declared scope')
        for name in proposal['files']:
            target=self.source/name
            if target.exists() and not target.is_file(): raise ValueError('invalid target')
        s=self.state(); s.pop('pause_reason',None); s.update(status='writing',human_run_approved=False,review_pass=False,tests_pass=False)
        self.save(s,'proposal_started')
        for name,content in proposal['files'].items():
            p=self.source/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(content,encoding='utf-8')
        s['iteration']+=1; s['status']='awaiting_tests'; s['code_hash']=self.digest()
        write_json(self.root/f'proposal-{s["iteration"]:02}.json',proposal)
        self.save(s,'proposal_applied',code_hash=s['code_hash'],iteration=s['iteration'])
        self.checkpoint()
    def record_tests(self,passed,summary):
        s=self.state(); s.update(tests_pass=bool(passed),tests_hash=self.digest(),human_run_approved=False,status='awaiting_human' if passed and s.get('review_pass') and s.get('review_hash')==self.digest() else 'awaiting_review')
        (self.root/f'tests-{s["iteration"]:02}.md').write_text(summary,encoding='utf-8')
        self.save(s,'tests_recorded',passed=bool(passed),code_hash=s['tests_hash'])
    def review(self,result,code_hash):
        if result.get('model')!='gpt': raise ValueError('reviewer must be GPT')
        if code_hash!=self.digest(): raise ValueError('stale review')
        if type(result.get('approved')) is not bool or not isinstance(result.get('findings'),list): raise ValueError('invalid review')
        s=self.state(); s.pop('pause_reason',None); s.update(review_hash=code_hash,review_pass=result['approved'],human_run_approved=False,status='awaiting_human' if result['approved'] else 'changes_requested')
        write_json(self.root/f'review-{s["iteration"]:02}.json',result)
        self.save(s,'review_recorded',approved=result['approved'],code_hash=code_hash)
    def approve(self):
        s=self.state(); h=self.digest()
        if not(s.get('review_pass') and s.get('tests_pass') and s.get('review_hash')==h and s.get('tests_hash')==h): raise ValueError('current tests and independent review required')
        s.update(human_run_approved=True,approval_hash=h,status='approved')
        self.save(s,'human_approved',code_hash=h)
    def can_run(self):
        s=self.state(); h=self.digest()
        return bool(s.get('human_run_approved') and s.get('review_pass') and s.get('tests_pass') and s.get('review_hash')==h and s.get('tests_hash')==h and s.get('approval_hash')==h)
    def pause(self,reason):
        s=self.state(); s.update(status='paused',pause_reason=reason,human_run_approved=False)
        self.save(s,'paused',reason=reason)
    def checkpoint(self):
        # Local Git history belongs to this disposable run, never to the user's dirty checkout.
        if not (self.source/'.git').exists():
            self.git('init','-b','workflow-test')
            self.git('config','user.name','Research workflow'); self.git('config','user.email','workflow@localhost')
            (self.source/'.git/info/exclude').write_text('__pycache__/\n*.pyc\n',encoding='utf-8')
        self.git('add','--all'); self.git('commit','--allow-empty','-m',f'workflow iteration {self.state()["iteration"]}')
        sha=self.git('rev-parse','HEAD').strip()
        s=self.state(); self.save(s,'git_checkpoint',commit=sha); return sha
    def git(self,*args):
        r=subprocess.run([GIT,'-C',str(self.source),*args],capture_output=True,text=True,encoding='utf-8',errors='replace')
        if r.returncode: raise RuntimeError(r.stderr)
        return r.stdout
    def report(self):
        s=self.state()
        content=f'''# 工作流运行报告\n\n- 运行：{self.root.name}\n- 状态：{s['status']}\n- 修改轮数：{s['iteration']}\n- 当前代码摘要：{self.digest()}\n- 审核通过：{s.get('review_pass',False)}\n- 测试通过：{s.get('tests_pass',False)}\n- 计算入口允许：{self.can_run()}\n\n## 优先阅读\n1. TASK.md：任务、物理假设与验收条件。\n2. 最新 review-XX.json：缺陷与审核意见。\n3. 最新 tests-XX.md：实际执行的测试及结果。\n4. source/ 与本地 Git 历史：逐轮代码变化。\n5. audit.jsonl、state.json：动作和恢复位置。\n\n## 科学结论边界\n此报告只说明工作流状态。测试数据不是行星观测，测试通过不代表 TP/EOS 物理正确。\n'''
        (self.root/'REPORT.md').write_text(content,encoding='utf-8'); return content

def main():
    p=argparse.ArgumentParser(); p.add_argument('action',choices=['new','status','import','approve','pause','report','checkpoint']); p.add_argument('--run',type=Path); p.add_argument('--file',type=Path); p.add_argument('--reason',default='manual'); p.add_argument('--repo',type=Path); p.add_argument('--scope',type=Path)
    a=p.parse_args()
    if a.action=='new':
        root=BASE/'runs'/(dt.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]); s=Store(root); s.initialize(a.file.read_text(encoding='utf-8') if a.file else 'Infrastructure trial; no science runs.')
        if a.scope:
            names=json.loads(a.scope.read_text(encoding='utf-8-sig')); validate_files({name:'' for name in names}); write_json(root/'scope.json',names)
        if a.repo:
            branch='workflow/'+root.name
            result=subprocess.run([GIT,'-C',str(a.repo.resolve()),'worktree','add','-b',branch,str(s.source),'HEAD'],capture_output=True,text=True)
            if result.returncode: s.pause('worktree_setup_failed'); raise RuntimeError(result.stderr)
            s.save(s.state(),'worktree_created',repository=str(a.repo.resolve()),branch=branch,base='HEAD; excludes uncommitted changes')
        print(root); return
    if not a.run: p.error('--run required')
    s=Store(a.run)
    if a.action=='status': print(json.dumps(s.state(),ensure_ascii=False,indent=2))
    elif a.action=='import': s.propose(json.loads(a.file.read_text(encoding='utf-8')))
    elif a.action=='approve': s.approve()
    elif a.action=='pause': s.pause(a.reason)
    elif a.action=='report': print(s.report())
    elif a.action=='checkpoint': print(s.checkpoint())
if __name__=='__main__': main()
