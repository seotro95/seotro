from __future__ import annotations
import copy,json,math,re
from pathlib import Path
from .common import save_json
from .subtitles import DEFAULT_STYLE,style,validate
from .effects import FILTERS,MOTIONS,TRANSITIONS

DEFAULTS={'resolution':720,'fps':24,'quality':'fast','encoder':'auto','threads':2,'language':'en','whisper_model':'tiny','mute_source':True,'source_volume':.2,'subtitle_path':'','subtitle_mode':'none','subtitle_style':DEFAULT_STYLE,'logo_path':'','logo_position':'top_right','logo_size':12.,'logo_opacity':1.,'full_verify':False,'screen_minors':True,'fit':'fill','auto_effects':True,'auto_transitions':True,'clip_model_path':None,'whisper_model_path':None}

def options(value=None):
    d={**copy.deepcopy(DEFAULTS),**(value or {})};d['subtitle_style']=style(d['subtitle_style'])
    if d['aspect_ratio'] not in ['16:9','9:16']:raise ValueError('Chọn 16:9 ngang hoặc 9:16 dọc.')
    d.setdefault('export_format','mp4');d.setdefault('auto_filename','VIDEO_HOAN_CHINH')
    d['auto_filename']=str(d['auto_filename']).strip()
    if d['export_format'] not in ['mp4','mkv']:raise ValueError('Định dạng xuất cần MP4 hoặc MKV.')
    name=d['auto_filename']
    if not name or len(name)>100 or re.search(r'[<>:"/\\|?*\x00-\x1f]',name) or name.endswith(('.', ' ')) or name.split('.')[0].upper() in ['CON','PRN','AUX','NUL']+[f'{p}{i}' for p in ['COM','LPT'] for i in range(1,10)]:raise ValueError('Tên video tự động không hợp lệ; chỉ nhập tên, không nhập đường dẫn.')
    d['threads']=int(d['threads']);d['fps']=int(d['fps']);d['resolution']=int(d['resolution'])
    for k in ['source_volume','logo_size','logo_opacity']:d[k]=float(d[k])
    if not 1<=d['threads']<=16:raise ValueError('CPU nhận dạng cần từ 1 đến 16 luồng.')
    if d['resolution'] not in [360,720,1080] or d['fps'] not in [24,25,30,60]:raise ValueError('Độ phân giải/FPS không hỗ trợ.')
    if d['quality'] not in ['fast','balanced','quality'] or d['encoder'] not in ['auto','cpu','nvenc','qsv','amf']:raise ValueError('Chế độ xuất không hợp lệ.')
    if not 0<=float(d['source_volume'])<=1 or not 2<=float(d['logo_size'])<=40 or not 0<=float(d['logo_opacity'])<=1:raise ValueError('Âm lượng/kích thước/độ mờ ngoài giới hạn.')
    if d['subtitle_mode'] not in ['none','soft','burn'] or d['fit'] not in ['fill','contain']:raise ValueError('Tùy chọn hiển thị không hợp lệ.')
    if d['logo_position'] not in ['top_left','top_right','bottom_left','bottom_right','center']:raise ValueError('Vị trí logo không hợp lệ.')
    return d

DEFAULTS.update(export_format='mp4',auto_filename='VIDEO_HOAN_CHINH',language='auto',visual_script_path='',whisper_model='base',aspect_ratio='16:9')

def reindex(project):
    plan=project['plan'];cursor=0
    for i,s in enumerate(plan['shots']):
        s.update(index=i,start_frame=cursor,end_frame=cursor+int(s['frames']),last=i==len(plan['shots'])-1);cursor+=int(s['frames'])
    plan['total_frames']=cursor;plan['video_seconds']=cursor/plan['fps']
    return project

