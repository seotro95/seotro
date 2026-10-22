# Voice Studio 3.7.0

Tool tạo voice và nhân bản giọng, giao diện tiếng Việt, chạy trên máy. Mở tool sẽ vào màn hình **Tạo giọng**. Tạo voice Việt không cần API key; lần cài đầu cần Internet để tải thư viện và mô hình.

## Cài mới trên Windows

1. Giải nén toàn bộ gói vào thư mục có quyền ghi, ví dụ `D:\Voice-Studio`.
2. Cài **Python 3.12 64-bit** từ https://www.python.org/downloads/windows/ và bật **Add python.exe to PATH**.
3. Cài FFmpeg có cả `ffmpeg` và `ffprobe`. Có thể dùng `winget install --id Gyan.FFmpeg -e`, sau đó đóng/mở lại cửa sổ. Hoặc đặt hai chương trình trong `voice-studio/.tools/ffmpeg/bin/`.
4. Trong thư mục `voice-studio`, bấm **MO_TOOL.bat**. Lần đầu tool tự tạo môi trường, cài thư viện, tải Nano và tạo âm thanh kiểm tra cả giọng sẵn có lẫn nhân bản. Turbo là lựa chọn tải riêng trong giao diện. Giữ cửa sổ mở; tốc độ tải phụ thuộc mạng và có thể mất nhiều phút.
5. Khi sẵn sàng, trình duyệt tự mở. Các lần sau tiếp tục bấm **MO_TOOL.bat**. Giữ cửa sổ chạy nền; Ctrl+C để tắt.

Gói ZIP này chứa đầy đủ mã ứng dụng, giao diện, trình cài/chạy và kiểm thử. **Không chứa Python, FFmpeg hoặc trọng số mô hình**; đây không phải EXE Portable đã kèm runtime. Cần vài GB dung lượng trống cho thư viện và các mô hình tải lần đầu. Nano/Turbo dùng ONNX CPU; không phải cài PyTorch để tạo giọng Việt.

Linux/macOS: cài Python 3.12, FFmpeg/FFprobe rồi chạy `bash install.sh`, sau đó `bash start.sh` trong thư mục `voice-studio`. Khuyến nghị RAM 8 GB trở lên; chọn một tiến trình nếu ít RAM.

## Cập nhật bản đang dùng

Tắt cửa sổ Voice Studio cũ. Sao lưu `.data`, rồi chép các tệp trong thư mục `voice-studio` của ZIP mới đè vào thư mục `voice-studio` cũ. **Giữ `.data`, `.venv` và các thư mục `runtime`/`ffmpeg` cũ**. Không xóa cả thư mục tool trước khi cập nhật.

Bấm `MO_TOOL.bat` trong thư mục vừa cập nhật. Nếu đã có Windows Portable với `../runtime/python.exe`, launcher dùng lại runtime đó. Nếu chưa có mô hình nhân bản Nano, giọng cá nhân cũ vẫn dùng Turbo; chọn giọng Nano cá nhân rồi bấm **Tải model** để bổ sung. Kiểm tra giao diện hiển thị **v3.7.0**.

## Tạo voice

1. Dán văn bản hoặc **Nhập TXT / SRT**.
2. Chọn ngôn ngữ, nguồn giọng, giọng đọc. Nếu chưa sẵn sàng, bấm **Tải model cho giọng đang chọn**, chờ kiểm tra xong.
3. Chọn kiểu đọc: **Tự nhiên, Kể chuyện, Review, Tin tức, Quảng cáo, Hướng dẫn, Thư giãn, Sôi nổi**.
4. Bấm **Tạo giọng nói**, nghe lại rồi tải WAV/MP3. TXT/SRT có thể xuất từ editor hoặc Lịch sử.

Các kiểu đọc điều chỉnh tốc độ và khoảng nghỉ. Đây là điều khiển nhịp đọc, chưa phải mô hình điều khiển đầy đủ cảm xúc bằng mô tả tự do. Có thể đánh dấu `**từ cần nhấn**` và `[pause=1.5]`. Kiểm tra tên riêng, số và phát âm trước khi dùng bản thu.

Nano 4 bước ưu tiên tốc độ/bản nháp; 8 hoặc 16 bước ưu tiên độ rõ. Có lựa chọn một/hai tiến trình tạo đoạn, giữ mô hình trong RAM và tái sử dụng các đoạn hoàn tất khi tiếp tục tác vụ. Đổi giọng không tự thay nội dung hoặc ngôn ngữ đang nhập.

## Nhân bản giọng đọc

Mở **Nhân bản giọng**, đặt tên, chọn ngôn ngữ và engine. Nạp mẫu WAV/MP3/M4A/FLAC/OGG/WEBM **3–30 giây, tối đa 20 MB**, một người nói rõ, ít tạp âm, không nhạc. Xác nhận quyền sử dụng giọng rồi lưu. Mẫu im lặng/quá nhỏ sẽ bị từ chối.

