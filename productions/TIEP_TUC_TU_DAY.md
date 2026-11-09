# Tiếp tục chuỗi video khoa học tiền sử

Repository **seotro95/seotro**, nhánh **codex/beringia-video-01**.

## Điểm tiếp tục

- Chủ đề 1 — Beringia: đã bàn giao tài liệu, 17 voice và video tiếng Anh hoàn chỉnh 20:00. [Video](https://github.com/seotro95/seotro/releases/download/beringia-video-01-final-20min/BERINGIA_01_EN_FINAL_20m_720p.mp4).
- Chủ đề 2 — White Sands: đã bàn giao kịch bản tiếng Anh 3.320 từ, 100 prompt trong 10 TXT, 32 ô dùng lại, 132 ô timeline và 17 voice riêng đúng 22:00. [Tài liệu](video-02-white-sands/README.md) · [17 voice](video-02-white-sands/VOICES/README.md). Chưa dựng video tập 2 vì chưa có clip mới của tập này.
- Chủ đề tiếp theo: **3 — Đứa trẻ Mal'ta và mối liên hệ bất ngờ giữa Siberia với tổ tiên người châu Mỹ.** Chưa bắt đầu.
- Giữ profile science-prehistory-17-v1: 16 nam, Hmong nữ 3; không chọn lại ID hoặc mẫu tham chiếu. Bản dịch và phương ngữ Hmong Trắng vẫn cần rà soát bản ngữ.

## Đọc trước khi làm tiếp

1. [Trạng thái và hàng đợi 100 chủ đề](series/SERIES_STATE.json)
2. [Danh sách chủ đề](series/TOPICS_001_100.csv)
3. [Quy trình mỗi tập](series/PRODUCTION_RUNBOOK.md)
4. [Hồ sơ 17 giọng cố định](series/VOICE_PROFILES_LOCKED.json)
5. [Phân tích video nguồn](beringia-video-01/PHAN_TICH_VIDEO_NGUON_VA_QUY_TRINH.txt)
6. [Kịch bản, prompt và voice chủ đề 2](video-02-white-sands/)

## Yêu cầu tiếp tục

Làm từng chủ đề, không tự chạy cả danh sách. Thứ tự: nghiên cứu và hoàn thiện kịch bản → bàn giao TXT, prompt, timeline → mới tạo 17 voice riêng. Video chính chỉ dùng tiếng Anh; các clip tạo sinh im lặng. Giữ nguyên mã giọng, engine và mẫu tham chiếu đã khóa; đo lại thời lượng thực cho từng tập.

Mặc định chuỗi là 20 phút mỗi tập. Chủ đề 2 có ngoại lệ 22 phút theo yêu cầu; không tự áp dụng 22 phút cho tất cả các tập sau. Với các bối cảnh trùng, ghi rõ REUSE và clip nguồn thay vì tạo prompt mới; mỗi TXT chứa 10 prompt mới.

Khi người dùng gửi clip của một tập: chọn những hình phù hợp và hấp dẫn nhất cho 30 giây đầu, dựng khớp voice Anh, bỏ âm thanh clip, rồi bàn giao video, link voice, 5 tiêu đề và 5 prompt thumbnail tương ứng.

## Câu nhắn cho lần sau

> Tiếp tục chủ đề 3. Đọc productions/TIEP_TUC_TU_DAY.md trong repository seotro95/seotro, nhánh codex/beringia-video-01, rồi làm theo quy trình đã lưu.

Nếu người dùng muốn dựng tập 2 trước, tiếp tục từ timeline và voice đã hoàn tất của White Sands, dùng clip họ cung cấp; không thay voice hoặc lấy clip chủ đề 1 làm bằng chứng cho chủ đề 2.
