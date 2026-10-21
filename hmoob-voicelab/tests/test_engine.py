"""Offline integrity and bounded-engine contracts; these are not voice quality tests."""
from array import array
import hashlib
import importlib.util
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
        self.root = Path(self.folder.name).resolve()
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

    def test_missing_change_clock_disables_cache_and_still_detects_corruption(self):
        self._manifest()
        # Simulate a filesystem without a reliable change clock, even when
        # every available identity/timestamp value stays unchanged.
        with patch.object(engine, "_file_fingerprint", return_value=(1, 2, 3, 4, None)), \
                patch.object(engine, "_sha256", wraps=engine._sha256) as checksum:
            engine.verify_models(self.root)
            engine.verify_models(self.root)
            self.assertEqual(checksum.call_count, len(engine.MODEL_FILES) * 2)
            path = self.root / engine.MODEL_FILES[0]
            path.write_bytes(b"x" * path.stat().st_size)
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

        def infer(reference, transcript, batch, model, **settings):
            calls.append((batch, settings))
            return np.ones(2400, dtype="float32") * .1, 24000

        fake_model = SimpleNamespace(ema_model=object(), vocoder=object(), mel_spec_type="vocos")
        reference = (np.ones((1, 72000), dtype="float32"), 24000)
        text = "Nyob zoo. " * 30
        with patch.object(speech, "_load", return_value=fake_model), \
                patch.object(speech, "_prepare_reference", return_value=(reference, "Nyob zoo. ")), \
                patch("hmong_f5.infer_batch", side_effect=infer):
            samples, rate = speech.synthesize(text, self.reference, "Nyob zoo.", quality="draft")
        self.assertGreater(len(calls), 1)
        self.assertEqual(rate, 24000)
        self.assertEqual(len(samples), len(calls) * 2400)
        self.assertTrue(all(settings["steps"] == 8 for _, settings in calls))
        self.assertEqual("".join("".join(batch for batch, _ in calls).split()), "".join(text.split()))

    def test_silent_or_nonfinite_model_output_never_marks_a_chunk_complete(self):
        import numpy as np
        speech = engine.SpeechEngine()
        fake_model = SimpleNamespace(ema_model=object(), vocoder=object(), mel_spec_type="vocos")
        reference = (np.ones((1, 72000), dtype="float32"), 24000)
        for output in (np.zeros(2400), np.array([float("nan")])):
            def infer(*args, **kwargs):
                return output, 24000
            with patch.object(speech, "_load", return_value=fake_model), \
                    patch.object(speech, "_prepare_reference", return_value=(reference, "Nyob zoo. ")), \
                    patch("hmong_f5.infer_batch", side_effect=infer):
                with self.assertRaises(engine.EngineError):
                    speech.synthesize("Kuv yog Hmoob.", self.reference, "Nyob zoo.")

    @unittest.skipUnless(importlib.util.find_spec("f5_tts"), "Optional F5-TTS dependency is not installed")
    def test_real_f5_short_utterances_follow_selected_speed(self):
        # Exercise the adapter's actual batching/duration and waveform slicing;
        # only the costly neural model and vocoder are controlled fixtures.
        # No model download or claim about generated speech quality is made.
        with patch.dict(os.environ, {
            "MPLCONFIGDIR": str(self.root / "matplotlib"),
            "NUMBA_CACHE_DIR": str(self.root / "numba"),
            "XDG_CACHE_HOME": str(self.root / "cache"),
            "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        }), patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
            import torch
            from hmong_f5 import HOP_LENGTH

            requested_steps = []

            class Model:
                def sample(self, *, duration, steps, **kwargs):
                    requested_steps.append(steps)
                    return torch.zeros((1, duration, 100)), None

            class Vocoder:
                def decode(self, mel):
                    return torch.ones((1, mel.shape[-1] * HOP_LENGTH)) * .1

            speech = engine.SpeechEngine()
            speech.device = "cpu"
            model = SimpleNamespace(ema_model=Model(), vocoder=Vocoder(), mel_spec_type="vocos")
            for utterance in ("Nyob zoo.", "Zoo!"):
                lengths = []
                for speed in (.5, 1, 2):
                    with patch.object(speech, "_load", return_value=model):
                        samples, rate = speech.synthesize(
                            utterance, self.reference, "Kuv yog ib tug Hmoob.", speed=speed, quality="fast")
                    lengths.append(len(samples))
                    self.assertEqual(rate, 24000)
                with self.subTest(utterance=utterance):
                    self.assertGreater(lengths[0], lengths[1])
                    self.assertGreater(lengths[1], lengths[2])
                    self.assertAlmostEqual(lengths[0], 2 * lengths[1], delta=512)
                    self.assertAlmostEqual(lengths[1], 2 * lengths[2], delta=512)
            self.assertEqual(requested_steps, [16] * 6)

    def test_progress_callback_reports_work_and_can_be_cleared(self):
        import numpy as np
        speech = engine.SpeechEngine()
        messages = []
        speech.set_progress_callback(messages.append)
        reference = (np.ones((1, 72000), dtype="float32"), 24000)
        with patch.object(speech, "_load", return_value=object()), \
                patch.object(speech, "_prepare_reference", return_value=(reference, "Nyob zoo. ")), \
                patch("hmong_f5.infer_batch", return_value=(np.ones(2400) * .1, 24000)):
            speech.synthesize("Kuv yog Hmoob.", self.reference, "Nyob zoo.")
            self.assertEqual(messages, ["Đang chuẩn bị đoạn giọng mẫu…", "Đang tạo âm thanh…"])
            speech.set_progress_callback(None)
            messages.clear()
            speech.synthesize("Kuv yog Hmoob.", self.reference, "Nyob zoo.")
            self.assertEqual(messages, [])


class InstallerIntegrityTests(unittest.TestCase):
    def test_installer_rejects_metadata_for_an_unvalidated_model_revision(self):
        import io
        for repository, _ in setup_voice.SOURCES:
            with self.subTest(repository=repository):
                body = json.dumps({'sha': '1' * 40}).encode()
                with patch('urllib.request.urlopen', return_value=io.BytesIO(body)):
                    with self.assertRaisesRegex(setup_voice.SetupError, 'khác bản'):
                        setup_voice._get_metadata(repository)

    def test_installer_uses_the_validated_revision_even_if_main_has_changed(self):
        import io
        for repository, _ in setup_voice.SOURCES:
            expected = setup_voice.MODEL_REVISIONS[repository]
            body = json.dumps({'sha': expected, 'siblings': []}).encode()
            with self.subTest(repository=repository):
                with patch('urllib.request.urlopen', return_value=io.BytesIO(body)) as request:
                    self.assertEqual(setup_voice._get_metadata(repository)['sha'], expected)
                self.assertIn('/revision/' + expected + '?blobs=true', request.call_args.args[0].full_url)

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
