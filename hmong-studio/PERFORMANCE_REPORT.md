# Báo cáo tối ưu Hmong Voice Studio 0.8.0

## Kết luận và phạm vi

**Chưa xác nhận tạo đủ 60 phút lời mới trong 120 giây.** Không dùng cache hit, lặp audio, khoảng lặng SRT hoặc thanh tốc độ đọc để chứng minh 30×. Các kiểm thử bằng sóng tổng hợp chỉ kiểm tra chức năng; chúng không nằm trong kết quả benchmark tốc độ.

Nguồn đầu vào là repository `seotro95/seotro`, component `hmong-studio`, commit gốc `e4c9e2a` (0.7.0) đã tồn tại trong phiên; không có tệp dự án mới hơn được đính kèm ở yêu cầu này. Đã sao lưu trước khi sửa tại `backups/HMONG_VOICE_STUDIO_ORIGINAL_0.7.0.zip`, SHA256 `9c903c8763628d4c9658f83e955bb80ba9848d349c3cbb4a7a5abd1492a1adec`. Dữ liệu/mô hình riêng `.data` được giữ nguyên, không xuất vào ZIP.

## Công nghệ và phần cứng

- Python 3.10–3.12, FastAPI/Uvicorn, giao diện HTML/CSS/JavaScript, PyTorch 2.6, Transformers, ONNX Runtime và FFmpeg.
- CosyVoice3 Hmong instruct2, nguồn `Xuajpaj2026/hmong-tts-weights`, revision `5663e0df2589c2ca2403cd327a52702c3ff96e8f`. Không đổi model/checkpoint/giọng, không tải dịch vụ thay thế. Hai mẫu gốc nam/nữ giữ nguyên.
- Người dùng: Windows, Xeon E5-2680 v4, 56 logical CPUs, khoảng 128 GB RAM; NVIDIA GTX 1060 6 GB, driver 560.94 theo ảnh đã cung cấp.
- Môi trường kiểm thử: Linux, CPU quota 4 lõi, Torch 4 luồng, giới hạn RAM 32 GiB, **không có CUDA**. Không coi kết quả này là tốc độ trên máy Windows của người dùng.

## Điểm nghẽn và thay đổi

Phần sinh phổ có 22 lớp DiT và 10 bước; token giọng được giải mã tuần tự. Phép đo 0.5.1 trước đây cho thấy khoảng 25,5 giây trong tổng khoảng 31,4 giây nằm ở sinh phổ cho mẫu ngắn. Giữ model/chất lượng nghĩa là không thể bỏ phần tính toán này chỉ bằng tăng worker. Backend flow yêu cầu batch 1; CFG nội bộ có batch cố định 2, không phải khả năng gộp hai yêu cầu độc lập. Nhân nhiều model trên GTX 1060 6 GB có thể hết VRAM.

| Kỹ thuật yêu cầu | Cách xử lý tương thích |
| --- | --- |
| Parallel TTS | Một worker mô hình có khóa; MP3/HTTP/I/O bất đồng bộ riêng. Không tạo nhiều bản model trên GPU 6 GB. |
| Dynamic batching | Batch yêu cầu giữ 1 theo giới hạn backend; không giả lập batch hoặc tuyên bố đã tối ưu batch >1. |
| Async task queue | Job chạy nền, IPC JSONL, khóa tuần tự, tiến độ không chặn HTTP. Một job sinh giọng hoạt động; job khác nhận 409 để tránh quá tải. |
| Model preloading | Launcher bật nạp nền, chung worker với job; các lượt hoàn tất dùng lại model/mẫu trong RAM. |
| GPU acceleration | Tự thử CUDA, xác minh phép tính thật trước khi kích hoạt; bảng chữ Qwen trên GPU nhỏ chuyển về RAM như 0.7.0. |
| FP16/BF16 | Giữ lựa chọn FP32/FP16 đã đo tại máy; không bật BF16 trên GTX 1060. ULTRA không tự bật INT8. |
| Text chunking | Giữ cách chia câu/từ an toàn hiện có, tối đa 220 ký tự, không dịch/sửa chữ Hmong RPA hoặc đảo đoạn. Câu quá dài chia tại từ để vừa tài nguyên. |
| Adaptive scheduling | Tôn trọng giới hạn một model/batch 1; không nhận là đã tìm được tối ưu toàn cục từ phép đo GPU chưa chạy. |
| Audio caching | Cache PCM theo khóa đầy đủ, SHA256, LRU 512 MiB/512 đoạn; chỉ ULTRA sử dụng. Đo hit/tái dùng tách khỏi lời mới. |
| Fast audio merging | PCM nối trực tiếp theo block vào WAV, không giải mã/mã hóa lại mỗi đoạn; SRT/atempo/lọc và MP3 dùng FFmpeg. Không đổi sang nhiều subprocess nối khi PCM đã cùng định dạng. |

