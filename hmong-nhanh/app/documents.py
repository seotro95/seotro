"""Read subtitle metadata without treating its timestamps or cue IDs as speech.

Only structural subtitle markers are removed. Numbers in dialogue are kept.
Times are parsed as integer milliseconds before converting to API seconds.
"""
from __future__ import annotations

import html
import re

MAX_CHARACTERS = 1_000_000
MAX_TIMELINE_SECONDS = 168 * 3600
_TIME = r'\d+(?::\d+){1,2}(?:[,.]\d+)?'
_RANGE = re.compile(rf'^(?P<start>{_TIME})\s*(?:-->|->|→|–>)\s*(?P<end>{_TIME})(?P<tail>.*)$')
_TIMEISH_RANGE = re.compile(r'^\s*[\[\("\'`]*\d+:[^\n]*?(?:-->|->|→|–>)')
_TAG = re.compile(r'</?(?:b|i|u|s|font|c(?:\.[\w-]+)*|v|lang|ruby|rt)(?:\s+[^<>]*?)?\s*>', re.I)
_INLINE_TIME = re.compile(rf'<{_TIME}>')
_ASS_OVERRIDE = re.compile(r'\{\\[^{}]*\}')
_VTT_SETTING = re.compile(r'^(?:align|line|position|size|vertical|region):\S+$')
_BRACKET_MARKER = re.compile(rf'^\s*\[(?P<time>{_TIME})\]\s*')
_PLAIN_MARKER = re.compile(rf'^\s*(?P<time>{_TIME})(?:\s+(?P<text>.*)|\s*)$')


def _milliseconds(value):
    clock, separator, fraction = value.replace(',', '.').partition('.')
    fields = clock.split(':')
    if (len(fields) not in (2, 3) or any(not field.isdecimal() for field in fields)
            or any(len(field) != 2 for field in fields[1:])
            or (separator and (not fraction.isdecimal() or not 1 <= len(fraction) <= 3))):
        raise ValueError('Mốc thời gian phải có dạng 00:04:28,533 hoặc 04:28.533.')
    if len(fields[0]) > 6:
        raise ValueError('Mốc thời gian quá lớn. Kiểm tra lại tệp phụ đề.')
    numbers = list(map(int, fields))
    if numbers[-1] >= 60 or (len(numbers) == 3 and numbers[-2] >= 60):
        raise ValueError('Phút/giây trong mốc thời gian không hợp lệ (phần giây phải dưới 60).')
    seconds = numbers[-1] + numbers[-2] * 60
    if len(numbers) == 3:
        seconds += numbers[0] * 3600
    return seconds * 1000 + int(fraction.ljust(3, '0') or '0')


def _unquote(line):
    line = line.strip()
    # A timestamp quoted when pasted is still a timestamp, not spoken text.
    for left, right in (('"', '"'), ("'", "'"), ('`', '`'), ('[', ']'), ('(', ')')):
        if line.startswith(left) and line.endswith(right):
            line = line[1:-1].strip()
    return line


def _range(line, number):
    value = _unquote(line)
    match = _RANGE.match(value)
    if match is None:
        if _TIMEISH_RANGE.match(line):
            raise ValueError(f'Dòng {number}: mốc phụ đề không hợp lệ; sửa mốc trước khi tạo giọng.')
        return None
    tail = match['tail']
    if tail and not tail[0].isspace():
        raise ValueError(f'Dòng {number}: thiếu khoảng cách sau mốc kết thúc.')
    try:
        start, end = _milliseconds(match['start']), _milliseconds(match['end'])
    except (ValueError, OverflowError) as exc:
        raise ValueError(f'Dòng {number}: {exc}') from None
    if end <= start:
        raise ValueError(f'Dòng {number}: mốc kết thúc phải lớn hơn mốc bắt đầu.')
    # WebVTT layout settings never become dialogue; inline TXT dialogue does.
    words = tail.strip().split()
    while words and _VTT_SETTING.fullmatch(words[0]):
        words.pop(0)
    return {'start_ms': start, 'end_ms': end, 'inline': ' '.join(words)}


def _spoken(text):
    text = _ASS_OVERRIDE.sub('', text)
    text = _INLINE_TIME.sub('', text)
    text = _TAG.sub('', text)
    return html.unescape(text).strip()


def _without_vtt_metadata(lines):
    """Keep indices stable while dropping WebVTT header, NOTE, STYLE and REGION."""
    result = list(lines)
    first = next((i for i, line in enumerate(lines) if line.strip()), None)
    is_vtt = first is not None and bool(re.match(r'^WEBVTT(?:\s|$)', lines[first].strip()))
    if not is_vtt:
        return result, False
    i = first
    while i < len(lines) and lines[i].strip():
        # Tolerate a missing blank line after the WEBVTT header.
        if i > first and _TIMEISH_RANGE.match(lines[i]):
            break
        result[i] = ''
        i += 1
    while i < len(lines):
        stripped = lines[i].strip()
        if (i == 0 or not lines[i - 1].strip()) and re.match(r'^(?:NOTE(?:\s|$)|STYLE$|REGION$)', stripped):
            while i < len(lines) and lines[i].strip():
                result[i] = ''
                i += 1
        else:
            i += 1
    return result, True


