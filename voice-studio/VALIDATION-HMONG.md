# Voice Studio Hmong 1.3.0 validation

This release replaces both default recordings and adds explicit storytelling controls. It does not certify native Hmong pronunciation or human emotional acting. The separate standard Voice Studio 3.6.2 defaults/environment are preserved.

## New reference recordings

| Uploaded recording | Original SHA256 | Source duration | Synthesis interval |
| --- | --- | --- | --- |
| hmong nữ 2(1).MP3 | 874f510e723f48fcd093d55a5ba4613fc80107a863261658ec9d3961ef493d84 | 4.7020 s | 0–4.7 s |
| hmong nam 2.MP3 | bc9104c2ebe00471abc46283c52627b2cadc615d96f15f1dc9d576b1316d78c8 | 4.7020 s | 0–4.7 s |

Both original MP3s are retained byte-for-byte for preview. All four active voice assets were replaced; old reference audio/text is not used as a default. Personal saved profiles/history are not deleted. Reference WAVs are mono PCM16 at24kHz and SHA256-checked by the launcher.

The initially uploaded female2 file had about18.85s of trailing exact silence. The user then explicitly replaced it with `hmong nữ 2(1).MP3`, about4.702s, and requested removal of the long version. Only this final short original is included. Both references use0–4.7s, preserving voiced content and quiet endings. PCM analysis found no full-scale clipping; reference peaks are about0.352/0.386 and RMS0.072/0.055 for female/male. Statistics do not certify pronunciation or identify word boundaries.

## User-provided reference words

On23October2026 the user supplied the exact words for the female excerpt and whole male recording, then confirmed the words still match the replacement short female file. `voices.json` records `reference_text_verified:true`, `reference_text_source:user_provided_for_selected_excerpt` and the confirmation date. This flag means user-provided/confirmed reference text, not independent certification of model output. The user's RPA spellings are preserved rather than automatically corrected.

The reference words are:

- Male: `hais tias tus neeng uas nyob rau ntawm yug ib sab no nws xav dag tsis rau yug`
- Female: `nyob zoo os yawb txiv , kuv nim qhov los xwb, ntseem tsis ntaub muaj dab tsis li os`

Initial cached local Hmong-ASR analysis yielded candidate words only. Those guesses were replaced by the user's words; no ASR-derived text is used as the authoritative default. No external inference service received the recordings. The QA recognizer is not packaged or advertised as a supported Hmong-ASR feature. Candidate timestamps and prior reference disagreement are not pronunciation scores.

Stored words remain editable for known originals. Custom text is not overwritten when crop bounds are omitted. Audio identity is verified separately by SHA256. The model's native pronunciation, dialect fidelity, speaker likeness and emotional realism still require listening assessment.

New preset jobs bind checkpoints and the warm synthesizer cache to a SHA256 fingerprint of the verified reference WAV and exact transcript. API resume and worker rendering reject missing/mismatched identities before reusing or modifying cached audio. Legacy preset jobs must start a new job after the default replacement; saved profiles/history and existing chunks are preserved.

## Storytelling and expression contract

New Hmong jobs use `hmong-expression-v1`. Supported passage controls are `[emotion=neutral|warm|joyful|sad|serious|suspense]`, `**emphasis**` and `[pause=0.5]` (seconds,0–10). Controls are parsed before RPA normalization and are never sent to F5 as words. Unknown/malformed controls produce actionable errors. TXT emotion state persists until changed; each SRT cue restarts from the chosen global emotion.

The implementation uses small pitch-preserving tempo adjustments, gain, a bounded smooth PCM energy envelope, and punctuation/paragraph pauses. It does not manipulate pitch contours, add vibrato or synthesize breath/laughter. Hmong lexical tone letters remain intact. This is rhythm/dynamics processing, not a trained emotion-control model. Result metadata explicitly records `neural_emotion:false`, `pitch_shift:false`, effective global settings and counts of emotions used.

Automatic rhythm retains sentence boundaries to insert pauses and can require more model calls. Disabling it permits bounded same-emotion packing, while explicit controls remain boundaries. SRT keeps original timing and existing fit limits; automatic TXT gaps are not inserted into timed cues. Explicit pauses remain available. Saved legacy segment markers retain the former behavior, and standard voices do not enter the Hmong expression path.

Completed expression SRT/TXT exports contain spoken words without control tags and retain actual cue-fit timing. Script SRT export uses that completed spoken file; before completion it plans clean cue text without changing saved source text. Raw project/script conversion keeps editable controls.

The default remains16steps FP32 onCPU; new Hmong requests select Story/Warm with intensity0.65 and automatic rhythm. Four-step CPUINT8 remains an optional draft, with FP32 fallback when unsupported. Model/reference caching and bounded inference are retained. These settings do not establish pronunciation quality, likeness, emotion realism or hardware-independent speed.

## Verification record

Completed during local integration:

- Final new-source SHA256s, both4.7s reference lengths and the user-provided words checked. Source/cloning/default replacement tests:7 passed.
- Expression/narration tests:27 passed, including real FFmpeg220Hz pitch-periodicity, PCM clipping/rate/zero-strength, actual render/resume and SRT timing checks.
- Existing worker/longform/standard regression subset:47 passed.
- Packaging/startup/default replacement subset:22 passed; curated source copy passed43 required-file checks and all four actual voice hashes.

- Final shared suite:262 passed,5 skipped. Separate pinned Hmong environment:101 passed, including all11 new resume/export regressions. Eleven Chromium contract checks passed. Both environments passed `pip check`; JavaScript syntax and Git whitespace checks passed.
- Actual Chromium uploaded the final short female and male MP3s, received the user-confirmed words, saved profiles and downloaded new audio from both at16steps FP32. Male used Warm, female Joyful, each with automatic rhythm; both completed with correct expression metadata and no JavaScript errors. This checks execution, not human emotion or native pronunciation.

`NATIVE-VALIDATION.json` and the release's `native-smoke.json` record the actual Windows release gate: relocated Windows runtime, new female/male defaults, source clones, expressive controls, TXT/SRT/MP3, nine actual BAT paths, normal startup and missing-first-run-model check. Publication requires this run to succeed; a previous1.2.0 result is not proof that1.3.0 passed. Generated preview metadata includes SHA256, source text and synthesis settings.

## Distribution

The portable package includes Python, CPU dependencies, verified FFmpeg, the two new original MP3s and reference WAVs. It excludes developer/user profiles, jobs, credentials and QA-ASR weights. First normal launch downloads about1.4GB of revision/SHA256-pinned F5/Vocos files; model weights are not redistributed because explicit redistribution terms are unclear. TLS/checksum verification remains enforced. After preparation, inference is offline without APIkeys.

Generated MP3 previews are auditions of actual tool output, not the input recordings or proof of native pronunciation/emotion realism. There is no promise of one hour of speech in two minutes or of human-equivalent emotional performance. Exact reference words and native listening remain necessary for a reliable quality assessment.
