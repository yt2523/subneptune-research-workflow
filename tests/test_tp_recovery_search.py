"""Analytic/fault tests only: no planet or provider calls."""
import math, unittest
from tp_recovery_search import recover, RecoveryBudgetExhausted

def point(f,r): return {'gas_fraction':f,'radius_cm':r}
class RecoveryTests(unittest.TestCase):
 def settings(self,**kw):return dict(radius_rtol=1e-10,fraction_width=1e-7,max_new_evaluations=50,xtol=1e-10,rtol=1e-12,maxiter=12,**kw)
 def test_known_root_cached_endpoints_and_signed_bounds(self):
  # Normalize the analytic oracle to avoid a few-ULP plateau from20+log(f).
  # Exact signed enclosure remains required; no scientific threshold is changed.
  lo,hi=.0005,.01;truth=.0027;target=1.;seen=[]
  def evaluate(f):
   self.assertNotIn(f,[lo,hi]);seen.append(f);return point(f,f/truth)
  r=recover(evaluate,point(lo,lo/truth),point(hi,hi/truth),target,**self.settings())
  self.assertTrue(r['converged']);self.assertLessEqual(abs(r['candidate']['gas_fraction']-truth),1e-10)
  self.assertLessEqual(r['lower']['gas_fraction'],truth);self.assertGreaterEqual(r['upper']['gas_fraction'],truth)
  self.assertLessEqual(r['lower']['residual']*r['upper']['residual'],0);self.assertLessEqual(r['fraction_width'],1e-7)
  self.assertEqual(r['new_evaluations'],len(seen));self.assertFalse(r['unique_root_proven'])
 def test_nonbracket_may_contain_two_roots_no_evaluations(self):
  fn=lambda f:2+1e4*(f-.004)*(f-.008);seen=[]
  with self.assertRaisesRegex(ValueError,'do not bracket'):
   recover(lambda f:seen.append(f),point(.002,fn(.002)),point(.01,fn(.01)),2,**self.settings())
  self.assertEqual(seen,[])
 def test_exact_endpoint_does_not_fake_zero_width(self):
  seen=[];fn=lambda f:1+f;lo=.002;hi=.006
  def evaluate(f):seen.append(f);return point(f,fn(f))
  r=recover(evaluate,point(lo,fn(lo)),point(hi,fn(hi)),fn(lo),radius_rtol=1e-12,fraction_width=5e-5,max_new_evaluations=30,xtol=1e-10,rtol=1e-12,maxiter=12)
  self.assertTrue(r['converged']);self.assertGreater(len(seen),0);self.assertGreater(r['fraction_width'],0);self.assertLessEqual(r['fraction_width'],5e-5)
 def test_budget_is_hard_and_no_extra_callback(self):
  seen=[]
  def evaluate(f):seen.append(f);return point(f,1+f*f)
  with self.assertRaises(RecoveryBudgetExhausted):
   recover(evaluate,point(.001,1.000001),point(.02,1.0004),1.00005,radius_rtol=1e-16,fraction_width=1e-15,max_new_evaluations=1,xtol=1e-12,rtol=1e-12,maxiter=12)
  self.assertEqual(len(seen),1)
 def test_model_failure_is_not_brent_cleanup(self):
  def bad(f):raise RuntimeError('sentinel model failed')
  with self.assertRaisesRegex(RuntimeError,'sentinel model failed'):
   recover(bad,point(.001,1),point(.01,3),2,**self.settings())
 def test_nonfinite_radius_is_rejected(self):
  with self.assertRaisesRegex(ValueError,'finite'):
   recover(lambda f:point(f,float('nan')),point(.001,1),point(.01,3),2,**self.settings())
 def test_returned_fraction_must_match_request(self):
  with self.assertRaisesRegex(ValueError,'fraction'):
   recover(lambda f:point(.8,2),point(.001,1),point(.01,3),2,**self.settings())
if __name__=='__main__':unittest.main()
