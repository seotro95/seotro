"""Browser contracts for the Hmong variant; mocked API, no inference claims."""
import contextlib
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import threading
from urllib.parse import urlparse

import pytest

playwright = pytest.importorskip('playwright.sync_api', reason='Optional Chromium UI checks need Playwright')
CHROMIUM = shutil.which('chromium') or shutil.which('chromium-browser')
pytestmark = pytest.mark.skipif(not CHROMIUM, reason='Optional UI checks need system Chromium')
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def static_site():
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)
        def do_GET(self):
            if self.path == '/':
                self.path = '/static/index.html'
            super().do_GET()
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield 'http://127.0.0.1:' + str(server.server_port)
    server.shutdown()
    server.server_close()
    thread.join()


@contextlib.contextmanager
def studio_page(site, *, hmong=True, ready=True, missing_reference_first=False, hmong_steps=16):
    language = 'mww' if hmong else 'vi'
    engine = 'f5_hmong' if hmong else 'vieneu'
    ident = 'hmong-female' if hmong else 'vi-maianh'
    state = {'ready': ready, 'speech': [], 'tasks': [], 'errors': []}
    def configuration():
        return {'variant': 'hmong' if hmong else 'standard', 'app_name': 'Voice Studio Hmong' if hmong else 'Voice Studio',
                'default_language': language, 'version': '3.6.2', 'mode': 'local', 'hardware': 'CPU', 'cpu_cores': 4,
                'available_ram_gb': 8, 'ffmpeg': True, 'max_characters': 200000, 'max_audio_minutes': 180,
                'languages': {language: 'Hmong Trắng' if hmong else 'Tiếng Việt'},
                'subtitle_languages': {'vi': 'Tiếng Việt', 'mww': 'Hmong Trắng'} if hmong else {'vi': 'Tiếng Việt'},
                'ai_voice_languages': [language], 'models': {engine: state['ready']}, 'nano_ready': False,
                'int8_cpu': False, 'fast_vieneu': False, 'subtitle_ready': False, 'hmong_ready': state['ready'],
                **({'hmong_steps': hmong_steps} if hmong_steps is not None else {}),
                **({'hardware_label': 'CỤC BỘ · CHƯA KIỂM TRA CPU/GPU'} if hmong else {}),
                'hmong_reference_note': 'Mẫu Hmong đã ghép lời tham chiếu.'}
    def voices():
        entries = [{'id': ident, 'engine': engine, 'name': 'Hmong Nữ' if hmong else 'Mai Anh',
                    'languages': [language], 'native_language': language, 'ready': state['ready'],
                    'description': 'Giọng tham chiếu'}]
        if missing_reference_first:
            entries.insert(0, {**entries[0], 'id': 'hmong-male', 'name': 'Mẫu đã bị xóa', 'ready': False})
        return {'voices': entries}
    def job(payload=None):
        payload = payload or (state['speech'][-1] if state['speech'] else {})
        return {**payload, 'id': 'a' * 32, 'status': 'done', 'progress': 100, 'audio_seconds': 4,
                'voice_name': 'Hmong Nữ', 'url': '/api/audio/' + 'a' * 32, 'format': 'wav', 'speed_report': None}
    def handle(route):
        request = route.request
        path = urlparse(request.url).path
        response = {}
        if path == '/api/config':
            response = configuration()
        elif path in ['/api/voices', '/api/voices/refresh']:
            response = voices()
        elif path in ['/api/history', '/api/videos']:
            response = {'items': []}
        elif path == '/api/writing/connections':
            response = {'providers': {'ollama': False}, 'local': {'connected': False, 'models': []},
                        'defaults': {'ollama': 'qwen3:4b'}}
        elif path == '/api/speech':
            state['speech'].append(request.post_data_json)
            response = job(request.post_data_json)
        elif path.startswith('/api/jobs/') and path.endswith('/alignment'):
            response = {'pending': True, 'cues': [], 'sync_ok': False}
        elif path.startswith('/api/jobs/'):
            response = job()
        elif path == '/api/video-tasks':
            state['tasks'].append(request.post_data_json)
            state['ready'] = True
            response = {'id': 'b' * 32, 'status': 'queued'}
        elif path.startswith('/api/video-tasks/'):
            response = {'id': 'b' * 32, 'status': 'done', 'progress': 100}
        elif path.startswith('/api/audio/'):
            route.fulfill(status=200, content_type='audio/wav', body=b'')
            return
        route.fulfill(status=200, content_type='application/json', body=json.dumps(response))
    with playwright.sync_playwright() as driver:
        browser = driver.chromium.launch(executable_path=CHROMIUM, headless=True, args=['--no-sandbox'])
        page = browser.new_page()
        page.on('pageerror', lambda error: state['errors'].append(str(error)))
        page.route('**/api/**', handle)
        page.goto(site, wait_until='networkidle')
        playwright.expect(page.locator('#voice')).to_have_value(ident)
        try:
            yield page, state
        finally:
            browser.close()


