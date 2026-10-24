"""Real Chromium interactions with mocked APIs; no inference or quality claims."""
import contextlib
import copy
import json
from urllib.parse import urlparse

import pytest

from test_hmong_ui import CHROMIUM, playwright, static_site, studio_page  # noqa: F401

pytestmark = pytest.mark.skipif(not CHROMIUM, reason='Character UI checks need Chromium')
VIDEO = 'c' * 32
CHARACTERS = [
    {'id': 'hero', 'name': 'Tub', 'voice_id': 'hmong-male'},
    {'id': 'friend', 'name': 'Ntxhais', 'voice_id': 'hmong-female'},
]
CUES = [
    {'id': 'cue-a', 'start': 0, 'end': 1, 'text': 'Nyob zoo.', 'character_id': 'hero'},
    {'id': 'cue-b', 'start': 3, 'end': 4, 'text': 'Kuv nyob ntawm no.', 'character_id': 'friend'},
    {'id': 'cue-c', 'start': 6, 'end': 7, 'text': 'Ua tsaug.'},
]


def project():
    return {'project_version': 2, 'cues': copy.deepcopy(CUES),
            'characters': copy.deepcopy(CHARACTERS), 'language': 'mww',
            'source_cues': copy.deepcopy(CUES), 'source_language': 'mww'}


@contextlib.contextmanager
def cast_page(site, *, saved=None, hmong=True):
    with studio_page(site, native=True, voice_choices=True, hmong=hmong) as (page, state):
        state.update(project=copy.deepcopy(saved if saved is not None else project()), saves=[], video_tasks=[],
                     task_pending=False, task_result={})

        def handle(route):
            request = route.request
            path = urlparse(request.url).path
            if path == '/api/videos':
                response = {'items': [{'id': VIDEO, 'name': 'Test.mp4', 'duration': 12, 'codec': 'h264'}]}
            elif path.endswith('/editor'):
                if request.method == 'PUT':
                    state['project'] = request.post_data_json
                    state['saves'].append(copy.deepcopy(state['project']))
                response = state['project']
            elif path.endswith('/alignment'):
                response = {'sync_ok': True, 'cues': []}
            elif path.endswith('/timing'):
                response = {'cues': [{'start': c['start'], 'end': c['end']} for c in state['project']['cues']]}
            elif path == '/api/video-tasks':
                state['video_tasks'].append(request.post_data_json)
                response = {'id': 'b' * 32, 'status': 'queued'}
            elif path.startswith('/api/video-tasks/'):
                response = {'id': 'b' * 32, 'status': 'queued' if state['task_pending'] else 'done',
                            'progress': 0 if state['task_pending'] else 100, 'video_url': '/test.mp4',
                            **state['task_result']}
            else:
                route.fulfill(status=200, content_type='video/mp4', body=b'')
                return
            route.fulfill(status=200, content_type='application/json', body=json.dumps(response))

        for pattern in ('**/api/videos', '**/api/videos/**', '**/api/jobs/*/alignment',
                        '**/api/jobs/*/timing', '**/api/video-tasks', '**/api/video-tasks/**'):
            page.route(pattern, handle)
        page.locator('.nav-item[data-tab="dub"]').click()
        page.evaluate('refreshDubSources()')
        page.select_option('#dub-existing', VIDEO)
        playwright.expect(page.locator('#editor-cues .editor-cue')).to_have_count(len(state['project']['cues']))
        yield page, state
        assert state['errors'] == []


def import_project(page, data, name='project.json'):
    page.locator('#editor-project-file').set_input_files(
        {'name': name, 'mimeType': 'application/json', 'buffer': json.dumps(data).encode()})


def test_cast_edit_sort_delete_and_narrator_mapping(static_site):
    with cast_page(static_site) as (page, state):
        page.fill('[data-character-id="hero"] input', 'Tus Tub')
        playwright.expect(page.locator('[data-cue-character="cue-a"] option:checked')).to_have_text('Tus Tub')
        page.select_option('[data-character-voice="friend"]', 'hmong-personal')
        # Move one cue past another, then sort using the actual editor control.
        page.fill('[data-cue-id="cue-a"] input', '08.000')
        page.fill('[data-cue-id="cue-a"] input >> nth=1', '09.000')
        page.click('#editor-cues-sort')
        assert page.evaluate('editorCues.map(c=>c.id)') == ['cue-b', 'cue-c', 'cue-a']
        assert page.evaluate('editorCharacterSpeech()') == {
            'character_voices': {'friend': 'hmong-personal', 'hero': 'hmong-male'},
            'cue_characters': ['friend', None, 'hero']}
        page.click('[data-cue-id="cue-b"] button:last-child')
        page.click('[data-character-id="hero"] button')
        assert page.evaluate('editorCues.every(c=>!c.character_id)')
        assert page.evaluate('editorSourceCues.every(c=>c.character_id!=="hero")')
        page.click('#editor-save')
        playwright.expect(page.locator('#editor-save-status')).to_contain_text('Đã lưu')
        assert state['saves'][-1]['cues'][-1]['id'] == 'cue-a'
        assert 'Tus Tub' not in page.locator('#dub-script').input_value()


