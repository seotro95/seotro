# Hmong Voice Studio 0.8.1 — ULTRA FAST

Ứng dụng đọc Hmong Trắng bằng **đúng mô hình CosyVoice Hmong và hai mẫu nam/nữ hiện có**, chạy trên máy, không cần API trả phí. **Mục tiêu 60 phút voice trong 120 giây chưa được xác nhận đạt.** ULTRA FAST giữ cấu hình suy luận Chuẩn; không giảm bước sinh phổ, không tự dùng INT8, đổi giọng hoặc đọc nhanh hơn để làm đẹp số đo.

## Cài và mở app

1. Cài Python 3.12 64-bit nếu máy chưa có. Nguồn chính thức: https://www.python.org/downloads/release/python-31210/ . Python 3.10–3.12 x64 được hỗ trợ.
2. Đóng Studio/bộ cài. Giải nén vào thư mục có quyền ghi. Cập nhật bản cũ: giải nén đè **đúng thư mục hiện có**, giữ `.data` và các thư mục `.venv-clone-*` tại chỗ. Ví dụ thư mục cũ `E:\voi hmong\Hmong-Studio-Trang`: giải nén vào `E:\voi hmong\`, tránh lồng thêm một thư mục cùng tên.
3. Bấm **CHAY-STUDIO.bat**. Tự thử NVIDIA/CUDA khi phát hiện card, kiểm tra phép tính CUDA thật trước khi chọn môi trường GPU. Nếu lần cài tự động thất bại, báo rõ và dùng CPU hợp lệ; **CAI-NVIDIA.bat** cho phép thử lại chủ động. Không thay driver.
4. Trình duyệt mở sau khi máy chủ sẵn sàng. Mô hình được nạp trước ở nền; lượt tạo đầu chờ cùng worker nếu chưa nạp xong. Giữ cửa sổ lệnh mở, Ctrl+C để đóng. Các lần sau dùng lại thư viện/mô hình đã hợp lệ.

Đây là app cục bộ mở trong trình duyệt, không phải EXE độc lập chứa sẵn Python/trọng số. ZIP gồm mã nguồn hiện tại, hai mẫu, các bộ cài, kiểm thử và báo cáo. Bản sao nguồn lịch sử được giữ riêng trong repository để tránh lồng ZIP cũ trong bản phát hành mới. **Mô hình khoảng 5,4 GB không nằm trong ZIP**; chỉ tải tệp thiếu/sai ở lần cài có Internet. Sau khi cài xong có thể tạo giọng cục bộ không cần Internet. Nên có RAM 16 GB trở lên, khoảng 15 GB đĩa cho mô hình/thư viện và thêm chỗ cho WAV/cache. Cài thêm môi trường CUDA cần thêm đĩa.

## Cảnh báo khi tải và tình trạng kiểm tra 0.8.1

Chưa xác định tên mối đe dọa hoặc tệp con bị phần mềm bảo vệ chặn, nên chưa thể kết luận nguyên nhân hay xác nhận cảnh báo đã hết. Đã kiểm tra mã/gói, chuyển kiểm tra GPU sang Python chỉ đọc và buộc trình tải mô hình giữ HTTPS cả khi chuyển hướng; đây là cải thiện minh bạch mã/cách tải, không phải bằng chứng đã xử lý đúng cảnh báo.

**Chưa quét antivirus thành công:** ClamAV 1.4.3 chạy được nhưng tải cơ sở dữ liệu chính thức bị proxy chặn (403); lần thử quét báo lỗi, không quét tệp nào. Không coi “0 infected” trong log lỗi là kết quả sạch. Xem `SECURITY_SCAN_REPORT.md` và `security-scan/` để kiểm tra bằng chứng/phạm vi. Chưa kiểm chứng bằng Windows Defender trên Windows thật. Nếu cảnh báo còn xuất hiện, giữ bảo vệ bật và ghi lại tên mối đe dọa/tệp trong Windows Security → Virus & threat protection → Protection history để xác định đúng phần bị chặn.

## Tạo voice và ULTRA FAST

- Chọn **Hmong Trắng**, giọng nam/nữ hoặc mẫu riêng, nhập TXT/SRT tối đa **1.000.000 ký tự**. Không cần micro hoặc bản chép mẫu trong chế độ CosyVoice instruct2.
- Review được chọn sẵn; các cách đọc khác và biên tập WAV vẫn giữ nguyên. Thanh tốc độ điều chỉnh nhịp đọc, không phải tốc độ tính toán.
- Bấm **TẠO VOICE SIÊU NHANH** hoặc chọn **ULTRA FAST** rồi Tạo voice. Lượt chưa có cache vẫn chạy mô hình Chuẩn; audio đã tạo đúng nội dung/mẫu/cách đọc/tốc độ/lọc ồn/precision/mô hình được dùng lại theo từng đoạn.
- Mặc định **Lọc ồn Nhẹ**. Tắt/Nhẹ/Mạnh giữ nguyên chức năng; lọc Mạnh có thể mất chi tiết nhỏ. Bộ lọc không tách riêng được nhạc hoặc giọng người khác. Mẫu gốc không bị ghi đè.
- **TẠM DỪNG** chờ tới checkpoint sau phần đang xử lý; giao diện hiện yêu cầu đang chờ trước khi worker xác nhận đã dừng. Không treo GPU giữa phép tính. **TIẾP TỤC** dùng cùng worker và giữ thứ tự đoạn. **DỪNG** hủy worker/tệp tạm của lượt đó; lượt sau cần nạp lại mô hình.
- Nghe và chọn **TẢI WAV** hoặc **TẢI MP3**. WAV giữ PCM gốc; MP3 nén bằng FFmpeg khi tải lần đầu, không thay WAV. Bản dài được ghi/đọc trực tiếp từ đĩa; không nạp toàn bộ vào JavaScript. Kết quả đang tải/xuất được giữ khỏi việc thu hồi bởi các job sau. Tải xong trước khi đóng Studio.

ULTRA FAST giữ nguyên chữ Hmong RPA, chữ biểu thị thanh điệu, thứ tự câu và mô hình hiện có. Chia đoạn ưu tiên ranh giới câu; câu vượt giới hạn an toàn được chia ở ranh giới từ, không cắt ký tự/tự dịch. Độ giống mẫu, phát âm và thanh điệu của chính mô hình vẫn cần người nghe Hmong kiểm tra; việc giữ thuật toán không thay thế đánh giá ngôn ngữ.

**Nhanh CPU** cũ vẫn có nhưng dùng INT8 thử nghiệm và có thể đổi âm sắc. Nó là lựa chọn riêng; **ULTRA FAST không tự bật INT8**. Với GTX 1060 6 GB dùng ULTRA/Chuẩn + Nhẹ. Đóng Studio rồi chạy **DO-TOC-DO.bat** để đo FP32/FP16; mở lại app để dùng chế độ có RTF tốt nhất trong mẫu đo. GTX 1060 không có Tensor Cores/TF32, nên không mặc định cho rằng FP16 nhanh hơn. BF16 không được bật trên card này. Chưa có GPU thật để kiểm chứng tốc độ trong môi trường phát triển.

## Số đo trên giao diện

Hiện tổng thời lượng dự kiến, đoạn hiện tại/đã xong, phần trăm, thời gian chạy, ETA, CPU/GPU/API, worker, batch và cache hit. Dự kiến/ETA hiển thị chưa đủ dữ liệu tới khi có đoạn hoàn tất; đây là ước lượng cập nhật, không phải cam kết. SRT có thể biết thời lượng timeline từ đầu, gồm khoảng lặng.

**Tốc độ tạo voice chỉ tính giây audio mới do mô hình sinh / thời gian hoạt động**, không tính audio dùng lại, khoảng lặng thêm vào hoặc thời gian đã xác nhận tạm dừng. Phần trăm chỉ đạt 100 sau khi WAV đã hoàn chỉnh và được kiểm tra. Cache hit được báo riêng, không dùng làm bằng chứng 30× tạo lời mới. Một worker/batch 1 là giới hạn tương thích của backend hiện tại; không nhân nhiều bản mô hình trên GTX 1060 6 GB.

## Cache và quyền riêng tư

Cache ở `.data/audio-cache`, tối đa 512 MiB/512 đoạn, có checksum WAV và giới hạn LRU. Chỉ ULTRA dùng cache; Chuẩn tạo lại lời. Khóa gồm nội dung chính xác, SHA256 mẫu, chỉ dẫn/cách đọc, tốc độ, lọc ồn, revision mô hình, thiết bị, precision và bản Torch. Metadata chỉ có hash/thông tin audio, không ghi kịch bản. Đóng Studio có thể xóa riêng `.data/audio-cache` để giải phóng; không xóa mô hình/mẫu nếu muốn giữ chúng. `.data`, môi trường Python và `.env` không được đóng gói.

Chế độ cục bộ không dùng API key. Các adapter API cũ vẫn có nếu bạn chủ động cấu hình; chỉ luồng adapter mới gửi mẫu/lời tới dịch vụ đó. ULTRA cần bộ máy Hmong cục bộ và mẫu giọng. Không có bí mật thật trong gói.

## SRT / Review

```srt
1
00:00:00,200 --> 00:00:02,700
Nyob zoo.

