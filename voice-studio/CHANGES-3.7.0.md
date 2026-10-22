# Thay đổi 3.7.0

- Cài lần đầu tự chuẩn bị giọng Nano và mô hình nhân bản; chỉ báo sẵn sàng sau khi tạo/kiểm tra WAV. Turbo và Qwen tải theo lựa chọn.
- Thêm nhân bản Nano, mã hóa tham chiếu một lần; giữ nguyên engine của hồ sơ Turbo cũ.
- Tách trạng thái mô hình preset/nhân bản; thêm sửa model ngay cạnh chọn giọng.
- Từ chối mẫu tham chiếu im lặng; phát hiện và thử lại âm thanh rỗng, hỏng, NaN/Infinity.
- Thêm Review, Quảng cáo, Hướng dẫn vào các kiểu đọc; hỗ trợ trong editor văn bản và voice video.
- Nhập/xuất TXT/SRT ở các editor; hỗ trợ UTF-8 và UTF-16 có BOM. Chặn tệp không đọc được trước khi thay nội dung.
- Sửa bộ lọc quốc gia cũ làm giọng cá nhân bị mất khỏi lựa chọn.
- Mặc định mở tạo voice; phần dịch thu gọn và không chặn tạo voice độc lập.
- Launcher giữ dữ liệu cũ, mở trình duyệt khi server sẵn sàng; Qwen Portable cài vào đúng runtime.
- Đo và hiển thị tốc độ thật. Chưa đạt mục tiêu tạo một giờ âm thanh trong hai phút trên CPU thử nghiệm.
