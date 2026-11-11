import math,sys,threading,time,unittest
from pathlib import Path
import numpy as np
from autodoc.common import Cancelled,Context,srt
from autodoc.planner import make_plan,time_windows,words_for

class DummyModel:
    def text(self,texts):
        v=np.zeros((len(texts),16),dtype=np.float32)
        for i in range(len(texts)):v[i,i%12]=1
        return v

class PlanningTests(unittest.TestCase):
    def test_integer_timeline_and_ten_shot_hook(self):
        for seconds in [4,12,29.9,30,30.01,65.37,1215,1340]:
            total=math.ceil(seconds*24);w=time_windows(total,24,[{'end':i+.12} for i in range(1,math.ceil(seconds))])
            self.assertEqual(sum(x['end_frame']-x['start_frame'] for x in w),total)
            self.assertEqual(w[0]['start_frame'],0);self.assertEqual(w[-1]['end_frame'],total)
            self.assertTrue(all(x['end_frame']>x['start_frame'] for x in w))
            self.assertTrue(all(a['end_frame']==b['start_frame'] for a,b in zip(w,w[1:])))
            if seconds>=30:self.assertEqual(sum(x['opening'] for x in w),10)
    def test_screening_and_distinct_opening(self):
        files=[{'id':i,'name':f'{i}.mp4','seconds':10} for i in range(16)]
        cand=[{'id':i,'file_id':i,'source_start':0,'source_duration':10,'motion':.03,'quality':.2} for i in range(16)]
        features=np.eye(16,dtype=np.float32);screen=np.zeros((16,4),dtype=np.float32)
        screen[0]=[.1,.4,.1,.3] # likely minor
        screen[1]=[.1,.1,.5,.1] # likely card
        cues=[{'start':0,'end':60,'text':'mammoth bone circle landscape evidence'}]
        p=make_plan(cues,files,cand,features,screen,DummyModel(),60)
        self.assertEqual(p['opening_shots'],10);self.assertEqual(p['opening_distinct_files'],10)
        self.assertTrue(all(x['source_id'] not in [0,1] for x in p['shots']))
        self.assertEqual(sum(x['frames'] for x in p['shots']),1440)
    def test_reject_all_filtered_sources(self):
        files=[{'id':0,'name':'a.mp4','seconds':10}];cand=[{'id':0,'file_id':0,'source_duration':10,'quality':.1,'source_start':0,'motion':.1}]
        with self.assertRaises(ValueError):make_plan([{'start':0,'end':60,'text':'a'}],files,cand,np.zeros((1,16)),np.array([[.1,.5,.1,.2]]),DummyModel(),60)
    def test_srt_and_context_during_pause(self):
        cues=[{'start':1,'end':3,'text':'one'},{'start':9,'end':12,'text':'two'}]
        self.assertIn('00:00:01,000 --> 00:00:03,000',srt(cues))
        self.assertEqual(words_for(cues,5,6),'one')
    def test_cancel_running_process(self):
        stop=threading.Event();ctx=Context(lambda *_:None,stop)
        timer=threading.Timer(.2,stop.set);timer.start();start=time.monotonic()
        with self.assertRaises(Cancelled):ctx.run([sys.executable,'-c','import time; time.sleep(10)'],capture=True)
        timer.cancel();self.assertLess(time.monotonic()-start,5)

if __name__=='__main__':unittest.main()
