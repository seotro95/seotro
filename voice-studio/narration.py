"""Bounded chunks and disk-streamed PCM assembly for up to three hours."""
import re
import wave
from dataclasses import dataclass

MAX_SECONDS = 3 * 60 * 60
MAX_CHARACTERS = 200_000
PROFILES = {'natural': (1.0, 0.22), 'story': (0.94, 0.5), 'news': (1.04, 0.25), 'calm': (0.88, 0.65), 'energetic': (1.12, 0.16), 'review': (1.04, 0.18), 'documentary': (0.97, 0.35)}


@dataclass
class Segment:
    text: str = ''
    pause: float = 0
    emphasis: bool = False
    cue: int | None = None
    emotion: str | None = None
    rhythm_pause: float = 0


def spoken_text(text, *, remove_labels=True):
    """Ignore caption ranges/indices; retain all ordinary words and numbers.

    Strong range metadata is never narration, even when single-clock labels
    are opted out. Original editable source is retained separately by the job.
    """
    from caption_markers import normalize_caption_text, parse_timing_line, strip_leading_clock, is_cue_index
    from html import unescape
    lines=normalize_caption_text(text).split('\n')
    spans=[parse_timing_line(line) for line in lines]
    caption_mode=any(span is not None for span in spans)
    output=[]
    seen_range=False
    has_body=False
    next_index=1
    for index,line in enumerate(lines):
        span=spans[index]
        if span is not None:
            seen_range=True
            content=unescape(re.sub(r'<[^>]*>','',span['text']))
            has_body=bool(content.strip())
            output.append(content)
            next_index+=1
            continue
        if is_cue_index(line):
            following=index+1
            while following<len(lines) and not lines[following].strip():
                following+=1
            if following<len(lines) and spans[following] is not None and (not seen_range or has_body):
                value=int(line.strip().rstrip('.)'))
                if value>0 and (not seen_range or value==next_index):
                    next_index=value
                    continue
        if caption_mode and line.strip()=='WEBVTT':
            continue
        content=strip_leading_clock(line) if remove_labels else line
        if caption_mode:
            content=unescape(re.sub(r'<[^>]*>','',content))
        output.append(content)
        has_body=has_body or bool(content.strip())
    return '\n'.join(output)


def split_script(text, limit=240, *, normalizer=None):
    # Explicit pauses and emphasis never reach the language model as spoken words.
    segments = []
    for part in re.split(r'(\[pause=\d+(?:\.\d+)?\]|\*\*[^*]+\*\*)', text):
        if not part:
            continue
        match = re.fullmatch(r'\[pause=(\d+(?:\.\d+)?)\]', part)
        if match:
            seconds = float(match.group(1))
            if not 0 <= seconds <= 10:
                raise ValueError('Mỗi [pause=...] phải từ 0 đến 10 giây.')
            segments.append(Segment(pause=seconds))
            continue
        emphasis = part.startswith('**') and part.endswith('**')
        if emphasis:
            part = part[2:-2]
        if normalizer is not None:
            # Parse pause/emphasis controls first. Keep paragraph boundaries
            # until sentence splitting, then normalize only spoken content.
            part = '\n'.join(normalizer(line) for line in part.splitlines())
        # Include newlines in splitting to retain paragraph breathing space.
        for sentence in re.split(r'(?<=[!?。！？;；])\s*|(?<=\.)(?!\d)\s+|\n+', part):
            sentence = sentence.strip()
            while sentence:
                end = min(limit, len(sentence))
                if end < len(sentence):
                    boundary = sentence.rfind(' ', 0, end + (normalizer is not None))
                    if normalizer is not None and boundary <= 0:
                        raise ValueError('Một từ Hmong quá dài và không có dấu cách. '
                                         'Thêm dấu cách đúng giữa các âm tiết RPA; không tự cắt chữ ghi thanh điệu.')
                    if boundary > end // 2 or normalizer is not None:
                        end = boundary
                piece, sentence = sentence[:end].strip(), sentence[end:].strip()
                if piece:
                    segments.append(Segment(text=piece, emphasis=emphasis))
    joined=[]
    pending=[]
    for segment in segments:
        if segment.text and not any(c.isalnum() for c in segment.text):
            if joined and joined[-1].text and len(joined[-1].text)+len(segment.text)<=limit:
                joined[-1].text+=segment.text
            else:pending.append(segment)
        else:
            prefix=''.join(s.text for s in pending)
            if segment.text and len(prefix)+len(segment.text)<=limit:segment.text=prefix+segment.text
            else:joined.extend(pending)
            pending=[]
            joined.append(segment)
    joined.extend(pending)
    return joined


