from pathlib import Path
import hashlib,json,zipfile
HERE=Path(__file__).resolve().parent
record=json.loads((HERE/'expected-package.json').read_text())
package=HERE/'package.zip'
assert hashlib.sha256(package.read_bytes()).hexdigest()==record['sha256'], 'Installer ZIP SHA256 mismatch'
assert package.stat().st_size==record['size']
source=HERE.parent/'melo-viet-local'
with zipfile.ZipFile(package) as z:
    manifest=z.read('Melo-Viet-Cai-Rieng/MANIFEST.sha256').decode().splitlines()
    assert len(z.namelist())==len(manifest)+1
    for line in manifest:
        sha,name=line.split('  ',1)
        raw=z.read('Melo-Viet-Cai-Rieng/'+name)
        actual=(source/name).read_bytes()
        if raw!=actual and raw.replace(b'\r\n',b'\n')!=actual.replace(b'\r\n',b'\n'):
            print('::error title=Installer source mismatch::'+name,flush=True)
            raise SystemExit(1)
        assert hashlib.sha256(raw).hexdigest()==sha,name
print('Installer ZIP matches every reviewed source file.')