ULTRA cold chạy cùng estimator như Chuẩn, không lượng tử hóa, không giảm bước hoặc tự tăng tốc đọc. Cache hit dùng lại một kết quả TTS thật trước đó cho đúng đoạn/cấu hình, không phải tạo lời mới nhanh hơn. Đổi nội dung, mẫu, style, tốc độ, cleanup, precision hoặc model sẽ thay khóa. Cache hỏng bị bỏ/tạo lại; việc không ghi được cache không làm mất bản voice. Metadata không lưu kịch bản.

## Điều khiển và tính đúng

Tạm dừng theo checkpoint, có revision/ACK riêng; không dùng SIGSTOP hoặc treo kernel CUDA. Chưa ACK thì chỉ báo đang yêu cầu. Tiếp tục giữ cùng worker và thứ tự. Thời gian active trừ phần đã xác nhận pause; tốc độ chỉ lấy synthesized_seconds, không dùng reused_seconds hoặc timeline SRT. ETA là ước lượng sau đoạn đầu, trước đó hiển thị chưa đủ dữ liệu. 100% chỉ sau WAV hợp lệ.

WAV giữ PCM gốc; MP3 là định dạng nén mất dữ liệu tùy chọn, FFmpeg chạy một lần khi yêu cầu, được ffprobe kiểm tra codec/thời lượng và atomic publish. Dừng xuất/đóng app kết thúc đúng tiến trình con. Kết quả đang tải/xuất được ghim khỏi thu hồi; các kết quả còn lại giới hạn 10. Server có giới hạn graceful shutdown 10 giây để yêu cầu MP3 dài không trì hoãn việc hủy vô hạn.

SRT giữ vị trí/gap và cơ chế căn giọng cũ. Cơ chế atempo tối đa 2× có thể đổi nhịp để vừa mốc; nếu không muốn thay nhịp phải nới mốc hoặc dùng TXT. Lọc ồn giữ frame/đuôi âm. Không tự khẳng định tiếng Hmong chuẩn, không mất/lặp chữ hoặc thanh điệu chỉ từ kiểm tra file: cần người bản ngữ nghe kết quả của mô hình. Những thay đổi này bảo toàn nội dung đầu vào và thuật toán sinh chuẩn, không phải một model sửa phát âm.

## Benchmark 1 / 5 / 15 / 30 / 60 phút

Công cụ `benchmark_ultra.py` có inventory không suy luận và các lệnh chạy thật từng mốc/tất cả. Mỗi mốc so Chuẩn với ULTRA cold (tắt đọc cache kể cả đoạn trùng trong lượt), tùy chọn warm riêng. Cùng seed 1986, mẫu nữ, Review, lọc Nhẹ, tốc độ đọc 1×. Mô hình nạp trước được ghi thời gian riêng; lượt Chuẩn đầu gồm chuẩn bị đặc trưng mẫu, lượt sau dùng lại đặc trưng đã có. Đây không phải hai lượt có cache đặc trưng lạnh giống nhau.

Ngân sách là mỗi chế độ, kiểm tra ở callback; có thể vượt khi đang ở phép tính dài. Khi hết ngân sách, báo budget_exceeded, không xuất kết quả như voice đã hoàn tất. Chỉ xác nhận mốc nếu cả hai lượt cold hoàn tất, cache hit 0, không tái dùng và số giây lời mới thực tế đủ mốc. Chỉ mốc 60 phút thật hoàn tất trong 120 giây mới xác nhận mục tiêu; mẫu ngắn không đủ.

Kết quả thực tế và trạng thái cập nhật tại phần cuối báo cáo và `benchmark-results`. Các mốc chưa chạy được ghi unrun; kết quả chức năng/tổng hợp không được lấy làm tốc độ thực.

## Tệp thay đổi

- `cosy_engine.py`, `audio_cache.py`: ULTRA và PCM cache, các bộ đếm lời mới/tái dùng.
- `voice_jobs.py`, `voice_worker.py`: preload, pause/resume/ACK, tiến độ, ETA, khóa worker, bảo vệ kết quả.
- `app.py`, `audio_export.py`, `review_script.py`: API ULTRA/điều khiển/MP3-WAV, ghim download và cộng metric SRT.
- `static/index.html`, `static/app.js`, `static/style.css`: giữ giao diện, thêm ULTRA/điều khiển/metrics/MP3.
- `CHAY-STUDIO.bat`, `open_studio.py`, `clone_runtime.py`: preload và dừng server có giới hạn; bộ phụ thuộc và model không đổi.
- `benchmark_ultra.py`, `BENCHMARK-ULTRA.bat`: benchmark thật theo mốc, báo cáo cold/warm/incomplete/unrun.
- `README.md`, `BAT-DAU.txt`, `PERFORMANCE_REPORT.md`, `TOC-DO.md`, `LOCAL-CLONING-STATUS.md`, `benchmark-results`, `backups`: hướng dẫn, dữ liệu đo và nguồn gốc.
- Các test mới/cập nhật trong `tests`: cache, pause, MP3 thật, API/Range, benchmark, Chromium, hủy tải và shutdown.

Không thêm thư viện Python: FFmpeg/ffprobe đã có trong bộ cài, Python standard library đủ cho các phần mới. Không có API key/token/mật khẩu thật, `.env`, `.data`, môi trường Python hoặc trọng số trong gói xuất.


