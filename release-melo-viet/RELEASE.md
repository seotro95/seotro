Melo + Việt Studio **1.1.0**: soạn tối đa **1.000.000 ký tự**, tự chia đoạn, tạo **1–4 bản đồng thời**, nhập nhiều TXT/SRT và lưu lịch sử bản thu.

**Đang dùng 1.0.0 / 1.0.1:** đóng tool cũ, giải nén ZIP mới vào thư mục cố định, chạy **CAP_NHAT.bat**, chờ xong rồi chạy **MO_TOOL.bat mới**. Không cài lại Ubuntu, không xóa mô hình hoặc bản thu. Nếu trang cũ còn hiện, Ctrl+F5. Bản cập nhật không chạy lại cài hai bộ Melo/VieNeu.

**Cài mới:** `CAI_DAT.bat` cài đủ ba bộ đọc. `CAI_TRUC_TUYEN.bat` chỉ cài bộ trực tuyến nhẹ, không tải mô hình Melo/VieNeu. ZIP là bộ cài, chưa chứa thư viện/mô hình. Vẫn cần **WSL2 với hệ điều hành Ubuntu 22.04**, tên đăng ký có thể là `Ubuntu`; không cần tên phải là `Ubuntu-22.04`.

Các tính năng:

- Chọn nhiều giọng để cùng một văn bản có nhiều bản thu. Hàng đợi theo thứ tự gửi, tiến độ theo đoạn, dừng từng bản, nghe đoạn đầu và tiếp tục sau gián đoạn. Giữ mô hình trong RAM; Melo giữ tối đa hai mô hình mỗi tiến trình xử lý và đổi số luồng không phải nạp lại trọng số.
- Kiểu nhịp kể chuyện, review phim, thuyết minh, bản tin, nhẹ nhàng. Đây là tốc độ gợi ý và nhịp nghỉ, **không phải mô hình cảm xúc riêng**. Tốc độ đọc 0,5–2×, giữ cao độ.
- Nhập nhiều TXT/SRT, tự nhận dạng theo nội dung và UTF-8/UTF-16 có BOM; chọn thêm Windows-1258/1252 nếu cần. Tệp lỗi được đánh dấu riêng. Không đọc số thứ tự/mốc SRT thành lời.
- Xuất WAV, TXT, SRT và báo cáo. SRT đầu ra theo ranh giới từng đoạn âm thanh thực, **không căn từng từ và không ép vào thời gian SRT nhập**. Mỗi phần WAV có phụ đề riêng; còn có phụ đề toàn bản. Bản dài tự chia WAV khoảng một giờ/phần để tránh giới hạn RIFF; ZIP64 tải trực tiếp không tạo thêm bản sao toàn bộ WAV trên đĩa.
- Lịch sử giữ lại giữa các lần mở; vẫn thấy WAV cũ 1.0.x. Dùng lại các đoạn đã tạo theo nội dung/giọng để tạo lại hoặc tiếp tục. Có thể tắt dùng lại đoạn khi đo tổng hợp mới.
- Ngoại tuyến: VieNeu Turbo FP32 cho Việt; MeloTTS cho Anh, Pháp, Nhật, Hàn, Tây Ban Nha, Trung. Không ép INT8 trên Xeon cũ, không cài CUDA/đụng driver GPU.
- Trực tuyến: tải danh mục giọng/quốc gia thật từ Microsoft Edge qua **edge-tts 7.3.1**, gồm các tiếng khác như Nga, Thái, Đức, Ý khi dịch vụ cung cấp. Không cần khóa trong tool. **Nội dung sẽ gửi tới Microsoft**; đây là tích hợp bên thứ ba, không phải API Azure chính thức, dịch vụ có thể thay đổi hoặc giới hạn. Mỗi quốc gia chỉ hiển thị giọng thực sự có, không nhân bản giả giọng.

Kiểm tra chức năng gồm 52 kiểm thử Python, 13 tình huống launcher Windows PowerShell 5.1 với WSL giả lập, kiểm thử trình duyệt máy tính/di động (âm thanh mô phỏng) và thử mô hình thật trên Ubuntu 22.04. Báo cáo thật kèm Release phân biệt tổng hợp mới và dùng lại đoạn; không dùng âm thanh mô phỏng để tuyên bố tốc độ mô hình.

**Chưa xác minh tạo một giờ lời đọc trong hai phút hoặc chất lượng nghe bởi người bản ngữ cho mọi giọng.** Số đo theo WAV có khoảng nghỉ, thời gian nạp, tốc độ phát âm đã chọn và số đoạn dùng lại; lượt có cache không phải tốc độ tổng hợp mới. Tạo nhiều bản đồng thời dùng thêm CPU/RAM và có thể làm từng bản chậm hơn. Kết quả Linux CI không bảo đảm tốc độ trên Windows/Xeon của bạn. Hướng dẫn đầy đủ trong `HUONG_DAN.txt`.
