# Voice Studio Hmong 1.2.0 validation

Separate Hmong White (Hmoob Daw, mww) variant of Voice Studio 3.6.2. The standard application retains its Vietnamese defaults and a separate Python environment. This document distinguishes implementation changes, completed diagnostic evidence and release checks; it does not certify native pronunciation.

## Input files and startup diagnosis

All 46 uploaded source/batch/document files matched the 1.1.0 versions after line-ending normalization. They did not include the required `static/`, `assets/hmong/`, Python runtime or FFmpeg directories. Individual source files cannot form the complete Windows application.

The previous inner `start_hmong.bat` required a source `.venv-hmong` even inside the portable package, whose bundled Python is in `runtime/`. The old generic `install.bat`/`start.bat` and README also described the Vietnamese environment. The previous `--check` path did not establish that the complete browser interface was present.

The 1.2.0 package routes root and inner `start.bat`/`start_hmong.bat` aliases to `MO_VOICE_STUDIO_HMONG.bat`; install aliases prepare the same Hmong runtime. Source `install_hmong.bat` creates and validates isolated Python 3.12 x64 `.venv-hmong`, checks the complete application, prepares FFmpeg with upstream SHA256 verification when needed, installs `requirements-hmong.txt`, runs `pip check`, and prepares models. It preserves personal data and the Vietnamese environment.

The stdlib-only bundle check requires application modules, browser files and all approved voice assets before library/model checks. It checks all four audio SHA256 values against `voices.json`. `--check` additionally checks FFmpeg/ffprobe, dependencies and local model integrity, without downloading or synthesizing audio. Missing resources give full-ZIP recovery guidance instead of a misleading success.

## Default voices and cloning

| Supplied file | SHA256 | Synthesis reference |
| --- | --- | --- |
| `hmong nam1.MP3` | `29285370b91db8465222b2056b204110c6dded1a60c9004c7fb8747fe4978c9c` | 0–4.5 seconds |
| `hmong nữ.MP3` | `2c3467e7b5f0e49a3277397c00762810f657fd1bbd36f738a7e17d0f067f6222` | 0–5.3 seconds |

Full originals remain available for preview. Their byte-identical uploads automatically select the approved excerpt and confirmed reference text. Other local 3–30 second uploads require a selected 3–8 second interval and its exact words. There is no guessed Hmong transcript. Saving a profile and generating new speech are distinct operations; Save and create test explicitly queues new synthesis.

The historical 1.1.0 clone fix addressed rejection of the full 19/22 second recordings by adding automatic known-reference selection and manual interval controls. Its earlier browser/inference and regression results are not treated as a successful 1.2.0 run.

## Text, timing and inference changes

- The default is now **16 steps**. Four/eight steps are explicit draft choices, and 32 steps remains available. CPU `auto` preserves FP32 for 8/16/32 steps. Explicitly choosing the four-step draft permits automatic CPU INT8 with verified FP32 fallback, without requiring configuration changes. `HMOOB_PRECISION=fp32` forces FP32 even at four steps; explicit `HMOOB_PRECISION=int8` remains experimental. Producing finite sound did not establish INT8 pronunciation parity.
- RPA normalization changes formatting only: whitespace, common typographic quotes/dashes and ellipses. It preserves case, all Latin letters and tone suffixes such as `b/j/v/s/g/m/d`. Other scripts, unsupported diacritics/control characters and characters absent from the model vocabulary produce actionable errors rather than unknown-token/space substitution. Numbers and names are not automatically translated into Hmong words.
- Estimated target duration uses the reference's observed seconds per RPA orthographic syllable, rather than the ratio of target/reference byte counts. This is a pacing heuristic; borrowed words, names and digits may not follow it.
- Very short input retains F5-TTS 1.1.22's below-ten-UTF-8-byte local-speed guard, with a one-second output floor. Batches obey character and reference-calibrated duration bounds and keep whole RPA tokens. These checks address truncated/rushed short output and excessive context; they do not prove semantic correctness.
- Consecutive short sentences are packed within bounded chunks so the same reference is not processed for every short sentence. Models/reference preprocessing are reused between chunks and jobs. These reduce repeated work while keeping memory bounded; no hardware-independent throughput is inferred.

