# Hmoob VoiceLab — tool mới cho văn bản dài

[Tải Hmoob VoiceLab 1.0 — gói ZIP](https://github.com/seotro95/seotro/raw/refs/heads/main/Hmoob-VoiceLab-1.0-source.zip)

Giải nén toàn bộ. Cài Python 3.12 64-bit và Python Launcher, rồi chạy `start.bat` để mở giao diện. Để tạo giọng, cài FFmpeg/ffprobe, chạy `install_voice.bat` và nhập lời khớp đoạn mẫu 3–8 giây. Gói mã nguồn không kèm Python, FFmpeg hoặc mô hình AI; bộ cài cần Internet để tải mô hình.

Mã nguồn độc lập tại [hmoob-voicelab](hmoob-voicelab/README.md). Nhập tối đa **1.000.000 ký tự**, hàng đợi có thể dừng/tiếp tục, đầu ra thành nhiều chương WAV và ZIP. Windows dùng Python 3.12 64-bit, chạy `start.bat`; cài bộ tạo giọng bằng `install_voice.bat`.

Phần ứng dụng đã kiểm thử. **Chưa xác minh tạo voice Hmong thật hoặc tốc độ**: máy cloud hiện bị proxy chặn tải mô hình Hugging Face (CONNECT 403); cần tải đủ trọng số và nhập lời khớp đoạn giọng mẫu. Xem hướng dẫn và `VALIDATION.md` trong thư mục tool.
