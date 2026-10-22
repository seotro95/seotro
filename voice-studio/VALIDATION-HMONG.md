# Voice Studio Hmong 1.0.0 validation

This is a separate Hmong White (Hmoob Daw, mww) variant of the shared Voice Studio 3.6.2 application. `VOICE_STUDIO_VARIANT=hmong` selects the variant; the standard application retains Vietnamese defaults.

## Completed in the cloud development machine

- Python 3.12, F5-TTS 1.1.22, torch/torchaudio 2.8.0+cpu in a separate environment; `pip check` passed.
- Fixed upstream revisions downloaded with HTTPS and verified LFS SHA256 or Git-blob identities. Local model integrity is checked before inference. No TLS or checksum bypass.
- Real F5 female synthesis: 5.131 seconds of non-silent finite audio in 43.136 seconds including initial model loading, using draft 8 steps. This is a small CPU sample, not a long-form throughput guarantee.
- Real live-server jobs: male/story 4.018 seconds audio (56.633 seconds job time), reference clone 2.485 seconds (27.209 seconds), SRT-aligned output exactly 12 seconds (28.745 seconds). MP3 export passed. These measurements are not controlled cross-machine benchmarks.
- Chromium exercised the actual live Hmong app: default mww, TXT input, female/review synthesis at 8 steps, WAV download, TXT/SRT export, SRT import, no JavaScript errors.
- Shared regression suite: 164 passed, 1 skipped before the final progress-preservation regression. Focused Hmong routing and packaging checks then passed 8 tests; worker regression checks passed 7 tests. The skip is distinct from a pass.
- Hmong launcher `--check` verifies cached prerequisites without making an inference claim. JavaScript syntax, shell syntax and changed Python compilation passed.

## Required native release checks

The separate `voice-studio-hmong-release.yml` workflow builds with Windows x64 Python 3.12.10 and CPU wheels, then moves the entire packaged runtime to a new path with spaces. Its real smoke creates female, male, reference-clone and timed SRT jobs, exports MP3/TXT/SRT, verifies non-silent finite 24 kHz audio, and starts the normal launcher. It tests first-run preparation before QA, then strips builder-owned models/data and confirms an offline check reports missing models. ZIP CRC and SHA256 are verified before publishing. Consult the successful Actions run and the package's `NATIVE-VALIDATION.json` for the actual native result; this document alone does not assert that an unexecuted native run passed.

## Practical limits

Weights are not redistributed in the ZIP: the normal first launch downloads approximately 1.4 GB from the pinned upstream model sources; subsequent prepared inference is offline. Windows package includes Python/dependencies/FFmpeg and the project's approved transcribed reference clips. No personal profiles, jobs or credentials are bundled.

Hmong pronunciation and speaker similarity have not been evaluated by a native listener in these checks. Story/review styles control tempo and pauses. Hmong speech recognition is unavailable; manual TXT/SRT remains supported. No claim of generating one hour of speech in two minutes is made.
