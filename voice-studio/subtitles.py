"""Strict, bounded SRT parsing and millisecond exports."""
import re
from html import unescape


def parse_srt(text):
    text = text.lstrip('\ufeff').replace('\r\n', '\n').replace('\r', '\n').strip()
    clock = r'(?:\d{1,3}:)?[0-5]?\d:[0-5]\d(?:[,.]\d{1,3})?'
    pattern = re.compile(r'^\s*(' + clock + r')\s*-->\s*(' + clock + r')(?=\s|$)[ \t]*(.*)$', re.M)
    matches = list(pattern.finditer(text))
    if not matches or text[:matches[0].start()].strip().strip('0123456789'):
        raise ValueError('SRT: dùng HH:MM:SS,mmm --> HH:MM:SS,mmm hoặc MM:SS --> MM:SS.')
    cues = []
    for index, match in enumerate(matches):
        tail = text[match.end():matches[index+1].start() if index+1 < len(matches) else len(text)]
        lines = tail.strip().splitlines()
        if index+1 < len(matches) and lines and lines[-1].strip().isdigit():
            lines.pop()
        content = unescape(re.sub(r'<[^>]*>', '', '\n'.join([match[3], *lines]))).strip()
        if '-->' in content:
            raise ValueError(f'SRT: mốc thời gian không hợp lệ ở câu {index+1}.')
        start, end = clock_seconds(match[1]), clock_seconds(match[2])
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


def minute_timestamp(seconds):
    ms=round(seconds*1000)
    return f'{ms//60000:02d}:{ms//1000%60:02d}.{ms%1000:03d}'


def clock_seconds(value):
    parts = value.replace(',', '.').split(':')
    return sum(float(part) * 60 ** index for index, part in enumerate(reversed(parts)))


def normalize_script(text, input_format='txt'):
    """Preserve explicit timings; never guess a final end time."""
    text = text.lstrip('\ufeff').replace('\r\n', '\n').replace('\r', '\n').strip()
    if input_format == 'srt' or '-->' in text:
        return export_srt(parse_srt(text)), 'srt'
    clock = r'(?:\d{1,3}:)?[0-5]?\d:[0-5]\d(?:[.,]\d{1,3})?'
    pattern = re.compile(r'^\s*(?:\[(' + clock + r')\]|\((' + clock + r')\)|(' + clock + r'))(?=\s|$)[ \t]*(?:[-–—|][ \t]*)?(.*)$')
    entries = []
    for line in text.splitlines():
        if not line.strip():
            continue
        match = pattern.fullmatch(line)
        if match:
            entries.append([clock_seconds(next(v for v in match.groups()[:3] if v is not None)), match[4]])
        elif entries:
            entries[-1][1] += '\n' + line
        else:
            return text, 'txt'
    if not entries:
        return text, 'txt'
    if entries[-1][1].strip():
        raise ValueError('TXT có mốc bắt đầu: thêm một dòng chỉ ghi mốc kết thúc cuối (ví dụ [02:30]), hoặc dùng khoảng 00:01 --> 00:05 cho từng câu.')
    if len(entries) < 2:
        raise ValueError('TXT có mốc cần ít nhất một câu và mốc kết thúc cuối.')
    cues = [{'start': a[0], 'end': b[0], 'text': a[1]} for a, b in zip(entries, entries[1:])]
    return export_srt(parse_srt(export_srt(cues))), 'srt'
