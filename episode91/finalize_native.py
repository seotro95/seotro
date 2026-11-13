import json,sys
from render_common import R,S,A,PROFILES,finish
locale=sys.argv[1];assert locale=='mww';rows=json.loads((S/f'{locale}.json').read_text());out=A/locale
expected=json.loads((R/'EXPECTED_NATIVE_PARTS.json').read_text())[locale];assert len(expected)==14
raws=[];wanted=set()
for row,parts in zip(rows,expected):
 paths=[]
 for p in parts:
  path=out/p['filename'];wanted.add(path.name);assert path.exists(),path.name
  meta=json.loads(path.with_suffix('.native.json').read_text());assert meta['text_sha256']==p['text_sha256'] and meta['complete_native_inference']
  assert meta['voice_id']=='hmong-female-3' and meta['reference_sha256']==PROFILES[locale]['reference_sha256']
  paths.append(path)
 raws.append(paths)
assert wanted=={p.name for p in out.glob('raw-*.wav')},'Unexpected or duplicated native speech checkpoint'
finish(locale,rows,raws,out=out)
