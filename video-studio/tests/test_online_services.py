import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

import test_studio  # Establish the isolated test data directory before importing app.
import app
import engine
import online_services as online
from fastapi.testclient import TestClient
import httpx


class OnlineTests(unittest.TestCase):
    def test_catalog_refresh_validation_and_offline_cache(self):
        voices = [{'ShortName':'vi-VN-HoaiMyNeural','Locale':'vi-VN','Gender':'Female'},
                  {'ShortName':'en-US-AriaNeural','Locale':'en-US','Gender':'Female'},
                  {'ShortName':'../../fakeNeural','Locale':'vi-VN'},
                  {'ShortName':'<script>Neural','Locale':'vi-VN'}]
        with tempfile.TemporaryDirectory() as root, patch.object(online, 'DATA', Path(root)):
            module = Mock(list_voices=AsyncMock(return_value=voices))
            with patch.object(online, 'edge_module', return_value=module):
                result = online.sync_voices(True)
                self.assertEqual(len(result['voices']), 2)
                self.assertIn('Nữ', online.voice_catalog()['voices'][0]['name'])
                online.sync_voices(False)
                module.list_voices.assert_awaited_once()
            old_time = result['updated']
            with patch.object(online, 'edge_module', side_effect=OSError('offline')):
                result = online.sync_voices(True)
                self.assertEqual(result['updated'], old_time)
                self.assertEqual(len(result['voices']), 2)
                self.assertIn('giữ danh mục cũ', result['message'])
            with self.assertRaises(ValueError):
                online.normalize_voices([voices[-1]])
            cached = Path(root) / 'edge-voices.json'
            corrupted = json.loads(cached.read_text())
            corrupted['checked'] = 'invalid timestamp'
            cached.write_text(json.dumps(corrupted))
            self.assertEqual(online.voice_catalog()['checked'], 0)

    def test_edge_voice_validation_rate_proxy_and_error_cleanup(self):
        with tempfile.TemporaryDirectory() as root, patch.object(online, 'DATA', Path(root)):
            output = Path(root) / 'voice.mp3'
            async def save(path):
                Path(path).write_bytes(b'audio')
            communicate = Mock(return_value=Mock(save=AsyncMock(side_effect=save)))
            with patch.object(online, 'edge_module', return_value=Mock(Communicate=communicate)), \
                 patch.object(online, 'getproxies', return_value={'https':'http://proxy:80'}), \
                 patch.object(online, 'proxy_bypass', return_value=False):
                online.speak_edge('Xin chào','vi-VN-HoaiMyNeural', output, 1.2)
                self.assertEqual(output.read_bytes(), b'audio')
                self.assertEqual(communicate.call_args.kwargs['rate'], '+20%')
                self.assertEqual(communicate.call_args.kwargs['proxy'], 'http://proxy:80')
                with self.assertRaises(ValueError):
                    online.speak_edge('x','https://other-site/',output)
                communicate.return_value.save = AsyncMock(side_effect=OSError('private internal error'))
                with self.assertRaisesRegex(ValueError, 'Không tạo được'):
                    online.speak_edge('x','vi-VN-HoaiMyNeural',output)
                self.assertFalse(output.exists())

    def test_provider_protocols_domains_and_sanitized_errors(self):
        seen = []
        def respond(request):
            seen.append(request)
            if request.url.host == 'api.openai.com':
                return httpx.Response(200, json={'output':[{'type':'message','content':[{'type':'output_text','text':'Xin chào GPT'}]}]})
            return httpx.Response(200, json={'candidates':[{'content':{'parts':[{'text':'private reasoning','thought':True},{'text':'Xin chào Gemini'}]}}]})
        actual_client = httpx.Client
        def client(**kwargs):
            return actual_client(transport=httpx.MockTransport(respond), **kwargs)
        messages = [{'role':'user','content':'Xin chào'}, {'role':'assistant','content':'Chào bạn'}, {'role':'user','content':'Viết kịch bản'}]
        with patch.object(online.httpx, 'Client', side_effect=client):
            self.assertEqual(online.chat('openai','test-key','gpt-4.1-mini',messages), 'Xin chào GPT')
            self.assertEqual(online.chat('gemini','test-key','gemini-2.5-flash',messages), 'Xin chào Gemini')
        self.assertEqual(seen[0].url.host,'api.openai.com')
        self.assertEqual(seen[0].url.path,'/v1/responses')
        self.assertFalse(json.loads(seen[0].content)['store'])
        self.assertEqual(seen[0].headers['authorization'],'Bearer test-key')
        self.assertEqual(seen[1].url.host,'generativelanguage.googleapis.com')
        self.assertEqual(seen[1].headers['x-goog-api-key'],'test-key')
        self.assertEqual(json.loads(seen[1].content)['contents'][1]['role'],'model')
        for request in seen:
            self.assertNotIn('test-key', str(request.url))
        def fail(**kwargs):
            return actual_client(transport=httpx.MockTransport(lambda r: httpx.Response(429, text='secret-provider-detail')), **kwargs)
        with patch.object(online.httpx,'Client',side_effect=fail), self.assertRaises(ValueError) as error:
            online.chat('openai','test-key','gpt-4.1-mini',messages)
        self.assertNotIn('secret-provider-detail', str(error.exception))
        with self.assertRaises(ValueError):
            online.chat('gemini','test-key','../../other',messages)

    def test_api_chat_keys_not_persisted_or_echoed_and_optional_services(self):
        with TestClient(app.app) as client:
            payload = {'provider':'gemini','api_key':'test-secret-key','model':'gemini-2.5-flash',
                       'messages':[{'role':'user','content':'Chào bạn'}]}
            before = engine.jobs()
            with patch.object(online,'chat',return_value='Trả lời') as respond:
                result = client.post('/api/chat',json=payload)
                self.assertEqual(result.status_code,200,result.text)
                self.assertEqual(result.json()['text'],'Trả lời')
                self.assertEqual(respond.call_args.args[0],'gemini')
            self.assertEqual(engine.jobs(), before)
            self.assertNotIn('test-secret-key', client.get('/api/config').text)
            self.assertNotIn('test-secret-key', result.text)
            payload['api_key'] = 'test-secret-key\ninvalid'
            result = client.post('/api/chat',json=payload)
            self.assertEqual(result.status_code,422)
            self.assertNotIn('test-secret-key',result.text)
            result = client.post('/api/chat',json=payload,headers={'Origin':'https://foreign.example'})
            self.assertEqual(result.status_code,403)
            self.assertEqual(client.post('/api/tts',json={'text':'xin chào','provider':'capcut','voice':'fake'}).status_code,422)
            self.assertEqual(client.post('/api/tts',json={'text':'xin chào','provider':'edge','voice':'../../fake'}).status_code,422)
            self.assertIn('id',client.get('/api/health').json()['languages'])
            for path in engine.DATA.rglob('*'):
                if path.is_file() and path.suffix in ('.json','.txt','.log'):
                    self.assertNotIn(b'test-secret-key',path.read_bytes())


if __name__ == '__main__':
    unittest.main()
