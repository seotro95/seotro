"""Decode Unicode subtitle files without losing RPA letters or replacing bytes."""
import base64
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = '217\r\n00:06:07,200 --> 00:06:08,400\r\nTae-yong cov ntaub ntawv tus kheej\r\n'


def test_text_reader_decodes_common_windows_subtitle_encodings_and_rejects_binary():
    node = shutil.which('node')
    if not node:
        pytest.skip('TextDecoder checks require Node.js')
    content = [SOURCE.encode('utf-8'), b'\xef\xbb\xbf' + SOURCE.encode('utf-8'),
               b'\xff\xfe' + SOURCE.encode('utf-16le'), b'\xfe\xff' + SOURCE.encode('utf-16be'),
               SOURCE.encode('utf-16le'), SOURCE.encode('utf-16be')]
    invalid = [b'\xff\xfea', b'\xfe\xff\xd8\x00', b'\xffbad', b'a\x00b\x00c', b'\x00\x01\x02\x03']
    program = (ROOT / 'static/text-import.js').read_text() + '''
    const fs=require('fs');
    const cases=JSON.parse(fs.readFileSync(0,'utf8'));
    (async()=>{
      const out=[];
      for(const raw of cases){
        const bytes=Buffer.from(raw,'base64');
        const file={arrayBuffer:async()=>bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength)};
        try{out.push({text:await readScriptFileText(file)});}catch(e){out.push({error:e.message});}
      }
      process.stdout.write(JSON.stringify(out));
    })().catch(e=>{process.stderr.write(String(e));process.exitCode=1;});
    '''
    result = subprocess.run([node, '-e', program], input=json.dumps([
        base64.b64encode(value).decode() for value in content + invalid]),
        capture_output=True, text=True, check=True, timeout=15)
    values = json.loads(result.stdout)
    assert values[:len(content)] == [{'text': SOURCE}] * len(content)
    assert all('UTF-' in item['error'] or 'văn bản' in item['error'] for item in values[len(content):])


@pytest.mark.parametrize('encoding,bom', [('utf-8', b''), ('utf-16le', b'\xff\xfe'), ('utf-16be', b'\xfe\xff')])
@pytest.mark.parametrize('extension', ['txt', 'srt'])
def test_browser_import_preserves_decoded_hmong_excerpt(encoding, bom, extension, request):
    from test_hmong_ui import CHROMIUM, CHANNEL, playwright, studio_page
    if not CHANNEL and not CHROMIUM:
        pytest.skip('Browser import checks require Chromium or Edge')
    site = request.getfixturevalue('static_site')
    with studio_page(site, native=True) as (page, state):
        conversions = []

        def convert(route):
            payload = route.request.post_data_json
            conversions.append(payload)
            route.fulfill(status=200, json={'text': payload['text']})

        page.route('**/api/scripts/convert', convert)
        page.locator('#script').fill('Lời đang soạn.')
        page.locator('#import-script').set_input_files({'name': 'hmong.' + extension,
            'mimeType': 'text/plain', 'buffer': bom + SOURCE.encode(encoding)})
        # HTML textareas standardize line endings to LF. The decoded bytes
        # above and the conversion request below retain the original CRLF.
        playwright.expect(page.locator('#script')).to_have_value(SOURCE.replace('\r\n', '\n'))
        playwright.expect(page.locator('#script-format')).to_have_value(extension)
        if extension == 'srt':
            assert conversions[0]['text'] == SOURCE
        assert state['errors'] == []


@pytest.fixture(scope='module')
def static_site(request):
    # Reuse the app's real static fixture without changing the optional-browser
    # marker on the pure TextDecoder test above.
    from test_hmong_ui import static_site as fixture
    yield from fixture.__wrapped__()
