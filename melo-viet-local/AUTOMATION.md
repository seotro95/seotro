# Local API — 1.1.0

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
