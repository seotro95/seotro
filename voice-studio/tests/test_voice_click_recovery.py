"""Browser regressions for visible speech failures and recoverable startup.

Speech responses are mocked here; real portable inference has a separate gate.
"""
import contextlib
import os
import shutil
import sys
from urllib.parse import urlparse

import pytest

from test_hmong_ui import playwright, static_site  # noqa: F401

CHROMIUM = shutil.which('chromium') or shutil.which('chromium-browser')
CHANNEL = os.environ.get('HMOOB_BROWSER_CHANNEL') or ('msedge' if sys.platform == 'win32' else None)
pytestmark = pytest.mark.skipif(not CHANNEL and not CHROMIUM, reason='Browser checks need Chromium or HMOOB_BROWSER_CHANNEL')


@contextlib.contextmanager
def click_page(site, *, fail=None, failures=1, hold=None, hmong=True):
    language = 'mww' if hmong else 'vi'
    engine = 'hmong_native' if hmong else 'vieneu'
    male = 'hmong-male' if hmong else 'vi-maianh'
    female = 'hmong-female' if hmong else 'vi-other'
    state = {'fail': fail, 'failures': failures, 'hold': hold, 'pending': [], 'posts': [], 'errors': [], 'reads': {}}
    config = {'variant': 'hmong' if hmong else 'standard', 'app_name': 'Voice Studio Hmong' if hmong else 'Voice Studio',
              'version': '1.6.3-hmong', 'default_language': language, 'languages': {language: 'Hmong' if hmong else 'Tiếng Việt'},
              'subtitle_languages': {language: 'Hmong'}, 'ai_voice_languages': [language], 'models': {engine: True},
              'hmong_backend': 'native', 'hmong_engine': engine, 'hmong_ready': True, 'nano_ready': False,
              'hardware': 'CPU', 'cpu_cores': 4, 'available_ram_gb': 8, 'max_characters': 1000000,
              'delivery': 'story', 'emotion': 'warm', 'emotion_strength': .65, 'auto_rhythm': False}
    voices = [{'id': ident, 'name': name, 'engine': engine, 'languages': [language], 'native_language': language,
               'ready': True, 'description': 'Giọng kiểm tra'} for ident, name in [(male, 'Nam'), (female, 'Nữ')]]

    def job(ident='click-job', status='done'):
        return {'id': ident, 'status': status, 'voice_name': 'Nam', 'progress': 100 if status == 'done' else 0,
                'audio_seconds': 2, 'format': 'wav', 'url': '/api/audio/' + ident}

    def handle(route):
        path = urlparse(route.request.url).path
        state['reads'][path] = state['reads'].get(path, 0) + 1
        if path == state['fail'] and state['failures']:
            state['failures'] -= 1
            route.fulfill(status=503, json={'detail': 'Kết nối tạm thời chưa sẵn sàng.'})
            return
        if path == state['hold']:
            state['pending'].append(route)
            return
        if path == '/api/config':
            response = config
        elif path in ['/api/voices', '/api/voices/refresh']:
            response = {'voices': voices}
        elif path == '/api/speech':
            payload = route.request.post_data_json
            state['posts'].append(payload)
            response = job()
        elif path == '/api/jobs/click-job':
            response = job()
        elif path in ['/api/history', '/api/videos']:
            response = {'items': []}
        elif path == '/api/writing/connections':
            response = {'providers': {'ollama': False}, 'local': {'connected': False, 'models': []},
                        'defaults': {'ollama': 'qwen3:4b'}}
        else:
            response = {}
        route.fulfill(status=200, json=response)

    with playwright.sync_playwright() as driver:
        launch = {'headless': True}
        if CHANNEL:
            launch['channel'] = CHANNEL
        else:
            launch['executable_path'] = CHROMIUM
            launch['args'] = ['--no-sandbox']
        browser = driver.chromium.launch(**launch)
        page = browser.new_page(viewport={'width': 1365, 'height': 900})
        page.on('pageerror', lambda error: state['errors'].append(str(error)))
        page.route('**/api/**', handle)
        page.goto(site, wait_until='domcontentloaded')
        try:
            yield page, state, config, voices, job
        finally:
            browser.close()


