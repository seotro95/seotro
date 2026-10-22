"""Preserve server failure status after the browser launcher becomes ready."""
import io

import pytest

import portable_launcher


class ReadyProcess:
    def __init__(self, returncode, *, interrupted=False):
        self.final_returncode = returncode
        self.returncode = None
        self.interrupted = interrupted
        self.wait_calls = []

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.wait_calls.append(timeout)
        if self.interrupted:
            self.interrupted = False
            raise KeyboardInterrupt
        self.returncode = self.final_returncode
        return self.returncode


def launch_ready(monkeypatch, process):
    class LocalOpener:
        def open(self, url, timeout):
            assert url == 'http://127.0.0.1:8770/api/config'
            return io.BytesIO(b'{"mode":"local","version":"1.2.0"}')

    monkeypatch.setattr(portable_launcher, 'available_port', lambda: 8770)
    monkeypatch.setattr(portable_launcher.subprocess, 'Popen', lambda *args, **kwargs: process)
    monkeypatch.setattr(portable_launcher.urllib.request, 'build_opener', lambda *args: LocalOpener())


def test_ready_server_failure_is_reported(monkeypatch):
    process = ReadyProcess(17)
    launch_ready(monkeypatch, process)
    with pytest.raises(RuntimeError, match='ma loi 17'):
        portable_launcher.main(open_browser=False)
    assert process.returncode == 17


def test_clean_server_exit_and_browser_fallback(monkeypatch, capsys):
    process = ReadyProcess(0)
    launch_ready(monkeypatch, process)
    opened = []
    monkeypatch.setattr(portable_launcher.webbrowser, 'open', lambda url: opened.append(url) or False)
    portable_launcher.main()
    assert process.returncode == 0
    assert opened == ['http://127.0.0.1:8770/?v=1.2.0']
    assert 'Mo dia chi Studio ben tren' in capsys.readouterr().out


def test_ctrl_c_shutdown_is_not_reported_as_server_failure(monkeypatch):
    process = ReadyProcess(130, interrupted=True)
    launch_ready(monkeypatch, process)
    portable_launcher.main(open_browser=False)
    assert process.wait_calls == [None, 8]
    assert process.returncode == 130
