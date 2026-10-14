# Video Studio VN 0.2.1 — không cần API key

Ứng dụng web tiếng Việt chạy trên máy Windows. Dịch phụ đề, nhận dạng lời nói và tạo giọng đọc bằng model CPU trên máy của bạn. Không cần tài khoản, API key hay dịch vụ AI bên ngoài để xử lý nội dung.

## Cài đặt và chạy

1. Giải nén bản ZIP **0.2.1** vào một thư mục mới. Nếu bản cũ bị lỗi cài với Python 3.15, tải ZIP 0.2.1 và chạy bộ khởi động mới.
2. Cài Python 3.11 hoặc 3.12 bản Windows 64-bit trên Windows 10/11. Các engine yêu cầu máy 64-bit và CPU tương thích. Nên có ít nhất 8 GB RAM khi dùng model nhẹ.
3. Đặt `ffmpeg.exe` và `ffprobe.exe` cạnh `khoi_dong.bat` hoặc thêm FFmpeg vào PATH. Có thể dùng các file FFmpeg bạn đã cung cấp; không cần `ffplay.exe`.
4. Chạy `khoi_dong.bat`. Tool tự chọn Python 3.11/3.12 Windows x64, kiểm tra hoặc tạo môi trường riêng, rồi cài các engine còn thiếu. Khi môi trường cũ dùng Python 3.15/32-bit, nó được đổi tên thành `.venv-backup-...` trước khi tạo lại; thư viện và model trong `data/` được giữ nguyên. Cửa sổ sẽ báo tiến trình cài thư viện, sau đó mở trình duyệt. Giữ cửa sổ này trong lúc sử dụng.
5. Nhập video/audio/SRT → tạo hoặc dịch phụ đề → tạo giọng đọc → **Xuất video**.

Lần đầu cài thư viện và tải model cần Internet, vài phút và vài trăm MB đến vài GB tùy model. Các lần sau model được dùng lại. Cắt/render video, sửa SRT, dịch, tạo voice và nhận dạng có thể chạy offline khi các model cần dùng đã tải đủ. Tải video Internet và kiểm tra bản cập nhật vẫn cần mạng.

## Tự tải model

- **Phụ đề → Tạo phụ đề**: chọn ngôn ngữ và Whisper Tiny/Base/Small/Medium. Tool tự tải model nhận dạng còn thiếu. Tiny nhẹ và nhanh; các model lớn hơn thường chính xác hơn nhưng cần nhiều RAM/thời gian. Giữ tiếng gốc khi nhận dạng.
- **Phụ đề → Dịch phụ đề**: chọn SRT, ngôn ngữ nguồn hoặc tự nhận dạng, rồi ngôn ngữ đích. Tool tự tải model dịch cần dùng. Một số cặp dịch qua tiếng Anh. Mốc thời gian và số đoạn được giữ nguyên; kết quả là SRT mới.
- **Giọng đọc**: chọn giọng Việt VAIS hoặc Anh Lessac, nhập nội dung và tốc độ. Piper tự tải model một lần, sau đó tạo WAV trên CPU. Bản này có một giọng Việt và một giọng Anh; không có clone giọng hoặc voice CapCut/NgocHuyen.
- **Cài đặt → Model & cập nhật → Chuẩn bị model**: tải trước giọng Việt, Whisper Tiny và dịch Anh → Việt. Các cặp ngôn ngữ khác được bổ sung khi bạn dịch lần đầu.

Tool dùng model dịch Argos/OPUS-MT với CTranslate2 và SentencePiece, Piper cho TTS, faster-whisper cho STT. Các model được lưu trong `data/models/`. Không gửi video, âm thanh hoặc văn bản tới một nhà cung cấp AI khi thực hiện những chức năng này.

Dịch máy và nhận dạng có thể sai thuật ngữ, tên riêng hoặc lời nói khó nghe. Kiểm tra và chỉnh SRT trong trình biên tập trước khi render. Nếu nhận dạng sai ngôn ngữ nguồn, hãy chọn ngôn ngữ đó thay vì Tự nhận dạng.

## Tự cập nhật tool và engine

Từ bản 0.2.0, tool mặc định kiểm tra phiên bản mới trên nhánh GitHub `seotro95/seotro`, `video-studio-vn`, tối đa một lần mỗi ngày khi mở. Khi có bản phát hành mới:

1. Tải ZIP qua HTTPS và kiểm tra SHA256 theo manifest phát hành.
2. Kiểm tra nội dung gói, sao lưu mã nguồn hiện tại vào `data/update-backups/`, rồi thay các tệp chương trình.
3. Giữ nguyên video, thư viện SQLite, model đã tải, FFmpeg và `.venv`.
4. Tự cài các phiên bản thư viện được yêu cầu cho bản mới rồi mở ứng dụng.

Nếu cập nhật mã nguồn thất bại, tool phục hồi các tệp đã thay và tiếp tục dùng bản cũ. Nếu cài thư viện thất bại, cửa sổ sẽ báo lỗi; kiểm tra mạng rồi mở lại. Không cập nhật thư viện trong lúc có tác vụ đang chạy.