def ready(page):
    playwright.expect(page.locator('#voice')).to_have_value('hmong-male')
    playwright.expect(page.locator('#panel-create')).to_be_visible()


@pytest.mark.parametrize('endpoint', ['/api/config', '/api/voices'])
def test_transient_startup_failure_recovers_without_reload_and_preserves_preferences(static_site, endpoint):
    with click_page(static_site, fail=endpoint) as (page, state, *_):
        # A click during the retry waits for complete config and voices.
        page.locator('.nav-item[data-tab="create"]').click()
        page.locator('#script').fill('Nyob zoo. Ua tsaug.')
        page.locator('#generate').click()
        playwright.expect(page.locator('#output-title')).to_contain_text('đã sẵn sàng')
        assert len(state['posts']) == 1 and state['posts'][0]['language'] == 'mww'
        assert page.locator('#language option').count() == 1
        page.locator('#hmong-voice-choices [data-hmong-gender="female"]').click()
        page.locator('#voice-source').select_option('ai')
        page.locator('#create-native').select_option('mww')
        page.locator('#delivery').select_option('review')
        page.locator('#voice-refresh-voices').click()
        playwright.expect(page.locator('#voice-refresh-voices')).to_be_enabled()
        assert page.locator('#voice').input_value() == 'hmong-female'
        assert page.locator('#voice-source').input_value() == 'ai'
        assert page.locator('#create-native').input_value() == 'mww'
        assert page.locator('#delivery').input_value() == 'review'
        assert page.locator('#language option').count() == 1
        assert state['errors'] == []


@pytest.mark.parametrize('recovery', ['retry', 'refresh', 'generate'])
def test_exhausted_config_failure_recovers_using_visible_controls(static_site, recovery):
    with click_page(static_site, fail='/api/config', failures=2) as (page, state, *_):
        page.locator('.nav-item[data-tab="create"]').click()
        page.locator('#script').fill('Kuv xav khaws cov lus no.')
        playwright.expect(page.locator('#voice-retry-studio')).to_be_visible()
        playwright.expect(page.locator('#generate-status')).to_contain_text('Không kết nối được studio')
        assert page.locator('#generate').is_enabled()
        if recovery == 'retry':
            page.locator('#voice-retry-studio').click()
        elif recovery == 'refresh':
            page.locator('#voice-refresh-voices').click()
        else:
            page.locator('#generate').click()
        ready(page)
        if recovery != 'generate':
            page.locator('#generate').click()
        playwright.expect(page.locator('#output-title')).to_contain_text('đã sẵn sàng')
        assert len(state['posts']) == 1
        assert state['posts'][0]['text'] == 'Kuv xav khaws cov lus no.'
        assert page.locator('#hmong-voice-choices').is_visible()
        assert page.locator('#language option').count() == 1
        assert state['errors'] == []


def test_http_validation_error_is_visible_at_clicked_button_and_preserves_exact_draft(static_site):
    with click_page(static_site) as (page, state, *_):
        ready(page)
        message = 'Văn bản có ký tự chưa được hỗ trợ: /. Hãy bỏ đường dẫn khỏi lời đọc.'
        def invalid(route):
            state['posts'].append(route.request.post_data_json)
            route.fulfill(status=422, json={'detail': message, 'field': 'text', 'code': 'unsupported_characters',
                                           'unsupported_characters': ['/']})
        page.route('**/api/speech', invalid)
        original = 'Nyob zoo https://example.com.'
        page.locator('#script').fill(original)
        page.locator('#generate').click()
        playwright.expect(page.locator('#generate-status')).to_have_text(message)
        playwright.expect(page.locator('#output-title')).to_have_text('Chưa tạo được bản thu')
        playwright.expect(page.locator('#output-subtitle')).to_have_text(message)
        playwright.expect(page.locator('#generate')).to_be_enabled()
        assert page.locator('#script').input_value() == original
        assert len(state['posts']) == 1
        assert page.locator('#notice').bounding_box()['y'] < 0
        box = page.locator('#generate-status').bounding_box()
        assert 0 <= box['y'] < 900, box
        assert state['errors'] == []


