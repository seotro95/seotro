import json
import os
from pathlib import Path
import socket
import subprocess
import urllib.request

import portable_launcher


def test_launcher_avoids_occupied_loopback_port():
    with socket.socket() as occupied:
        try:
            occupied.bind(('127.0.0.1', 8770))
        except OSError:
            pass  # A real local process already occupies this port.
        chosen = portable_launcher.available_port()
        assert 8771 <= chosen < 8790


def test_custom_install_environment_is_used_by_start_script(tmp_path):
    import pytest
    if os.name == 'nt':
        pytest.skip('This check exercises the Linux shell launcher.')
    executable = tmp_path / 'custom env' / 'bin' / 'python'
    executable.parent.mkdir(parents=True)
    executable.write_text('#!/bin/sh\nprintf "%s\\n" "$PWD" "$@"\n')
    executable.chmod(0o700)
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(['bash', str(root / 'start.sh')], env={**os.environ, 'VOICE_STUDIO_VENV': str(executable.parent.parent), 'VOICE_STUDIO_PYTHON': ''}, cwd=tmp_path, capture_output=True, text=True, check=True)
    assert result.stdout.splitlines() == [str(root), 'portable_launcher.py']


def test_launcher_serves_before_browser_is_opened(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path / 'voice-data'))
    monkeypatch.setattr(portable_launcher.sys, 'executable', os.environ.get('VOICE_STUDIO_TEST_PYTHON', portable_launcher.sys.executable))
    children = []
    real_popen = subprocess.Popen
    def spawn(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        children.append(process)
        return process
    monkeypatch.setattr(portable_launcher.subprocess, 'Popen', spawn)
    opened = []
    def open_browser(url):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url.split('/?')[0] + '/api/config', timeout=2) as response:
            config = json.load(response)
        assert config['mode'] == 'local'
        opened.append(url)
        children[0].terminate()
        return True
    monkeypatch.setattr(portable_launcher.webbrowser, 'open', open_browser)
    portable_launcher.main()
    assert len(opened) == 1
    assert children[0].poll() is not None
