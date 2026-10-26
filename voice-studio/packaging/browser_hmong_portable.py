"""Gate a Windows portable release on real browser selection and real speech.

Playwright belongs to a separate QA environment. This script never replaces
HTTP responses, selects voices through the visible controls, and leaves model
inference to the already running, relocated application.
"""
from __future__ import annotations

import argparse
import array
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import sys
import time
from urllib.parse import urlparse
import wave
import zipfile


MALE = 'hmong-male'
FEMALE = 'hmong-female'
ADDITIONAL = ('hmong-ngoc-huyen', 'hmong-female-3')
SRT_SPOKEN_SAMPLE = '"217\n00:06:07,200 --> 00:06:08,400\nTae-yong cov ntaub ntawv tus kheej "'
SRT_SPOKEN_WORDS = 'Tae-yong cov ntaub ntawv tus kheej'
REPORT_NAME = 'browser-smoke.json'
HYPHENATED_SAMPLE = 'Nyob-zoo, kuv yog ib tug Hmoob.'
SAMPLE = 'Nyob zoo. Ua tsaug rau koj mloog.'
INVALID_SAMPLE = 'Nyob zoo https://example.com.'
CAPTION_SAMPLE = ('\ufeff1\n"00:04:28,533 --> 00:04:29,333"\nNyob zoo.\n'
                  '2\n99:59.500 --> 100:00.300\nKuv muaj 2 tug me nyuam.\n')
CAPTION_SPOKEN = 'Nyob zoo. Kuv muaj ob tug me nyuam.'
TIMED_USER_WORDS = (
    'Tus txiv neej taub hau do nqa ib tog ntoo hnyav tsib caug kilo ntaus rau daim iav kawg zog',
    'Tab sis daim iav muaj zog ntawd tseem tsis tawg li',
    'Thaum Win pom lo lus Made in China sau rau saum daim iav',
    'Nws thiaj xav tsis thoob kiag',
)
TIMED_USER_TIMES = ((.133, 3.066), (3.5, 5.166), (5.533, 8), (8.266, 9))
TIMED_USER_SAMPLE = ('"1\n00:00:00,133 --> 00:00:03,066\n' + TIMED_USER_WORDS[0]
    + '\n\n2\n00:00:03,500 --> 00:00:05,166\n' + TIMED_USER_WORDS[1]
    + '\n\n3\n00:00:05,533 --> 00:00:08,000\n' + TIMED_USER_WORDS[2]
    + '\n\n4\n00:00:08,266 --> 00:00:09,000\n' + TIMED_USER_WORDS[3] + '"')


def check_click_rejection(page, expect):
    """Reject a real unsupported draft and keep the visible editor recoverable."""
    script, button = page.locator('#script'), page.locator('#generate')
    script.fill(INVALID_SAMPLE)
    page.locator('#format').select_option('wav')
    page.locator('#script-format').select_option('txt')
    expect(button).to_be_enabled()
    requests = []

    def collect(request):
        if urlparse(request.url).path == '/api/speech' and request.method == 'POST':
            requests.append(request)

    page.on('request', collect)
    try:
        with page.expect_response(lambda response:
                urlparse(response.url).path == '/api/speech'
                and response.request.method == 'POST', timeout=30000) as pending:
            button.click()
        response = pending.value
        payload = response.request.post_data_json
        assert response.status == 422, response.text()
        assert payload['text'] == INVALID_SAMPLE and payload['voice_id'] == MALE
        assert payload['language'] == 'mww'
        detail = response.json()['detail']
        assert isinstance(detail, str) and detail.strip(), 'HTTP 422 must explain how to fix the draft'
        inline, output = page.locator('#generate-status'), page.locator('#output-subtitle')
        expect(inline).to_have_text(detail)
        expect(output).to_have_text(detail)
        expect(page.locator('#output-title')).to_have_text('Chưa tạo được bản thu')
        expect(button).to_be_enabled()
        assert script.input_value() == INVALID_SAMPLE, 'Rejected speech must preserve the editable draft'
        # Visibility must include the viewport: the original notice had a
        # nonzero box but was thousands of pixels above the clicked button.
        expect(inline).to_be_in_viewport()
        expect(output).to_be_in_viewport()
        page.wait_for_timeout(350)
        assert len(requests) == 1, 'A rejected speech POST must never be retried automatically'
        return {'success': True, 'real_ui_post': True, 'responses_mocked': False,
                'ui_entrypoint': '#generate', 'invalid_text': INVALID_SAMPLE,
                'request_text': payload['text'], 'request_voice_id': payload['voice_id'],
                'request_language': payload['language'], 'http_status': response.status,
                'request_count': len(requests), 'error_detail': detail,
                'inline_error': inline.inner_text(), 'output_error': output.inner_text(),
                'output_error_title': page.locator('#output-title').inner_text(),
                'inline_error_visible': True, 'output_error_visible': True,
                'button_unlocked': True, 'draft_preserved': True}
    finally:
        page.remove_listener('request', collect)


