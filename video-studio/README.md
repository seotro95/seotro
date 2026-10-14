# Video Studio VN 0.2.0

Tool video tiếng Việt với dịch SRT, nhận dạng và tạo giọng đọc bằng model CPU. Không cần API key. Tự tải model còn thiếu và tự kiểm tra/cập nhật bản phát hành mới khi mở.

Trên Windows: cài Python 64-bit, giải nén ZIP, đặt FFmpeg/FFprobe cạnh launcher rồi chạy `khoi_dong.bat`. Các engine được cài tự động trong `.venv`.

Đọc [HUONG_DAN.md](HUONG_DAN.md) để biết các model, cách cập nhật, dùng offline và giới hạn. Bản 0.1.0 cần tải ZIP 0.2.0 mới lần đầu.

Kiểm thử: `python -m unittest discover -s tests -v`.
