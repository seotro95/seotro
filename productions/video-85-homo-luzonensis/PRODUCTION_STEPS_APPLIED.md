# Quy trình áp dụng — chủ đề 85, thời lượng 21:22

1. Tra đúng mục 85 trong danh mục đã lưu: “Homo luzonensis: những mảnh xương mở rộng bản đồ họ hàng của chúng ta”. Không tự khởi động các chủ đề khác.
2. Đối chiếu metadata video tham khảo với hash đã lưu; xem lại bảng hình và transcript được phân tích. Dùng nhịp vật nhỏ–câu hỏi lớn–nghiên cứu–giới hạn–trở lại vật mở đầu; viết lời mới, không sao chép footage, giọng hoặc câu chữ.
3. Kiểm bằng chứng Callao, cấu trúc răng, niên đại xét lại, địa lý đảo, Kalinga và phân tích họ hàng năm 2026. Phân biệt tuổi tối thiểu với tuổi chính xác và tuổi xuất hiện loài; không gán người Kalinga là H. luzonensis hay gán hệ gene Denisovan cho hóa thạch Callao.
4. Viết 3.501 từ Anh, chia 129 mốc: 128 mốc 10 giây và 2 giây cuối. Bản dịch có 13 chương chung: 12 chương 100 giây và 82 giây cuối.
5. Tạo 120 prompt mới trong 12 TXT, đúng 10 prompt/TXT; đánh dấu 9 mốc dùng lại. Mốc cuối lấy 2 giây từ clip 001. Lập kế hoạch 10 cảnh trong 30 giây mở đầu, nằm trong tổng 21:22.
6. Mọi prompt cấm trẻ em, thiếu niên, hình ảnh và mẫu vật chưa trưởng thành; không tái hiện nguyên bộ 13 mẫu có cả mẫu chưa trưởng thành. Chỉ dùng giáo cụ giải phẫu trưởng thành có dấu chế tạo rõ, không di cốt người thật. Không phục dựng khuôn mặt, chiều cao, sọ hoặc cơ thể hoàn chỉnh của loài.
7. Mỗi prompt kết thúc “Video không có lời nói và không có âm thanh”. Không thoại, khẩu hình, nhạc, SFX, chữ, tuyến di cư hoặc dữ liệu khảo cổ giả. Mô hình vật lý là ví dụ minh họa.
8. Phát hành tài liệu trước voice. Viết lại đủ chương Việt và H’mông. Với 14 ngôn ngữ khác, dùng nguồn dịch được làm rõ và rà những câu then chốt. Sửa nghĩa “đặc điểm giải phẫu”, quá trình uranium và phân biệt các niên đại. Ghi rõ chưa có biên tập bản ngữ độc lập.
9. Giữ đủ 17 ID từ tập 71: Andrew cho tiếng Anh; Nam Minh thật, vi-VN-NamMinhNeural, nam cho tiếng Việt; H’mông female-3 nữ với hash mẫu tham chiếu cố định. Dùng backend Melo + Việt 1.3.1 online cho 16 giọng và backend VITS + OpenVoice của Voice-Studio-Hmong 1.6.6 cho H’mông. Không nhận là đã chạy giao diện Windows trong môi trường Linux.
10. Kiểm mẫu Anh 30 giây và Nam Minh 10 giây trước full render. Anh tạo nhóm tối đa 3 mốc, đối chiếu chữ hoàn toàn với metadata từ rồi tách lại theo mốc. Bản dịch căn theo chương; nhịp câu và nhấn từ nhẹ tùy backend, không đổi cao độ. Không nhận các ngôn ngữ đồng bộ từng từ.
11. Giữ checkpoint thành công. Chặn phản hồi thiếu lời trước khi đưa vào cache; tạo lại có giới hạn. Dừng khi gặp 401/403/429, không lách giới hạn dịch vụ. Khi chạy lại, chỉ xử lý phần thiếu hoặc lỗi và giữ phần đúng.
12. Trước phát hành, kiểm đủ 17 giọng, 16 nam và 1 nữ; giải mã mỗi MP3 đúng 61.536.000 mẫu mono ở 48 kHz = 1.282 giây. Đặt tên theo quốc gia; H’mông ghi theo ngôn ngữ và giới tính. Xuất MP3 riêng, ZIP voice, ZIP tài liệu và bảng tải.
13. Tải lại từ link công khai để kiểm hash, CRC, đủ link và thời lượng. Lưu báo cáo, hồ sơ giọng và trạng thái tiếp tục trên GitHub, giữ nguyên các tập đã xong.
14. Chỉ edit khi có footage của tập 85. Phim chính chỉ voice Anh, bỏ toàn bộ tiếng clip; thiếu cảnh dùng video chuyển động liên quan, không ảnh tĩnh hoặc thẻ chữ. Dựng 10 cảnh mở đầu trong 30 giây, không tăng tổng thời lượng.

Kiểm kỹ thuật không thay thế nghe/biên tập bản ngữ độc lập hoặc xác minh phương ngữ H’mông Trắng. Gói hiện tại không có footage hoặc MP4 tập 85.
