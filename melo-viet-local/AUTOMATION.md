The server runs locally at `http://localhost:8817` after `MO_TOOL.bat` starts.
Load once, then reuse the same language and thread count for subsequent clips.
No shell commands are evaluated from request text. Audio is WAV PCM.

Use Python on Windows (standard library only), with the tool running:

```python
import json, time, urllib.request

BASE = 'http://localhost:8817'

def api(path, payload=None):
    request = urllib.request.Request(BASE + path,
        data=None if payload is None else json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)

def finished():
    while True:
        job = api('/api/job')
        if job['status'] == 'done':
            return job
        if job['status'] in {'error', 'cancelled'}:
            raise RuntimeError(job.get('error', job['status']))
        time.sleep(1)

api('/api/start', {'op': 'voices', 'language': 'KR', 'threads': 4})
voices = finished()['voices']
speaker = voices[0]['id']
api('/api/start', {'op': 'render', 'language': 'KR', 'threads': 4,
                  'voice': speaker, 'text': '안녕하세요. 오늘도 좋은 하루 보내세요.'})
job = finished()
with urllib.request.urlopen(BASE + job['audio_url']) as response:
    with open('korean.wav', 'wb') as output:
        while block := response.read(65536):
            output.write(block)
print(job)
```

Use `VI` for Vietnamese, `EN` English, `FR` French, `JP` Japanese,
`KR` Korean, `ES` Spanish, `ZH` Chinese. There are no RU/TH routes.
The actual voice list comes from each loaded model. Vietnamese and international
readers use separate interpreters. Output does not clone the old private samples.