def check_release_features(page, context, get_json, expect, tab, references):
    """Use the actual editor, cast controls and completed chapter deliverable."""
    tab('create')
    script = page.locator('#script')
    expect(script).to_have_attribute('maxlength', '1000000')
    original = script.input_value()
    million = ('Nyob zoo. ' * 100001)[:1_000_000]
    script.fill(million)
    assert len(script.input_value()) == 1_000_000
    expect(page.locator('#longform-note')).to_be_visible()
    script.fill(original)

    completed = [job for job in get_json('/api/history')['items']
                 if job.get('qa_release_longform') and job.get('status') == 'done']
    assert len(completed) == 1, 'Native QA must leave one real two-part deliverable for browser validation'
    long_job = completed[0]
    assert long_job['chapter_count'] == 2 and long_job['longform'] is True
    tab('history')
    archive_link = page.locator('a[href="/api/jobs/' + long_job['id'] + '/archive"]')
    expect(archive_link).to_have_count(1)
    card = page.locator('.history-item').filter(has=archive_link)
    chapter_select = card.get_by_label('Chọn phần để nghe', exact=True)
    expect(chapter_select).to_be_visible()
    chapter_select.select_option('2')
    audio = card.locator('audio')
    expect(audio).to_have_attribute('src', '/api/jobs/' + long_job['id'] + '/chapters/2')
    audio.evaluate('async audio => { audio.muted=true; audio.currentTime=0; await audio.play(); }')
    page.wait_for_function('id => document.querySelector(`audio[src="/api/jobs/${id}/chapters/2"]`).currentTime > .05',
                           arg=long_job['id'], timeout=10000)
    playback = audio.evaluate('audio => { const r={ready_state:audio.readyState,media_error:audio.error?.code??null,current_time:audio.currentTime}; audio.pause(); return r; }')
    assert playback['ready_state'] >= 2 and playback['media_error'] is None
    with page.expect_download(timeout=30000) as pending:
        archive_link.click()
    download = pending.value
    assert download.failure() is None and download.suggested_filename.endswith('.zip')
    archive_bytes = Path(download.path()).read_bytes()
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        assert archive.testzip() is None
        manifest = json.loads(archive.read('manifest.json'))
        assert manifest['chapter_count'] == 2
        for chapter in manifest['chapters']:
            audio_evidence(archive.read(chapter['files']['audio']))
            assert archive.read(chapter['files']['txt']).strip()
            assert b'-->' in archive.read(chapter['files']['srt'])
    longform = {'success': True, 'million_character_editor': True,
                'million_character_synthesis_performed': False, 'real_archive': True,
                'chapter_selection': True, 'audio_playback_checked': True,
                'download_verified': True, 'archive_job_id': long_job['id'],
                'archive_sha256': hashlib.sha256(archive_bytes).hexdigest(),
                'completed_chapters': 2}

    tab('dub')
    videos = [item for item in get_json('/api/videos')['items'] if item['name'] == 'release-cast-qa.mp4']
    assert len(videos) == 1, 'A real builder-owned cast video is required'
    page.locator('#dub-existing').select_option(videos[0]['id'])
    expect(page.locator('#editor-character-add')).to_be_visible()
    srt = ('1\n00:00:00,000 --> 00:00:12,000\nNyob zoo.\n\n'
           '2\n00:00:12,000 --> 00:00:24,000\nUa tsaug.\n')
    page.locator('#editor-project-file').set_input_files({'name': 'release-cast.srt',
        'mimeType': 'application/x-subrip', 'buffer': srt.encode('utf-8')})
    expect(page.locator('#editor-cues select[data-cue-character]')).to_have_count(2)
    character_ids = []
    for index, ident in enumerate((MALE, FEMALE)):
        page.locator('#editor-character-add').click()
        row = page.locator('#editor-character-list .editor-character').nth(index)
        character = row.get_attribute('data-character-id')
        assert character
        row.locator('input').fill('Narrator' if index == 0 else 'Guest')
        row.locator('select[data-character-voice]').select_option(ident)
        page.locator('#editor-cues select[data-cue-character]').nth(index).select_option(character)
        character_ids.append(character)
    page.locator('#workspace-caption-language').select_option('mww')
    page.locator('#dub-language').select_option('mww')
    with page.expect_response(lambda response: urlparse(response.url).path == '/api/speech'
                              and response.request.method == 'POST', timeout=30000) as pending:
        page.locator('#workspace-voice').click()
    response = pending.value
    payload = response.request.post_data_json
    assert response.status == 202, response.text()
    assert payload['character_voices'] == dict(zip(character_ids, (MALE, FEMALE)))
    assert payload['cue_characters'] == character_ids and payload['input_format'] == 'srt'
    assert 'Narrator' not in payload['text'] and 'Guest' not in payload['text']
    ident = response.json()['id']
    deadline = time.monotonic() + 600
    while True:
        job = get_json('/api/jobs/' + ident)
        if job['status'] not in {'queued', 'running', 'cancelling'}:
            break
        assert time.monotonic() < deadline, 'Cast UI speech exceeded ten minutes'
        page.wait_for_timeout(300)
    assert job['status'] == 'done' and job['engine'] == 'hmong_native', job
    cast = job['character_cast']
    assert cast['cues'] == character_ids
    for character, voice in zip(character_ids, (MALE, FEMALE)):
        assert cast['voices'][character]['voice_id'] == cast['voices'][character]['speaker'] == voice
        assert cast['voices'][character]['hmong_reference_fingerprint'] == references[voice]
    wav = context.request.get('/api/audio/' + ident)
    assert wav.ok
    evidence = audio_evidence(wav.body())
    expect(page.locator('#workspace-audio')).to_be_visible(timeout=20000)
    expect(page.locator('#workspace-audio')).to_have_attribute('src', job['url'])
    with page.expect_download(timeout=30000) as pending:
        page.locator('#workspace-audio-download').click()
    downloaded = pending.value
    assert downloaded.failure() is None
    assert hashlib.sha256(Path(downloaded.path()).read_bytes()).hexdigest() == evidence['sha256']
    return {'longform': longform, 'character_cast': {'success': True, 'real_ui_post': True,
        'job_id': ident, 'status': job['status'], 'voice_ids': [MALE, FEMALE],
        'reference_identities_verified': True, 'character_names_not_spoken': True,
        'download_verified': True, 'cue_count': 2, **evidence}}


