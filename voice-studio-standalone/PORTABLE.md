# Bản Portable Windows 1.1.1

Quy trình build trong `.github/workflows/standalone-voice-portable.yml` tạo gói Windows x64 gồm Python 3.12, toàn bộ thư viện chạy giọng, FFmpeg, mô hình Nano/Nano nhân bản và Turbo tiêu chuẩn. Đầu ra là `Voice-Studio-Rieng-1.1.1-Portable-Windows-x64.zip`.

Người dùng giải nén toàn bộ ZIP rồi mở **MO_TOOL.bat**. Không cần cài Python, FFmpeg, thư viện, API key hoặc tải mô hình tiếng Việt. Dữ liệu và mẫu giọng nằm trong `app/.data`; sao lưu thư mục này trước khi cập nhật.

Gói này chuẩn bị đầy đủ quy trình tạo và nhân bản **tiếng Việt trên CPU**, cùng giọng Việt/Anh có sẵn của Turbo. Mô hình Qwen quốc tế không được đưa vào gói. Nhân bản Nano 4 bước ưu tiên tốc độ và có thể giảm độ giống giọng, vì vậy cần nghe thử.

## Kiểm tra trước khi phát hành

- Build trên Windows 2022 x64 với Python 3.12.10 và bộ thư viện đã ghim phiên bản.
- Xác minh SHA256 FFmpeg theo manifest chính thức; giữ giấy phép của Python, FFmpeg, thư viện và model cards trong ZIP.
- Chuyển thư mục đã build sang đường dẫn có khoảng trắng để kiểm tra khả năng di chuyển của Python và thư viện.
- Bật chế độ offline, chặn kết nối ngoài loopback cho Python và các worker con; chạy tạo giọng có sẵn, đăng ký mẫu, nhân bản Nano song song và Turbo, xuất WAV/MP3/TXT/SRT và mở launcher bằng Python kèm gói.
- Chỉ đóng ZIP và phát hành khi các bước native Windows thành công. Dọn mẫu kiểm thử, lịch sử và tệp tạm khỏi dữ liệu gói trước khi phát hành.

Lệnh build cho máy Windows có Visual Studio/MSVC redistributable và dependencies đã cài:

```powershell
python packaging/build_windows.py --output "C:/build/Voice-Studio-Rieng-Portable"
```

Không thể dùng Python Linux để tạo ra kết quả đã kiểm chứng Windows. Trạng thái thành công phải được lấy từ chính lượt GitHub Actions tương ứng; việc có mã build không có nghĩa đã có bản Portable dùng được.
