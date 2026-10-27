"""Trusted acceptance checks for the bounded TP utility. No scientific solver."""
import importlib.util, math, pathlib, sys, unittest
source=pathlib.Path(sys.argv[1]); spec=importlib.util.spec_from_file_location('checked_profile',source/'profile.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
class Checks(unittest.TestCase):
 def test_bar_units(self): self.assertEqual(m.pressure_pa(1),100000); self.assertEqual(m.pressure_pa(0.01),1000)
 def test_invalid_pressure(self):
  for x in (0,-1,float('nan'),float('inf'),-float('inf')):
   with self.subTest(x=x),self.assertRaises(ValueError): m.pressure_pa(x)
 def test_valid_profile(self): self.assertIs(m.validate([0.1,1,10],[300,400,500]),True)
 def test_reverse_pressure(self):
  with self.assertRaises(ValueError): m.validate([1,0.1],[300,400])
 def test_duplicate_pressure(self):
  with self.assertRaises(ValueError): m.validate([1,1],[300,400])
 def test_nonfinite_temperature(self):
  for x in (float('nan'),float('inf'),-1,0):
   with self.subTest(x=x),self.assertRaises(ValueError): m.validate([0.1,1],[300,x])
 def test_nonfinite_profile_pressure(self):
  with self.assertRaises(ValueError): m.validate([0.1,float('nan')],[300,400])
 def test_lengths(self):
  for p,t in (([],[]),([1],[300]),([1,2],[300])):
   with self.subTest(p=p,t=t),self.assertRaises(ValueError): m.validate(p,t)
class OverflowChecks(unittest.TestCase):
 def test_unrepresentable_pressure(self):
  with self.assertRaises(ValueError): m.pressure_pa(10**400)
 def test_conversion_overflow(self):
  with self.assertRaises(ValueError): m.pressure_pa(1e308)
 def test_unrepresentable_level(self):
  with self.assertRaises(ValueError): m.validate([1,10**400],[300,400])
if __name__=='__main__': unittest.main(argv=[sys.argv[0]],verbosity=2)
