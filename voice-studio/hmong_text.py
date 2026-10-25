"""Conservative Hmong RPA normalization and reference-calibrated pacing.

RPA uses its final Latin letters as tone markers. They must never be removed,
romanized again or treated as English spelling. Duration here is a heuristic
based on whitespace/hyphen-separated syllables, not a pronunciation score.
"""
from __future__ import annotations

from collections.abc import Collection, Mapping
import math
import re
import string
import unicodedata


class HmongTextError(ValueError):
    """An actionable text or pacing error suitable for the user interface."""

    def __init__(self, message, *, unsupported_characters=()):
        super().__init__(message)
        self.unsupported_characters = list(dict.fromkeys(unsupported_characters))[:16]
        self.code = 'unsupported_speech_characters' if self.unsupported_characters else None


_TRANSLATION = str.maketrans({
    **{character: "'" for character in '‘’‚‛ʼ'},
    **{character: '"' for character in '“”„‟'},
    **{character: '-' for character in '‐‑‒–—―−'},
    '…': '...', '\u200b': ' ', '\ufeff': ' ',
})
_ALLOWED = frozenset(string.ascii_letters + string.digits + string.punctuation + ' ')
_SYLLABLE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)*|[0-9]+(?:[.,][0-9]+)*")


def _shown(characters):
    return ', '.join(repr(character) for character in dict.fromkeys(characters))[:120]


def normalize_text(text: str, *, vocabulary: Collection[str] | Mapping[str, object] | None = None) -> str:
    """Normalize formatting only; preserve RPA letters, case and numeric text.

    Other scripts/diacritics are rejected rather than silently converted to the
    F5 vocabulary's unknown-space token. An optional vocabulary also checks
    model-specific ASCII punctuation. Empty formatting normalizes to ''.
    """
    if not isinstance(text, str):
        raise HmongTextError('Nội dung Hmong cần là văn bản.')
    normalized = unicodedata.normalize('NFC', text).translate(_TRANSLATION)
    normalized = ''.join(' ' if character.isspace() else character for character in normalized)
    normalized = re.sub(r' +', ' ', normalized).strip()
    unsupported = [character for character in normalized if character not in _ALLOWED]
    if unsupported:
        raise HmongTextError('Nội dung cần dùng chữ Hmong RPA (a–z), với chữ đuôi ghi thanh điệu. '
                             'Ký tự chưa hỗ trợ: ' + _shown(unsupported) + '. Không tự đổi hoặc bỏ chữ.',
                             unsupported_characters=unsupported)
    if vocabulary is not None:
        unknown = [character for character in normalized if character not in vocabulary]
        if unknown:
            raise HmongTextError('Mô hình không có các ký tự: ' + _shown(unknown)
                                 + '. Hãy sửa văn bản; tool không tự thay chúng bằng khoảng trắng.',
                                 unsupported_characters=unknown)
    return normalized


def syllable_count(text: str) -> int:
    """Count RPA orthographic syllables, including hyphen-separated units.

    Digits remain opaque input units; this does not guess Hmong number words.
    Borrowed words/proper names may not follow the monosyllabic RPA heuristic.
    """
    return len(_SYLLABLE.findall(normalize_text(text)))


def estimate_new_seconds(reference_text: str, text: str, reference_seconds: float, speed: float = 1.0) -> float:
    """Estimate generated duration from the actual reference syllable rate.

    Retain F5's short-input guard: below ten UTF-8 bytes its local speed is 0.3.
    One second is a floor so a short utterance is not forced into a tiny mel.
    """
    for value, label in ((reference_seconds, 'Thời lượng mẫu'), (speed, 'Tốc độ')):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise HmongTextError(label + ' cần là số dương hữu hạn.')
    reference = normalize_text(reference_text)
    target = normalize_text(text)
    reference_count, target_count = syllable_count(reference), syllable_count(target)
    if not reference_count or not target_count:
        raise HmongTextError('Lời mẫu và nội dung cần có từ Hmong RPA, không chỉ dấu câu hoặc khoảng trắng.')
    local_speed = 0.3 if len(target.encode('utf-8')) < 10 else speed
    return max(1.0, float(reference_seconds) * target_count / reference_count / local_speed)


def iter_batches(text: str, reference_text: str, reference_seconds: float, speed: float = 1.0,
                 *, max_chars: int = 240, max_new_seconds: float = 16.0):
    """Yield whole-word chunks within both character and estimated time bounds.

    A single oversized unspaced token is rejected instead of splitting its RPA
    tone suffix. Whitespace is normalized, while all words/punctuation survive.
    """
    if isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars < 1:
        raise HmongTextError('Giới hạn ký tự cần là số nguyên dương.')
    if (isinstance(max_new_seconds, bool) or not isinstance(max_new_seconds, (int, float))
            or not math.isfinite(max_new_seconds) or max_new_seconds < 1):
        raise HmongTextError('Giới hạn thời lượng đoạn cần ít nhất một giây.')
    normalized = normalize_text(text)
    if not normalized:
        return
    # Validate the reference and numeric options even before the first chunk.
    estimate_new_seconds(reference_text, normalized, reference_seconds, speed)

    tokens = normalized.split(' ')
    start = 0
    while start < len(tokens):
        candidate = ''
        accepted = ''
        next_start = start
        for index in range(start, len(tokens)):
            candidate += (' ' if candidate else '') + tokens[index]
            if len(candidate) > max_chars:
                break
            if not syllable_count(candidate):
                continue
            if estimate_new_seconds(reference_text, candidate, reference_seconds, speed) <= max_new_seconds:
                accepted = candidate
                next_start = index + 1
            # Adding text can lower duration when the short-input speed guard
            # turns off at ten bytes. After that point duration is monotonic.
            elif len(candidate.encode('utf-8')) >= 10:
                break
        if not accepted:
            raise HmongTextError('Một từ hoặc cụm không có dấu cách vượt giới hạn tạo giọng. '
                                 'Thêm dấu cách đúng giữa các âm tiết và kiểm tra lời mẫu khớp bản thu.')
        yield accepted
        start = next_start
