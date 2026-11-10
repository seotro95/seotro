import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).parent;O=R/'package/REFERENCES';O.mkdir(parents=True,exist_ok=True)
land=json.load(open('/workspace/work/beringia/edit/ne_110m_land.geojson'));lakes=json.load(open('/workspace/work/malta/ne_110m_lakes.geojson'))
def polys(data):
 for f in data['features']:
  g=f['geometry']
  for poly in g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]:
   a=np.array(poly[0],dtype=float)
   for delta in [-360,0,360]:yield a+np.array([delta,0.])
boundslist=[('ALTAI_MODERN_BASE',(60,115,30,65)),('ASIA_MODERN_BASE',(45,155,5,65)),('ASIA_OCEANIA_MODERN_BASE',(45,180,-20,70)),('TIBETAN_PLATEAU_MODERN_BASE',(65,115,10,45))]
for name,bounds in boundslist:
 fig,ax=plt.subplots(figsize=(12.8,7.2),dpi=100);fig.patch.set_facecolor('#103448');ax.set_facecolor('#103448')
 for p in polys(land):ax.add_patch(Polygon(p,facecolor='#8c9d83',edgecolor='#c1cdb9',linewidth=.65))
 for p in polys(lakes):ax.add_patch(Polygon(p,facecolor='#103448',edgecolor='#c1cdb9',linewidth=.5))
 ax.set_xlim(bounds[:2]);ax.set_ylim(bounds[2:]);ax.set_aspect('auto');ax.set_axis_off();fig.subplots_adjust(0,0,1,1);fig.savefig(O/(name+'.png'));plt.close(fig)
for name in ['COMPARISON_BLOCKS','ABSTRACT_PARENTAGE','RESEARCH_AND_ANCIENT_TIME']:
 im=Image.new('RGB',(1280,720),'#0b1d28');d=ImageDraw.Draw(im)
 if name=='COMPARISON_BLOCKS':
  for row in range(3):
   for k in range(16):d.rectangle((120+k*65,180+row*135,167+k*65,226+row*135),fill=['#72bfc5','#e1b374','#a9b2b3'][(k//3+(row if k%5==0 else 0))%3])
 elif name=='ABSTRACT_PARENTAGE':
  for x,y,col in [(365,205,'#72bfc5'),(915,205,'#e1b374')]:d.rounded_rectangle((x-130,y-45,x+130,y+45),radius=7,fill=col)
  d.line((365,265,640,420),fill='#72bfc5',width=5);d.line((915,265,640,420),fill='#e1b374',width=5)
  for k in range(10):d.rectangle((350+k*60,461,395+k*60,508),fill='#72bfc5' if k%2 else '#e1b374')
 else:
  d.line((130,235,1150,235),fill='#a9b2b3',width=3)
  for x in [260,550,940]:d.ellipse((x-10,225,x+10,245),fill='#e1b374')
  for x,w in [(190,220),(615,310),(1040,110)]:d.rounded_rectangle((x,440,x+w,473),radius=4,fill='#72bfc5')
 im.save(O/(name+'.png'))
guide={'modern_geometry':'Natural Earth1:110m land and lakes, public domain; modern general geographic orientation, not elevation, dated palaeoshore or surveyed site coordinates','rendering':'Whole polygon rings and whole-ring longitude shifts; never modulo individual vertices and close cut fragments','map_bounds':dict(boundslist),'approximate_regional_markers':{'Denisova_Altai_region':[84.7,51.4],'Baishiya_Gansu_region':[102.6,35.5],'Harbin_region':[126.6,45.8],'Taiwan_Strait_region':[120,23.5],'Bianfu':'Use a broad Yunnan regional label, not an unverified exact site coordinate','Xujiayao':'Use a broad Nihewan Basin regional label, not an exact surveyed coordinate'},'diagram_policy':'The three abstract plates are conceptual teaching diagrams, no actual genetic data, exact genealogy, measured time scale or human figures. Add all verified text in editing.','no_children_in_visuals':True}
(O/'REFERENCE_GUIDE.json').write_text(json.dumps(guide,ensure_ascii=False,indent=2))
(O/'README.md').write_text('''# Nền tham chiếu — Denisova

Bốn bản đồ dùng dữ liệu Natural Earth1:110m công cộng, giữ nguyên vòng đa giác. Chỉ định hướng địa lý hiện đại tổng quát: không phải bản đồ cao độ, bờ biển cổ hoặc tuyến di cư đã biết. Toạ độ vùng trongGUIDE là gần đúng; Bianfu/Xujiayao chỉ gắn nhãn vùng nếu chưa có toạ độ khảo sát đã đối chiếu.

Ba sơ đồ trừu tượng không có hình người. Chúng không phải dữ liệu gene thật, tỷ lệ tổ tiên, phả hệ cá nhân hoặc thang niên đại đã đo. Thêm chữ và giải thích khi edit. Nếu công cụ tạo video không giữ được nền, dùng PNG này pan/zoom trực tiếp trong editor; không chấp nhận bản đồ AI làm biến dạng địa lý.

Không tạo hình trẻ em ở bất kỳ nơi nào. Không tái hiện chủ mẫu Denisova3/Denisova11. Nền không chứa người, cờ quốc gia hoặc biên giới dân tộc.
''')
print('Four modern maps and three non-human schematic plates ready')
