import hashlib,zipfile
from pathlib import Path
R=Path(__file__).parent;p=R/'CONTENT_INPUTS.zip'
assert hashlib.sha256(p.read_bytes()).hexdigest()==(R/'CONTENT_INPUTS.sha256').read_text().strip()
with zipfile.ZipFile(p) as z:
    assert z.testzip() is None
    for x in z.infolist():
        assert not Path(x.filename).is_absolute() and '..' not in Path(x.filename).parts
        out=R/x.filename;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(z.read(x))
print('ROMAN_CONTENT_INPUTS_VERIFIED')
