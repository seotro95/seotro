# Native Windows portable build

Run in a clean **Windows x64** CI checkout. The regular Linux setup/source ZIP is
not a portable Windows release. Never copy a developer's `.data`, `.venv`, keys,
uploads or recordings into this build.

The fastest supported build reuses only the runtime, FFmpeg and prepared model
storage from the checksum-pinned, native-Windows-tested `windows-portable-36`
release. It overlays the standalone app and reruns its own relocated offline
tests; old app code and project history are excluded.

The older base lacks psutil. The builder adds its pinned, hash-verified Windows
wheel with bundled Python before offline QA. Physical-core/RAM detection must
succeed in the native smoke; missing detection cannot silently pass as a
one-worker hardware budget. RUNTIME-ADDITIONS.txt records the added dependency.

```powershell
python packaging/build_windows.py --output "$env:RUNNER_TEMP/Voice-Studio-Rieng-1.10.0-Portable" --base-archive "$env:RUNNER_TEMP/Voice-Studio-Windows-x64.zip"
```

Pinned base URL:
`https://github.com/seotro95/seotro/releases/download/windows-portable-36/Voice-Studio-Windows-x64.zip`

Pinned SHA256:
`5998b2f9e5198cf8ef4ab82a4796539bed0754f2b5eeaeb4da72d4fec27d1501`

For a fresh build, use base Python 3.12 x64 (not a venv) on `windows-2022`, install
`requirements-runtime.txt`, then omit `--base-archive`. Nano is required; pass
`--include-turbo` to additionally prepare Turbo. MSVC app-local runtime libraries
are copied from the installed Visual Studio redistributable directory. FFmpeg is
downloaded with verified upstream SHA256, preserving its license and docs.
TLS, checksums and package verification must remain enabled.

Both modes require successful offline real model inference, the exact
1.410s-into-0.900s regression, pitch/tail preservation and actual launcher HTTP.
The entire folder is moved to a path with spaces and non-ASCII text before those
checks, using its bundled `runtime/python.exe`. Synthetic regression tones do not
establish speech intelligibility; compressed cues still require listening.

Only after those Windows checks pass does the builder write `BUILD_INFO.json`,
the complete file SHA256 manifest, ZIP and ZIP checksum. A successful build may be
published as a GitHub release; a Linux source archive must not be described as a
tested ready-to-use Windows binary.

Version 1.9 additionally runs `benchmark_shared_runtime.py` in the relocated
bundled interpreter. Separate native subprocesses compare two shared-weight
tasks with two independent model processes for Nano and Turbo, then validate
real SRT timing on both paths. Peak process-tree RSS, cold/warm speech throughput
and sampling limitations are saved in `SHARED-MODEL-QA.json`. The shared cases
must observe distinct engine copies/decode locks and identical ONNX session
objects. Nano gets a benchmark-only deterministic per-text seed; Turbo retains
production stochastic sampling. The whole-hour 30x goal is not inferred from
short samples, RAM savings, or artificial subtitle silence.

The optional international runtime separately runs small-tensor attention/cache,
INT8 rollback/precision and IPC tests. It does not load the private reference
recordings or the full international model on GitHub Actions. FP32 stays the
default; real INT8 language checks and Linux measurements are reported with
their own scope and quality limits. INT8 cold model conversion can consume more
RAM and time than its eventual resident allocation.

Expect roughly 1.2 GB compressed for the prepared base variant, 3–5 GB unpacked,
about 8–12 GB temporary disk and 4–8 GB RAM during single-process Nano/Turbo
validation. Actual size/time depends on model revisions and runner throughput.
Base download, extraction, tests and compression commonly need 5–15 minutes;
fresh preparation may need substantially longer.

Version 1.6 tests real Nano news pacing at native speed 1.04 and the fast WSOLA fitter. Two fresh ten-sentence, four-step, two-process jobs measure cold and warm throughput; no artificial paragraph gaps or subtitle silence count as speech. PORTABLE-QA.json and BUILD_INFO.json record measured estimates, without promising 30x realtime or a result on another PC. Worker pools close before relocation moves back.

Version 1.6 expands bounded Nano pools to32, budgets physical CPU cores and available RAM, and calibrates candidate worker/thread teams with fresh real speech. Steps stay unchanged within the selected mode. The native smoke also measures and persists a real on-runner calibration, including warm model reuse and temporary-output cleanup. The runner calibration is removed before packaging so each user calibrates their own hardware.

Version 1.6 enables the same bounded ordered process pool for Turbo/Mai Anh, honors per-worker ORT threads, limits nested BLAS teams, and budgets 3GiB per Turbo worker. Calibration records are separated by engine. Native QA additionally requires real Mai Anh FP32 two-worker SRT alignment and cold/warm HTTP benchmarks. An explicit UI Nano comparison changes the selected voice and starts measurement without replacing the editor text.

Version 1.10 saves custom Turbo speaker embeddings and reference codes in a
private, validated local cache. After enrollment, custom VI/EN references use
the same `voice` dictionary path as built-in Turbo presets. This avoids reading
and locking the reference for every sentence and re-encoding after restarts; it
does not establish a 30x end-to-end synthesis result. Cached voice data is not
part of the public archive. A changed reference invalidates its content key.
Native smoke enrollment uses generated audio from the public Mai Anh preset,
checks exact array round trips, disables the encoder, and requires actual
dictionary-based speech inference after a disk cache hit. The prepare/load
timings are recorded in `PORTABLE-QA.json`; private references are never used.

Automatic ONNX CPU selection keeps shared weights until calibration compares
actual speech with shared and process execution and records a measured winner.
Results are scoped to the engine, quality mode, resource profile and precision.
The calibration preserves the selected voice and synthesis steps. Explicit
shared/process choices remain available within CPU/RAM budgets.

Turbo supports Vietnamese and English. The private Korean, Russian, Japanese,
French, Spanish and Thai defaults continue to use the separate multilingual
VoxCPM2 runtime. Labeling a sample as a default does not change that engine.
No equal-speed or full-hour 30x result is claimed for these references.

`.github/workflows/voice-studio-reference-1.10.yml` builds a single full Windows
download on pushes to `voice-studio-throughput-v1.10.0` or a manual dispatch.
It keeps the existing encrypted 19-voice package, tests the current application
and legacy unlock path, and publishes only after native Windows QA passes.
