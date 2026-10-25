"""Exercise first-run download recovery against a real local HTTP server."""
from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import ssl
import threading
import urllib.error
import urllib.parse

import pytest

import prepare_hmong as setup


@contextmanager
def model_server(responses):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append({"path": self.path, "headers": dict(self.headers)})
            response = responses[min(len(requests) - 1, len(responses) - 1)]
            body = response.get("body", b"")
            self.send_response(response.get("status", 200))
            self.send_header("Content-Length", str(response.get("length", len(body))))
            for key, value in response.get("headers", {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
            self.close_connection = True

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=.01), daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/resolve/pinned/model.pth", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture(autouse=True)
def immediate_retries(monkeypatch):
    monkeypatch.setattr(setup.time, "sleep", lambda seconds: None)


def download(url, path, payload):
    return setup._download(url, path, len(payload), hashlib.sha256(payload).hexdigest(), None)


@pytest.mark.parametrize("status", [403, 408, 429, 500, 502, 503, 504])
def test_transient_http_retries_original_pinned_path_without_weakening_integrity(tmp_path, status):
    payload = b"verified model bytes"
    target = tmp_path / "model.pth"
    with model_server([{"status": status, "headers": {"Retry-After": "1"}}, {"body": payload}]) as (url, requests):
        assert download(url, target, payload) == hashlib.sha256(payload).hexdigest()
    assert target.read_bytes() == payload
    assert len(requests) == 2
    first, retry = [urllib.parse.urlsplit(item["path"]) for item in requests]
    assert first.path == retry.path == "/resolve/pinned/model.pth"
    assert not first.query and "voice_studio_retry" in urllib.parse.parse_qs(retry.query)
    assert requests[1]["headers"]["Cache-Control"] == "no-cache"
    assert not target.with_name("model.pth.part").exists()


def test_connection_ending_mid_file_resumes_at_saved_offset(tmp_path):
    payload = b"pinned model bytes\n" * 10_000
    prefix_size = 32_000
    target = tmp_path / "model.pth"
    with model_server([
        {"body": payload[:prefix_size], "length": len(payload)},
        {"status": 206, "body": payload[prefix_size:],
         "headers": {"Content-Range": f"bytes {prefix_size}-{len(payload)-1}/{len(payload)}"}},
    ]) as (url, requests):
        download(url, target, payload)
    assert target.read_bytes() == payload
    assert len(requests) == 2
    assert requests[1]["headers"]["Range"] == f"bytes={prefix_size}-"


def test_socket_reset_retries_from_the_flushed_prefix(tmp_path, monkeypatch):
    payload = b"model download survives a TCP connection reset"
    requests = []

    class ResetResponse(io.BytesIO):
        status = 200
        headers = {}

        def read(self, size):
            if self.tell():
                raise ConnectionResetError("connection reset by peer")
            return super().read(8)

    def open_response(request, timeout):
        requests.append(request)
        assert timeout == setup.DOWNLOAD_TIMEOUT
        if len(requests) == 1:
            return ResetResponse(payload)
        response = io.BytesIO(payload[8:])
        response.status = 206
        response.headers = {"Content-Range": f"bytes 8-{len(payload)-1}/{len(payload)}"}
        return response

    monkeypatch.setattr(setup.urllib.request, "urlopen", open_response)
    target = tmp_path / "model.pth"
    download("https://huggingface.co/resolve/pinned/model.pth", target, payload)
    assert target.read_bytes() == payload
    assert len(requests) == 2 and requests[1].get_header("Range") == "bytes=8-"


def test_restart_reuses_partial_only_after_a_valid_206_and_final_checksum(tmp_path):
    payload = b"model kept across launcher restarts"
    offset = 8
    target = tmp_path / "model.pth"
    target.with_name("model.pth.part").write_bytes(payload[:offset])
    with model_server([{"status": 206, "body": payload[offset:],
                        "headers": {"Content-Range": f"bytes {offset}-{len(payload)-1}/{len(payload)}"}}]) as (url, requests):
        download(url, target, payload)
    assert target.read_bytes() == payload
    assert requests[0]["headers"]["Range"] == f"bytes={offset}-"


def test_server_ignoring_range_replaces_partial_instead_of_appending(tmp_path):
    payload = b"server only supports full model downloads"
    target = tmp_path / "model.pth"
    target.with_name("model.pth.part").write_bytes(b"old partial")
    with model_server([{"body": payload}]) as (url, requests):
        download(url, target, payload)
    assert target.read_bytes() == payload
    assert len(requests) == 1 and requests[0]["headers"]["Range"] == "bytes=11-"


@pytest.mark.parametrize("content_range", [None, "bytes 0-23/32", "bytes 8-31/999", "invalid"])
def test_inconsistent_range_never_appends_or_replaces_an_existing_model(tmp_path, content_range):
    payload = b"m" * 32
    target = tmp_path / "model.pth"
    target.write_bytes(b"existing installation")
    partial = target.with_name("model.pth.part")
    partial.write_bytes(payload[:8])
    headers = {"Content-Range": content_range} if content_range is not None else {}
    with model_server([{"status": 206, "body": payload[8:], "headers": headers}]) as (url, requests):
        with pytest.raises(setup.SetupError, match="Content-Range"):
            download(url, target, payload)
    assert target.read_bytes() == b"existing installation"
    assert partial.read_bytes() == payload[:8]
    assert len(requests) == 1


def test_corrupt_saved_prefix_cannot_be_installed_despite_valid_range_response(tmp_path):
    payload = b"verified pinned model"
    target = tmp_path / "model.pth"
    target.write_bytes(b"existing installation")
    partial = target.with_name("model.pth.part")
    partial.write_bytes(b"wrong")
    with model_server([{"status": 206, "body": payload[5:],
                        "headers": {"Content-Range": f"bytes 5-{len(payload)-1}/{len(payload)}"}}]) as (url, _):
        with pytest.raises(setup.SetupError, match="Checksum"):
            download(url, target, payload)
    assert target.read_bytes() == b"existing installation"
    assert not partial.exists()


def test_unavailable_server_retries_only_three_times_and_keeps_partial_for_next_launch(tmp_path):
    payload = b"downloaded prefix and remaining model"
    target = tmp_path / "model.pth"
    partial = target.with_name("model.pth.part")
    partial.write_bytes(payload[:8])
    with model_server([{"status": 503}]) as (url, requests):
        with pytest.raises(setup.SetupError, match="sau 3 lần"):
            download(url, target, payload)
    assert len(requests) == 3
    assert not target.exists()
    assert partial.read_bytes() == payload[:8]


def test_cancellation_keeps_received_prefix_and_releases_lock(tmp_path, monkeypatch):
    payload = b"preserved interrupted model"
    target = tmp_path / "model.pth"
    partial = target.with_name("model.pth.part")

    class InterruptedResponse:
        status = 200
        headers = {}

        def __enter__(self):
            self.reads = 0
            return self

        def __exit__(self, *args):
            pass

        def read(self, size):
            self.reads += 1
            if self.reads == 1:
                return payload[:8]
            raise KeyboardInterrupt

    monkeypatch.setattr(setup.urllib.request, "urlopen", lambda *args, **kwargs: InterruptedResponse())
    with pytest.raises(KeyboardInterrupt):
        download("https://huggingface.co/resolve/pinned/model.pth", target, payload)
    assert partial.read_bytes() == payload[:8]
    assert not target.exists()
    with setup._download_lock(target):
        pass


def test_completed_partial_is_verified_offline_before_installation(tmp_path, monkeypatch):
    payload = b"complete but not installed before restart"
    target = tmp_path / "model.pth"
    target.with_name("model.pth.part").write_bytes(payload)
    monkeypatch.setattr(setup.urllib.request, "urlopen", lambda *args, **kwargs: pytest.fail("No network needed"))
    download("https://huggingface.co/resolve/pinned/model.pth", target, payload)
    assert target.read_bytes() == payload


def test_missing_upstream_file_fails_without_repeated_requests(tmp_path):
    with model_server([{"status": 404}]) as (url, requests):
        with pytest.raises(urllib.error.HTTPError, match="404"):
            download(url, tmp_path / "model.pth", b"model")
    assert len(requests) == 1


def test_second_downloader_cannot_write_while_first_owns_partial(tmp_path):
    target = tmp_path / "model.pth"
    with setup._download_lock(target):
        with pytest.raises(setup.SetupError, match="cửa sổ khác"):
            download("https://huggingface.co/resolve/pinned/model.pth", target, b"model")
    assert not target.exists()


def test_tls_certificate_failure_never_uses_an_unverified_context(tmp_path, monkeypatch):
    calls = []

    def certificate_failure(request, timeout):
        calls.append(request.full_url)
        raise ssl.SSLCertVerificationError("certificate verify failed")

    monkeypatch.setattr(setup.urllib.request, "urlopen", certificate_failure)
    with pytest.raises(ssl.SSLCertVerificationError):
        download("https://huggingface.co/resolve/pinned/model.pth", tmp_path / "model.pth", b"model")
    assert calls == ["https://huggingface.co/resolve/pinned/model.pth"]
    assert not (tmp_path / "model.pth").exists()