The pinned [Hmong integration README](https://github.com/YangNobody12/F5-TTS-Hmong/blob/ec21db33d2dea156840bd6ff03a2087e950b067e/README.md) warns that long text and some words may be inaccurate. It recommends reference audio no longer than eight seconds, smaller chunks, and speed 0.8–0.9 for missed words, while warning that slowing too far can introduce reference speech. Its [inference constants](https://github.com/YangNobody12/F5-TTS-Hmong/blob/ec21db33d2dea156840bd6ff03a2087e950b067e/src/f5_tts/infer/utils_infer.py#L60) use `nfe_step = 32  # 16, 32`; this supports offering 16/32 rather than describing four steps as a validated quality default. The restored ten-byte guard comes from the installed upstream [F5-TTS 1.1.22 implementation](https://github.com/SWivid/F5-TTS/blob/9c614e9657089213efc6a7421b30630be138a3f5/src/f5_tts/infer/utils_infer.py#L491). The Hmong fork has a different, fifteen-character guard; it is not the source of the ten-byte threshold.

## Pronunciation diagnostic: ASR calibration failed

A QA-only local experiment evaluated `Pakorn2112/whisper-model-large-hmong/SingleSpeech` at revision `ad820dd7f90495cac4f74673f25e54956636de64`. The safetensor shards were downloaded over verified HTTPS and checked against upstream SHA256; small files were checked against Git blob identities. Inference used local files only, safetensors and `trust_remote_code=False`, following the author's English decoder-language prompt for this Hmong fine-tune. Neither user's audio was uploaded to a service. This ASR model is not shipped and adds no product feature.

The scorer was calibrated on the two real reference recordings before evaluating generated speech:

| Real reference | Word edits / reference words | Word error rate |
| --- | --- | --- |
| Male approved WAV | 13 / 14 | 92.86% |
| Female approved WAV | 21 / 16 | 131.25% |

Both exceeded the preselected 35% calibration threshold. WER can exceed 100% when insertions occur. These are **ASR errors on real recordings**, not scores for generated speech; they may reflect scorer, prompt, dialect or short-context limitations and do not establish that the confirmed reference words are wrong. Consequently no generated 4/16/32-step samples were scored with this ASR, and no automatic pronunciation improvement claim is supported by it. Native-listener assessment of intelligibility, tones and speaker similarity remains necessary.

The smaller `kengher2004/hmong-whisper-small` candidate was rejected before downloading weights because its own pinned model card reported WER 100% and lacked processor files. Stock Whisper does not expose a Hmong language token; forcing `language='hmong'` is not a supported replacement.

## Release verification record

Local 1.2.0 checks completed with Python 3.12:

- Shared regression suite: 214 passed, 5 skipped. Four skips require Torch in the separate Hmong environment; the remaining optional check is unrelated to Hmong. The five Chromium contract checks passed within this run.
- Focused checks in the actual pinned Hmong environment: 59 passed, including all five adapter/precision regressions. Both environments passed `pip check`.
- Actual offline checkpoint inference produced finite, non-silent PCM for both approved references at 16 steps FP32 and for the short female greeting `Nyob zoo.` at 32 steps FP32. The short greeting now lasts about 2.20 seconds. This checks execution and timing bounds, not word correctness or voice similarity.

The following **1.2.0 release checks must be completed and recorded by the release run**; this document does not assert that a pending run has passed:

- Python 3.12, pinned F5-TTS 1.1.22 and matching torch/torchaudio; `pip check` and shared regression results.
- Complete-bundle rejection for missing browser/assets, source installation validation, root/inner start/install aliases, and Hmong data/environment separation.
- Real synthesis for both preset voices and both full-MP3 clone paths at the new 16-step default; a manual interval from a different recording; TXT/SRT import, WAV/MP3 export and SRT alignment. Short text, mixed sentence lengths and long bounded input need distinct coverage.
- Native Windows x64 runtime relocated to a path with spaces, real offline inference, browser startup, first-run preparation and missing-first-run-model check.
- ZIP CRC, SHA256 and inventory checks; no builder-owned jobs, model cache, credentials or other personal profiles in the distribution. Publish measured timings with machine/precision/step information; do not use the earlier 4-step INT8 sample as the 16-step performance expectation.

Consult the successful release Actions run and packaged `NATIVE-VALIDATION.json` for the actual check results and timing. A nonempty/nonsilent file, passing regression test, successful clone route or speed measurement alone cannot establish correct Hmong pronunciation.

## Distribution and limits

First normal launch downloads approximately 1.4 GB of revision-pinned, checksum-verified F5-Hmong/Vocos files. Hmong weights are not redistributed because explicit redistribution terms are unclear. Prepared inference works offline without an API key. TLS/checksums remain enforced; a network policy blocking GitHub/Hugging Face can still prevent download.

The two explicitly supplied default MP3s and their approved references are included. No other personal profiles, jobs or credentials belong in the package. The QA-only ASR model/cache is excluded.

Story/review settings control tempo and pauses; they are not separately trained emotional voices. There is no bundled Hmong ASR or cloud GPU service. Runtime and memory depend on hardware, text, quality settings and reference pace. No one-hour-in-two-minutes promise, universal pronunciation guarantee or native speaker-similarity validation is made.
