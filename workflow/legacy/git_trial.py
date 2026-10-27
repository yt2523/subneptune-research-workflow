"""Local Git integration trial: no GitHub network or user repository changes."""
import json,subprocess,tempfile,sys
from pathlib import Path
from workflow import BASE,GIT,Store

def git(repo,*args):
 p=subprocess.run([GIT,'-C',str(repo),*args],capture_output=True,text=True,check=True);return p.stdout.strip()
with tempfile.TemporaryDirectory(prefix='workflow-git-',dir=r'D:\Codex\tmp') as d:
 repo=Path(d)/'original';repo.mkdir();git(repo,'init','-b','main');git(repo,'config','user.name','Workflow test');git(repo,'config','user.email','test@localhost')
 (repo/'README.md').write_text('baseline\n');git(repo,'add','README.md');git(repo,'commit','-m','baseline')
 (repo/'README.md').write_text('USER DIRTY CHANGE\n')
 p=subprocess.run([sys.executable,str(BASE/'workflow.py'),'new','--repo',str(repo)],capture_output=True,text=True,check=True)
 root=Path(p.stdout.strip());s=Store(root)
 assert (s.source/'README.md').read_text()=='baseline\n'
 assert git(s.source,'branch','--show-current').startswith('workflow/')
 s.propose({'model':'deepseek','origin':'OFFLINE_GIT_FIXTURE','files':{'README.md':'isolated edit\n'}})
 sha=git(s.source,'rev-parse','HEAD');assert (repo/'README.md').read_text()=='USER DIRTY CHANGE\n'
 git(s.source,'revert','--no-edit',sha)
 assert (s.source/'README.md').read_text()=='baseline\n'
 s.save(s.state(),'git_revert_verified',reverted_commit=sha)
 s.report();git(repo,'worktree','remove',str(s.source));
 result={'trial':'LOCAL_GIT_ONLY','run':str(root),'isolated_branch':True,'automatic_commit':True,'original_dirty_changes_preserved':True,'revert':True,'github_network_tested':False}
 (BASE/'logs/git-integration.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