def test_manual_cues_characters_and_script_draft_keep_assignments(static_site):
    with cast_page(static_site, saved={'cues': [], 'language': 'mww'}) as (page, state):
        page.click('#editor-add')
        page.fill('#editor-cues textarea', 'Nyob zoo.')
        page.click('#editor-character-add')
        page.fill('#editor-character-list input', 'Leej Tub')
        first_id = page.locator('.editor-character').first.get_attribute('data-character-id')
        page.select_option('#editor-cues [data-cue-character]', first_id)
        page.fill('#editor-seek', '4')
        page.click('#editor-add')
        page.fill('#editor-cues textarea >> nth=1', 'Ua tsaug.')
        page.click('#editor-character-add')
        second_id = page.locator('.editor-character').last.get_attribute('data-character-id')
        page.select_option('[data-character-voice="' + second_id + '"]', 'hmong-female')
        page.select_option('#editor-cues [data-cue-character] >> nth=1', second_id)
        ids = page.evaluate('editorCues.map(c=>c.id)')
        page.click('#editor-script-open')
        page.fill('#editor-script-draft', 'Kuv nyob ntawm no.\n\nPeb rov los tsev.')
        page.click('#editor-script-apply')
        playwright.expect(page.locator('#editor-script-status')).to_contain_text('Đã lưu kịch bản mới')
        assert page.evaluate('editorCues.map(c=>c.id)') == ids
        assert page.evaluate('editorCharacterSpeech().cue_characters') == [first_id, second_id]
        assert state['project']['cues'][1]['text'] == 'Peb rov los tsev.'


def test_speech_maps_timing_metadata_export_and_voice_changes(static_site):
    with cast_page(static_site) as (page, state):
        page.click('#workspace-voice')
        playwright.expect(page.locator('#workspace-status')).to_contain_text('Voice đã sẵn sàng')
        speech = state['speech'][-1]
        assert speech['character_voices'] == {'hero': 'hmong-male', 'friend': 'hmong-female'}
        assert speech['cue_characters'] == ['hero', 'friend', None]
        assert speech['input_format'] == 'srt' and speech['language'] == 'mww'
        assert 'Tub' not in speech['text'] and 'Ntxhais' not in speech['text']
        assert state['project']['cues'] == CUES and state['project']['source_cues'] == CUES
        page.click('#workspace-export-voice')
        playwright.expect(page.locator('#workspace-status')).to_contain_text('Video có phụ đề và voice')
        assert state['video_tasks'][-1]['voice_job_id'] == 'a' * 32
        page.select_option('[data-character-voice="hero"]', 'hmong-personal')
        assert page.evaluate('workspaceVoice') is None
        page.click('#workspace-voice')
        playwright.expect(page.locator('#workspace-status')).to_contain_text('Voice đã sẵn sàng')
        assert state['speech'][-1]['character_voices']['hero'] == 'hmong-personal'
        page.click('#workspace-hmong-voice-choices [data-hmong-gender="female"]')
        assert page.evaluate('workspaceVoice') is None
        page.click('#workspace-voice')
        playwright.expect(page.locator('#workspace-status')).to_contain_text('Voice đã sẵn sàng')
        assert state['speech'][-1]['voice_id'] == 'hmong-female'
        assert state['speech'][-1]['character_voices']['hero'] == 'hmong-personal'


def test_imported_proto_id_serializes_and_passes_python_cast_validation(static_site):
    from character_cast import validate_cast_request
    with cast_page(static_site) as (page, state):
        imported = project()
        imported['characters'][0]['id'] = '__proto__'
        for cue in imported['cues'] + imported['source_cues']:
            if cue.get('character_id') == 'hero':
                cue['character_id'] = '__proto__'
        import_project(page, imported)
        playwright.expect(page.locator('#notice')).to_contain_text('Đã nhập')
        page.click('#workspace-voice')
        playwright.expect(page.locator('#workspace-status')).to_contain_text('Voice đã sẵn sàng')
        speech = state['speech'][-1]
        assert speech['character_voices'] == {'__proto__': 'hmong-male', 'friend': 'hmong-female'}
        assert speech['cue_characters'] == ['__proto__', 'friend', None]
        assert validate_cast_request(speech['character_voices'], speech['cue_characters'], 3) == speech['cue_characters']


