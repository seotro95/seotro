"""Decode uploaded scripts and retain explicit TXT/SRT dialogue timelines."""
from pathlib import Path
import math
import re
import unicodedata

from subtitles import (ARROW_PATTERN, CLOCK_PATTERN, MAX_CUES, MAX_TIMELINE_SECONDS,
                       clean_cue_text, export_srt, normalize_newlines, parse_clock,
                       parse_srt, validate_cues)

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_CHARACTERS = 200_000
_SEPARATOR = r'(?:' + ARROW_PATTERN + r'|[-–—])'
_BRACKETED = re.compile(r'^\s*[\[(]\s*(?P<start>' + CLOCK_PATTERN + r')'
                        r'(?:\s*' + _SEPARATOR + r'\s*(?P<end>' + CLOCK_PATTERN + r'))?'
                        r'\s*[\])]\s*(?:[:|–—-]\s*)?(?P<text>.*)$')
_PLAIN = re.compile(r'^\s*(?P<start>' + CLOCK_PATTERN + r')'
                   r'(?:\s*' + _SEPARATOR + r'\s*(?P<end>' + CLOCK_PATTERN + r'))?'
                   r'(?=$|\s|[|–—-])\s*(?:[|–—-]\s*)?(?P<text>.*)$')
_SUSPICIOUS_CLOCK = re.compile(r'^\s*[\[(]?\d{1,3}:')


def _check_text(text):
    if '\ufffd' in text:
        raise ValueError('Tệp có ký tự thay thế không đọc được (�). Hãy kiểm tra và lưu lại bằng UTF-8.')
    if any(unicodedata.category(char) == 'Cc' and char not in '\t\n\r' for char in text):
        raise ValueError('Tệp chứa dữ liệu nhị phân hoặc ký tự điều khiển; hãy chọn đúng tệp TXT/SRT.')
    return text


def decode_script_bytes(payload):
    """Decode common Windows encodings strictly, never replacing characters."""
    if len(payload) > MAX_FILE_BYTES:
        raise ValueError('Tệp văn bản không được vượt quá 2 MB.')
    warnings = []
    if payload.startswith((b'\xff\xfe\x00\x00', b'\x00\x00\xfe\xff')):
        encoding, codec = 'UTF-32', 'utf-32'
    elif payload.startswith((b'\xff\xfe', b'\xfe\xff')):
        encoding, codec = 'UTF-16', 'utf-16'
    elif payload.startswith(b'\xef\xbb\xbf'):
        encoding, codec = 'UTF-8 BOM', 'utf-8-sig'
    elif b'\x00' in payload:
        even, odd = payload[::2], payload[1::2]
        if len(payload) % 2 == 0 and odd and odd.count(0) / len(odd) > .4 and even.count(0) / max(1, len(even)) < .05:
            encoding, codec = 'UTF-16 LE', 'utf-16-le'
        elif len(payload) % 2 == 0 and even and even.count(0) / len(even) > .4 and odd.count(0) / max(1, len(odd)) < .05:
            encoding, codec = 'UTF-16 BE', 'utf-16-be'
        else:
            raise ValueError('Không xác định được mã hóa của tệp. Hãy lưu bằng UTF-8 hoặc UTF-16 có BOM.')
    else:
        encoding, codec = 'UTF-8', 'utf-8'
        try:
            text = payload.decode(codec, errors='strict')
        except UnicodeDecodeError:
            encoding, codec = 'Windows-1258', 'cp1258'
            warnings.append('Tệp dùng mã hóa Windows-1258 cũ. Hãy kiểm tra dấu tiếng Việt trong ô văn bản sau khi nhập.')
        else:
            return _check_text(text), encoding, warnings
    try:
        text = payload.decode(codec, errors='strict')
    except UnicodeDecodeError:
        raise ValueError('Không đọc được mã hóa của tệp. Hãy lưu TXT/SRT bằng UTF-8 hoặc UTF-16 rồi nhập lại.') from None
    if len(text) > MAX_CHARACTERS:
        raise ValueError('Tệp vượt quá 200.000 ký tự. Hãy chia nội dung thành các phần trước khi nhập.')
    return _check_text(unicodedata.normalize('NFC', text) if codec == 'cp1258' else text), encoding, warnings


def _txt_timing(line):
    match = _BRACKETED.fullmatch(line) or _PLAIN.fullmatch(line)
    if match is None:
        return None
    return {'start': parse_clock(match['start']),
            'end': parse_clock(match['end']) if match['end'] is not None else None,
            'text': match['text']}


