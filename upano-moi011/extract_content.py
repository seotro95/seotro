from pathlib import Path
import hashlib
import zipfile

R = Path(__file__).parent
archive = R / 'CONTENT_INPUTS.zip'
expected = (R / 'CONTENT_INPUTS.sha256').read_text().strip()
assert hashlib.sha256(archive.read_bytes()).hexdigest() == expected
allowed = {'CUES_DRAFT.tsv', 'VISUALS_DRAFT.tsv', 'NGUON_KIEM_CHUNG.md',
           'PHAN_TICH_VA_KE_HOACH_DUNG.md', '5_TIEU_DE_VA_THUMBNAIL.txt',
           'PRODUCTION_STEPS_APPLIED.md'}
with zipfile.ZipFile(archive) as z:
    assert set(z.namelist()) == allowed
    assert z.testzip() is None
    for name in z.namelist():
        (R / name).write_bytes(z.read(name))
print('CONTENT_INPUTS_VERIFIED', flush=True)