def test_queued_job_freezes_cast_and_cues_and_rejects_stale_narrator(static_site):
    with cast_page(static_site) as (page, state):
        state['job_pending'] = True
        page.click('#workspace-voice')
        playwright.expect(page.locator('#workspace-status')).to_contain_text('queued')
        for selector in ('#editor-character-add', '#editor-cues-sort', '#editor-project-import',
                         '#editor-add', '[data-character-voice="hero"]', '[data-character-id="hero"] input',
                         '[data-cue-character="cue-a"]', '[data-cue-id="cue-a"] textarea',
                         '#editor-script-apply'):
            playwright.expect(page.locator(selector)).to_be_disabled()
        # An unrelated completed task must not release the workspace's lock.
        page.evaluate('taskButtons(false)')
        playwright.expect(page.locator('#editor-add')).to_be_disabled()
        page.click('#workspace-hmong-voice-choices [data-hmong-gender="female"]')
        state['job_pending'] = False
        playwright.expect(page.locator('#workspace-status')).to_contain_text('giọng đã đổi')
        assert state['speech'][-1]['voice_id'] == 'hmong-male'
        assert state['speech'][-1]['cue_characters'] == ['hero', 'friend', None]
        assert page.evaluate('workspaceVoice') is None
        playwright.expect(page.locator('#editor-character-add')).to_be_enabled()


def test_preview_freezes_cast_even_after_unrelated_task_completion(static_site):
    with cast_page(static_site) as (page, state):
        state['task_pending'] = True
        page.click('#preview-video-create')
        playwright.expect(page.locator('#preview-status')).to_contain_text('queued')
        page.evaluate('taskButtons(false)')
        for selector in ('#editor-add', '#editor-character-add', '#editor-cues-sort',
                         '[data-cue-id="cue-a"] textarea', '[data-cue-character="cue-a"]'):
            playwright.expect(page.locator(selector)).to_be_disabled()
        state['task_pending'] = False
        playwright.expect(page.locator('#preview-status')).to_contain_text('Bản xem thử từ giây')
        playwright.expect(page.locator('#editor-add')).to_be_enabled()


@pytest.mark.parametrize('button', ['editor-dub', 'editor-render', 'editor-translate', 'preview-video-create'])
def test_cast_freezes_while_saving_before_a_task_is_queued(static_site, button):
    with cast_page(static_site) as (page, state):
        pending = []
        page.route('**/api/videos/' + VIDEO + '/editor', lambda route: pending.append(route))
        page.locator('#workspace-advanced').evaluate('(node)=>{node.open=true;}')
        page.click('#' + button)
        playwright.expect(page.locator('#editor-character-add')).to_be_disabled()
        playwright.expect(page.locator('#editor-add')).to_be_disabled()
        playwright.expect(page.locator('[data-cue-character="cue-a"]')).to_be_disabled()
        assert len(pending) == 1
        state['project'] = pending[0].request.post_data_json
        pending[0].fulfill(status=200, content_type='application/json', body=json.dumps(state['project']))
        playwright.expect(page.locator('#editor-character-add')).to_be_enabled()


def test_project_export_import_retains_source_and_cast_and_srt_never_speaks_names(static_site):
    saved = project()
    saved['source_language'] = 'vi'
    saved['source_cues'][0]['text'] = 'Xin chào.'
    with cast_page(static_site, saved=saved) as (page, state):
        with page.expect_download() as download_info:
            page.click('#editor-project-export')
        exported = json.loads(download_info.value.path().read_text())
        assert exported['project_version'] == 2
        assert exported['characters'] == CHARACTERS
        assert exported['source_cues'] == saved['source_cues']
        assert exported['source_language'] == 'vi'
        page.click('[data-character-id="hero"] button')
        import_project(page, exported)
        playwright.expect(page.locator('[data-cue-character="cue-a"]')).to_have_value('hero')
        assert state['project']['source_cues'] == saved['source_cues']
        assert state['project']['source_language'] == 'vi'
        srt = page.evaluate('editorSrt(checkedEditorCues())')
        assert 'Tub' not in srt and 'Ntxhais' not in srt
        page.locator('#editor-project-file').set_input_files({'name': 'same.srt', 'mimeType': 'text/plain', 'buffer': srt.encode()})
        playwright.expect(page.locator('#editor-save-status')).to_contain_text('Đã lưu')
        assert page.evaluate('checkedEditorCues()') == CUES
        changed = srt.replace('Nyob zoo.', 'Lwm cov lus.')
        page.locator('#editor-project-file').set_input_files({'name': 'new.srt', 'mimeType': 'text/plain', 'buffer': changed.encode()})
        playwright.expect(page.locator('[data-cue-character]').first).to_have_value('')
        assert page.evaluate('editorCues[0].id') != 'cue-a'
        assert page.evaluate('editorCues[1].character_id') == 'friend'


