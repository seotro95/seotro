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
PROJECT_REFERENCES = json.loads((ROOT / 'assets/hmong/voices.json').read_text(encoding='utf-8'))


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
def studio_page(site, *, hmong=True, ready=True, missing_reference_first=False, hmong_steps=16,
                transcript_verified=True, known_reference=True):
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
                'delivery': 'story' if hmong else 'natural', 'emotion': 'warm' if hmong else 'neutral',
                'emotion_strength': .65, 'auto_rhythm': hmong,
                **({'hardware_label': 'CỤC BỘ · CHƯA KIỂM TRA CPU/GPU'} if hmong else {}),
                'hmong_reference_note': 'Hai mẫu đi kèm dùng lời mẫu do bạn cung cấp và xác nhận khớp đoạn thu.'}
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
        elif path == '/api/hmong/reference-info':
            reference = PROJECT_REFERENCES['female']
            response = {'duration': reference['duration'], 'automatic': known_reference,
                        'known_preset': 'hmong-female' if known_reference else None,
                        'reference_start': reference['reference']['start'], 'reference_end': reference['reference']['end'],
                        'transcript': reference['reference']['text'] if known_reference else '',
                        'transcript_verified': transcript_verified if known_reference else False}
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
        playwright.expect(page.locator('#delivery')).to_have_value('story')
        playwright.expect(page.locator('#hmong-emotion')).to_have_value('warm')
        playwright.expect(page.locator('#hmong-emotion-strength')).to_have_value('0.65')
        playwright.expect(page.locator('#hmong-auto-rhythm')).to_be_checked()
        playwright.expect(page.locator('label[for="paragraph-pause"]')).to_contain_text('Nghỉ bổ sung')
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
        assert state['speech'][-1]['emotion'] == 'warm' and state['speech'][-1]['emotion_strength'] == .65
        assert state['speech'][-1]['auto_rhythm'] is True
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
        assert state['speech'][-1]['delivery'] == 'review'
        assert state['speech'][-1]['emotion'] == 'warm' and state['speech'][-1]['auto_rhythm'] is True
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
        assert state['speech'][-1]['delivery'] == 'story' and state['speech'][-1]['emotion'] == 'warm'
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


@pytest.mark.parametrize('transcript_verified', [True, False])
def test_known_source_prefill_honors_word_verification_and_keeps_words_editable(static_site, transcript_verified):
    with studio_page(static_site, transcript_verified=transcript_verified) as (page, state):
        playwright.expect(page.locator('#hmong-reference-note')).to_contain_text('do bạn cung cấp và xác nhận')
        page.locator('.nav-item[data-tab="clone"]').click()
        playwright.expect(page.locator('#panel-clone .page-heading p')).to_contain_text('lời do bạn cung cấp và xác nhận')
        page.locator('#clone-file').set_input_files(ROOT / 'assets/hmong' / PROJECT_REFERENCES['female']['file'])
        playwright.expect(page.locator('#transcript')).to_have_value(PROJECT_REFERENCES['female']['reference']['text'])
        playwright.expect(page.locator('#transcript')).to_be_editable()
        playwright.expect(page.locator('#clone-reference-info')).to_contain_text('do bạn cung cấp và xác nhận' if transcript_verified else 'chưa được xác minh khớp âm thanh')
        playwright.expect(page.locator('#clone-status')).to_contain_text('xác nhận khớp đoạn thu' if transcript_verified else 'chưa được xác minh')
        playwright.expect(page.locator('#clone-submit')).to_be_enabled()
        page.fill('#transcript', 'Kuv sau cov lus no rau kuv tus kheej.')
        playwright.expect(page.locator('#transcript')).to_have_value('Kuv sau cov lus no rau kuv tus kheej.')
        playwright.expect(page.locator('#clone-reference-info')).to_contain_text('Bạn đang sửa lời mẫu')
        assert state['errors'] == []


