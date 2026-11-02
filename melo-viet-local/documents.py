"""Lossless text planning, strict SRT recognition and bounded-memory WAV assembly."""
from dataclasses import dataclass
import html
import array
import math
import sys
from pathlib import Path
import re
import shutil
import subprocess
import wave

MAX_CHARS = 1_000_000
STYLES = {
    'friendly': {'name': 'Thân thiện · dễ nghe', 'speed': .98, 'pause_ms': 150, 'pitch': '+0Hz'},
    'neutral': {'name': 'Tự nhiên', 'speed': 1.0, 'pause_ms': 100, 'pitch': '+0Hz'},
    'story': {'name': 'Kể chuyện', 'speed': .96, 'pause_ms': 240, 'pitch': '+0Hz'},
    'review': {'name': 'Review phim', 'speed': 1.10, 'pause_ms': 80, 'pitch': '+0Hz'},
    'narration': {'name': 'Thuyết minh', 'speed': 1.0, 'pause_ms': 140, 'pitch': '+0Hz'},
    'news': {'name': 'Bản tin', 'speed': 1.06, 'pause_ms': 90, 'pitch': '+0Hz'},
    'calm': {'name': 'Nhẹ nhàng', 'speed': .90, 'pause_ms': 300, 'pitch': '+0Hz'},
}
TIMING = re.compile(r'^\s*(\d{1,3}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{1,3}):(\d{2}):(\d{2})[,.](\d{3})(?:\s+.*)?$')


def milliseconds(groups):
    h, m, s, ms = map(int, groups)
    if m > 59 or s > 59:
        raise ValueError('Mốc SRT có phút/giây vượt 59.')
    return ((h * 60 + m) * 60 + s) * 1000 + ms


def parse_document(text, name='Lời đọc.txt', requested='auto'):
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_CHARS or '\x00' in text:
        raise ValueError('Mỗi văn bản cần 1–1.000.000 ký tự, không chứa ký tự NUL.')
    if requested not in {'auto', 'txt', 'srt'}:
        raise ValueError('Định dạng phải là auto, txt hoặc srt.')
    normalized = text.lstrip('\ufeff').replace('\r\n', '\n').replace('\r', '\n')
    if not normalized.strip():
        raise ValueError('Nội dung không có lời đọc.')
    is_srt = requested == 'srt' or (requested == 'auto' and ('-->' in normalized or str(name).lower().endswith('.srt')))
    if not is_srt:
        return {'format': 'txt', 'text': normalized, 'cues': [], 'warnings': []}
    lines = normalized.split('\n')
    cues, i, previous_start = [], 0, -1
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        if lines[i].strip().isdigit():
            i += 1
        if i >= len(lines) or not (match := TIMING.fullmatch(lines[i])):
            raise ValueError(f'SRT sai mốc thời gian ở dòng {i + 1}; không đọc số thứ tự/mốc thành lời.')
        start = milliseconds(match.groups()[:4]); end = milliseconds(match.groups()[4:])
        if end <= start or start < previous_start:
            raise ValueError(f'SRT có mốc ngược hoặc sai thứ tự ở dòng {i + 1}.')
        previous_start = start
        i += 1
        body = []
        while i < len(lines) and lines[i].strip():
            body.append(lines[i]); i += 1
        spoken = re.sub(r'(?i)<br\s*/?>', '\n', '\n'.join(body))
        spoken = html.unescape(re.sub(r'<[^>]*>|\{\\[^}]*\}', '', spoken)).strip()
        if spoken:
            cues.append({'start_ms': start, 'end_ms': end, 'text': spoken})
    if not cues:
        raise ValueError('SRT không có lời đọc.')
    warnings = ['Mốc SRT xuất được tạo lại theo âm thanh thực; không ép lời vào mốc nhập và không căn từng từ.']
    if any(a['end_ms'] > b['start_ms'] for a, b in zip(cues, cues[1:])):
        warnings.append('SRT nhập có mốc chồng nhau; các câu được đọc theo thứ tự.')
    return {'format': 'srt', 'text': '\n'.join(c['text'] for c in cues), 'cues': cues, 'warnings': warnings}