def audio_evidence(content):
    """Check downloaded PCM speech, independently of browser/API metadata."""
    with wave.open(io.BytesIO(content), 'rb') as source:
        rate, channels, width, frames = (source.getframerate(), source.getnchannels(),
                                         source.getsampwidth(), source.getnframes())
        assert rate == 24000 and channels in {1, 2}, 'Unexpected generated WAV format'
        assert width == 2 and source.getcomptype() == 'NONE', 'Generated WAV must contain PCM16'
        assert frames > rate / 3, 'Generated speech is too short'
        samples = array.array('h', source.readframes(frames))
    if sys.byteorder != 'little':
        samples.byteswap()
    assert len(samples) == frames * channels, 'Generated WAV is truncated'
    peak = max(abs(value) for value in samples) / 32768
    assert peak > .001, 'Generated speech is silent'
    return {'audio_bytes': len(content), 'audio_seconds': frames / rate,
            'sample_rate': rate, 'channels': channels, 'sample_width': width,
            'peak_amplitude': peak, 'sha256': hashlib.sha256(content).hexdigest()}


def launch_browser(driver):
    """Prefer the browsers already installed on GitHub's Windows runners."""
    failures = []
    args = ['--autoplay-policy=no-user-gesture-required']
    if sys.platform.startswith('linux'):
        args.append('--no-sandbox')
    for channel in ('msedge', 'chrome'):
        try:
            return driver.chromium.launch(channel=channel, headless=True, args=args), channel
        except Exception as error:
            failures.append(channel + ': ' + str(error).splitlines()[0])
    executable = shutil.which('chromium') or shutil.which('chromium-browser')
    if executable:
        try:
            return driver.chromium.launch(executable_path=executable, headless=True,
                                           args=args), 'system-chromium'
        except Exception as error:
            failures.append('system-chromium: ' + str(error).splitlines()[0])
    # A separately installed QA browser is allowed, but no browser is downloaded
    # by the package builder or added to the portable runtime.
    if Path(driver.chromium.executable_path).is_file():
        try:
            return driver.chromium.launch(headless=True, args=args), 'playwright-chromium'
        except Exception as error:
            failures.append('playwright-chromium: ' + str(error).splitlines()[0])
    raise RuntimeError('A real installed browser is required; no UI check may be skipped. '
                       + ' | '.join(failures))


