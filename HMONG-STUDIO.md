# Hmong Studio 0.3.1 — tải và chạy

[Tải gói mã nguồn kèm hai mẫu giọng Nam/Nữ](https://github.com/seotro95/seotro/raw/refs/heads/main/Hmong-Studio-0.3.1-source.zip)

Giải nén toàn bộ. Cần Python 3.10–3.12 64-bit (ưu tiên 3.12) và FFmpeg/ffprobe trong PATH. Windows chạy `start.bat`; Linux/macOS chạy `bash start.sh`. Cài thư viện lần đầu cần Internet. Đây là gói mã nguồn, không kèm Python, FFmpeg hoặc trọng số AI.

Bản 0.3.1 sửa lỗi bộ cài chọn Python 3.15 khiến PyYAML đòi Visual C++. Cài thêm [Python 3.12.10 64-bit](https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe), rồi chạy lại bản mới. Launcher kiểm tra phiên bản và giữ lại `.venv` cũ bằng cách đổi tên nếu cần. Không xóa dữ liệu giọng trong `.data`.

Hai mẫu Hmong Trắng do người dùng cung cấp đã được đặt làm mẫu mặc định, giữ nguyên âm thanh gốc. Tool có soạn/nhập TXT, lưu dự án, thu/nhập âm thanh, cắt và chỉnh âm lượng, xuất WAV/MP3, quản lý giọng cá nhân, chọn đoạn 3–8 giây và nhập lời tham chiếu sau.

**Chưa tạo hoặc nhân bản lời Hmong mới được kiểm chứng.** Cần cài mô hình Hmong phù hợp, vocabulary và vocoder, rồi nhập lời khớp đoạn mẫu. Tích hợp F5-Hmong là thử nghiệm; chưa xác nhận chất lượng Hmong Trắng/độ giống giọng. Không cần API key trong chế độ cục bộ mặc định.

Xem [hướng dẫn đầy đủ](hmong-studio/README.md). Bộ kiểm thử ứng dụng và bộ chọn Python đã chạy trên Linux; đã thử trình duyệt máy tính/điện thoại và xuất MP3 thật. Đã xác nhận có wheel PyYAML cho Python 3.12 Windows 64-bit. Launcher BAT chưa chạy trên Windows thật. Test mô phỏng suy luận không chứng minh chất lượng giọng AI.
