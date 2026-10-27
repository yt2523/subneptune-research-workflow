import copy, json, os, sys, tempfile, time, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import portable

class ReleaseSafety(unittest.TestCase):
 def config(self,d):
  root=Path(d)/'project';root.mkdir(exist_ok=True);(root/'demo.py').write_text('value=0\n')
  return {'project_root':str(root),'run_dir':str(Path(d)/'run'),'context':[], 'coder':{'model':'deepseek-v4-pro','base_url':'https://api.deepseek.com'},'reviewer':{'provider':'api','model':'test-review-model','base_url':'https://example.invalid/v1'},'limits':{'max_model_calls':8,'max_seconds':2,'max_fix_rounds':5,'call_timeout':1},'plan':{'tasks':[{'id':'a','priority':1,'depends_on':[],'scope':['demo.py'],'acceptance':'value=2','tests':[['{python}','-c','import demo; assert demo.value==2']],'offline_files':{'demo.py':'value=2\n'}}]}}
 def runner(self,c,d,offline=True):return portable.Runner(c,str(Path(d)/'config.json'),{},offline,True)
 def test_completed_resume_does_not_restage(self):
  with tempfile.TemporaryDirectory() as d:
   c=self.config(d);r=self.runner(c,d);r.run();p=Path(c['run_dir'])/'source/demo.py';before=p.read_bytes();r=self.runner(c,d);r.run();self.assertEqual(p.read_bytes(),before);self.assertEqual(p.read_text(),'value=2\n')
 def test_full_contract_changes_reject_resume(self):
  for mutate in [lambda c:c['coder'].update(model='different'),lambda c:c['limits'].update(max_model_calls=999),lambda c:c.update(project_root=str(Path(c['project_root']).parent))]:
   with self.subTest(mutate=mutate),tempfile.TemporaryDirectory() as d:
    c=self.config(d);self.runner(c,d).run();mutate(c)
    with self.assertRaises((portable._Pause,ValueError,RuntimeError)):self.runner(c,d).run()
 def test_windows_and_nested_hidden_scopes_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   for path in ['C:/outside.py','src/.env','src/.hidden/x.py','src/../out.py','a\\b.py']:
    c=self.config(d);c['plan']['tasks'][0]['scope']=[path]
    with self.subTest(path=path),self.assertRaises(ValueError):portable.validate_plan(c['plan'])
 def test_offline_failure_executes_once(self):
  with tempfile.TemporaryDirectory() as d:
   c=self.config(d);c['plan']['tasks'][0]['tests']=[['{python}','-c',"from pathlib import Path;p=Path('attempts.log');p.write_text((p.read_text() if p.exists() else '')+'x');raise SystemExit(1)"]]
   try:self.runner(c,d).run()
   except portable._Pause:pass
   p=Path(c['run_dir'])/'source/attempts.log';self.assertEqual(p.read_text(),'x')
 def test_offline_cli_ignores_malformed_credentials(self):
  import subprocess
  with tempfile.TemporaryDirectory() as d:
   c=self.config(d);p=Path(d)/'config.json';p.write_text(json.dumps(c));key=Path(d)/'keys.json';key.write_text('{bad')
   result=subprocess.run([sys.executable,'-B',portable.__file__,'run','--offline','--config',str(p),'--credentials',str(key)],capture_output=True,text=True,timeout=8)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
 def test_lock_does_not_evict_live_owner_by_age(self):
  with tempfile.TemporaryDirectory() as d:
   c=self.config(d);a=self.runner(c,d);b=self.runner(c,d);a._acquire_lock()
   try:
    os.utime(a.lock_path,(time.time()-120,time.time()-120))
    with self.assertRaises((portable._Pause,RuntimeError,ValueError,OSError)):b._acquire_lock()
   finally:a._release_lock()
 def test_model_call_budget_reserves_reviewer(self):
  with tempfile.TemporaryDirectory() as d:
   c=self.config(d);c['limits']['max_model_calls']=1;c['plan']['tasks'][0]['tests']=[['{python}','-c','assert True']]
   r=portable.Runner(c,str(Path(d)/'config.json'),{'DEEPSEEK_API_KEY':'dummy-coder','OPENAI_API_KEY':'dummy-review'},False,True)
   response={'choices':[{'message':{'content':json.dumps({'files':{'demo.py':'value=2\n'}})}}],'usage':{'prompt_tokens':1,'completion_tokens':1}}
   with patch.object(r,'_post_api',return_value=response) as req:
    try:r.run()
    except portable._Pause:pass
    self.assertEqual(req.call_count,1);self.assertEqual(r.state['model_calls'],1);self.assertNotEqual(r.state.get('statuses',{}).get('a'),'passed')

 def test_source_and_destination_symlinks_preserve_sentinel(self):
  for where in ['source','destination']:
   with self.subTest(where=where),tempfile.TemporaryDirectory() as d:
    c=self.config(d);sentinel=Path(d)/'outside.py';sentinel.write_text('sentinel')
    if where=='source':
     link=Path(c['project_root'])/'demo.py';link.unlink()
    else:
     link=Path(c['run_dir'])/'source/demo.py';link.parent.mkdir(parents=True)
    try:link.symlink_to(sentinel)
    except (OSError,NotImplementedError):self.skipTest('symlink privilege unavailable')
    with self.assertRaises((portable._Pause,ValueError,RuntimeError)):self.runner(c,d).run()
    self.assertEqual(sentinel.read_text(),'sentinel')

if __name__=='__main__':unittest.main()
