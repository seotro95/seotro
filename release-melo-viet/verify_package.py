from pathlib import Path
import hashlib,json,zipfile
HERE=Path(__file__).resolve().parent
record=json.loads((HERE/'expected-package.json').read_text())
package=HERE/'package.zip'
with package.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==record['sha256']
assert package.stat().st_size==record['size']
source=HERE.parent/'melo-viet-local'
with zipfile.ZipFile(package) as z:
    manifest=z.read('Melo-Viet-Cai-Rieng/MANIFEST.sha256').decode().splitlines()
    assert len(z.namelist())==len(manifest)+1
    for line in manifest:
        sha,name=line.split('  ',1)
        raw=z.read('Melo-Viet-Cai-Rieng/'+name)
        assert raw==(source/name).read_bytes(),name
        assert hashlib.sha256(raw).hexdigest()==sha,name
print('Installer ZIP matches every reviewed source file.')
