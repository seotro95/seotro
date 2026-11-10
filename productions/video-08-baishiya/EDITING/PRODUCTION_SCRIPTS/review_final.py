import subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).parent;V=R/'delivery/BAISHIYA_08_EN_FINAL_22m20s_720p.mp4';D=R/'review';D.mkdir(exist_ok=True)
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16)
def page(name,times):
    image=Image.new('RGB',(384*4,240*((len(times)+3)//4)),(12,20,26));draw=ImageDraw.Draw(image)
    for k,t in enumerate(times):
        p=D/f'final_{str(t).replace(".","_")}.jpg'
        subprocess.run(['ffmpeg','-v','error','-threads','1','-ss',str(t),'-i',str(V),'-frames:v','1','-vf','scale=384:216','-threads','1','-y',str(p)],check=True)
        x=k%4*384;y=k//4*240;image.paste(Image.open(p),(x,y));draw.text((x+8,y+218),f'{int(t)//60:02d}:{t%60:04.1f}',font=font,fill='white')
    image.save(D/name,quality=91)
page('FINAL_OPENING.jpg',[1.5,3.5,5.5,8,11.5,13.8,16,18.5,21,23,25,28.5])
page('FINAL_OVERVIEW_1.jpg',[45,65,125,165,195,245,285,305,345,355,395,435,465,505,545,555])
page('FINAL_OVERVIEW_2.jpg',[575,605,655,685,705,745,785,795,815,855,895,905,945,965,995,1015])
page('FINAL_OVERVIEW_3.jpg',[1035,1055,1095,1115,1125,1145,1175,1205,1235,1245,1285,1295,1305,1325,1335,1339.7])
page('FINAL_CHAPTERS.jpg',[1.5,121.5,241.5,351.5,461.5,571.5,681.5,791.5,901.5,1011.5,1121.5,1231.5])
print('Finished movie review pages ready',flush=True)
