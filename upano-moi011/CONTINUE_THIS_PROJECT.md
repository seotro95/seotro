# Tiếp tục đúng dự án MỚI-011 — Upano

Đây là MỚI-011 trong bộ 100 đề tài ngày 16/11/2026. Không nhầm với chủ đề 11 về kim khâu ở danh sách cũ.

Repository: seotro95/seotro.
Nhánh sản xuất: codex/upano-moi011-production-20261116.
Release: https://github.com/seotro95/seotro/releases/tag/upano-moi-011-20m22s
Thư mục làm việc: /workspace/work/upano-moi011.

## Các yêu cầu đã khóa

- Phim mục tiêu 20:22, tức 1.222 giây.
- Kịch bản Anh nguyên bản 3.229 từ; 123 mốc: 122 × 10 giây + 2 giây.
- 130 prompt, 13 TXT, mỗi TXT đúng 10 prompt. Mỗi clip tạo 10 giây.
- Khi dựng: mở đầu 10 cảnh × 3 giây; thân 119 cảnh × 10 giây; cuối 2 giây.
- Không trẻ em trong mọi prompt, kể cả ảnh, bóng, nền, phản chiếu và màn hình.
- Mỗi prompt có câu “Video không có âm thanh, không có lời nói.”
- Phim chính chỉ voice Anh; xóa tiếng clip, không nhạc/SFX. Cảnh thiếu thay bằng video chuyển động phù hợp, không ảnh chữ.
- 16 voice nam theo danh sách hiện tại. Không có yêu cầu H'mông trong tập này.
- Việt Nam: vi-VN-NamMinhNeural. Anh: en-US-AndrewNeural.
- Đức: de-DE-ChristophNeural. Conrad cũ không có trong danh mục dịch vụ ngày 16/11/2026; đã thông báo thay đổi trong chat. 15 ID còn lại giữ nguyên. Xem VOICE_ID_CHANGE.json.
- Mỗi MP3 cần giải mã đúng 58.656.000 mẫu mono 48 kHz. Bản Anh căn 123 mốc; bản dịch căn 13 chương chung: 12 × 100 giây + 22 giây.
- Không tự nhận các bản dịch khớp từng từ hoặc đã có kiểm nghe bản ngữ độc lập.

## Trạng thái nguồn và nội dung

Nguồn khoa học chính: Rostain và cộng sự, Science 2024, DOI 10.1126/science.adi6317.
Đã đọc bản thảo tác giả công khai và các nguồn cơ quan/phương pháp. Không phát hành lại bài báo hoặc hình gốc.

Giữ rõ: LiDAR không phát hiện từ hư vô; không nhìn xuyên lá đặc hoặc chụp nhà bị chôn. Nền, đường và khu canh tác được đối chiếu khai quật. Hơn 6.000 nền trong khoảng 300 km² phân tích không tương đương số nhà cùng thời hoặc số dân. Không khẳng định một vụ phun trào xóa sổ toàn mạng lưới.

Hình tạo sinh và mô hình chỉ minh họa, không phải dữ liệu đo hay tư liệu Upano thật. Không kim tự tháp đá Maya, thành phố vàng, công cụ hay nghi lễ bịa đặt.

## Các mốc GitHub Actions

- Preflight Andrew 30 giây và Nam Minh 10 giây: 43902964757 — thành công.
- Phát hành tài liệu và 13 TXT prompt: 43905782574 — thành công; link công khai đã được tải và kiểm.
- Tạo 16 voice lần đầu: 43909217031, commit 58448e292eaae4a12f27820a55764d60df0f7cbe. Riêng Đức cũ bị thiếu trong danh mục.
- Sửa Đức Christoph và ghép 15 bản còn lại: 43910504424, commit 72729c674f1f9602281f75db0594ec201e479ee7.

Đọc SESSION_PROGRESS.json và trạng thái run hiện tại trước khi làm thêm. Không tạo lại các voice thành công vô ích.

## Kiểm tra và bàn giao

verify_public_delivery.py tải ZIP voice, kiểm SHA, CRC, giải mã đủ 16 file và kiểm HEAD các link trực tiếp. Nó kiểm cả 13 TXT, 130 prompt, dòng không âm, cấm trẻ em, timeline 1.222 giây, 5 cặp tiêu đề/thumbnail và UTF-8.

Sau khi tất cả qua, lưu báo cáo PUBLIC_DELIVERY_QA.json, profile cuối, nguồn, kịch bản, prompt và link trong GitHub. Giữ nguyên danh sách cũ và trạng thái tập tiếp theo của bộ cũ. Không tự bắt đầu tập khác.

Chưa có footage hoặc MP4 tập Upano. Người dùng đang yêu cầu kịch bản, prompt, voice và 5 tiêu đề/thumbnail; không tự nhận đã dựng phim.
