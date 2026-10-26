"""User-facing voice selection and clone recovery contracts (mocked HTTP)."""
from test_hmong_ui import PROJECT_REFERENCES, ROOT, playwright, pytestmark, static_site, studio_page  # noqa: F401
from test_voice_click_recovery import click_page


SOURCE = '217\n00:06:07,200 --> 00:06:08,400\nTae-yong cov ntaub ntawv tus kheej'


def test_main_srt_defaults_to_timeline_and_allows_explicit_speech_only(static_site):
    with click_page(static_site) as (page, state, *_):
        playwright.expect(page.locator('#voice')).to_have_value('hmong-male')
        page.locator('.nav-item[data-tab="create"]').click()
        page.locator('#script-format').select_option('srt')
        page.locator('#script').fill(SOURCE)
        playwright.expect(page.locator('#create-subtitle-timing')).to_be_checked()
        playwright.expect(page.locator('#srt-reading-note')).to_contain_text('Giữ đúng mốc')
        page.locator('#generate').click()
        playwright.expect(page.locator('#output-title')).to_contain_text('đã sẵn sàng')
        assert state['posts'][-1]['subtitle_timing'] is True
        assert state['posts'][-1]['cue_fit'] == 'adaptive'
        assert state['posts'][-1]['max_cue_tempo'] == 4
        assert state['posts'][-1]['text'] == SOURCE
        assert state['posts'][-1]['input_format'] == 'srt'
        page.locator('#create-subtitle-timing').uncheck()
        page.locator('#generate').click()
        playwright.expect(page.locator('#output-title')).to_contain_text('đã sẵn sàng')
        assert state['posts'][-1]['subtitle_timing'] is False
        assert 'cue_fit' not in state['posts'][-1]
        assert state['errors'] == []


def test_new_presets_and_preferred_voice_survive_reload_but_not_override_manual_refresh(static_site):
    with click_page(static_site) as (page, state, config, voices, _):
        # The fixture yields at DOMContentLoaded so startup-failure tests can
        # hold its API calls. Finish this initial bootstrap before changing the
        # simulated persisted preference and navigating to another document.
        playwright.expect(page.locator('#voice')).to_have_value('hmong-male')
        page.wait_for_function('studioInitialized === true && document.getElementById("workspace-version").textContent.includes("Voice Studio Hmong")')
        error_stacks = []
        page.on('pageerror', lambda error: error_stacks.append(error.stack))
        config['default_voice_id'] = 'hmong-female-3'
        voices.extend([{**voices[0], 'id': ident, 'name': name, 'builtin': True,
                        'sample_url': '/api/hmong/presets/' + ident + '/sample'}
                       for ident, name in [('hmong-female-3', 'Hmong nữ 3'),
                                           ('hmong-ngoc-huyen', 'Ngọc Huyền')]])
        defaults = []

        def preferred(route):
            ident = route.request.post_data_json['voice_id']
            defaults.append(ident)
            config['default_voice_id'] = ident
            route.fulfill(json={'default_voice_id': ident})

        page.route('**/api/voices/default', preferred)
        page.reload(wait_until='networkidle')
        for selector in ('#voice', '#dub-voice'):
            playwright.expect(page.locator(selector)).to_have_value('hmong-female-3')
        playwright.expect(page.locator('#hmong-voice-choices [data-hmong-voice="hmong-female-3"]')).to_have_attribute('aria-pressed', 'true')
        page.locator('.nav-item[data-tab="voices"]').click()
        page.locator('[data-default-voice="hmong-ngoc-huyen"]').click()
        assert defaults == ['hmong-ngoc-huyen']
        playwright.expect(page.locator('#voice')).to_have_value('hmong-ngoc-huyen')
        page.locator('.nav-item[data-tab="create"]').click()
        page.locator('#hmong-voice-choices [data-hmong-gender="male"]').click()
        page.locator('#voice-source').select_option('ai')
        page.evaluate('workspaceChooseReady(true)')
        assert page.locator('#voice-source').input_value() == 'ai'
        page.evaluate('refreshVoices()')
        playwright.expect(page.locator('#voice')).to_have_value('hmong-male')
        assert page.locator('#voice-source').input_value() == 'ai'
        page.reload(wait_until='networkidle')
        playwright.expect(page.locator('#voice')).to_have_value('hmong-ngoc-huyen')
        assert state['errors'] == [], error_stacks


def test_clone_file_selected_during_bootstrap_is_inspected_after_config_arrives(static_site):
    with click_page(static_site, hold='/api/config') as (page, state, config, *_):
        inspections = []

        def inspect(route):
            inspections.append(route.request)
            route.fulfill(json={'duration': 12, 'reference_start': 4, 'reference_end': 11,
                                'automatic': False, 'transcript': ''})

        page.route('**/api/hmong/reference-info', inspect)
        page.locator('.nav-item[data-tab="clone"]').click()
        page.locator('#clone-file').set_input_files(ROOT / 'assets/hmong' / PROJECT_REFERENCES['female']['file'])
        assert not inspections
        page.wait_for_function('document.querySelector("#clone-status").textContent.includes("kết nối")')
        assert len(state['pending']) == 1
        state['pending'].pop().fulfill(json=config)
        playwright.expect(page.locator('#clone-reference-end')).to_have_value('11')
        playwright.expect(page.locator('#clone-reference-start')).to_have_value('4')
        playwright.expect(page.locator('#clone-submit')).to_be_enabled()
        assert len(inspections) == 1
        assert state['errors'] == []


