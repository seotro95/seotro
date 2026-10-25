import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pytest
import soundfile as sf
from fastapi import HTTPException

import audio_import
import builtin_references
import custom_references as refs


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv('HMONG_STUDIO_DATA_DIR', str(tmp_path / 'data'))


def encode(tmp_path, suffix, codec, seconds=4):
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        pytest.skip('Real codec test requires FFmpeg')
    path = tmp_path / ('sample.' + suffix)
    command = [ffmpeg, '-nostdin', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i',
               'sine=frequency=250:sample_rate=48000', '-t', str(seconds), '-ac', '1', '-c:a', codec, str(path)]
    subprocess.run(command, check=True, capture_output=True, timeout=30)
    return path


@pytest.mark.parametrize('suffix,codec', [('m4a', 'aac'), ('aac', 'aac'), ('mp4', 'aac'), ('webm', 'libopus')])
def test_phone_and_video_audio_import_normalizes_real_media_and_keeps_transcript(tmp_path, suffix, codec):
    original = encode(tmp_path, suffix, codec)
    upload = tmp_path / 'upload.bin'
    shutil.copyfile(original, upload)
    ident = refs.register(upload, 'Giọng điện thoại', '../../phone.' + suffix)
    source = refs.original(ident)
    info = sf.info(str(source))
    assert source.name == 'source.wav'
    assert info.channels == 1 and info.samplerate == 24000 and 4 <= info.duration < 4.2
    assert np.max(np.abs(sf.read(str(source))[0])) > .01
    metadata = json.loads((source.parent / 'metadata.json').read_text())
    assert metadata['converted'] is True and metadata['original_name'] == 'phone.' + suffix
    settings = builtin_references.ReferenceSettings(start=0, end=4, text='The exact words in the original recording.')
    refs.save(ident, settings)
    selected, transcript = refs.selected(ident)
    assert transcript == settings.text
    assert sf.info(str(selected)).frames == 4 * 24000
    assert refs.list_ids() == [ident]


def test_overlong_compressed_recording_is_rejected_instead_of_truncated(tmp_path):
    original = encode(tmp_path, 'm4a', 'aac', seconds=602)
    with pytest.raises(HTTPException) as error:
        refs.register(original, 'Too long', original.name)
    assert error.value.status_code == 422
    assert refs.list_ids() == []
    assert not list(refs.directory().glob('.upload-*'))


def test_decoder_command_disallows_network_inputs_and_limits_output(tmp_path, monkeypatch):
    source = tmp_path / 'my (phone) sample.m4a'
    source.write_bytes(b'fixture')
    destination = tmp_path / 'source.wav'
    seen = []
    monkeypatch.setattr(audio_import, 'ffmpeg_executable', lambda: '/packaged/ffmpeg')
    def run(command, **options):
        seen.append((command, options))
        sf.write(str(destination), np.ones(24000 * 4) * .1, 24000, subtype='PCM_16')
    monkeypatch.setattr(audio_import.subprocess, 'run', run)
    audio_import.decode_to_wav(source, destination)
    command, options = seen[0]
    assert command[0] == '/packaged/ffmpeg'
    assert command[command.index('-protocol_whitelist') + 1] == 'file,pipe'
    assert command[command.index('-t') + 1] == '601'
    assert command[command.index('-i') + 1] == str(source.resolve())
    assert command[command.index('-map') + 1] == '0:a:0'
    assert options['timeout'] == 120 and options.get('shell', False) is False


def test_missing_packaged_and_system_decoder_has_actionable_error(monkeypatch):
    monkeypatch.setitem(sys.modules, 'imageio_ffmpeg', None)
    monkeypatch.setattr(audio_import.shutil, 'which', lambda _: None)
    with pytest.raises(audio_import.DecoderUnavailable, match='MO_HMONG_NHANH'):
        audio_import.ffmpeg_executable()


def test_timeout_removes_partial_decoded_recording(tmp_path, monkeypatch):
    source, destination = tmp_path / 'source.m4a', tmp_path / 'result.wav'
    source.write_bytes(b'fixture')
    monkeypatch.setattr(audio_import, 'ffmpeg_executable', lambda: '/packaged/ffmpeg')
    def run(*args, **kwargs):
        destination.write_bytes(b'partial')
        raise subprocess.TimeoutExpired(args[0], kwargs['timeout'])
    monkeypatch.setattr(audio_import.subprocess, 'run', run)
    with pytest.raises(audio_import.AudioImportError, match='quá lâu'):
        audio_import.decode_to_wav(source, destination)
    assert not destination.exists()


def test_video_without_audio_and_untrusted_playlist_are_rejected(tmp_path):
    playlist = tmp_path / 'playlist.m3u8'
    playlist.write_text('#EXTM3U\n#EXTINF:4,\nhttps://example.invalid/private\n')
    with pytest.raises(HTTPException) as error:
        refs.register(playlist, 'Not audio', 'pretend.m4a')
    assert error.value.status_code == 422
    assert refs.list_ids() == []
