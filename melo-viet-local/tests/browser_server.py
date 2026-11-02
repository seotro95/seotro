"""Browser test fixture; every generated waveform is synthetic, not a model benchmark."""
import argparse
from pathlib import Path
import sys
import time
import wave
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app

class SyntheticReader:
    def __init__(self,*args):pass
    def close(self):pass
    def request(self,body,cancel=None):
        time.sleep(.08)
        if body['op']=='catalog':
            voices=[{'id':locale+'-'+name,'name':name+' (synthetic UI test)','locale':locale,'gender':gender}
                for locale in ['vi-VN','fr-FR','ru-RU','th-TH'] for name,gender in [('A','Female'),('B','Male')]]
            return {'voices':voices,'locales':{k:2 for k in ['vi-VN','fr-FR','ru-RU','th-TH']}}
        if body['op']=='voices':return {'voices':[{'id':'voice-a','name':'Synthetic A','gender':'Male'},{'id':'voice-b','name':'Synthetic B','gender':'Female'}]}
        if body.get('voice')=='ru-RU-B':raise RuntimeError('Lỗi dịch vụ giả lập: không trả về âm thanh')
        with wave.open(body['output'],'wb') as f:
            f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(b'\x01\x00'*4800)
        return {'audio_seconds':.2,'model_load_seconds':0}

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
for engine in ('melo','viet','piper'):
    folder=a.root/'envs'/engine/'bin';folder.mkdir(parents=True,exist_ok=True);(folder/'python').touch()
studio=app.Studio(a.root,reader_factory=SyntheticReader)
server=app.ThreadingHTTPServer(('127.0.0.1',0),app.handler(studio))
print(server.server_port,flush=True)
try:server.serve_forever()
finally:server.server_close();studio.close()
