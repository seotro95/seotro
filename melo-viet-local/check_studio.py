"""Real local-model pipeline test; fresh and cached assembly are reported separately."""
import argparse
import json
from pathlib import Path
import time
from app import Studio
from documents import parse_document


def main(root,output):
    studio=Studio(root);report={'platform':'Linux CI, not Windows/Xeon','real_model_audio':True,
        'human_listening_quality_verified':False,'target_30x_verified':False,'results':[]}
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    def wait(ident):
        end=time.monotonic()+180
        while time.monotonic()<end:
            job=studio.jobs[ident]
            if job['status'] in {'done','error','cancelled'}:
                if job['status']!='done':raise RuntimeError(str(job.get('error')))
                return job
            time.sleep(.1)
        raise TimeoutError('Local pipeline timeout')
    try:
        voice=wait(studio.start({'op':'voices','language':'VI','threads':2})['id'])['voices'][0]['id']
        request={'op':'render','language':'VI','voice':voice,'threads':2,'speed':1.1,'style':'narration','chunk_size':80,'name':'public-test.srt',
          'text':'1\n00:00:20,000 --> 00:00:25,000\nXin chào các bạn. Đây là một đoạn thử giọng tiếng Việt.\n\n2\n00:00:30,000 --> 00:00:35,000\nCông cụ tạo phụ đề theo từng đoạn âm thanh thực tế.\n','use_cache':False}
        first=wait(studio.start(request)['id']);request['use_cache']=True
        second=wait(studio.start(request)['id'])
        assert first['cache_hits']==0 and second['cache_hits']==second['total_chunks']
        cues=parse_document((Path(root)/'outputs'/first['id']/'subtitles.srt').read_text(),'out.srt')['cues']
        assert cues[0]['start_ms']==0
        report['results']=[{k:r[k] for k in ('audio_seconds','processing_seconds','realtime_multiplier','cache_hits','total_chunks','fresh_inference','speed')} for r in (first,second)]
        report['status']='passed'
    finally:
        studio.close();(output/'STUDIO-QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Real local-model pipeline passed; cached work is labelled separately.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();main(a.root,a.output)
