import hashlib,json,zipfile
from pathlib import Path
R=Path(__file__).parent.resolve();p=R/'VOICE_INPUTS.zip';expected=(R/'VOICE_INPUTS.sha256').read_text().strip();assert hashlib.file_digest(p.open('rb'),'sha256').hexdigest()==expected
with zipfile.ZipFile(p) as z:
 assert z.testzip() is None
 for x in z.infolist():
  dest=(R/x.filename).resolve();assert dest.is_relative_to(R) and not x.is_dir() and x.file_size<250000
  assert x.filename.startswith(('voice/scripts/','documents/')) or x.filename in ['DOCUMENT_DELIVERY_STATE.json','EXPECTED_NATIVE_PARTS.json','VOICE_INPUT_QA.json']
  dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(x))
print('Episode45 narration inputs extracted and SHA256 verified',flush=True)
