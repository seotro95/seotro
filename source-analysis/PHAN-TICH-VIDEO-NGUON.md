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

## Vận dụng cho Pohnpei — 20:00

Mở bằng đảo nhìn từ biển và đỉnh khuất mây; theo nước qua đá núi lửa, rừng, đất, vườn, suối, rừng ngập mặn và rạn. Sau đó nối với cộng đồng và dấu tích cổ, kết trở lại cảnh đầu. Cấu trúc dấu vết nhỏ → câu hỏi lớn → cơ chế → con người → quay về đầu được học từ nguồn; lời và nội dung được viết mới.

Tám phần lời, mỗi phần 2:30: định vị và kết nối; bộ khung núi lửa; thời tiết và mưa; rừng và đất; suối và thác; bờ và rạn; cộng đồng và nơi cổ; chăm sóc cảnh quan và tổng kết.

Yêu cầu cuối cùng của người dùng là **10 giây mỗi clip**, bỏ prompt cho bối cảnh lặp. Có 120 cue lời, mỗi cue 10 giây. Rà theo chức năng hình ảnh cho ra 60 prompt mới và 60 ô dùng lại, tổng đúng 20:00. Từng mã clip và timecode nằm trong BANG-TINH-120-DOAN.md và scene-voice-edit.csv.

Không tạo prompt thêm để lấp các ô đã có cảnh phù hợp. Các cảnh nói tiếp về cùng thác, mây hoặc cơ chế nước dùng lại clip tương ứng. Cận chi tiết khác chức năng giải thích vẫn có prompt riêng. Nhịp mỗi clip: khoảng 2 giây thiết lập, 6 giây phát triển, 2 giây ổn định; cắt trong ô để không làm hụt tổng phim.

Mỗi prompt ghi không trẻ em, không âm thanh, không lời nói. Mô hình khoa học và hình lịch sử gợi ý luôn được phân biệt với bằng chứng khảo sát hay footage thực địa.
