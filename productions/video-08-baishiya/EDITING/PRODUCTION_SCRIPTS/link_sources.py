"""Map the user's original downloads into the reproducible local edit project.

Usage: python link_sources.py /path/to/folder/containing/original/mp4/files
Files are copied, never moved. Existing correctly hashed files are retained.
"""
import hashlib,json,shutil,sys
from pathlib import Path
R=Path(__file__).parent
folder=Path(sys.argv[1]).resolve()
assert folder.is_dir()
rows=json.loads((R/'SOURCE_MANIFEST.json').read_text())['clips']
needed={s['label'] for c in json.loads((R/'EDIT_PLAN.json').read_text()) for s in c['segments'] if not s['label'].startswith('@')}
(R/'raw').mkdir(exist_ok=True)
for row in rows:
    if row['label'] not in needed: continue
    target=R/'raw'/f"{row['label']}.mp4"
    if target.exists():
        assert hashlib.file_digest(target.open('rb'),'sha256').hexdigest()==row['sha256']
        continue
    matches=list(folder.rglob(row['source_name']))
    source=next((p for p in matches if hashlib.file_digest(p.open('rb'),'sha256').hexdigest()==row['sha256']),None)
    if source is None: raise FileNotFoundError(f"Missing verified original: {row['source_name']}")
    shutil.copyfile(source,target)
    print(row['label'],flush=True)
print('Sources copied and hash-verified. Originals unchanged.')
