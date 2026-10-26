"""Timed imports and the actual filter path must retain the chosen clone.

HTTP is mocked; portable Windows inference provides the separate audio gate.
"""
from test_hmong_ui import playwright, pytestmark, static_site, studio_page  # noqa: F401
from test_voice_click_recovery import click_page


USER_SRT = ('"1\n00:00:00,133 --> 00:00:03,066\n'
    'Tus txiv neej taub hau do nqa ib tog ntoo hnyav tsib caug kilo ntaus rau daim iav kawg zog\n\n'
    '2\n00:00:03,500 --> 00:00:05,166\nTab sis daim iav muaj zog ntawd tseem tsis tawg li\n\n'
    '3\n00:00:05,533 --> 00:00:08,000\nThaum Win pom lo lus Made in China sau rau saum daim iav\n\n'
    '4\n00:00:08,266 --> 00:00:09,000\nNws thiaj xav tsis thoob kiag"')


def test_pasted_timed_script_keeps_every_source_word_and_uses_bounded_adaptive_fit(static_site):
    with click_page(static_site) as (page, state, *_):
        playwright.expect(page.locator('#voice')).to_have_value('hmong-male')
        page.locator('#script').fill(USER_SRT)
        playwright.expect(page.locator('#script-format')).to_have_value('srt')
        playwright.expect(page.locator('#create-subtitle-timing')).to_be_checked()
        page.locator('#generate').click()
        playwright.expect(page.locator('#output-title')).to_contain_text('đã sẵn sàng')
        payload = state['posts'][-1]
        assert payload['text'] == USER_SRT
        assert payload['input_format'] == 'srt' and payload['subtitle_timing'] is True
        assert payload['cue_fit'] == 'adaptive' and payload['max_cue_tempo'] == 4
        assert state['errors'] == []


def test_txt_import_detects_timestamps_and_keeps_explicit_continuous_choice(static_site):
    with click_page(static_site) as (page, state, *_):
        playwright.expect(page.locator('#voice')).to_have_value('hmong-male')
        page.locator('.nav-item[data-tab="create"]').click()
        conversions = []
        def convert(route):
            conversions.append(route.request.post_data_json)
            route.fulfill(json={'text': USER_SRT})
        page.route('**/api/scripts/convert', convert)
        page.locator('#script-format').select_option('srt')
        page.locator('#create-subtitle-timing').uncheck()
        page.locator('#script-format').select_option('txt')
        page.locator('#import-script').set_input_files({'name': 'lo lus.txt',
            'mimeType': 'text/plain', 'buffer': USER_SRT.encode('utf-16')})
        playwright.expect(page.locator('#script')).to_have_value(USER_SRT)
        playwright.expect(page.locator('#script-format')).to_have_value('srt')
        playwright.expect(page.locator('#create-subtitle-timing')).not_to_be_checked()
        assert conversions == [{'text': USER_SRT, 'input_format': 'srt', 'output_format': 'srt'}]
        page.evaluate('refreshVoices()')
        page.evaluate('workspaceChooseReady(true)')
        playwright.expect(page.locator('#create-subtitle-timing')).not_to_be_checked()
        page.locator('#generate').click()
        playwright.expect(page.locator('#output-title')).to_contain_text('đã sẵn sàng')
        assert state['posts'][-1]['subtitle_timing'] is False
        assert 'cue_fit' not in state['posts'][-1]
        assert state['posts'][-1]['text'] == USER_SRT
        assert state['errors'] == []


