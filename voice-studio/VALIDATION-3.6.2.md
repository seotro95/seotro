# Kiểm chứng Voice Studio 3.6.2

Ngày kiểm tra: 22/10/2026. Máy kiểm tra: Linux x64, Python 3.12, CPU giới hạn 4 core, khoảng 32 GB RAM trống; không có GPU.

- **154 kiểm thử đạt, 1 bỏ qua**, 0 thất bại. Một cảnh báo deprecation trong Starlette/AnyIO không ảnh hưởng lượt chạy. Kiểm tra cú pháp JavaScript, shell và `pip check` đạt.
- Khởi động/khởi động lại dịch vụ thật; API giao diện, cấu hình và danh mục giọng hoạt động. Cổng trống được chọn khi cổng mặc định đang dùng.
- Chromium: tạo voice Nano 4 bước từ TXT, chọn nhịp Review, tải WAV, xuất TXT/SRT, nhập SRT; không có lỗi JavaScript. Cấu hình tốc độ trên máy đủ RAM chọn 4 tiến trình × 1 luồng.
- Đã tải thật Nano, Turbo và Whisper base từ upstream. Lỗi proxy Hugging Face CONNECT 403 không còn xuất hiện trong các lượt tải hoàn tất này. Không tắt TLS hoặc thay checksum để tải thành công.
- Suy luận Turbo và nhân bản từ mẫu tổng hợp đã chạy với `HF_HUB_OFFLINE=1`. Đây là phép kiểm tra luồng tham chiếu, không đo độ giống giọng của một người thật. Whisper offline nhận lại đúng câu chào/nội dung chính của mẫu Nano tạo mới.
- Đã kiểm tra tham chiếu im lặng, WAV hỏng/rỗng/NaN, checkpoint bị cắt cụt/sai định dạng, đổi số tiến trình và giữ thứ tự câu khi tiếp tục.

## Đo trọn một giờ âm thanh

Tác vụ API `07dec843cecf4cfe83bea39d648f2d8c`: Nano, Minh Quân, 4 bước, 4 tiến trình × 1 luồng, CFG mặc định, nhịp tự nhiên, tốc độ đọc 1×, không thêm khoảng nghỉ, WAV. Văn bản thử tổng hợp lặp lại, giới hạn đầu ra 60 phút; không tái sử dụng checkpoint. Không tính chờ hàng đợi.

- Đầu ra thực: **3.600,000 giây** âm thanh, mono PCM16 24 kHz. Đã đọc kiểm tra đủ khung và giây cuối có dữ liệu.
- Thời gian xử lý API: **205,299 giây = 3 phút 25,3 giây**.
- Tốc độ: **17,54× thời gian thực**. **Chưa đạt mục tiêu 1 giờ trong 2 phút (30×)** trên máy này.
- Khi đạt giới hạn 60 phút, tool dừng phần văn bản còn lại và báo `duration_limited=true`; không coi toàn bộ 163.200 ký tự đầu vào đã được đọc.
- Nano 4 bước là chế độ ưu tiên tốc độ; chất lượng/giọng khác có thể chậm hơn. Đây là kết quả trên văn bản và phần cứng cụ thể, không phải cam kết cho mọi máy.

## Gói Windows

Gói được ghép trên Linux từ Python Windows chính thức của Python Software Foundation trên NuGet, wheels Windows từ PyPI, FFmpeg được xác minh SHA256 và cache mô hình đã suy luận thật. Đã kiểm tra SHA512 runtime, SHA256/RECORD wheels, phụ thuộc riêng Windows và các DLL cần đi kèm. BUILD.json ghi nguồn và checksum. Giữ model cards/thông báo giấy phép trong gói.

**Chưa thực thi trên Windows thật.** Kiểm thử Linux và kiểm tra phụ thuộc không thay thế việc đó. `KIEM_TRA_TOOL.bat` kiểm tra mô hình offline trên máy đích bằng tệp tạm, không xóa mẫu giọng hoặc lịch sử. Qwen quốc tế, Ollama và API dịch/viết là tùy chọn chưa kèm mô hình trong gói cơ bản.