Bạn có thể bật/tắt cập nhật trong **Model & cập nhật**, kiểm tra bản mới hoặc hẹn áp dụng khi mở lại. `cap_nhat.bat` kiểm tra cập nhật ngay; đóng tool đang chạy trước. Chức năng mới được nhận khi người duy trì phát hành bản mới; tool không tự tạo ra chức năng chưa được phát triển.

Model còn thiếu được tải tự động; model đã cài được dùng lại để bảo đảm chạy offline. Danh mục model dịch được làm mới khi cần tải cặp mới, tối đa sau mỗi 7 ngày. Giọng Piper dùng phiên bản model đã xác minh đi kèm bản tool; model giọng mới có thể được bổ sung qua các bản phát hành tiếp theo.

## Các chức năng khác

- **Thư viện**: kéo thả và nhập nhiều tệp video, audio, SRT, TXT; xem/nghe và lưu kết quả.
- **Tải video**: YouTube, TikTok, Douyin, Bilibili; mỗi dòng một link HTTPS, tối đa 30 video/lượt.
- **Xuất video**: cắt đoạn, đổi tốc độ 0.5–2×, chỉnh chiều cao, chèn SRT/tiêu đề, thay âm thanh, xuất MP4 H.264/AAC.
- **Hàng loạt**: chọn nhiều tệp để nhận dạng hoặc render; xử lý tối đa hai tác vụ đồng thời.
- **Biên tập**: chuẩn hóa khoảng trắng/dấu câu, tạo tiêu đề theo mẫu và khung kịch bản 60 giây. Đây là công cụ quy tắc/mẫu cục bộ, không phải chatbot sinh văn bản.
- **Dừng**: kết thúc tiến trình thực cho render, tải video và model/inference cục bộ; tệp nguồn được giữ nguyên. Tác vụ bị gián đoạn khi đóng tool được đánh dấu trong lịch sử.

Phần xem trước hiển thị video nguồn; các tùy chỉnh được áp dụng vào tệp xuất. Khi cắt hoặc tăng tốc, mốc SRT được dịch chuyển theo video mới. Giọng đọc thay âm thanh gốc, được đệm im lặng nếu ngắn và cắt nếu dài; chưa căn giọng theo từng câu phụ đề.

## Dữ liệu và cookie

Media tối đa 2 GB/tệp; SRT/TXT UTF-8 tối đa 2 MB. Dữ liệu nằm trong `data/` cạnh mã nguồn hoặc `VIDEO_STUDIO_DATA` nếu được cấu hình. Sao lưu toàn bộ thư mục dữ liệu để giữ thư viện, lịch sử và model.

Nguồn tải có thể yêu cầu cookie của tài khoản hoặc giới hạn theo khu vực. Có thể đặt `YTDLP_COOKIES_FILE` trỏ tới tệp Netscape trước khi mở tool. Không gửi cookie trong chat hay đưa vào Git. Xử lý video có sẵn không cần cookie.

Tool nghe trên cổng loopback 8766, dùng trình duyệt của máy. Đặt `VIDEO_STUDIO_PORT` nếu cần đổi cổng. Không chạy hai instance cùng một database. Đây là ứng dụng cá nhân cục bộ, chưa phải dịch vụ nhiều tài khoản trên Internet.

## Phát triển trên Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
VIDEO_STUDIO_AUTO_UPDATE=0 .venv/bin/python launcher.py --no-browser
.venv/bin/python -m unittest discover -s tests -v
```

FFmpeg/FFprobe cần có trong PATH. `VIDEO_STUDIO_AUTO_UPDATE=0` tắt tự thay mã nguồn trong checkout phát triển. Cache Hugging Face/Xet được đặt trong dữ liệu model nếu chưa có cấu hình riêng. PyAV được ghim ở phiên bản tương thích với faster-whisper.

## Xác minh

Bản này được kiểm tra trên Linux: model thật dịch Anh → Việt và Trung → Việt, Piper tạo giọng Việt/Anh, Whisper Tiny nhận dạng lời nói, và luồng trình duyệt tạo phụ đề → dịch → tạo voice → render. Các kiểm thử còn kiểm tra cập nhật, checksum, sao lưu/rollback và giữ dữ liệu. Xem `KIEM_TRA_VIDEO_STUDIO.md` trong ZIP để biết kết quả cụ thể. Các file BAT và môi trường Windows cần kiểm tra trên máy Windows.

## Lỗi không tìm thấy CTranslate2 trên Python 3.15

Trình cài cũ dùng `py -3`, chọn Python mới nhất trên máy. Nếu có cả Python 3.11 và 3.15, nó chọn 3.15 trong khi các engine chưa có wheel phù hợp. Bản 0.2.1 chọn 3.12/3.11 x64 từ Python Launcher, registry hoặc PATH, kiểm tra môi trường và chuyển môi trường không phù hợp sang thư mục sao lưu. Không cần sửa requirements hoặc cài CTranslate2 bằng Python 3.15.

Nếu không tìm thấy Python 3.11/3.12 x64, cửa sổ báo cụ thể phiên bản đã thấy và hướng dẫn cài bản 64-bit từ python.org. Python 3.11/3.12 32-bit, ARM64 native và PyPy không được chọn. Nếu cài xong nhưng DLL engine không nạp được, xem hướng dẫn Visual C++ Redistributable x64 trong cửa sổ lỗi.