def _pack_segments(source, limit):
    packed = []
    for segment in source:
        if (segment.text and packed and packed[-1].text and not segment.emphasis
                and not packed[-1].emphasis
                and packed[-1].emotion == segment.emotion and not packed[-1].rhythm_pause
                and len(packed[-1].text) + 1 + len(segment.text) <= limit):
            packed[-1].text += ' ' + segment.text
            packed[-1].rhythm_pause = segment.rhythm_pause
        else:
            packed.append(segment)
    return packed


def _expression_segments(text, job, *, timed=False):
    """Parse controls before text normalization; emotion persists within a cue.

    TXT keeps the selected emotion across paragraphs. Every SRT cue starts
    again with the job's emotion. Explicit pauses, including zero, override
    the automatic pause immediately before them.
    """
    if job.get('hmong_phrase_context') is True:
        return _context_expression_segments(text, job, timed=timed)
    from hmong_expression import automatic_pause, validate_emotion, validate_strength
    from hmong_text import normalize_speech_text as normalize_text
    emotion = validate_emotion(job.get('emotion', 'neutral'))
    strength = validate_strength(job.get('emotion_strength', .65))
    rhythm = bool(job.get('auto_rhythm', True)) and not timed
    emphasis = False
    output = []
    for part in re.split(r'(\[emotion=[^\]]*\]|\[pause=[^\]]*\]|\*\*)', text):
        if not part:
            continue
        if part == '**':
            emphasis = not emphasis
            continue
        if part.startswith('[emotion='):
            emotion = validate_emotion(part[len('[emotion='):-1].strip())
            continue
        if part.startswith('[pause='):
            value = part[len('[pause='):-1]
            if not re.fullmatch(r'\d+(?:\.\d+)?', value) or not 0 <= float(value) <= 10:
                raise ValueError('Mỗi [pause=...] phải từ 0 đến 10 giây.')
            if output and output[-1].text:
                output[-1].rhythm_pause = 0
            output.append(Segment(pause=float(value)))
            continue
        if re.search(r'\[emotion(?:=|\])|\[pause=', part, flags=re.IGNORECASE):
            raise ValueError('Kiểm tra cú pháp [emotion=warm] hoặc [pause=1].')
        for line in part.splitlines(keepends=True):
            newline = line.endswith(('\n', '\r'))
            normalized = normalize_text(line)
            # Closing dialogue quotes belong to the preceding sentence. Split
            # only at sentence punctuation, never every comma or RPA syllable.
            phrases = re.split(r'(?<=[.!?;:])\s+|(?<=[.!?;:][\"\')\]])\s+', normalized)
            line_segments = [segment for phrase in phrases
                             for segment in split_script(phrase, limit=160, normalizer=normalize_text)]
            for segment in line_segments:
                segment.emotion = emotion
                segment.emphasis = emphasis
                if rhythm and segment.text:
                    segment.rhythm_pause = automatic_pause(segment.text, emotion, strength)
                output.append(segment)
            if rhythm and newline and output and output[-1].text:
                output[-1].rhythm_pause = automatic_pause(output[-1].text, output[-1].emotion,
                                                         strength, paragraph=True)
    if emphasis:
        raise ValueError('Đóng phần nhấn giọng bằng dấu ** ở cuối đoạn.')
    # Added gaps and emphasis remain barriers; packing never loses a pause or
    # crosses an emotion change. A user-added gap also keeps sentence boundaries.
    return _pack_segments(output, 160) if job.get('paragraph_pause', 0) == 0 else output


def _context_line(text, emphasis):
    """Normalize a line while retaining which whole tokens contain bold text.

    Bold delimiters inside RPA words are rejected by the caller, so preserving
    a token-level flag is sufficient. Formatting normalization can expand
    punctuation or replace a zero-width separator without losing tone letters.
    """
    from hmong_text import normalize_speech_text as normalize_text
    words, flags = [], []
    for match in re.finditer(r'\S+', text):
        word = normalize_text(match.group())
        if not word:
            continue
        marked = any(emphasis[index] and character.isalnum()
                     for index, character in enumerate(text[match.start():match.end()], match.start()))
        if words:
            words.append(' ')
            flags.append(False)
        words.append(word)
        flags.extend([marked] * len(word))
    return ''.join(words), flags


