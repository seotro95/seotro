from pathlib import Path
import hashlib
import zipfile

R = Path(__file__).parent
path = R / 'VOICE_INPUTS.zip'
expected = (R / 'VOICE_INPUTS.sha256').read_text().strip()
assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
with zipfile.ZipFile(path) as archive:
    assert archive.testzip() is None
    for item in archive.infolist():
        parts = Path(item.filename).parts
        assert parts and not Path(item.filename).is_absolute() and '..' not in parts
        assert item.filename in {'VOICE_INPUT_QA.json','TRANSLATION_REVIEW.json','LOCALIZATION_SOURCE_CHAPTERS.json'} or item.filename.startswith('voice/scripts/')
        out = R / item.filename
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(archive.read(item))
print('VOICE_INPUTS_VERIFIED', flush=True)
