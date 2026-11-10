import subprocess
from pathlib import Path
from PIL import Image,ImageDraw
R=Path(__file__).parent;V=R/'delivery/YANA_04_EN_FINAL_23m_720p.mp4';D=R/'review';D.mkdir(exist_ok=True)
times=[33,125,245,365,485,605,725,835,945,1055,1165,1275,135,275,395,535,675,775,875,995,1115,1215,1315,1377]
for page in range(2):
 im=Image.new('RGB',(1536,720),(12,20,26));d=ImageDraw.Draw(im)
 for n,t in enumerate(times[page*12:page*12+12]):
  p=D/f'final_{t}.jpg';subprocess.run(['ffmpeg','-v','error','-threads','1','-ss',str(t),'-i',str(V),'-frames:v','1','-vf','scale=384:216','-threads','1','-y',str(p)],check=True)
  x=n%4*384;y=n//4*240;im.paste(Image.open(p),(x,y));d.text((x+8,y+219),f'{t//60:02d}:{t%60:02d}',fill='white')
 im.save(D/f'FINAL_CONTACT_{page+1}.jpg')
print('Final review contacts ready',flush=True)
