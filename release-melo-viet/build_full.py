import traceback
try:
 """Build an update with the additional native voices, preserving the user's 1.2.0 models."""
 import hashlib,json,os,shutil,zipfile,urllib.request
 from pathlib import Path
 HERE=Path(__file__).resolve().parent
 out=Path(os.environ['RELEASE_ASSETS']);out.mkdir(parents=True,exist_ok=True)
 root=Path(os.environ['MELO_VIET_ROOT']);small=json.loads((HERE/'expected-package.json').read_text())
 small_file=out/small['name'];shutil.copyfile(HERE/'package.zip',small_file);shutil.copyfile(HERE/'package.sha256',out/(small['name']+'.sha256'))
 full=out/'Melo-Viet-Studio-1.3.0-Them-Giong-Windows.zip';prefix='Melo-Viet-Cai-Rieng/'
 catalog=json.loads((HERE.parent/'melo-viet-local/fast_catalog.json').read_text())['models'];catalog=[m for m in catalog if not m.get('bundled',True)]
 multi=json.loads((HERE.parent/'melo-viet-local/multi_catalog.json').read_text())
 def digest(path):
  h=hashlib.sha256()
  with path.open('rb') as f:
   while block:=f.read(1024*1024):h.update(block)
  return h.hexdigest()
 manifest=[]
 with zipfile.ZipFile(full,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
  with zipfile.ZipFile(small_file) as source:
   for item in source.infolist():z.writestr(item,source.read(item.filename))
  records=[('models/piper/'+m['id'],m['files']) for m in catalog]+[('models/'+key,record['files']) for key,record in multi.items()]
  for relative,files in records:
   for name,sha in files.items():
    f=root/relative/name;assert digest(f)==sha,'Unverified file '+relative+'/'+name
    z.write(f,prefix+'voice-pack/'+relative+'/'+name);manifest.append(sha+'  '+relative+'/'+name+'\n')
  # Preserve the model's own license alongside the conversion project's MIT license.
  license_url='https://huggingface.co/supertone-oss-archive/supertonic-3/resolve/aafc6e32416a594460b32413efc49d7fe4ce6d46/LICENSE'
  with urllib.request.urlopen(license_url,timeout=60) as f:license_text=f.read()
  assert b'OpenRAIL' in license_text
  relative='models/supertonic3/LICENSE-MODEL';z.writestr(prefix+'voice-pack/'+relative,license_text);manifest.append(hashlib.sha256(license_text).hexdigest()+'  '+relative+'\n')
  z.writestr(prefix+'voice-pack/PACK.json',json.dumps({'piper':[m['id'] for m in catalog],'multi':list(multi)},indent=2))
  z.writestr(prefix+'voice-pack/MANIFEST.sha256',''.join(manifest))
  z.writestr(prefix+'voice-pack/DOC_TRUOC.txt','GOI CAP NHAT CHO BAN 1.2.0: them giong, giu nguyen model/outputs cu. Giai nen, dong tool, chay CAP_NHAT.bat. Cai thu vien can Internet. Khong can cai lai Ubuntu.\n')
 assert full.stat().st_size<2*1024**3,'GitHub single-asset limit'
 (out/(full.name+'.sha256')).write_text(digest(full)+'  '+full.name+'\n')
 print('Additional-voice update:',full.stat().st_size,'bytes;',len(catalog),'Piper models;',len(multi),'shared native models',flush=True)
except Exception:
 print('::error title=Voice update packaging::'+traceback.format_exc()[-6000:].replace('%','%25').replace('\n','%0A').replace('\r','%0D'),flush=True)
 raise
