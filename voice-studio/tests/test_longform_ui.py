"""Browser contracts for long Hmong scripts and chapter archive playback."""
from test_hmong_ui import PROJECT_REFERENCES, ROOT, playwright, static_site, studio_page  # noqa: F401


def chapter_job(**changes):
    ident = 'c' * 32
    return {'id': ident, 'status': 'done', 'progress': 100, 'voice_name': 'Hmong Nữ',
            'language': 'mww', 'created_at': '2026-10-24T00:00:00Z', 'text': 'Nyob zoo. Ua tsaug.',
            'input_format': 'txt', 'longform': True, 'format': 'mp3', 'audio_seconds': 12,
            'url': f'/api/jobs/{ident}/archive', 'chapters': [
                {'index': 1, 'id': 'd' * 32, 'characters': 20000, 'audio_seconds': 5, 'format': 'mp3'},
                {'index': 2, 'id': 'e' * 32, 'characters': 1000, 'audio_seconds': 7, 'format': 'mp3'}],
            **changes}


def test_hmong_configured_million_limit_imports_large_unicode_and_submits_every_character(static_site):
    with studio_page(static_site, native=True) as (page, state):
        page.evaluate('config.max_characters=1000000;updateScriptLimits();')
        playwright.expect(page.locator('#script')).to_have_attribute('maxlength', '1000000')
        playwright.expect(page.locator('#char-count')).to_contain_text('/ 1.000.000')
        playwright.expect(page.locator('#longform-note')).to_contain_text('không dừng ở mốc 3 giờ')
        # Three-byte characters prove the import allows a 3 MB UTF-8 manuscript.
        text = '漢' * 1000000
        page.locator('#import-script').set_input_files(
            {'name': 'long-story.txt', 'mimeType': 'text/plain', 'buffer': text.encode('utf-8')})
        playwright.expect(page.locator('#char-count')).to_have_text('1.000.000 / 1.000.000 ký tự')
        page.click('#generate')
        playwright.expect(page.locator('#output-title')).to_contain_text('đã sẵn sàng')
        assert state['speech'][-1]['text'] == text
        page.locator('#import-script').set_input_files(
            {'name': 'too-long.txt', 'mimeType': 'text/plain', 'buffer': b'x' * 1000001})
        playwright.expect(page.locator('#notice')).to_contain_text('Tối đa 1.000.000 ký tự')
        assert page.locator('#script').input_value() == text
        assert state['errors'] == []


def test_standard_script_keeps_two_hundred_thousand_limit(static_site):
    with studio_page(static_site, hmong=False) as (page, state):
        playwright.expect(page.locator('#script')).to_have_attribute('maxlength', '200000')
        playwright.expect(page.locator('#char-count')).to_have_text('0 / 200.000 ký tự')
        playwright.expect(page.locator('#longform-note')).to_be_hidden()
        page.locator('#import-script').set_input_files(
            {'name': 'too-long.txt', 'mimeType': 'text/plain', 'buffer': b'x' * 200001})
        playwright.expect(page.locator('#notice')).to_contain_text('Tối đa 200.000 ký tự')
        assert page.locator('#script').input_value() == ''
        assert state['errors'] == []


def test_archive_output_history_and_dub_preview_chapters_instead_of_zip(static_site):
    job = chapter_job()
    with studio_page(static_site, native=True) as (page, state):
        page.evaluate('(job)=>{activeOutputId=job.id;setOutput(job);}', job)
        playwright.expect(page.locator('#download')).to_have_attribute('href', job['url'])
        playwright.expect(page.locator('#download')).to_have_attribute('download', 'voice-studio-cccccccc.zip')
        playwright.expect(page.locator('#download')).to_contain_text('ZIP · 2 phần MP3')
        playwright.expect(page.locator('#output-audio')).to_have_attribute('src', '/api/jobs/' + job['id'] + '/chapters/1')
        page.select_option('#output-chapter', '2')
        playwright.expect(page.locator('#output-audio')).to_have_attribute('src', '/api/jobs/' + job['id'] + '/chapters/2')
        # Polling the same completed job keeps the user's selected chapter.
        page.evaluate('setOutput', job)
        playwright.expect(page.locator('#output-chapter')).to_have_value('2')
        page.evaluate('updateDub', job)
        playwright.expect(page.locator('#dub-audio')).to_have_attribute('src', '/api/jobs/' + job['id'] + '/chapters/1')
        playwright.expect(page.locator('#dub-audio-download')).to_have_attribute('download', 'voice-studio-cccccccc.zip')
        page.route('**/api/history', lambda route: route.fulfill(json={'items': [job]}))
        page.locator('.nav-item[data-tab="history"]').click()
        history = page.locator('#history-list')
        playwright.expect(history.locator('audio')).to_have_attribute('src', '/api/jobs/' + job['id'] + '/chapters/1')
        history.get_by_label('Chọn phần để nghe').select_option('2')
        playwright.expect(history.locator('audio')).to_have_attribute('src', '/api/jobs/' + job['id'] + '/chapters/2')
        playwright.expect(history.get_by_text('Tải ZIP · 2 phần MP3 ↓')).to_have_attribute('href', job['url'])
        assert not page.locator('audio[src$="/archive"]').count()
        page.evaluate('setOutput', chapter_job(status='queued', chapters=[]))
        assert page.locator('#output-audio').get_attribute('src') is None
        assert state['errors'] == []


