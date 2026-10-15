import subprocess
from unittest.mock import patch

import pytest
from dubbing import inspect_video, mux_video
from test_app import studio  # noqa: F401


@pytest.fixture
def movie(tmp_path):
    path = tmp_path / 'source.mp4'
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=128x96:r=10:d=4', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=4', '-c:v', 'libx264', '-c:a', 'aac', '-shortest', '-y', str(path)], check=True)
    return path


def test_real_upload_mux_preserves_video_and_rejects_lost_words(studio, movie):
    client, root = studio
    uploaded = client.post('/api/videos', files={'file': ('test.mp4', movie.read_bytes(), 'video/mp4')})
    assert uploaded.status_code == 201, uploaded.text
    video = uploaded.json()
    assert video['has_audio'] and 3.9 <= video['duration'] <= 4.1
    assert client.get('/api/videos').json()['items'][0]['id'] == video['id']
    audio = root / 'audio' / 'test.wav'
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=880:duration=1', '-y', str(audio)], check=True)
    work = root / 'parts' / 'test'
    work.mkdir()
    for mix in (False, True):
        job = {'id': 'test', 'video_id': video['id'], 'video_offset': 1, 'video_mix': mix}
        mux_video(job, audio, work, root, 1)
        output = root / 'audio' / 'test.mp4'
        assert abs(inspect_video(output)['duration'] - 4) < .1
        def video_hash(path):
            return subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(path), '-map', '0:v:0', '-c', 'copy', '-f', 'hash', '-'])
        assert video_hash(movie) == video_hash(output)
    with pytest.raises(ValueError, match='không tự cắt'):
        mux_video(job, audio, work, root, 4)
    (root / 'models' / 'vieneu_nano.ready').touch()
    payload = {'text': 'Xin chào.', 'voice_id': 'nano-minhquan', 'video_id': video['id']}
    assert client.post('/api/speech', json={**payload, 'video_offset': 4}).status_code == 422
    with patch('app.executor.submit'):
        response = client.post('/api/speech', json=payload)
    assert response.status_code == 202
    assert response.json()['video_id'] == video['id']
    assert client.delete('/api/videos/' + video['id']).status_code == 409
    assert client.get('/api/dubbed/' + response.json()['id']).status_code == 404


def test_bad_upload_is_cleaned_and_identifier_is_validated(studio):
    client, root = studio
    r = client.post('/api/videos', files={'file': ('bad.mp4', b'not a video', 'video/mp4')})
    assert r.status_code == 422
    assert not list((root / 'videos').iterdir())
    assert client.post('/api/speech', json={'text': 'Xin chào', 'voice_id': 'nano-minhquan', 'video_id': '../escape'}).status_code == 404
