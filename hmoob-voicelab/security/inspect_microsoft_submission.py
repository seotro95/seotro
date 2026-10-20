"""Inspect public submission requirements only; no upload, login or token use."""
from html.parser import HTMLParser
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
            with tempfile.TemporaryDirectory(prefix='ms-public-browser-') as profile:
                rendered = subprocess.run([browser, '--headless', '--dump-dom',
                    '--timeout=30000', '--virtual-time-budget=12000', '--user-data-dir=' + profile,
                    PORTAL], capture_output=True, timeout=60, check=False)
                report['browser_exit_code'] = rendered.returncode
                report['browser_page'] = inspect(rendered.stdout.decode('utf-8', 'replace'))
    except Exception as exc:
        report['access_error'] = str(exc)
    (directory / 'requirements.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    message = json.dumps(report, ensure_ascii=False, separators=(',', ':'))
    if len(message) > 18000:
        message = message[:18000] + ' [report truncated in annotation; full JSON in artifact]'
    escaped = message.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print('::notice title=Microsoft submission prerequisites::' + escaped)


if __name__ == '__main__':
    main()