def validate_project(p):
    if p.get('schema')!='autodoc-project-2':raise ValueError('Đây không phải dự án AutoDoc Studio2.')
    p['settings']=options(p['settings']);plan=p['plan'];fps=int(plan['fps']);total=0
    if fps not in [24,25,30,60] or not math.isfinite(float(plan['voice_seconds'])) or plan['voice_seconds']<4:raise ValueError('FPS/thời lượng dự án không hợp lệ.')
    plan['fps']=fps
    if not p['files'] or not plan['shots']:raise ValueError('Dự án chưa có cảnh.')
    for i,f in enumerate(p['files']):
        if f['id']!=i or f['kind'] not in ['image','video']:raise ValueError('Danh sách nguồn không hợp lệ.')
    for s in plan['shots']:
        s['source_id']=int(s['source_id']);s['frames']=int(s['frames'])
        if not 0<=int(s['source_id'])<len(p['files']) or int(s['frames'])<1:raise ValueError('Cảnh tham chiếu nguồn sai.')
        if s.get('effect','none') not in set(FILTERS)|MOTIONS:raise ValueError('Hiệu ứng không được hỗ trợ.')
        if s.get('transition','cut') not in TRANSITIONS:raise ValueError('Chuyển cảnh không được hỗ trợ.')
        for key,lo,hi,default in [('speed',.25,3,1),('crop',1,2,1),('focus_x',0,1,.5),('focus_y',0,1,.5)]:
            value=float(s.get(key,default))
            if not math.isfinite(value) or not lo<=value<=hi:raise ValueError(f'Cảnh có {key} ngoài giới hạn.')
            s[key]=value
        start=float(s.get('source_in',0))
        if not math.isfinite(start) or start<0:raise ValueError('Điểm đầu clip không hợp lệ.')
        s['source_in']=start;total+=int(s['frames'])
    if abs(total/fps-plan['voice_seconds'])>1/fps+.002:raise ValueError('Tổng cảnh phải khớp thời lượng voice, không thay lời đọc.')
    p['cues']=validate(p['cues'],plan['voice_seconds']);return reindex(p)

def save(p,path=None):
    validate_project(p);path=Path(path or p['project_file']).resolve();protected={Path(p['voice_source']).resolve()}|{Path(x['path']).resolve() for x in p['files']}
    protected|={Path(p['settings'][k]).resolve() for k in ['logo_path','subtitle_path','visual_script_path'] if p['settings'].get(k)}
    if path in protected:raise ValueError('Không ghi dự án đè lên nguồn.')
    p['project_file']=str(path);save_json(path,p);return path

def load(path):
    p=json.loads(Path(path).read_text(encoding='utf-8-sig'));p['project_file']=str(Path(path).resolve());return validate_project(p)

def split(p,index,seconds_in_scene):
    s=p['plan']['shots'][index];n=round(seconds_in_scene*p['plan']['fps'])
    if n<max(1,p['plan']['fps']//2) or s['frames']-n<max(1,p['plan']['fps']//2):raise ValueError('Mỗi phần sau chia cần ít nhất0,5giây.')
    right=copy.deepcopy(s);right['source_in']+=n/p['plan']['fps']*s.get('speed',1);right['frames']-=n;right['transition']='cut';s['frames']=n
    p['plan']['shots'].insert(index+1,right);return reindex(p)

def merge_previous(p,index):
    if index<=0:raise ValueError('Chọn cảnh thứ2trở đi để gộp vào cảnh trước.')
    p['plan']['shots'][index-1]['frames']+=p['plan']['shots'][index]['frames'];del p['plan']['shots'][index];return reindex(p)

def swap_sources(p,a,b):
    shots=p['plan']['shots']
    if not 0<=b<len(shots):return p
    keys=['source_id','source_name','source_in','effect','crop','focus_x','focus_y','speed']
    for k in keys:shots[a][k],shots[b][k]=shots[b].get(k),shots[a].get(k)
    return p

def change_fps(p,fps):
    if fps not in [24,25,30,60]:raise ValueError('FPS không hỗ trợ.')
    old=p['plan']['fps'];cursor=0
    for s in p['plan']['shots']:
        end=round(s['end_frame']/old*fps);s['frames']=max(1,end-cursor);cursor+=s['frames']
    target=math.ceil(p['plan']['voice_seconds']*fps-1e-7)
    p['plan']['shots'][-1]['frames']+=target-cursor;p['plan']['fps']=fps;p['settings']['fps']=fps
    return validate_project(p)
