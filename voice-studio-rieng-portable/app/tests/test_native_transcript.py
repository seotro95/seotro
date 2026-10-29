"""Private ASR cache integrity and isolated, strictly offline inference."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import wave

import pytest

import native_transcript as transcript


def write_reference(path, *, sample=b'\x10\x00', width=2):
    with wave.open(str(path), 'wb') as output:
        output.setparams((1, width, 24000, 0, 'NONE', 'not compressed'))
        output.writeframes(sample * 72000)


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    data = tmp_path/'data'
    model = data/'models/native-asr'
    model.mkdir(parents=True)
    entries = []
    for name in sorted(transcript.ASR_FILES):
        content = ('synthetic test file '+name).encode()
        (model/name).write_bytes(content)
        entries.append({'name': name, 'size': len(content), 'sha256': hashlib.sha256(content).hexdigest()})
    record = {'schema': 1, 'repository': transcript.ASR_REPOSITORY,
              'revision': transcript.ASR_REVISION, 'package': 'faster-whisper',
              'version': transcript.ASR_VERSION, 'files': entries}
    manifest = model/'VOICE-STUDIO-ASR.json'
    manifest.write_text(json.dumps(record))
    reference = tmp_path/'private-reference.wav'
    write_reference(reference)
    dependencies = tmp_path/'runtime-native/asr'
    dependencies.mkdir(parents=True)
    monkeypatch.setenv('VOICE_STUDIO_NATIVE_ROOT', str(dependencies.parent))
    return data, reference, manifest, dependencies


def request_for(data, reference, language='fr'):
    return {'reference': str(reference), 'data': str(data), 'language': language,
            'reference_sha256': transcript._reference_metadata(reference)[1],
            'asr_manifest_sha256': transcript._asr_manifest(data)[2]}


def install_synthetic_child(monkeypatch, text='Bonjour, voici une voix de test.'):
    calls = []
    def run(args, **options):
        request = json.loads(options['input'])
        calls.append((args, options, request))
        return SimpleNamespace(returncode=0, stdout=json.dumps({
            'ok': True, 'text': text, 'language': request['language'],
            'reference_sha256': request['reference_sha256'],
            'asr_manifest_sha256': request['asr_manifest_sha256']}))
    monkeypatch.setattr(transcript.subprocess, 'run', run)
    return calls


def test_existing_transcript_needs_no_model_dependencies_or_audio(tmp_path, monkeypatch):
    monkeypatch.setattr(transcript.subprocess, 'run', lambda *a, **k: pytest.fail('supplied transcript must skip ASR'))
    assert transcript.reference_transcript(tmp_path/'missing.wav', tmp_path, 'fr', '  Texte original.  ') == 'Texte original.'


def test_missing_transcript_is_private_offline_isolated_and_cached(prepared, monkeypatch):
    data, reference, _, _ = prepared
    original = reference.read_bytes()
    calls = install_synthetic_child(monkeypatch)
    expected = 'Bonjour, voici une voix de test.'
    assert transcript.reference_transcript(reference, data, 'fr') == expected
    assert transcript.reference_transcript(reference, data, 'fr') == expected
    assert len(calls) == 1 and reference.read_bytes() == original
    args, options, request = calls[0]
    assert args[:2] == [sys.executable, '-s'] and args[-1] == '--transcribe'
    assert str(reference) not in args and expected not in args
    assert request['reference'] == str(reference) and options['timeout'] == 300
    assert options['env']['HF_HUB_OFFLINE'] == options['env']['TRANSFORMERS_OFFLINE'] == '1'
    assert 'PYTHONPATH' not in options['env'] and 'PYTHONHOME' not in options['env']
    cached = json.loads(next((data/'cache/native-transcripts').glob('*.json')).read_text())
    assert cached['source'] == 'local_machine_transcription' and cached['local_only'] is True
    assert cached['text'] == expected and cached['asr_revision'] == transcript.ASR_REVISION


@pytest.mark.parametrize('change', ['audio', 'language', 'manifest', 'cache_identity'])
def test_cache_identity_tracks_exact_reference_language_and_asr_manifest(prepared, monkeypatch, change):
    data, reference, manifest, _ = prepared
    calls = install_synthetic_child(monkeypatch)
    transcript.reference_transcript(reference, data, 'fr')
    language = 'fr'
    if change == 'audio':
        write_reference(reference, sample=b'\x20\x00')
    elif change == 'language':
        language = 'ja'
    elif change == 'manifest':
        record = json.loads(manifest.read_text())
        record['build'] = 'different verified preparation'
        manifest.write_text(json.dumps(record))
    else:
        cache = next((data/'cache/native-transcripts').glob('*.json'))
        record = json.loads(cache.read_text())
        record['reference_sha256'] = '0'*64
        cache.write_text(json.dumps(record))
    transcript.reference_transcript(reference, data, language)
    assert len(calls) == 2


@pytest.mark.parametrize(('width', 'sample'), [(1, b'\x80'), (2, b'\x00\x00')])
def test_silent_reference_is_rejected_before_model_or_child(tmp_path, monkeypatch, width, sample):
    reference = tmp_path/'silence.wav'
    write_reference(reference, width=width, sample=sample)
    monkeypatch.setattr(transcript.subprocess, 'run', lambda *a, **k: pytest.fail('silence must not invoke ASR'))
    with pytest.raises(ValueError, match='im lặng'):
        transcript.reference_transcript(reference, tmp_path, 'fr')


@pytest.mark.parametrize('failure', ['empty', 'wrong_reference', 'timeout', 'failed_child'])
def test_failed_or_unmatched_transcription_never_enters_cache(prepared, monkeypatch, failure):
    data, reference, _, _ = prepared
    def run(args, **options):
        if failure == 'timeout':
            raise subprocess.TimeoutExpired(args, 300)
        request = json.loads(options['input'])
        return SimpleNamespace(returncode=1 if failure == 'failed_child' else 0,
            stdout=json.dumps({'ok': True, 'text': '   ' if failure == 'empty' else 'Bonjour.',
                               'language': request['language'],
                               'reference_sha256': '0'*64 if failure == 'wrong_reference' else request['reference_sha256'],
                               'asr_manifest_sha256': request['asr_manifest_sha256']}))
    monkeypatch.setattr(transcript.subprocess, 'run', run)
    with pytest.raises(ValueError):
        transcript.reference_transcript(reference, data, 'fr')
    assert not list((data/'cache/native-transcripts').glob('*.json'))


def test_child_verifies_model_sha_before_loading_asr(prepared):
    data, reference, _, _ = prepared
    request = request_for(data, reference)
    path = data/'models/native-asr/model.bin'
    content = bytearray(path.read_bytes())
    content[-1] ^= 1
    path.write_bytes(content)
    with pytest.raises(ValueError, match='SHA256'):
        transcript._transcribe_request(request)


@pytest.mark.parametrize('segments', [
    [SimpleNamespace(text=' Bonjour. ', no_speech_prob=.1, avg_logprob=-.2),
     SimpleNamespace(text=' Une autre phrase.', no_speech_prob=.2, avg_logprob=-.4)],
    [],
    [SimpleNamespace(text='Hallucination.', no_speech_prob=.99, avg_logprob=-2)]])
def test_child_uses_only_local_cpu_asr_and_rejects_empty_low_confidence_speech(prepared, monkeypatch, segments):
    data, reference, _, dependencies = prepared
    observed = {}
    class Model:
        def __init__(self, path, **options):
            observed['model'] = path
            observed.update(options)
        def transcribe(self, path, **options):
            observed['reference'] = path
            observed['inference'] = options
            return iter(segments), None
    monkeypatch.setitem(sys.modules, 'faster_whisper', SimpleNamespace(WhisperModel=Model))
    monkeypatch.setattr(transcript.importlib.metadata, 'version', lambda package: transcript.ASR_VERSION)
    original_path = list(sys.path)
    try:
        if segments and segments[0].no_speech_prob < .8:
            result = transcript._transcribe_request(request_for(data, reference, 'en'))
            assert result['text'] == 'Bonjour. Une autre phrase.'
        else:
            with pytest.raises(ValueError):
                transcript._transcribe_request(request_for(data, reference, 'en'))
        assert sys.path[0] == str(dependencies)
    finally:
        sys.path[:] = original_path
    assert observed['model'] == str(data/'models/native-asr')
    assert observed['device'] == 'cpu' and observed['compute_type'] == 'int8'
    assert observed['local_files_only'] is True and observed['num_workers'] == 1
    assert observed['reference'] == str(reference)
    assert observed['inference']['language'] == 'en' and observed['inference']['beam_size'] == 3


def test_child_stdout_is_json_and_upstream_logging_stays_on_stderr(monkeypatch, capsys):
    def transcribe(request):
        print('upstream model progress')
        return {'ok': True, 'text': 'Local private transcription.'}
    monkeypatch.setattr(transcript, '_transcribe_request', transcribe)
    monkeypatch.setattr(sys, 'argv', ['native_transcript', '--transcribe'])
    monkeypatch.setattr(sys, 'stdin', io.StringIO('{}'))
    assert transcript.main() == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)['text'] == 'Local private transcription.'
    assert 'upstream model progress' in captured.err and 'Local private transcription.' not in captured.err
