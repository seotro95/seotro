"""Inspect public submission requirements only; no upload, login or token use."""
from html.parser import HTMLParser
import asyncio
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

PORTAL = 'https://www.microsoft.com/en-us/wdsi/filesubmission'


def public_url(value):
    parsed = urlsplit(urljoin(PORTAL, value))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, '', ''))


class PublicPage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.text = []
        self.forms = []
        self.fields = []
        self.links = []
        self.title = ''
        self.in_title = False
        self.captcha_markup = False

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag in ('script', 'style'):
            self.skip += 1
        if tag == 'title':
            self.in_title = True
        if tag == 'form':
            self.forms.append({'action': public_url(attributes.get('action', '')),
                               'method': attributes.get('method', 'get')})
        if tag in ('input', 'select', 'textarea', 'button') and attributes.get('type') not in ('hidden', 'password'):
            self.fields.append({key: attributes[key] for key in
                                ('name', 'id', 'type', 'required', 'disabled', 'accept', 'aria-label') if key in attributes})
        if tag == 'a' and re.search(r'login|signin|sign-in|submit|account', attributes.get('href', ''), re.I):
            self.links.append(public_url(attributes['href']))
        if any(re.search(r'captcha', attributes.get(key, ''), re.I) for key in ('id', 'class')):
            self.captcha_markup = True

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip = max(0, self.skip - 1)
        if tag == 'title':
            self.in_title = False

    def handle_data(self, value):
        if not self.skip:
            self.text.append(value)
            if self.in_title:
                self.title += value


def inspect(markup):
    page = PublicPage()
    page.feed(markup)
    visible = re.sub(r'\s+', ' ', ' '.join(page.text))
    excerpts = []
    for match in re.finditer(r'sign in|log in|account|captcha|submit a file|submission|50 MB', visible, re.I):
        excerpt = visible[max(0, match.start() - 80):match.start() + 220]
        if excerpt not in excerpts:
            excerpts.append(excerpt)
        if len(excerpts) >= 18:
            break
    return {'title': page.title.strip(), 'forms': page.forms, 'non_secret_fields': page.fields,
            'relevant_links_without_queries': sorted(set(page.links)),
            'captcha_markup_present': page.captcha_markup, 'visible_excerpts': excerpts}


async def inspect_visible_flow(browser):
    from playwright.async_api import async_playwright
    async with async_playwright() as automation:
        instance = await automation.chromium.launch(executable_path=browser, headless=True,
                                                    chromium_sandbox=True)
        try:
            context = await instance.new_context()
            page = await context.new_page()
            await page.goto(PORTAL, wait_until='domcontentloaded', timeout=45000)
            await page.wait_for_timeout(2000)
            before = await page.locator('body').inner_text()
            # This selects the truthful reporter role only. It never supplies
            # identity, solves a challenge or clicks a file-submission button.
            developer = page.locator('#SelectSoftwareDeveloper')
            if await developer.count() and await developer.is_visible():
                await developer.click()
                await page.wait_for_timeout(2500)
            continuation = page.locator('#btnTypeSelectedContinue')
            if await continuation.count() and await continuation.is_visible() and await continuation.is_enabled():
                await continuation.click()
                await page.wait_for_timeout(3500)
            if len(context.pages) > 1:
                page = context.pages[-1]
            text = await page.locator('body').inner_text(timeout=15000)
            fields = []
            for field in await page.locator('input,select,textarea').all():
                if not await field.is_visible():
                    continue
                fields.append({key: await field.get_attribute(key) for key in ('name', 'id', 'type')})
            host = urlsplit(page.url).hostname or ''
            return {'initial_visible_text': before[:7000], 'final_visible_text': text[:9000],
                    'final_url_without_query': public_url(page.url), 'title': await page.title(),
                    'visible_input_names_only': fields,
                    'interactive_sign_in_required': host in ('login.live.com', 'login.microsoftonline.com') or
                        bool(await page.locator('input[name="loginfmt"],input[type="password"]').count()),
                    'visible_file_picker': await page.locator('input[type="file"]').count() > 0 and
                        await page.locator('input[type="file"]').first.is_visible()}
        finally:
            await instance.close()


def main():
    directory = Path(os.environ['RUNNER_TEMP']) / 'microsoft-submission-prerequisites'
    directory.mkdir(parents=True, exist_ok=True)
    report = {'submission_performed': False, 'file_uploaded': False, 'login_attempted': False,
              'requested_portal': PORTAL}
    try:
        request = Request(PORTAL, headers={'User-Agent': 'VoiceLabReviewPreparation/1.0'})
        with urlopen(request, timeout=30) as response:
            raw = response.read(3_000_001)
            if len(raw) > 3_000_000:
                raise ValueError('Portal document exceeds inspection limit.')
            report['http_status'] = response.status
            report['final_url_without_query'] = public_url(response.url)
        report['server_page'] = inspect(raw.decode('utf-8', 'replace'))
        # Normal, unauthenticated browser rendering only. Never alter browser
        # security, solve a CAPTCHA or load an existing authenticated profile.
        browser = shutil.which('google-chrome') or shutil.which('google-chrome-stable')
        if browser:
            report['visible_flow'] = asyncio.run(inspect_visible_flow(browser))
    except Exception as exc:
        report['access_error'] = str(exc)
    (directory / 'requirements.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    def annotation(title, value):
        message = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
        escaped = message.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        print('::notice title=' + title + '::' + escaped)
    annotation('Microsoft portal access', {key: value for key, value in report.items()
                                           if key not in ('server_page', 'visible_flow')})
    flow = report.get('visible_flow')
    if flow:
        annotation('Visible Microsoft submission flow', {key: value for key, value in flow.items()
            if key not in ('initial_visible_text', 'final_visible_text')})
        text = flow['final_visible_text']
        for offset in range(0, len(text), 2500):
            annotation('Visible Microsoft portal text ' + str(offset // 2500 + 1), text[offset:offset + 2500])
    for key in ('server_page',):
        page = report.get(key)
        if not page:
            continue
        annotation(key + ' authentication indicators', {name: page[name] for name in
            ('title', 'captcha_markup_present', 'relevant_links_without_queries')})
        excerpts = page['visible_excerpts']
        for offset in range(0, len(excerpts), 4):
            annotation(key + ' visible text ' + str(offset // 4 + 1), excerpts[offset:offset + 4])
        fields = [field for field in page['non_secret_fields'] if not
                  re.search(r'^(?:uhf|pf|c-shell|close-epb|cli_shell|search|cancel-search)', field.get('id', ''))]
        for offset in range(0, len(fields), 12):
            annotation(key + ' submission fields ' + str(offset // 12 + 1), fields[offset:offset + 12])


if __name__ == '__main__':
    main()
