Thêm 19 lựa chọn **Turbo Việt/Anh** từ đúng 19 mẫu giọng đã có; giữ nguyên 19 lựa chọn tiếng gốc. Các bản Turbo tái sử dụng WAV, mô hình và bộ nhớ đệm, không nhân đôi mẫu âm thanh.

### Đã có tool 1.12.2
Tải **Voice-Studio-1.12.3-Turbo19-Update.zip** (khoảng 176 KB). Đóng tool, giải nén thư mục cập nhật vào cạnh `app`, `runtime`, `MO_TOOL.bat`, rồi chạy `CAP_NHAT.bat` bên trong. Trình cập nhật kiểm tra SHA256, sao lưu mã cũ và giữ model, mẫu giọng, bản thu, lịch sử.

### Tải bộ đầy đủ
Tải **TAI_TOOL_19_TURBO.zip**, giải nén rồi chạy `TAI_TOOL_19_TURBO.cmd`. Trình tải lấy hai phần từ GitHub, kiểm tra SHA256 rồi ghép thành **Voice-Studio-1.12.3-19-Turbo-Windows.zip**, khoảng **2,46 GB**. Giải nén ZIP hoàn chỉnh vào thư mục mới rồi mở `MO_TOOL.bat`. Không cần cài thêm bản cập nhật nhỏ.

### Chọn giọng
Chọn **Tiếng Việt hoặc English**, rồi chọn tên có hậu tố **Turbo Việt/Anh**. Để đọc Hàn, Nga, Nhật, Pháp, Tây Ban Nha hoặc Thái, chọn ngôn ngữ gốc và tên không có hậu tố; các bản đó tiếp tục dùng OmniVoice CPU trong gói gọn. Turbo không được quảng cáo là bộ đọc các ngôn ngữ gốc này.

Sửa chống tràn biên độ trước khi ghi PCM; thêm xử lý nhiều đoạn song song cho OmniVoice CPU trong giới hạn RAM/CPU. Không giảm số bước, không đổi tốc độ phát âm để nâng kết quả đo. Máy Xeon E5-2680 v4 không có VNNI nên giữ Turbo FP32.

### Kiểm chứng
- 867 kiểm thử logic/API/FFmpeg và 9 kiểm tra con đạt; 7 bỏ qua. Hai kiểm thử trình cập nhật đạt.
- Mã hóa thật cả 19 mẫu bằng Turbo FP32; tạo thật bốn đoạn Việt/Anh từ mẫu Hàn và Thái trên CPU Linux.
- Từng tệp trong bộ đầy đủ đã được kiểm tra SHA256; tài sản tải lên cũng được đối chiếu digest từ GitHub.
- Chưa chạy lại trên Windows/GTX 1060, chưa đánh giá nghe toàn bộ 19 giọng, chưa xác minh độ giống giọng hoặc mục tiêu **1 giờ lời đọc trong 2 phút (30×)**. Đổi ngôn ngữ có thể đổi âm sắc và phát âm; nghe mẫu trước bản dài.