def split_text(text, limit=480):
    """Keep every input character exactly once; prefer sentence/word boundaries."""
    if type(limit) is not int or not 80 <= limit <= 1200:
        raise ValueError('Độ dài đoạn cần từ 80 đến 1.200 ký tự.')
    pieces, start = [], 0
    while start < len(text):
        end = min(start + limit, len(text))
        if end < len(text):
            region = text[start:end]
            endings = [m.end() for m in re.finditer(r'[.!?。！？…]+(?:[\s\u3000]+|(?=[^\w]))|\n+', region)]
            choices = [p for p in endings if p >= limit // 3]
            if choices:
                end = start + choices[-1]
            else:
                spaces = [m.end() for m in re.finditer(r'\s+', region) if m.end() >= limit // 2]
                if spaces:
                    end = start + spaces[-1]
        pieces.append(text[start:end]); start = end
    return pieces


def plan_document(document, limit=480):
    sources = [c['text'] for c in document['cues']] if document['format'] == 'srt' else [document['text']]
    return [piece for source in sources for piece in split_text(source, limit) if piece.strip()]


def timestamp(seconds):
    total = max(0, round(seconds * 1000)); sec, ms = divmod(total, 1000)
    minute, sec = divmod(sec, 60); hour, minute = divmod(minute, 60)
    return f'{hour:02}:{minute:02}:{sec:02},{ms:03}'


def convert_audio(source, destination, speed=1.0, sample_rate=24000, gain_db=0.0):
    """Pitch-preserving atempo; unchanged native PCM bypasses the subprocess."""
    if not .5 <= speed <= 2.0:
        raise ValueError('Tốc độ đọc cần từ 0,5× đến 2×.')
    with wave.open(str(source), 'rb') as audio:
        compatible = audio.getparams()[:3] == (1, 2, sample_rate)
    if compatible and speed == 1.0 and gain_db==0:
        shutil.copyfile(source, destination)
        return
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', '-i', str(source),
               '-ac', '1', '-ar', str(sample_rate), '-c:a', 'pcm_s16le']
    filters=[]
    if speed!=1.0:filters.append(f'atempo={speed:.6f}')
    if gain_db:
        peak=0
        with wave.open(str(source),'rb') as audio:
            while block:=audio.readframes(65536):
                samples=array.array('h',block)
                if sys.byteorder!='little':samples.byteswap()
                peak=max(peak,max((abs(x) for x in samples),default=0))
        factor=min(10**(gain_db/20),max(1.0,.92*32767/max(1,peak)))
        filters.extend([f'volume={factor:.6f}','alimiter=limit=0.95:level=false'])
    if filters:command+=['-af',','.join(filters)]
    result = subprocess.run(command + [str(destination)], capture_output=True, timeout=180)
    if result.returncode:
        raise ValueError('Không đổi được tốc độ/định dạng WAV: ' + result.stderr.decode('utf-8', 'replace')[-600:])


class Assembler:
    """Write at most one hour per RIFF WAV; never hold a whole book in memory."""
    def __init__(self, folder, part_seconds=3600, sample_rate=24000):
        self.folder = Path(folder); self.rate=sample_rate; self.limit = int(part_seconds * self.rate)
        self.parts = []; self.part_starts = []; self.writer = None; self.part_subtitle = None; self.part_cues = 0; self.part_frames = 0; self.total_frames = 0; self.cue_count = 0
        self.subtitle = (self.folder / 'subtitles.srt.partial').open('w', encoding='utf-8')

    def append(self, path, text, pause_ms=0):
        with wave.open(str(path), 'rb') as audio:
            if audio.getparams()[:3] != (1, 2, self.rate) or audio.getnframes() == 0:
                raise ValueError('Đoạn âm thanh không phải PCM mono có cùng tần số lấy mẫu.')
            count = audio.getnframes()
            if self.writer is None or (self.part_frames and self.part_frames + count > self.limit):
                if self.writer:
                    self.writer.close()
                    self.part_subtitle.close()
                name = f'part-{len(self.parts) + 1:04}.wav'
                self.parts.append(name); self.writer = wave.open(str(self.folder / name), 'wb')
                self.writer.setparams((1, 2, self.rate, 0, 'NONE', 'not compressed')); self.part_frames = 0
                self.part_starts.append(self.total_frames / self.rate); self.part_cues = 0
                self.part_subtitle = (self.folder / name.replace('.wav','.srt')).open('w',encoding='utf-8')
            start = self.total_frames / self.rate
            while block := audio.readframes(32768):
                self.writer.writeframesraw(block)
            self.part_frames += count; self.total_frames += count
            self.cue_count += 1; self.part_cues += 1
            offset = self.part_starts[-1]
            self.part_subtitle.write(f'{self.part_cues}\n{timestamp(start-offset)} --> {timestamp(self.total_frames / self.rate-offset)}\n{text.strip()}\n\n')
            self.part_subtitle.flush()
            self.subtitle.write(f'{self.cue_count}\n{timestamp(start)} --> {timestamp(self.total_frames / self.rate)}\n{text.strip()}\n\n')
            silence = round(pause_ms * self.rate / 1000)
            if silence:
                self.writer.writeframesraw(b'\x00\x00' * silence)
                self.part_frames += silence; self.total_frames += silence
            self.writer.writeframes(b'')  # refresh header for safe preview after each chunk
            self.subtitle.flush()

    def finish(self):
        self.close()
        (self.folder / 'subtitles.srt.partial').replace(self.folder / 'subtitles.srt')
        return {'audio_seconds': self.total_frames / self.rate, 'sample_rate': self.rate, 'parts': self.parts, 'part_start_seconds': self.part_starts}

    def close(self):
        if self.writer:
            self.writer.close(); self.writer = None
        if self.part_subtitle and not self.part_subtitle.closed:
            self.part_subtitle.close()
        if not self.subtitle.closed:
            self.subtitle.close()
