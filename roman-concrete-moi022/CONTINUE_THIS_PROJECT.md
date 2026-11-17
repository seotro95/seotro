# Tiếp tục MỚI-022 — Bê tông La Mã

Đây là chủ đề 022 của bộ 100 đề tài mới ngày 16/11/2026, do người dùng chỉ định. Không nhầm với bộ chủ đề cũ. Giờ người dùng GMT+7, ngày bắt đầu tập này 17/11/2026.

Repository seotro95/seotro; nhánh codex/roman-moi022-production-20261117; canonical codex/beringia-video-01. Release: https://github.com/seotro95/seotro/releases/tag/roman-concrete-moi-022-21m22s

## Khóa yêu cầu

- Mục tiêu 21:22 = 1.282 giây. 129 cues Anh: 128 × 10 giây + 2 giây cuối. 3.539 từ.
- 140 prompt mới trong 14 TXT, đúng 10/tệp. Clip nguồn 10 giây. Không trẻ em/thiếu niên kể cả nền, ảnh, màn hình, phản chiếu; người/tay rõ trưởng thành 35–65 tuổi.
- Yêu cầu bổ sung mới nhất: lấy nhiều bối cảnh lịch sử La Mã, bỏ nhà khoa học và mọi phòng thí nghiệm hiện đại. Tất cả 140 prompt đã thay ở bản historical-context-v2-no-scientists. Mô hình cận vật liệu vẫn dùng được nếu trung tính và chỉ minh họa; không bịa người La Mã làm thí nghiệm hiện đại.
- Mỗi prompt kết đúng “Video không có âm thanh, không có lời nói.”
- Timeline 136 cảnh: 10 cảnh mở × 3 giây, 125 cảnh × 10 giây, cuối 2 giây. 137–140 là bốn prompt dự phòng được đánh dấu, không cộng vào timeline.
- Phim chính khi có footage chỉ voice Anh, xóa âm clip, không nhạc/SFX. Không dùng ảnh chữ thay cảnh thiếu. Hiện chưa có footage, thumbnail hay MP4 tập này.
- 16 voice nam giữ nguyên cả 16 ID đã dùng Upano, gồm Andrew, Nam Minh và Christoph; không H'mông trong yêu cầu tập này. Đã kiểm live catalogue 318 giọng: cả 16 ID còn có.
- Backend online Melo-Viet-Studio 1.3.1 ở commit 4f4fa1d72d976d6e2b9c94f906b0e12c6a2cf043, checksum khóa tại MELO_SOURCE_LOCK.json. Giọng Microsoft Edge qua edge-tts; không UI Windows hoặc native Melo đa ngôn ngữ.
- Mỗi MP3 giải mã đúng 61.536.000 mẫu mono 48 kHz = 21:22. Anh căn 129 cues; bản dịch 13 chương chung: 12 × 100 giây + 82 giây cuối. Không hứa đồng bộ từng từ.
- Không tuyên bố đã kiểm nghe/biên tập bản ngữ độc lập. Việt Nam viết lại toàn bộ 4.437 từ đếm khoảng trắng; 14 bản khác dịch từ nguồn kỹ thuật đã làm rõ, sửa thuật ngữ, đọc các đoạn quan trọng, rà ngày/số và tiếng Anh lọt. Phạm vi thật nằm trong TRANSLATION_REVIEW.json; không dùng draft cũ.

## Nội dung và nguồn

Nguồn chính: Seymour và cộng sự, Science Advances 2023, DOI 10.1126/sciadv.add1602; toàn văn chính đã đọc ở PMC9821858, không tự nhận đọc toàn bộ supplement. Phân biệt mẫu khảo cổ Privernum với mẫu hiện đại dùng trong phép thử. Mẫu thử Mix 1 là vữa OPC/tro bay/cát/nước và thêm vôi sống, không bản sao mọi công thức La Mã. Khe khoảng 0,5 mm; có tiền xử lý hai tháng ướt/khô trước pha dòng chảy tối đa 30 ngày. Giảm thấm không chứng minh khôi phục toàn sức chịu lực.

Bằng chứng công trường Pompeii 2025: đọc abstract và MIT News; Nature chuyển xác thực, PMC kiểm tra trình duyệt. Không vượt chặn, không tự nhận toàn văn. Không suy mọi người La Mã cùng kỹ thuật hoặc chủ ý hóa học hiện đại. Bê tông biển là câu chuyện liên quan nhưng khác; không dùng nước biển để “sửa” mọi vật liệu. Nguồn và phạm vi chi tiết nằm trong NGUON_KIEM_CHUNG.md.

