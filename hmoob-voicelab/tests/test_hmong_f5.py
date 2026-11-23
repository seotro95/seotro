"""Offline adapter parity using real tensor operations and controlled models."""
import ast
from concurrent.futures import ThreadPoolExecutor
import importlib.util
from importlib.resources import files
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import hmong_f5


class AdapterImportTests(unittest.TestCase):
    def test_import_does_not_load_native_or_upstream_api_modules(self):
        code = ("import sys, engine, hmong_f5; "
                "assert not any(name in sys.modules for name in "
                "('torch','f5_tts.api','f5_tts.infer.utils_infer','matplotlib','transformers'))")
        result = subprocess.run([sys.executable, '-c', code], cwd=Path(hmong_f5.__file__).parent,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(importlib.util.find_spec('f5_tts'), 'Optional F5-TTS dependency is not installed')
class NativeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.environment = patch.dict(os.environ, {
            'MPLCONFIGDIR': str(self.root / 'matplotlib'),
            'NUMBA_CACHE_DIR': str(self.root / 'numba'),
            'XDG_CACHE_HOME': str(self.root / 'cache'),
            'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def upstream_batch(self):
        # Execute the installed upstream function verbatim without importing
        # its unrelated plotting/ASR module. This compares actual library code
        # while keeping the regression runnable with the lean runtime imports.
        import numpy as np
        import torch
        import torchaudio
        from f5_tts.model.utils import convert_char_to_pinyin
        source = files('f5_tts').joinpath('infer/utils_infer.py').read_text(encoding='utf-8')
        node = next(node for node in ast.parse(source).body
                    if isinstance(node, ast.FunctionDef) and node.name == 'infer_batch_process')
        namespace = {'np': np, 'torch': torch, 'torchaudio': torchaudio, 'tqdm': None,
                     'ThreadPoolExecutor': ThreadPoolExecutor, 'target_sample_rate': 24000,
                     'hop_length': 256, 'convert_char_to_pinyin': convert_char_to_pinyin}
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<installed-f5-batch>', 'exec'), namespace)
        return namespace['infer_batch_process']

    def test_waveform_and_sample_contract_match_upstream_at_selected_speeds_and_rms(self):
        import numpy as np
        import torch
        upstream = self.upstream_batch()

        class Model:
            def __init__(self):
                self.calls = []

            def sample(self, **settings):
                self.calls.append(settings)
                value = settings['cond'].mean()
                return torch.ones((1, settings['duration'], 100)) * value, None

        class Vocoder:
            def decode(self, mel):
                return mel.mean(dim=1).repeat_interleave(256, dim=-1)

        for amplitude in (.02, .2):
            for speed in (.5, 1, 2):
                with self.subTest(amplitude=amplitude, speed=speed):
                    reference = (torch.full((1, 72000), amplitude), 24000)
                    actual_model, expected_model = Model(), Model()
                    adapter_model = SimpleNamespace(ema_model=actual_model, vocoder=Vocoder())
                    text = 'Nyob zoo, kuv yog ib tug Hmoob.'
                    actual, rate = hmong_f5.infer_batch(
                        reference, 'Nyob zoo. ', text, adapter_model,
                        steps=16, speed=speed, device='cpu')
                    expected, expected_rate, _ = next(upstream(
                        reference, 'Nyob zoo. ', [text], expected_model, Vocoder(),
                        progress=None, cross_fade_duration=0, nfe_step=16, speed=speed, device='cpu'))
                    self.assertEqual(rate, expected_rate)
                    np.testing.assert_array_equal(actual, expected)
                    actual_call, expected_call = actual_model.calls[0], expected_model.calls[0]
                    self.assertEqual(actual_call.keys(), expected_call.keys())
                    for key in actual_call:
                        if key == 'cond':
                            torch.testing.assert_close(actual_call[key], expected_call[key], rtol=0, atol=0)
                        else:
                            self.assertEqual(actual_call[key], expected_call[key])

    def test_ema_checkpoint_conversion_removes_only_legacy_buffers_and_metadata(self):
        import torch
        from safetensors.torch import save_file
        checkpoint = self.root / 'model.safetensors'
        wanted = torch.full((2, 2), .25)
        save_file({'ema_model.weight': wanted,
                   'initted': torch.tensor(True), 'step': torch.tensor(4),
                   'ema_model.mel_spec.mel_stft.mel_scale.fb': torch.ones(1),
                   'ema_model.mel_spec.mel_stft.spectrogram.window': torch.ones(1)}, str(checkpoint))
        model = torch.nn.Linear(2, 2, bias=False)
        loaded = hmong_f5._load_ema_checkpoint(model, checkpoint, 'cpu')
        self.assertIs(loaded, model)
        torch.testing.assert_close(model.weight, wanted, rtol=0, atol=0)
        self.assertEqual(model.weight.dtype, torch.float32)
        save_file({'ema_model.unknown': torch.ones(1)}, str(checkpoint))
        with self.assertRaises(RuntimeError):
            hmong_f5._load_ema_checkpoint(model, checkpoint, 'cpu')


if __name__ == '__main__':
    unittest.main()
