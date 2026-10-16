# Voice Studio Windows Portable

The downloadable runtime package is built by [Build Windows Portable](https://github.com/seotro95/seotro/actions/workflows/windows-portable.yml).

The **source-code ZIP is not the portable runtime package**. Only a successful native Windows build publishes `Voice-Studio-Windows-x64.zip` under GitHub Releases.

## Published and verified Windows build

[Download Voice-Studio-Windows-x64.zip](https://github.com/seotro95/seotro/releases/download/windows-portable-19/Voice-Studio-Windows-x64.zip)

- Release: `windows-portable-19`; source application/build commit: `2874ea6`.
- File size: **1,262,063,789 bytes** (about 1.18 GiB).
- SHA256: `0ac6c82e2d0fb7563aa43df5e14c8052ef6c30a44e7154a1b8e562305ca2a9d3`.
- [Successful native Windows build](https://github.com/seotro95/seotro/actions/runs/38873288983): regression checks, relocated bundled Python, offline Nano/Turbo synthesis, Whisper subtitle recognition, logo-region processing, API/static assets, FFmpeg/FFprobe and MP4 output all completed before publication.
- Includes the Windows FFmpeg 8.1 build verified against upstream checksums. Padding now stops at the video duration; progress uses a sidecar timestamp file and a bounded wait, fixing the native Windows video export hang found during packaging.
- Personal recordings/history are not copied into the package. Model snapshot links are converted to regular files and duplicate blob storage is omitted for reliable Windows ZIP extraction.

## Use the packaged download

1. Download `Voice-Studio-Windows-x64.zip` from a successful release, rather than GitHub's automatically generated Source code ZIP.
2. Extract **all** files to a writable folder on a Windows 10/11 x64 machine.
3. Double-click **MO_VOICE_STUDIO.bat**. It opens the browser after the local server is ready.

No system Python, pip, venv creation, separate FFmpeg installation, API key or first-run model download is needed for the included Nano/Turbo Vietnamese voices, Turbo English voices and Whisper base multilingual subtitle recognition. TXT/SRT, voice cloning with Turbo, and video dubbing use the bundled runtime. Optional Qwen international voices can be downloaded with `THEM_GIONG_QUOC_TE.bat`; this requires Internet and several GB. Optional local AI script writing and subtitle translation require Ollama and a downloaded local model; neither requires an API key. Run voice-studio/setup_local_writer.bat after installing Ollama. Cloud ChatGPT/Gemini writing still requires the provider's API credentials.

Projects, reference voices, history and models live in `voice-studio/.data` inside the extracted package. They are independent of previous source installations. Keep the console open while using the app; press Ctrl+C there to stop it. Back up `.data` before deleting a portable installation.

## Build/release checks

- Windows 2022 runner, CPython 3.12.10 x64, pinned application dependencies.
- FFmpeg archive verified against its upstream SHA256 manifest; binaries, upstream notices and docs retained.
- Installed base Python copied with its site-packages and app-local MSVC runtime DLLs; no developer venv is copied.
- A fresh output folder is used; no developer projects, keys, history or recordings are copied.
- Nano and Turbo inference preparation includes a Turbo voice cloning check. Model cards are retained beside weights.
- The copied interpreter then runs a second smoke test with offline model flags: dependency imports, API/static files, Nano/Turbo synthesis, offline Whisper recognition, real logo filtering, FFmpeg/FFprobe and MP4 output. No runtime asset is published unless these checks succeed.
- Package SHA256 is published beside the ZIP. The release notes identify the exact source commit and the package includes a dependency manifest.

A workflow definition or queued build alone is not evidence that a usable Windows ZIP exists. Verify the completed release and asset before sharing a ready-to-use download link.

## Video tools in 2.6

Choose a video in Lồng tiếng video, its original language (or automatic detection), target language and voice. Generate timed SRT for editing, translate an existing SRT, or run recognition → optional local translation → selected voice → MP4. TXT/SRT import/export remains available. Recognition has a quality/speed choice. Review recognition and translation before using the result; Vietnamese transcription can contain spelling mistakes. Long translated cues may need editing to fit their timing.

Show the video frame and drag a rectangle over a fixed logo. Export only the region treatment or apply it while dubbing. FFmpeg interpolates the selected region; it cannot recover covered detail or track moving logos. Filtering re-encodes H.264 and takes longer than the normal video-copy mux. Stop and percentage progress are available for recognition, translation, voice creation and video processing.

Validation: 42 Linux regression tests passed; the same native Windows regression suite and relocated offline smoke completed successfully. Chromium exercised real recognition → SRT → Nano dubbing → MP4, pointer-based logo selection/export, mobile layout, and stopping a running recognition worker. Translation schema/timestamps were checked with mocked Ollama responses; a live translated result was not measured in the cloud environment. Missing Ollama reports setup instructions and preserves the original SRT.

## Direct video subtitle editor in 2.7

Select/upload a video, then use **Tự tạo phụ đề từ lời nói trong video**. Edit sentence text and start/end times in the built-in cue list; preview against the video, add a sentence at the current position, or delete a sentence. **Lưu phụ đề đã sửa** stores the project in `.data/editor` and restores it when that video is selected again. TXT/SRT entry is optional and collapsed under advanced settings.

**Xuất video có phụ đề đã sửa** burns captions into MP4 while retaining original audio. Seek to a frame, choose **Khoanh vùng logo tại thời điểm đang xem**, drag the fixed region, and enable its use during export to combine captions and logo treatment. Local translation and dubbing can use edited sentences directly. Recognition does not OCR text already baked into video frames; covering an old caption/logo region does not restore the obscured scene.

Validation: 45 regression checks passed on Linux and Windows. Decoded output pixels verify that burned text appears within the cue and disappears afterward. Chromium exercised video-only recognition, direct editing of words/timing, cue addition, project save/reload, synchronization with dubbing controls, selected-frame logo region, real caption+logo MP4 output, progress and mobile layout.

## Export modes in 2.8

The direct editor has **Xuất video MP4**, **Xuất video có phụ đề đã sửa**, **Xuất lời TXT đã sửa** and **Xuất phụ đề SRT đã sửa**. Plain MP4 export works without creating subtitles. Text exports save current edits first; TXT contains words and SRT includes cue times.

Choose **Gốc / HD720p / FullHD1080p / UHD4K** before exporting video, treating a logo region or dubbing. Original mode avoids upscaling and caps larger input at UHD4K. Fixed-size modes may upscale small input. Output retains the image proportions and fits within 3840×2160 for landscape or 2160×3840 for portrait; other aspect ratios use smaller dimensions inside those limits. Logo treatment precedes resizing and captions are rendered afterward. Resizing is not AI detail restoration, and 4K requires more processing time and RAM.

Validation: 50 Linux and native Windows regression checks passed. Actual files were probed at UHD resolution for plain export, captions, portrait video and narration mux. Chromium exercised no-cue MP4 export, 3840×2160 output, progress100, downloads of currently edited TXT/SRT, auto-save, mobile layout with no JavaScript errors. The relocated Windows bundle also checks a real UHD export using its packaged FFmpeg before publication.

## Voice selection, translation and export in 2.9

Unloaded international voices stay visible with their readiness status. Refresh voices rescans Windows SAPI; switch to a bundled AI voice if the system has none, or explicitly download the selected optional model in the tool. Windows OneCore voices are not assumed to be SAPI voices.

Subtitle target language and narration language are independent. Optional OpenAI/ChatGPT and Gemini translation use your own provider credentials; Ollama remains the local option without an API key. Cloud credentials are kept out of job files. Direct TXT/SRT exports remain available alongside original/720p/1080p/4K video export and fast/balanced/highest-quality encoding. Up to 20 fixed logo regions can be interpolated or covered with independently chosen colors. This cannot restore hidden image details.

The fast preset selects available Nano settings and bounded CPU parallelism. Recognition results are cached for repeat edits. Actual performance depends on hardware, model and output settings; an hour of speech in two minutes is not guaranteed.

Validation: 61 regression checks passed on Linux and native Windows. Relocated offline Windows smoke passed actual Nano/Turbo voice, Whisper recognition, narration with captions and multiple colored regions, and highest-quality UHD export. The published 1.26 GB ZIP was downloaded in full, SHA256 verified, and checked for version 2.9.0, the new modules, bundled models and absence of personal job/history/key files. OpenAI/Gemini contracts used mocked responses; live provider translation requires the user's own credentials.

## Inline video editor in 2.9.1

Subtitle language/provider and narration language/voice controls now appear directly below the video preview. TXT/SRT exports sit beside the cue editor. Full-script rewriting keeps each paragraph attached to its existing cue time; an incorrect paragraph count or concurrently changed cues is rejected before saving. Saved rewritten text is used by exports and dubbing.

Validation: 61 Linux/native Windows checks and relocated offline Windows smoke passed. Chromium verified inline controls, full-script editing with preserved timestamps, actual TXT/SRT downloads, wrong-paragraph-count protection, mobile layout and no JavaScript errors. The published ZIP was downloaded fully, SHA256 checked, and inspected for version 2.9.1 and new editor controls.

## Subtitle designer and short proofs in 3.0

The direct editor now previews font, size, text/outline/background colors, bold/italic, vertical position and margin. Styling is saved with the project and passed to caption exports and narrated video. Browser font rendering is approximate; missing fonts are substituted.

At the current video position, create a 10-second encoded proof using actual FFmpeg subtitle and selected logo filters, or generate the selected voice for those timed cues and hear it in the proof video. The proof uses 720p and fast encoding; complete exports retain the chosen output profile. Input seeking avoids decoding from the beginning of long videos. Stop/progress controls are available. Review voice timing manually; this does not perform lip synchronization or restore hidden logo detail. Translate the script before generating a proof in another language.

Validation: 68 Linux/native Windows regression checks passed. Actual decoded pixels verify styled captions and logo coverage; output duration and audio spectrum verify a short clip with the selected voice rather than original audio. Chromium exercised instant style changes, save/reload, a real 10-second logo/caption proof, Nano speech plus video proof, mobile layout, no JavaScript errors and stop UI recovery (queued response fixture). Existing inline rewrite and TXT/SRT downloads passed. Relocated offline Windows smoke includes a styled proof with bundled voice, plus normal synthesis, recognition, mux and UHD export. The complete published ZIP was downloaded, SHA256 verified, and inspected for version 3.0.0 and video-preview.js.
