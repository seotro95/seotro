import hashlib,json,urllib.request
from pathlib import Path
from .common import data_dir,save_json

TRANSITIONS={'cut':'Cắt thẳng','dissolve':'Hòa hình','fade':'Mờ chuyển','wipeleft':'Lau trái','wiperight':'Lau phải','slideleft':'Trượt trái','slideright':'Trượt phải','smoothleft':'Trượt mượt trái','smoothright':'Trượt mượt phải','circleopen':'Mở tròn','circleclose':'Đóng tròn','fadeblack':'Qua nền đen','fadewhite':'Qua nền trắng','pixelize':'Điểm ảnh','radial':'Tỏa tròn','diagtl':'Chéo góc','hlslice':'Lát ngang','vertopen':'Mở dọc','squeezeh':'Ép ngang'}
TRANSITION_NAMES=TRANSITIONS
FILTERS={'none':'','warm':'colorbalance=rs=.05:bs=-.035','cool':'colorbalance=bs=.05:rs=-.025','grayscale':'hue=s=0','vignette':'vignette=PI/5','sharpen':'unsharp=5:5:.6:3:3:0','cinema':'eq=contrast=1.06:saturation=.88','bright':'eq=brightness=.035','sepia':'colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131','soft':'gblur=sigma=.65','contrast':'eq=contrast=1.12','faded':'eq=contrast=.9:brightness=.025:saturation=.85','grain':'noise=alls=4:allf=t','denoise':'hqdn3d=2:1.5:3:2','mirror':'hflip','negative':'negate'}
MOTIONS={'zoom_in','zoom_out','pan_left','pan_right'}
NAMES={'none':'Nguyên bản','warm':'Ấm','cool':'Lạnh','grayscale':'Đen trắng','vignette':'Tối góc','sharpen':'Nét nhẹ','cinema':'Điện ảnh','bright':'Sáng hơn','zoom_in':'Phóng vào','zoom_out':'Thu ra','pan_left':'Lướt trái','pan_right':'Lướt phải','sepia':'Nâu cổ','soft':'Mềm','contrast':'Tương phản','faded':'Phai màu','grain':'Hạt phim','denoise':'Giảm nhiễu','mirror':'Lật ngang','negative':'Âm bản'}
BASE_EFFECTS=['none','warm','cool','grayscale','vignette','sharpen','cinema','zoom_in','zoom_out','pan_left','pan_right']
PACK_URL='https://raw.githubusercontent.com/seotro95/seotro/codex/beringia-video-01/tools/autodoc-studio/effect_packs/manifest.json'

def installed_effects():
    p=data_dir()/'effects/installed.json'
    if not p.exists():return BASE_EFFECTS
    try:d=json.loads(p.read_text());return list(dict.fromkeys(BASE_EFFECTS+[x for x in d['effects'] if x in NAMES]))
    except (OSError,ValueError,KeyError):return BASE_EFFECTS

def install_pack(ctx,url=PACK_URL):
    ctx.emit(5,'Tìm gói hiệu ứng bổ sung…')
    with urllib.request.urlopen(url,timeout=30) as f:raw=f.read(100000)
    manifest=json.loads(raw);address=manifest['url']
    if not address.startswith(('https://raw.githubusercontent.com/seotro95/seotro/','https://github.com/seotro95/seotro/releases/download/')):raise ValueError('Địa chỉ gói hiệu ứng không được hỗ trợ.')
    with urllib.request.urlopen(address,timeout=45) as f:data=f.read(1000000)
    if hashlib.sha256(data).hexdigest()!=manifest['sha256']:raise ValueError('Hash gói hiệu ứng không khớp.')
    pack=json.loads(data)
    if any(x not in NAMES for x in pack['effects']) or any(x not in TRANSITIONS for x in pack['transitions']):raise ValueError('Gói có mục không tương thích phiên bản này.')
    save_json(data_dir()/'effects/installed.json',pack);ctx.emit(100,'Đã cài gói hiệu ứng bổ sung.');return pack
