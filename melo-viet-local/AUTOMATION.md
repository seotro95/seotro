# Local API — 1.3.0

Keep `MO_TOOL.bat` open. Base URL: `http://localhost:8817`. Only local Host and same-origin browser requests are accepted. This is a local service, not an authenticated network server.

`GET /api/config` returns offline languages, styles, limits and available installation modes. `POST /api/start` queues a single job. `POST /api/batch` accepts `{"jobs":[...]}` (1–32 entries). Validation is atomic. There are at most 64 queued/running jobs and 16 million queued characters, with one million characters per source.

Offline voice discovery:

```json
{"op":"voices","engine":"local","language":"VI","threads":4}
```

Online voice discovery (requires Internet, not available in `MO_OFFLINE.bat`):

```json
{"op":"catalog","engine":"edge"}
```

Read the resulting `voices`, including real `id` and `locale`. Do not invent voice IDs. Online text is sent to Microsoft through the third-party `edge-tts` integration, not the official Azure API.

Render using a voice ID returned by discovery:

```json
{"op":"render","engine":"local","language":"VI","voice":"REPLACE_WITH_REAL_ID","threads":4,"name":"Script.txt","text":"Xin chào.","format":"auto","speed":1.0,"style":"narration","chunk_size":480,"use_cache":true}
```

For online rendering use `engine="edge"`, its exact locale such as `vi-VN`, and a real online voice ID. Styles are pacing presets (boundary pauses and suggested speed), not model emotion/style tokens. Rendering rate adjustment uses pitch-preserving audio processing; the native synthesis rate remains unchanged.

`GET /api/job?id=ID` returns one job; `GET /api/jobs?limit=100&offset=0` returns persisted history. States: `queued`, `running`, `done`, `error`, `cancelled`, `interrupted`. Progress includes completed chunks, cache hits, estimated remaining seconds and preview URL. Poll about once per second.

`POST /api/settings` with `{"parallelism":2}` changes concurrent output jobs (1–4). Each job has its own CPU thread budget. More workers consume more RAM and can slow individual jobs. `POST /api/cancel` with `{"id":"ID"}` stops a specific job; `{"all":true}` stops queued and running jobs. `POST /api/resume` with `{"id":"ID"}` queues a new job from the stored source and reuses valid cached chunks.

`POST /api/inspect` accepts `text`, `name`, `format` (`auto`, `txt`, `srt`), `chunk_size`, and optional `include_text`. It returns detected format, spoken character count, planned chunks, SRT cues and warnings. SRT numbers, timestamps and formatting are not narrated. Output subtitles use actual synthesized chunk boundaries, not forced input deadlines and not word alignment. The input SRT is retained separately.

Completed jobs expose `audio_url`, `downloads` for individual WAV parts, `text_url`, `srt_url`, `report_url` and `bundle_url`. WAV parts are about one hour each, to avoid RIFF size limits. ZIP64 downloads stream directly without a second full audio copy on disk. WAV downloads support byte ranges.

`processing_seconds` includes synthesis/loading and WAV assembly but excludes queue wait and download time. `realtime_multiplier` is output WAV duration (including pauses, after the requested speaking-rate adjustment) divided by processing time. Always inspect `cache_hits`, `fresh_inference`, and `speed` when comparing performance; cached reassembly is not fresh model inference. `target_30x_verified` remains false.

## Local fast CPU selection

`GET /api/config` returns 36 local language groups (including experimental Hmong RPA), `fast_languages`, `original_languages`, available CPU quota and a recommended parallel chunk count. For voice discovery add `"local_provider":"fast"` to the local request. The returned IDs are `piper:MODEL_ID:SPEAKER_ID`; use those exact IDs for rendering. Original Melo/VieNeu IDs remain valid and never silently change to another model. `local_provider="original"` prefers the seven original local readers; the twenty new languages use Piper.

Rendering can include `"chunk_workers":4` (1–4). Only Piper uses concurrent chunks of a single output. Effective concurrency is bounded by the detected CPU quota, per-chunk thread budget and configured concurrent output jobs. Results retain source order. Output reports contain `parallel_chunks`, `threads` and the real engine. Synthesis remains FP32 at native speaking rate; requested tempo is applied separately. WAV assembly preserves native sample rate when possible.

Online catalogue refresh accepts `"refresh":true` with `op="catalog"`. Errors keep the selected voice and include a visible service/network classification; no language/voice substitution occurs.

## Additional native presets, progress, MP3

Use `local_provider="multi"` for Supertonic 3's 10 real presets in 31 languages. It uses optional CPU INT8, five inference steps; it does not replace original FP32 readers. For unsupported languages the existing reader is used. Rendering is routed by the exact returned voice ID, preserving existing jobs. Hmong uses `language="HMN"` and its returned native voice ID, independently of the provider selector. It is experimental: one speaker, unverified gender/White Hmong dialect, direct on-demand download from the pinned community source. No English/Vietnamese substitute.

Rendering and inspection accept boolean `expressive` (punctuation-aware pacing) and `emphasis` (recognize balanced `**words**` marks). Explicit emphasis applies modest pitch-preserving slowing and bounded gain. Exported spoken TXT/SRT omits the marks. Defaults are false, preserving previous behavior. `friendly` is a pacing preset, not an emotion model.

`progress` is a fraction of completed source characters, capped below 1 until assembly succeeds. `stage` is queued/preparing/synthesizing/assembling/done; model preparation may stay at zero.

Once WAV rendering is done, `POST /api/mp3` with `{"id":"ID"}` queues MP3 export (192 kbps, 44.1 kHz mono). Repeating is idempotent while active or completed. `POST /api/cancel-mp3` stops that export only. Poll `/api/job?id=ID`, including for old recordings beyond the first history page. Fields: `mp3_status`, `mp3_progress` (0–1), `mp3_url`, `mp3_encoding_seconds`, `mp3_error`. A single exporter and bounded queue limit CPU/disk pressure; WAVs remain intact. The recording ZIP includes MP3/report after export finishes. Export time is separate from synthesis measurements.
