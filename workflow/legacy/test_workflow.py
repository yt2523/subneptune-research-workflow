import json, tempfile, unittest
from pathlib import Path
from workflow import Store, fingerprint, validate_files
class WorkflowTests(unittest.TestCase):
    def test_gate_and_edit_invalidation(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)); s.initialize('test')
            s.propose({'model':'deepseek','files':{'profile.py':'x=1\n'}})
            s.record_tests(True, 'pass')
            s.review({'model':'gpt','approved':True,'findings':[]}, s.digest())
            self.assertFalse(s.can_run())
            s.approve(); self.assertTrue(s.can_run())
            (s.source/'profile.py').write_text('x=2\n')
            self.assertFalse(s.can_run())
    def test_reject_and_fix_rounds(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)); s.initialize('test')
            s.propose({'model':'deepseek','files':{'profile.py':'x=-1\n'}})
            s.record_tests(False,'negative temperature')
            s.review({'model':'gpt','approved':False,'findings':['negative temperature']},s.digest())
            self.assertEqual(s.state()['status'],'changes_requested')
            s.propose({'model':'deepseek','files':{'profile.py':'x=1\n'}})
            s.record_tests(True,'pass')
            s.review({'model':'gpt','approved':True,'findings':[]},s.digest())
            s.approve(); self.assertTrue(s.can_run())
            self.assertEqual(s.state()['iteration'],2)
    def test_paths_and_models(self):
        for name in ('../escape.py','/abs.py','C:/x.py','a\\b.py','.git/config'):
            with self.assertRaises(ValueError): validate_files({name:'bad'})
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)); s.initialize('test')
            with self.assertRaises(ValueError): s.propose({'model':'gpt','files':{'x.py':'x'}})
    def test_restart_and_stale_review(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)); s.initialize('test'); s.pause('rate_limit')
            resumed=Store(Path(d)); self.assertEqual(resumed.state()['status'],'paused')
            resumed.propose({'model':'deepseek','files':{'x.py':'1'}})
            with self.assertRaises(ValueError): resumed.review({'model':'gpt','approved':True,'findings':[]},'old')
    def test_no_approval_after_failed_tests(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)); s.initialize('test')
            s.propose({'model':'deepseek','files':{'x.py':'1'}}); s.record_tests(False,'fail')
            s.review({'model':'gpt','approved':True,'findings':[]},s.digest())
            with self.assertRaises(ValueError): s.approve()
    def test_task_change_invalidates_approval(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)); s.initialize('original task')
            s.propose({'model':'deepseek','files':{'x.py':'x=1'}})
            s.record_tests(True,'pass'); s.review({'model':'gpt','approved':True,'findings':[]},s.digest()); s.approve()
            (s.root/'TASK.md').write_text('different physics assumptions')
            self.assertFalse(s.can_run())
    def test_fingerprint_framing(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'a.txt').write_bytes(b'x\0b.txt\0y'); h=fingerprint(p)
            (p/'a.txt').write_bytes(b'x'); (p/'b.txt').write_bytes(b'y')
            self.assertNotEqual(h,fingerprint(p))
    def test_crash_during_pause_fails_closed(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d));s.initialize('task');s.propose({'model':'deepseek','files':{'x.py':'x=1'}})
            s.record_tests(True,'pass');s.review({'model':'gpt','approved':True,'findings':[]},s.digest());s.approve()
            with patch('workflow.os.replace',side_effect=OSError('injected crash')):
                with self.assertRaises(OSError): s.pause('quota')
            self.assertFalse(Store(Path(d)).can_run())
    def test_scope_and_commit_digest(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d));s.initialize('task');(s.root/'scope.json').write_text('["x.py"]')
            with self.assertRaises(ValueError): s.propose({'model':'deepseek','files':{'other.py':'x=1'}})
            s.propose({'model':'deepseek','files':{'x.py':'x=1'}})
            self.assertEqual(s.state()['code_hash'],s.digest())
    def test_audit(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)); s.initialize('test'); s.pause('quota')
            rows=[json.loads(x) for x in (s.root/'audit.jsonl').read_text().splitlines()]
            self.assertEqual([x['event'] for x in rows],['initialized','paused'])
if __name__=='__main__': unittest.main()
