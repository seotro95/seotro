"""Separate character assignments from timed narration and freeze voice identity."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from hmong_assets import HMONG_ENGINES, is_builtin_voice_id, reference_text_required


MAX_CHARACTERS = 32
_CHARACTER_ID = re.compile(r'[A-Za-z0-9_-]{1,64}\Z')
_VOICE_ID = re.compile(r'[A-Za-z0-9_-]{1,128}\Z')
_FINGERPRINT = re.compile(r'[0-9a-f]{64}\Z')


def is_preset_voice(voice):
    """A preset name in legacy personal metadata must never override its WAV."""
    speaker = voice.get('speaker')
    return (voice.get('category') != 'cloned' and is_builtin_voice_id(speaker)
            and voice.get('voice_id', voice.get('id')) == speaker)


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


def validate_cast_request(character_voices, cue_characters, cue_count):
    """Validate the public array contract; null cues use the selected base voice."""
    if not isinstance(character_voices, dict) or len(character_voices) > MAX_CHARACTERS:
        raise ValueError('Mỗi kịch bản có tối đa 32 nhân vật.')
    for character, voice_id in character_voices.items():
        if not isinstance(character, str) or not _CHARACTER_ID.fullmatch(character):
            raise ValueError('Mã nhân vật cần 1–64 chữ, số, dấu gạch ngang hoặc gạch dưới.')
        if not isinstance(voice_id, str) or not _VOICE_ID.fullmatch(voice_id):
            raise ValueError('Chọn giọng hợp lệ cho từng nhân vật.')
    if not isinstance(cue_characters, list) or len(cue_characters) != cue_count:
        raise ValueError('Danh sách nhân vật cần khớp chính xác số câu SRT.')
    for character in cue_characters:
        if character is not None and (not isinstance(character, str) or character not in character_voices):
            raise ValueError('Mỗi câu SRT cần dùng nhân vật đã khai báo hoặc giọng mặc định.')
    return cue_characters


def reference_identity(voice, data):
    """Hash verified preset audio or a personal WAV and its exact reference words."""
    voice_id = voice.get('id', voice.get('voice_id'))
    if is_preset_voice({**voice, 'voice_id': voice_id}):
        from hmong_assets import reference_fingerprint
        return reference_fingerprint(voice['speaker'])
    if not isinstance(voice_id, str) or not _VOICE_ID.fullmatch(voice_id):
        raise ValueError('Không tìm thấy mẫu giọng nhân vật hợp lệ.')
    audio_hash = hashlib.sha256()
    with (Path(data) / 'voices' / (voice_id + '.wav')).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            audio_hash.update(block)
    return _digest({'version': 1, 'audio_sha256': audio_hash.hexdigest(),
                    'transcript': voice.get('transcript', voice.get('reference_text', ''))})


def make_voice_snapshot(voice, engine, language, data):
    """Resolve one immutable Hmong voice; validation errors and IO errors propagate."""
    if (engine not in HMONG_ENGINES or voice.get('engine') != engine
            or language != 'mww' or language not in voice.get('languages', [])):
        raise ValueError('Giọng nhân vật cần hỗ trợ Hmong Trắng và cùng mô hình Hmong.')
    voice_id = voice.get('id', voice.get('voice_id'))
    if not isinstance(voice_id, str) or not _VOICE_ID.fullmatch(voice_id):
        raise ValueError('Không tìm thấy giọng nhân vật hợp lệ.')
    voice = {**voice, 'voice_id': voice_id}
    # Older imported personal profiles can carry a copied preset `speaker`.
    # Keep their stored JSON intact, but freeze their own audio for new jobs.
    if not is_preset_voice(voice):
        voice = {**voice, 'speaker': None}
    if is_preset_voice(voice):
        from hmong_assets import reference
        _, words = reference(voice['speaker'])
    else:
        words = voice.get('transcript', '')
    audio_reference = not reference_text_required(voice.get('speaker'), engine)
    if not isinstance(words, str) or (not audio_reference and not words.strip()) or len(words) > 2000:
        raise ValueError('Nhập đúng lời Hmong của mẫu giọng nhân vật, tối đa 2.000 ký tự.')
    from narration import validate_voice_text
    if not audio_reference:
        validate_voice_text(words, engine, 'Lời mẫu tham chiếu nhân vật')
    return {'voice_id': voice_id, 'voice_name': voice.get('name', voice_id),
            'engine': engine, 'speaker': voice.get('speaker'), 'language': language,
            'reference_text': words, 'hmong_reference_fingerprint': reference_identity(voice, data)}


def validate_cast(job):
    """Validate saved jobs independently of mutable profile metadata."""
    cast = job.get('character_cast')
    if cast is None:
        return None
    if not isinstance(cast, dict) or type(cast.get('version')) is not int or cast['version'] != 1:
        raise ValueError('Phiên bản phân vai không hợp lệ; tạo tác vụ mới.')
    if (job.get('input_format') != 'srt' or job.get('subtitle_timing', True) is False
            or job.get('engine') not in HMONG_ENGINES or job.get('language') != 'mww'):
        raise ValueError('Phân vai nhân vật cần kịch bản SRT Hmong Trắng.')
    voices = cast.get('voices')
    if not isinstance(voices, dict) or not voices:
        raise ValueError('Chưa lưu giọng cho nhân vật; tạo tác vụ mới.')
    from subtitles import parse_srt
    validate_cast_request({key: value.get('voice_id') if isinstance(value, dict) else None
                           for key, value in voices.items()}, cast.get('cues'), len(parse_srt(job['text'])))
    snapshots = [cast.get('default_voice'), *voices.values()]
    for voice in snapshots:
        _validate_snapshot(voice, job)
    return cast


def _validate_snapshot(voice, job):
    if (not isinstance(voice, dict) or voice.get('engine') not in HMONG_ENGINES
            or voice.get('engine') != job.get('engine')
            or (voice.get('speaker') is not None and not is_preset_voice(voice))
            or voice.get('language') != 'mww' or voice.get('language') != job.get('language')
            or not isinstance(voice.get('voice_id'), str) or not _VOICE_ID.fullmatch(voice['voice_id'])
            or not isinstance(voice.get('hmong_reference_fingerprint'), str)
            or not _FINGERPRINT.fullmatch(voice['hmong_reference_fingerprint'])
            or not isinstance(voice.get('reference_text'), str)
            or (not voice['reference_text'].strip()
                and reference_text_required(voice.get('speaker'), job.get('engine')))
            or len(voice['reference_text']) > 2000):
        raise ValueError('Danh tính mẫu giọng nhân vật chưa đầy đủ hoặc khác mô hình; tạo tác vụ mới.')
    from narration import validate_voice_text
    if reference_text_required(voice.get('speaker'), job['engine']):
        validate_voice_text(voice['reference_text'], job['engine'], 'Lời mẫu tham chiếu nhân vật')


def cast_voice_ids(job):
    """Include every frozen profile when guarding deletion of queued/running jobs."""
    result = {job['voice_id']} if job.get('voice_id') else set()
    cast = job.get('character_cast')
    if isinstance(cast, dict):
        voices = cast.get('voices', {})
        snapshots = list(voices.values()) if isinstance(voices, dict) else []
        snapshots.append(cast.get('default_voice'))
        result.update(voice['voice_id'] for voice in snapshots
                      if isinstance(voice, dict) and isinstance(voice.get('voice_id'), str))
    return result


def validate_cast_references(job, data):
    """Fail before checkpoint/output mutation if any cast recording or words changed."""
    cast = validate_cast(job)
    if cast is None:
        return
    _validate_references([cast['default_voice'], *cast['voices'].values()], data)


def validate_job_references(job, data):
    """Verify every frozen Hmong reference before resuming or changing output."""
    if (job.get('engine') in HMONG_ENGINES
            and is_builtin_voice_id(job.get('speaker'))
            and not is_preset_voice(job)):
        raise ValueError('Tác vụ cũ đã gắn giọng cá nhân với giọng mặc định. '
                         'Tạo tác vụ mới bằng hồ sơ giọng cá nhân; các đoạn cũ được giữ nguyên.')
    cast = validate_cast(job)
    snapshots = [cast['default_voice'], *cast['voices'].values()] if cast else []
    base = job.get('hmong_voice_snapshot')
    if base is not None:
        _validate_snapshot(base, job)
        if (base['voice_id'] != job.get('voice_id') or base.get('speaker') != job.get('speaker')
                or base['hmong_reference_fingerprint'] != job.get('hmong_reference_fingerprint')):
            raise ValueError('Danh tính mẫu giọng đã thay đổi; tạo tác vụ mới.')
        snapshots.append(base)
    _validate_references(snapshots, data)


def _validate_references(snapshots, data):
    seen = set()
    for voice in snapshots:
        key = (voice['voice_id'], voice.get('speaker'), voice['hmong_reference_fingerprint'],
               voice['reference_text'])
        if key in seen:
            continue
        seen.add(key)
        try:
            if is_preset_voice(voice):
                current = reference_identity(voice, data)
                from hmong_assets import reference
                _, words = reference(voice['speaker'])
            else:
                record = json.loads((Path(data) / 'voices' / (voice['voice_id'] + '.json')).read_text(encoding='utf-8'))
                if not isinstance(record, dict):
                    raise ValueError('Hồ sơ giọng không hợp lệ.')
                words = record.get('transcript', '')
                current = reference_identity({'voice_id': voice['voice_id'], 'transcript': words}, data)
        except (OSError, ValueError, TypeError):
            current, words = None, None
        if current != voice['hmong_reference_fingerprint'] or words != voice['reference_text']:
            raise ValueError('Mẫu giọng nhân vật đã thay đổi hoặc không còn. Tạo tác vụ mới bằng giọng hiện tại; '
                             'các đoạn đã tạo vẫn được giữ nguyên.')


def settings_for_cue(job, cue):
    cast = job.get('character_cast')
    if not cast:
        return job
    character = cast['cues'][cue]
    voice = cast['voices'][character] if character is not None else cast['default_voice']
    return {**job, **voice, 'character_id': character}


def checkpoint_identity(job, segment):
    """Bind cast checkpoints to spoken text, resolved voice, and audio controls."""
    settings = settings_for_cue(job, segment.cue)
    keys = ('engine', 'voice_id', 'speaker', 'language', 'quality', 'nano_steps', 'nano_threads',
            'hmong_steps', 'hmong_reference_fingerprint', 'reference_text', 'speed', 'delivery',
            'segment_plan', 'emotion', 'emotion_strength', 'auto_rhythm', 'hmong_phrase_context')
    if settings.get('engine') == 'hmong_native' and settings.get('hmong_audio_profile') not in (None, 'legacy-v1'):
        keys += ('hmong_audio_profile',)
    if settings.get('require_complete_audio') is True:
        keys += ('require_complete_audio',)
    cast = job['character_cast']
    references = {character: voice['hmong_reference_fingerprint']
                  for character, voice in cast['voices'].items()}
    return _digest({'version': 1, 'text': segment.text, 'cue': segment.cue,
                    'emphasis': segment.emphasis, 'emotion': segment.emotion,
                    'pause': segment.pause, 'rhythm_pause': segment.rhythm_pause,
                    'voice': {key: settings.get(key) for key in keys},
                    'references': references,
                    'default_reference': cast['default_voice']['hmong_reference_fingerprint']})
