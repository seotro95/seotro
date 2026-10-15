# Voice Studio Windows Portable

The downloadable runtime package is built by [Build Windows Portable](https://github.com/seotro95/seotro/actions/workflows/windows-portable.yml).

The **source-code ZIP is not the portable runtime package**. Only a successful native Windows build publishes `Voice-Studio-Windows-x64.zip` under GitHub Releases.

## Published and verified Windows build

[Download Voice-Studio-Windows-x64.zip](https://github.com/seotro95/seotro/releases/download/windows-portable-9/Voice-Studio-Windows-x64.zip)

- Release: `windows-portable-9`; source application/build commit: `6a96ca6`.
- File size: **1,076,004,328 bytes** (about 1.00 GiB).
- SHA256: `5c646cc9d94ec9cd9a9e3573deb00a61664d810c1cb0ff91044ad16cea87537e`.
- [Successful native Windows build](https://github.com/seotro95/seotro/actions/runs/38777016365): regression checks, relocated bundled Python, offline Nano/Turbo synthesis, API/static assets, FFmpeg/FFprobe and MP4 output all completed before publication.
- Includes the Windows FFmpeg 8.1 build verified against upstream checksums. Padding now stops at the video duration; progress uses a sidecar timestamp file and a bounded wait, fixing the native Windows video export hang found during packaging.
- Personal recordings/history are not copied into the package. Model snapshot links are converted to regular files and duplicate blob storage is omitted for reliable Windows ZIP extraction.

## Use the packaged download

1. Download `Voice-Studio-Windows-x64.zip` from a successful release, rather than GitHub's automatically generated Source code ZIP.
2. Extract **all** files to a writable folder on a Windows 10/11 x64 machine.
3. Double-click **MO_VOICE_STUDIO.bat**. It opens the browser after the local server is ready.

No system Python, pip, venv creation, separate FFmpeg installation, API key or first-run model download is needed for the included Nano/Turbo Vietnamese voices and Turbo English voices. TXT/SRT, voice cloning with Turbo, and video dubbing use the bundled runtime. Optional Qwen international voices can be downloaded with `THEM_GIONG_QUOC_TE.bat`; this requires Internet and several GB. Optional local AI script writing still requires Ollama and an Ollama model. Cloud ChatGPT/Gemini writing still requires the provider's API credentials.

Projects, reference voices, history and models live in `voice-studio/.data` inside the extracted package. They are independent of previous source installations. Keep the console open while using the app; press Ctrl+C there to stop it. Back up `.data` before deleting a portable installation.

## Build/release checks

- Windows 2022 runner, CPython 3.12.10 x64, pinned application dependencies.
- FFmpeg archive verified against its upstream SHA256 manifest; binaries, upstream notices and docs retained.
- Installed base Python copied with its site-packages and app-local MSVC runtime DLLs; no developer venv is copied.
- A fresh output folder is used; no developer projects, keys, history or recordings are copied.
- Nano and Turbo inference preparation includes a Turbo voice cloning check. Model cards are retained beside weights.
- The copied interpreter then runs a second smoke test with offline model flags: dependency imports, API/static files, Nano/Turbo synthesis, FFmpeg/FFprobe and MP4 output. No runtime asset is published unless these checks succeed.
- Package SHA256 is published beside the ZIP. The release notes identify the exact source commit and the package includes a dependency manifest.

A workflow definition or queued build alone is not evidence that a usable Windows ZIP exists. Verify the completed release and asset before sharing a ready-to-use download link.
