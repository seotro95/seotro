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


MALE = 'hmong-male'
FEMALE = 'hmong-female'
REPORT_NAME = 'browser-smoke.json'
HYPHENATED_SAMPLE = 'Nyob-zoo, kuv yog ib tug Hmoob.'
SAMPLE = 'Nyob zoo. Ua tsaug rau koj mloog.'


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


def run(url, reports, expected_references, *, allow_non_windows=False):
    """Write a mandatory browser report; raise if any release check fails."""
    reports = Path(reports)
    reports.mkdir(parents=True, exist_ok=True)
    result = {'success': False, 'platform': sys.platform,
              'native_windows_validation': sys.platform == 'win32',
              'engine': 'hmong_native', 'real_ui_synthesis': False,
              'browser': {}, 'runtime': {}, 'voices': {}, 'cases': [],
              'expected_reference_fingerprints': expected_references,
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
            voices = get_json('/api/voices')['voices']
            presets = {voice['id']: voice for voice in voices if voice['id'] in {MALE, FEMALE}}
            assert set(presets) == {MALE, FEMALE}
            assert all(voice['ready'] is not False and voice['engine'] == 'hmong_native'
                       for voice in presets.values())
            page.goto(url, wait_until='networkidle')
            expect(page).to_have_title('Voice Studio Hmong')
            expect(page.locator('#panel-create')).to_be_visible()
            expect(page.locator('#voice')).to_have_value(MALE)
            expect(page.locator('#dub-voice')).to_have_value(MALE)

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

            def synthesize(name, ident, text=SAMPLE, workspace=False):
                script = '#workspace-free-script' if workspace else '#script'
                button = '#workspace-free-generate' if workspace else '#generate'
                audio = '#workspace-free-audio' if workspace else '#output-audio'
                page.locator(script).fill(text)
                if not workspace:
                    page.locator('#format').select_option('wav')
                    page.locator('#script-format').select_option('txt')
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
                assert job['voice_id'] == job['speaker'] == ident, job
                assert job['hmong_reference_fingerprint'] == expected_references[ident], job
                assert job['text'] == text, 'The stored job must preserve the original UI text'
                assert job['engine'] == 'hmong_native' and job['hmong_backend'] == 'vits_openvoice_v2'
                assert job['hmong_steps'] is None and job['hmong_precision'] == 'fp32'
                assert job['hmong_device'] == 'cpu', 'Release browser gate validates the shipped CPU runtime'
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
                          'original_text_preserved': job['text'] == text,
                          'ui_entrypoint': button, 'real_ui_post': True,
                          'playback': playback, 'audio_playback_checked': True,
                          'download_verified': True,
                          'wall_seconds': round(time.monotonic() - started, 3), **evidence}
                result['cases'].append(record)
                return record

            explicit('male')
            result['voices'][MALE] = synthesize('main_male_button', MALE, HYPHENATED_SAMPLE)
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
          'browser male/female selection, library filter recovery, '
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
    args = parser.parse_args()
    run(args.url, args.reports, json.loads(args.expected_references),
        allow_non_windows=args.allow_non_windows)


if __name__ == '__main__':
    main()
