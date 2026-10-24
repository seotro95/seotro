"""Validated direct subtitle projects and fixed-path ASS rendering."""
import math
import re
from subtitles import export_srt, parse_srt


def validate_cues(cues, duration):
    if not cues or len(cues)>10000:
        raise ValueError('Cần 1–10.000 câu phụ đề.')
    normalized=[]
    ids=set()
    for cue in cues:
        start,end=float(cue['start']),float(cue['end'])
        text=cue['text'].strip()
        if not all(math.isfinite(v) for v in (start,end)) or start<0 or end>duration+.001 or start>=end:
            raise ValueError('Mỗi câu cần thời điểm bắt đầu nhỏ hơn kết thúc và nằm trong video.')
        if not text or len(text)>4000:
            raise ValueError('Mỗi câu cần nội dung, tối đa 4.000 ký tự.')
        row={'start':round(start,3),'end':round(end,3),'text':text}
        for key in ('id','character_id'):
            value=cue.get(key)
            if value is not None:
                if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',value):
                    raise ValueError('Mã câu hoặc nhân vật không hợp lệ.')
                row[key]=value
        if row.get('id') in ids:
            raise ValueError('Mỗi câu cần mã riêng, không trùng lặp.')
        if row.get('id'):ids.add(row['id'])
        normalized.append(row)
    if any(c['start']<normalized[i-1]['end'] for i,c in enumerate(normalized) if i):
        raise ValueError('Các câu phải theo thứ tự và không chồng mốc thời gian.')
    if sum(len(c['text']) for c in normalized)>200000:
        raise ValueError('Phụ đề tối đa 200.000 ký tự.')
    cleaned=parse_srt(export_srt(normalized))
    return [{**cue,**{key:row[key] for key in ('id','character_id') if key in row}}
            for cue,row in zip(cleaned,normalized)]


def ass_text(text):
    # User content is text, never ASS styling or drawing commands.
    return text.replace('\\','\\\\').replace('{','\\{').replace('}','\\}').replace('\r','').replace('\n',r'\N')


FONTS = ('Arial', 'Times New Roman', 'Verdana', 'Tahoma', 'Courier New')
def validate_style(style=None):
    defaults={'font':'Arial','size':4.5,'color':'#ffffff','outline_color':'#000000','background_color':'#000000','bold':False,'italic':False,'background':False,'position':'bottom','margin':4.5,'outline':2}
    style=style or {}
    if not isinstance(style,dict) or set(style)-set(defaults):raise ValueError('Kiểu phụ đề không hợp lệ.')
    result={**defaults,**style}
    if result['font'] not in FONTS or result['position'] not in ('top','middle','bottom'):raise ValueError('Phông hoặc vị trí phụ đề không hợp lệ.')
    for key in ('color','outline_color','background_color'):
        if not isinstance(result[key],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',result[key]):raise ValueError('Màu phụ đề cần dạng #RRGGBB.')
    for key,low,high in [('size',2,12),('margin',0,25),('outline',0,6)]:
        if isinstance(result[key],bool):raise ValueError('Thông số phụ đề không hợp lệ.')
        try:value=float(result[key])
        except (ValueError,TypeError):raise ValueError('Thông số phụ đề không hợp lệ.') from None
        if not math.isfinite(value) or not low<=value<=high:raise ValueError('Thông số phụ đề vượt giới hạn.')
        result[key]=value
    for key in ('bold','italic','background'):
        if not isinstance(result[key],bool):raise ValueError('Kiểu phụ đề không hợp lệ.')
    return result

def write_ass(path,cues,width,height,style=None):
    def stamp(seconds):
        value=round(seconds*100)
        h,value=divmod(value,360000);m,value=divmod(value,6000);s,cs=divmod(value,100)
        return f'{h}:{m:02}:{s:02}.{cs:02}'
    style=validate_style(style)
    size=max(8,round(height*style['size']/100))
    def color(value):return '&H00'+value[5:7]+value[3:5]+value[1:3]
    alignment={'bottom':2,'middle':5,'top':8}[style['position']]
    header=f'''[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style['font']},{size},{color(style['color'])},{color(style['color'])},{color(style['background_color'] if style['background'] else style['outline_color'])},{color(style['background_color'])},{-1 if style['bold'] else 0},{-1 if style['italic'] else 0},0,0,100,100,0,0,{3 if style['background'] else 1},{style['outline']},0,{alignment},15,15,{round(height*style['margin']/100)},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    path.write_text(header+''.join(f'Dialogue: 0,{stamp(c["start"])},{stamp(c["end"])},Default,,0,0,0,,{ass_text(c["text"])}\n' for c in cues),encoding='utf-8')