@pytest.mark.parametrize('bad_voice', ['deleted-profile', 'not-ready', 'wrong-engine'])
def test_only_used_characters_are_validated_and_unavailable_voices_block_speech(static_site, bad_voice):
    saved = project()
    saved['characters'][0]['voice_id'] = bad_voice
    with cast_page(static_site, saved=saved) as (page, state):
        if bad_voice != 'deleted-profile':
            page.evaluate('voice => {voices.push(voice);drawEditorCues();}',
                          {'id': bad_voice, 'name': bad_voice, 'engine': 'f5_hmong' if bad_voice == 'wrong-engine' else 'hmong_native',
                           'languages': ['mww'], 'category': 'cloned', 'ready': bad_voice != 'not-ready'})
        page.click('#workspace-voice')
        playwright.expect(page.locator('#workspace-status')).to_contain_text('giọng' if bad_voice != 'not-ready' else 'chưa sẵn sàng')
        assert state['speech'] == []
        page.select_option('[data-cue-character="cue-a"]', '')
        page.click('#workspace-voice')
        playwright.expect(page.locator('#workspace-status')).to_contain_text('Voice đã sẵn sàng')
        assert state['speech'][-1]['character_voices'] == {'friend': 'hmong-female'}
        assert state['speech'][-1]['cue_characters'] == [None, 'friend', None]


def test_import_validation_limit_and_legacy_migration(static_site):
    with cast_page(static_site) as (page, state):
        legacy = {'cues': [{'start': 0, 'end': 1, 'text': 'Nyob zoo.'}], 'language': 'mww'}
        import_project(page, legacy)
        playwright.expect(page.locator('#editor-cues .editor-cue')).to_have_count(1)
        playwright.expect(page.locator('#editor-save-status')).to_contain_text('Đã lưu')
        assert state['project']['project_version'] == 2
        assert state['project']['cues'][0]['id'] == state['project']['source_cues'][0]['id']
        full = project()
        full['characters'] = [{'id': 'person-' + str(i), 'name': 'Tus ' + str(i), 'voice_id': 'hmong-male'} for i in range(32)]
        for cue in full['cues'] + full['source_cues']:
            cue.pop('character_id', None)
        import_project(page, full)
        playwright.expect(page.locator('.editor-character')).to_have_count(32)
        page.click('#editor-character-add')
        assert page.locator('.editor-character').count() == 32
        invalid = copy.deepcopy(full)
        invalid['characters'].append({'id': 'overflow', 'name': 'Too many', 'voice_id': 'hmong-male'})
        before = page.evaluate('editorProjectData()')
        import_project(page, invalid)
        playwright.expect(page.locator('#notice')).to_contain_text('32')
        assert page.evaluate('editorProjectData()') == before
        invalid = copy.deepcopy(full)
        invalid['cues'][0]['character_id'] = 'missing'
        import_project(page, invalid)
        playwright.expect(page.locator('#notice')).to_contain_text('không có trong dự án')
        assert page.evaluate('editorProjectData()') == before


def test_translation_preserves_metadata_only_for_same_cue_timing(static_site):
    with cast_page(static_site) as (page, state):
        translated = copy.deepcopy(CUES)
        for cue in translated:
            cue.pop('id')
            cue.pop('character_id', None)
            cue['text'] = 'Translated ' + cue['text']
        page.evaluate('cues=>loadDirectCues(cues,"vi",{preserveMetadata:true})', translated)
        assert page.evaluate('editorCues.map(c=>[c.id,c.character_id||null])') == [
            ['cue-a', 'hero'], ['cue-b', 'friend'], ['cue-c', None]]
        assert page.evaluate('editorSourceCues') == CUES
        before = page.evaluate('editorProjectData()')
        translated[0]['start'] = .1
        error = page.evaluate('async cues=>{try{await loadDirectCues(cues,"vi",{preserveMetadata:true});return null}catch(e){return e.message}}', translated)
        assert 'Mốc hoặc số câu' in error
        assert page.evaluate('editorProjectData()') == before
        error = page.evaluate('async cues=>{try{await loadDirectCues(cues,"vi",{preserveMetadata:true});return null}catch(e){return e.message}}', translated[:1])
        assert 'Mốc hoặc số câu' in error


