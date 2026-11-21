# MỚI-061 — kịch bản và dựng theo retention mới

Phim điều tra địa chất ngoài trời: ảnh toàn thể gặp lớp đá thật/mô hình dưới đất. Câu hỏi trung tâm là điều gì nâng các lớp đá, mở chúng thành vòng và để Richat hiện ra như hôm nay. Phát hiện sớm: vòng bám lớp đá chịu xói mòn khác nhau; cú ngoặt lớn: một cấu trúc có thể chứa nhiều thế hệ magma.

## Nhịp kể

- 00:00–00:10: chỉ một chi tiết, lớp đá nghiêng nối vào sống núi cong; một câu hỏi. Không intro, tên kênh hoặc địa lý trước hook.
- Trước 00:30 nêu câu hỏi trung tâm. Phát hiện cụ thể đầu tiên ngay phần mở, trước phút thứ hai.
- Mười phần, chín phần 130 giây và phần cuối 132 giây, tổng 21:42. Mỗi phần có 20 block lời; block 3–10 giây, độ dài câu và số câu biến đổi. Toàn bộ chữ số trong lời Anh được viết thành từ.
- Mỗi phần có móc cụ thể ở đầu và khoảng giữa: lớp đá, vật mẫu, nơi chốn, tuổi hoặc phép thử. Khoảng cách re-hook được kiểm trong RETENTION_QA.json; không đoạn suy ngẫm trừu tượng dài hơn 90 giây.
- Mỗi phần có ít nhất một khoảnh khắc hiện tại cụ thể. Một beat giới hạn bằng chứng ngắn ở gần cuối; các beat cách ít nhất 120 giây, không xếp hai caveat liên tiếp. Sau beat là câu chuyển/kéo sang phần tiếp.
- Kết trả lời nguồn gốc địa chất ở mức bằng chứng cho phép. Dòng cuối duy nhất: “What lies beneath the Eye's oldest rings?”

## Trục mười phần

1. 00:00–02:10: lớp nghiêng và vòng rộng khoảng 40km; vị trí, phát hiện sớm, vòm bị bóc mái.
2. 02:10–04:20: mô hình cắt lớp cong, dip ra ngoài, cuesta và xói mòn chọn lọc.
3. 04:20–06:30: trầm tích cổ, quan hệ tiếp xúc và thứ tự trước/sau.
4. 06:30–08:40: sill/dyke, gabbro và đề xuất nghiên cứu 2024.
5. 08:40–10:50: breccia, hốc, hòa tan–sập đổ, chất lưu nóng và feldspar.
6. 10:50–13:00: các đồng hồ khác nhau; mô hình tuổi gabbro và sự kiện trẻ hơn.
7. 13:00–15:10: phần đá mất đi, nước/gió, đá cứng–mềm và cồn cát.
8. 15:10–17:20: phép thử va chạm/công trình con người; dữ kiện nào phân biệt quá trình.
9. 17:20–19:30: ảnh Landsat hợp lệ, các tỷ lệ quan sát, mô hình từ trường/trọng lực.
10. 19:30–21:42: trở lại lớp mở đầu, trả lời câu hỏi chính rồi để một bí ẩn ngầm mạnh nhất.

## Ngôn ngữ dựng

Hook mới ưu tiên một vật thể trong 10 giây đầu, thay cho montage 10 cảnh của yêu cầu cũ. Sau đó 5 cảnh × 4 giây để mở rộng quy mô. Timeline: 10 + 5 × 4 + 127 × 10 + 2 = 1.302 giây, 134 cảnh. Tạo 140 clip 10 giây/14 TXT; ID135–140 là dự phòng, không cộng vào phim. CSV gắn từng shot với mọi block lời chồng lấn, không buộc một cue lời bằng một clip.

Cắt theo ý và từ nhấn; phần thân xen field/macro/model/reference. Match cut đường lớp đá → mép mô hình → vòng ở ảnh vệ tinh. Chủ yếu cut thẳng; dissolve ngắn khi chuyển quy mô/thời đoạn. Không flash/strobe, hiệu ứng video game hoặc đảo địa chất để tạo cú ngoặt giả. Giữ màu sa mạc tự nhiên. Không vẽ thêm thành phố, hố thiên thạch, đồng tâm hoàn hảo hoặc magma đang phun tại Richat hiện đại.

Toàn cảnh Richat dùng ảnh NASA/USGS nguyên gốc làm reference; chuyển động máy trên ảnh 2D không phải footage bay thực hay DEM. Chọn khung tránh chú giải mép dưới trái; giữ credit trong mô tả/credit biên tập. Hình field/deep-time và các mẫu là minh họa. Mô hình bỏ tỷ lệ để giải thích, không lấy hình paper và làm giả biểu đồ nghiên cứu.

Không lab, áo blouse, trẻ em, chữ đọc được hoặc âm thanh/lời nói trong clip. Tất cả nhân vật và bàn tay nhìn rõ trưởng thành 35–65, không trẻ em ở nền/bóng/phản chiếu. Thời kỳ địa chất sâu không có người, công trình hoặc khủng long trang trí. Chỉ voice Anh trong bản dựng chính, xóa âm clip, không nhạc/SFX. Cảnh thiếu thay clip chuyển động tương ứng từ dự phòng.

## Giọng và kiểm định

Giữ 16 ID giọng nam đã lưu, Andrew cho Anh và Nam Minh cho Việt. Backend online khóa của Melo-Viet-Studio1.3.1 / Microsoft Edge qua edge-tts; không nhận đã chạy UI Windows hoặc model Melo đa ngôn ngữ cục bộ. Native rate Anh +2%, nhấn từ nhẹ tối đa1,2dB, không đổi pitch. Fit theo ranh giới từ thực và giới hạn tempo0,55–1,65. Bản nước ngoài chuyển thể theo 10 phần chung (9×130+132 giây), không dịch từng câu hoặc đồng bộ từng từ. Mỗi MP3 phải giải mã đủ62.496.000 mẫu mono48kHz. Thành công được checkpoint, chỉ tạo lại phần thiếu. Chưa kiểm nghe/biên tập bản ngữ độc lập.
