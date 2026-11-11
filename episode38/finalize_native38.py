import json
from pathlib import Path
from render_episode import finish
R=Path(__file__).parent;rows=json.loads((R/'voice/scripts/mww.json').read_text());out=R/'voice/audio/mww';raws=[]
for i,row in enumerate(rows):
 paths=sorted(out.glob(f'raw-{i+1:03}-*.wav'));assert paths,(i+1)
 for path in paths:assert path.with_suffix('.native.json').exists()
 raws.append(paths)
finish('mww',rows,raws,out=out)
