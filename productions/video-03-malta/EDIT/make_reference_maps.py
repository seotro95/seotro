import hashlib,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'package/REFERENCES';OUT.mkdir(exist_ok=True)
land=json.loads(Path('/workspace/work/beringia/edit/ne_110m_land.geojson').read_text());lakes=json.loads((ROOT/'ne_110m_lakes.geojson').read_text())
def polys(data):
 for f in data['features']:
  g=f['geometry']
  for p in g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]:
   a=np.array(p[0],dtype=float)
   # Preserve each complete polygon ring. Draw a shifted whole-ring copy
   # instead of wrapping individual vertices and closing split ring pieces.
   yield a
   yield a+np.array([360.0,0.0])
for name,bounds in [('NORTH_PACIFIC_MODERN_BASE',(45,285,20,82)),('BAIKAL_MODERN_BASE',(95,120,45,62)),('YANA_MODERN_BASE',(95,180,48,80))]:
 fig,ax=plt.subplots(figsize=(19.2,10.8),dpi=100);fig.patch.set_facecolor('#103448');ax.set_facecolor('#103448')
 for p in polys(land):ax.add_patch(Polygon(p,facecolor='#8c9d83',edgecolor='#c1cdb9',linewidth=.75))
 for p in polys(lakes):ax.add_patch(Polygon(p,facecolor='#103448',edgecolor='#c1cdb9',linewidth=.6))
 ax.set_xlim(bounds[:2]);ax.set_ylim(bounds[2:]);ax.set_aspect('auto');ax.set_axis_off();fig.subplots_adjust(0,0,1,1)
 fig.savefig(OUT/(name+'.png'),dpi=100);plt.close(fig)
guide={'modern_base_data':'Natural Earth110m land and lakes, generalised modern geometry; not topographic elevation or a paleocoast reconstruction','land_source':'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_land.geojson','lakes_source':'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_lakes.geojson','license':'Natural Earth public domain','markers_are_generalised_orientation_only':True,'approximate_regions':{'Malta':[103.5,52.85],'Lake_Baikal':[108,53.5],'Yana':[135.4,70.7],'Ust_Kyahta':[106.5,50.35]},'nps_reference_url':'https://www.nps.gov/subjects/beringia/images/Beringia-Map_Bathymetry_web72_final_50_1.png?autorotate=false&maxwidth=1300','nps_source_page':'https://www.nps.gov/subjects/beringia/about.htm','nps_note':'Unmodified regional bathymetry map; preserve source credit. The NPS image labels a21,000BP shoreline/ice reconstruction and modern shore. Preserve those labels. It is orientation context, not a precise24,000BP reconstruction or the child’s route.'}
(OUT/'REFERENCE_GUIDE.json').write_text(json.dumps(guide,ensure_ascii=False,indent=2))
(OUT/'README.md').write_text('''# Bản đồ tham chiếu

Ba nềnPNG được vẽ từ NaturalEarth110m: bờ biển/hồ hiện đại tổng quát, không có số liệu địa hình cao độ hoặc bờ biển24ka. BảnNPSbathymetry giữ nguyên từ trang AboutBeringia; giữcredit nguồn, ảnh nguồn có nhãn khoảng21.000BP và bờ hiện đại: giữ nhãn nguồn, ghi rõ là bối cảnh định hướng, không phải bờ24.000năm chính xác hoặc tuyến đi của MA-1.

REFERENCE_GUIDE.json ghi URL và các vùng định hướng xấp xỉ để editor đặt nhãn; không dùng làm toạđộ khảo sát. MALTA là địa điểm Siberia phía tâyLakeBaikal. Ust-Kyahta ở vùng phía namlake, Yana xa vềphíabắc. Các dòng nối chỉ quan hệ di truyền phải ghi legend và nétđứt, không thành tuyến đi đã chứngminh của đứa trẻ.

Mọi promptMAP_REFERENCE nên dựng pan/zoom trực tiếp trên nền khoá sẵn nếu côngcụ tạo video không bảo toàn địa lý. Nền không chữ; editor thêm tên, mốc và chúthích nguồn. Không gán các vùng màu của sơđồ tổtiên thành biên giới dân tộc hoặc tỷlệ gene đo thật.
''')
print('Three modern reference maps and unchanged NPS bathymetry guide ready.')