def test_network_failure_is_local_and_does_not_retry_speech_automatically(static_site):
    with click_page(static_site) as (page, state, *_):
        ready(page)
        calls = []
        def disconnected(route):
            calls.append(route.request.post_data_json)
            route.abort('failed')
        page.route('**/api/speech', disconnected)
        page.locator('#script').fill('Nyob zoo.')
        page.locator('#generate').click()
        playwright.expect(page.locator('#generate-status')).to_contain_text('Mất kết nối với tool')
        playwright.expect(page.locator('#output-title')).to_have_text('Chưa tạo được bản thu')
        playwright.expect(page.locator('#generate')).to_be_enabled()
        page.wait_for_timeout(400)
        assert len(calls) == 1
        assert page.locator('#script').input_value() == 'Nyob zoo.'
        assert state['errors'] == []


def test_pending_post_cannot_be_duplicated_by_voice_changes_or_repeated_handler_calls(static_site):
    with click_page(static_site, hold='/api/speech') as (page, state, _config, _voices, job):
        ready(page)
        page.locator('#script').fill('Nyob zoo.')
        page.locator('#generate').click()
        playwright.expect(page.locator('#generate-status')).to_have_text('Đang gửi yêu cầu tạo giọng…')
        assert len(state['pending']) == 1
        page.locator('#hmong-voice-choices [data-hmong-gender="female"]').click()
        playwright.expect(page.locator('#generate')).to_be_disabled()
        page.evaluate('void document.querySelector("#generate").onclick()')
        assert len(state['pending']) == 1
        route = state['pending'].pop()
        state['hold'] = None
        route.fulfill(status=202, json=job())
        playwright.expect(page.locator('#output-title')).to_contain_text('đã sẵn sàng')
        playwright.expect(page.locator('#generate')).to_be_enabled()
        assert state['errors'] == []


@pytest.mark.parametrize('hmong', [True, False])
def test_initial_loading_click_waits_for_atomic_bootstrap(static_site, hmong):
    with click_page(static_site, hold='/api/config', hmong=hmong) as (page, state, config, _voices, _job):
        page.locator('.nav-item[data-tab="create"]').click()
        page.locator('#script').fill('Nyob zoo.' if hmong else 'Xin chào.')
        page.locator('#generate').click()
        playwright.expect(page.locator('#generate-status')).to_contain_text('Đang kết nối studio')
        playwright.expect(page.locator('#generate')).to_be_disabled()
        assert page.locator('#voice option').count() == 0
        assert state['posts'] == [] and len(state['pending']) == 1
        route = state['pending'].pop()
        state['hold'] = None
        route.fulfill(status=200, json=config)
        playwright.expect(page.locator('#output-title')).to_contain_text('đã sẵn sàng')
        playwright.expect(page.locator('#panel-create')).to_be_visible()
        assert len(state['posts']) == 1
        assert state['errors'] == []


def test_model_not_ready_and_empty_filter_give_local_feedback_instead_of_dead_button(static_site):
    with click_page(static_site) as (page, state, _config, voices, _job):
        ready(page)
        page.locator('#script').fill('Nyob zoo.')
        page.locator('#create-native').select_option('cloned')
        playwright.expect(page.locator('#generate')).to_be_enabled()
        page.locator('#generate').click()
        playwright.expect(page.locator('#generate-status')).to_contain_text('Chưa có giọng phù hợp')
        assert state['posts'] == []
        for voice in voices:
            voice['ready'] = False
        page.locator('#create-native').select_option('all')
        page.locator('#voice-refresh-voices').click()
        playwright.expect(page.locator('#voice-refresh-voices')).to_be_enabled()
        page.locator('#generate').click()
        playwright.expect(page.locator('#generate-status')).to_contain_text('Giọng chưa tải model')
        playwright.expect(page.locator('#output-subtitle')).to_contain_text('Giọng chưa tải model')
        assert state['posts'] == [] and state['errors'] == []


