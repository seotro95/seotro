# Phân tích video tham chiếu và cách vận dụng

Nguồn người dùng cung cấp: https://github.com/seotro95/seotro/releases/tag/video

Tệp đã tải: `video.c.a.toi.mp4`, 340.611.128 byte, dài 1.262,933 giây
(21:02,933), hình 1280×720, 60 fps, âm thanh AAC stereo 44,1 kHz.
Ngôn ngữ lời kể quan sát được qua nhận dạng là tiếng Nga.

Phương pháp: đọc metadata; xem 21 khung hình lấy mẫu mỗi phút; dò chuyển cảnh
trên bản thu nhỏ 2 fps; nhận dạng toàn bộ âm thanh bằng Whisper tiny đa ngôn
ngữ. Trọng số ASR tải từ release chính thức sherpa-onnx và đối chiếu SHA-256.
Bản ASR có lỗi, kể cả đoạn lặp từ; không phải bản chép lời được duyệt nguyên
văn. Các mốc dưới đây mô tả cấu trúc lớn, không phải danh sách cắt từng frame.

## Cách kể chuyện nhìn thấy trong nguồn

- **Mở bằng một dấu vết nhỏ, mở rộng quy mô:** khoảng 00:00–01:00 nhắc đến răng
  tìm thấy ở khu vực sông Yana, rồi dẫn tới con người và khí hậu thời băng hà.
  Mồi câu nằm ở sự chênh lệch giữa vật chứng nhỏ và câu chuyện rất lớn.
- **Một luận điểm xuyên suốt:** phần lời quanh 02:00 diễn giải các lớp bảo toàn
  nhiệt: cơ thể, quần áo, nơi ở, lửa. Người xem có một ý tưởng để bám theo,
  thay vì chỉ xem các cảnh đẹp nối nhau.
- **Mỗi vật thể mở ra một vấn đề:** ảnh lấy mẫu cho thấy phòng thí nghiệm,
  vật liệu da/lông, kim, trang phục trong bảo tàng, kính che tuyết, cấu trúc
  xương voi ma mút, giày và dụng cụ. Cảnh rộng cho bối cảnh; cận cảnh cho bằng
  chứng; hình cắt lớp giải thích cơ chế.
- **Liên hệ hiện tại để hiểu quá khứ:** phần cuối liên hệ cách giữ nhiệt với
  vật liệu, thiết bị và môi trường sống hiện đại. Nhờ vậy, thông tin khảo cổ
  trở thành một câu hỏi gần gũi.
- **Kết quay về ý đầu:** đoạn kết tương phản hình ảnh ngọn lửa lớn với vai trò
  của một dụng cụ nhỏ như chiếc kim. Đây là một vòng kể chuyện khép kín.
- Có lời mời bình luận trong phần sau; không đặt lời kêu gọi quá dài trước khi
  người xem nhận được câu trả lời chính.

## Dựng và hình ảnh

Máy dò tìm được **196 ứng viên chuyển cảnh**, khoảng cách trung vị **5,5 giây**,
trung bình khoảng **6,41 giây**. Đây là số đo phụ thuộc ngưỡng 0,24 và bước lấy
mẫu 0,5 giây, không phải chứng nhận rằng mọi shot thực đều dài như vậy.

Hình ảnh luân phiên giữa toàn cảnh môi trường, cảnh người/nhà nghiên cứu, cận
vật chứng, trưng bày và hình giải thích. Mẫu khung hình có cả ảnh tư liệu và
hình mang tính tái dựng. Có logo/đồ họa kênh và cờ trong nguồn; bộ mới không
sao chép các dấu nhận diện này. Những hình có trẻ em trong video tham chiếu
không được đưa vào prompt hoặc dùng làm footage cho bộ phim mới.



## Vận dụng cho Angkor — 21:32

Chủ đề 85: thành phố và mạng lưới nước. Video nguồn được đối chiếu lại qua GitHub: HTTP 206, 65.536 byte đầu khớp tệp tham chiếu đã lưu, tổng kích thước qua Content-Range là 340.611.128 byte. Đây là kiểm tra tiền tố và kích thước, không phải tải lại và băm toàn bộ video. Xem validation/reference-access.json.

Mở bằng vệt nước nhỏ trên đá, đặt câu hỏi về thành phố, đi từ mùa và địa hình sang hồ chứa, mạng lưới, hộ gia đình, bằng chứng khảo cổ, biến động khí hậu và chính trị. Kết quay lại chính vệt nước ban đầu. Lời viết mới, không dịch hoặc chép lời video tham chiếu.

Các lớp hình: toàn cảnh xác định quy mô; trung cảnh người trưởng thành làm việc; cận đá, nước, lúa, trầm tích; mô hình giải thích cao độ, chia dòng và niên đại. Các mô hình là hình minh họa có chú thích, không phải kết quả khảo sát hay footage về một sự kiện cổ đại. Giữ nhịp quan sát và hé lộ thay vì dựng thảm họa không có bằng chứng.

Theo yêu cầu cập nhật, bộ cuối có 100 prompt trong 10 TXT, mỗi tệp đúng 10 prompt. Mỗi prompt tạo một clip 10 giây. Có 129 ô hình 10 giây, trong đó 100 ô dùng cảnh mới và 29 ô dùng lại. Ô 130 giữ khung hình cuối 2 giây. Tổng 1.000 + 290 + 2 = 1.292 giây, đúng 21:32. 129 cue lời kết thúc 21:30, sau đó là 2 giây kết không lời trong mọi MP3.

Nguồn có khoảng cách ứng viên chuyển cảnh trung vị 5,5 giây, nhanh hơn giới hạn clip 10 giây của bộ mới. Vì vậy mỗi prompt chọn một chuyển động có mục đích: 2 giây thiết lập, 6 giây phát triển, 2 giây ổn định. Trong dựng có thể chuyển từ toàn khung sang crop trong cùng ô, giữ nguyên ranh giới thời gian. Không thêm prompt trùng để mô phỏng từng nhát cắt.

Mỗi prompt ghi rõ không trẻ em, không âm thanh, không lời nói. Hình trong nguồn có trẻ em không được dùng làm footage mới. Không sao chép logo hoặc đồ họa nhận diện của nguồn. Kiểm tra cả hậu cảnh của clip sinh ra để bảo đảm chỉ có người rõ ràng từ 25 tuổi trở lên.