def _timed_txt(text, total_seconds):
    lines = text.split('\n')
    parsed = []
    has_clock = False
    for line_number, line in enumerate(lines, 1):
        cue = _txt_timing(line)
        if cue is not None:
            has_clock = True
        parsed.append((line_number, line, cue))
    if not has_clock:
        if any(_SUSPICIOUS_CLOCK.match(line) for line in lines):
            raise ValueError('TXT: có mốc thời gian không hợp lệ. Dùng [MM:SS] lời thoại hoặc [MM:SS - MM:SS] lời thoại.')
        return None, []
    cues = []
    for line_number, line, cue in parsed:
        if cue is not None:
            cues.append(cue)
        elif line.strip():
            if _SUSPICIOUS_CLOCK.match(line):
                raise ValueError(f'TXT: mốc thời gian không hợp lệ ở dòng {line_number}.')
            if not cues:
                raise ValueError(f'TXT: dòng {line_number} chưa có mốc thời gian; hãy thêm mốc để không bỏ sót lời đọc.')
            cues[-1]['text'] += ('\n' if cues[-1]['text'] else '') + line
    if len(cues) > MAX_CUES:
        raise ValueError('TXT: tối đa 10.000 câu.')
    inferred = False
    for index, cue in enumerate(cues):
        cue['text'] = clean_cue_text(cue['text'])
        if not cue['text']:
            raise ValueError(f'TXT: câu {index + 1} chưa có lời đọc.')
        if cue['start'] >= MAX_TIMELINE_SECONDS:
            raise ValueError(f'TXT: mốc bắt đầu câu {index + 1} phải nhỏ hơn 3 giờ.')
        if cue['end'] is None and index + 1 < len(cues):
            cue['end'] = cues[index + 1]['start']
            inferred = True
    if cues[-1]['end'] is None and total_seconds is not None:
        cues[-1]['end'] = total_seconds
        inferred = True
    complete = [cue for cue in cues if cue['end'] is not None]
    if complete:
        validate_cues(complete, label='TXT')
    if cues[-1]['end'] is None and len(cues) > 1 and cues[-1]['start'] < cues[-2]['end']:
        raise ValueError('TXT: câu cuối chồng mốc thời gian với câu trước.')
    warnings = ['Mốc kết thúc của câu chỉ có giờ bắt đầu được lấy từ giờ bắt đầu câu kế tiếp.'] if inferred else []
    return cues, warnings


def parse_script_text(text, input_format='txt', *, total_seconds=None):
    """Normalize speech input; timed TXT becomes canonical SRT.

    A start-only final cue has no knowable end. Return a pending timeline and
    require the caller to provide its intended total duration.
    """
    if input_format not in {'txt', 'srt'}:
        raise ValueError('Chỉ hỗ trợ tệp .txt hoặc .srt.')
    if len(text) > MAX_CHARACTERS:
        raise ValueError('Tệp vượt quá 200.000 ký tự. Hãy chia nội dung thành các phần trước khi nhập.')
    source_text = normalize_newlines(_check_text(text))
    text = source_text.strip()
    if not text:
        raise ValueError('Tệp chưa có nội dung để đọc.')
    if total_seconds is not None:
        if isinstance(total_seconds, bool) or not isinstance(total_seconds, (float, int)) or not math.isfinite(total_seconds) or not 0 < total_seconds <= MAX_TIMELINE_SECONDS:
            raise ValueError('Tổng thời lượng phải lớn hơn 0 và không vượt quá 3 giờ.')
        if abs(total_seconds * 1000 - round(total_seconds * 1000)) > 1e-6:
            raise ValueError('Tổng thời lượng chỉ hỗ trợ độ chính xác đến mili giây.')
    first_lines = [line for line in text.split('\n') if line.strip()][:2]
    numbered_srt = len(first_lines) == 2 and first_lines[0].strip().isdigit() and re.search(ARROW_PATTERN, first_lines[1])
    if input_format == 'srt' or numbered_srt:
        cues, warnings = parse_srt(text), []
    else:
        cues, warnings = _timed_txt(text, total_seconds)
    if cues is None:
        return {'text': text, 'input_format': 'txt', 'cues': [], 'has_timeline': False,
                'timeline_seconds': None, 'requires_total_duration': False, 'warnings': warnings,
                'source_text': source_text, 'source_input_format': input_format}
    pending = cues[-1]['end'] is None
    if pending:
        warnings.append('Câu cuối chỉ có mốc bắt đầu. Nhập tổng thời lượng video để xác định mốc kết thúc chính xác; tool không tự đoán thời lượng.')
    else:
        validate_cues(cues, label='SRT' if input_format == 'srt' else 'TXT')
    return {'text': text if pending else export_srt(cues), 'input_format': 'txt' if pending else 'srt',
            'cues': cues, 'has_timeline': True, 'timeline_seconds': None if pending else cues[-1]['end'],
            'requires_total_duration': pending, 'warnings': warnings,
            'source_text': source_text, 'source_input_format': input_format}


def import_script_bytes(payload, filename, *, total_seconds=None):
    extension = Path(filename or '').suffix.lower()
    if extension not in {'.txt', '.srt'}:
        raise ValueError('Chọn tệp có đuôi .txt hoặc .srt.')
    text, encoding, warnings = decode_script_bytes(payload)
    result = parse_script_text(text, extension[1:], total_seconds=total_seconds)
    result['encoding'] = encoding
    result['warnings'] = warnings + result['warnings']
    return result
