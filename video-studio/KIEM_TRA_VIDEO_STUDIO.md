# Xác minh Video Studio VN 0.3.0

- 26 kiểm thử đạt trên Linux/Python 3.12, không bỏ qua. Bao gồm media, render, hàng đợi, cập nhật/rollback, chọn Python Windows và các kiểm thử mới cho kho giọng/connector.
- Đã lấy danh mục thật 322 giọng Microsoft Edge; có hai giọng vi-VN. Số lượng phụ thuộc dịch vụ tại thời điểm cập nhật.
- Đã tổng hợp MP3 tiếng Việt thật bằng vi-VN-HoaiMyNeural qua cả engine trực tiếp và tác vụ từ Chromium. Tệp kết quả được nhận dạng audio, lưu vào thư viện và tải được qua API.
- Chromium: lọc giọng, cập nhật danh mục, gửi TTS Edge thật; 26 lựa chọn dịch; chat GPT/Gemini với phản hồi mô phỏng; ngữ cảnh nhiều lượt; chuyển nhà cung cấp/xóa key; không lưu key vào localStorage/sessionStorage; chống thực thi HTML trong câu trả lời; bố cục 390 px và không có lỗi JavaScript.
- Kiểm thử adapter xác minh hostname/endpoint, Authorization OpenAI, x-goog-api-key Gemini, chuyển vai hội thoại, không đưa key vào URL, không trả chi tiết lỗi nhạy cảm. Kiểm thử API xác minh không ghi key vào jobs/config/tệp, không phản chiếu key trong lỗi validation, và từ chối Origin ngoài ứng dụng.
- Chưa gọi GPT/Gemini bằng tài khoản API thật vì chưa có key người dùng. Chưa xác minh kết nối tự động danh mục CapCut; chỉ có liên kết mở trang chính thức và nhập audio do người dùng xuất.
- Pip dry-run giải quyết đầy đủ 52 gói cho Windows win_amd64 CPython 3.11 và 3.12, gồm edge-tts/aiohttp. Giữ nguyên bản sửa tránh Python 3.15. Chưa thực thi BAT/DLL trên Windows thật.
- `pip check`, kiểm tra cú pháp JavaScript và `git diff --check` đều đạt. Danh mục hỏng/mất mạng được kiểm tra giữ cache; giọng không hợp lệ bị từ chối.

# Xác minh bản sửa cài đặt Windows 0.2.1

- Người dùng có Python 3.11 và 3.15; script cũ chọn bản mới nhất bằng py -3, dẫn đến không có wheel CTranslate2 tương thích Python 3.15.
- 22 kiểm thử đạt trên Linux: các kiểm thử media/model/update hiện có và bảy kiểm thử mới cho bộ chọn Python, từ chối phiên bản/ABI không hỗ trợ, giữ môi trường cũ, giữ data/model, tái dùng môi trường đúng và thông báo thiếu DLL.
- Pip dry-run giải quyết đầy đủ 42 gói cho Windows win_amd64 / CPython 3.11 và 3.12. langdetect dùng wheel Python thuần được dựng từ sdist chính thức; trên máy người dùng pip có thể dựng wheel này khi cài.
- Đã tải các wheel Windows CTranslate2, SentencePiece, Piper, PyAV, Pydantic Core và ONNX Runtime, kiểm tra native library là PE Windows x64. Không đổi pin CTranslate2 vì phiên bản đó có wheel cho 3.11/3.12; lỗi là bộ chọn interpreter.
- Đã kiểm thử bảo toàn thư mục .venv lỗi bằng mô phỏng filesystem; chưa thực thi BAT hoặc nạp DLL trên Windows thật. Việc xác nhận cuối cùng trên máy người dùng cần chạy khoi_dong.bat của bản 0.2.1.

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