def test_hmong_branding_steps_and_all_speech_entrypoints(static_site):
    with studio_page(static_site, missing_reference_first=True) as (page, state):
        playwright.expect(page).to_have_title('Voice Studio Hmong')
        playwright.expect(page.locator('#panel-create')).to_be_visible()
        playwright.expect(page.locator('#language')).to_have_value('mww')
        playwright.expect(page.locator('#nano-steps')).to_be_hidden()
        playwright.expect(page.locator('#target-preset')).to_be_hidden()
        playwright.expect(page.locator('#hmong-steps')).to_have_value('16')
        playwright.expect(page.locator('#dub-hmong-steps')).to_have_value('16')
        playwright.expect(page.locator('#paragraph-pause')).to_have_value('0')
        playwright.expect(page.locator('#delivery')).to_have_value('natural')
        playwright.expect(page.locator('#hardware')).to_have_text('CỤC BỘ · CHƯA KIỂM TRA CPU/GPU')
        page.click('#sample-button')
        playwright.expect(page.locator('#script')).to_have_value('Nyob zoo, kuv zoo siab tau ntsib koj. Hnub no peb yuav mloog ib zaj dab neeg. Ua tsaug rau koj mloog.')
        page.select_option('#hmong-steps', '32')
        page.select_option('#delivery', 'review')
        page.click('#generate')
        playwright.expect(page.locator('#output-title')).to_contain_text('đã sẵn sàng')
        assert state['speech'][-1]['language'] == 'mww'
        assert state['speech'][-1]['hmong_steps'] == 32
        assert state['speech'][-1]['delivery'] == 'review'
        assert state['speech'][-1]['paragraph_pause'] == 0
        playwright.expect(page.locator('#dub-hmong-steps')).to_have_value('32')
        page.locator('.nav-item[data-tab="dub"]').click()
        playwright.expect(page.locator('#editor-recognize')).to_be_hidden()
        playwright.expect(page.locator('#asr-language')).to_be_hidden()
        playwright.expect(page.locator('#hmong-asr-note')).to_be_visible()
        page.fill('#workspace-free-script', 'Nyob zoo. Ua tsaug rau koj mloog.')
        page.click('#workspace-free-generate')
        playwright.expect(page.locator('#workspace-free-status')).to_contain_text('Voice riêng đã sẵn sàng')
        assert state['speech'][-1]['hmong_steps'] == 32
        assert state['speech'][-1]['language'] == 'mww'
        page.locator('.nav-item[data-tab="clone"]').click()
        assert page.locator('#transcript').get_attribute('required') is not None
        playwright.expect(page.locator('label[for="transcript"]')).to_contain_text('3–8 giây')
        assert state['errors'] == []


@pytest.mark.parametrize('configured_steps', [None, 12])
def test_hmong_missing_or_invalid_steps_fall_back_to_16_and_allow_explicit_draft(static_site, configured_steps):
    with studio_page(static_site, hmong_steps=configured_steps) as (page, state):
        playwright.expect(page.locator('#hmong-steps')).to_have_value('16')
        page.fill('#script', 'Nyob zoo. Ua tsaug.')
        page.click('#generate')
        playwright.expect(page.locator('#output-title')).to_contain_text('đã sẵn sàng')
        assert state['speech'][-1]['hmong_steps'] == 16
        assert state['speech'][-1]['paragraph_pause'] == 0
        page.select_option('#hmong-steps', '4')
        playwright.expect(page.locator('#dub-hmong-steps')).to_have_value('4')
        page.click('#generate')
        playwright.expect(page.locator('#generate')).to_be_enabled()
        assert state['speech'][-1]['hmong_steps'] == 4
        assert state['errors'] == []


def test_hmong_model_button_requests_the_hmong_engine(static_site):
    with studio_page(static_site, ready=False) as (page, state):
        page.click('#voice-load-model')
        playwright.expect(page.locator('#voice-load-model')).to_contain_text('sẵn sàng', timeout=10000)
        assert state['tasks'] == [{'action': 'prepare_voice', 'engine': 'f5_hmong'}]
        assert state['errors'] == []


def test_standard_mode_keeps_original_default_and_optional_transcript(static_site):
    with studio_page(static_site, hmong=False) as (page, state):
        playwright.expect(page.locator('#panel-dub')).to_be_visible()
        page.locator('.nav-item[data-tab="create"]').click()
        playwright.expect(page.locator('#hmong-settings')).to_be_hidden()
        playwright.expect(page.locator('#nano-steps')).to_be_visible()
        # Existing standard UI's fast-start initializer selects zero pause.
        playwright.expect(page.locator('#paragraph-pause')).to_have_value('0')
        playwright.expect(page.locator('#delivery')).to_have_value('natural')
        assert page.locator('#transcript').get_attribute('required') is None
        page.fill('#script', 'Xin chào.')
        page.click('#generate')
        playwright.expect(page.locator('#output-title')).to_contain_text('đã sẵn sàng')
        assert 'hmong_steps' not in state['speech'][-1]
        assert state['speech'][-1]['paragraph_pause'] == 0
        assert state['errors'] == []
