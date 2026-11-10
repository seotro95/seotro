import subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).parent;O=R/'delivery';V=O/'DENISOVA_06_EN_FINAL_21m_720p.mp4';D=R/'review';D.mkdir(exist_ok=True)
f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16)
def page(name,times,cols=4):
 rows=(len(times)+cols-1)//cols;im=Image.new('RGB',(384*cols,240*rows),(12,20,26));d=ImageDraw.Draw(im)
 for k,t in enumerate(times):
  p=D/f'final_{str(t).replace(".","_")}.jpg';subprocess.run(['ffmpeg','-v','error','-threads','1','-ss',str(t),'-i',str(V),'-frames:v','1','-vf','scale=384:216','-threads','1','-y',str(p)],check=True);x=k%cols*384;y=k//cols*240;im.paste(Image.open(p),(x,y));d.text((x+8,y+218),f'{int(t)//60:02d}:{t%60:04.1f}',font=f,fill='white')
 im.save(O/name,quality=91)
page('DENISOVA_06_REVIEW_OPENING.jpg',[1.5,3.5,5.5,8,11.5,13.8,16,18.5,21,23,25,28.5])
page('DENISOVA_06_REVIEW_OVERVIEW_1.jpg',[45,115,165,235,285,335,365,395,445,465,505,555,625,665,705,755])
page('DENISOVA_06_REVIEW_OVERVIEW_2.jpg',[775,805,845,865,885,935,975,1015,1065,1095,1115,1155,1175,1215,1245,1258])
print('Final opening and overview contact sheets ready',flush=True)
