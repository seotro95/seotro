from pathlib import Path
import zipfile
R=Path(__file__).parent.resolve()
with zipfile.ZipFile(R/'VOICE_INPUTS.zip') as z:
 for x in z.infolist():
  p=(R/x.filename).resolve();assert p.is_relative_to(R) and not x.is_dir()
  assert x.filename.startswith(('voice/scripts/','documents/')) or x.filename=='DOCUMENT_DELIVERY_STATE.json'
  assert x.file_size<250000
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(x))
print('Verified episode38 narration inputs extracted')
