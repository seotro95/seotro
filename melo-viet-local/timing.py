"""Pitch-preserving TXT/SRT timing with measured exports and bounded WAV parts."""
import html
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import wave

RATE = 48000
MAX_SECONDS = 7 * 24 * 3600


def timing_plan(document, mode='auto', target=None):
    if mode not in {'auto', 'exact', 'natural'}:
        raise ValueError('Chế độ thời gian không hợp lệ.')
    if target is not None and (type(target) not in {int, float} or not math.isfinite(target)
                               or target <= 0 or target > MAX_SECONDS or round(target*RATE) < 1):
        raise ValueError('Thời lượng đích cần lớn hơn 0, tối đa 7 ngày.')
    if mode == 'natural':
        if target is not None:
            raise ValueError('Đã nhập thời lượng đích: bật Giữ thời lượng TXT/SRT hoặc xóa thời lượng để đọc tự nhiên.')
        return None
    if document['format'] == 'srt':
        previous = 0
        for index, cue in enumerate(document['cues'], 1):
            if cue['start_ms'] < previous:
                raise ValueError(f'Câu SRT {index}: mốc chồng nhau. Sửa mốc trước khi tạo voice.')
            previous = cue['end_ms']
            if cue['text'] and not any(c.isalnum() for c in cue['text']):
                raise ValueError(f'Câu SRT {index} chỉ có ký hiệu, chưa có lời để đọc.')
        seconds = document['cues'][-1]['end_ms']/1000
        if seconds > MAX_SECONDS:
            raise ValueError('SRT dài quá 7 ngày.')
        if target is not None and round(target*RATE) != round(seconds*RATE):
            raise ValueError('SRT lấy thời lượng từ mốc cuối; TXT nhập cùng mốc này. Xóa thời lượng TXT khi nhập SRT khác.')
        cues = document['cues']
    elif target is not None:
        seconds = target
        cues = [{'start_ms': 0, 'end_ms': seconds*1000, 'text': document['text']}]
    elif mode == 'exact':
        raise ValueError('TXT chưa có mốc: nhập thời lượng đích, ví dụ 10:00.')
    else:
        return None
    return {'target_seconds': seconds, 'target_frames': round(seconds*RATE),
            'source_format': document['format'], 'cues': cues}


def run_audio(command, log, event=None, timeout=600):
    log = Path(log)
    with log.open('wb') as errors:
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=errors,
                                   start_new_session=True)
        started = time.monotonic()
        try:
            while process.poll() is None:
                if event is not None and event.wait(.1):
                    raise InterruptedError('Đã dừng căn thời lượng.')
                if event is None:
                    time.sleep(.1)
                if time.monotonic()-started > timeout:
                    raise ValueError('Căn âm thanh quá thời gian xử lý; hãy chia nhỏ kịch bản.')
            if process.returncode:
                raise ValueError('Không xử lý được âm thanh: '+log.read_text(errors='replace')[-600:])
        finally:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)


def verify_parts(folder, parts, rate, expected=None):
    frames = 0
    signal_found = False
    for name in parts:
        with wave.open(str(Path(folder)/name), 'rb') as source:
            if source.getparams()[:3] != (1, 2, rate):
                raise ValueError('WAV xuất ra sai định dạng.')
            actual = 0
            while block := source.readframes(65536):
                actual += len(block)//2
                signal_found = signal_found or any(block)
            if actual != source.getnframes() or not actual:
                raise ValueError('WAV bị thiếu mẫu âm thanh.')
            frames += actual
    if not signal_found:
        raise ValueError('File voice chỉ có im lặng; hãy thử lại hoặc chọn giọng hỗ trợ ngôn ngữ.')
    if expected is not None and frames != expected:
        raise ValueError('File voice thực tế chưa đúng thời lượng đích; tool chưa công bố bản thu.')
    return {'verified': True, 'sample_rate': rate, 'sample_frames': frames,
            'audio_seconds': frames/rate, 'target_seconds': expected/rate if expected is not None else None,
            'error_frames': frames-expected if expected is not None else None}


