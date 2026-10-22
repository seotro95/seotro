# Voice Studio Hmong 1.1.0 validation

Separate Hmong White (Hmoob Daw, mww) variant of Voice Studio 3.6.2. The standard application retains Vietnamese defaults and a separate Python environment.

## Defaults and cloning

Uploaded `hmong nam1.MP3` SHA256: `29285370b91db8465222b2056b204110c6dded1a60c9004c7fb8747fe4978c9c`. Uploaded `hmong nữ.MP3` SHA256: `2c3467e7b5f0e49a3277397c00762810f657fd1bbd36f738a7e17d0f067f6222`. These exactly match the project's approved originals with confirmed reference words. Full MP3s are included for preview; synthesis uses the approved male 0–4.5 second and female 0–5.3 second excerpts.

The old clone route rejected the full 19/22 second recordings because it accepted only 3–8 seconds and offered no trimming. Version 1.1.0 recognizes byte-identical originals and pairs the approved clip/words automatically. Other local 3–30 second uploads accept explicit 3–8 second selection and the exact words of that interval. There is no guessed Hmong transcription. Invalid ranges, corrupt/silent/oversized/unsupported uploads are rejected, with temporary files removed.

## Development checks

- Python 3.12, F5-TTS 1.1.22, torch/torchaudio 2.8.0+cpu; pip check passed.
- Actual Chromium workflow uploaded each MP3, received automatic clip/words, clicked Save and create test, and downloaded new audio from both personal voices at default 4 steps. No JavaScript errors. This used real inference, independently from mock UI contract tests.
- Full shared regression: 168 passed, 1 skipped. Additional focused checks exercise actual FFmpeg cropping and source hashes, independently from model quality.
- Isolated adapter probes: 3.723 seconds output took 31.20 seconds with FP32/8 steps and 6.84 seconds with INT8/4 steps, excluding load. A later same-script run recorded 44.803 and 7.546 seconds. Short sample measurements do not establish long-form throughput or equal speed on other hardware.
- Default 4-step draft uses automatic CPU INT8 when supported, with verified FP32 reload if automatic conversion fails. 8/16/32 steps remain available. Models/reference cache are retained across chunks; HMOOB_PRECISION=fp32 allows source users to compare the previous path.

## Native publication gate

The 1.1.0 workflow builds with Windows x64 Python 3.12.10, CPU wheels and verified FFmpeg. It relocates the full runtime to a path with spaces and checks real offline jobs: complete source MP3 preview hashes, both presets, both full-MP3 clones without manual words, a selected interval from a different long recording, TXT/SRT/MP3, 12-second SRT alignment and normal startup.

It also compares FP32/8 steps with optimized 4 steps on the same Windows machine, excluding model load, and requires a measured speed improvement. NATIVE-VALIDATION.json/public native-smoke.json records this measurement. This document does not assert a pending native run passed; consult the successful release Actions run and report.

## Distribution and limits

First-run preparation is tested, then only builder-owned QA data/models are stripped. Offline --check must report missing first-run weights. ZIP CRC/SHA256 are verified. No personal profiles/jobs/credentials are included beyond the two explicit default MP3s supplied for this purpose.

First normal launch downloads approximately 1.4 GB of pinned, checksum-verified upstream weights. Weights are not redistributed because explicit redistribution terms are unclear. Prepared inference is offline with no API key. TLS/checksums remain enforced. No cloud GPU service or credentials are supplied or implied.

Pronunciation/speaker similarity have not been scored by a native listener. Four steps trade quality for speed. Story/review control tempo/pauses; Hmong ASR is unsupported. No hardware-independent throughput or one-hour-in-two-minutes claim is made.
