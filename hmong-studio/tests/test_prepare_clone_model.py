import hashlib
import io
import json
from email.message import Message
import pytest

import prepare_clone_model as model


def artifact(data=b'known verified model contents', name='nested/model.bin', *, lfs=True):
    entry = {'rfilename': name, 'size': len(data)}
    if lfs:
        entry['lfs'] = {'sha256': hashlib.sha256(data).hexdigest()}
    else:
        entry['blobId'] = hashlib.sha1(
            b'blob ' + str(len(data)).encode() + b'\0' + data
        ).hexdigest()
    return entry


class Response(io.BytesIO):
    def __init__(self, data, status=200, content_range=None):
        super().__init__(data)
        self.status = status
        self.headers = {} if content_range is None else {'Content-Range': content_range}


def block_network(monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail('A verified model must not be requested from the network')
    monkeypatch.setattr(model, '_open', unexpected)


def redirect_transport(monkeypatch, destination):
    """Exercise urllib redirects with an in-memory HTTPS transport only."""
    requests = []
    original_build_opener = model.urllib.request.build_opener

    class Transport(model.urllib.request.HTTPSHandler, model.urllib.request.HTTPHandler):
        def https_open(self, request):
            requests.append(request)
            headers = Message()
            if len(requests) == 1:
                headers['Location'] = destination
                status, message, data = 302, 'Found', b'redirect response'
            else:
                status, message, data = 200, 'OK', b'model bytes'
            response = model.urllib.response.addinfourl(
                io.BytesIO(data), headers, request.full_url, status)
            response.msg = message
            return response

        def http_open(self, request):
            pytest.fail('An HTTPS model download must never make an HTTP request')

    monkeypatch.setattr(model.urllib.request, 'build_opener',
                        lambda *handlers: original_build_opener(*handlers, Transport()))
    return requests


@pytest.mark.parametrize('url', [
    'http://huggingface.co/model', 'ftp://example.com/model',
    'file:///tmp/model', 'data:application/octet-stream,model',
])
def test_initial_download_requires_https_before_opening_transport(monkeypatch, url):
    def unexpected(*args, **kwargs):
        pytest.fail('A non-HTTPS model URL must be rejected before opening transport')
    monkeypatch.setattr(model.urllib.request, 'build_opener', unexpected)
    with pytest.raises(ValueError, match='HTTPS'):
        model._open(model.urllib.request.Request(url))


@pytest.mark.parametrize('destination', [
    'http://cdn.example.com/model', 'ftp://cdn.example.com/model',
    'file:///tmp/model', 'data:application/octet-stream,model',
    'javascript:alert(1)',
])
def test_redirect_rejects_non_https_destination_before_request(monkeypatch, destination):
    requests = redirect_transport(monkeypatch, destination)
    original = 'https://huggingface.co/model'
    with pytest.raises((RuntimeError, model.urllib.error.HTTPError)):
        model._open(model.urllib.request.Request(original))
    assert [request.full_url for request in requests] == [original]


def test_https_redirect_is_followed_and_preserves_resume_header(monkeypatch):
    destination = 'https://cdn.example.com/model?signature=pinned-download'
    requests = redirect_transport(monkeypatch, destination)
    original = 'https://huggingface.co/model'
    request = model.urllib.request.Request(original, headers={'Range': 'bytes=5-'})
    with model._open(request) as response:
        assert response.read() == b'model bytes'
    assert [request.full_url for request in requests] == [original, destination]
    assert all(request.get_header('Range') == 'bytes=5-' for request in requests)


@pytest.mark.parametrize('lfs', [True, False], ids=['lfs-sha256', 'git-blob-sha1'])
def test_verification_requires_expected_size_and_checksum(tmp_path, lfs):
    data = b'known model content'
    entry = artifact(data, lfs=lfs)
    target = tmp_path / 'model'
    assert model.verified(target, entry) is None
    target.mkdir()
    assert model.verified(target, entry) is None
    target.rmdir()
    target.write_bytes(data[:-1])
    assert model.verified(target, entry) is None
    target.write_bytes(b'X' + data[1:])
    assert model.verified(target, entry) is None
    target.write_bytes(data)
    assert model.verified(target, entry) == {
        'path': entry['rfilename'], 'size': len(data),
        'sha256': hashlib.sha256(data).hexdigest(),
    }


def test_complete_target_is_reused_without_network(tmp_path, monkeypatch):
    data = b'verified existing contents'
    entry = artifact(data, 'model.bin')
    (tmp_path / 'model.bin').write_bytes(data)
    block_network(monkeypatch)
    result = model.download(tmp_path, entry)
    assert result['sha256'] == hashlib.sha256(data).hexdigest()
    assert (tmp_path / 'model.bin').read_bytes() == data
    assert not (tmp_path / 'model.bin.part').exists()


def test_complete_verified_partial_is_promoted_without_network(tmp_path, monkeypatch):
    data = b'complete before previous process stopped'
    entry = artifact(data, 'model.bin')
    partial = tmp_path / 'model.bin.part'
    partial.write_bytes(data)
    block_network(monkeypatch)
    model.download(tmp_path, entry)
    assert (tmp_path / 'model.bin').read_bytes() == data
    assert not partial.exists()


def test_corrupt_target_is_replaced_only_after_verified_download(tmp_path, monkeypatch):
    data = b'correct model bytes'
    entry = artifact(data, 'model.bin')
    target = tmp_path / 'model.bin'
    target.write_bytes(b'X' * len(data))
    requests = []

    def serve(request, timeout):
        requests.append(request)
        assert request.get_header('Range') is None
        assert target.read_bytes() == b'X' * len(data)
        return Response(data)

    monkeypatch.setattr(model, '_open', serve)
    model.download(tmp_path, entry)
    assert len(requests) == 1
    assert target.read_bytes() == data


@pytest.mark.parametrize('extra', [0, 7], ids=['same-size-bad-checksum', 'larger-than-manifest'])
def test_complete_corrupt_partial_is_discarded_before_fresh_download(tmp_path, monkeypatch, extra):
    data = b'correct model bytes'
    entry = artifact(data, 'model.bin')
    partial = tmp_path / 'model.bin.part'
    partial.write_bytes(b'X' * (len(data) + extra))

    def serve(request, timeout):
        assert request.get_header('Range') is None
        assert not partial.exists()
        return Response(data)

    monkeypatch.setattr(model, '_open', serve)
    model.download(tmp_path, entry)
    assert (tmp_path / 'model.bin').read_bytes() == data
    assert not partial.exists()


def test_interrupted_transfer_resumes_exact_partial_using_range(tmp_path, monkeypatch):
    data = b'0123456789abcdef'
    entry = artifact(data, 'weights/model file.bin')
    target = tmp_path / 'weights' / 'model file.bin'
    partial = target.with_name(target.name + '.part')
    requests = []

    class Interrupted(Response):
        def read(self, size=-1):
            if self.tell():
                raise OSError('simulated network disconnect')
            return super().read(5)

    def serve(request, timeout):
        requests.append(request)
        assert '/resolve/' + model.REVISION + '/weights/model%20file.bin' in request.full_url
        if len(requests) == 1:
            assert request.get_header('Range') is None
            return Interrupted(data)
        assert request.get_header('Range') == 'bytes=5-'
        assert partial.read_bytes() == data[:5]
        return Response(data[5:], 206, f'bytes 5-{len(data) - 1}/{len(data)}')

    monkeypatch.setattr(model, '_open', serve)
    with pytest.raises(OSError, match='disconnect'):
        model.download(tmp_path, entry)
    assert partial.read_bytes() == data[:5]
    assert not target.exists()
    model.download(tmp_path, entry)
    assert target.read_bytes() == data
    assert not partial.exists()
    assert len(requests) == 2


def test_server_ignoring_range_restarts_instead_of_appending(tmp_path, monkeypatch):
    data = b'the full model response'
    entry = artifact(data, 'model.bin')
    partial = tmp_path / 'model.bin.part'
    partial.write_bytes(data[:4])

    def serve(request, timeout):
        assert request.get_header('Range') == 'bytes=4-'
        return Response(data, 200)

    monkeypatch.setattr(model, '_open', serve)
    model.download(tmp_path, entry)
    assert (tmp_path / 'model.bin').read_bytes() == data
    assert not partial.exists()


@pytest.mark.parametrize('content_range', [None, 'bytes 0-15/16', 'bytes 50-59/60'])
def test_wrong_range_does_not_modify_existing_partial(tmp_path, monkeypatch, content_range):
    data = b'0123456789abcdef'
    entry = artifact(data, 'model.bin')
    partial = tmp_path / 'model.bin.part'
    original = data[:5]
    partial.write_bytes(original)

    def serve(request, timeout):
        assert request.get_header('Range') == 'bytes=5-'
        return Response(b'wrong response', 206, content_range)

    monkeypatch.setattr(model, '_open', serve)
    with pytest.raises(RuntimeError, match='khoang du lieu'):
        model.download(tmp_path, entry)
    assert partial.read_bytes() == original
    assert not (tmp_path / 'model.bin').exists()


def test_checksum_failure_keeps_target_and_never_promotes_partial(tmp_path, monkeypatch):
    data = b'expected verified bytes'
    entry = artifact(data, 'model.bin')
    target = tmp_path / 'model.bin'
    original = b'old target must survive'
    target.write_bytes(original)
    bad_download = b'X' * len(data)
    monkeypatch.setattr(model, '_open', lambda *args, **kwargs: Response(bad_download))
    with pytest.raises(RuntimeError, match='checksum'):
        model.download(tmp_path, entry)
    assert target.read_bytes() == original
    assert target.with_name(target.name + '.part').read_bytes() == bad_download


@pytest.mark.parametrize('name', ['../outside.bin', 'nested/../../outside.bin', '/outside.bin', r'nested\outside.bin', '', '.'])
def test_manifest_paths_cannot_escape_or_name_the_root(tmp_path, monkeypatch, name):
    root = tmp_path / 'models'
    root.mkdir()
    block_network(monkeypatch)
    with pytest.raises(RuntimeError):
        model.download(root, artifact(name=name))
    assert list(root.iterdir()) == []
    assert not (tmp_path / 'models.part').exists()


@pytest.mark.parametrize('symlink_name', ['weights', 'model.bin', 'model.bin.part'])
def test_model_and_partial_symlinks_cannot_write_outside_root(tmp_path, monkeypatch, symlink_name):
    root = tmp_path / 'models'
    root.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    sentinel = outside / 'model.bin'
    original = b'outside user data'
    sentinel.write_bytes(original)
    link = root / symlink_name
    if symlink_name == 'weights':
        link.symlink_to(outside, target_is_directory=True)
        name = 'weights/model.bin'
    else:
        link.symlink_to(sentinel)
        name = 'model.bin'
    block_network(monkeypatch)
    with pytest.raises(RuntimeError):
        model.download(root, artifact(b'downloaded model contents', name))
    assert sentinel.read_bytes() == original
    assert link.is_symlink()


def test_prepare_writes_ready_marker_only_for_verified_snapshot(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    source.mkdir()
    first = b'small model A'
    second = b'small model B'
    entries = [artifact(first, 'first.bin'), artifact(second, 'nested/second.bin', lfs=False)]
    manifest = {'repository': model.REPOSITORY, 'revision': model.REVISION, 'entries': entries}
    (source / 'clone_model_manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    monkeypatch.setattr(model, 'BASE', source)

    def serve(request, timeout):
        return Response(first if '/first.bin?' in request.full_url else second)

    monkeypatch.setattr(model, '_open', serve)
    root = tmp_path / 'models'
    assert model.prepare(root) == root.resolve()
    marker = root / '.hmong-model-ready.json'
    payload = json.loads(marker.read_text(encoding='utf-8'))
    assert payload['repository'] == model.REPOSITORY
    assert payload['revision'] == model.REVISION
    assert [row['path'] for row in payload['files']] == ['first.bin', 'nested/second.bin']
    assert all(model.verified(root / e['rfilename'], e) for e in entries)
    assert not marker.with_suffix('.tmp').exists()

    (root / 'first.bin').write_bytes(b'bad')
    monkeypatch.setattr(model, '_open', lambda *args, **kwargs: Response(b'broken'))
    with pytest.raises(RuntimeError):
        model.prepare(root)
    assert not marker.exists()


def test_prepare_rejects_unpinned_manifest_before_model_writes(tmp_path, monkeypatch):
    manifest = {'repository': model.REPOSITORY, 'revision': 'unreviewed-revision', 'entries': []}
    (tmp_path / 'clone_model_manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    monkeypatch.setattr(model, 'BASE', tmp_path)
    root = tmp_path / 'models'
    with pytest.raises(RuntimeError, match='phien ban'):
        model.prepare(root)
    assert not root.exists()


def test_empty_git_file_downloads_from_cold_cache(tmp_path, monkeypatch):
    entry = artifact(b'', 'CosyVoice/cosyvoice/__init__.py', lfs=False)
    target = tmp_path / entry['rfilename']
    assert not target.parent.exists()
    block_network(monkeypatch)

    result = model.download(tmp_path, entry)

    assert target.is_file()
    assert target.read_bytes() == b''
    assert result == {
        'path': entry['rfilename'], 'size': 0,
        'sha256': hashlib.sha256(b'').hexdigest(),
    }
    assert not target.with_name(target.name + '.part').exists()


@pytest.mark.parametrize('lfs', [True, False], ids=['lfs-sha256', 'git-blob-sha1'])
def test_empty_artifact_with_wrong_checksum_is_never_promoted(tmp_path, monkeypatch, lfs):
    entry = artifact(b'', '__init__.py', lfs=lfs)
    if lfs:
        entry['lfs']['sha256'] = '0' * 64
    else:
        entry['blobId'] = '0' * 40
    target = tmp_path / '__init__.py'
    original = b'previous file must survive a malformed manifest'
    target.write_bytes(original)
    monkeypatch.setattr(model, '_open', lambda *args, **kwargs: Response(b''))

    with pytest.raises(RuntimeError, match='checksum'):
        model.download(tmp_path, entry)

    assert target.read_bytes() == original
    assert model.verified(target, entry) is None


def test_corrupt_partial_for_empty_file_is_repaired(tmp_path, monkeypatch):
    entry = artifact(b'', 'cosyvoice/__init__.py', lfs=False)
    target = tmp_path / entry['rfilename']
    target.parent.mkdir()
    target.write_bytes(b'old incorrect file')
    partial = target.with_name(target.name + '.part')
    partial.write_bytes(b'incomplete incorrect data')
    monkeypatch.setattr(model, '_open', lambda *args, **kwargs: Response(b''))

    result = model.download(tmp_path, entry)

    assert target.read_bytes() == b''
    assert result == model.verified(target, entry)
    assert not partial.exists()


def test_prepare_ready_marker_includes_verified_empty_git_file(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    source.mkdir()
    empty = artifact(b'', 'CosyVoice/cosyvoice/__init__.py', lfs=False)
    weights = artifact(b'model bytes', 'weights.bin')
    entries = [weights, empty]
    manifest = {'repository': model.REPOSITORY, 'revision': model.REVISION, 'entries': entries}
    (source / 'clone_model_manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    monkeypatch.setattr(model, 'BASE', source)

    def serve(request, timeout):
        return Response(b'model bytes' if '/weights.bin?' in request.full_url else b'')

    monkeypatch.setattr(model, '_open', serve)
    root = tmp_path / 'models'
    model.prepare(root)

    payload = json.loads((root / '.hmong-model-ready.json').read_text(encoding='utf-8'))
    assert payload['files'] == [
        {'path': empty['rfilename'], 'size': 0, 'sha256': hashlib.sha256(b'').hexdigest()},
        {'path': weights['rfilename'], 'size': weights['size'],
         'sha256': hashlib.sha256(b'model bytes').hexdigest()},
    ]
    assert all(model.verified(root / entry['rfilename'], entry) for entry in entries)
