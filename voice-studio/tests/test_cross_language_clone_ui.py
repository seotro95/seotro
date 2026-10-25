"""The native clone form accepts external audio without a Hmong transcript."""
from test_hmong_ui import PROJECT_REFERENCES, ROOT, playwright, pytestmark, static_site, studio_page  # noqa: F401


def test_native_external_voice_without_transcript_is_selected_and_used_after_refresh(static_site):
    with studio_page(static_site, native=True, voice_choices=True, known_reference=False) as (page, state):
        page.locator('.nav-item[data-tab="clone"]').click()
        playwright.expect(page.locator('label[for="clone-language"]')).to_have_text('Ngôn ngữ lời đọc đầu ra')
        assert page.locator('#transcript').get_attribute('required') is None
        page.fill('#clone-name', 'External voice')
        page.locator('#clone-file').set_input_files(ROOT / 'assets/hmong' / PROJECT_REFERENCES['female']['file'])
        playwright.expect(page.locator('#clone-status')).to_contain_text('Không cần nhập lời mẫu')
        assert page.locator('#transcript').input_value() == ''
        page.check('#clone-form input[name="consent"]')
        page.click('#clone-submit')
        playwright.expect(page.locator('#panel-create')).to_be_visible()
        for node in ('voice', 'dub-voice'):
            playwright.expect(page.locator('#' + node)).to_have_value('hmong-new-personal')
        # A normal library refresh must preserve the personal voice, not the
        # previous male/female preset, in both speech entry points.
        page.evaluate('refreshVoices()')
        for node in ('voice', 'dub-voice'):
            playwright.expect(page.locator('#' + node)).to_have_value('hmong-new-personal')
        page.fill('#script', 'Nyob zoo. Ua tsaug.')
        page.click('#generate')
        playwright.expect(page.locator('#output-title')).to_contain_text('đã sẵn sàng')
        assert state['speech'][-1]['voice_id'] == 'hmong-new-personal'
        assert state['speech'][-1]['language'] == 'mww'
        assert state['errors'] == []


def test_f5_external_reference_still_requires_hmong_transcript(static_site):
    with studio_page(static_site, native=False, known_reference=False) as (page, state):
        page.locator('.nav-item[data-tab="clone"]').click()
        playwright.expect(page.locator('#transcript')).to_have_attribute('required', '')
        page.fill('#clone-name', 'External voice')
        page.locator('#clone-file').set_input_files(ROOT / 'assets/hmong' / PROJECT_REFERENCES['female']['file'])
        playwright.expect(page.locator('#clone-status')).to_contain_text('nhập đúng lời Hmong')
        page.check('#clone-form input[name="consent"]')
        page.click('#clone-submit')
        assert state['clones'] == []
        assert state['errors'] == []
