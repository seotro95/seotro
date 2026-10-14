"""SRT parsing, validation and generation, with Unicode preserved."""
import re

STAMP = re.compile(r'^(\d{1,3}):(\d{2}):(\d{2})[,.](\d{3})$')


def seconds(value):
    match = STAMP.fullmatch(value.strip())
    if not match:
        raise ValueError('Mốc thời gian không hợp lệ: ' + value[:30])
    h, m, s, ms = map(int, match.groups())
    if m >= 60 or s >= 60:
        raise ValueError('Phút và giây phải nhỏ hơn 60.')
    return h * 3600 + m * 60 + s + ms / 1000


def timestamp(value):
    total = round(float(value) * 1000)
    h, rest = divmod(total, 3600000)
    m, rest = divmod(rest, 60000)
    s, ms = divmod(rest, 1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def parse_srt(content):
    content = content.lstrip('\ufeff').replace('\r\n', '\n').strip()
    if not content:
        raise ValueError('Phụ đề đang trống.')
    cues = []
    for block in re.split(r'\n\s*\n', content):
        lines = block.splitlines()
        if lines and lines[0].strip().isdigit():
            lines.pop(0)
        if not lines or '-->' not in lines[0]:
            raise ValueError('Mỗi đoạn SRT cần có thời gian bắt đầu --> kết thúc.')
        start, end = lines.pop(0).split('-->', 1)
        a, b = seconds(start), seconds(end)
        text = '\n'.join(lines).strip()
        if b <= a or not text:
            raise ValueError('Phụ đề cần có nội dung và thời gian kết thúc lớn hơn bắt đầu.')
        if cues and a < cues[-1]['start']:
            raise ValueError('Các đoạn phụ đề cần theo thứ tự thời gian.')
        cues.append({'start': a, 'end': b, 'text': text})
    if len(cues) > 10000:
        raise ValueError('Tối đa 10.000 đoạn phụ đề.')
    return cues


def to_srt(cues):
    result = '\n\n'.join(f"{i}\n{timestamp(c['start'])} --> {timestamp(c['end'])}\n{c['text']}"
                         for i, c in enumerate(cues, 1)) + '\n'
    parse_srt(result)
    return result