2
00:00:03,000 --> 00:00:09,000
Hnub no peb saib qhov no ua ke.
```

Chỉ đọc lời, không đọc mốc giờ. Giữ khoảng lặng và thứ tự; mốc chồng lấn/sai được từ chối. Cơ chế căn SRT cũ có thể tăng tốc giữ cao độ tối đa 2× để vừa mốc; nếu vẫn không vừa sẽ báo lỗi, không cắt lời. Muốn giữ nhịp đọc nguyên bản thì nới mốc đủ dài hoặc dùng TXT. Lọc ồn bù độ trễ, giữ số mẫu/đuôi âm. WAV tối đa 24 giờ mỗi lượt; WAV dài cần tới khoảng 4,15 GB đĩa.

## Benchmark thật

Đóng Studio trước khi đo để tránh tranh CPU/VRAM. **BENCHMARK-ULTRA.bat** không tham số chỉ tạo danh sách 1/5/15/30/60 phút chưa chạy, không giả kết quả. Chạy rõ từng mốc:

```bat
BENCHMARK-ULTRA.bat --target-minutes 1 --include-warm
BENCHMARK-ULTRA.bat --target-minutes 5
BENCHMARK-ULTRA.bat --target-minutes 15
BENCHMARK-ULTRA.bat --target-minutes 30
BENCHMARK-ULTRA.bat --target-minutes 60
```

Có thể dùng `--text-file "kich-ban-hmong.txt"` để đo đúng kịch bản của bạn; không sửa chữ hoặc tự kéo dài audio để đạt mốc. Không có TXT thì công cụ dùng văn bản Hmong mẫu lặp trong **kịch bản**, mỗi lượt cold vẫn thật sự chạy TTS cho từng đoạn. Thời lượng danh nghĩa chỉ là ước lượng từ chữ; báo cáo ghi thời lượng lời mới thực tế, chỉ xác nhận mốc khi đủ lời mới. Không dùng SRT/khoảng lặng để làm tăng thời lượng.

`--all --max-seconds 86400` đo mọi mốc với giới hạn rất dài; CPU có thể mất nhiều giờ. Mặc định ngân sách 600 giây **mỗi chế độ**, kiểm tra ở checkpoint, nên một phép tính dài có thể vượt ngân sách trước khi dừng an toàn. Giữ rõ `budget_exceeded/incomplete/unrun`, không coi như benchmark thành công. Các lượt Chuẩn và ULTRA cold cùng seed, mô hình đã nạp; cold tắt mọi cache read kể cả đoạn trùng trong cùng lượt. `--include-warm` đo cache riêng và không xác nhận tốc độ sinh lời mới. Nạp mô hình được đo riêng. Báo cáo/WAV nằm `.data/benchmarks`.

Xem **PERFORMANCE_REPORT.md**, **TOC-DO.md**, **LOCAL-CLONING-STATUS.md** và thư mục `benchmark-results` để biết kết quả/phạm vi kiểm chứng. Mốc 120 giây chỉ được xác nhận khi thật sự sinh đủ 3.600 giây lời mới, không có cache, và toàn bộ lượt đó hoàn tất trong 120 giây.

## Nguồn và xác minh

Mô hình: https://huggingface.co/Xuajpaj2026/hmong-tts-weights , revision `5663e0df2589c2ca2403cd327a52702c3ff96e8f`. Giữ nguyên snapshot/checksum, chỉ nạp trọng số bằng `weights_only=True`, không chạy wrapper sửa checkpoint. CosyVoice/Matcha và giấy phép nằm trong snapshot đã tải. Không đổi checksum, tắt TLS hoặc cài bộ huấn luyện Windows.

Môi trường kiểm thử là Linux CPU 4 luồng, giới hạn RAM 32 GiB, không CUDA. Kiểm thử phần mềm/sóng tổng hợp là kiểm thử chức năng, **không phải audio chứng minh tốc độ**. Các WAV benchmark được ghi nhãn thật riêng. Chưa kiểm chứng Windows/GTX 1060 thật hoặc tự động đánh giá phát âm/thanh điệu bằng người bản ngữ.

Bản sao nguồn gốc 0.7.0, commit `e4c9e2a`, được giữ [riêng trong repository](https://github.com/seotro95/seotro/blob/hmong-studio-0.3-download/hmong-studio/backups/HMONG_VOICE_STUDIO_ORIGINAL_0.7.0.zip). Không chứa `.data`, trọng số tải về, mẫu cá nhân hoặc bí mật; không lồng bản sao này vào ZIP 0.8.1. `PERFORMANCE_REPORT.md` giữ kết quả đo của 0.8.0; danh sách thay đổi 0.8.1 ở `CHANGED_FILES_0.8.1.txt`. `FILE_SHA256SUMS.txt` liệt kê hash các tệp đóng gói (trừ chính danh sách này); hash kiểm tra toàn vẹn, không thay thế quét virus.
