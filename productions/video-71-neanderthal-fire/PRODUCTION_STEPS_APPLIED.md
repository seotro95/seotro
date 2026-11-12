# Quy trình đã áp dụng — tập71,22:38

1. Tra đúng mục71 trong TOPICS_001_100.csv; không thay bằng một chủ đề tự chọn.
2. Đối chiếu video tham khảo với hồ sơ phân tích và ảnh mẫu đã có; dùng cấu trúc vật nhỏ–câu hỏi–nghiên cứu–giới hạn–trở lại vật mở đầu; viết lời mới.
3. Kiểm nguồn nghiên cứu, phân biệt có cháy, kiểm soát, tạo lửa và sử dụng thường xuyên; phân biệt quan sát, diễn giải và mô hình có điều kiện.
4. Viết3500từ Anh,136mốc lời,12chương110giây+38giây cuối.130prompt10giây,13TXT×10prompt,6mốc dùng lại; cuối lấy8giây. Mọi prompt không trẻ em, không chữ và không tiếng.
5. Phát hành kịch bản/prompt trước voice. Chuẩn bị10cảnh/30giây đầu trong thời lượng gốc; chỉ thực hiện edit khi có footage tập71.
6. Giữ16ID khác từtập58, đổi Việt sang actual male vi-VN-NamMinhNeural theo yêu cầu mới. Kiểm danh mục giọng và audio mẫu10giây; giữ Andrew Anh và H’môngfemale-3 tham chiếu cố định.
7. Dịch14ngôn ngữ qua nguồn được làm rõ; viết lại đủ13chương Việt/H’mông; rà thuật ngữ và niên đại. Đây không phải biên tập bản ngữ độc lập.
8. Chạy backend gốc Melo1.3.1online cho16giọng; nativeVITS+OpenVoice củaHmong1.6.6cho1giọng nữ. Mã nguồn/model/reference khóa hash. Không chạy WindowsGUI trong môi trườngLinux.
9. Anh tạo nhóm tối đa3mốc, kiểm chữ chính xác theo word-boundary rồi tách lại136mốc. Bản dịch căn13chương; nhấn từ nhẹ và thay tốc độ câu, không đổi cao độ. Cùng thời lượng không có nghĩa đồng bộ từng từ giữa ngôn ngữ.
10. Lưu checkpoint từng phần. Chỉ retry có giới hạn;401/403/429dừng, không lách giới hạn. Chỉ chạy lại job lỗi sau khi toàn bộrunkết thúc.
11. Kiểm đủ17giọng,16nam+1nữ,giải mã mỗiMP3đúng65.184.000mẫu/48kHz=1358giây. Đặt tên theo quốc gia;H’mông là tên ngôn ngữ.
12. Phát hànhMP3riêng+ZIP,kiểm tải công khai/hash/CRC và lưuQA. Lưu hồ sơv3NamMinhcho tập mới, giữ tất cả hồ sơ và audio tập cũ.

Chưa có kiểm nghe bản ngữ độc lập hoặc xác minh phương ngữ H’mông Trắng độc lập. Tập71chưa có footage hoặcMP4; không đưa video/ngữ liệu cũ của tập khác vào.