class PCMParts:
    def __init__(self, folder, rate=RATE, part_seconds=3600):
        self.folder, self.rate = Path(folder), rate
        self.limit = round(rate*part_seconds)
        if self.limit < 1:
            raise ValueError('Giới hạn phần WAV quá ngắn.')
        self.parts, self.starts = [], []
        self.file = None
        self.frames = self.part_frames = 0

    def open_part(self):
        if self.file is not None:
            self.file.close()
        name = f'part-{len(self.parts)+1:04}.wav'
        self.parts.append(name)
        self.starts.append(self.frames)
        self.file = wave.open(str(self.folder/name), 'wb')
        self.file.setparams((1, 2, self.rate, 0, 'NONE', 'not compressed'))
        self.part_frames = 0

    def write(self, block):
        if len(block) % 2:
            raise ValueError('PCM không đủ một mẫu âm thanh.')
        offset = 0
        while offset < len(block):
            if self.file is None or self.part_frames == self.limit:
                self.open_part()
            count = min((len(block)-offset)//2, self.limit-self.part_frames)
            self.file.writeframesraw(block[offset:offset+count*2])
            offset += count*2
            self.frames += count
            self.part_frames += count

    def silence_to(self, frame, event=None):
        if self.frames > frame:
            raise ValueError('Lời đọc vượt mốc; tool không cắt mất từ.')
        while self.frames < frame:
            if event is not None and event.is_set():
                raise InterruptedError('Đã dừng.')
            self.write(b'\0\0'*min(65536, frame-self.frames))

    def close(self):
        if self.file is not None:
            self.file.close()
            self.file = None


class TimedAssembler:
    def __init__(self, folder, plan, event=None, part_seconds=3600, max_tempo=2, progress=None):
        self.folder, self.plan, self.event = Path(folder), plan, event
        self.rate, self.max_tempo = RATE, max_tempo
        self.progress = progress
        self.temp = self.folder/'.timing'
        self.temp.mkdir()
        self.output = self.temp/'out'
        self.output.mkdir()
        self.units = []
        self.writer = PCMParts(self.output, part_seconds=part_seconds)

    def append(self, path, text, pause_ms=0, cue=None):
        index = len(self.units)
        destination = self.temp/f'unit-{index:06}.wav'
        with wave.open(str(path), 'rb') as source, wave.open(str(destination), 'wb') as target:
            if source.getparams()[:3] != (1, 2, RATE):
                raise ValueError('Căn thời gian cần WAV mono 24 kHz.')
            target.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
            count = 0
            while block := source.readframes(65536):
                target.writeframesraw(block)
                count += len(block)//2
            if count != source.getnframes() or count == 0:
                raise ValueError('Đoạn voice thiếu mẫu âm thanh.')
            pause = max(0, round(pause_ms*RATE/1000))
            remaining = pause
            while remaining:
                block = min(65536, remaining)
                target.writeframesraw(b'\0\0'*block)
                remaining -= block
        self.units.append({'path': destination, 'frames': count+pause, 'text': text,
                           'cue': cue if self.plan['source_format'] == 'srt' else 0})

    def fit(self, units, frames, cue_number):
        total = sum(unit['frames'] for unit in units)
        if not total:
            return None, 0, 1
        ratio = total/frames
        if ratio > self.max_tempo+1e-9:
            raise ValueError(f'Câu/đoạn {cue_number}: lời dài {total/RATE:.2f}s cho ô {frames/RATE:.2f}s, cần {ratio:.2f}× vượt {self.max_tempo:g}×. Tăng thời lượng hoặc sửa lời; tool không cắt mất nội dung.')
        listing = self.temp/'sources.ffconcat'
        listing.write_text('ffconcat version 1.0\n'+''.join(
            "file '"+str(unit['path'].resolve()).replace("'","'\\''")+"'\n" for unit in units), encoding='utf-8')
        pcm = self.temp/'fitted.pcm'
        tempo = max(.65, ratio)
        for attempt in range(7):
            if self.event is not None and self.event.is_set():
                raise InterruptedError('Đã dừng.')
            command = ['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
                       '-f','concat','-safe','0','-protocol_whitelist','file,pipe','-i',str(listing),
                       '-vn','-ac','1','-ar',str(RATE),'-af',f'atempo={tempo:.12g}',
                       '-c:a','pcm_s16le','-f','s16le',str(pcm)]
            run_audio(command, self.temp/'fit.log', self.event,
                      timeout=max(180, min(21600, total/RATE*2)))
            size = pcm.stat().st_size
            if size % 2 or not size:
                raise ValueError(f'Câu/đoạn {cue_number}: không tạo được lời khi căn tốc độ.')
            actual = size//2
            if actual <= frames:
                return pcm, actual, tempo
            if tempo >= self.max_tempo or attempt == 6:
                raise ValueError(f'Câu/đoạn {cue_number}: vẫn vượt ô ở tốc độ tối đa; hãy tăng thời lượng. Không cắt lời.')
            tempo = min(self.max_tempo, tempo*actual/frames*1.002)
        raise AssertionError('unreachable')

    def finish(self):
        from documents import timestamp
        captions, report = [], []
        groups = {}
        for unit in self.units:
            groups.setdefault(unit['cue'], []).append(unit)
        for index, cue in enumerate(self.plan['cues']):
            start, end = round(cue['start_ms']*RATE/1000), round(cue['end_ms']*RATE/1000)
            units = groups.get(index, [])
            pcm, speech, tempo = self.fit(units, end-start, index+1)
            self.writer.silence_to(start, self.event)
            if pcm is not None:
                with pcm.open('rb') as source:
                    while block := source.read(131072):
                        if self.event is not None and self.event.is_set():
                            raise InterruptedError('Đã dừng.')
                        self.writer.write(block)
            self.writer.silence_to(end, self.event)
            if self.plan['source_format'] == 'srt':
                captions.append((start, end, cue['text']))
            else:
                raw = sum(unit['frames'] for unit in units)
                prefix = 0
                for position, unit in enumerate(units):
                    begin = start+round(prefix*speech/raw)
                    prefix += unit['frames']
                    finish = end if position == len(units)-1 else start+round(prefix*speech/raw)
                    captions.append((begin, max(begin+1, finish), unit['text']))
            report.append({'cue': index+1, 'start_frame': start, 'end_frame': end,
                           'speech_frames': speech, 'tempo': tempo, 'padding_frames': end-start-speech})
            if self.progress is not None:
                self.progress(index+1, len(self.plan['cues']))
        self.writer.silence_to(self.plan['target_frames'], self.event)
        self.writer.close()
        duration = verify_parts(self.output, self.writer.parts, RATE, self.plan['target_frames'])
        def srt(cues):
            return ''.join(f'{i}\n{timestamp(a/RATE)} --> {timestamp(b/RATE)}\n{html.escape(text.strip(), quote=False)}\n\n'
                           for i, (a,b,text) in enumerate(cues, 1))
        (self.output/'subtitles.srt').write_text(srt(captions), encoding='utf-8')
        for index, (name, start) in enumerate(zip(self.writer.parts, self.writer.starts)):
            end = self.writer.starts[index+1] if index+1 < len(self.writer.starts) else self.writer.frames
            clipped = [(max(a,start)-start,min(b,end)-start,text) for a,b,text in captions if a < end and b > start]
            (self.output/name.replace('.wav','.srt')).write_text(srt(clipped), encoding='utf-8')
        if self.event is not None and self.event.is_set():
            raise InterruptedError('Đã dừng.')
        for path in self.output.iterdir():
            path.replace(self.folder/path.name)
        result = {'audio_seconds': duration['audio_seconds'], 'sample_rate': RATE,
                  'parts': self.writer.parts, 'part_start_seconds': [frame/RATE for frame in self.writer.starts],
                  'timing_mode': 'exact', 'target_seconds': self.plan['target_seconds'],
                  'duration_verified': True, 'duration_report': duration,
                  'sync_ok': True, 'sync_report': {'complete': True, 'cues': report,
                      'target_seconds': self.plan['target_seconds'], 'actual_seconds': duration['audio_seconds'],
                      'error_frames': 0, 'sample_rate': RATE}}
        shutil.rmtree(self.temp)
        return result

    def close(self):
        self.writer.close()
        shutil.rmtree(self.temp, ignore_errors=True)


def measure_encoded(path, folder, rate, expected=None, event=None):
    temporary = Path(folder)/'verify-export.pcm'
    try:
        run_audio(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
                   '-i',str(path),'-vn','-ac','1','-ar',str(rate),'-c:a','pcm_s16le','-f','s16le',str(temporary)],
                  Path(folder)/'verify-export.log', event, timeout=3600)
        if event is not None and event.is_set():
            raise InterruptedError('Đã dừng xuất MP3.')
        size = temporary.stat().st_size
        if not size or size % 2:
            raise ValueError('MP3 không giải mã được thành mẫu âm thanh.')
        frames = size//2
        if expected is not None and frames != expected:
            raise ValueError('Thời lượng MP3 thực tế không khớp; WAV gốc được giữ để xuất lại.')
        return {'verified': True, 'sample_frames': frames, 'sample_rate': rate,
                'audio_seconds': frames/rate, 'error_frames': frames-expected if expected is not None else None}
    finally:
        temporary.unlink(missing_ok=True)
