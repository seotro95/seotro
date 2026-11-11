from __future__ import annotations
import difflib,math,re
from pathlib import Path
from .common import srt

DEFAULT_STYLE={'font':'Arial','size':32,'color':'#FFFFFF','outline_color':'#000000','outline':2,'bold':False,'italic':False,'position':'bottom','background':False,'background_color':'#000000'}

def seconds(value):
    if isinstance(value,(float,int)):return float(value)
    value=str(value).strip().replace(',','.')
    parts=value.split(':')
    try:return sum(float(n)*60**i for i,n in enumerate(reversed(parts)))
    except ValueError:raise ValueError('Mốc thời gian cần là số giây hoặc HH:MM:SS.mmm.') from None

def validate(cues,duration):
    cleaned=[]
    for i,c in enumerate(cues,1):
        a,b=seconds(c['start']),seconds(c['end']);text=str(c['text']).strip()
        if not math.isfinite(a+b) or a<0 or b<=a or b>duration+.06:raise ValueError(f'Phụ đề {i}: mốc phải nằm trong voice và kết thúc sau bắt đầu.')
        if not text:continue
        if len(text)>4000:raise ValueError(f'Phụ đề {i} quá dài.')
        cleaned.append({'start':round(a,3),'end':round(min(b,duration),3),'text':text})
    if not cleaned:raise ValueError('Không có lời phụ đề hợp lệ.')
    return sorted(cleaned,key=lambda x:(x['start'],x['end']))

def read_srt(path,duration):
    text=Path(path).read_text(encoding='utf-8-sig').replace('\r\n','\n').strip();cues=[]
    for block in re.split(r'\n\s*\n',text):
        lines=block.splitlines();n=next((i for i,x in enumerate(lines) if '-->' in x),None)
        if n is None:continue
        a,b=lines[n].split('-->',1);b=b.strip().split()[0]
        cues.append({'start':seconds(a),'end':seconds(b),'text':'\n'.join(lines[n+1:])})
    return validate(cues,duration)

def read_txt(path):
    text=Path(path).read_text(encoding='utf-8-sig').strip()
    if not text:raise ValueError('Tệp TXT trống.')
    return text

def align_txt(text,asr,duration):
    # Match the provided spelling to recognized word times; unmatched spans
    # interpolate between anchors. Low match ratios are explicitly reported.
    tokens=list(re.finditer(r'\S+',text));source=[]
    for c in asr:
        if c.get('words'):source.extend(c['words'])
        else:
            words=c['text'].split();step=(c['end']-c['start'])/max(1,len(words))
            source.extend({'text':w,'start':c['start']+i*step,'end':c['start']+(i+1)*step} for i,w in enumerate(words))
    norm=lambda w:re.sub(r'[^\w]','',w.casefold())
    left=[norm(x['text']) for x in source];right=[norm(x.group()) for x in tokens]
    matcher=difflib.SequenceMatcher(None,left,right,autojunk=False);anchors={}
    for a,b,n in matcher.get_matching_blocks():
        for k in range(n):anchors[b+k]=(source[a+k]['start'],source[a+k]['end'])
    ratio=len(anchors)/max(1,len(tokens));times=[]
    for i,t in enumerate(tokens):
        if i in anchors:times.append(anchors[i]);continue
        lo=max((k for k in anchors if k<i),default=-1);hi=min((k for k in anchors if k>i),default=len(tokens))
        a=anchors[lo][1] if lo>=0 else 0;b=anchors[hi][0] if hi<len(tokens) else duration
        step=max(.001,(b-a)/(hi-lo-1));times.append((a+(i-lo-1)*step,a+(i-lo)*step))
    cues=[];start=0
    for i,t in enumerate(tokens):
        stop=bool(re.search(r'[.!?。！？]$',t.group())) or i-start>=11 or i==len(tokens)-1
        if stop:
            a=max(0,min(duration-.05,times[start][0]));b=max(a+.04,min(duration,times[i][1]))
            cues.append({'start':a,'end':b,'text':text[tokens[start].start():tokens[i].end()].strip()});start=i+1
    return validate(cues,duration),ratio

def style(value=None):
    d={**DEFAULT_STYLE,**(value or {})}
    d['font']=str(d['font']).strip()
    if not d['font'] or len(d['font'])>100 or any(c in d['font'] for c in ',\n\r{}\\'):raise ValueError('Tên phông không hợp lệ.')
    for key in ['color','outline_color','background_color']:
        if not re.fullmatch(r'#[0-9a-fA-F]{6}',str(d[key])):raise ValueError('Màu cần định dạng #RRGGBB.')
    d['size']=float(d['size']);d['outline']=float(d['outline'])
    if not 12<=d['size']<=100 or not 0<=d['outline']<=10:raise ValueError('Cỡ chữ 12–100; viền 0–10.')
    if d['position'] not in ['bottom','middle','top']:raise ValueError('Vị trí phụ đề không hợp lệ.')
    return d

def escape(text):
    return text.replace('\\','\\\\').replace('{',r'\{').replace('}',r'\}').replace('\r','').replace('\n',r'\N')

def write_ass(path,cues,width,height,settings=None,offset=0,duration=None):
    d=style(settings);size=d['size']*height/720
    color=lambda h:'&H00'+h[5:7]+h[3:5]+h[1:3]
    def stamp(t):
        n=max(0,round(t*100));h,n=divmod(n,360000);m,n=divmod(n,6000);s,n=divmod(n,100);return f'{h}:{m:02}:{s:02}.{n:02}'
    alignment={'bottom':2,'middle':5,'top':8}[d['position']]
    header=f'''[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,{d['font']},{size},{color(d['color'])},{color(d['color'])},{color(d['background_color'] if d['background'] else d['outline_color'])},{color(d['background_color'])},{-1 if d['bold'] else 0},{-1 if d['italic'] else 0},0,0,100,100,0,0,{3 if d['background'] else 1},{d['outline']*height/720},0,{alignment},{round(width*.04)},{round(width*.04)},{round(height*.055)},1
[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
'''
    lines=[]
    for c in cues:
        a=max(0,c['start']-offset);b=c['end']-offset
        if duration is not None:b=min(duration,b)
        if b>a:lines.append(f'Dialogue: 0,{stamp(a)},{stamp(b)},Default,,0,0,0,,{escape(c["text"])}\n')
    Path(path).write_text(header+''.join(lines),encoding='utf-8')

def export(cues,path):
    path=Path(path)
    if path.suffix.lower()=='.srt':path.write_text(srt(cues),encoding='utf-8-sig')
    elif path.suffix.lower()=='.txt':path.write_text('\n'.join(c['text'] for c in cues)+'\n',encoding='utf-8-sig')
    else:raise ValueError('Chọn đuôi .txt hoặc .srt.')