def test_video_project_limit_stays_200k_while_free_text_limit_is_1m(static_site):
    with cast_page(static_site) as (page, state):
        page.evaluate('config.max_characters=1000000;updateScriptLimits()')
        oversized = {'project_version': 2, 'characters': [], 'source_cues': [], 'language': 'mww',
                     'cues': [{'start': i / 10, 'end': (i + 1) / 10, 'text': 'a' * 4000} for i in range(51)]}
        before = page.evaluate('editorProjectData()')
        import_project(page, oversized)
        playwright.expect(page.locator('#notice')).to_contain_text('200.000 ký tự trong 3 giờ')
        assert page.evaluate('editorProjectData()') == before
        assert state['saves'] == []


@pytest.mark.parametrize('change', ['edit', 'busy', 'video'])
def test_delayed_import_cannot_overwrite_changed_project_or_busy_job(static_site, change):
    with cast_page(static_site) as (page, state):
        page.evaluate('''() => {window.pendingCharacterImport=editorImportFile({name:'late.srt',size:100,
            text:()=>new Promise(resolve=>{window.finishCharacterImport=resolve;})});}''')
        if change == 'edit':
            page.fill('[data-cue-id="cue-a"] textarea', 'Kuv hloov lawm.')
        elif change == 'busy':
            page.evaluate('workspaceSetBusy(true)')
        else:
            page.evaluate('dubSource={...dubSource,id:"different-video"}')
        before = page.evaluate('editorCues')
        page.evaluate('''async()=>{finishCharacterImport('1\\n00:00:00,000 --> 00:00:01,000\\nLate words.');await pendingCharacterImport;}''')
        assert page.evaluate('editorCues') == before
        assert state['saves'] == []
        playwright.expect(page.locator('#notice')).to_contain_text('đã đổi khi đọc tệp')
        page.evaluate('workspaceSetBusy(false)')


def test_standard_variant_hides_cast_and_sends_no_character_maps(static_site):
    with cast_page(static_site, hmong=False) as (page, state):
        playwright.expect(page.locator('#editor-characters')).to_be_hidden()
        assert page.locator('[data-cue-character]').count() == 0
        assert page.evaluate('editorCharacterSpeech()') == {}


def test_free_long_script_plays_chapters_downloads_zip_and_invalidates_stale_player(static_site):
    with cast_page(static_site) as (page, state):
        job_id = 'a' * 32
        job = {'id': job_id, 'status': 'done', 'progress': 100, 'longform': True,
               'format': 'wav', 'audio_seconds': 20, 'url': '/api/jobs/' + job_id + '/archive',
               'chapters': [{'index': 1, 'characters': 120000, 'audio_seconds': 10},
                            {'index': 2, 'characters': 120000, 'audio_seconds': 10}]}
        page.route('**/api/jobs/' + job_id, lambda route: route.fulfill(
            status=200, content_type='application/json', body=json.dumps(job)))
        page.route('**/api/jobs/' + job_id + '/archive', lambda route: route.fulfill(
            status=200, content_type='application/zip', body=b'PK\x03\x04test-archive'))
        page.evaluate('config.max_characters=1000000;updateScriptLimits()')
        long_text = 'Nyob zoo. ' * 24000
        page.fill('#workspace-free-script', long_text)
        page.click('#workspace-free-generate')
        playwright.expect(page.locator('#workspace-free-status')).to_contain_text('tải ZIP')
        assert len(state['speech'][-1]['text']) > 200000
        assert state['speech'][-1]['input_format'] == 'txt'
        assert not state['speech'][-1].get('character_voices')
        audio = page.locator('#workspace-free-audio')
        chapters = audio.locator('xpath=preceding-sibling::select[1]')
        playwright.expect(audio).to_have_attribute('src', '/api/jobs/' + job_id + '/chapters/1')
        chapters.select_option('2')
        playwright.expect(audio).to_have_attribute('src', '/api/jobs/' + job_id + '/chapters/2')
        playwright.expect(page.locator('#workspace-free-format')).to_be_disabled()
        with page.expect_download() as download_info:
            page.click('#workspace-free-download')
        assert download_info.value.suggested_filename == 'voice-rieng.zip'
        page.fill('#workspace-free-script', 'Cov lus tshiab.')
        playwright.expect(audio).to_be_hidden()
        playwright.expect(chapters).to_be_hidden()
        assert page.evaluate('workspaceFreeVoice') is None
        playwright.expect(page.locator('#workspace-free-format')).to_be_enabled()