def _context_phrases(runs, emotion, strength, rhythm):
    """Yield bounded linguistic context; emphasis applies to a containing phrase.

    No word alignment is available. A marked word does not become a separate
    F5 prompt, and the existing emphasis processing affects its whole bounded
    phrase. This preserves surrounding words for acoustic coarticulation.
    """
    from hmong_expression import automatic_pause
    text = ''.join(part for part, _ in runs)
    emphasis = [marked for part, marked in runs for _ in part]
    output, offset = [], 0
    for line in text.splitlines(keepends=True):
        normalized, flags = _context_line(line, emphasis[offset:offset + len(line)])
        offset += len(line)
        start = 0
        # Keep punctuation and closing dialogue quotes in the preceding phrase.
        boundaries = [match.start() for match in re.finditer(
            r'(?<=[.!?;:])\s+|(?<=[.!?;:]["\')\]])\s+', normalized)] + [len(normalized)]
        for boundary in boundaries:
            while start < boundary and normalized[start].isspace():
                start += 1
            while start < boundary:
                end = min(start + 160, boundary)
                if end < boundary:
                    end = normalized.rfind(' ', start, end + 1)
                    if end <= start:
                        raise ValueError('Một từ Hmong quá dài và không có dấu cách. '
                                         'Thêm dấu cách đúng giữa các âm tiết RPA; không tự cắt chữ ghi thanh điệu.')
                phrase = normalized[start:end].strip()
                if phrase:
                    segment = Segment(text=phrase, emotion=emotion,
                                      emphasis=any(flags[start:end]))
                    if rhythm:
                        segment.rhythm_pause = automatic_pause(phrase, emotion, strength)
                    output.append(segment)
                start = end
                while start < boundary and normalized[start].isspace():
                    start += 1
            start = boundary
        if rhythm and line.endswith(('\n', '\r')) and output:
            output[-1].rhythm_pause = automatic_pause(output[-1].text, emotion, strength, paragraph=True)
    return output


def _context_expression_segments(text, job, *, timed=False):
    """Opt-in context plan; old jobs retain the original expression parser.

    Buffers span bold toggles, never emotion/pause controls. With automatic
    rhythm disabled, compatible phrases can share one bounded F5 call even
    when some words are marked. Explicit zero pauses remain real boundaries.
    """
    from hmong_expression import validate_emotion, validate_strength
    if re.search(r'[A-Za-z]\*\*(?=[A-Za-z])', text):
        raise ValueError('Đặt ** quanh cả từ hoặc cụm Hmong; không chèn dấu nhấn bên trong âm tiết RPA '
                         'vì có thể tách chữ ghi thanh điệu.')
    emotion = validate_emotion(job.get('emotion', 'neutral'))
    strength = validate_strength(job.get('emotion_strength', .65))
    rhythm = bool(job.get('auto_rhythm', True)) and not timed
    marked, runs, output = False, [], []

    def flush():
        segments = _context_phrases(runs, emotion, strength, rhythm)
        runs.clear()
        if not rhythm and job.get('paragraph_pause', 0) == 0:
            packed = []
            for segment in segments:
                if packed and len(packed[-1].text) + 1 + len(segment.text) <= 160:
                    packed[-1].text += ' ' + segment.text
                    packed[-1].emphasis = packed[-1].emphasis or segment.emphasis
                else:
                    packed.append(segment)
            segments = packed
        output.extend(segments)

    for part in re.split(r'(\[emotion=[^\]]*\]|\[pause=[^\]]*\]|\*\*)', text):
        if not part:
            continue
        if part == '**':
            marked = not marked
        elif part.startswith('[emotion='):
            flush()
            emotion = validate_emotion(part[len('[emotion='):-1].strip())
        elif part.startswith('[pause='):
            flush()
            value = part[len('[pause='):-1]
            if not re.fullmatch(r'\d+(?:\.\d+)?', value) or not 0 <= float(value) <= 10:
                raise ValueError('Mỗi [pause=...] phải từ 0 đến 10 giây.')
            if output and output[-1].text:
                output[-1].rhythm_pause = 0
            output.append(Segment(pause=float(value)))
        else:
            if re.search(r'\[(?:emotion|pause)(?:=|\]|\s|$)', part, flags=re.IGNORECASE):
                raise ValueError('Kiểm tra cú pháp [emotion=warm] hoặc [pause=1].')
            if '*' in part:
                raise ValueError('Kiểm tra cú pháp **cụm cần nhấn**; mỗi đầu dùng đúng hai dấu *.')
            runs.append((part, marked))
    if marked:
        raise ValueError('Đóng phần nhấn giọng bằng dấu ** ở cuối đoạn.')
    flush()
    return output


