# Mẫu tham khảo và cách áp dụng cho MỚI-011 Upano

Nguồn người dùng: https://github.com/seotro95/seotro/releases/tag/video

Asset: video.c.a.toi.mp4. Kích thước 340.611.128 byte. SHA256: f1a8659dbccd4db12a79e3c18ea2e1fe08f46f7a03c42bc2250f454f69eff70c. Metadata release được đối chiếu lại trong lượt này.

Đã đọc lại phần phân tích dựa trên transcript và các bảng khung hình mở đầu, chuyển động, tổng thể lưu trong phiên trước. Không khẳng định vừa xem liên tục toàn bộ phim hoặc xác định phần mềm, prompt, giọng nội bộ của tác giả.

Mẫu tham khảo kể về tiền sử và sinh tồn qua một vật nhỏ, bối cảnh khắc nghiệt và cơ chế giải thích. Các mẫu hình luân phiên toàn cảnh, hoạt động, đặc tả hiện vật, mô hình địa lý và cảnh phục dựng. Phần mở có chữ thời gian, quốc kỳ và logo; tập Upano không cần mang các lớp này sang.

Tập mới giữ cách mở rộng quy mô của câu hỏi, nhưng chọn một trọng tâm thống nhất: người Upano tổ chức nền đất, đường, canh tác và nước thành một mạng lưới thế nào, và bằng chứng cho biết tới đâu. Mở đầu không hứa phim về kho báu hoặc một dân tộc hoàn toàn chưa ai biết.

## Nhịp câu chuyện 20:22

- 00:00–00:30: 10 cảnh ngắn; từ tán cây tới nền đất, mô hình mạng lưới, đường, nước và vật mẫu. Câu hỏi chính nằm trong phần voice mở.
- 00:30–02:00: địa lý, vật liệu và việc một cảnh quan màu mỡ vẫn có thể khó tổ chức.
- 02:00–05:00: khảo sát trước LiDAR, cơ chế xung sáng và việc ghép khảo sát với khai quật.
- 05:00–11:00: nền đất → đường → thoát nước → canh tác và thức ăn.
- 11:00–16:00: quan hệ không gian, bảo trì, tích lũy qua thời gian và cách phối hợp xã hội.
- 16:00–19:00: tính đồng thời, dân số, niên đại, núi lửa và những giải thích phải kiểm tra.
- 19:00–20:22: thu lại các mối liên hệ, trở lại cảnh quan mở đầu và trả lời ở mức bằng chứng cho phép.

Không dùng mọi câu hỏi như một cliffhanger. Mỗi phần phải thêm thông tin hoặc cơ chế. Cảnh 10 giây là nguyên liệu; không bắt một ý voice bằng một cảnh trong đoạn mở 3 giây.

## Phương án hình

130 prompt mới, 13 TXT, mỗi TXT 10 prompt. Mỗi clip nguồn 10 giây. Trên timeline: cảnh 001–010 lấy 3 giây mỗi cảnh; 011–129 lấy 10 giây; 130 lấy 2 giây. Tổng 1.222 giây. Không thêm một intro riêng ngoài thời lượng.

Các góc máy được chọn cho từng việc: toàn cảnh cho địa hình, góc cao cho bố cục, thấp ngang cho độ cao nền, macro cho đất và mẫu, mặt cắt/mô hình cho cơ chế. Tránh chỉ bay drone qua rừng trong mọi đoạn.

Mô hình có ngôn ngữ vật liệu đất và hình thức giải thích rõ ràng. Point cloud, đường sáng và địa hình tạo sinh không phải dữ liệu đo Upano. Phục dựng nhà luôn có giới hạn; nhiều cảnh chỉ để nền hoặc khung, không tự thêm kiến trúc Maya, mái đền, ngai vàng hoặc nghi lễ.

Không có trẻ em trong bất kỳ prompt nào, kể cả nền, ảnh, màn hình, bóng và phản chiếu. Người hiện đại và bàn tay phải rõ trưởng thành 35–65 tuổi. Không tái hiện một nhà nghiên cứu có thật bằng gương mặt AI.

## Hướng dựng khi có footage

Cắt theo nhịp câu và nghĩa. Ưu tiên cut thẳng; hòa ngắn khoảng 0,2–0,35 giây khi chuyển không gian. Thông số này là đề xuất mới, không phải số đo xác nhận từ phim tham khảo.

Giữ màu đất và cây tự nhiên; mô hình đủ rõ để người xem không nhầm với ảnh khảo sát thật. Không dùng glitch, flash hay zoom giật liên tục để thay việc dẫn chuyện.

Chỉ voice tiếng Anh trong phim chính. Xóa toàn bộ âm clip, không nhạc/SFX. Nếu thiếu cảnh, dùng video chuyển động phù hợp cùng ý, không ảnh tĩnh có chữ. Giữ các bản voice quốc gia riêng.

Khi hòa có overlap, bù thời lượng để hình vẫn đủ 20:22. Kiểm tra điểm kết, khoảng đen, cảnh trùng gần nhau, chữ AI bị sinh sai, nước chảy phi vật lý và mọi hình người chưa trưởng thành trước khi xuất.

Đây là kịch bản và kế hoạch tạo hình; chưa có clip hoặc MP4 tập Upano. Đồng bộ voice kiểm theo mẫu âm thanh; không tự nhận footage chưa được tạo đã khớp nội dung.