def test_accepted_job_worker_error_reaches_both_local_status_and_output(static_site):
    with click_page(static_site) as (page, state, _config, _voices, job):
        ready(page)
        page.route('**/api/speech', lambda route: route.fulfill(status=202, json=job(status='queued')))
        page.route('**/api/jobs/click-job', lambda route: route.fulfill(status=200,
                   json={**job(status='error'), 'error': 'Không tải được model đã chọn.'}))
        page.locator('#script').fill('Nyob zoo.')
        page.locator('#generate').click()
        playwright.expect(page.locator('#generate-status')).to_have_text('Không tải được model đã chọn.')
        playwright.expect(page.locator('#output-title')).to_have_text('Chưa tạo được bản thu')
        playwright.expect(page.locator('#output-subtitle')).to_have_text('Không tải được model đã chọn.')
        playwright.expect(page.locator('#generate')).to_be_enabled()
        assert page.locator('#output-audio').is_hidden()
        assert state['errors'] == []


@pytest.mark.parametrize('stale_source', ['poll', 'history'])
def test_late_previous_job_response_cannot_overwrite_new_rejection(static_site, stale_source):
    with click_page(static_site, hold='/api/history' if stale_source == 'history' else None) as (page, state, _config, _voices, job):
        ready(page)
        stale = []
        posts = []
        def speech(route):
            posts.append(route.request.post_data_json)
            if stale_source == 'poll' and len(posts) == 1:
                route.fulfill(status=202, json=job('previous-job', status='queued'))
            else:
                route.fulfill(status=422, json={'detail': 'Kịch bản mới có ký tự chưa hỗ trợ.'})
        page.route('**/api/speech', speech)
        page.route('**/api/jobs/previous-job', lambda route: stale.append(route))
        if stale_source == 'poll':
            page.locator('#script').fill('Nyob zoo.')
            page.locator('#generate').click()
            page.wait_for_function('document.querySelector("#output-title").textContent.includes("hàng đợi")')
            assert len(stale) == 1
        else:
            page.wait_for_timeout(100)
            assert len(state['pending']) == 1
        page.locator('#script').fill('Nyob zoo https://example.com.')
        page.locator('#generate').click()
        playwright.expect(page.locator('#output-subtitle')).to_have_text('Kịch bản mới có ký tự chưa hỗ trợ.')
        if stale_source == 'poll':
            stale.pop().fulfill(status=200, json=job('previous-job'))
        else:
            state['pending'].pop().fulfill(status=200, json={'items': [job('previous-job')]})
        page.wait_for_timeout(200)
        playwright.expect(page.locator('#generate-status')).to_have_text('Kịch bản mới có ký tự chưa hỗ trợ.')
        playwright.expect(page.locator('#output-title')).to_have_text('Chưa tạo được bản thu')
        playwright.expect(page.locator('#output-subtitle')).to_have_text('Kịch bản mới có ký tự chưa hỗ trợ.')
        assert state['errors'] == []


@pytest.mark.parametrize('endpoint', ['/api/config','/api/voices'])
def test_free_text_button_recovers_bootstrap_without_sending_empty_voice(static_site, endpoint):
    with click_page(static_site, fail=endpoint, failures=2) as (page, state, *_):
        page.wait_for_function("!document.getElementById('voice-retry-studio').hidden")
        playwright.expect(page.locator('#panel-dub')).to_be_visible()
        page.locator('#workspace-free-script').fill('Nyob zoo. Ua tsaug.')
        page.locator('#workspace-free-generate').click()
        playwright.expect(page.locator('#workspace-free-audio')).to_have_attribute('src','/api/audio/click-job')
        assert len(state['posts'])==1
        assert state['posts'][0]['voice_id']=='hmong-male' and state['posts'][0]['language']=='mww'
        assert page.locator('#workspace-free-script').input_value()=='Nyob zoo. Ua tsaug.'
        playwright.expect(page.locator('#panel-dub')).to_be_visible()
        assert not page.locator('#workspace-free-generate').is_disabled()
        assert state['errors']==[]
