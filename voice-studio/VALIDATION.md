## Voice Studio 2.5 — TXT/SRT và giọng hệ thống

- **38 kiểm thử đạt**, không bỏ qua, một cảnh báo Starlette/AnyIO deprecation. Kiểm thử mới: SRT BOM/CRLF, bỏ thẻ HTML, roundtrip millisecond, từ chối mốc lỗi/chồng/vượt 3 giờ, WAV có im lặng đúng mốc 1 và 3 giây, tổng 4 giây, căn ô ngắn bằng FFmpeg mà không dịch câu sau, từ chối ô quá ngắn, xuất mốc từ TXT, API nhập/xuất, giọng system không đòi marker AI và hợp đồng gọi Windows dùng JSON (không đưa nội dung người dùng vào mã PowerShell).
- Chromium + Nano 8 bước thật: nhập SRT hai câu, chọn nguồn/giọng ngay ở video, tạo WAV 16 giây theo mốc, lồng tiếng vào video 30 giây, xuất SRT đã cộng offset 1 giây. Tạo voice riêng từ SRT không cần video, thanh % đạt 100%, tải video/WAV, 390 px không tràn ngang và không lỗi JavaScript.
- Trình duyệt thật: nhập SRT ở mục Tạo giọng, xuất MP3 thật, tải SRT đúng mốc; tạo TXT dài với Nano chạy song song rồi bấm Dừng trong mục Lồng tiếng, trạng thái Đã dừng và % chưa tới 100, không lỗi JavaScript. Luồng FFmpeg xuất video dùng `-progress pipe:1`, đọc `out_time_us`; không dùng timer giả để tăng %.
- Windows SAPI / PowerShell chỉ kiểm thử hợp đồng bằng mô phỏng trên Linux; **chưa chạy giọng hệ thống trên máy Windows thật**. Danh sách Windows trống trên Linux là hành vi dự kiến. Chưa kiểm tra nghe độ rõ/phát âm từng từ, căn từ, video 3 giờ hoặc dừng lúc FFmpeg đang ghép trên Windows. SRT là căn từng ô/đoạn, không phải khớp khẩu hình. Không có phụ thuộc Python hay trọng số mới.

---

## Voice Studio 2.4 — lồng tiếng video

- **33 kiểm thử đạt** trên Linux CPU, không bỏ qua; một cảnh báo Starlette/AnyIO. Kiểm thử mới dùng FFmpeg thật để tạo video H.264 có âm thanh, tải qua API, ghép giọng với thời điểm bắt đầu và cả hai lựa chọn giữ/thay tiếng gốc. Hash luồng video trước/sau giống hệt, thời lượng giữ 4 giây; từ chối lời dài vượt video, video hỏng, ID không hợp lệ, xóa nguồn còn được tham chiếu và tải sản phẩm chưa hoàn tất.
- Chromium + mô hình thật: tải video H.264 30 giây, tạo lời Việt bằng Nano **8 bước / hai tiến trình**, bắt đầu đọc ở giây 1, trộn tiếng gốc 15%, xem và tải MP4 thành công. FFprobe xác minh có cả hình và tiếng, video vẫn dài 30 giây. Tải lại trang và chọn lại video đã lưu; màn hình 390 px không tràn ngang, không lỗi JavaScript.
- Giữ nguyên đường tạo giọng/cancel/resume hiện có; FFmpeg ghép video nằm trong cây tiến trình worker để nút Dừng có thể dừng cả ghép. Chưa thử dừng đúng lúc FFmpeg đang ghép một video dài trên Windows. Không cần thư viện Python/mô hình mới; FFprobe là yêu cầu thêm bên cạnh FFmpeg.
- Chưa đo video dài đủ 3 giờ, codec HEVC/AV1/VP9 hoặc tác vụ nhân bản video riêng. Không đánh giá nghe thủ công độ chính xác từng từ; không cam kết phát âm chuẩn 100%. Chưa có nhận dạng, dịch, SRT, căn câu hay khớp khẩu hình. Tốc độ 30× bản trước là số liệu Nano 4 bước, không áp dụng mặc nhiên cho lồng tiếng 8 bước hoặc mọi phần cứng.

---

## Voice Studio 2.3 — tốc độ đo được và giới hạn

