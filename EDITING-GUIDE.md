# Dựng tập 40 — Flores — đúng 22:00

Nguồn kể chuyện: https://github.com/seotro95/seotro/releases/tag/video . Lời và hình của tập này được viết mới theo chủ đề 40 đã lưu.

## Tính số cảnh

- Toàn phim: **1.320 giây = 132 ô × 10 giây**.
- Tạo **60 clip mới**, mỗi clip 10 giây: **600 giây**.
- **72 ô dùng lại** các clip đã có: **720 giây**.
- Tổng 600 + 720 = 1.320 giây. Không bỏ các ô dùng lại khỏi timeline.
- Có **6 TXT**, mỗi TXT đúng 10 prompt; số thứ tự liên tục 1–60. Không cần tạo thêm prompt cho bối cảnh đã có.

Đặt tên clip `clip-001.mp4` đến `clip-060.mp4`. Trong `scene-voice-edit.csv`, cột `prompt` là mã clip, `slot` là vị trí dựng. Một mã clip có thể xuất hiện ở nhiều ô nhưng chỉ cần tạo một lần. Bảng Markdown tương đương là `BANG-TINH-132-DOAN.md`; `shot-reuse-map.json` cung cấp dữ liệu máy đọc được.

## Thứ tự thao tác

1. Tạo 60 clip bằng sáu TXT theo thứ tự. Mỗi clip phải có đủ 10 giây sử dụng được, không có trẻ em, âm thanh hay lời nói.
2. Tạo sequence 16:9 dài chính xác 22:00. Chọn tốc độ khung hình giao nhận 25 hoặc 30 fps; cả hai đều chia tròn mỗi ô 10 giây.
3. Điền đầy đủ 132 ô theo bảng. Ô 1 bắt đầu 00:00; ô 132 chạy 21:50–22:00. Giữ cảnh dùng lại đủ 10 giây; có thể đổi crop nhẹ nếu nguồn đủ độ phân giải, không làm sai bối cảnh hoặc đổi chiều địa lý.
4. Cắt thẳng ở các ranh giới 10 giây. Nếu muốn nhịp gần nguồn hơn, có thể cắt giữa toàn cảnh và crop chi tiết ngay trong một ô, không tạo prompt mới. Chuyển cảnh mềm phải nằm trong độ dài đã tính, không cộng thêm thời gian vào cuối phim.
5. Xóa hoặc tắt toàn bộ âm thanh do mô hình video sinh ra. Mỗi bản phim dùng một MP3 ngôn ngữ tương ứng bắt đầu từ 00:00; không chồng cả 17 voice.
6. Nạp SRT đúng ngôn ngữ trong `scripts/`. Mỗi file có 132 cue, cùng mốc với lời và hình. Tiếng Anh Andrew là bản phim chính; các MP3 khác là track thay thế, không phải phần phụ nối sau tiếng Anh.
7. Khi xuất, đặt điểm kết 22:00. MP3 có thể hiện thêm vài mili giây do khung mã hóa; dữ liệu giải mã đã kiểm tra đúng **31.680.000 mẫu ở 24 kHz = 1.320 giây**.

## Cách kể và hình ảnh

Mở bằng ánh sáng ở cửa hang và một dấu vết nhỏ, mở rộng ra địa chất cùng biển, rồi trở lại phát hiện và câu hỏi niên đại. Sau đó chuyển sang cảnh quan, cộng đồng hiện tại và kết lại ở cửa hang. Xen toàn cảnh để định vị, trung cảnh để theo hành động, cận cảnh để giải thích vật chứng. Trong clip 10 giây, gợi ý 2 giây thiết lập, 6 giây phát triển, 2 giây ổn định.

Các chương: 00:00–02:40 mở câu hỏi và định vị; 02:40–05:20 địa chất; 05:20–08:00 Wallacea và sinh thái đảo; 08:00–10:40 phát hiện; 10:40–13:00 niên đại; 13:00–15:20 quá khứ sớm hơn; 15:20–19:00 cảnh quan và cộng đồng; 19:00–22:00 kết nối và kết phim.

Gắn chú thích biên tập như “Illustrative reconstruction” cho mô hình khoa học hoặc cảnh tái dựng; prompt cố ý không yêu cầu mô hình tự viết chữ. Không gọi chúng là footage khảo sát thực tế. Không thêm cảnh người tiền sử nhỏ, bộ xương người, hình trẻ em, nghi lễ dàn dựng hay hồ đổi màu tức thì. Kiểm tra tất cả khung hình của clip được tạo, kể cả hậu cảnh.

## Giọng và kiểm tra cuối

Giữ nguyên voice ID, model và preset trong `VOICE_PROFILES.json` cho các tập sau: 16 giọng nam; ngoại lệ H’Mông Trắng là nữ female-3. Công cụ chạy bằng backend Python của Melo-Viet Studio và Voice Studio Hmong trong Linux cloud. File Windows EXE không được chạy.

Các file đã qua kiểm tra độ dài, mẫu âm thanh, dữ liệu hữu hạn, mức đỉnh, không mất từ do cắt và sự khớp giữa kịch bản với báo cáo render. Chưa có duyệt toàn bộ bởi người bản ngữ; nên nghe rà trước khi phát hành phim. Gói này cung cấp lời, voice, prompt và bảng dựng, chưa chứa 60 clip do mô hình video tạo hay phim MP4 hoàn chỉnh.