def test_main_filter_auto_selects_personal_voice_and_late_workspace_keeps_it(static_site):
    with studio_page(static_site, native=True, voice_choices=True) as (page, state):
        page.wait_for_function('studioInitialized === true')
        page.select_option('#create-native', 'cloned')
        for select in ('#voice', '#dub-voice'):
            playwright.expect(page.locator(select)).to_have_value('hmong-personal')
        assert page.evaluate('hmongVoiceId') == 'hmong-personal'
        page.evaluate('workspaceChooseReady(true)')
        page.evaluate('refreshVoices()')
        playwright.expect(page.locator('#create-native')).to_have_value('cloned')
        page.locator('#script').fill('Nyob zoo. Ua tsaug.')
        page.locator('#generate').click()
        playwright.expect(page.locator('#output-title')).to_contain_text('đã sẵn sàng')
        assert state['speech'][-1]['voice_id'] == 'hmong-personal'
        page.locator('.nav-item[data-tab="dub"]').click()
        page.locator('#workspace-free-script').fill('Nyob zoo.')
        page.locator('#workspace-free-generate').click()
        playwright.expect(page.locator('#workspace-free-status')).to_contain_text('sẵn sàng')
        assert len(state['speech']) == 2 and state['speech'][-1]['voice_id'] == 'hmong-personal'
        page.evaluate('async()=>{workspaceChooseReady(true);await refreshVoices();workspaceChooseReady();}')
        assert page.evaluate('workspaceFreeVoice.voice_id') == 'hmong-personal'
        playwright.expect(page.locator('#workspace-free-audio')).to_be_visible()
        assert state['errors'] == []


def test_workspace_filter_adopts_clone_and_does_not_restore_default_when_empty(static_site):
    with studio_page(static_site, native=True, voice_choices=True) as (page, state):
        page.wait_for_function('studioInitialized === true')
        page.locator('.nav-item[data-tab="dub"]').click()
        page.select_option('#workspace-native', 'cloned')
        playwright.expect(page.locator('#workspace-native')).to_have_value('cloned')
        for select in ('#voice', '#dub-voice'):
            playwright.expect(page.locator(select)).to_have_value('hmong-personal')
        page.evaluate('workspaceChooseReady(true)')
        page.locator('#workspace-free-script').fill('Nyob zoo.')
        page.locator('#workspace-free-generate').click()
        playwright.expect(page.locator('#workspace-free-status')).to_contain_text('sẵn sàng')
        assert state['speech'][-1]['voice_id'] == 'hmong-personal'
        # A refreshed library may no longer contain a personal voice (for
        # example, it was deleted elsewhere). An empty personal filter must
        # stay empty instead of silently narrating with a builtin voice.
        page.evaluate("voices=voices.filter(v=>v.category!=='cloned');updateDubVoices();workspaceChooseReady(true)")
        assert page.locator('#dub-voice').input_value() == ''
        assert page.locator('#workspace-native').input_value() == 'cloned'
        assert page.evaluate('hmongVoiceId') == 'hmong-personal'
        assert state['errors'] == []


def test_standard_srt_keeps_existing_timing_controls_and_no_hmong_adaptive_override(static_site):
    with click_page(static_site, hmong=False) as (page, state, *_):
        playwright.expect(page.locator('#voice')).to_have_value('vi-maianh')
        assert page.locator('#workspace-sync-mode').input_value() == 'strict'
        assert page.locator('#workspace-sync-tempo').input_value() == '2'
        page.locator('.nav-item[data-tab="create"]').click()
        page.locator('#script-format').select_option('srt')
        page.locator('#script').fill(USER_SRT)
        page.locator('#generate').click()
        playwright.expect(page.locator('#output-title')).to_contain_text('đã sẵn sàng')
        assert state['posts'][-1]['subtitle_timing'] is True
        assert 'cue_fit' not in state['posts'][-1] and 'max_cue_tempo' not in state['posts'][-1]
        assert state['errors'] == []


def test_completed_timed_voice_shows_fast_cue_notice_without_reporting_failure(static_site):
    with click_page(static_site) as (page, state, _, _, job):
        playwright.expect(page.locator('#voice')).to_have_value('hmong-male')
        page.locator('.nav-item[data-tab="create"]').click()
        notice = 'Câu SRT 4 cần đọc nhanh 2.5 lần. Nới mốc để giữ nhịp tự nhiên hơn.'
        def result(route):
            if route.request.method == 'POST':
                state['posts'].append(route.request.post_data_json)
            route.fulfill(json={**job(), 'timing_warnings': [notice]})
        page.route('**/api/speech', result)
        page.route('**/api/jobs/click-job', result)
        page.locator('#script').fill(USER_SRT)
        page.locator('#generate').click()
        playwright.expect(page.locator('#output-title')).to_contain_text('đã sẵn sàng')
        playwright.expect(page.locator('#generate-status')).to_contain_text(notice)
        assert 'error-message' not in page.locator('#generate-status').get_attribute('class')
        assert state['errors'] == []