- Linux AMD EPYC, 5 CPU logic, RAM 33,3 GB, không GPU NVIDIA. VieNeu Nano Minh Quân, **4 bước bản nháp**, hai tiến trình, hai ONNX threads mỗi tiến trình, WAV PCM 24 kHz, nhịp tự nhiên 1×, không thêm nghỉ câu. Không kéo giãn âm thanh hoặc chèn im lặng để đạt hệ số tốc độ.
- Mẫu ~40,8 giây: lượt đầu 2,215 giây xử lý (18,47×); hai lượt giữ mô hình trong RAM đạt 31,24× và 31,32×. Một lượt đọc dài **618,284 giây âm thanh / 18,867 giây xử lý = 32,77×**. Số liệu API tính từ lúc bắt đầu tác vụ đến khi xuất xong, không tính chờ hàng đợi. Đã giải mã tệp và kiểm tra tín hiệu khác 0; không thay thế đánh giá nghe.
- Kiểm tra dài hoàn chỉnh sau khi nạp sẵn mô hình: **3.711,250 giây âm thanh (1 giờ 1 phút 51 giây) / 111,224 giây xử lý = 33,37×**; 811 đoạn, tệp WAV giải mã được và có tín hiệu. Đây là bản đọc tiếng Việt lặp lại văn bản mẫu, không phải đánh giá nội dung đa dạng hoặc độ rõ từng từ. Lượt này thực sự tạo hơn 1 giờ âm thanh, không chỉ ngoại suy từ mẫu ngắn.
- **31 kiểm thử đạt**, không bỏ qua; một cảnh báo Starlette/AnyIO deprecation. Kiểm tra bổ sung xác minh ghép đúng thứ tự khi đoạn sau hoàn tất trước, dùng lại checkpoint, bảo toàn nhấn/nghỉ, phép tính tốc độ, giới hạn cấu hình và chẩn đoán máy.
- Chromium thật với server/mô hình thật: chọn cấu hình 4 bước/hai tiến trình, chạy mẫu đo và hiện kết quả, giữ nguyên văn bản người dùng, nút đọc cấu hình máy, màn hình 390 px không tràn ngang và không lỗi JavaScript.
- Dừng tác vụ Nano song song: toàn bộ bốn tiến trình con đã dừng trong 0,317 giây trên Linux; tác vụ mới sau Dừng tạo được WAV. Windows `taskkill /T /F` chưa được thực thi trên máy Windows.
- Tốc độ trên máy người dùng, GPU/CUDA, chất lượng cảm nhận của chế độ 4 bước và tốc độ nhân bản/giọng quốc tế chưa được chứng minh bằng các số liệu trên. Không cam kết 30× cho mọi máy hoặc mô hình. Lượt tiếp tục có checkpoint không hiện ước tính tốc độ để tránh coi âm thanh đã có là vừa tạo mới.

---

# Voice Studio 2.2 — tốc độ và dừng trực tiếp

- **26 kiểm thử đạt**: bổ sung tái sử dụng cấu hình/mô hình, hai tác vụ cùng tiến trình worker sống, giải phóng worker, xử lý PCM/resample không gọi FFmpeg ở nhịp 1×, fallback Tự động và giọng Nano chỉ được chọn rõ ràng. Các kiểm thử cũ về 3 giờ, checkpoint, dừng tiến trình, kết nối cloud/local vẫn đạt.
- Đo thực tế trên CPU cloud 5 vCPU, cùng nội dung 3 câu tiếng Việt, WAV, nhịp 1×: bản cũ FP32 tiến trình mới 4,915 / 4,744 giây; bản mới FP32 lạnh/nóng 4,689 / 1,760 giây; INT8 đổi mô hình/nóng 2,855 / 1,344 giây; Nano đổi mô hình/nóng 1,051 / 0,741 giây. Âm thanh dài khoảng 6 giây, giải mã được và có tín hiệu. Turbo có sampling nên độ dài khác nhẹ; Nano khác giọng/chất lượng. Không coi số đo này là bảo đảm tốc độ Windows hoặc dự án dài.
- Chromium thật: tạo tác vụ dài rồi bấm **Dừng tạo giọng** trên màn hình chính; backend báo cancelled và worker bị kết thúc trong khoảng 0,142 giây ở Linux. Kiểm tra nút ChatGPT/Gemini chọn đúng nhà cung cấp và hiện trường key; Ollama ẩn key; mobile không tràn ngang, không lỗi JavaScript.
- Chưa kiểm tra CUDA, Windows taskkill hoặc chất lượng nghe Nano; Nano chỉ giọng có sẵn tiếng Việt. API cloud vẫn mới được kiểm tra hợp đồng mô phỏng, chưa có tài khoản thật.

