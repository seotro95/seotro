"""Bounded chunks and disk-streamed PCM assembly for up to three hours."""
import re
import wave
from dataclasses import dataclass

MAX_SECONDS = 3 * 60 * 60
MAX_CHARACTERS = 200_000
PROFILES = {'natural': (1.0, 0.22), 'story': (0.94, 0.5), 'news': (1.04, 0.25), 'calm': (0.88, 0.65), 'energetic': (1.12, 0.16)}


@dataclass
class Segment:
    text: str = ''
    pause: float = 0
    emphasis: bool = False
    cue: int | None = None


def spoken_text(text):
    """Remove line-leading caption clocks, never numbers inside spoken prose."""
    clock = r'(?:\d{1,3}:)?\d{1,2}:[0-5]\d(?:[.,]\d{1,3})?'
    timing = re.compile(r'^\s*' + clock + r'\s*-->\s*' + clock + r'(?:\s+.*)?$')
    leading = re.compile(r'^\s*(?:\[' + clock + r'\]|\(' + clock + r'\)|' + clock + r')(?=\s|$)\s*(?:[-–—|]\s*)?')
    lines = text.replace('\r\n', '\n').split('\n')
    output = []
    for index, line in enumerate(lines):
        if timing.fullmatch(line):
            continue
        if line.strip().isdigit() and index + 1 < len(lines) and timing.fullmatch(lines[index + 1]):
            continue  # SRT cue index immediately before its timing line.
        output.append(leading.sub('', line))
    return '\n'.join(output)


def split_script(text, limit=240):
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
        # Include newlines in splitting to retain paragraph breathing space.
        for sentence in re.split(r'(?<=[!?。！？;；])\s*|(?<=\.)(?!\d)\s+|\n+', part):
            sentence = sentence.strip()
            while sentence:
                end = min(limit, len(sentence))
                if end < len(sentence):
                    boundary = sentence.rfind(' ', 0, end)
                    if boundary > end // 2:
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


def plan_segments(job):
    if job.get('input_format') == 'srt':
        from subtitles import parse_srt
        output = []
        for index, cue in enumerate(parse_srt(job['text'])):
            segments = split_script(cue['text'], limit=130 if job.get('engine') == 'vieneu_nano' else 240)
            if not any(s.text for s in segments):
                raise ValueError('Mỗi câu SRT cần có lời đọc.')
            for segment in segments:
                segment.cue = index
                output.append(segment)
        return output
    text = spoken_text(job['text']) if job.get('skip_timestamps', True) else job['text']
    if job.get('segment_plan') != 'nano-packed-v1':
        return split_script(text)
    # Packing is opt-in with zero added sentence gap; explicit pauses/emphasis stay barriers.
    source = split_script(text, limit=130)
    packed = []
    for segment in source:
        if segment.text and packed and packed[-1].text and not segment.emphasis and not packed[-1].emphasis and len(packed[-1].text) + 1 + len(segment.text) <= 130:
            packed[-1].text += ' ' + segment.text
        else:
            packed.append(segment)
    return packed


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


def validate_voice_text(text,engine,label='Nội dung'):
    import unicodedata
    if not any(c.isalnum() for c in text):
        raise ValueError(f'{label} chỉ có dấu hoặc ký hiệu, chưa có chữ/số để đọc. Sửa lời hoặc bỏ câu này trước khi tạo voice.')
    if engine in {'vieneu','vieneu_nano'}:
        unsupported=[c for c in text if c.isalpha() and 'LATIN' not in unicodedata.name(c,'')]
        if unsupported:
            sample=''.join(dict.fromkeys(unsupported))[:16]
            raise ValueError(f'{label} có chữ “{sample}” mà giọng VieNeu Việt/Anh không đọc được. Dịch lời sang ngôn ngữ giọng đọc, tự sửa lời hoặc chọn giọng quốc tế hỗ trợ ngôn ngữ gốc. Lời gốc được giữ nguyên.')
