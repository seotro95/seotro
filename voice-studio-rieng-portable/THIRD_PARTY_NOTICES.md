# Third-party components

Voice Studio Riêng provides application source and dependency specifications. The Windows Portable build also redistributes a Python runtime, installed dependencies, FFmpeg and Vietnamese model weights. A private voice update contains application changes and its supplied reference recordings, and reuses the installed Portable runtime. Optional international components are installed separately.

- Python: https://www.python.org/psf/license/ ; Portable license at `runtime/LICENSE.txt`.
- Python dependencies: license files and metadata remain in `runtime/Lib/site-packages/*.dist-info` for Portable, `.venv/Lib/site-packages/*.dist-info` for source installations, or `runtime-international/Lib/site-packages/*.dist-info` for the optional international runtime.
- VieNeu: https://pypi.org/project/vieneu/ and model cards at https://huggingface.co/pnnbao-ump . Portable model cards remain in `app/.data/models/cache/hub`; the model Apache-2.0 license is at `MODEL-APACHE-2.0-LICENSE.txt` or `BASE-MODEL-APACHE-2.0-LICENSE.txt`.
- MOSS Audio Tokenizer: https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX ; its model card remains beside the bundled tokenizer weights.
- Optional VoxCPM2: https://github.com/OpenBMB/VoxCPM and https://huggingface.co/openbmb/VoxCPM2 . Code and official model weights are Apache-2.0. The installer preserves the upstream model config and weights, license text and `MODEL_PROVENANCE.json` with the frozen upstream revision and file SHA256 values in `app/.data/models/voxcpm2-original`. CPU FP32 configuration is prepared in a separate derived directory; original model files remain unchanged. The public model pack contains only these official model files and notices, without user recordings.
- Optional Qwen3-TTS: https://github.com/QwenLM/Qwen3-TTS and relevant model cards on https://huggingface.co/Qwen ; not bundled with the Portable release.
- FFmpeg Windows GPL build: https://github.com/BtbN/FFmpeg-Builds . Portable notices and docs remain in `ffmpeg`, with the verified upstream checksum at `ffmpeg/UPSTREAM-SHA256.txt`. Source installation uses `tools/ffmpeg`.
- PyTorch CPU wheels: https://pytorch.org/ and https://download.pytorch.org/whl/cpu . Package license files remain in their runtime distribution metadata.
- Microsoft Visual C++ app-local runtime: https://learn.microsoft.com/cpp/windows/redistributing-visual-cpp-files ; subject to the Microsoft Visual Studio redistributable license.

Respect the applicable code, binary, model and recording licenses before redistribution. Public application packages exclude personal recordings, uploaded scripts, credentials and user history. Reference recordings supplied in a private voice pack remain separate from the public release and from the Apache-2.0 model license.
