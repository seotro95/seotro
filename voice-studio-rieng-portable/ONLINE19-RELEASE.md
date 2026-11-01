19 giọng **Azure Neural bản ngữ** cho Anh, Hàn, Nga, Nhật, Pháp, Tây Ban Nha và Thái. Đây là các giọng có tên riêng của Azure; không phải Turbo Việt/Anh hoặc bản nhân bản từ 19 mẫu cũ.

### Bộ Windows trực tuyến đầy đủ — khoảng 164 MB
Tải **Voice-Studio-1.13.0-Online19-Windows.zip**, giải nén vào thư mục mới rồi mở **MO_TOOL.bat**. Python, FFmpeg và ứng dụng đi kèm. Không chứa model cục bộ, CUDA hoặc âm thanh riêng; không cần tải lại bộ 2,46 GB.

### Đã có tool 1.12.2/1.12.3 — cập nhật khoảng 184 KB
Tải **Voice-Studio-1.13.0-Online19-Update.zip**. Đóng tool, giải nén thư mục cập nhật vào cạnh `MO_TOOL.bat`, `app`, `runtime`, rồi chạy `CAP_NHAT.bat` bên trong. Giữ nguyên giọng cũ, model, bản thu và lịch sử; mã cũ được sao lưu.

### Bắt buộc cấu hình dịch vụ của bạn
Mở **19 giọng quốc tế trực tuyến · Azure Neural**, nhập **khóa Azure Speech và vùng tài nguyên**, bấm **Lưu khóa và kiểm tra**. Cần Internet và tài khoản có hạn mức; các lượt tạo giọng, kể cả mẫu đo, có thể tính phí. Tool không bao gồm tài khoản hay tín dụng Azure. Không gửi khóa trong chat. Trên Windows, khóa lưu bằng DPAPI cho tài khoản Windows hiện tại và không xuất trong lịch sử/báo cáo.

### Các giọng
Anh (en-GB): Ryan, Thomas, Oliver. Hàn: InJoon, SunHi. Nga: Dmitry, Svetlana, Dariya. Nhật: Keita, Daichi, Naoki. Pháp: Henri, Denise, Eloise. Tây Ban Nha: Alvaro, Elvira, Ximena. Thái: Niwat, Premwadee.

Tool kiểm tra danh sách thật trong vùng/tài khoản; giọng thiếu sẽ báo rõ, không tự thay bằng giọng khác. Chọn ngôn ngữ và giọng mới, bấm **Đo giọng đang chọn**, nghe mẫu trước bản dài.

Tối đa 4 yêu cầu đồng thời, hoặc 1 khi chọn Nhẹ. Ghép câu ngắn khi không yêu cầu nghỉ riêng để giảm lượt gọi; nhận WAV PCM 24 kHz trực tiếp, giữ nguyên dấu câu và tốc độ đọc. Các chế độ giữ cùng mô hình Neural. Không dùng khoảng lặng hoặc tăng tốc phát âm để nâng số đo.

### Kiểm chứng và giới hạn
923 kiểm thử logic/API/FFmpeg và 9 kiểm tra con đạt; 7 bỏ qua. Hai kiểm thử cập nhật đạt. Bộ ZIP kiểm tra SHA256 từng tệp. Windows release gate kiểm tra bộ runtime đi kèm, API cục bộ, mã hóa/giải mã DPAPI và xử lý PCM bằng phản hồi dịch vụ giả lập; xem WINDOWS-QA.json.

**Chưa tạo giọng qua tài khoản Azure thật trong phiên này:** chưa đánh giá nghe 19 giọng, chưa đo tốc độ dịch vụ, chưa xác minh mục tiêu 1 giờ lời đọc trong 2 phút (30×). Thời gian phụ thuộc vùng, mạng, hạn mức và dịch vụ. Danh sách ứng viên được đối chiếu catalog Azure của Subtitle Edit; khả dụng hiện tại được kiểm tra bằng API khi bạn nhập khóa.
