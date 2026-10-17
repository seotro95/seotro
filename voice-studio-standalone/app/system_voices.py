"""Installed Windows SAPI voices; no model download or credentials."""
import hashlib
import json
import os
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from language_catalog import LANGUAGES,system_language

SCRIPT = Path(__file__).with_name('system_speech.ps1')


def command(action):
    # Execute our fixed script text without changing Windows execution policy.
    script = SCRIPT.read_text(encoding='utf-8').split('\n', 1)[1]
    prefix = "$Action='"+action+"'; $InputFile=$env:VOICE_STUDIO_SPEECH_REQUEST;\n"
    return ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', prefix+script]


@lru_cache(maxsize=1)
def installed_voices():
    if os.name != 'nt' or not shutil.which('powershell.exe'):
        return []
    try:
        result = subprocess.run(command('list'), capture_output=True, text=True, encoding='utf-8-sig', timeout=20, check=True)
        entries = json.loads(result.stdout)
        if isinstance(entries, dict):
            entries = [entries]
        voices = []
        for entry in entries:
            culture = entry['culture']
            language=system_language(culture)
            if language not in LANGUAGES:continue
            voices.append({'id': 'sys-'+hashlib.sha256(entry['name'].encode()).hexdigest()[:24], 'name': entry['name']+' · Windows', 'engine': 'system', 'speaker': entry['name'], 'languages': [language], 'category': 'system','culture':culture, 'description': 'Giọng có sẵn trên Windows · không cần mô hình AI'})
        return voices
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        return []


def speak(text, voice, output):
    if os.name != 'nt':
        raise ValueError('Giọng hệ thống hiện hỗ trợ Windows. Chọn giọng AI trên máy này.')
    request = Path(str(output)+'.json')
    request.write_text(json.dumps({'text': text, 'voice': voice, 'output': str(output.resolve())}, ensure_ascii=False), encoding='utf-8')
    try:
        subprocess.run(command('speak'), env=dict(os.environ, VOICE_STUDIO_SPEECH_REQUEST=str(request)), check=True, timeout=180, stdout=subprocess.DEVNULL)
    finally:
        request.unlink(missing_ok=True)