def test_unknown_reference_does_not_claim_verified_words(static_site):
    with studio_page(static_site, known_reference=False) as (page, state):
        page.locator('.nav-item[data-tab="clone"]').click()
        page.locator('#clone-file').set_input_files(ROOT / 'assets/hmong' / PROJECT_REFERENCES['female']['file'])
        playwright.expect(page.locator('#clone-reference-info')).to_contain_text('Nhập lời Hmong khớp chính xác')
        playwright.expect(page.locator('#transcript')).to_have_value('')
        playwright.expect(page.locator('#transcript')).to_be_editable()
        assert 'xác nhận' not in page.locator('#clone-status').inner_text()
        assert state['errors'] == []


def test_standard_mode_keeps_original_default_and_optional_transcript(static_site):
    with studio_page(static_site, hmong=False) as (page, state):
        playwright.expect(page.locator('#panel-dub')).to_be_visible()
        page.locator('.nav-item[data-tab="create"]').click()
        playwright.expect(page.locator('#hmong-settings')).to_be_hidden()
        playwright.expect(page.locator('#hmong-script-controls')).to_be_hidden()
        playwright.expect(page.locator('#nano-steps')).to_be_visible()
        # Existing standard UI's fast-start initializer selects zero pause.
        playwright.expect(page.locator('#paragraph-pause')).to_have_value('0')
        playwright.expect(page.locator('#delivery')).to_have_value('natural')
        assert page.locator('#transcript').get_attribute('required') is None
        page.fill('#script', 'Xin chào.')
        page.click('#generate')
        playwright.expect(page.locator('#output-title')).to_contain_text('đã sẵn sàng')
        assert all(field not in state['speech'][-1] for field in ['hmong_steps', 'emotion', 'emotion_strength', 'auto_rhythm'])
        assert state['speech'][-1]['paragraph_pause'] == 0
        assert state['errors'] == []


def test_hmong_expression_controls_sync_and_reach_workspace_dub_and_benchmark(static_site):
    with studio_page(static_site) as (page, state):
        page.locator('.nav-item[data-tab="dub"]').click()
        assert page.locator('#workspace-advanced').get_attribute('open') is None
        playwright.expect(page.locator('#dub-hmong-emotion')).to_be_visible()
        page.select_option('#dub-hmong-emotion', 'suspense')
        page.locator('#dub-hmong-emotion-strength').press('Home')
        page.uncheck('#dub-hmong-auto-rhythm')
        page.select_option('#dub-hmong-delivery', 'calm')
        page.fill('#dub-hmong-paragraph-pause', '0.2')
        playwright.expect(page.locator('#hmong-emotion')).to_have_value('suspense')
        playwright.expect(page.locator('#hmong-emotion-strength')).to_have_value('0')
        playwright.expect(page.locator('#hmong-auto-rhythm')).not_to_be_checked()
        playwright.expect(page.locator('#delivery')).to_have_value('calm')
        playwright.expect(page.locator('#paragraph-pause')).to_have_value('0.2')
        playwright.expect(page.locator('label[for="paragraph-pause"]')).to_have_text('Nghỉ giữa các câu/đoạn (giây)')
        text = 'Nyob zoo. [emotion=warm]Ua tsaug.'
        page.fill('#workspace-free-script', text)
        page.click('#workspace-free-generate')
        playwright.expect(page.locator('#workspace-free-status')).to_contain_text('Voice riêng đã sẵn sàng')
        assert state['speech'][-1]['text'] == text
        assert state['speech'][-1]['delivery'] == 'calm'
        assert state['speech'][-1]['emotion'] == 'suspense' and state['speech'][-1]['emotion_strength'] == 0
        assert state['speech'][-1]['auto_rhythm'] is False and state['speech'][-1]['paragraph_pause'] == .2
        page.select_option('#dub-hmong-emotion', 'joyful')
        playwright.expect(page.locator('#workspace-free-audio')).to_be_hidden()
        playwright.expect(page.locator('#workspace-free-status')).to_contain_text('Tạo voice riêng lại')
        page.locator('#workspace-advanced').evaluate('(node) => {node.open = true;}')
        page.locator('#workspace-advanced > details').first.evaluate('(node) => {node.open = true;}')
        srt = '1\n00:00:00,000 --> 00:00:04,000\n[emotion=warm]Nyob zoo.\n'
        page.locator('#dub-import').set_input_files({'name': 'story.srt', 'mimeType': 'text/plain', 'buffer': srt.encode()})
        playwright.expect(page.locator('#dub-script')).to_have_value(srt)
        page.click('#dub-voice-only')
        playwright.expect(page.locator('#dub-status')).to_contain_text('sẵn sàng')
        assert state['speech'][-1]['input_format'] == 'srt' and state['speech'][-1]['text'] == srt
        assert state['speech'][-1]['emotion'] == 'joyful' and state['speech'][-1]['emotion_strength'] == 0
        assert state['speech'][-1]['auto_rhythm'] is False
        page.locator('.nav-item[data-tab="create"]').click()
        page.click('#benchmark-speed')
        playwright.expect(page.locator('#benchmark-speed')).to_be_enabled()
        assert state['speech'][-1]['delivery'] == 'calm' and state['speech'][-1]['emotion'] == 'joyful'
        assert state['speech'][-1]['emotion_strength'] == 0 and state['speech'][-1]['auto_rhythm'] is False
        assert state['errors'] == []


