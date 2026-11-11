import copy,tempfile,unittest
from pathlib import Path
from autodoc.languages import subtitle_language,visual_reference
from autodoc.common import Context
from autodoc.project import options
from autodoc.subtitles import export

class LanguageTests(unittest.TestCase):
    def test_subtitle_language_detection(self):
        samples={'en':'The researchers found a circle built from mammoth bones. This evidence changes how we understand human history.','vi':'Các nhà nghiên cứu phát hiện một vòng tròn làm từ xương voi ma mút. Bằng chứng này thay đổi cách chúng ta hiểu lịch sử con người.','es':'Los investigadores encontraron un círculo construido con huesos de mamut. Esta evidencia cambia nuestra comprensión de la historia humana.','ja':'研究者たちはマンモスの骨で作られた円を発見しました。この証拠は人類の歴史についての理解を変えます。'}
        for code,text in samples.items():self.assertEqual(subtitle_language([{'text':text}])[0],code)
    def test_timed_reference_preserves_native_captions_and_hmong_bypasses_asr(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);path=folder/'English.srt';english=[{'start':0,'end':5,'text':'A circle made from mammoth bones.'}];export(english,path);native=[{'start':0,'end':5,'text':'Ib lub voj voog ua los ntawm pob txha.'}];before=copy.deepcopy(native)
            visual,meta,warnings=visual_reference(folder/'no_asr_required.wav',native,folder,options({'language':'hmn','visual_script_path':str(path)}),6,Context(lambda *_:None),False)
            self.assertEqual(native,before);self.assertEqual(visual,english);self.assertEqual(meta['visual_matching'],'reference_en_srt');self.assertEqual(meta['detected_language'],'hmn')
            with self.assertRaises(ValueError):visual_reference(folder/'x.wav',native,folder,options({'language':'hmn'}),6,Context(lambda *_:None),False)

if __name__=='__main__':unittest.main()
