"""Offline fault-injection trial: fixture proposals/reviews are NOT live LLM outputs."""
import json, subprocess, sys, datetime as dt, uuid
from pathlib import Path
from workflow import BASE, Store, fingerprint
CHECK='''import importlib.util, pathlib, unittest
p=pathlib.Path(__file__).parent/'source'/'profile.py'
s=importlib.util.spec_from_file_location('profile_fixture',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
class Checks(unittest.TestCase):
 def test_units(self): self.assertEqual(m.pressure_pa(1),100000)
 def test_monotonic(self):
  with self.assertRaises(ValueError): m.validate([1,0.1],[300,400])
 def test_temperature(self):
  with self.assertRaises(ValueError): m.validate([0.1,1],[300,-1])
 def test_positive_pressure(self):
  with self.assertRaises(ValueError): m.pressure_pa(0)
 def test_valid(self): self.assertTrue(m.validate([0.1,1],[300,400]))
if __name__=='__main__': unittest.main()
'''
FIXTURES=[
'''def pressure_pa(p): return p*1e6
def validate(p,t): return True
''',
'''def pressure_pa(p):
    if p<=0: raise ValueError('pressure must be positive')
    return p*1e5
def validate(p,t):
    if any(x<=0 for x in t): raise ValueError('temperature must be positive')
    return True
''',
'''import math
def pressure_pa(p):
    if not math.isfinite(p) or p<=0: raise ValueError('pressure must be positive and finite')
    return p*1e5
def validate(p,t):
    if len(p)!=len(t) or len(p)<2: raise ValueError('matching arrays, at least two levels')
    if any(not math.isfinite(x) or x<=0 for x in p+t): raise ValueError('positive finite P/T required')
    if any(a>=b for a,b in zip(p,p[1:])): raise ValueError('pressure must increase')
    return True
''']
def main():
 root=BASE/'runs'/('offline-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]); s=Store(root)
 s.initialize('OFFLINE INFRASTRUCTURE TRIAL. No live DeepSeek/GPT calls in these three fixture rounds.\nCheck bar-to-Pa units, pressure ordering, positive finite temperature. No planetary science inference.')
 (root/'check_fixture.py').write_text(CHECK,encoding='utf-8')
 outcomes=[]
 for i,code in enumerate(FIXTURES,1):
  s.propose({'model':'deepseek','origin':'OFFLINE_FIXTURE_NOT_LLM','files':{'profile.py':code}})
  r=subprocess.run([sys.executable,str(root/'check_fixture.py')],capture_output=True,text=True,timeout=20)
  passed=r.returncode==0; s.record_tests(passed,r.stdout+r.stderr)
  findings=[] if passed else ['Round 1: bar->Pa factor incorrect and invalid input accepted.' if i==1 else 'Round 2: descending pressures accepted.']
  s.review({'model':'gpt','origin':'OFFLINE_FIXTURE_NOT_LLM','approved':passed,'findings':findings},s.digest())
  sha=s.git('rev-parse','HEAD').strip(); outcomes.append({'round':i,'tests_pass':passed,'commit':sha})
  if i==2:
   s.pause('injected_rate_limit'); s=Store(root)
   assert s.state()['status']=='paused'
 s.report(); (root/'outcomes.json').write_text(json.dumps({'mode':'OFFLINE_FIXTURES','rounds':outcomes,'recovery_verified':True,'science_run_started':False},indent=2),encoding='utf-8')
 assert [x['tests_pass'] for x in outcomes]==[False,False,True]
 assert not s.can_run(), 'No human approval in offline trial'
 print(json.dumps({'run':str(root),'rounds':outcomes,'recovery_verified':True,'science_run_started':False},indent=2))
if __name__=='__main__': main()
