# Verified local cloning implementation

Version0.4.3 uses CosyVoice3 Hmong instruct2 with each supplied male/female audio reference, without a reference transcript. The user-provided poem is not used as reference text. No API key or paid runtime service is needed.

Model source: https://huggingface.co/Xuajpaj2026/hmong-tts-weights , pinned revision5663e0df2589c2ca2403cd327a52702c3ff96e8f. The bundled manifest selects118 files (~5.43GB), avoiding optional duplicate ONNX and training artifacts. Downloader validates LFS SHA256 or Git blob SHA1, supports Range resume and rejects traversal/symlink escapes. Model code hashes are checked again before loading. Tensor checkpoints use weights_only=True; primitive epoch/step training metadata is removed only in memory. Inference YAML is selected and its constructors allowlisted before construction; training objects are not evaluated. No source/checkpoint files are rewritten.

The runtime uses offline Hub settings and local files, float32 CPU with four Torch threads. Each request runs in a cancellable worker process. Supplied references are decoded to mono24kHz and limited to10 seconds for instruct2 conditioning. Original MP3s remain unchanged. Nine style choices become actual model instructions; speed is passed to synthesis. Style strength, voice similarity and correct native pronunciation still require listening checks.

Validation on Linux CPU:

- Female neutral, expected text “Nyob zoo, kuv hais lus Hmoob.”: PCM16 mono24kHz,2.71seconds,130124bytes. Cold execution64.68seconds, peak RSS7.84GiB.
- Male Review, same expected text: PCM16 mono24kHz,2.51seconds,120524bytes. Real browser/API job completed in93.617seconds.
- Real browser stopped a worker, then completed a new job. No microphone request was made while selecting supplied references or creating voice. Mobile390px had no overflow or JS errors.
- Both outputs decode and contain nonzero finite samples. No native pronunciation or similarity rating has been performed.
- 83 Python tests passed for0.4.3, including five empty-artifact regressions and three single-launch/server-lifecycle tests. Prior0.4.1 passed8 Chromium microphone checks and dependencies pass pip check. Windows dependency resolution and wheel availability checked for CPython3.12x64; native Windows BAT/model inference unrun.

The cloud download restriction was resolved after network publication. Model bytes and sources are now verified under /workspace/models/hmong-cosy on the current cloud machine; set HMONG_COSY_DIR to that root there. Windows default is the extracted app's .data/models/hmong-cosy. Binary model weights are downloaded by install_clone_ai.bat, not included in the small source ZIP or Git repository.

Windows installer0.4.1 uses a fresh versioned clone environment and atomically selects it only after checks pass. Existing .venv and selected runtimes are never upgraded in place. Failed/interrupted attempts preserve the previous selection; rerunning a valid installation is read-only. Installer locking blocks concurrent installs. Full fresh install, read-only reuse and selected-runtime server startup were verified on Linux; native Windows remains unrun.

Downloader0.4.2 fixes missing .part errors for cold-cache zero-byte source files. Empty artifacts are materialized locally, verified against their pinned Git blob SHA1 or LFS SHA256, then atomically promoted. Bad checksums cannot replace existing targets. A real snapshot test omitted all12 empty files, reused5.43GB of hard-linked nonempty files, disabled HTTP entirely and completed the118-file ready marker; large weight sizes, modification times and inodes were unchanged. Updating code in the same app folder preserves .data and avoids downloading already verified weights again.

Package0.4.3 adds CHAY-STUDIO.bat: a single entry point installs missing prerequisites with the existing isolated-runtime installer, then starts the app using its selected interpreter. Ready runtimes are validated read-only. The browser is opened by the server child only after uvicorn has successfully started; a failed bind/startup does not open an unrelated local page. The ZIP includes app code, both supplied audio references and all installer fixes; dependencies and model weights are downloaded automatically when missing, not bundled as Windows binaries. The same archive root Hmong-Studio-Trang allows overlaying existing installs without replacing .data.

The actual launch command was exercised using the installed isolated interpreter and real model snapshot: it served API0.4.3 with local_cloning and cosy.ready true, retained the runtime pointer byte-for-byte, performed no pip installs and shut down its owned server. Linux browser handling used a no-op system browser; separate real socket tests verified that a browser callback can make HTTP200 requests after startup and is not called after application startup failure. Native Windows execution remains unrun.
