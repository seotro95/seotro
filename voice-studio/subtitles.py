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
        if not content or start >= end or end > 10800 or (cues and start < cues[-1]['end']):
            raise ValueError('SRT: cần lời đọc, mốc tăng dần, không chồng nhau và kết thúc trong 3 giờ.')
        cues.append({'start': start, 'end': end, 'text': content})
        if len(cues) > 10000:
            raise ValueError('SRT tối đa 10.000 câu.')
    return cues


def timestamp(seconds):
    value = max(0, round(seconds*1000))
    h, value = divmod(value, 3600000)
    m, value = divmod(value, 60000)
    s, ms = divmod(value, 1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def export_srt(cues, offset=0):
    return '\n\n'.join(f'{i}\n{timestamp(c["start"]+offset)} --> {timestamp(c["end"]+offset)}\n{c["text"]}' for i, c in enumerate(cues, 1)) + '\n'
