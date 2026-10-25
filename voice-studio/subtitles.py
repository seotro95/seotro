"""Bounded caption parsing and millisecond SRT exports."""
import re
from html import unescape

from caption_markers import cue_index_value, normalize_caption_text, parse_timing_line


def parse_srt(text):
    """Read cue boundaries from timing lines, including adjacent pasted cues.

    Blank separators are common formatting rather than the boundary itself.
    Otherwise an omitted blank would put the next cue's number and clocks in
    the words sent to the speech engine.
    """
    cues = []
    timing = None
    content_lines = []
    next_index = 1
    numbered_captions = False

    def finish():
        start, end = timing['start'], timing['end']
        lines = ([timing['text']] if timing['text'] else []) + content_lines
        content = unescape(re.sub(r'<[^>]*>', '', '\n'.join(lines))).strip()
        if not content or start >= end or end > 10800 or (cues and start < cues[-1]['end']):
            raise ValueError('SRT: cần lời đọc, mốc tăng dần, không chồng nhau và kết thúc trong 3 giờ.')
        cues.append({'start': start, 'end': end, 'text': content})
        if len(cues) > 10000:
            raise ValueError('SRT tối đa 10.000 câu.')

    for line in normalize_caption_text(text).split('\n'):
        try:
            marker = parse_timing_line(line)
        except ValueError as exc:
            raise ValueError(f'SRT: mốc thời gian không hợp lệ ở câu {len(cues)+1}. {exc}') from None
        if marker is None:
            content_lines.append(line)
            continue
        # A standalone number just before a timing line can be the next
        # cue's index. Keep it when it is the current cue's only body line:
        # a numeric caption is speech, and must never become an empty cue.
        while content_lines and not content_lines[-1].strip():
            content_lines.pop()
        has_other_words = (timing is None or timing['text']
                           or any(line.strip() for line in content_lines[:-1]))
        value = cue_index_value(content_lines[-1]) if content_lines else None
        if value is not None and has_other_words:
            blank_before = len(content_lines) > 1 and not content_lines[-2].strip()
            if timing is None or numbered_captions or value == next_index or blank_before:
                content_lines.pop()
                next_index = value
                numbered_captions = True
        if timing is not None:
            finish()
        elif any(line.strip() for line in content_lines):
            raise ValueError('SRT: cần bắt đầu bằng mốc thời gian hoặc số thứ tự câu.')
        timing = marker
        content_lines = []
        next_index += 1
    if timing is None:
        raise ValueError('SRT: mốc thời gian không hợp lệ ở câu 1. Dùng HH:MM:SS,mmm --> HH:MM:SS,mmm.')
    finish()
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