def plan_segments(job):
    hmong = job.get('engine') in {'f5_hmong', 'hmong_native'}
    expression = hmong and job.get('segment_plan') == 'hmong-expression-v1'
    normalizer = None
    if hmong:
        from hmong_text import normalize_speech_text as normalize_text
        normalizer = normalize_text
    hmong_packed = (hmong and job.get('segment_plan') == 'hmong-packed-v1'
                    and job.get('paragraph_pause') == 0)
    limit = 160 if hmong_packed else 130 if job.get('engine') == 'vieneu_nano' else 240
    if job.get('input_format') == 'srt':
        from subtitles import parse_srt
        output = []
        for index, cue in enumerate(parse_srt(job['text'])):
            segments = (_expression_segments(cue['text'], job, timed=True) if expression else
                        split_script(cue['text'], limit=limit, normalizer=normalizer))
            if hmong_packed:
                segments = _pack_segments(segments, limit)
            if not any(s.text for s in segments):
                raise ValueError('Mỗi câu SRT cần có lời đọc.')
            for segment in segments:
                segment.cue = index
                output.append(segment)
        return output
    text = spoken_text(job['text'], remove_labels=job.get('skip_timestamps', True))
    if expression:
        return _expression_segments(text, job)
    if hmong:
        source = split_script(text, limit=limit, normalizer=normalizer)
        return _pack_segments(source, limit) if hmong_packed else source
    if job.get('segment_plan') != 'nano-packed-v1':
        return split_script(text)
    # Packing is opt-in with zero added sentence gap; explicit pauses/emphasis stay barriers.
    source = split_script(text, limit=130)
    return _pack_segments(source, 130)


class PCMWriter:
    """Write small blocks, never allocate a multi-hour waveform in RAM."""
    def __init__(self, path, rate=24000, max_seconds=MAX_SECONDS):
        self.rate = rate
        self.limit = int(rate * max_seconds)
        self.frames = 0
        self.file = wave.open(str(path), 'wb')
        self.file.setnchannels(1)
        self.file.setsampwidth(2)
        self.file.setframerate(rate)

    def append(self, path):
        with wave.open(str(path), 'rb') as source:
            if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (1, 2, self.rate):
                raise ValueError('PCM input format mismatch')
            while self.frames < self.limit:
                block = source.readframes(min(65536, self.limit - self.frames))
                if not block:
                    break
                self.file.writeframesraw(block)
                self.frames += len(block) // 2
            truncated = source.tell() < source.getnframes()
        return truncated

    def silence(self, seconds):
        remaining = min(round(seconds * self.rate), self.limit - self.frames)
        while remaining > 0:
            count = min(65536, remaining)
            self.file.writeframesraw(b'\0\0' * count)
            self.frames += count
            remaining -= count

    def close(self):
        self.file.close()


def _labelled_voice_text_error(exc, label):
    error = ValueError(f'{label}: {exc}')
    for attribute in ('code', 'unsupported_characters'):
        if hasattr(exc, attribute):
            setattr(error, attribute, getattr(exc, attribute))
    return error


def validate_voice_text(text,engine,label='Nội dung'):
    import unicodedata
    if engine in {'f5_hmong', 'hmong_native'}:
        from hmong_text import normalize_text
        try:
            text = normalize_text(text)
        except ValueError as exc:
            raise _labelled_voice_text_error(exc, label) from None
        if engine == 'hmong_native':
            from hmong_native import EngineError, validate_text
            try:
                validate_text(text)
            except EngineError as exc:
                raise _labelled_voice_text_error(exc, label) from None
    if not any(c.isalnum() for c in text):
        raise ValueError(f'{label} chỉ có dấu hoặc ký hiệu, chưa có chữ/số để đọc. Sửa lời hoặc bỏ câu này trước khi tạo voice.')
    if engine in {'vieneu','vieneu_nano'}:
        unsupported=[c for c in text if c.isalpha() and 'LATIN' not in unicodedata.name(c,'')]
        if unsupported:
            sample=''.join(dict.fromkeys(unsupported))[:16]
            raise ValueError(f'{label} có chữ “{sample}” mà giọng VieNeu Việt/Anh không đọc được. Dịch lời sang ngôn ngữ giọng đọc, tự sửa lời hoặc chọn giọng quốc tế hỗ trợ ngôn ngữ gốc. Lời gốc được giữ nguyên.')
