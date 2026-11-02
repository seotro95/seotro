import hashlib,urllib.request,traceback
try:
 url='https://huggingface.co/supertone-oss-archive/supertonic-3/resolve/aafc6e32416a594460b32413efc49d7fe4ce6d46/LICENSE'
 with urllib.request.urlopen(url,timeout=60) as f:text=f.read()
 assert b'OpenRAIL' in text
 print('::notice title=Model license verified::'+str(len(text))+' bytes; SHA256 '+hashlib.sha256(text).hexdigest(),flush=True)
except Exception:
 print('::error title=Model license packaging::'+traceback.format_exc().replace('\n','%0A'),flush=True);raise
