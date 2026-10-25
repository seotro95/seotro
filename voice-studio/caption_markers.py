"""Recognize caption metadata without rewriting any spoken words or numbers."""
from __future__ import annotations

import re

_PREFIX = re.compile(r'^[ \t\ufeff\u200b\u200e\u200f]+', re.M)
CLOCK = r'\d{1,5}:\d{2}(?::\d{2})?(?:[,.]\d{1,3})?(?![\d:.,])'
_WRAPS = {'[': ']', '(': ')', '"': '"', "'": "'", '“': '”', '‘': '’'}
_TOKEN = '(?:' + CLOCK + '|' + '|'.join(
    re.escape(left) + r'\s*' + CLOCK + r'\s*' + re.escape(right)
    for left, right in _WRAPS.items()) + ')'
_RANGE = re.compile(r'^(?P<start>' + _TOKEN + r')\s*(?:-->|->|→|⟶|–>|—>)\s*(?P<end>' + _TOKEN + r')(?P<text>.*)$')
_INDEX = re.compile(r'^\d{1,9}[.)]?\s+(?=[\[\(\"\'“‘]?\d+:)')
_SETTING = re.compile(r'^\s*(?:align|position|line|size|vertical):[^\s]+(?:\s+|$)', re.I)
_LEADING = re.compile(r'^\s*(?P<clock>' + _TOKEN + r')(?=\s|$)\s*(?:[-–—|]\s*)?')


def normalize_caption_text(text):
    if not isinstance(text, str):
        raise ValueError('Nội dung phụ đề cần là văn bản.')
    return _PREFIX.sub('', text.replace('\r\n', '\n').replace('\r', '\n'))


def _seconds(token):
    token = token.strip()
    if token[:1] in _WRAPS and token.endswith(_WRAPS[token[0]]):
        token = token[1:-1].strip()
    parts = re.split(r'[,.]', token)
    clock = list(map(int, parts[0].split(':')))
    if len(clock) not in {2, 3} or clock[-1] >= 60 or (len(clock) == 3 and clock[-2] >= 60):
        raise ValueError('Mốc thời gian không hợp lệ. Dùng HH:MM:SS,mmm hoặc MM:SS.mmm.')
    fraction = int(parts[1]) / (10 ** len(parts[1])) if len(parts) == 2 else 0
    return (clock[-1] + clock[-2] * 60 + (clock[0] * 3600 if len(clock) == 3 else 0) + fraction)


def parse_timing_line(line):
    """Return a leading clock range and any inline words, or None.

    Endpoints may have brackets or quotes. An entire range may also have a
    wrapper. Only known caption settings immediately after the end are ignored.
    No blank line is needed to recognize a subsequent SRT cue.
    """
    source = normalize_caption_text(line).strip()
    source = _INDEX.sub('', source, count=1)
    match = _RANGE.match(source)
    closing = None
    if match is None and source[:1] in _WRAPS:
        closing = _WRAPS[source[0]]
        match = _RANGE.match(source[1:].lstrip())
    if match is None:
        if looks_like_timing_line(source):
            raise ValueError('Mốc phụ đề chưa đầy đủ hoặc không hợp lệ. Dùng HH:MM:SS,mmm --> HH:MM:SS,mmm.')
        return None
    tail = match['text'].strip()
    if closing is not None:
        if tail.startswith(closing):
            tail = tail[len(closing):].lstrip()
        elif tail.endswith(closing):
            tail = tail[:-len(closing)].rstrip()
        else:
            raise ValueError('Đóng dấu ngoặc hoặc dấu nháy quanh mốc thời gian phụ đề.')
    while True:
        setting = _SETTING.match(tail)
        if setting is None:
            break
        tail = tail[setting.end():]
    return {'start': _seconds(match['start']), 'end': _seconds(match['end']), 'text': tail}


def strip_leading_clock(line):
    """Remove an optional single caption label; callers retain the opt-out."""
    source = normalize_caption_text(line)
    match = _LEADING.match(source)
    if match is None:
        return source
    _seconds(match['clock'])
    return source[match.end():]


def is_cue_index(line):
    return bool(re.fullmatch(r'\d{1,9}[.)]?', normalize_caption_text(line).strip()))


def looks_like_timing_line(line):
    """Recognize malformed range metadata so it is rejected, never narrated."""
    source = normalize_caption_text(line).strip()
    source = _INDEX.sub('', source, count=1)
    return bool(re.match(r'^[\[\(\"\'“‘]?\d+[\d:.,\s\[\]\(\)\"\'“”‘’]*(?:-->|->|→|⟶|–>|—>)', source))