def test_confirmed_clone_is_usable_even_when_library_refresh_would_fail(static_site):
    with studio_page(static_site, native=True, known_reference=False) as (page, state):
        reads = []

        def unavailable(route):
            reads.append(route.request)
            route.fulfill(status=503, json={'detail': 'Thư viện tạm thời chưa tải được.'})

        page.route('**/api/voices', unavailable)
        page.locator('.nav-item[data-tab="clone"]').click()
        page.locator('#clone-name').fill('My external voice')
        page.locator('#clone-file').set_input_files(ROOT / 'assets/hmong' / PROJECT_REFERENCES['female']['file'])
        playwright.expect(page.locator('#clone-submit')).to_be_enabled()
        page.locator('#clone-form input[name="consent"]').check()
        page.locator('#clone-submit').click()
        playwright.expect(page.locator('#panel-create')).to_be_visible()
        playwright.expect(page.locator('#voice')).to_have_value('hmong-new-personal')
        assert len(state['clones']) == 1 and reads == []
        page.locator('#script').fill('Nyob zoo. Ua tsaug.')
        page.locator('#generate').click()
        playwright.expect(page.locator('#output-title')).to_contain_text('đã sẵn sàng')
        assert state['speech'][-1]['voice_id'] == 'hmong-new-personal'
        assert state['errors'] == []


def test_old_reference_reply_cannot_replace_the_newly_selected_file(static_site):
    with studio_page(static_site, native=True, known_reference=False) as (page, state):
        pending = []
        page.route('**/api/hmong/reference-info', lambda route: pending.append(route))
        page.locator('.nav-item[data-tab="clone"]').click()
        sample = (ROOT / 'assets/hmong' / PROJECT_REFERENCES['female']['file']).read_bytes()
        with page.expect_request('**/api/hmong/reference-info'):
            page.locator('#clone-file').set_input_files({'name': 'first.mp3', 'mimeType': 'audio/mpeg', 'buffer': sample})
        with page.expect_request('**/api/hmong/reference-info'):
            page.locator('#clone-file').set_input_files({'name': 'second.mp3', 'mimeType': 'audio/mpeg', 'buffer': sample})
        for _ in range(100):
            if len(pending) == 2:
                break
            page.wait_for_timeout(20)
        assert len(pending) == 2
        pending.pop().fulfill(json={'duration': 6, 'reference_start': 0, 'reference_end': 6,
                                    'automatic': False, 'transcript': ''})
        playwright.expect(page.locator('#clone-reference-end')).to_have_value('6')
        pending.pop().fulfill(json={'duration': 20, 'reference_start': 4, 'reference_end': 11,
                                    'automatic': False, 'transcript': ''})
        page.wait_for_timeout(80)
        assert page.locator('#clone-reference-end').input_value() == '6'
        assert page.evaluate('cloneReference.file.name') == 'second.mp3'
        assert state['errors'] == []


def test_pending_clone_cannot_be_posted_twice(static_site):
    with studio_page(static_site, native=True, known_reference=False) as (page, state):
        pending = []
        page.route('**/api/voices/clone', lambda route: pending.append(route))
        page.locator('.nav-item[data-tab="clone"]').click()
        page.locator('#clone-name').fill('A single saved profile')
        page.locator('#clone-file').set_input_files(ROOT / 'assets/hmong' / PROJECT_REFERENCES['female']['file'])
        playwright.expect(page.locator('#clone-submit')).to_be_enabled()
        page.locator('#clone-form input[name="consent"]').check()
        with page.expect_request('**/api/voices/clone'):
            page.locator('#clone-submit').click()
        playwright.expect(page.locator('#clone-submit')).to_be_disabled()
        page.evaluate("""() => {
            const form=document.querySelector('#clone-form');
            form.onsubmit({preventDefault(){},target:form,submitter:document.querySelector('#clone-submit')});
        }""")
        assert len(pending) == 1
        pending.pop().fulfill(status=201, json={'id': 'one-saved-profile', 'name': 'A single saved profile',
            'engine': 'hmong_native', 'language': 'mww', 'languages': ['mww'], 'category': 'cloned'})
        playwright.expect(page.locator('#voice')).to_have_value('one-saved-profile')
        assert state['errors'] == []


def test_clone_submit_recovers_bootstrap_failure_without_reselecting_file(static_site):
    with click_page(static_site, fail='/api/config', failures=2) as (page, state, *_):
        page.route('**/api/hmong/reference-info', lambda route: route.fulfill(json={
            'duration': 6, 'reference_start': 0, 'reference_end': 6,
            'automatic': False, 'transcript': ''}))
        saved = []

        def clone(route):
            saved.append(route.request)
            route.fulfill(status=201, json={'id': 'recovered-personal', 'name': 'Recovered voice',
                'engine': 'hmong_native', 'language': 'mww', 'languages': ['mww']})

        page.route('**/api/voices/clone', clone)
        page.locator('.nav-item[data-tab="clone"]').click()
        page.locator('#clone-name').fill('Recovered voice')
        page.locator('#clone-file').set_input_files(ROOT / 'assets/hmong' / PROJECT_REFERENCES['female']['file'])
        playwright.expect(page.locator('#clone-status')).to_contain_text('Kết nối tạm thời chưa sẵn sàng')
        playwright.expect(page.locator('#clone-submit')).to_be_enabled()
        page.locator('#clone-form input[name="consent"]').check()
        page.locator('#clone-submit').click()
        playwright.expect(page.locator('#panel-create')).to_be_visible()
        playwright.expect(page.locator('#voice')).to_have_value('recovered-personal')
        assert len(saved) == 1 and state['errors'] == []
