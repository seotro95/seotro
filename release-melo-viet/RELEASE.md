**Melo + Việt Studio 1.2.0** thêm bộ đọc **Piper ONNX FP32 chạy CPU** để tạo lời mới nhanh hơn và thêm đúng **20 ngôn ngữ trên máy**. Không đổi tên các giọng này thành Melo/VieNeu.

### Tải và cập nhật

- **CPU-Day-Du-Windows.zip**: chương trình và **27 mô hình Piper cho 24 tiếng**, có cấu hình, mã SHA256 và MODEL_CARD gốc. Cài thư viện vẫn cần Internet lần đầu. Sau khi cài, những giọng Piper này dùng ngoại tuyến. Melo/VieNeu giữ nguyên mô hình đã có; khi cài mới, các mô hình đó được tải riêng lúc dùng.
- **Cap-Nhat-Windows.zip**: chương trình nhỏ; tải mô hình Piper đã chọn khi dùng lần đầu. Phù hợp nếu muốn tải ít giọng.

Đóng tool cũ → giải nén ZIP → chạy **CAP_NHAT.bat** → mở **MO_TOOL.bat mới** → Ctrl+F5. Không cần cài lại Ubuntu; tên WSL `Ubuntu` với hệ điều hành 22.04 vẫn dùng được. Các mô hình, bản thu và lịch sử cũ được giữ lại.

Cài mới nhẹ: **CAI_CPU_NHANH.bat** cài Piper + bộ trực tuyến, không cài PyTorch/CUDA, có 24 tiếng Piper. **CAI_DAT.bat** cài thêm Melo/VieNeu để đủ tổng cộng 27 tiếng và các preset gốc.

### Chọn đúng bộ đọc để đo lại

Bộ đọc **Trên máy** → Loại giọng **CPU nhanh** → tiếng **Tây Ban Nha** → giọng **ONNX nhanh · es_ES-davefx-medium**. Bấm **Nghe thử** trước, rồi nhập lời và tạo **bản mới**. Bỏ chọn dùng lại đoạn nếu muốn đo tổng hợp mới. Báo cáo cần ghi **Piper ONNX FP32 CPU**. Số đo MeloTTS cũ trong lịch sử không thay đổi sau cập nhật.

Piper là mô hình/giọng khác với Melo/VieNeu; chất giọng và phát âm có thể khác. Chọn **Melo/VieNeu gốc** để dùng các giọng cũ. Nhật/Hàn/Trung vẫn dùng MeloTTS. Không có việc âm thầm thay giọng trong một tác vụ.

### Hai mươi tiếng mới chạy trên máy

Nga, Đức, Ý, Bồ Đào Nha, Hà Lan, Ba Lan, Hindi, Thụy Điển, Đan Mạch, Phần Lan, Na Uy, Séc, Slovakia, Hungary, Romania, Thổ Nhĩ Kỳ, Ả Rập, Ba Tư, Indonesia và Catalan. Tổng cộng **27 tiếng** khi có cả Melo/VieNeu. Piper còn cung cấp các lựa chọn CPU nhanh cho Việt/Anh/Pháp/Tây Ban Nha.

### Tăng tốc và sửa điều khiển

- Tạo 1–4 đoạn Piper song song trong cùng một bản, giữ đúng thứ tự lời. Tự giới hạn theo CPU khả dụng, số bản đồng thời và số luồng mỗi đoạn để giảm quá tải. Giữ 1–4 bản đồng thời như trước.
- Giữ tần số lấy mẫu gốc khi ghép WAV. Tốc độ đọc 1× không cần chạy ffmpeg để đổi tần số từng đoạn. Giữ FP32 và khoảng dự phòng biên độ; không ép INT8 hoặc đổi tốc độ phát âm để làm đẹp số đo.
- Chọn một giọng là mặc định; bật **Chọn nhiều giọng** khi cần. **Nghe thử** tạo âm thanh thật với giọng đang chọn và mở trình phát khi xong.
- Nút tải danh mục trực tuyến thực sự làm mới danh sách. Lỗi tạo âm thanh xuất hiện ngay gần ô chọn giọng, có **Sao chép lỗi**; phân biệt không có âm thanh, HTTP 401/403, SSL, proxy và hết thời gian chờ. Không chỉ dựa vào việc tải được danh sách để cho rằng tạo giọng đã hoạt động.
- Trực tuyến vẫn cần mạng truy cập Microsoft từ WSL. Đã kiểm tra bằng mẫu thật; không thể bảo đảm mọi mạng/mọi thời điểm đều kết nối được. Chọn bộ trên máy để dùng ngoại tuyến.

Giữ các tính năng 1.1.0: ô một triệu ký tự, chia đoạn, TXT/SRT và mã hóa tệp, kiểu nhịp đọc, tốc độ 0,5–2×, nhiều giọng, hàng đợi, lịch sử, tiếp tục, WAV từng phần và ZIP tải trực tiếp. SRT xuất theo ranh giới âm thanh thực, không căn từng từ hay ép mốc nhập.

**Chưa xác minh tạo đủ một giờ lời đọc trong hai phút trên máy Windows của bạn.** Các mẫu FP32 tổng hợp mới nhanh hơn đáng kể trong kiểm thử, nhưng tốc độ còn phụ thuộc giọng, CPU, số đoạn/bản đồng thời. Báo cáo phân biệt cache với tổng hợp mới; không coi dùng lại âm thanh là tăng tốc mô hình. Chưa có đánh giá nghe bởi người bản ngữ cho mọi giọng. Các bộ/mô hình giữ giấy phép riêng trong SOURCES.md và MODEL_CARD.
