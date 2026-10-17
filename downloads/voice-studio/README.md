# Voice Studio Riêng · Windows 10/11 x64

[Tải gói ZIP](./Voice-Studio-Rieng-Windows-10-11.zip?raw=true)

Giải nén toàn bộ ZIP. Đây là gói mã nguồn kèm bộ cài, cần Python 3.12 64-bit và Internet cho lần cài/tải mô hình đầu tiên.

1. Chạy `CAI_DAT.bat` để cài thư viện và FFmpeg.
2. Chạy `TAI_GIONG_VIET.bat` để tải giọng Việt Nano.
3. Chạy `MO_TOOL.bat` để mở studio.

Giới hạn 200.000 ký tự mỗi tác vụ. Hỗ trợ TXT/SRT, mẫu giọng cá nhân, lịch sử và xuất WAV/MP3/TXT/SRT. Giọng tiêu chuẩn và quốc tế có bộ tải riêng trong ZIP. Xem `DOC_TRUOC.md` trong gói để biết chi tiết và giới hạn.

Đã kiểm tra bộ cài trên Linux, giao diện Chromium, tạo giọng Nano thật và xuất đủ bốn định dạng. Chưa chạy trực tiếp trên Windows. Mẫu Nano 148 ký tự tạo 8,23 giây âm thanh trong khoảng 1,11 giây xử lý; không bảo đảm tốc độ này với kịch bản dài và chưa đạt mục tiêu 60×.

Gói không chứa môi trường Python đã cài, trọng số mô hình, dữ liệu giọng cá nhân hay API key. Bản xuất theo tệp đúng 2 phút và ghép tệp tùy chọn chưa được triển khai.

SHA256: `ee5c95db7ceb8fbafc92399106049ac15d742c42117b6511a0cc5572e4b5dd7d`

Thư mục này chỉ cung cấp gói tải xuống; các tệp ứng dụng hiện có trong repository được giữ nguyên.
