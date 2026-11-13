# Quy trình đã áp dụng cho chủ đề 87

1. Đối chiếu danh mục đã lưu: Schöningen — vũ khí gỗ và kỹ năng săn bắt cổ. Dùng thời lượng người dùng yêu cầu:20:22, tương đương 1.222 giây. Giữ đủ 17 ID giọng từ tập 71; không sửa audio các tập trước.
2. Đối chiếu tham khảo bằng transcript và các bảng khung hình đã kiểm. Áp dụng cấu trúc vật nhỏ → câu hỏi lớn → bằng chứng → phương pháp → giới hạn → quay về vật ban đầu. Kịch bản nguyên bản, không sao chép lời, hình hoặc giọng tác giả.
3. Rà nguồn: tuổi khoảng 400 nghìn năm trong bài 1997, khoảng 300 nghìn ở các công bố sau, và khoảng 200 nghìn theo nghiên cứu 2025.187 hiện vật gồm mảnh/phế liệu, không phải 187 giáo; ít nhất 20 vũkhí và 35 công cụ gỗ chẻ theo 2024.
4. Viết 3.249 từ Anh, 123 mốc:122 mốc 10 giây và 2 giây cuối.13 chương chung cho bản dịch:12 × 100+22 giây. Cùng thời lượng và ranh giới chương, không khẳng định đồng thời từng từ.
5.110 prompt cho 110 clip mới 10 giây; 11 TXT, đúng 10 prompt/TXT, 001–110.13 mốc dùng lại được đánh dấu. Mỗi prompt cấm trẻ em, thiếu niên, lời nói và âm thanh. Bản sao gỗ và mô hình là minh họa, không dữ liệu đo thật.
6. Phát hành và kiểm tải tài liệu trước khi tạo voice. Lập kế hoạch 10 cảnh trong 30 giây mở đầu, nằm trong 20:22. Chưa có footage hoặcMP 4 tập này.
7. Thử Anh 30 giây và Nam Minh 10 giây. Xác minh vi-VN-NamMinhNeural nam trong danh mục backend và audio thật; không đổi nhãn giọng khác. Lỗi cờ tài liệu của lần thử đầu đã sửa; lần thử sau đạt.
8. Việt và H’mông viết lại đủ 13 chương.14 ngôn ngữ khác có nháp và được rà ý chính, niên đại, đơn vị và thuật ngữ. Đã thay ba đoạn Đức sót tiếng Anh, sửa câu Nhật hiểu tuổi thành số người. Chưa có kiểm nghe/biên tập bản ngữ độc lập.
9. Backend online Melo+ViệtStudio 1.3.1 cho 16 giọng. H’mông dùng backend riêng Voice-Studio-Hmong 1.6.6, VITS/OpenVoiceV 2, mẫu nữfemale-3 cố định SHA. Giữ nguồn, model, reference, ID; không đổi backend để vượt lỗi xác thực/giới hạn truy cập.
10. Anh tổng hợp nhóm tối đa 3 mốc, kiểm đủ lời bằng word metadata rồi cắt về từng mốc. Bản dịch căn chương. Nhấn từ khóa vừa phải, ngắt câu hỏi/đoạn kết, căn tempo giữ cao độ. Cache theo nội dung/giọng/tốc độ; giữ phần thành công khi sửa.
11. MP 3 mono 48 kHz 96 kbps, loudness mục tiêu−19 LUFS/truepeak−2 dB. Chỉ phát hành khi đủ lời, đúng ID và giải mã mỗi bản đúng 58.656.000 mẫu. Kiểm metadata 16 online, hash văn bản/reference Hmong, 17 hash audio riêng.
12. Phát hành 17 MP 3 tên quốc gia, ZIPvoice, script, SRT, timeline, prompt và 5 cặp tiêu đề/thumbnail. Tải lại public kiểmSHA/CRC, 17 link và duration giải mã; rồi lưu canonical GitHub.
13. Khi có footage: phim chính chỉ voice Anh, xóa âm clip, không nhạc/SFX.10 cảnh mạnh theo lời trong 30 giây đầu, không cộng intro. Thiếu cảnh dùng video chuyển động liên quan, không ảnh tĩnh/thẻ chữ. Giữ hồ sơ giọng cho tập sau, không tự bắt đầu tập khác.

Giới hạn: chưa có kiểm nghe/biên tập bản ngữ độc lập; phương ngữ H’mông Trắng chưa được xác minh độc lập. Kiểm kỹ thuật không chứng nhận phát âm hoặc độ tự nhiên.

Sửa lỗi riêng tập87: dịch vụ trả NoAudioReceived cho nhómAnh5 sau các lần thử có giới hạn. Giữ40nhómAnh đã xong và16voice khác; tách nhóm5 thành3request nhỏ cùng giọngAndrew vàbackend, ghép bằng số mẫu vàword metadata thực, rồi kiểm đủ lời và123mốc. Không sửa kịch bản,đổi giọng hoặc dùng audio trống để bù.
