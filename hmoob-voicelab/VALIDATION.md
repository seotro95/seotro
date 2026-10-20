# Kết quả kiểm tra Hmoob VoiceLab

Máy Linux, Python 3.12, 5 CPU logic; PyTorch 2.8.0+cpu, không có CUDA khả dụng.

## Đã xác minh

- 39 kiểm thử unittest: giới hạn ký tự, Unicode/CRLF, gom câu, ghép chương, phục hồi lỗi, dừng/tiếp tục, khôi phục sau restart, khóa dữ liệu, HTTP, WAV/ZIP và kiểm tra tính toàn vẹn mô hình/bộ tải.
- Tác vụ **đủ 1.000.000 ký tự** đi qua HTTP, hàng đợi và bộ ghép đầu ra: 3.334 lần gọi engine kiểm thử, hoàn tất một triệu ký tự, tổng frame WAV đúng bằng tổng frame của các đoạn. Engine ở kiểm thử trả waveform nhân tạo; đây không phải bản đọc Hmong.
- Mỗi lần polling chỉ lấy trạng thái gọn, không gửi lại toàn bộ kịch bản. Kiểm tra nhận 1.000.001 ký tự trả lỗi trước khi khởi chạy mô hình.
- FFmpeg thật trích mẫu 3 giây từ bản MP3 có sẵn; lời tham chiếu và WAV được cố định vào từng tác vụ.
- Cài và import thật F5-TTS 1.1.22, PyTorch, torchaudio, Soundfile; thử WAV thành tensor 24 kHz và tái sử dụng tensor.
- Chromium: giao diện máy tính/điện thoại, một triệu ký tự ASCII/Unicode, vượt giới hạn, tạo/dừng/tiếp tục và lịch sử bằng API kiểm thử; giao diện với máy chủ thật báo đúng thiếu mô hình và chưa có lời mẫu. Không lỗi JavaScript hoặc tràn ngang trong các lượt thử.
- Thử bộ chia đoạn với một triệu ký tự liên tục, nhiều câu ngắn và Unicode: khoảng 0,05 giây trên máy này. Đây chỉ là **thời gian chia đoạn**, không phải tốc độ inference.

## Chưa xác minh / đang bị chặn

- Tải trọng số F5-Hmong/Vocos: proxy CONNECT 403 tới Hugging Face. Bộ cài dừng an toàn, không bỏ TLS hoặc checksum.
- Chưa suy luận giọng Hmong thật, chưa có tốc độ tạo voice, chất lượng/phương ngữ Hmong Trắng hoặc độ giống hai mẫu được đánh giá. Test giả lập không thay thế các bước này.
- Hai mẫu giọng chưa có lời chép chính xác được người dùng lưu; cần nhập lời khớp đoạn 3–8 giây trước khi nhân bản.
- Chưa thử Windows BAT, CUDA/MPS hoặc một task mới sau khi publish môi trường.

Bản nháp cấu hình môi trường và snapshot được publish là hai trạng thái khác nhau. Kết quả trên không chứng minh publish hoặc khôi phục trong task mới đã thành công.