def test_saved_reference_quality_guidance_is_visible_without_similarity_score(static_site):
    with studio_page(static_site, native=True, voice_choices=True) as (page, state):
        voice = {'id': 'hmong-new-personal', 'name': 'Hmong mới', 'engine': 'hmong_native',
                 'languages': ['mww'], 'native_language': 'mww', 'category': 'cloned',
                 'ready': True, 'description': 'Mẫu vừa lưu', 'quality': {
                     'advisories': ['Mẫu có tiếng nền nhẹ.'],
                     'guidance': 'Thu gần micro trong phòng yên tĩnh để giữ chất giọng.'}}
        def save(route):
            state['clones'].append(voice)
            route.fulfill(json=voice)
        page.route('**/api/voices/clone', save)
        page.locator('.nav-item[data-tab="clone"]').click()
        page.fill('#clone-name', 'Hmong mới')
        page.locator('#clone-file').set_input_files(ROOT / 'assets/hmong' / PROJECT_REFERENCES['female']['file'])
        playwright.expect(page.locator('#clone-submit')).to_be_enabled()
        page.check('#clone-form input[name="consent"]')
        page.click('#clone-submit')
        playwright.expect(page.locator('#notice')).to_contain_text('Mẫu có tiếng nền nhẹ.')
        playwright.expect(page.locator('#notice')).to_contain_text('Thu gần micro')
        assert '100%' not in page.locator('#notice').inner_text()
        assert state['errors'] == []


def test_advanced_dub_uses_cast_only_for_matching_current_editor_srt(static_site):
    with studio_page(static_site, native=True, voice_choices=True) as (page, state):
        page.evaluate("""() => {
            dubSource={id:'c'.repeat(32),duration:10};editorVideoId=dubSource.id;
            editorCharacters=[{id:'hero',name:'Tub',voice_id:'hmong-male'}];
            editorCues=[{id:'cue-a',start:0,end:2,text:'Nyob zoo.',character_id:'hero'}];
            $('dub-format').value='srt';$('dub-script').value=editorSrt(editorCues);
        }""")
        page.evaluate('submitDub(false)')
        assert state['speech'][-1]['character_voices'] == {'hero': 'hmong-male'}
        assert state['speech'][-1]['cue_characters'] == ['hero']
        # A different valid raw SRT stays usable even if the old editor is now invalid.
        page.evaluate("""() => {
            editorCues[0].text='';
            $('dub-script').value='1\\n00:00:00,000 --> 00:00:02,000\\nUa tsaug.';
        }""")
        page.evaluate('submitDub(false)')
        assert len(state['speech']) == 2
        assert 'character_voices' not in state['speech'][-1]
        assert 'cue_characters' not in state['speech'][-1]
        page.evaluate("""() => {
            editorCues[0].text='Nyob zoo.';$('dub-script').value=editorSrt(editorCues);
            editorVideoId='e'.repeat(32);
        }""")
        page.evaluate('submitDub(false)')
        assert len(state['speech']) == 3
        assert 'character_voices' not in state['speech'][-1]
        assert state['errors'] == []


def test_longform_srt_export_downloads_chapter_zip_with_correct_extension(static_site):
    job = chapter_job()
    with studio_page(static_site, native=True) as (page, state):
        page.route('**/api/jobs/' + job['id'], lambda route: route.fulfill(json=job))
        page.route('**' + job['url'], lambda route: route.fulfill(
            content_type='application/zip', body=b'PK\x05\x06' + b'\0' * 18))
        page.evaluate("""job => {
            activeOutputId=job.id;setOutput(job);$('script').value=job.text;
            $('script-format').value='txt';$('script').oninput();
        }""", job)
        with page.expect_download() as completed:
            page.click('#export-script-srt')
        assert completed.value.suggested_filename == 'voice-studio-cccccccc.zip'
        playwright.expect(page.locator('#notice')).to_contain_text('SRT riêng cho từng phần nằm trong ZIP')
        assert state['errors'] == []