## Kết quả thực tế của phiên này

Kiểm thử: **329 Python đạt, 1 native CUDA bỏ qua** do không có GPU; **3 nhóm Chromium ULTRA mới và 9 nhóm hồi quy hiện có đạt**. Có kiểm thử MP3 thật bằng FFmpeg, tải Range/HEAD, hủy encoder, ghim tải, pause/resume/ACK, preload, cache key/checksum/LRU và WAV/SRT. Một cảnh báo deprecation Starlette/httpx hiện có, không làm kiểm thử thất bại. Kiểm thử tổng hợp không dùng làm tốc độ TTS.

Phép thử kịch bản ước lượng 1 phút thực sự chạy model CPU, tốc độ đọc 1×, không đọc cache. Ngân sách 300 giây mỗi chế độ, kiểm tra ở checkpoint:

| Chế độ | Wall time tới checkpoint | Lời mới đã sinh | Cache hit | Trạng thái |
| --- | ---: | ---: | ---: | --- |
| Chuẩn | 309,038 giây | 33,200 giây | 0 | budget_exceeded, chưa hoàn tất |
| ULTRA cold | 419,201 giây | 53,160 giây | 0 | budget_exceeded, chưa hoàn tất |
| ULTRA warm của kịch bản này | — | — | — | unrun vì cold chưa hoàn tất |

Không có WAV hoàn tất cho hai lượt bị dừng; không cung cấp phần đó như một bản đọc hoàn chỉnh. Không so tỷ lệ tăng tốc từ hai số này vì khối lượng đã xử lý khác nhau và cả hai đều chưa xong. Ngân sách vượt 300 giây do chờ phép tính hiện tại kết thúc, đúng cơ chế cooperative đã công bố. Lượt Chuẩn đầu có chuẩn bị mẫu, lượt sau dùng lại đặc trưng. Môi trường CPU dùng chung trong phiên kiểm thử, có kiểm thử nhẹ chạy xen kẽ; đây không phải phép đo GPU hoặc so sánh hiệu năng được cô lập hoàn toàn.

| Mốc yêu cầu | Tình trạng |
| --- | --- |
| 1 phút | Đã thử, incomplete; chưa có cặp hoàn tất đủ 60 giây lời mới |
| 5 phút | Chưa chạy — unrun |
| 15 phút | Chưa chạy — unrun |
| 30 phút | Chưa chạy — unrun |
| 60 phút | Chưa chạy — unrun; **không xác nhận 120 giây/30×** |

Các mốc dài chưa chạy do chi phí mô hình trên CPU và không có GPU tương ứng để đo. Chạy `BENCHMARK-ULTRA.bat` với mốc/giới hạn rõ ràng trên máy người dùng để có dữ liệu phần cứng thực. Bản raw: `benchmark-results/one-minute-attempt.json`; tổng hợp trạng thái: `benchmark-results/duration-targets.json`. Nội dung mẫu là văn bản Hmong literal lặp trong kịch bản benchmark, TTS cold vẫn chạy thật mỗi đoạn; không có vòng lặp audio hoặc chèn khoảng lặng để đủ mốc.


## Mẫu ngắn hoàn tất để kiểm tra PCM/cache

Lời thực tế: “Nyob zoo, kuv hais lus Hmoob.”, cùng seed, giọng nữ Review + lọc Nhẹ, 1×. Đây là mẫu **1,960 giây lời mới + 0,150 giây khoảng lặng tool thêm**, không phải benchmark 1 phút. Nạp mô hình được đo riêng trong JSON. Không có mô hình/worker khác cạnh tranh trong lúc đo mẫu ngắn này.

| Lượt | Thời gian | Lời mới | Audio dùng lại | Cache hit |
| --- | ---: | ---: | ---: | ---: |
| Chuẩn | 37,131 giây | 1,960 giây | 0 | 0 |
| ULTRA cold | 37,396 giây | 1,960 giây | 0 | 0 |
| ULTRA warm | 0,136 giây | 0 | 1,960 giây | 1 |

ULTRA cold không nhanh hơn Chuẩn trong mẫu này. Warm giảm công việc tạo lại, **không phải tạo lời mới với tốc độ 30×**. Không ngoại suy một mẫu ngắn thành một giờ. Chuẩn đầu chuẩn bị mẫu, lượt cold sau dùng lại đặc trưng như báo cáo; không coi đây là hai lượt có reference cache lạnh giống nhau.

Ba WAV hoàn chỉnh giống từng byte với nhau và với WAV Chuẩn 0.6/0.7 trước đó; SHA256 `49f40eacdae0bfcc86c372672cfccc6716fad571a3fe76eaf51954fa8f256a17`. Hai MP3 mẫu gốc cũng khớp byte với commit `e4c9e2a`. Đây là bằng chứng giữ kết quả của câu đã thử, không bảo đảm phát âm/thanh điệu cho mọi kịch bản. Nghe ở `benchmark-results/short-sample`; raw JSON `short-sample-report.json` giữ đường dẫn máy chạy ban đầu, bản WAV trong ZIP nằm ở đường dẫn tương đối nêu trên.
