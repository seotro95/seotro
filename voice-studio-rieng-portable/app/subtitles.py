"""Strict, bounded SRT parsing and millisecond exports."""
import re
from html import unescape


def parse_srt(text):
    blocks = re.split(r'\n\s*\n', text.lstrip('\ufeff').replace('\r\n', '\n').strip())
    cues = []
    for block in blocks:
        lines = block.strip().splitlines()
        if lines and lines[0].strip().isdigit():
            lines = lines[1:]
        match = re.fullmatch(r'\s*(\d{2,3}):([0-5]\d):([0-5]\d)[,.](\d{3})\s*-->\s*(\d{2,3}):([0-5]\d):([0-5]\d)[,.](\d{3})\s*', lines[0] if lines else '')
        if not match:
            raise ValueError(f'SRT: mốc thời gian không hợp lệ ở câu {len(cues)+1}. Dùng HH:MM:SS,mmm --> HH:MM:SS,mmm.')
        numbers = list(map(int, match.groups()))
        start = numbers[0]*3600+numbers[1]*60+numbers[2]+numbers[3]/1000
        end = numbers[4]*3600+numbers[5]*60+numbers[6]+numbers[7]/1000
        content = unescape(re.sub(r'<[^>]*>', '', '\n'.join(lines[1:]))).strip()
        if not content or start >= end or end > 86400 or (cues and start < cues[-1]['end']):
            raise ValueError('SRT: cần lời đọc, mốc tăng dần, không chồng nhau và kết thúc trong 24 giờ.')
        cues.append({'start': start, 'end': end, 'text': content})
        if len(cues) > 100000:
            raise ValueError('SRT tối đa 100.000 câu.')
    return cues


def timestamp(seconds):
    value = max(0, round(seconds*1000))
    h, value = divmod(value, 3600000)
    m, value = divmod(value, 60000)
    s, ms = divmod(value, 1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def export_srt(cues, offset=0):
    return '\n\n'.join(f'{i}\n{timestamp(c["start"]+offset)} --> {timestamp(c["end"]+offset)}\n{c["text"]}' for i, c in enumerate(cues, 1)) + '\n'


def minute_timestamp(seconds):
    ms=round(seconds*1000)
    return f'{ms//60000:02d}:{ms//1000%60:02d}.{ms%1000:03d}'


def timed_txt(text):
    """Timestamped TXT: explicit ranges, or starts with a final empty end marker."""
    clock = r'(?:\d{1,3}:)?\d{1,2}:[0-5]\d(?:[.,]\d{1,3})?'
    pattern = re.compile(r'^\s*[\[(]?(' + clock + r')[\])]?\s*(?:-->\s*[\[(]?(' + clock + r')[\])]?)?\s*(?:[-–—|]\s*)?(.*)$')
    def seconds(value):
        fields=value.replace(',', '.').split(':')
        return sum(float(v)*60**i for i,v in enumerate(reversed(fields)))
    rows=[]
    for line in text.lstrip('\ufeff').splitlines():
        if not line.strip(): continue
        match=pattern.fullmatch(line)
        if match:
            start,end,content=match.groups()
            rows.append({'start':seconds(start),'end':seconds(end) if end else None,'text':content.strip()})
        elif rows:
            rows[-1]['text']+='\n'+line.strip()
        else:
            return None
    if not rows:return None
    cues=[]
    for i,row in enumerate(rows):
        if not row['text']:
            if i==len(rows)-1 and row['end'] is None and cues:continue
            raise ValueError('TXT: mốc không có lời chỉ được dùng làm mốc kết thúc cuối tệp.')
        end=row['end'] if row['end'] is not None else (rows[i+1]['start'] if i+1<len(rows) else None)
        if end is None:
            raise ValueError('TXT có mốc bắt đầu cần mốc kết thúc câu cuối. Thêm dòng cuối, ví dụ [02:30], hoặc dùng khoảng 00:00 --> 00:05 lời thoại.')
        cues.append(dict(start=row['start'],end=end,text=row['text']))
    return parse_srt(export_srt(cues))


def normalize_script(text, kind):
    text=text.lstrip('\ufeff').replace('\r\n','\n').replace('\r','\n')
    if not text.strip():raise ValueError('Tệp chưa có nội dung để đọc.')
    if kind=='srt' or re.search(r'^\s*\d{2,3}:[0-5]\d:[0-5]\d[,.]\d{3}\s*-->.*\n', text, re.M):
        return export_srt(parse_srt(text)), 'srt'
    cues=timed_txt(text)
    return (export_srt(cues),'srt') if cues else (text,'txt')


def decode_script(raw):
    if raw.startswith((b'\xff\xfe',b'\xfe\xff')):
        return raw.decode('utf-16')
    if raw.startswith(b'\xef\xbb\xbf'):return raw.decode('utf-8-sig')
    if b'\x00' in raw:
        return raw.decode('utf-16-be' if raw[0]==0 else 'utf-16-le')
    return raw.decode('utf-8')
