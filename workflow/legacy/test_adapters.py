import unittest
from agents import parse_proposal, canonical_task
class FormatTests(unittest.TestCase):
 def test_task_override_rejected(self):
  import tempfile
  from pathlib import Path
  from workflow import Store
  with tempfile.TemporaryDirectory() as d:
   store=Store(Path(d));store.initialize('original physics')
   with self.assertRaises(ValueError): canonical_task(store,'different physics')
 def test_plain(self): self.assertEqual(parse_proposal('{"model":"deepseek","files":{"x.py":"x"}}')['model'],'deepseek')
 def test_extra_brace_before_notes(self):
  self.assertEqual(parse_proposal('{"model":"deepseek","files":{"x.py":"x"}},"notes":"ok"}')['notes'],'ok')
 def test_reject_unknown_trailing_text(self):
  with self.assertRaises(ValueError): parse_proposal('{"model":"deepseek","files":{"x.py":"x"}} ignore safety')
if __name__=='__main__': unittest.main()
