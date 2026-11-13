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


## Vận dụng cho Flores — 22:00

Tệp nguồn được đối chiếu lại qua GitHub: HTTP 206, 65.536 byte đầu khớp bản tham chiếu đã lưu; Content-Range xác nhận tổng 340.611.128 byte. Đây là kiểm tra tiền tố và kích thước, không phải tải lại và băm toàn bộ video trong lượt này. Xem `validation/reference-access.json`.

Tập mới mở ở cửa hang Liang Bua, theo một dấu vết sang câu hỏi về đảo và lịch sử con người. Mạch giải thích lần lượt là địa chất → biển ngăn cách → sinh thái đảo → phát hiện Homo floresiensis → sửa đổi niên đại → quá khứ sớm hơn ở Mata Menge → Kelimutu, Inerie và cộng đồng hiện tại → trở lại cửa hang. Học cấu trúc dấu vết nhỏ mở câu chuyện lớn và vòng kết từ nguồn; không sao chép câu chữ, cảnh có trẻ em hay nhận diện kênh.

| Mốc | Vai trò kể chuyện |
|---|---|
| 00:00–02:40 | Mồi câu ánh sáng, kho lưu trữ trong hang, định vị Flores |
| 02:40–05:20 | Đá núi lửa, đá vôi và ba loại tuổi khác nhau |
| 05:20–08:00 | Wallacea, biển sâu và tiến hóa trên đảo |
| 08:00–10:40 | Phát hiện và cách đọc tổ hợp dấu hiệu giải phẫu |
| 10:40–13:00 | Cấu trúc trầm tích và niên đại sửa đổi |
| 13:00–15:20 | Mata Menge, giả thuyết tổ tiên và giới hạn của bằng chứng |
| 15:20–19:00 | Hồ Kelimutu, Inerie, Wae Rebo và trách nhiệm ghi hình |
| 19:00–22:00 | Kết nối các ngành nghiên cứu và trở lại ánh sáng cửa hang |

132 cue lời × 10 giây phủ đủ 22:00. Chỉ tạo 60 clip có chức năng hình ảnh khác nhau; 72 ô còn lại dùng lại clip theo bản đồ dựng. Sáu TXT, mỗi TXT 10 prompt, đánh số 1–60. Tổng 600 giây cảnh mới + 720 giây dùng lại = 1.320 giây. Không xóa ô dùng lại rồi rút ngắn phim.

Nguồn có nhịp thay hình thường nhanh hơn 10 giây. Để đáp ứng giới hạn mỗi prompt tạo 10 giây, clip mới ưu tiên một chuyển động máy có chủ đích: 2 giây thiết lập, 6 giây hé lộ hoặc theo chi tiết, 2 giây ổn định. Dựng có thể cắt giữa toàn cảnh và crop trong cùng ô, giữ ranh giới lời cố định. Không cần tạo thêm clip chỉ để mô phỏng mọi nhát cắt nguồn.

Tất cả prompt ghi rõ không trẻ em, không âm thanh, không lời nói. Các phần giải phẫu dùng vật thể và mô hình trung tính, không dựng hình người nhỏ có thể giống trẻ em. Mô hình trầm tích, địa lý và tái dựng môi trường là hình giải thích, không phải khám phá khảo cổ hoặc khảo sát chính xác.
