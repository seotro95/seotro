import hashlib,json,os
from pathlib import Path
root=Path(os.environ['RELEASE_ASSETS'])
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while block:=f.read(1024*1024):h.update(block)
    return h.hexdigest()
records={p.name:{'size':p.stat().st_size,'sha256':digest(p)} for p in root.iterdir() if p.is_file()}
Path(os.environ['RUNNER_TEMP'],'RELEASE-ASSETS.json').write_text(json.dumps(records,indent=2))
print('Prepared release manifest for',len(records),'files.')
