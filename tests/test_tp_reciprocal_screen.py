"""Rounded-boundary branch screen tests; no solver calls."""
import unittest
from pathlib import Path
from run_tp_reciprocal import screen, authenticate_cached_file, sha
class ScreenTests(unittest.TestCase):
 def setUp(self):
  self.dir=Path(__file__).resolve().parent/'.build/reciprocal-screen-tests';self.dir.mkdir(parents=True,exist_ok=True)
  self.contract={'base_acceptance':{'earth_mass_g':5.9722e27},'branch_screen':{'relative_margin':1e-6}}
  self.diag={'gas_base_mass':4.99*5.9722e27,'gas_base_pressure':1e10,'gas_base_temperature':700,'gas_rows':[{'density_g_cm3':1.0}]}
  (self.dir/'model.txt').write_text('Index Radius P M Density T Phase\n0 1.5 1 4.99 3 700 Solid fixture\n1 1.5 1 4.99 1 700 Ideal Gas\n')
 def test_separated_density_passes_and_is_not_physical_claim(self):
  r=screen(self.dir,self.diag,self.contract);self.assertTrue(r['pass']);self.assertIn('not physical',r['meaning'])
 def test_inversion_and_rounded_near_equality_rejected(self):
  for value in [4.,3.,3.*(1-5e-7)]:
   with self.subTest(value=value):
    self.diag['gas_rows'][0]['density_g_cm3']=value
    with self.assertRaisesRegex(ValueError,'ambiguous'):screen(self.dir,self.diag,self.contract)
 def test_missing_boundary_not_silently_accepted(self):
  (self.dir/'model.txt').write_text('0 1.5 1 4.99 1 700 Ideal Gas\n')
  with self.assertRaisesRegex(ValueError,'solid-side'):screen(self.dir,self.diag,self.contract)
class CacheIdentityTests(unittest.TestCase):
 def test_committed_digest_detects_artifact_mutation(self):
  root=Path(__file__).resolve().parent/'.build/reciprocal-cache-test';p=root/'case/model.txt';p.parent.mkdir(parents=True,exist_ok=True);p.write_text('original boundary evidence\n')
  original={'sha256':{'data/case/model.txt':sha(p)}}
  self.assertEqual(authenticate_cached_file(root,'case/model.txt',original),sha(p))
  p.write_text('modified boundary evidence\n')
  with self.assertRaisesRegex(ValueError,'hash mismatch'):authenticate_cached_file(root,'case/model.txt',original)
 def test_cache_escape_rejected(self):
  root=Path(__file__).resolve().parent/'.build/reciprocal-cache-test';root.mkdir(parents=True,exist_ok=True)
  with self.assertRaisesRegex(ValueError,'escapes root'):authenticate_cached_file(root,'../outside.txt',{'sha256':{}})
if __name__=='__main__':unittest.main()
