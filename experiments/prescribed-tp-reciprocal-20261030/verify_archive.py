"""Byte-integrity check only: no solver/API calls."""
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parent
index=json.loads((root/'INDEX_SHA256.json').read_text())
for n,h in index['sha256'].items():
 p=(root/n).resolve();assert p.is_relative_to(root) and p.is_file(),n
 assert hashlib.sha256(p.read_bytes()).hexdigest()==h,n
s=json.loads((root/'data/results.json').read_text());assert s['status']=='PASS_LOCAL_ENGINEERING_RECOVERY' and s['new_full_fits']==6 and s['cumulative_full_fits']==14
print('Archive byte hashes PASS; conditional local recovery, original direction remainsFAILED; no models run')