def run(url, reports, expected_references, *, allow_non_windows=False, external_reference=None,
        expected_additional_references=None):
    """Write a mandatory browser report; raise if any release check fails."""
    reports = Path(reports)
    reports.mkdir(parents=True, exist_ok=True)
    result = {'success': False, 'platform': sys.platform,
              'native_windows_validation': sys.platform == 'win32',
              'engine': 'hmong_native', 'real_ui_synthesis': False,
              'browser': {}, 'runtime': {}, 'voices': {}, 'cases': [],
              'expected_reference_fingerprints': expected_references,
              'expected_additional_reference_fingerprints': expected_additional_references,
              'cloned_filter_library_selection': False,
              'cross_panel_selection': False, 'hyphenated_text_preserved': False,
              'page_errors': [],
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
              'pronunciation_evaluated': False, 'target_30x_verified': False}
    browser = None
    try:
        assert sys.platform == 'win32' or allow_non_windows, \
            'Release browser QA must execute on real Windows'
        parsed = urlparse(url)
        assert parsed.scheme == 'http' and parsed.hostname == '127.0.0.1' and parsed.port, \
            'Only the builder-owned local application may be checked'
        assert parsed.path in {'', '/'} and not parsed.query and not parsed.fragment
        assert isinstance(expected_references, dict) and set(expected_references) == {MALE, FEMALE}
        assert all(isinstance(value, str) and re.fullmatch(r'[a-f0-9]{64}', value)
                   for value in expected_references.values()), 'Missing independently verified reference identities'
        assert isinstance(expected_additional_references, dict) and set(expected_additional_references) == set(ADDITIONAL)
        assert all(re.fullmatch(r'[a-f0-9]{64}', value) for value in expected_additional_references.values())
        from playwright.sync_api import expect, sync_playwright
        with sync_playwright() as driver:
            browser, channel = launch_browser(driver)
            result['browser'] = {'channel': channel, 'version': browser.version,
                                 'headless': True, 'responses_mocked': False}
            context = browser.new_context(base_url=url, accept_downloads=True,
                                           viewport={'width': 1440, 'height': 1100})
            context.set_default_timeout(20000)
            page = context.new_page()
            page.on('pageerror', lambda error: result['page_errors'].append(str(error)))

            def get_json(path):
                response = context.request.get(path, timeout=20000)
                assert response.ok, f'Application request failed: {path}: {response.status}'
                return response.json()

            config = get_json('/api/config')
            assert config['variant'] == 'hmong' and config['hmong_engine'] == 'hmong_native'
            assert config['hmong_backend'] == 'native' and config['models']['hmong_native'] is True
            result['runtime'] = get_json('/api/runtime')
            assert result['runtime']['backend'] == 'hmong_native'
            assert result['runtime']['url'].rstrip('/') == url.rstrip('/')
            assert result['runtime']['version'] == config['version']
            result['application_version'] = config['version']
            assert config['default_voice_id'] == 'hmong-female-3'
            result['initial_voice_id'] = config['default_voice_id']
            voices = get_json('/api/voices')['voices']
            presets = {voice['id']: voice for voice in voices if voice['id'] in {MALE, FEMALE}}
            assert set(presets) == {MALE, FEMALE}
            assert all(voice['ready'] is not False and voice['engine'] == 'hmong_native'
                       for voice in presets.values())
            additional_presets = {voice['id']: voice for voice in voices if voice['id'] in ADDITIONAL}
            assert set(additional_presets) == set(ADDITIONAL)
            assert all(voice['ready'] is not False and voice['engine'] == 'hmong_native'
                       and voice['reference_conditioning'] == 'audio'
                       for voice in additional_presets.values())
            page.goto(url, wait_until='networkidle')
            expect(page).to_have_title('Voice Studio Hmong')
            expect(page.locator('#panel-create')).to_be_visible()
            expect(page.locator('#voice')).to_have_value('hmong-female-3')
            expect(page.locator('#dub-voice')).to_have_value('hmong-female-3')
            assert config['subtitle_timing_default'] is True
            assert page.locator('#create-subtitle-timing').is_checked()
            result['timed_subtitles'] = {'success': False, 'default_checked': True, 'cases': {}}

            def tab(name):
                page.locator('.nav-item[data-tab="' + name + '"]').click()
                expect(page.locator('#panel-' + name)).to_be_visible()

            def selected(ident):
                expect(page.locator('#voice')).to_have_value(ident)
                expect(page.locator('#dub-voice')).to_have_value(ident)
                gender = ident.removeprefix('hmong-')
                other = 'female' if gender == 'male' else 'male'
                for scope in ('#hmong-voice-choices', '#workspace-hmong-voice-choices'):
                    expect(page.locator(scope + ' [data-hmong-gender="' + gender + '"]')).to_have_attribute('aria-pressed', 'true')
                    expect(page.locator(scope + ' [data-hmong-gender="' + other + '"]')).to_have_attribute('aria-pressed', 'false')

            def explicit(gender, workspace=False):
                scope = '#workspace-hmong-voice-choices' if workspace else '#hmong-voice-choices'
                button = page.locator(scope + ' [data-hmong-gender="' + gender + '"]')
                expect(button).to_be_visible()
                expect(button).to_be_enabled()
                button.click()
                selected('hmong-' + gender)
                for selector in ('#create-native', '#workspace-native'):
                    expect(page.locator(selector)).to_have_value('all')

            render_references = dict(expected_references)
            render_references.update(expected_additional_references)

            def synthesize(name, ident, text=SAMPLE, workspace=False, *, record_case=True, custom=False,
                           input_format='txt', subtitle_timing=True, auto_detect=False,
                           source_filename=None):
                script = '#workspace-free-script' if workspace else '#script'
                button = '#workspace-free-generate' if workspace else '#generate'
                audio = '#workspace-free-audio' if workspace else '#output-audio'
                if not workspace:
                    page.locator('#format').select_option('wav')
                    page.locator('#script-format').select_option('txt' if auto_detect else input_format)
                if source_filename:
                    assert not workspace
                    page.locator('#import-script').set_input_files({'name': source_filename,
                        'mimeType': 'text/plain' if source_filename.endswith('.txt') else 'application/x-subrip',
                        'buffer': text.encode('utf-8')})
                    expect(page.locator(script)).to_have_value(text)
                else:
                    page.locator(script).fill(text)
                effective_format = 'srt' if auto_detect else input_format
                if not workspace:
                    if auto_detect:
                        expect(page.locator('#script-format')).to_have_value('srt')
                    else:
                        page.locator('#script-format').select_option(effective_format)
                    if effective_format == 'srt':
                        page.locator('#create-subtitle-timing').set_checked(subtitle_timing)
                expect(page.locator(button)).to_be_enabled()
                started = time.monotonic()
                with page.expect_response(lambda response:
                        urlparse(response.url).path == '/api/speech'
                        and response.request.method == 'POST', timeout=30000) as pending:
                    page.locator(button).click()
                response = pending.value
                payload = response.request.post_data_json
                assert payload['voice_id'] == ident and payload['language'] == 'mww', payload
                assert payload['text'] == text and payload['format'] == 'wav', payload
                if effective_format == 'srt':
                    assert payload['input_format'] == 'srt' and payload['subtitle_timing'] is subtitle_timing
                assert 'hmong_steps' not in payload, 'Native UI must not request F5 steps'
                assert response.status == 202, response.text()
                queued = response.json()
                deadline = time.monotonic() + 600
                while True:
                    job = get_json('/api/jobs/' + queued['id'])
                    if job['status'] not in {'queued', 'running', 'cancelling'}:
                        break
                    assert time.monotonic() < deadline, 'Browser speech did not finish within ten minutes'
                    page.wait_for_timeout(300)
                assert job['status'] == 'done', job
                assert job['voice_id'] == ident and job['speaker'] == (None if custom else ident), job
                assert job['hmong_reference_fingerprint'] == render_references[ident], job
                assert job['text'] == text, 'The stored job must preserve the original UI text'
                assert job['engine'] == 'hmong_native' and job['hmong_backend'] == 'vits_openvoice_v2'
                assert job['hmong_steps'] is None and job['hmong_precision'] == 'fp32'
                assert job['hmong_device'] == 'cpu', 'Release browser gate validates the shipped CPU runtime'
                assert job['require_complete_audio'] is True and job['speech_complete'] is True
                audio_response = context.request.get(job['url'])
                assert audio_response.ok and audio_response.headers['content-type'].split(';')[0] == 'audio/wav'
                evidence = audio_evidence(audio_response.body())
                assert abs(evidence['audio_seconds'] - job['audio_seconds']) < .05
                expect(page.locator(audio)).to_be_visible(timeout=20000)
                expect(page.locator(audio)).to_have_attribute('src', job['url'], timeout=20000)
                page.locator(audio).evaluate('''async audio => {
                    audio.muted = true;
                    audio.currentTime = 0;
                    await audio.play();
                }''')
                page.wait_for_function('selector => document.querySelector(selector).currentTime > 0.05',
                                       arg=audio, timeout=10000)
                playback = page.locator(audio).evaluate('''audio => {
                    const evidence = {ready_state: audio.readyState, duration: audio.duration,
                                      current_time: audio.currentTime, muted: audio.muted,
                                      media_error: audio.error ? audio.error.code : null};
                    audio.pause(); return evidence;
                }''')
                assert playback['ready_state'] >= 2 and playback['media_error'] is None
                assert playback['duration'] > 1 / 3 and playback['current_time'] > .05
                if workspace:
                    page.locator('#workspace-free-format').select_option('wav')
                    download_button = '#workspace-free-download'
                else:
                    download_button = '#download'
                with page.expect_download(timeout=30000) as pending_download:
                    page.locator(download_button).click()
                download = pending_download.value
                assert download.failure() is None, 'The browser download failed'
                downloaded = Path(download.path()).read_bytes()
                assert hashlib.sha256(downloaded).hexdigest() == evidence['sha256'], \
                    'The downloaded UI WAV differs from the generated audio'
                record = {'case': name, 'voice_id': ident, 'post_voice_id': payload['voice_id'],
                          'speaker': job['speaker'], 'job_id': job['id'], 'status': job['status'],
                          'hmong_reference_fingerprint': job['hmong_reference_fingerprint'],
                          'engine': job['engine'], 'hmong_backend': job['hmong_backend'],
                          'hmong_steps': job['hmong_steps'], 'hmong_precision': job['hmong_precision'],
                          'hmong_device': job['hmong_device'], 'text': text,
                          'hmong_audio_profile': job['hmong_audio_profile'],
                          'original_text_preserved': job['text'] == text,
                          'input_format': job['input_format'], 'subtitle_timing': job.get('subtitle_timing', True),
                          'requested_input_format': input_format, 'auto_detected_from_txt': auto_detect,
                          'source_filename': source_filename, 'require_complete_audio': job['require_complete_audio'],
                          'speech_complete': job['speech_complete'], 'cue_fit': job['cue_fit'],
                          'max_cue_tempo': job['max_cue_tempo'],
                          'timing_warnings': job.get('timing_warnings', []),
                          'ui_entrypoint': button, 'real_ui_post': True,
                          'playback': playback, 'audio_playback_checked': True,
                          'download_verified': True,
                          'wall_seconds': round(time.monotonic() - started, 3), **evidence}
                if record_case:
                    result['cases'].append(record)
                return record

            explicit('male')
            result['click_recovery'] = check_click_rejection(page, expect)
            result['voices'][MALE] = synthesize('main_male_button', MALE, HYPHENATED_SAMPLE)
            result['click_recovery'].update({
                'recovery_case': 'main_male_button',
                'recovery_job_id': result['voices'][MALE]['job_id'],
                'recovered_audio_sha256': result['voices'][MALE]['sha256'],
                'recovery_succeeded': True})
            result['hyphenated_text_preserved'] = True
            explicit('female')
            result['voices'][FEMALE] = synthesize('main_female_button', FEMALE)

            # Reproduce the reported failure: a preset picked in the library
            # must override the main personal-voice filter and allow synthesis.
            page.locator('#create-native').select_option('cloned')
            expect(page.locator('#create-native')).to_have_value('cloned')
            tab('voices')
            card = page.locator('.voice-card').filter(has=page.get_by_role('heading', name=presets[MALE]['name'], exact=True))
            expect(card).to_have_count(1)
            card.get_by_role('button', name='Sử dụng giọng →', exact=True).click()
            expect(page.locator('#panel-create')).to_be_visible()
            selected(MALE)
            expect(page.locator('#create-native')).to_have_value('all')
            expect(page.locator('#workspace-native')).to_have_value('all')
            expect(page.locator('#generate')).to_be_enabled()
            synthesize('library_preset_after_cloned_filter', MALE)
            result['cloned_filter_library_selection'] = True

            # Main female selection must survive navigation and reach the
            # standalone workspace POST and the worker's verified reference.
            explicit('female')
            tab('dub')
            selected(FEMALE)
            synthesize('main_female_to_workspace_speech', FEMALE, workspace=True)
            explicit('male', workspace=True)
            tab('create')
            selected(MALE)
            expect(page.locator('#generate')).to_be_enabled()
            result['cross_panel_selection'] = True
            result['cross_panel_directions'] = {'main_female_to_workspace': True,
                                                'workspace_male_to_main': True}
            # Keep the ordinary selectors usable as well as the new buttons.
            page.locator('#voice').select_option(FEMALE)
            selected(FEMALE)
            tab('dub')
            page.locator('#dub-voice').select_option(MALE)
            selected(MALE)
            result['dropdown_selection'] = True
            tab('create')
            explicit('male')
            caption = synthesize('caption_metadata_as_txt', MALE, CAPTION_SAMPLE,
                                 record_case=False, auto_detect=True, subtitle_timing=False)
            exported = context.request.get('/api/jobs/' + caption['job_id'] + '/export.txt')
            assert exported.ok
            spoken = ' '.join(exported.text().split())
            assert spoken == CAPTION_SPOKEN, 'Only caption words may enter the speech/export plan'
            assert 1 / 3 < caption['audio_seconds'] < 30, 'TXT clocks must not create timestamp silence'
            result['caption_metadata'] = {**caption, 'success': True,
                'exported_spoken_text': spoken,
                'timestamps_not_spoken': True, 'cue_indices_not_spoken': True,
                'continuous_txt_duration': True}
            only_words = synthesize('quoted_217_srt_speech_only', MALE, SRT_SPOKEN_SAMPLE,
                                    record_case=False, input_format='srt', subtitle_timing=False)
            exported = context.request.get('/api/jobs/' + only_words['job_id'] + '/export.txt')
            generated_srt = context.request.get('/api/jobs/' + only_words['job_id'] + '/script.srt')
            assert exported.ok and generated_srt.ok
            assert ' '.join(exported.text().split()) == SRT_SPOKEN_WORDS
            assert 1 / 3 < only_words['audio_seconds'] < 30
            generated_text = generated_srt.text().replace('\r\n', '\n')
            assert generated_text.startswith('1\n00:00:00,000 --> ')
            assert '00:06:07,200' not in generated_text and '217\n' not in generated_text
            result['srt_speech_only'] = {**only_words, 'success': True,
                'exported_spoken_text': SRT_SPOKEN_WORDS,
                'generated_srt': generated_text, 'generated_timing_checked': True,
                'timestamps_not_spoken': True, 'cue_indices_not_spoken': True,
                'continuous_srt_duration': True}
            for kind in ('srt', 'txt'):
                timed = synthesize('user_four_cue_' + kind, MALE, TIMED_USER_SAMPLE,
                    record_case=False, input_format=kind, subtitle_timing=True,
                    auto_detect=kind == 'txt', source_filename='user-four-cues.' + kind)
                exported = context.request.get('/api/jobs/' + timed['job_id'] + '/export.txt')
                generated = context.request.get('/api/jobs/' + timed['job_id'] + '/script.srt')
                assert exported.ok and generated.ok
                sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
                from subtitles import parse_srt
                expected = [dict(start=start, end=end, text=words)
                    for (start, end), words in zip(TIMED_USER_TIMES, TIMED_USER_WORDS)]
                assert parse_srt(generated.text()) == expected
                spoken = ' '.join(exported.text().split())
                assert spoken == ' '.join(TIMED_USER_WORDS), 'Timed audio must retain every source word'
                alignment = get_json('/api/jobs/' + timed['job_id'] + '/alignment')
                assert alignment['sync_ok'] is True and alignment['mode'] == 'adaptive'
                assert len(alignment['cues']) == 4 and abs(timed['audio_seconds'] - 9) < 1/24000
                for measured, cue in zip(alignment['cues'], expected):
                    assert measured['status'] == 'matched'
                    assert measured['start'] == cue['start'] and measured['end'] == cue['end']
                    assert measured['spoken_text'] == cue['text']
                    assert abs(measured['spoken_start'] - cue['start']) <= .001
                    assert measured['spoken_end'] <= cue['end'] + .001
                result['timed_subtitles']['cases'][kind] = {**timed, 'success': True,
                    'exported_spoken_text': spoken, 'generated_srt': generated.text().replace('\r\n', '\n'),
                    'alignment': alignment, 'cue_count': 4, 'all_source_words_retained': True,
                    'exact_timeline_seconds': 9, 'source_import_format': kind,
                    'real_file_import': True, 'timestamps_not_spoken': True, 'cue_indices_not_spoken': True}
            result['timed_subtitles']['success'] = True
            additional_metadata = json.loads((Path(__file__).resolve().parents[1]
                / 'assets/hmong/additional-voices.json').read_text(encoding='utf-8'))
            result['additional_presets'] = {}
            for ident in ADDITIONAL:
                metadata = additional_metadata[ident]
                page.locator('#hmong-voice-choices [data-hmong-voice="' + ident + '"]').click()
                expect(page.locator('#voice')).to_have_value(ident)
                expect(page.locator('#dub-voice')).to_have_value(ident)
                source = context.request.get(additional_presets[ident]['sample_url'])
                assert source.ok and hashlib.sha256(source.body()).hexdigest() == metadata['sha256']
                refbytes = (Path(__file__).resolve().parents[1] / 'assets/hmong' / metadata['reference_file']).read_bytes()
                assert hashlib.sha256(refbytes).hexdigest() == metadata['reference_sha256']
                identity = hashlib.sha256(json.dumps({'version': 1,
                    'audio_sha256': metadata['reference_sha256'], 'transcript': ''},
                    ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
                assert identity == expected_additional_references[ident]
                added = synthesize('additional_preset_' + ident, ident, record_case=False)
                snapshot = get_json('/api/jobs/' + added['job_id'])['hmong_voice_snapshot']
                assert snapshot['reference_text'] == '' and snapshot['speaker'] == ident
                result['additional_presets'][ident] = {**added, 'success': True,
                    'source_sha256': metadata['sha256'],
                    'reference_audio_sha256': metadata['reference_sha256'],
                    'reference_conditioning': 'audio', 'no_transcript': True,
                    'preset_button_checked': True, 'full_source_preview_checked': True}
            assert external_reference is not None, 'A real non-Hmong reference is required'
            external = Path(external_reference)
            assert external.is_file() and external.name == 'external-english-reference.wav'
            external_bytes = external.read_bytes()
            tab('clone')
            page.locator('#clone-name').fill('English reference QA')
            with page.expect_response(lambda response:
                    urlparse(response.url).path == '/api/hmong/reference-info'
                    and response.request.method == 'POST', timeout=30000) as pending:
                page.locator('#clone-file').set_input_files(str(external))
            info = pending.value
            assert info.status == 200 and info.json()['requires_transcript'] is False
            expect(page.locator('#clone-reference-start')).to_be_enabled()
            page.locator('#clone-reference-start').fill('0')
            page.locator('#clone-reference-end').fill('5')
            page.locator('#transcript').fill('')
            page.locator('#clone-form input[name="consent"]').check()
            with page.expect_response(lambda response:
                    urlparse(response.url).path == '/api/voices/clone'
                    and response.request.method == 'POST', timeout=30000) as pending:
                page.locator('#clone-submit').click()
            response = pending.value
            assert response.status == 201, response.text()
            profile = response.json()
            custom_id = profile['id']
            assert custom_id not in expected_references and profile['transcript'] == ''
            assert profile['reference_conditioning'] == 'audio' and profile['cross_language_reference'] is True
            assert profile['source_sha256'] == hashlib.sha256(external_bytes).hexdigest()
            expect(page.locator('#panel-create')).to_be_visible()
            expect(page.locator('#voice')).to_have_value(custom_id)
            expect(page.locator('#dub-voice')).to_have_value(custom_id)
            reference_response = context.request.get('/api/voices/' + custom_id + '/sample')
            assert reference_response.ok
            reference_bytes = reference_response.body()
            (reports / 'external-clone-reference.wav').write_bytes(reference_bytes)
            reference = audio_evidence(reference_bytes)
            assert abs(reference['audio_seconds'] - 5) < .001
            identity = hashlib.sha256(json.dumps({'version': 1,
                'audio_sha256': reference['sha256'], 'transcript': ''},
                ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
            assert identity not in expected_references.values()
            render_references[custom_id] = identity
            # The old bug changed the visible personal dropdown while the
            # canonical selection and other panel still pointed to a preset.
            # Check automatic filter adoption before explicitly choosing the
            # newly imported English reference.
            explicit('male')
            page.locator('#create-native').select_option('cloned')
            adopted = page.locator('#voice').input_value()
            assert re.fullmatch(r'[a-f0-9]{32}', adopted) and adopted not in presets
            expect(page.locator('#dub-voice')).to_have_value(adopted)
            expect(page.locator('#create-native')).to_have_value('cloned')
            adopted_profile = next(voice for voice in get_json('/api/voices')['voices']
                                   if voice['id'] == adopted)
            adopted_sample = context.request.get('/api/voices/' + adopted + '/sample')
            assert adopted_sample.ok
            adopted_reference = audio_evidence(adopted_sample.body())
            adopted_words = adopted_profile.get('transcript', '')
            assert isinstance(adopted_words, str)
            adopted_identity = hashlib.sha256(json.dumps({'version': 1,
                'audio_sha256': adopted_reference['sha256'], 'transcript': adopted_words},
                ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
            render_references[adopted] = adopted_identity
            auto_personal = synthesize('personal_filter_main_auto_speech', adopted,
                                       record_case=False, custom=True)
            expect(page.locator('#create-native')).to_have_value('cloned')
            expect(page.locator('#voice')).to_have_value(adopted)
            expect(page.locator('#dub-voice')).to_have_value(adopted)
            auto_personal = {**auto_personal, 'success': True,
                'reference_audio_sha256': adopted_reference['sha256'],
                'reference_text': adopted_words, 'independent_reference_fingerprint': adopted_identity,
                'selection_after_filter_without_manual_choice': True, 'default_fallback': False}
            page.locator('#voice').select_option(custom_id)
            expect(page.locator('#dub-voice')).to_have_value(custom_id)
            custom = synthesize('external_english_reference_to_hmong', custom_id,
                                record_case=False, custom=True)
            result['external_clone'] = {**custom, 'success': True,
                'source_language': 'en', 'output_language': 'mww',
                'reference_conditioning': 'audio', 'no_transcript': True,
                'cross_language_reference': True, 'auto_selected': True,
                'source_sha256': profile['source_sha256'],
                'reference_audio_sha256': reference['sha256'],
                'reference_seconds': reference['audio_seconds'],
                'independent_reference_fingerprint': identity,
                'default_fallback': False, 'perceptual_similarity_evaluated': False}
            tab('dub')
            page.locator('#workspace-native').select_option('cloned')
            expect(page.locator('#workspace-native')).to_have_value('cloned')
            expect(page.locator('#dub-voice')).to_have_value(custom_id)
            expect(page.locator('#voice')).to_have_value(custom_id)
            filtered = synthesize('personal_filter_workspace_speech', custom_id,
                                 workspace=True, record_case=False, custom=True)
            expect(page.locator('#workspace-native')).to_have_value('cloned')
            expect(page.locator('#dub-voice')).to_have_value(custom_id)
            expect(page.locator('#voice')).to_have_value(custom_id)
            result['clone_filter_selection'] = {**filtered, 'success': True,
                'main_filter_auto_speech': auto_personal,
                'main_filter_adopted_voice_id': adopted, 'main_filter_other_panel_voice_id': adopted,
                'main_filter_preserved': True, 'workspace_filter_preserved': True,
                'main_filter_value': 'cloned', 'workspace_filter_value': 'cloned',
                'main_job_id': custom['job_id'], 'main_reference_fingerprint': identity,
                'workspace_selected_voice_id': custom_id, 'main_selected_voice_id': custom_id,
                'independent_reference_fingerprint': identity, 'default_fallback': False,
                'perceptual_similarity_evaluated': False}
            result['features_1_6'] = check_release_features(page, context, get_json, expect, tab,
                                                         expected_references)
            assert not result['page_errors'], result['page_errors']
            assert len(result['cases']) == 4 and set(result['voices']) == {MALE, FEMALE}
            result['real_ui_synthesis'] = True
            result['success'] = True
            context.close()
            browser.close()
            browser = None
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        # Always leave evidence of failure. A missing browser/dependency is a
        # failed release gate, never an optional/empty successful UI report.
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
        (reports / REPORT_NAME).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('PASS: real ' + ('Windows ' if sys.platform == 'win32' else 'development ') +
          'browser click-error recovery, male/female selection, library filter recovery, '
          'cross-panel speech, playback, downloads and verified references.', flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--reports', required=True, type=Path)
    parser.add_argument('--expected-references', required=True,
                        help='JSON map of preset IDs to fingerprints verified by the packaged runtime.')
    parser.add_argument('--allow-non-windows', action='store_true',
                        help='Local development only; this report cannot pass the Windows release gate.')
    parser.add_argument('--external-reference', required=True, type=Path,
                        help='Builder-owned five-second English reference, independent of default voices.')
    parser.add_argument('--expected-additional-references', required=True,
                        help='Exact JSON fingerprints of the two additional user-supplied native voices.')
    args = parser.parse_args()
    run(args.url, args.reports, json.loads(args.expected_references),
        allow_non_windows=args.allow_non_windows, external_reference=args.external_reference,
        expected_additional_references=json.loads(args.expected_additional_references))


if __name__ == '__main__':
    main()
