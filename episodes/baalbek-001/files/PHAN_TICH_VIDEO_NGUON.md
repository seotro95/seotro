# Nguồn tham khảo và cách chuyển sang Baalbek

Nguồn người dùng: https://github.com/seotro95/seotro/releases/tag/video
Tệp: video.c.a.toi.mp4; release 438900717; asset 726808685.
Digest công khai: f1a8659dbccd4db12a79e3c18ea2e1fe08f46f7a03c42bc2250f454f69eff70c.

Đã xem lại contact sheet của đúng bộ phân tích đã lưu từ nguồn này và đọc hồ sơ metadata/nhịp dựng trước đó. Phạm vi là mẫu hình theo thời gian, không phải nghe duyệt toàn bộ video hoặc có transcript nguyên văn. Bản nhận dạng tự động cũ là tiếng Nga và không được coi là lời nguồn chính xác. Không sao chép câu chữ nguồn.

Metadata đã lưu: nguồn dài 21:02,933, 1280×720, H.264 60fps; tiếng AAC stereo. Nguồn dài hơn mục tiêu 20:42 của tập Baalbek. Máy dò cũ trên mẫu 2fps, ngưỡng 0,24 có 196 ứng viên chuyển cảnh, khoảng cách trung vị 5,5 giây; đây không phải số điểm cắt chính xác từng frame.

Các mẫu hình quan sát được luân phiên cảnh quan, cận vật liệu, dụng cụ, người nghiên cứu, bảo tàng và hình cắt lớp. Có đoạn liên hệ tri thức sinh tồn thời cổ với hiện tại. Nguồn có thành phần hình, cờ, logo và con người không được chuyển nguyên sang bộ mới.

## Cách áp dụng
- Mở bằng vật thể và câu hỏi: ba khối Trilithon đã lắp; đối chiếu ngay với khối còn ở mỏ.
- Một lập luận xuyên suốt: tải trọng phải được đỡ liên tục từ nền đá gốc đến vị trí đặt; thiết bị kéo chỉ là một phần hệ thống.
- Xen cảnh đẹp và cơ chế: cảnh đền/mỏ, cận dấu đục, bản đồ, mô hình ma sát, mặt cắt nền đường, nghiên cứu hiện vật.
- Tăng trở ngại theo tiến trình: tách đá, nền đường, lực kéo, dốc, dừng tải, căn chỉnh; sau đó kiểm tra giả định và bằng chứng.
- Kết vòng tròn: trở lại góc máy nền đền như mở đầu, nhưng câu hỏi giờ cụ thể và có thể kiểm tra hơn.

## Dùng khung người dùng cung cấp
0:00–0:25: câu hỏi trung tâm. Mốc 0:25 nằm trong clip 3 và có thể đặt marker tại đó mà không thay lưới voice 10 giây.
0:25–2:00: bối cảnh và giới hạn.
2:00–5:00: bằng chứng từ mỏ và nền đền.
5:00–11:00: giải thích cơ chế theo bước.
11:00–16:00: thử thách mô hình và giới hạn bằng chứng.
16:00–19:00: so sánh các khả năng.
19:00–20:40: kết luận có giới hạn, trở lại hình mở đầu và câu hỏi khảo sát.
20:40–20:42: hai giây kết không lời; phần kết được mở rộng phù hợp thời lượng 20:42 đã yêu cầu.

## Chuyển sang prompt 10 giây
Mỗi prompt ưu tiên một chuyển động máy và một mục tiêu hình. Nhịp gợi ý 2 giây thiết lập, 6 giây hé lộ, 2 giây ổn định. Có thể crop hoặc cắt cận trong ô 10 giây ở bản dựng mà không làm thay đổi tổng thời gian. Lời đọc nằm ở file voice riêng, không yêu cầu mô hình video phát lời.

125 prompt: 124 clip đầu dùng đủ 10 giây; clip 125 tạo 10 giây nhưng chỉ dùng 2 giây đầu. 12 TXT đầu có 10 prompt/tệp; TXT 13 có 5 prompt. Không bỏ số hoặc thêm prompt giả để đủ nhóm.

Mọi prompt nhắc lại không âm thanh, lời nói và không trẻ em. Nhân vật nếu có phải rõ là người trưởng thành 30–60 tuổi, kể cả người ở xa hoặc hình trong hình. Mọi cảnh RECON/DIAGRAM/LAB là phục dựng hoặc minh họa; nhãn và số liệu chính xác được thêm khi dựng, không giao AI tự tạo chữ.
