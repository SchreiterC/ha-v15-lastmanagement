#!/usr/bin/env python3
"""Static release checks (does not emulate Home Assistant)."""
from pathlib import Path
import json, sys, py_compile
base=Path(__file__).resolve().parents[1]
root=base/'custom_components'/'v15_lastmanagement'
manifest=json.loads((root/'manifest.json').read_text())
assert manifest['domain']=='v15_lastmanagement'
assert manifest['integration_type']=='hub'
assert manifest['config_flow'] is True
assert manifest['version'] == '0.3.5b4'
assert manifest['documentation'] == 'https://github.com/SchreiterC/ha-v15-lastmanagement'
assert list(manifest)[:2] == ['domain', 'name']
assert list(manifest)[2:] == sorted(list(manifest)[2:]), 'Hassfest manifest key ordering'
assert (root/'device.py').read_text().count('sw_version="0.3.5b4"') == 1
for key in ('name','version','documentation','issue_tracker','codeowners'):
    assert key in manifest, key
for p in root.glob('*.py'): py_compile.compile(str(p), doraise=True)
for p in [root/'strings.json',*list((root/'translations').glob('*.json')),base/'hacs.json']:
    json.loads(p.read_text())
try:
    from PIL import Image
except ImportError:
    print('Pillow not installed: image dimensions not checked')
else:
    for f,n in (('icon.png',256),('icon@2x.png',512),('logo.png',256),('logo@2x.png',512)):
        assert Image.open(root/'brand'/f).size == (n,n)
assert 'OWNER' not in (root/'manifest.json').read_text()
print('Static checks passed; HA runtime/HACS network checks not performed')
