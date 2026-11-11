import shutil,tempfile,unittest,zipfile
from pathlib import Path
from autodoc.resources import VAD_ASSET,VAD_ARCHIVE_PATH,VAD_SHA256,prepare_distribution,validate_archive,verify_vad_asset,check_vad

class DistributionTests(unittest.TestCase):
    def test_packaging_keeps_vad_but_removes_only_example_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            app=Path(tmp)/'AutoDocStudio';examples=app/'_internal/onnxruntime/datasets';examples.mkdir(parents=True);(examples/'unused.onnx').write_bytes(b'unused example')
            info=prepare_distribution(app);self.assertEqual(info['sha256'],VAD_SHA256);self.assertFalse((examples/'unused.onnx').exists());self.assertTrue((app/'_internal/faster_whisper/assets'/VAD_ASSET).is_file())
            archive=Path(tmp)/'delivered.zip'
            with zipfile.ZipFile(archive,'w') as z:
                for p in app.rglob('*'):
                    if p.is_file():z.write(p,'AutoDocStudio/'+p.relative_to(app).as_posix())
            self.assertTrue(validate_archive(archive)['required_vad_present'])
    def test_shipped_archive_without_vad_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'old.zip'
            with zipfile.ZipFile(path,'w') as z:z.writestr('AutoDocStudio/AutoDocStudio.exe',b'test placeholder')
            with self.assertRaisesRegex(RuntimeError,'ZIP thiếu'):validate_archive(path)
            with self.assertRaisesRegex(RuntimeError,'Thiếu hoặc hỏng'):verify_vad_asset(tmp)
    def test_actual_bundled_model_can_run_onnx_inference(self):
        result=check_vad();self.assertTrue(result['onnx_inference_passed']);self.assertEqual(result['sha256'],VAD_SHA256)

if __name__=='__main__':unittest.main()
