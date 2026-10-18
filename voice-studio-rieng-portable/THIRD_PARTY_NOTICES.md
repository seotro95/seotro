# Third-party components

This standalone package adapts the voice components of the user's `seotro95/seotro` repository. Original project source files in the cloud checkout were left unchanged.

The archive contains application source and dependency specifications. It does not redistribute Python, installed Python packages, FFmpeg binaries, or model weights. Installing optional components downloads them from their upstream publishers under their respective licenses.

- Python: https://www.python.org/psf/license/
- Python dependencies: their licenses and metadata are retained in `.venv/Lib/site-packages/*.dist-info` after Windows installation.
- VieNeu: https://pypi.org/project/vieneu/ and the model cards at https://huggingface.co/pnnbao-ump
- Qwen3-TTS: https://github.com/QwenLM/Qwen3-TTS and the relevant model cards on https://huggingface.co/Qwen
- Optional FFmpeg Windows build: https://github.com/BtbN/FFmpeg-Builds ; GPL build. The installer retains upstream notices, docs and licenses in `tools/ffmpeg`, and the verified upstream asset checksum in `UPSTREAM-SHA256.txt`.
- PyTorch CPU wheels: https://pytorch.org/ and https://download.pytorch.org/whl/cpu

Respect the applicable licenses before redistributing any runtime or model downloaded later. Personal recordings and credentials are not included in this package.