def test_hmong_imports_preserve_expression_settings_and_inline_text(static_site):
    with studio_page(static_site) as (page, state):
        page.select_option('#hmong-emotion', 'serious')
        page.locator('#hmong-emotion-strength').evaluate("(node) => {node.value='0.85';node.dispatchEvent(new Event('input',{bubbles:true}));}")
        page.uncheck('#hmong-auto-rhythm')
        for name, text, kind in [('story.txt', 'Nyob zoo. **Ua tsaug.** [pause=0.5] [emotion=warm]Kuv tuaj.', 'txt'),
                                 ('story.srt', '1\n00:00:01,000 --> 00:00:05,000\n[emotion=joyful]Nyob zoo.\n', 'srt')]:
            page.locator('#import-script').set_input_files({'name': name, 'mimeType': 'text/plain', 'buffer': text.encode()})
            playwright.expect(page.locator('#script')).to_have_value(text)
            playwright.expect(page.locator('#script-format')).to_have_value(kind)
            playwright.expect(page.locator('#hmong-emotion')).to_have_value('serious')
            playwright.expect(page.locator('#hmong-emotion-strength')).to_have_value('0.85')
            playwright.expect(page.locator('#hmong-auto-rhythm')).not_to_be_checked()
            page.click('#generate')
            playwright.expect(page.locator('#generate')).to_be_enabled()
            assert state['speech'][-1]['text'] == text and state['speech'][-1]['input_format'] == kind
            assert state['speech'][-1]['emotion'] == 'serious' and state['speech'][-1]['emotion_strength'] == .85
            assert state['speech'][-1]['auto_rhythm'] is False
        assert state['errors'] == []


def test_hmong_phrase_buttons_insert_controls_without_replacing_other_words(static_site):
    with studio_page(static_site) as (page, state):
        page.fill('#script', 'Nyob zoo. Ua tsaug.')
        page.locator('#script').evaluate('(node) => {node.setSelectionRange(10,node.value.length);}')
        page.click('[data-hmong-emotion="sad"]')
        playwright.expect(page.locator('#script')).to_have_value('Nyob zoo. [emotion=sad] Ua tsaug. [emotion=warm] ')
        page.click('#hmong-insert-example')
        assert page.locator('#script').input_value().startswith('Nyob zoo. [emotion=sad] Ua tsaug.')
        assert '**Ua tsaug.** [pause=0.5] [emotion=warm]' in page.locator('#script').input_value()
        assert state['errors'] == []
