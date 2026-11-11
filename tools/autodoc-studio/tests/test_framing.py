import tempfile,unittest
from pathlib import Path
from autodoc.framing import dimensions,pointer_in_image
from autodoc.project import options
from autodoc.subtitles import write_ass

class FramingTests(unittest.TestCase):
    def test_real_video_sizes_for_both_orientations(self):
        self.assertEqual(dimensions(720,'16:9'),(1280,720));self.assertEqual(dimensions(720,'9:16'),(720,1280));self.assertEqual(dimensions(1080,'16:9'),(1920,1080));self.assertEqual(dimensions(1080,'9:16'),(1080,1920));self.assertEqual(dimensions(360,'9:16'),(360,640))
        self.assertEqual(options()['aspect_ratio'],'16:9')
        with self.assertRaises(ValueError):options({'aspect_ratio':'1:1'})
    def test_caption_size_tracks_short_edge_for_portrait(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'captions.ass';write_ass(path,[{'start':0,'end':2,'text':'A vertical story.'}],720,1280,{'size':32});text=path.read_text();self.assertIn('PlayResX: 720',text);self.assertIn('PlayResY: 1280',text);self.assertIn('Style: Default,Arial,32.0,',text)
    def test_click_mapping_ignores_bars_and_maps_inside_portrait(self):
        box=(200,0,180,320);self.assertIsNone(pointer_in_image(100,150,box));self.assertEqual(pointer_in_image(290,160,box),(.5,.5));self.assertEqual(pointer_in_image(200,0,box),(0,0));self.assertIsNone(pointer_in_image(300,350,box))

if __name__=='__main__':unittest.main()
