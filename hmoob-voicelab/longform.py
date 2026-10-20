"""Lossless, bounded planning for documents of up to one million characters."""
from __future__ import annotations

import re

MAX_CHARACTERS = 1_000_000
MAX_TEXT_BYTES = 4_000_000
MAX_JSON_BYTES = 16_000_000
CHUNK_CHARACTERS = 300
PLANNER_VERSION = 1
_BOUNDARY = re.compile(r"(?<=[.!?。！？])\s+|[\r\n]+")


def validate_text(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Nhập văn bản cần đọc.')
    if len(text) > MAX_CHARACTERS:
        raise ValueError('Văn bản tối đa 1.000.000 ký tự.')
    try:
        text.encode('utf-8')
    except UnicodeError:
        raise ValueError('Văn bản chứa ký tự Unicode không hợp lệ.') from None
    return text


def plan(text, limit=CHUNK_CHARACTERS):
    """Return contiguous source spans without dropping whitespace or punctuation.

    Each search sees at most ``limit`` characters, including unbroken words and
    huge whitespace runs. Short sentences are packed rather than synthesized
    individually. The saved spans, not a future re-plan, drive resumed jobs.
    """
    validate_text(text)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 32 <= limit <= 1000:
        raise ValueError('Giới hạn chia đoạn không hợp lệ.')
    spans, start, size = [], 0, len(text)
    while start < size:
        end = min(start + limit, size)
        if end < size:
            window = text[start:end]
            floor = limit // 2
            candidates = [m.end() for m in _BOUNDARY.finditer(window) if m.end() >= floor]
            if candidates:
                end = start + candidates[-1]
            else:
                for index in range(len(window) - 1, floor - 1, -1):
                    if window[index].isspace():
                        end = start + index + 1
                        break
        spans.append({'start': start, 'end': end})
        start = end
    return spans
