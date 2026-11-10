# Hồ sơ các bước đã áp dụng — chủ đề 3, Mal’ta

## Kết quả

- Kịch bản tiếng Anh mới: 3.087 từ, 120 đoạn, 12 chương, mục tiêu và audio thực 20:00.
- 100 prompt mới trong 10 TXT; mỗi clip nguồn 10 giây im lặng. 20 ô timeline dùng lại clip có đánh dấu nguồn.
- Kế hoạch 8 shot cho 30 giây đầu; không cộng intro vào lời.
- 17 voice đầy đủ: 16 nam và H’Mông nữ 3; cùng ID và mẫu giọng các tập trước.
- Phong cách đọc có nhấn nhá `science-documentary-expressive-v1`; tên tệp bàn giao theo quốc gia bằng `country-filenames-vi-v1`.
- Chưa có video dựng tập 3 vì người dùng chưa cung cấp clip cho tập này.

## Các bước thực tế

1. Đọc lại hàng đợi, hồ sơ giọng, quy trình và phân tích video nguồn có SHA-256 `f1a8659dbccd4db12a79e3c18ea2e1fe08f46f7a03c42bc2250f454f69eff70c`.
2. Tra nghiên cứu Mal’ta/MA-1, Yana, Ust-Kyahta, phương pháp ADN cổ, di truyền và địa lý Beringia. Lưu 16 nguồn và bảng đối chiếu câu với giới hạn diễn giải.
3. Viết lời kể từ hạt trang sức → đứa trẻ và thung lũng → ADN hư hại → quan hệ tổ tiên → mô hình mạng lưới → địa lý và mẫu bổ sung → trở lại con người và hạt trang sức.
4. Lập 120 ô lời, chọn 100 clip riêng, đánh dấu 20 vị trí dùng lại; chia đúng 10 prompt mỗi TXT. Chuẩn bị bản đồ bờ biển/hồ hiện đại từ Natural Earth và ảnh tham chiếu NPS có nhãn 21.000 BP, không nhầm với đường bờ chính xác lúc MA-1 sống khoảng 24.000 năm trước.
5. Bàn giao tài liệu trước khi tạo audio, tại commit `ca4e72ec2d5e0db299a203d8e4ce6f52c939dc73`. ZIP gốc có SHA-256 `e8406c627595cda691bf1859a57739da0d996639f0fcc67fb3cf48676a9ef6ec`.
6. Chuẩn bị bản dịch theo ngữ cảnh 12 chương. Viết lại bản Việt và H’Mông để sửa những lỗi đã phát hiện: đại từ cho đứa trẻ, Bắc Á Âu khác Bắc Âu, tên bảo tàng, kỳ băng hà khác mùa hè, quan hệ tổ tiên khác quan hệ cha con hay một lễ hội.
7. Theo yêu cầu bổ sung, tạo cách đọc có nhấn nhá cho cả 17 bản, giữ ID và cao độ. Kiểm tra bản thử Anh 30 giây trước: 6 phần lời, 70 mốc từ, 3 nhấn từ; đủ 30 giây sau giải mã.
8. Tạo 16 giọng nam bằng backend Melo đã khoá và adapter nhịp/nhấn. Tạo H’Mông bằng engine native và mẫu nữ 3. Kiểm tra trước toàn bộ đầu vào H’Mông; mã `MA-1` có dạng đọc `em a ib`, tránh lỗi chữ số dính tên.
9. Giữ checkpoint; các giọng tạo đủ và đạt kiểm tra trong workflow `42727239753`. Không tạo lại các bản đã xong chỉ để đổi tên tệp.
10. Đối chiếu đủ 17 audio: mỗi bản giải mã 57.600.000 mẫu tại 48 kHz, đúng 1.200 giây, sai số 0 mẫu. Anh có đủ 120 SRT khớp nguyên văn kịch bản. 16 bản online có ghi nhận nhấn từ; H’Mông ghi điều khiển theo cụm.
11. Đổi tên bàn giao theo quốc gia/ngôn ngữ, giữ nguyên hash từng MP3; tạo bảng ánh xạ, ZIP tên quốc gia và hồ sơ tải riêng.
12. Lưu quy trình chuẩn, mã xử lý, hồ sơ giọng, cấu hình nhấn nhá, cấu hình tên tệp và trạng thái tiếp nối để áp dụng cho các chủ đề sau.

## Bài học giữ lại

Số từ không chứng minh thời lượng. Không chia số hàng nghìn thành nhiều câu. Không tự chọn lại giọng khi một dịch vụ lỗi. Không gọi cá thể Mal’ta là tổ tiên trực tiếp của mọi người châu Mỹ, hay gọi đường nối di truyền là một tuyến đi đã biết. Đổi tên file không làm thay đổi voice ID.

Các bản dịch và độ tự nhiên vẫn cần nghe/đọc rà soát; phương ngữ H’Mông Trắng chưa được xác nhận độc lập. Giữ trạng thái này trong những lần tiếp tục.
