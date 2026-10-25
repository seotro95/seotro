"""The one-click voice check keeps the draft and uses the selected voice."""
from test_hmong_ui import playwright,static_site,studio_page  # noqa:F401


def test_help_trial_posts_selected_voice_without_overwriting_text(static_site):
    with studio_page(static_site,native=True,voice_choices=True) as (page,state):
        page.locator('.nav-item[data-tab="create"]').click()
        page.locator('#script').fill('Kuv xav khaws cov lus no.')
        page.locator('#hmong-voice-choices [data-hmong-gender="female"]').click()
        page.locator('#help-button').click()
        playwright.expect(page.locator('#hmong-help-tools')).to_be_visible()
        playwright.expect(page.get_by_role('link',name='Mở hướng dẫn đầy đủ · có thể in')).to_have_attribute('href','/help/hmong')
        page.locator('#hmong-test-selected-voice').click()
        page.wait_for_function('!document.querySelector("#help-dialog").open')
        assert len(state['speech'])==1
        body=state['speech'][0]
        assert body['voice_id']=='hmong-female' and body['language']=='mww' and body['format']=='wav'
        assert body['text']=='Nyob zoo. Ua tsaug rau koj mloog.'
        assert page.locator('#script').input_value()=='Kuv xav khaws cov lus no.'
        assert state['errors']==[]
