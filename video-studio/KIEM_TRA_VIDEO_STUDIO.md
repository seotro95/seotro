# Xác minh Video Studio VN 0.2.0

Môi trường: Linux, Python 3.12, FFmpeg 7.1.5, CPU.

- 15 kiểm thử đạt, không bỏ qua: nhập media, range download, SRT, render/cắt/tốc độ/âm thanh/hàng loạt, dừng tiến trình, lưu thư viện/cài đặt và biên tập cục bộ.
- Model thật: dịch Anh → Việt và Trung → Việt; giữ nguyên mốc thời gian, số đoạn SRT; tạo giọng Việt và Anh bằng Piper; Whisper Tiny nhận dạng câu tiếng Anh từ giọng tổng hợp đúng nội dung.
- Xác minh offline: chặn hàm tải/đọc danh mục mạng khi dịch Anh → Việt và tạo giọng Việt bằng model đã cài; các thao tác hoàn tất.
- Chromium thật: nhập WAV/video, Whisper STT, dịch SRT cục bộ, Piper TTS tiếng Việt, render kèm SRT và giọng mới, lưu cấu hình tự cập nhật, không có ô nhập key, bố cục màn hình nhỏ và không có lỗi JavaScript.
- Cập nhật: kiểm tra SHA256, từ chối gói chứa đường dẫn thoát/thay dữ liệu, giữ video/.venv/tệp người dùng, sao lưu mã nguồn và rollback khi mô phỏng file Windows bị khóa.
- Đã sửa cache Hugging Face/Xet về thư mục model có quyền ghi. Đã ghim PyAV 16.1.0 để tương thích faster-whisper 1.2.1.
- Chưa chạy các file BAT trên Windows; chưa xác minh mọi cặp ngôn ngữ/model lớn hay tải video nền tảng thật. Windows cần Python 64-bit và FFmpeg/FFprobe như hướng dẫn.

Kết quả dịch máy không bảo đảm chính xác mọi thuật ngữ. Biên tập văn bản của bản này dùng quy tắc/mẫu, không phải chatbot sinh văn bản.
