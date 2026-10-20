"""Offline integrity and bounded-engine contracts; these are not voice quality tests."""
from array import array
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import engine
import setup_voice


class EngineValidationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        self.reference = self.root / "reference.wav"
        pcm = array("h", (int(1000 * math.sin(i * .1)) for i in range(72000)))
        if sys.byteorder != "little":
            pcm.byteswap()
        with wave.open(str(self.reference), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(24000)
            output.writeframes(pcm.tobytes())

    def tearDown(self):
        self.folder.cleanup()

    def _manifest(self):
        records = {}
        for relative in engine.MODEL_FILES:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            data = (relative + " fixture").encode()
            path.write_bytes(data)
            records[relative] = {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        (self.root / "verified-models.json").write_text(json.dumps({"files": records}), encoding="utf-8")

    def test_checksum_is_rechecked_when_file_changes_same_size(self):
        self._manifest()
        engine.verify_models(self.root)
        path = self.root / engine.MODEL_FILES[0]
        stat = path.stat()
        path.write_bytes(b"x" * stat.st_size)
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        with self.assertRaises(engine.EngineError):
            engine.verify_models(self.root)

    def test_missing_manifest_is_not_ready_and_does_not_access_network(self):
        with patch.dict(os.environ, {"HMOOB_MODEL_DIR": str(self.root)}), \
                patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
            self.assertFalse(engine.availability()["ready"])

    def test_model_directory_respects_data_override(self):
        with patch.dict(os.environ, {"HMOOB_DATA_DIR": str(self.root)}):
            with patch.dict(os.environ, clear=False):
                os.environ.pop("HMOOB_MODEL_DIR", None)
                self.assertEqual(engine.model_directory(), self.root / "models")

    def test_bounded_batches_preserve_words_and_utf8(self):
        text = "Nyob zoo. Kuv yog Hmoob! " * 9 + "á" * 25
        pieces = list(engine._bounded_batches(text, 22))
        self.assertEqual("".join("".join(pieces).split()), "".join(text.split()))
        self.assertTrue(all(len(part.encode("utf-8")) <= 22 for part in pieces))

    def test_invalid_requests_rejected_before_model_load(self):
        speech = engine.SpeechEngine()
        with patch.object(speech, "_load", side_effect=AssertionError("loaded invalid request")):
            for text, transcript, speed, quality in [
                ("x" * 401, "ref", 1, "fast"), ("hello", "", 1, "fast"),
                ("hello", "ref", float("nan"), "fast"), ("hello", "ref", True, "fast"),
                ("hello", "ref", 1, "unknown"),
            ]:
                with self.subTest(text=text[:10], quality=quality):
                    with self.assertRaises(engine.EngineError):
                        speech.synthesize(text, self.reference, transcript, speed, quality)

    def test_synthesis_uses_sequential_adaptive_batches_with_selected_steps(self):
        import numpy as np
        speech = engine.SpeechEngine()
        calls = []

        def infer(reference, transcript, batches, model, vocoder, **settings):
            calls.append((batches, settings))
            yield np.ones(2400, dtype="float32") * .1, 24000, None

        fake_module = SimpleNamespace(infer_batch_process=infer)
        fake_model = SimpleNamespace(ema_model=object(), vocoder=object(), mel_spec_type="vocos")
        reference = (np.ones((1, 72000), dtype="float32"), 24000)
        text = "Nyob zoo. " * 30
        with patch.object(speech, "_load", return_value=fake_model), \
                patch.object(speech, "_prepare_reference", return_value=(reference, "Nyob zoo. ")), \
                patch.dict(sys.modules, {"f5_tts.infer.utils_infer": fake_module}):
            samples, rate = speech.synthesize(text, self.reference, "Nyob zoo.", quality="draft")
        self.assertGreater(len(calls), 1)
        self.assertEqual(rate, 24000)
        self.assertEqual(len(samples), len(calls) * 2400)
        self.assertTrue(all(len(batch) == 1 and settings["nfe_step"] == 8 for batch, settings in calls))
        self.assertEqual("".join("".join(batch[0] for batch, _ in calls).split()), "".join(text.split()))

    def test_silent_or_nonfinite_model_output_never_marks_a_chunk_complete(self):
        import numpy as np
        speech = engine.SpeechEngine()
        fake_model = SimpleNamespace(ema_model=object(), vocoder=object(), mel_spec_type="vocos")
        reference = (np.ones((1, 72000), dtype="float32"), 24000)
        for output in (np.zeros(2400), np.array([float("nan")])):
            def infer(*args, **kwargs):
                yield output, 24000, None
            with patch.object(speech, "_load", return_value=fake_model), \
                    patch.object(speech, "_prepare_reference", return_value=(reference, "Nyob zoo. ")), \
                    patch.dict(sys.modules, {"f5_tts.infer.utils_infer": SimpleNamespace(infer_batch_process=infer)}):
                with self.assertRaises(engine.EngineError):
                    speech.synthesize("Kuv yog Hmoob.", self.reference, "Nyob zoo.")


class InstallerIntegrityTests(unittest.TestCase):
    def test_metadata_requires_authoritative_identity_and_size(self):
        with self.assertRaises(setup_voice.SetupError):
            setup_voice._entry({"siblings": [{"rfilename": "vocab.txt", "size": 5}]}, "vocab.txt")

    def test_git_blob_checksum_for_small_file(self):
        data = b"abc\n"
        blob = hashlib.sha1(b"blob 4\0" + data).hexdigest()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "vocab.txt"
            path.write_bytes(data)
            self.assertEqual(setup_voice._verified(path, 4, None, blob), hashlib.sha256(data).hexdigest())
            self.assertIsNone(setup_voice._verified(path, 4, None, "0" * 40))

    def test_bad_download_is_removed_and_existing_model_preserved(self):
        import io
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "model.safetensors"
            path.write_bytes(b"existing")
            with patch("urllib.request.urlopen", return_value=io.BytesIO(b"bad")):
                with self.assertRaises(setup_voice.SetupError):
                    setup_voice._download("https://huggingface.co/file", path, 3, "0" * 64, None)
            self.assertEqual(path.read_bytes(), b"existing")
            self.assertEqual(list(Path(folder).glob("*.part")), [])


if __name__ == "__main__":
    unittest.main()
