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

## Vận dụng cho Nan Madol, tập 36

Luận điểm mới: **một thành phố đá là kết quả của cả mạng lưới con người, nguồn lực và hiểu biết về mặt nước**.

Mở bằng một khối bazan ở mép triều. Nâng góc máy để lộ tường, rồi các đảo và kênh. Đi từ vật chứng nhỏ sang câu hỏi lớn giống cấu trúc kể của nguồn, nhưng toàn bộ lời và nội dung Nan Madol được viết mới. Không sao chép lời Nga, cảnh cụ thể, logo hay nhạc nguồn.

Mạch triển khai: địa hình và vật liệu → khả năng vận chuyển → nhu cầu sống và lối tiếp cận → quyền lực Saudeleur → truyền khẩu và giới hạn bằng chứng → biến đổi vai trò → bảo tồn → trở lại khối đá ban đầu. Câu trả lời chính là năng lực tổ chức của con người; các chi tiết chưa đủ bằng chứng vẫn được để ngỏ.

## Nhịp lời 22:18

| Chương | Mốc lời | Trọng tâm |
|---|---|---|
| 1 | 00:00–02:30 | Khối đá, thành phố, câu hỏi và cách đọc chứng cứ |
| 2 | 02:30–05:00 | Pohnpei, bazan, nền đảo và mạng kênh |
| 3 | 05:00–07:30 | Chia nhỏ bài toán vận chuyển, tổ chức lao động |
| 4 | 07:30–10:00 | Nước ngọt, thực phẩm, lối vào và những gì không còn |
| 5 | 10:00–12:30 | Saudeleur, kiến trúc quyền lực, Nandowas |
| 6 | 12:30–15:00 | Truyền khẩu, định tuổi và giới hạn diễn giải |
| 7 | 15:00–17:30 | Thay đổi chức năng, ký ức còn sống, môi trường |
| 8 | 17:30–20:00 | Bảo tồn, cộng đồng, du lịch và mô hình minh họa |
| 9 | 20:00–22:18 | Tổng hợp, trở lại khối đá và con triều |

Các mốc chương theo lời, không yêu cầu cắt hình tại mọi ranh giới chương. Có 134 cue: 133 cue dài 10 giây và cue cuối dài 8 giây. Bản Anh có khoảng 2.870 từ, gồm lời và các khoảng nghỉ đã định trong từng cue.

## Thay đổi người dùng đã chọn: giảm còn 70 prompt

Mỗi prompt tạo một clip khoảng 20 giây, một chuyển động máy chính. Nhịp gợi ý 4 giây thiết lập, 12 giây hé lộ, 4 giây ổn định. Luân phiên toàn, trung, cận và mô hình ở các clip kế tiếp để giữ năng lượng trong giới hạn ít clip hơn nguồn.

- Prompt 1–66 dùng 20 giây/cảnh: tổng 22:00.
- Prompt 67 tạo 20 giây, dùng 18 giây đầu: kết thúc 22:18.
- Prompt 68–70 là dự phòng, chỉ thay cảnh tương ứng; không nối thêm.
- Có 7 TXT, mỗi TXT đúng 10 prompt, đánh số liên tục 1–70.
- Mỗi cảnh chính khớp hai cue lời; xem `scene-voice-edit.csv`.

Ưu tiên cắt thẳng. Nếu hòa trộn, giữ hiệu ứng bên trong ô thời gian hoặc dùng handle ngoài ô; không chồng lấn làm hụt tổng phim. Khi dựng loại mọi track âm thanh clip nguồn bằng `-an`, rồi ghép đúng một narration đã kiểm tra. Không có nhạc và hiệu ứng trong bộ voice này.

Mỗi prompt nhắc rõ không trẻ em, không âm thanh và không lời nói. Người nếu xuất hiện phải rõ ràng từ 25 tuổi. Hình về vận chuyển, mặt cắt nền đảo và địa chất là mô hình giải thích; không tự nhận đã biết chính xác công pháp, đã khai quật mới hay đang quay thực địa.
