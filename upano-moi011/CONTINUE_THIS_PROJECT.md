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

## Trạng thái hoàn tất

Đã phát hành và tải công khai kiểm lại cả 16 voice. Mỗi bản giải mã đúng 58.656.000 mẫu mono 48 kHz = 20:22; ZIP qua CRC và SHA256. Cả 16 link MP3 trả HTTP 200. Tài liệu cuối có 130 prompt trong 13 TXT, timeline 130 cảnh đủ 1.222 giây, kịch bản và phụ đề, 5 cặp tiêu đề/thumbnail, bản dịch và hồ sơ giọng.

Tệp đọc được lưu tại productions/video-moi011-upano/ trong repository. Hồ sơ dùng cho bộ đề tài mới nằm tại research/channel-analysis-20261116/VOICE_PROFILES_LOCKED.json và PRODUCTION_STATE.json. Bộ đề tài cũ productions/series/ vẫn giữ nguyên.

## Các mốc GitHub Actions

- Preflight Andrew 30 giây và Nam Minh 10 giây: 43902964757 — thành công.
- Tài liệu và 13 TXT prompt: 43905782574 — thành công.
- Lượt tạo đầu 43909217031: giữ 14 voice thành công, giữ các nhóm Anh đã tạo; Conrad cũ vắng trong danh mục.
- Đức Christoph: 43910504424 — phần tạo Đức thành công; phần chờ cũ không dùng làm chứng nhận bàn giao.
- Khôi phục phần Anh thiếu và xuất gói cuối: 43914663934 — cả ba job english, country14, publish thành công. Không tạo lại 16 bản này khi chỉ cần tải chúng.

Backend thực dùng là thành phần online của Melo-Viet-Studio 1.3.1 ở commit khóa trong MELO_SOURCE_LOCK.json, gọi giọng Microsoft Edge qua edge-tts. Không khẳng định chạy giao diện Windows hoặc model Melo đa ngôn ngữ cục bộ.

## Kiểm tra và bàn giao

verify_public_delivery.py tải ZIP voice, kiểm SHA, CRC, giải mã đủ 16 file và kiểm HEAD các link trực tiếp. Nó kiểm cả 13 TXT, 130 prompt, dòng không âm, cấm trẻ em, timeline 1.222 giây, 5 cặp tiêu đề/thumbnail và UTF-8.

Các kiểm tra đã qua; PUBLIC_DELIVERY_QA.json, GITHUB_ASSET_AUDIT.json, profile cuối, nguồn, kịch bản, prompt và link được lưu trong GitHub. Giữ nguyên danh sách cũ và trạng thái tập tiếp theo của bộ cũ. Không tự bắt đầu tập khác.

Chưa có footage hoặc MP4 tập Upano. Người dùng đang yêu cầu kịch bản, prompt, voice và 5 tiêu đề/thumbnail; không tự nhận đã dựng phim.
