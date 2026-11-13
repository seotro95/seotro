# Quy trình đã áp dụng — chủ đề 71, thời lượng 22:38

1. Tra đúng chủ đề 71 trong danh mục TOPICS_001_100.csv: “Người Neanderthal dùng lửa thế nào, và vì sao bằng chứng phân bố không đều?”. Giữ các chủ đề chưa được yêu cầu ở trạng thái chờ.
2. Đối chiếu video tham khảo với bản phân tích và ảnh mẫu đã có. Dùng nhịp kể từ một vật nhỏ đến câu hỏi lớn, nghiên cứu, cơ chế, giới hạn bằng chứng và trở lại vật mở đầu; viết lời mới. Không nhận là đã xem lại liên tục toàn bộ video nguồn trong lượt này.
3. Kiểm nguồn nghiên cứu. Tách bốn câu hỏi: có cháy, kiểm soát lửa, tạo lửa và dùng thường xuyên. Phân biệt quan sát, diễn giải và mô hình có điều kiện; không suy rộng một địa điểm thành mọi nhóm Neanderthal.
4. Viết 3.500 từ Anh, 136 mốc lời, chia 12 chương 110 giây và 38 giây cuối. Tạo 130 prompt cho clip 10 giây, đóng 13 TXT, đúng 10 prompt/TXT; đánh dấu 6 mốc dùng lại. Mốc cuối lấy 8 giây từ clip đã chỉ định.
5. Mỗi prompt cấm trẻ em, thiếu niên, chữ và tiếng; kết thúc bằng “Video không có lời nói và không có âm thanh”. Tự chọn góc máy, chuyển động và bối cảnh tương ứng lời kể. Các nhân vật, mẫu vật, trầm tích và bố trí khảo cổ đều là minh họa.
6. Phát hành tài liệu trước voice. Lập kế hoạch 10 cảnh trong 30 giây mở đầu, nằm trong thời lượng gốc. Chỉ thực hiện edit khi người dùng cung cấp footage của tập 71.
7. Theo yêu cầu mới, đổi Việt sang giọng nam thật vi-VN-NamMinhNeural. Kiểm danh mục giọng và mẫu audio 10 giây. Giữ 16 nhận diện khác, gồm Andrew cho bản Anh và nữ H’mông female-3 với mẫu tham chiếu cố định. Audio Adam của các tập 45/58 giữ nguyên.
8. Viết lại đủ 13 chương Việt và H’mông. Với 14 ngôn ngữ khác, dịch từ nguồn đã làm rõ các ý dễ nhầm, rồi rà niên đại và thuật ngữ chính. Ghi riêng trạng thái kiểm ngôn ngữ; không nhận là đã được biên tập bản ngữ độc lập.
9. Dùng backend online của Melo + Việt 1.3.1 cho 16 giọng và backend VITS + OpenVoice của Voice-Studio-Hmong 1.6.6 cho giọng nữ H’mông. Khóa mã nguồn và hash model/mẫu tham chiếu. Thực thi backend trong Linux, không nhận là đã chạy giao diện Windows.
10. Bản Anh tạo theo nhóm tối đa 3 mốc. Kiểm chữ khớp hoàn toàn với metadata từ, rồi tách lại 136 mốc. Bản dịch căn theo 13 ranh giới chương chung. Nhấn từ nhẹ và điều chỉnh nhịp câu trong khả năng từng backend; căn thời lượng không đổi cao độ. Không nhận là các ngôn ngữ đồng bộ từng từ.
11. Lưu từng phần đã thành công. Retry có giới hạn; dừng khi gặp 401/403/429. Đoạn Đan Mạch trả về thiếu lời đã bị chặn, vô hiệu hóa cache không đầy đủ và tạo lại thành công trong workflow 43243793604. Không dùng đoạn thiếu lời để lấp thời lượng.
12. Kiểm đủ 17 giọng: 16 nam và 1 nữ. Giải mã mỗi MP3 đúng 65.184.000 mẫu mono ở 48 kHz, tương đương 1.358 giây. Đặt tên file theo quốc gia; H’mông được ghi theo ngôn ngữ và giới tính.
13. Phát hành MP3 riêng, ZIP voice và ZIP tài liệu; sau đó tải lại để kiểm hash, CRC, link tải và thời lượng. Lưu các báo cáo kiểm tra cùng cấu hình v3 Nam Minh trên GitHub cho những tập mới.
14. Khi có footage: phim chính chỉ voice Anh; bỏ toàn bộ tiếng clip, không nhạc hoặc SFX. Cảnh thiếu dùng video chuyển động liên quan, không ảnh tĩnh hoặc thẻ chữ. Giữ 10 cảnh mở đầu trong 30 giây và tổng 22:38.

Các bản dịch và audio chưa có kiểm nghe/biên tập bản ngữ độc lập; phương ngữ H’mông Trắng chưa được xác minh độc lập. Tập 71 chưa có footage hoặc MP4. Không dùng media của tập khác làm bản phim hoàn chỉnh cho tập này.