Hình tạo sinh/mô hình/mặt cắt/màu nhiệt không phải dữ liệu đo, mẫu cổ thật hay tái lập thí nghiệm. Không khe tự khép hai bờ trong một shot, không bê tông nóng chảy, hạt sáng, đồ thị giả hoặc chữa công trình đổ sập.

## Các mốc Actions và phục hồi

- Tài liệu và English: run 44033941869, commit 7a1614ad66f92896df148aa6cf52463d0429224e. Cả hai jobs thành công.
- English job 133872388671 đã tạo và upload MP3 đầy đủ, artifact roman-moi022-voice-en-US. Log: 61.536.000 frames; tempo 0,7933–1,4571; 79 accents. Đã tải public và tự giải mã lại; ENGLISH_PUBLIC_QA.json passed.
- Tài liệu public đã tải và kiểm ZIP/CRC/SHA: DOCUMENT_PUBLIC_DOWNLOAD_QA.json. Link không phụ thuộc workspace.
- 15 nước và xuất gói cuối: run 44036830939, commit a6a39633f5c86b55359d4da5b8db90f09ae082de. Đọc SESSION_PROGRESS.json/trạng thái mới nhất trước khi tiếp tục.
- Job english_ready kiểm run Anh; publisher tải 15 artifact nước trong run hiện tại và EN từ run 44033941869.
- Checkpoint tên roman-moi022-checkpoint-<locale>, artifact hoàn chỉnh roman-moi022-voice-<locale>. Không tạo lại giọng thành công. Nếu một job lỗi, đọc log job đã kết thúc, sửa phần liên quan, giữ toàn bộ audio/artifact còn lại. Không fetch log job đang chạy.
- COUNTRY backend request_adaptive.py dùng cùng giọng, chia nhỏ request khi NoAudio/incomplete; không đổi ID/giọng, không vượt 401/403/429. Metadata từ thật, ghép offset theo mẫu âm thanh.

## Bàn giao cuối

Chỉ nhận đủ 16 voice khi publish_voices.py đã kiểm ID/hash/script/word metadata và giải mã cả 16. Chạy verify_public_delivery.py sau khi manifest stage = all16voices_and_documents_published; nó tải ZIP công khai, kiểm SHA/CRC, giải mã lần nữa từng MP3 và HEAD đủ 16 URL, kiểm 14 TXT/140 prompt/136 timeline/1.282 giây và 5 cặp title-thumbnail.

Lưu báo cáo, nguồn, script, prompt, bản dịch, profile và link vào productions/video-moi022-roman-concrete/; cập nhật trạng thái bộ mới trong research/channel-analysis-20261116/PRODUCTION_STATE.json, giữ lại hoàn tất Upano. Giữ nguyên productions/series/ và danh mục cũ; không tự bắt đầu tập kế tiếp.

Người dùng không tải được link workspace; dùng public GitHub Release. Link cơ sở: https://github.com/seotro95/seotro/releases/download/roman-concrete-moi-022-21m22s/ . Tên file: ROMAN_MOI022_TAI_LIEU_21m22s.zip, ROMAN_MOI022_16_VOICES_21m22s.zip, ROMAN_MOI022_My_Tieng_Anh.mp3, LINK_TAI_VOICE.txt, 5_TIEU_DE_VA_THUMBNAIL.txt. File cuối có 5 tiêu đề và 5 prompt ảnh tương ứng, chưa tạo ảnh.

## Phát hành bản hình lịch sử

Bản voice đang chạy dùng nội dung và checksum ban đầu. Không sửa gói voice hay CUES_MASTER.tsv. build_documents.py áp dụng HISTORICAL_CUE_VISUALS.tsv sau khi xây mốc lời; đã kiểm English script SHA không đổi. Workflow phát hành hình lịch sử sẽ chờ run 44036830939 hoàn tất, tải tài liệu cuối đã kiểm, xây lại 14 TXT/timeline/thumbnail theo hình lịch sử và phát hành lại tài liệu. Nó giữ nguyên cả 16 MP3 và ZIP voice. Chỉ chạy verify_public_delivery.py sau bản historical-context-v2-no-scientists đã phát hành. Có gói riêng ROMAN_MOI022_PROMPT_LICH_SU_14_TXT.zip.