def _untimed(lines):
    cleaned, found = [], False
    for line in lines:
        remaining = line
        marker = _BRACKET_MARKER.match(remaining)
        while marker:
            _milliseconds(marker['time'])
            remaining = remaining[marker.end():]
            found = True
            marker = _BRACKET_MARKER.match(remaining)
        if remaining == line:
            marker = _PLAIN_MARKER.match(line)
            if marker:
                _milliseconds(marker['time'])
                remaining = marker['text'] or ''
                found = True
        cleaned.append(remaining)
    text = '\n'.join(cleaned).strip()
    if found:
        text = _spoken(text)
    if not text:
        raise ValueError('Tệp chỉ có mốc thời gian; chưa có văn bản để đọc.')
    return {'format': 'timestamped' if found else 'text', 'text': text, 'cues': [],
            'duration': None, 'timed': False,
            'warnings': ['Đã bỏ mốc đầu dòng. Thiếu cặp thời gian bắt đầu/kết thúc nên đọc theo nhịp tự nhiên.'] if found else []}


def parse_document(text, timing='auto'):
    """Return clean speech plus optional subtitle timing, without guessing words.

    ``auto`` preserves a valid non-overlapping subtitle timeline. ``natural``
    strips the same metadata and reads dialogue in file order, allowing valid
    overlapping or out-of-order cues. Invalid timestamp syntax is always an
    error rather than accidentally becoming speech.
    """
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_CHARACTERS:
        raise ValueError('Nhập từ 1 đến 1.000.000 ký tự có nội dung.')
    if timing not in ('auto', 'natural'):
        raise ValueError('Chế độ thời gian phải là auto hoặc natural.')
    text = text.lstrip('\ufeff').replace('\r\n', '\n').replace('\r', '\n')
    lines, is_vtt = _without_vtt_metadata(text.split('\n'))
    ranges = [(i, value) for i, line in enumerate(lines) if (value := _range(line, i + 1)) is not None]
    if not ranges:
        return _untimed(lines)

    # Detect only IDs which have structural evidence. In particular, a number
    # spoken on its own before an unnumbered timestamp is not discarded.
    ids, previous_id = set(), None
    for index, value in ranges:
        preceding = index - 1
        candidate = lines[preceding].strip() if preceding >= 0 else ''
        boundary = preceding == 0 or (preceding > 0 and not lines[preceding - 1].strip())
        if candidate.isdecimal() and (boundary or (previous_id is not None and int(candidate) == previous_id + 1)):
            ids.add(preceding)
            previous_id = int(candidate)
        elif is_vtt and candidate and boundary:
            # WebVTT permits nonnumeric cue identifiers.
            ids.add(preceding)
            previous_id = None
        else:
            previous_id = None

    first = ranges[0][0]
    if any(lines[i].strip() for i in range(first) if i not in ids):
        raise ValueError('Có văn bản trước mốc phụ đề đầu tiên. Đặt lời vào một mốc hoặc dùng tệp TXT chỉ có lời.')
    cues, warning = [], []
    previous_end = 0
    for offset, (index, value) in enumerate(ranges):
        if timing == 'auto' and value['end_ms'] > MAX_TIMELINE_SECONDS * 1000:
            raise ValueError(f'Dòng {index + 1}: thời gian phụ đề vượt 168 giờ. Sửa mốc hoặc chọn đọc theo nhịp tự nhiên.')
        after = ranges[offset + 1][0] if offset + 1 < len(ranges) else len(lines)
        body = [value['inline']] + [lines[i] for i in range(index + 1, after) if i not in ids]
        spoken = _spoken('\n'.join(body))
        if not spoken:
            raise ValueError(f'Dòng {index + 1}: phụ đề có thời gian nhưng chưa có lời để đọc.')
        if value['start_ms'] < previous_end:
            if timing == 'auto':
                raise ValueError(f'Dòng {index + 1}: mốc phụ đề chồng lấn hoặc sai thứ tự. Sửa mốc hoặc chọn đọc theo nhịp tự nhiên.')
            if not warning:
                warning.append('Mốc phụ đề chồng lấn hoặc sai thứ tự; đọc lời theo thứ tự trong tệp, không căn thời gian.')
        previous_end = value['end_ms']
        cues.append({'start': value['start_ms'] / 1000, 'end': value['end_ms'] / 1000, 'text': spoken})
    return {'format': 'vtt' if is_vtt else 'srt', 'text': '\n\n'.join(cue['text'] for cue in cues),
            'cues': cues, 'duration': max(cue['end'] for cue in cues),
            'timed': timing == 'auto', 'warnings': warning}
