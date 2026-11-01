Bộ cài **MeloTTS riêng + VieNeu Turbo tiếng Việt**, chạy CPU trên Windows thông qua Ubuntu 22.04 / WSL2. Không cần Azure hoặc API tạo giọng trả phí. Không sửa Voice Studio đang có.

**ZIP khoảng 25 KB là bộ cài, chưa chứa mô hình**: khi cài và thử các tiếng sẽ tải thêm vài GB thư viện, từ điển và mô hình; nên chuẩn bị ít nhất 15 GB trống.

1. Trong PowerShell **Run as administrator**, chạy `wsl --install -d Ubuntu-22.04`; khởi động lại nếu được yêu cầu.
2. Mở Ubuntu 22.04 từ Start, tạo username/mật khẩu Linux.
3. Giải nén ZIP vào thư mục cố định, ví dụ `D:\Melo-Viet`. Chạy `CAI_DAT.bat`, nhập mật khẩu Linux khi sudo hỏi và chờ cài xong.
4. Chạy `MO_TOOL.bat`. Mở `http://localhost:8817`, chọn ngôn ngữ, bấm **Tải/chuẩn bị giọng**, rồi tạo WAV.
5. Sau khi đã tạo thử thành công các tiếng muốn dùng, có thể mở `MO_OFFLINE.bat` để dùng những mô hình đã lưu.

**Các tiếng:** VI dùng VieNeu Turbo FP32; EN, FR, JP, KR, ES, ZH dùng MeloTTS. Nga/Thái và nhân bản 19 mẫu riêng cũ không nằm trong bộ này. Các giọng hiển thị từ chính mô hình sau khi tải.

MeloTTS chính thức hiện có release v0.1.2; bộ cài dùng main `209145371cff8fc3bd60d7be902ea69cbdb7965a` đã kiểm tra. Hai môi trường độc lập tránh xung đột NumPy/Librosa; PyTorch CPU, không cài CUDA/driver và không ép INT8 trên Xeon E5-2680 v4. Mô hình giữ lại giữa các lượt đọc; không nạp lại mỗi câu khi giữ tool mở.

29 kiểm thử điều khiển/API/PCM đạt. Cổng phát hành chạy cài đặt thực trên Ubuntu 22.04, kiểm tra mô hình bằng các câu ngắn công khai trong bảy tiếng; số đo trong `MODEL-QA.json` là CPU Linux của runner, không phải Windows/Xeon của bạn. Kiểm tra launcher Windows chỉ xác nhận cú pháp PowerShell; WSL vẫn cần được bạn bật và cài trên máy.

**Chưa có đánh giá nghe bởi người bản ngữ cho mọi giọng hoặc xác minh 30× lời đọc thực.** WAV có khoảng nghỉ; số đo theo độ dài WAV không chứng minh tạo một giờ lời đọc trong hai phút. Nghe mẫu trước khi tạo bản dài. Chi tiết cài, lỗi thường gặp và tự động hóa nằm trong ZIP.
