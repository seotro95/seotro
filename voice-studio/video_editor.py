"""Validated direct subtitle projects and fixed-path ASS rendering."""
import math
from subtitles import export_srt, parse_srt


def validate_cues(cues, duration):
    if not cues or len(cues)>10000:
        raise ValueError('Cần 1–10.000 câu phụ đề.')
    normalized=[]
    for cue in cues:
        start,end=float(cue['start']),float(cue['end'])
        text=cue['text'].strip()
        if not all(math.isfinite(v) for v in (start,end)) or start<0 or end>duration+.001 or start>=end:
            raise ValueError('Mỗi câu cần thời điểm bắt đầu nhỏ hơn kết thúc và nằm trong video.')
        if not text or len(text)>4000:
            raise ValueError('Mỗi câu cần nội dung, tối đa 4.000 ký tự.')
        normalized.append({'start':round(start,3),'end':round(end,3),'text':text})
    if any(c['start']<normalized[i-1]['end'] for i,c in enumerate(normalized) if i):
        raise ValueError('Các câu phải theo thứ tự và không chồng mốc thời gian.')
    if sum(len(c['text']) for c in normalized)>200000:
        raise ValueError('Phụ đề tối đa 200.000 ký tự.')
    return parse_srt(export_srt(normalized))


def ass_text(text):
    # User content is text, never ASS styling or drawing commands.
    return text.replace('\\','\\\\').replace('{','\\{').replace('}','\\}').replace('\r','').replace('\n',r'\N')


def write_ass(path,cues,width,height):
    def stamp(seconds):
        value=round(seconds*100)
        h,value=divmod(value,360000);m,value=divmod(value,6000);s,cs=divmod(value,100)
        return f'{h}:{m:02}:{s:02}.{cs:02}'
    size=max(16,round(height/22))
    header=f'''[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,15,15,{max(12,round(height*.045))},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    path.write_text(header+''.join(f'Dialogue: 0,{stamp(c["start"])},{stamp(c["end"])},Default,,0,0,0,,{ass_text(c["text"])}\n' for c in cues),encoding='utf-8')
