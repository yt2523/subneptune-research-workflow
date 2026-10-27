import copy, json, os, tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import portable

class PortableAcceptance(unittest.TestCase):
    def plan(self):
        return {'tasks': [
            {'id':'a','priority':10,'depends_on':[],'scope':['demo.py'],'acceptance':'Write demo', 'tests':[[sys.executable,'-c','assert True']]},
            {'id':'b','priority':20,'depends_on':['a'],'scope':['demo.py'],'acceptance':'Improve demo','tests':[[sys.executable,'-c','assert True']]},
            {'id':'c','priority':1,'depends_on':['b'],'scope':['demo.py'],'acceptance':'Finish demo','tests':[[sys.executable,'-c','assert True']]}
        ]}
    def test_dependency_priority_and_complete(self):
        p=self.plan(); portable.validate_plan(p)
        self.assertEqual(portable.choose_next(p,{} )['id'],'a')
        self.assertEqual(portable.choose_next(p,{'a':'passed'})['id'],'b')
        self.assertIsNone(portable.choose_next(p,dict.fromkeys(['a','b','c'],'passed')))
    def test_plan_errors(self):
        for mutate in [lambda p:p['tasks'][0].update(depends_on=['c']),lambda p:p['tasks'][0].update(depends_on=['missing']),lambda p:p['tasks'][1].update(id='a'),lambda p:p['tasks'][0].update(scope=['../escape.py']),lambda p:p['tasks'][0].update(scope=['.env']),lambda p:p['tasks'][0].update(tests=['echo hello'])]:
            p=self.plan();mutate(p)
            with self.assertRaises(ValueError):portable.validate_plan(p)
    def test_external_json_and_dotenv_credentials(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'repo';root.mkdir();f=Path(d)/'key.json'
            f.write_text(json.dumps({'DEEPSEEK_API_KEY':'offline-test-secret'}))
            self.assertEqual(portable.load_credentials(f,root)['DEEPSEEK_API_KEY'],'offline-test-secret')
            f=Path(d)/'key.env';f.write_text('DEEPSEEK_API_KEY="offline-test-secret"\n')
            self.assertEqual(portable.load_credentials(f,root)['DEEPSEEK_API_KEY'],'offline-test-secret')
            f=root/'key.json';f.write_text('{}')
            with self.assertRaises(ValueError):portable.load_credentials(f,root)
    def test_redaction(self):
        self.assertNotIn('offline-test-secret',portable.redact('bad offline-test-secret',{'DEEPSEEK_API_KEY':'offline-test-secret'}))

if __name__=='__main__':unittest.main()
