"""Verify archived bytes only; never launch a solver."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parent
index=json.loads((root/'INDEX_SHA256.json').read_text())
for name,expected in index['sha256'].items():
 p=(root/name).resolve()
 assert p.is_relative_to(root) and p.is_file(),name
 assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,name
state=json.loads((root/'data/results.json').read_text())
assert state['status']=='FAILED' and state['full_planet_invocations']==8
print('Archive byte hashes PASS:',len(index['sha256']),'files; scientific run remains FAILED,8/20 fits,no inferred composition')
