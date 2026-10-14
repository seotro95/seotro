# Video Studio VN — 0.1.0

Tool riêng với giao diện web tiếng Việt chạy trên máy Windows. Phát triển từ mô tả chức năng trong tài liệu bạn cung cấp. Mã nguồn, giao diện và bộ xử lý của tool này được xây dựng riêng.

## Cài và chạy trên Windows

1. Giải nén thư mục `video-studio` vào một thư mục mới.
2. Cài **Python 3.10 trở lên, bản 64-bit** từ python.org; bật tùy chọn thêm Python vào PATH.
3. Đặt `ffmpeg.exe` và `ffprobe.exe` cạnh `khoi_dong.bat`. Có thể dùng hai tệp FFmpeg bạn đã cung cấp. `ffplay.exe` không cần thiết. Nếu FFmpeg đã có trong PATH, không cần chép lại.
4. Chạy `cai_dat.bat` để cài thư viện, rồi chạy `khoi_dong.bat`. Tool mở trình duyệt tự động. Giữ cửa sổ khởi động trong lúc sử dụng; đóng cửa sổ để dừng server.
5. Nhập video/âm thanh/SRT → chọn tệp → tạo hoặc sửa phụ đề → tạo giọng đọc nếu cần → **Xuất video**.

Tool dùng cổng 8766 trên máy. Để đổi cổng, đặt biến `VIDEO_STUDIO_PORT` trước khi chạy. Giao diện phục vụ trên loopback; đây là tool cá nhân, chưa phải dịch vụ công cộng nhiều tài khoản.

## Chức năng

| Chức năng | Sử dụng |
| --- | --- |
| Thư viện | Nhập nhiều video, audio, SRT, TXT; kéo thả; xem/nghe; tải tệp về |
| Tải video | Dán một link HTTPS mỗi dòng; YouTube, TikTok, Douyin, Bilibili; hàng đợi hai tác vụ |
| Phụ đề | Tạo SRT bằng API hoặc Whisper CPU; sửa và lưu bản mới |
| Dịch SRT | API chat dịch theo nhóm; giữ nguyên mốc thời gian; kiểm tra đủ đoạn |
| Giọng đọc | Windows Speech có sẵn; Edge TTS trực tuyến; hoặc API audio/speech |
| Xuất video | Cắt đoạn, đổi tốc độ 0.5–2×, chỉnh chiều cao, chèn SRT, tiêu đề và thay âm thanh |
| Hàng loạt | Chọn nhiều tệp để tạo phụ đề hoặc render; tải nhiều liên kết |
| Trợ lý AI | Viết kịch bản, tiêu đề, biên tập lời thoại; lưu kết quả TXT |
| Hàng đợi | Lưu lịch sử vào SQLite; dừng tác vụ; nhận diện tác vụ bị gián đoạn khi khởi động lại |

Video gốc được giữ nguyên. Phụ đề và tiêu đề hiển thị trên tệp render, chưa được áp dụng trực tiếp trong phần xem trước. Khi cắt hoặc tăng tốc, tool dịch chuyển mốc SRT theo video xuất. Âm thanh lồng tiếng thay thế âm thanh gốc, được đệm im lặng nếu ngắn và cắt nếu dài. Chưa có căn giọng đọc theo từng câu SRT, clone giọng, dựng timeline nhiều track hay hiệu ứng CapCut.

## AI miễn phí / cục bộ

Chạy `cai_ai_cuc_bo.bat`, sau đó khởi động lại tool:

- **Whisper cục bộ**: tạo phụ đề trên CPU. Model Tiny/Base/Small/Medium tải từ Hugging Face lần đầu; cần Internet và dung lượng lưu model. Sau khi model tải đầy đủ có thể nhận dạng cục bộ. Chất lượng tùy ngôn ngữ, tiếng nền và model; Base/Tiny phù hợp máy yếu.
- **Edge TTS**: có Hoài My/Nam Minh tiếng Việt; cần Internet, không cần API key. Dịch vụ có thể thay đổi hoặc từ chối kết nối.
- **Windows Speech**: dùng các giọng đã cài trên Windows; hỗ trợ tiếng Việt phụ thuộc gói giọng trên máy. Không cần cài phần AI để dùng giọng Windows.

