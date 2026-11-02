import hashlib,json,os,subprocess
from pathlib import Path
root=Path(os.environ['RELEASE_ASSETS'])
expected={p.name:{'size':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()} for p in root.iterdir() if p.is_file()}
release=json.loads(subprocess.check_output(['gh','api','repos/seotro95/seotro/releases/431143566']))
assert release['tag_name']=='melo-viet-studio-1.1.0'
actual={a['name']:a for a in release['assets']}
assert set(actual)==set(expected)
for name,record in expected.items():
    assert actual[name]['state']=='uploaded' and actual[name]['size']==record['size']
    assert actual[name]['digest']=='sha256:'+record['sha256'],name
print('Every hosted release asset matches its reviewed bytes.')