---

# Voice Studio 2.1 — viết cục bộ không cần khóa

- **22 kiểm thử đạt**, gồm viết bằng Ollama với toàn bộ API key unset, xác nhận không có header xác thực và mọi yêu cầu local chỉ tới loopback, xử lý Ollama chưa mở/model chưa tải, từ chối model cloud/URL ngoài, phản hồi rỗng và giới hạn token. Kiểm thử hợp đồng dùng MockTransport. Ngoài ra đã chạy Ollama 0.40.4 thật và viết qua endpoint Voice Studio khi không có khóa, dùng GGUF chính thức Qwen3 0.6B Q8_0 nhập cục bộ dưới tên studio-local-test. Archive Ollama được kiểm tra SHA256 với sha256sum chính thức; GGUF được kiểm tra SHA256 với LFS oid chính thức. Chưa đánh giá mô hình mặc định Qwen3 4B hoặc chất lượng kịch bản dài; mô hình thử nhỏ có thể lặp lời và ký hiệu được làm sạch trước khi chuyển đọc.
- Chromium: mặc định chọn Ollama, ẩn trường API key, kiểm tra kết nối không gửi khóa, viết và chuyển nội dung sang đọc, đổi qua cloud hiện trường khóa rồi quay lại local ẩn khóa; desktop/mobile không lỗi JavaScript. Ngoài kiểm thử UI mô phỏng, đã chạy trình duyệt thật với Ollama thật: tự chọn model local có sẵn, ô key ẩn, viết 306 ký tự và chuyển đúng nội dung sang trình đọc mà không nhập khóa.
- Windows BAT và việc cài Ollama trên Windows chưa được thực thi trên máy Linux này. Người dùng cần cài/mở Ollama và tải mô hình một lần; phần viết không tự chạy khi chưa có runtime/model.

---

# Voice Studio 2 — xác minh bản nâng cấp

- **18 kiểm thử đạt** trên Linux CPU, bao gồm ranh giới thời lượng PCM đúng 10.800 giây (dùng sample rate thấp cho fixture 3 giờ), giới hạn đầu ra thật qua FFmpeg ở mức 60 giây, kịch bản dài hơn 2.000 ký tự, chia tiếng Việt/Nhật/Hàn, nhấn/nghỉ, dừng/tiếp tục, cache đoạn, chống chạy hai server cùng thư mục dữ liệu, tắt tiến trình khi đóng ứng dụng, hợp đồng HTTP OpenAI Responses và Gemini generateContent, khóa chỉ giữ trong bộ nhớ, từ chối khóa sai. Có một cảnh báo deprecation Starlette/AnyIO.
- **Âm thanh AI thật**: VieNeu FP32 với nhiều đoạn, nhấn/nghỉ và xuất MP3; VieNeu INT8 trên CPU VNNI, dừng tiến trình rồi tiếp tục, xác minh mtime các đoạn đã có không đổi; Qwen 0.6B chế độ nhanh nhiều đoạn tiếng Anh. Các bản thu giải mã được và có tín hiệu khác 0. Thời lượng lần lượt khoảng 8,07 / 7,63 / 5,82 giây; không dùng các lượt khác nhịp/format này để kết luận tỷ lệ tăng tốc.
- **Chromium thật**: editor 200.000 ký tự, chọn nhà cung cấp/model, chuyển/nối/viết tiếp kết quả kịch bản, nhịp đọc và giới hạn 180 phút, desktop/mobile không tràn ngang, không có lỗi JavaScript.
- Chưa chạy AI tạo liên tục đủ 3 giờ. Kiểm thử fixture xác minh bộ ghép, chặn thời lượng và cơ chế tiếp tục, không chứng minh chất lượng giọng hay độ ổn định mô hình suốt một dự án thực tế 3 giờ.
- API viết được kiểm tra bằng MockTransport, không dùng tài khoản thật vì chưa có API key. Các yêu cầu không xác thực tới OpenAI/Gemini bị proxy cloud từ chối (CONNECT 403). Đã lưu các miền cần truy cập vào cấu hình nháp; chưa xác nhận áp dụng mạng hay thanh toán/model của người dùng. Máy Windows chạy độc lập cần mạng và API key riêng.
- Windows BAT và dừng cây tiến trình bằng taskkill, macOS, CUDA chưa được chạy trong môi trường Linux này. Chất lượng cảm nhận, âm sắc và độ giống giọng người thật vẫn cần đánh giá bằng nghe.

