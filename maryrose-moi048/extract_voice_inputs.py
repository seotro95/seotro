import hashlib,zipfile
from pathlib import Path
R=Path(__file__).parent;p=R/'VOICE_INPUTS.zip'
assert hashlib.sha256(p.read_bytes()).hexdigest()==(R/'VOICE_INPUTS.sha256').read_text().strip()
with zipfile.ZipFile(p) as z:
 assert z.testzip() is None
 for item in z.infolist():
  assert not Path(item.filename).is_absolute() and '..' not in Path(item.filename).parts
  assert item.filename.startswith('voice/scripts/') or item.filename in ['VOICE_INPUT_QA.json','TRANSLATION_REVIEW.json','LOCALIZATION_SOURCE_CHAPTERS.json']
  out=R/item.filename;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(z.read(item))
print('MARYROSE_VOICE_INPUTS_VERIFIED')
