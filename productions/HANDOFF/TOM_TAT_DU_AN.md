# Dự án chuỗi phim khoa học tiền sử

Người dùng làm video tài liệu dài, có lời kể tiếng Anh, đồng thời phát hành16 bản voice bổ sung. Chủ đề xoay quanh khảo cổ, con người cổ, vật chứng, sinh tồn thời Băng hà và những điều khoa học còn tranh luận. Trao đổi công việc bằng tiếng Việt. Làm từng tập theo số người dùng chỉ định; danh sách100 chủ đề đã có.

Mẫu tham khảo là video.c.a.toi.mp4 ở https://github.com/seotro95/seotro/releases/tag/video, SHA256 f1a8659dbccd4db12a79e3c18ea2e1fe08f46f7a03c42bc2250f454f69eff70c. Nguồn dài khoảng21:03, lời Nga. Đã phân tích lời kể, contact sheet và các đoạn đại diện; không có tuyên bố biết phần mềm dựng, prompt nội bộ hay xem tay liên tục toàn bộ nguồn. Phong cách áp dụng: vật chứng nhỏ → câu hỏi → địa điểm/thời gian → kiểm chứng → cơ chế sinh tồn → quay lại vật chứng/câu hỏi. Xen toàn cảnh, cận vật liệu, thao tác người lớn, mô hình và phòng thí nghiệm. Cắt theo ý và dùng dissolve ngắn có lý do; không sao chép lời hay footage nguồn.

Các tập có kết quả đã lưu:1Beringia,2White Sands,3Mal’ta,4Yana,6Denisova,8Baishiya và19Kostenki. Đây không phải xác nhận mọi tập1–19 đều xong. Trạng thái đầy đủ và link ở SERIES_STATE/TIEN_DO. next_topic_id=5 trong hồ sơ là hàng đợi cũ, không phải lệnh bắt đầu tập5. Chỉ làm tập mới khi người dùng chỉ định.

Tập19 gần nhất: “Nhà bằng xương voi ma mút: kiến trúc, nguyên liệu và những điều còn tranh luận.” Tên Anh: Kostenki: The House That Remains a Question. Đã giao kịch bản2.816từ Anh;122mốc gồm121×10giây và5giây cuối;120prompt mới/12TXT; hai mốc dùng lại. Cả17MP3 đã kiểm kỹ thuật đúng1.215giây. Bản Anh dùng AndrewNeural, H’Mông dùng nữ3. Đã sửa riêng câu113 khi provider trả audio quá ngắn; không đổi lời hay ID. Năm câu fallback không có metadata từ ghép đầy đủ được ghi rõ trong QA, không tuyên bố kiểm từng từ cho những câu đó.

Video19 đã hoàn thành:20:15,1280×720,24fps,29.160khung hình; chỉ voiceAnh;10cảnh đầu trong30giây.100clip khác nhau đã được lấy mẫu hình,84clip được chọn.20mã prompt thiếu cùng các bối cảnh không phù hợp được bù bằng video liên quan; không có ảnh đứng/bảng chữ thay cảnh.34đường tiếng nguồn đã loại ngay bước nhập. Có9dissolve0,4giây có bù thời gian,12chương và phụ đềAnh tùy chọn mặc định tắt. Toàn bộ video giải mã thành công;15điểm sóng âm có độ lệch0giây, tương quan thấp nhất0,994121. Link công khai đã tải kiểm toàn bộ và khớp SHA256.

Video19:355.760.692byte, SHA2569097bce34878a4361c9a46e026694a539e2a958c067f5a022caa7cc1f760e8bd. VoiceAnh đã duyệt: SHA25684efbd7b1f7fa1a08940d793d9fdac88a645ee8267643280ba7240a781f16c5a. Kết quả kiểm hình là lấy mẫu nguồn và bản xuất, không phải xem tay liên tục toàn bộ phim.

Quy tắc khoa học cho tập19: mái che/chức năng còn là giả thuyết; phân biệt tuổi mẫu với lúc xây và thời gian sử dụng; hơn60voi ma mút không đồng nghĩa một cuộc săn; mẫu nghiên cứu39cá thể có30cá thể xác định giới tính gồm17con cái/13con đực, không phải số người. Mezhyrich/Gontsy là so sánh khác di chỉ/thời điểm; hình mô hình không thay bằng chứng. Nguồn chi tiết nằm trong CHU_DE_19/TAI_LIEU.

Giới hạn đã ghi: bản dịch và khả năng nghe tự nhiên chưa được người bản ngữ biên tập/nghe độc lập đầy đủ; phương ngữ H’Mông Trắng chưa được xác nhận độc lập. Giữ các nhãn này trong hồ sơ, không nâng QA kỹ thuật thành chứng nhận ngôn ngữ. Provider online có thể đổi mô hình dù giữ cùng voiceID.