- **Nano**: nhân bản Việt ưu tiên tốc độ; tải thêm các đồ thị tham chiếu khi chưa có. Mô hình giọng có sẵn và mô hình nhân bản có trạng thái sẵn sàng riêng.
- **Turbo**: lựa chọn Việt khác, dùng mô hình riêng. Không tự đổi các hồ sơ Turbo cũ sang Nano.
- **Tự động**: chọn Nano nếu mô hình nhân bản đã sẵn sàng, nếu chưa dùng Turbo.
- **Qwen**: nhân bản quốc tế, cần cài/tải riêng qua `THEM_GIONG_QUOC_TE.bat` hoặc nút tải model trong tool. Nên nhập đúng lời nói trong mẫu; không bắt buộc với Nano.

Sau khi lưu, bấm **Sử dụng giọng**, nhập **lời đọc mới** và tạo voice. Lưu mẫu là đăng ký tham chiếu; quá trình tạo âm thanh mới dùng các đặc trưng giọng đã mã hóa, không phát lại bản mẫu và không huấn luyện lại mô hình. Chỉ dùng mẫu của bạn hoặc có quyền sử dụng. Độ giống/chất lượng phụ thuộc mẫu và ngôn ngữ; cần nghe kiểm tra. Các phép thử tự động không đo độ giống người nói.

## Nhập/xuất tệp

- Nhập `.txt` và `.srt`, tối đa 2 MB/tệp và 200.000 ký tự; UTF-8 hoặc UTF-16 có BOM. Có thể chọn định dạng khi dán nội dung.
- TXT: đọc liên tục; tùy chọn bỏ mốc phút–giây đầu dòng. Xuất TXT được ngay. TXT sang SRT cần tạo voice xong để lấy mốc đoạn thực tế; sửa lời thì tạo lại voice trước khi xuất SRT.
- SRT: giữ mốc từng câu, chèn im lặng để bám timeline. Câu dài có thể tăng nhịp trong giới hạn; nếu không vừa, báo câu cần rút ngắn/nới mốc, không bỏ lời. Mốc tăng dần, không chồng nhau, tối đa 10.000 câu/3 giờ.
- Tải bản thu WAV/MP3 và lời TXT/SRT trong Lịch sử. SRT là mốc câu/đoạn, chưa căn từng từ hay khớp khẩu hình.
- Có khu vực video để nhập video, sửa phụ đề, tạo voice riêng hoặc lồng tiếng. Nhận dạng video cần Whisper (`download_subtitle_model.bat`); dịch và viết kịch bản là tính năng tùy chọn, cần Ollama có mô hình riêng hoặc API của nhà cung cấp.

## Tốc độ: mục tiêu 1 giờ voice trong 2 phút

Mục tiêu tương đương **30× thời gian thực**. Bản này giảm số lượt mô hình bằng ghép câu ngắn, giữ mô hình nóng, mã hóa mẫu giọng một lần và tạo đoạn song song khi chọn. Không tăng tốc bản đọc hoặc chèn im lặng để làm đẹp số đo.

Phép đo thật trên CPU AMD EPYC 7763, 3 vCPU, không GPU, Nano 4 bước/một tiến trình: **89,84 giây âm thanh trong 12,152 giây xử lý**, tương đương **7,39×**; ngoại suy khoảng **8,1 phút cho một giờ âm thanh**. Đây là mẫu ngắn, không phải phép chạy đủ một giờ; không gồm thời gian tải/cài model. Nhân bản và các kiểu đọc có thể chậm hơn. **Chưa đạt và không bảo đảm mục tiêu 2 phút/giờ**. Tool hiển thị tốc độ đo được từ tác vụ mới hoàn tất; không dùng các đoạn cache để công bố benchmark.

## Nếu không tạo được voice

- Giữ cửa sổ tool mở và kiểm tra giọng đã **Sẵn sàng**. Bấm **Kiểm tra / sửa model** để tải bổ sung và kiểm tra lại âm thanh; cần Internet.
- Có model nhưng báo thiếu thư viện: chạy lại `install.bat`; bản Portable dùng lại runtime cũ và có thể tải/sửa model qua giao diện.
- Model tạo WAV rỗng/hỏng/NaN: tool thử lại tối đa ba lần; Nano thử 16 bước ở lần cuối. Nếu vẫn lỗi, báo đúng đoạn/câu; không đánh dấu tệp rỗng là hoàn tất.
- Giọng Việt/Anh VieNeu không đọc chữ Trung/Nhật/Hàn. Dịch lời hoặc chọn giọng quốc tế hỗ trợ, tool sẽ báo trước khi đưa tác vụ vào hàng đợi.
- Dừng tác vụ có thể **Tiếp tục** từ các đoạn đã lưu. Khởi động lại giữ lịch sử, mẫu giọng và bản thu trong `.data`.

## Kiểm chứng

Xem `VALIDATION.md` cho kết quả kiểm thử phiên bản này. Đã chạy tạo voice Nano và nhân bản thật offline, nhập/xuất TXT/SRT/WAV/MP3 qua API và trình duyệt Chromium trên Linux CPU. Chưa chạy bộ cài hoặc batch trên Windows thật trong phiên này. Không có phép đo đầy đủ một giờ hoặc đánh giá độ giống giọng người thật. Mô hình quốc tế Qwen là tùy chọn, chưa kiểm tra sinh âm thanh trong phiên này.
