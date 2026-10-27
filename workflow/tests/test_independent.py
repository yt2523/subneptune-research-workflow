import json, tempfile, unittest, sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import portable

class IndependentGuards(unittest.TestCase):
 def task(self):return {'id':'a','priority':1,'depends_on':[],'scope':['demo.py'],'acceptance':'a','tests':[['{python}','-c','assert True']]}
 def runner(self,d):
  p=Path(d)/'project';p.mkdir(exist_ok=True)
  return portable.Runner({'project_root':str(p),'run_dir':str(Path(d)/'run'),'plan':{'tasks':[self.task()]},'coder':{'model':'deepseek-v4-pro'},'reviewer':{'provider':'codex'},'limits':{}},str(Path(d)/'c.json'),{},True,True)
 def test_failed_task_stays_selectable(self):
  self.assertEqual(portable.choose_next({'tasks':[self.task()]},{'a':'failed'})['id'],'a')
 def test_approval_must_be_boolean(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.runner(d)
   for v in ['false',1,None]:
    with self.assertRaises((ValueError,portable._Pause)):r._parse_reviewer_json(json.dumps({'approved':v,'findings':[]}))
 def test_uppercase_protected_acceptance(self):
  t=self.task();t['scope']=['ACCEPTANCE.md']
  with self.assertRaises(ValueError):portable.validate_plan({'tasks':[t]})
 def test_doctor_offline_needs_no_codex(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.runner(d)
   with patch('shutil.which',return_value=None):self.assertEqual(r.doctor(),[])
 def test_context_can_stage_protected_test(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.runner(d);(r.project_root/'test_fixed.py').write_text('assert True')
   r.context_files=['test_fixed.py'];r._stage_source()
   self.assertTrue((r.source_dir/'test_fixed.py').exists())

if __name__=='__main__':unittest.main()
