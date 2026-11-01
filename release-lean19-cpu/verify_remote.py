import json,subprocess
from pathlib import Path
expected=json.loads((Path(__file__).parent/'expected-assets.json').read_text())
raw=subprocess.check_output(['gh','api','repos/seotro95/seotro/releases/430556707'])
release=json.loads(raw);assets={a['name']:a for a in release['assets']}
assert release['tag_name']=='voice-studio-lean19-cpu1', 'Unexpected release tag'
for name,record in expected.items():
    a=assets[name]
    assert a['state']=='uploaded' and a['size']==record['size'],name
    assert a.get('digest')=='sha256:'+record['sha256'],('Server digest mismatch',name,a.get('digest'))
assert set(assets)==set(expected),'Unexpected release assets'
print('Every GitHub-hosted asset matches the reviewed payload sizes and SHA256 digests.')
