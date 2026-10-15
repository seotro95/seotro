# Video Studio VN 0.3.0

Tool video tiếng Việt với tạo SRT, dịch 26 ngôn ngữ, giọng Piper offline và kho giọng Microsoft Edge online không cần key. Tự làm mới danh mục giọng, tự tải model thiếu và cập nhật bản phát hành khi mở.

Thêm tab GPT/Gemini: API tùy chọn với key chỉ giữ trong phiên, hoặc mở trang chat và sao chép yêu cầu để dùng không cần API key. Chưa có kết nối tự động với kho giọng CapCut; có thể nhập audio đã xuất từ CapCut.

Windows: cài Python 3.11/3.12 x64, giải nén ZIP, đặt FFmpeg/FFprobe cạnh launcher rồi chạy `khoi_dong.bat`. Trình cài tự chọn bản Python tương thích khi máy có cả Python 3.15.

Đọc [HUONG_DAN.md](HUONG_DAN.md) để biết cách cài, cập nhật và dùng các kết nối. Kiểm thử: `python -m unittest discover -s tests -v`.
