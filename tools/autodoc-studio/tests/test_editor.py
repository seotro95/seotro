import copy,json,tempfile,unittest
from pathlib import Path
from autodoc.project import options,save,load,reindex,split,merge_previous,change_fps,validate_project
from autodoc.subtitles import read_srt,align_txt,write_ass,export,style

def project(root):
    return reindex({'schema':'autodoc-project-2','settings':options(),'files':[{'id':0,'kind':'image','path':str(root/'photo.jpg')}],'voice_source':str(root/'voice.wav'),'project_file':str(root/'project.json'),'cues':[{'start':0,'end':10.015,'text':'Hello world.'}],'plan':{'fps':24,'voice_seconds':10.015,'shots':[{'source_id':0,'source_in':0,'frames':241,'effect':'zoom_in','transition':'cut','speed':1,'crop':1,'focus_x':.5,'focus_y':.5}]}})

class EditorTests(unittest.TestCase):
    def test_split_merge_fps_save_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=project(Path(tmp));split(p,0,3.25);self.assertEqual(sum(s['frames'] for s in p['plan']['shots']),241);self.assertEqual(p['plan']['shots'][1]['source_in'],3.25)
            change_fps(p,30);self.assertEqual(p['plan']['total_frames'],301);merge_previous(p,1);save(p);q=load(p['project_file']);self.assertEqual(q['plan']['shots'][0]['frames'],301)
            with self.assertRaises(ValueError):save(p,p['voice_source'])
    def test_reject_unsupported_effect_and_broken_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=project(Path(tmp));p['plan']['shots'][0]['effect']='arbitrary ffmpeg expression'
            with self.assertRaises(ValueError):validate_project(p)
            p=project(Path(tmp));p['plan']['shots'][0]['frames']=20
            with self.assertRaises(ValueError):validate_project(p)
    def test_srt_unicode_roundtrip_and_ass_literal_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'sub.srt';cues=[{'start':.1,'end':2.2,'text':'Xin chào {\\pos(1,2)}\nBằng chứng?'}];export(cues,path);loaded=read_srt(path,3);self.assertEqual(cues,loaded)
            ass=Path(tmp)/'sub.ass';write_ass(ass,loaded,1280,720,{'color':'#00FF00','bold':True});text=ass.read_text();self.assertIn('&H0000FF00',text);self.assertIn(r'\{\\pos(1,2)\}',text);self.assertIn(r'\NBằng chứng?',text)
            with self.assertRaises(ValueError):style({'color':'red;evil'})
            with self.assertRaises(ValueError):style({'font':'Arial,Subtitle'})
    def test_txt_align_retains_spelling_and_warns_bad_match(self):
        recognized=[{'start':0,'end':4,'text':'the hidden bone circle holds a secret'}]
        cues,ratio=align_txt('The hidden bone circle holds a secret!',recognized,4);self.assertGreater(ratio,.8);self.assertEqual(' '.join(c['text'] for c in cues),'The hidden bone circle holds a secret!')
        _,ratio=align_txt('Entirely different narration',recognized,4);self.assertLess(ratio,.3)
    def test_audio_and_style_defaults(self):
        d=options();self.assertTrue(d['mute_source']);self.assertEqual(d['encoder'],'auto')
        with self.assertRaises(ValueError):options({'source_volume':-1})
        with self.assertRaises(ValueError):options({'threads':999})
    def test_export_temporary_path_cannot_overwrite_source(self):
        from autodoc.render import export_movie
        from autodoc.common import Context
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=project(root);p['job']=str(root);p['files'][0]['path']=str(root/'movie.checking.mp4');p['files'][0]['kind']='video'
            source=root/'movie.checking.mp4';source.write_bytes(b'original clip content')
            with self.assertRaises(ValueError):export_movie(p,root/'movie.mp4',Context(lambda *_:None))
            self.assertEqual(source.read_bytes(),b'original clip content')

if __name__=='__main__':unittest.main()
