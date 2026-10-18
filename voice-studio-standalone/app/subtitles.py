"""Bounded subtitle parsing with exact millisecond timeline exports."""
import re
from html import escape, unescape

MAX_TIMELINE_SECONDS = 3 * 60 * 60
MAX_CUES = 10_000
CLOCK_PATTERN = r'(?:\d{1,3}:)?\d{1,3}:[0-5]?\d(?:[,.]\d{1,3})?'
ARROW_PATTERN = r'(?:--\s*>|->|→|–>|—>)'
_RANGE = re.compile(r'^\s*(?P<start>' + CLOCK_PATTERN + r')\s*' + ARROW_PATTERN +
                    r'\s*(?P<end>' + CLOCK_PATTERN + r')(?P<tail>.*)$')
_SRT_POSITION = re.compile(r'(?:\s+[XY][12]:\d+){4}\s*$', re.IGNORECASE)
_FORMATTING = re.compile(r'</?(?:b|i|u|s|font|ruby|rt|c|v)(?:\.[\w.-]+)?(?:\s+[^<>]*)?>', re.IGNORECASE)


def normalize_newlines(text):
    return text.lstrip('\ufeff').replace('\r\n', '\n').replace('\r', '\n')


def parse_clock(value):
    """Read MM:SS or HH:MM:SS without floating point rounding drift."""
    if not re.fullmatch(CLOCK_PATTERN, value.strip()):
        raise ValueError('Mốc thời gian cần có dạng MM:SS hoặc HH:MM:SS,mmm.')
    whole, _, fraction = value.strip().replace(',', '.').partition('.')
    parts = [int(part) for part in whole.split(':')]
    if len(parts) == 3:
        hours, minutes, seconds = parts
        if minutes > 59:
            raise ValueError('Phần phút trong HH:MM:SS phải nhỏ hơn 60.')
    else:
        hours, (minutes, seconds) = 0, parts
    milliseconds = ((hours * 60 + minutes) * 60 + seconds) * 1000 + int(fraction.ljust(3, '0') or 0)
    if milliseconds > MAX_TIMELINE_SECONDS * 1000:
        raise ValueError('Mốc kết thúc không được vượt quá 3 giờ.')
    return milliseconds / 1000


def clean_cue_text(text):
    # Remove recognized subtitle formatting only; preserve literal <names>.
    return unescape(_FORMATTING.sub('', text)).strip()


def _timing_line(line):
    match = _RANGE.fullmatch(line)
    if not match:
        return None
    tail = match['tail']
    if _SRT_POSITION.fullmatch(tail):
        tail = ''
    elif tail and not tail[0].isspace():
        return None
    return parse_clock(match['start']), parse_clock(match['end']), tail.strip()


def validate_cues(cues, *, label='SRT'):
    if not cues:
        raise ValueError(f'{label}: tệp chưa có lời đọc.')
    if len(cues) > MAX_CUES:
        raise ValueError(f'{label}: tối đa 10.000 câu.')
    previous_end = 0
    for index, cue in enumerate(cues, 1):
        if not cue['text'].strip() or cue['start'] < 0 or cue['start'] >= cue['end']:
            raise ValueError(f'{label}: câu {index} cần lời đọc và mốc kết thúc lớn hơn mốc bắt đầu.')
        if cue['end'] > MAX_TIMELINE_SECONDS:
            raise ValueError(f'{label}: mốc kết thúc không được vượt quá 3 giờ.')
        if cue['start'] < previous_end:
            raise ValueError(f'{label}: câu {index} chồng mốc thời gian với câu trước; hãy sửa tệp để không mất lời đọc.')
        previous_end = cue['end']
    return cues


def parse_srt(text):
    """Accept SRT, abbreviated clocks and files missing blank lines.

    Invalid timing lines are errors, including those inside cue text, so clocks
    cannot accidentally become spoken dialogue.
    """
    lines = normalize_newlines(text).strip().split('\n')
    cues = []
    index = 0
    try:
        while index < len(lines):
            if not lines[index].strip():
                index += 1
                continue
            if lines[index].strip().isdigit() and index + 1 < len(lines) and _timing_line(lines[index + 1]) is not None:
                index += 1
            timing = _timing_line(lines[index])
            if timing is None:
                raise ValueError(f'mốc thời gian không hợp lệ ở câu {len(cues) + 1}. Dùng HH:MM:SS,mmm --> HH:MM:SS,mmm.')
            start, end, inline = timing
            index += 1
            content = [inline] if inline else []
            while index < len(lines):
                line = lines[index]
                if _timing_line(line) is not None:
                    break
                if line.strip().isdigit() and index + 1 < len(lines) and _timing_line(lines[index + 1]) is not None:
                    break
                if re.search(ARROW_PATTERN, line) and re.match(r'\s*\d', line):
                    raise ValueError(f'mốc thời gian không hợp lệ sau câu {len(cues) + 1}.')
                content.append(line)
                index += 1
            cues.append({'start': start, 'end': end, 'text': clean_cue_text('\n'.join(content))})
            if len(cues) > MAX_CUES:
                raise ValueError('tối đa 10.000 câu.')
        return validate_cues(cues)
    except ValueError as exc:
        if str(exc).startswith('SRT:'):
            raise
        raise ValueError(f'SRT: {exc}') from None


def timestamp(seconds):
    value = max(0, round(seconds*1000))
    h, value = divmod(value, 3600000)
    m, value = divmod(value, 60000)
    s, ms = divmod(value, 1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def export_srt(cues, offset=0):
    return '\n\n'.join(f'{i}\n{timestamp(c["start"]+offset)} --> {timestamp(c["end"]+offset)}\n{escape(c["text"], quote=False)}' for i, c in enumerate(cues, 1)) + '\n'


def minute_timestamp(seconds):
    ms=round(seconds*1000)
    return f'{ms//60000:02d}:{ms//1000%60:02d}.{ms%1000:03d}'