## API AI

Mở **Cài đặt → Cài đặt AI**, nhập endpoint HTTPS, key và tên model. Các endpoint theo định dạng OpenAI: `chat/completions`, `audio/transcriptions` (trả SRT), `audio/speech`. Nhà cung cấp chỉ hỗ trợ chat sẽ không tự động hỗ trợ STT/TTS. Các model mặc định là ví dụ của OpenAI; hãy kiểm tra tài khoản và tài liệu nhà cung cấp.

Key chỉ giữ trong RAM, không lưu trong thư viện hoặc trình duyệt. Đổi endpoint sẽ xóa key cũ; nhập key cho nhà cung cấp mới. Đóng tool sẽ mất cấu hình phiên. Có thể cấu hình khi khởi động bằng `VIDEO_AI_BASE_URL` và `VIDEO_AI_KEY` trên máy của bạn. Không gửi key/cookie trong chat hoặc đưa vào Git.

STT API gửi audio tới nhà cung cấp; dịch và biên tập gửi văn bản; TTS API gửi lời thoại. Render và sửa SRT không cần API. STT API giới hạn audio đã chuyển đổi dưới 24 MB; dùng Whisper cục bộ hoặc cắt đoạn cho video dài. API có thể tính phí theo tài khoản.

## Cookie và tải video

Nguồn có thể yêu cầu cookie hoặc giới hạn theo khu vực/tài khoản. Dùng tệp cookie định dạng Netscape của tài khoản của bạn, đặt biến `YTDLP_COOKIES_FILE` trỏ tới tệp trước khi khởi động. Tool không kèm tài khoản, cookie hoặc API của phần mềm mẫu. Không cần cookie để nhập/xử lý video có sẵn.

## Tệp và giới hạn

- Media tối đa 2 GB mỗi tệp; SRT/TXT tối đa 2 MB. SRT là UTF-8.
- Dữ liệu dự án nằm trong `data/` cạnh mã nguồn, hoặc đường dẫn `VIDEO_STUDIO_DATA` nếu được cấu hình. Sao lưu thư mục này để giữ thư viện và lịch sử.
- Đóng tool có thể làm tác vụ đang chạy bị gián đoạn; tạo tác vụ mới khi mở lại. Dừng FFmpeg/yt-dlp kết thúc tiến trình con. Tác vụ API và tải model chỉ nhận yêu cầu dừng sau khi thao tác hiện tại kết thúc hoặc hết timeout.
- FFmpeg cần hỗ trợ `libx264`, `aac`, `subtitles`, `drawtext`; font hệ thống cần có ký tự của ngôn ngữ phụ đề. Trên Windows, cài font tiếng Việt nếu thấy ô vuông.
- Tool tạo MP4 H.264/AAC. Nếu nguồn không có audio và không chọn lồng tiếng, kết quả không có audio.

## Phát triển trên Linux

```bash
cd video-studio
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
# FFmpeg/FFprobe cần có trong PATH.
.venv/bin/python launcher.py --no-browser
```

Chạy kiểm thử bằng `python -m unittest discover -s tests -v` sau khi cài thư viện. Dùng `VIDEO_STUDIO_DATA` riêng khi chạy kiểm thử/instance phát triển. Không chạy hai instance dùng chung database.

## Mức độ xác minh

Kiểm thử phát triển xác minh bằng video mẫu cục bộ: upload, lưu SRT, render kèm phụ đề/tiêu đề, cắt/tốc độ, ghép audio, hàng loạt, dừng tiến trình và lưu lịch sử. Các adapter API được kiểm tra bằng máy chủ giả lập; kết quả đó không xác minh tài khoản AI thực. Việc tải từ nguồn thật, model Whisper, dịch vụ Edge TTS và Windows Speech cần kết nối/cấu hình tương ứng để kiểm tra trên máy của bạn. Các file BAT được cung cấp cho Windows; môi trường phát triển hiện tại là Linux.
