import json,os,subprocess
from pathlib import Path
expected=json.loads(Path(os.environ['EXPECTED_ASSETS']).read_text())
release=json.loads(subprocess.check_output(['gh','api','repos/seotro95/seotro/releases/431224144']))
assert release['tag_name']=='melo-viet-studio-1.2.0'
actual={a['name']:a for a in release['assets']}
assert set(actual)==set(expected),(set(actual),set(expected))
for name,record in expected.items():
    assert actual[name]['state']=='uploaded' and actual[name]['size']==record['size'],name
    assert actual[name]['digest']=='sha256:'+record['sha256'],name
print('Every hosted asset matches the verified build including the full model ZIP.')