---

## Kết quả lịch sử bản 1


Đã chạy trên Linux x86_64, Python 3.12.14, CPU AMD EPYC (5 vCPU), không có GPU NVIDIA.

- `pytest -q tests`: **8 đạt**, một cảnh báo deprecation của Starlette/AnyIO; không có kiểm thử bị bỏ qua.
- `pip check`: không có lỗi phụ thuộc. `install.sh` đã chạy lại thành công với môi trường Python ngoài checkout.
- Chromium thật: điều hướng 4 màn hình, văn bản mẫu, thông báo mô hình thiếu, thư viện giọng, lịch sử; không có lỗi JavaScript. Bố cục máy tính 1440 px và điện thoại 390 px; không tràn ngang trên điện thoại.
- FFmpeg thật: nhập mẫu, chuyển mono 24 kHz, kiểm tra thời lượng, từ chối tệp hỏng/mẫu quá ngắn; trả lại mẫu, xóa mẫu, quản lý hàng đợi và bản thu.

## Suy luận thực tế qua API của ứng dụng

Tất cả lượt dưới đây chạy tiến trình worker với `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, dùng đường dẫn snapshot cục bộ cho Qwen. Đã kiểm tra HTTP trả âm thanh thành công, tệp giải mã được, thời lượng trên 1 giây và biên độ khác 0.

| Luồng | Mô hình | Đầu ra |
|---|---|---|
| Việt · Mai Anh | VieNeu v3 Turbo ONNX | WAV, 48 kHz, 4.72 giây |
| Việt · Nhân bản mẫu tổng hợp | VieNeu v3 Turbo ONNX | MP3 192 kbps, 48 kHz, 3.82 giây |
| Anh · Nhân bản mẫu tổng hợp | Qwen3-TTS 0.6B Base | WAV, 24 kHz, 2.95 giây |
| Anh · Aiden | Qwen3-TTS 0.6B CustomVoice | WAV, 24 kHz, 3.00 giây |
| Nhật · Ono Anna | Qwen3-TTS 0.6B CustomVoice | WAV, 24 kHz, 4.92 giây |
| Hàn · Sohee | Qwen3-TTS 0.6B CustomVoice | WAV, 24 kHz, 6.44 giây |

Mẫu nhân bản trong QA là âm thanh tổng hợp từ mô hình, không phải giọng một người dùng thật. Hồ sơ mẫu QA đã được xóa sau kiểm tra. Bản thu thử thành công được giữ trong lịch sử cục bộ; không đưa trọng số hoặc âm thanh vào gói mã nguồn.

## Giới hạn đã biết

- Chưa đánh giá nghe thủ công, độ giống một người nói thật, MOS hoặc chất lượng thương mại/phòng thu. Không hứa nhân bản chính xác 100%.
- US/UK cùng ngôn ngữ English; giọng vùng phụ thuộc mẫu/người nói. Chưa xác minh một mẫu giọng Anh Anh thực tế.
- Các ngôn ngữ còn lại lấy từ danh sách hỗ trợ chính thức của mô hình, chưa tạo âm thanh kiểm thử từng ngôn ngữ.
- Windows BAT, macOS và NVIDIA GPU chưa được chạy thử trong môi trường Linux CPU này.
- Qwen SDK in cảnh báo thiếu flash-attn (tùy chọn cho GPU) và SoX khi import. Luồng tokenizer 12 Hz được dùng ở đây vẫn vượt qua kiểm tra suy luận thật; FFmpeg được dùng để xử lý/xuất âm thanh.
- Đã sửa lỗi nạp Qwen offline bằng snapshot cục bộ; đã sửa vị trí tệp tạm VieNeu bằng lớp kế thừa cục bộ, không chỉnh sửa thư viện bên thứ ba.
- Snapshot cloud mới sau Publish chưa được xác minh. Gói mã nguồn không kèm mô hình (~5.3 GB cache); máy mới cần tải trọng số một lần.

2026-10-16: 2.6 video tools: 42 regression tests passed on Linux, including real FFmpeg logo export, API task lifecycle, queued cancellation and translation count/timestamp validation. Chromium verified pointer-based region selection, real logo export, 100% progress and mobile layout. Whisper base CPU/int8 recognized a known Vietnamese narration video offline and returned timed SRT; transcription had spelling errors, so review remains necessary. Translation contracts tested with a mocked Ollama response; full live Ollama translation requires an installed local model and was not measured here. Native Windows Portable smoke now also checks bundled Whisper recognition and logo export before publishing.

2026-10-16: 2.7 direct editor: 45 Linux regression tests passed, including structured cue validation, saved project retrieval, HTTP range video preview, frame-at-time selection and real ASS subtitle+logo encoding. Decoded pixels verify white subtitle text during its cue and absence after its end. Chromium exercised video-only ASR, editing text/timing, adding a cue, save/reload, selecting a logo region and exporting burned captions+logo to MP4, progress100 and mobile layout without JS errors. New Windows smoke covers combined burned subtitle/logo export with bundled FFmpeg.

2026-10-16: 2.8 export: 50 regression tests passed on Linux. Actual FFmpeg outputs verified at 3840×2160 for plain video, burned captions and narration mux; portrait output verified at 2160×3840. Bounds/aspect ratio, maximum4K, original-without-upscale, invalid profile rejection and edited TXT/SRT responses checked. Chromium verified MP4 export without cues, actual output dimensions, 100% progress, direct TXT/SRT downloads with current edited text/timings and auto-save, mobile layout and no JS errors. Relocated Windows smoke now verifies an actual 3840×2160 output using the bundled FFmpeg.

2026-10-16: 2.9: 61 Linux regression checks passed, including cloud translation request/response contracts (OpenAI/Gemini mocked, no live cloud credentials), incomplete-output rejection, cue timing preservation, secret delivery through child environment without key in job JSON, visible unloaded international voices, SAPI cache refresh, actual two-color region encoding, cached recognition invalidation/deletion and narration+captions+logo UHD mux. Chromium exercised empty-system-voice recovery to AI, separate subtitle/read languages, provider/key dialog, multi-region colors, fast/max controls, real export and Nano dubbing, mobile and no JS errors. Provider response fixtures exercised text translation → real Nano speech and English captions + Vietnamese speech in one MP4. Real Whisper recognition plus repeated cached job returned identical SRT: 1.76s first / 0.31s cached on the short QA video; this is not a long-video or general hardware speed claim. Existing local test model passed transport but returned unchanged text; no translation-quality claim was made for that model. New relocated Windows smoke covers combined voice/captions/multiple regions and highest-quality UHD export.

2026-10-16: 2.9.1 inline editor: 61 regression checks passed. Chromium verified subtitle target and voice selection inside the direct video editor, full-script rewrite preserving cue times, saved TXT/SRT downloads containing rewritten text, rejection of wrong paragraph counts without overwriting saved cues, mobile layout and no JavaScript errors.

2026-10-16: 3.0: 68 Linux regression checks passed. New checks reject invalid font/color/size/style, decode actual styled short-preview pixels to verify yellow top captions and red logo coverage, probe clip duration and analyze output audio frequency to verify the selected voice replaces original audio at a nonzero preview start. Chromium verified live font/color/bold/position, project style save/reload, real 10-second subtitle/logo proof, real Nano voice plus video proof, mobile and no JS errors; existing inline rewrite/TXT/SRT flow also passed. Native relocated smoke now exercises styled short proof with bundled voice. Browser style preview is approximate; the encoded proof uses the actual FFmpeg filters.

2026-10-16: 3.1 simplified video workspace: 78 Linux tests passed, one Win32-only case skipped. New tests exercise gap-aware SRT fitting without dropping words, strict-mode compatibility, timeline bounds and completed timing API, rejection of unfinished/oversized reusable audio, and actual complete-video composition with a ready WAV (audio-spectrum check). Chromium verified the default video workspace, ready Nano selection, immediate missing-video feedback, queued progress/stop recovery with fixtures, real voice creation for short cues with updated timestamps, synchronized playback and seeking, edit/stale-voice protection, real reused-voice MP4 export, mobile and no JS errors. A separate browser flow exercised real local Whisper → Nano speech → synchronized listening → MP4 from a source with no cues in one click. Native smoke adds the workspace asset and complete-video composition without repeating synthesis.

2026-10-16: 3.2: 81 Linux checks passed, one Win32-only case skipped. Catalogue tests verify 52 choices, expanded ASR/translation validation, truthful Qwen capability exclusions and nine preset speakers, and simulated Windows Thai/Hindi/French culture enumeration. The four new speaker identifiers and dialect flags were checked against the official Qwen 0.6B CustomVoice config; their model inference was not downloaded/run for this change. Chromium verified separate subtitle/voice languages, native-country filters, clone language restrictions, Windows add-voice help, missing-language clarity, speed controls and mobile without JS errors. A mocked English→Vietnamese translation response fed real Nano 4-step synthesis while saved English captions remained English and times remained valid. Previous local voice/ASR and media tests remain covered.

2026-10-16: 3.3: 90 Linux tests passed; one native-Windows lock test skipped. Six-language synthetic timeline tests verify exact original cue boundaries and silence outside speech windows; these are not multilingual model quality measurements. Real FFmpeg tests verify configurable tempo limits, actionable oversized-cue reports and full-WAV preview seeking using audio frequency. Chromium created real Vietnamese Nano and English Turbo speech from SRT, verified unchanged original cue times, per-cue reports, synchronized listening and encoded preview reusing the same voice at a nonzero video time. Native portable smoke additionally synthesizes a strict two-cue Vietnamese SRT and validates its alignment report.

2026-10-16: 3.4: 93 Linux tests passed and one Win32-only test skipped. Real FFmpeg conversion verified MP3 codec; downloaded WAV bytes, Unicode TXT and SRT timestamps verified. Model preflight fixtures cover installed Ollama fallback, explicit missing model rejection, empty library, and cloud missing-model diagnostics without live cloud credentials. Chromium downloaded all four formats after real Vietnamese/English speech synthesis and verified an absent Ollama model is rejected before ASR starts, with busy state released. Existing strict alignment/listening/preview flow passed. Portable smoke now downloads all four formats from relocated native runtime.

2026-10-16: 3.4.1: Cloud translation recovery uses provider model discovery, Gemini generation-capability filtering/pagination, default-model replacement on metadata or generation 404, and immutable source cues across failed batches. 97 Linux tests passed; one Windows-only check skipped. Chromium reproduced a cloud translation failure at 58% with fixtures, restored original cues in the actual editor, selected a discovered model, retried with SRT instead of ASR, then generated real Nano speech. Cloud catalog/generation responses were fixtures, not live provider verification. Model status does not imply translation quality. Native smoke checks recovery/model selector assets alongside existing offline synthesis/media/download checks.

2026-10-16: 3.4.2: 101 Linux tests passed; one Win32-only case skipped. Generation preflight now performs the same JSON translation call as the actual task, instead of accepting model metadata. Fixtures verify two consecutive listed-model 404s followed by success, bounded fallback, no model hopping on quota failure, runtime recovery without source mutation, and retaining provider HTTP/message while redacting keys. Chromium verifies failed generation preflight prevents video/ASR enqueue at 0% and the standalone model-test button displays provider reason; prior cue recovery/retry → real Nano flow also rerun. User reports a Google AI Studio key; no user credential was requested or used in cloud tests. Actual account/model availability remains checked on the user's machine.

2026-10-16: 3.4.3: 101 Linux tests passed, one native-only skip. Chromium verified empty Windows-source recovery despite conflicting country filter, ready Nano selection, native Japanese unloaded-voice selection, Windows voice download-disabled state using a simulated installed SAPI catalogue, unsupported-language help preserving language, both video/text controls, no automatic model requests, mobile layout and no JS errors. The real Vietnamese Nano/English Turbo strict SRT synthesis, cue report, synchronized playback and encoded voice preview flow passed again. Installed Windows voices in UI testing were fixtures, not live SAPI synthesis on Linux.

2026-10-16: 3.4.4: 108 Linux tests passed; one native-only skip. New HTTP fixtures verify 503→success, three-attempt cap, Retry-After clamped at five seconds, original Google error preservation, no retry on 401/403/429, preflight/runtime same-provider model fallback, and all-busy outage messaging without blaming the key. Chromium confirms Stop during pending preflight prevents video/ASR enqueue after response arrives and releases controls. Existing failed-translation cue recovery, retry from SRT and real Nano synthesis passed again. These checks simulate provider overload; no user API key was requested or used, and they do not establish live Gemini availability.
