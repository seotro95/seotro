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
    return segments


def plan_segments(job):
    if job.get('segment_plan') != 'nano-packed-v1':
        return split_script(job['text'])
    # Packing is opt-in with zero added sentence gap; explicit pauses/emphasis stay barriers.
    source = split_script(job['text'], limit=130)
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
