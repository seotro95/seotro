# Tiếp tục chuỗi video khoa học tiền sử

Repository **seotro95/seotro**, nhánh **codex/beringia-video-01**.

## Trạng thái

- Chủ đề1—Beringia: đã bàn giao tài liệu,17 voice và video tiếng Anh hoàn chỉnh20:00. [Video](https://github.com/seotro95/seotro/releases/download/beringia-video-01-final-20min/BERINGIA_01_EN_FINAL_20m_720p.mp4).
- Chủ đề2—White Sands: đã bàn giao kịch bản3.320 từ,100 prompt/10 TXT,32 ô dùng lại,132 ô timeline và17 voice riêng22:00. [Tài liệu](video-02-white-sands/README.md). Đã bàn giao [video tiếng Anh hoàn chỉnh22:00](https://github.com/seotro95/seotro/releases/download/white-sands-video-02-final-22min/WHITE_SANDS_02_EN_FINAL_22m_720p.mp4), [project dựng](https://github.com/seotro95/seotro/releases/download/white-sands-video-02-final-22min/WHITE_SANDS_02_EDIT_PROJECT.zip),5 tiêu đề và5 promptthumbnail. Chỉ voice Anh, đã bỏ mọi tiếng clip; mở đầu8shot/30giây.
- Chủ đề3—Mal’ta: đã bàn giao kịch bản3.087 từ,100 prompt/10 TXT,20 ô dùng lại,120 ô timeline và17 voice có nhấn nhá, mỗi bản20:00. [Tài liệu](video-03-malta/README.md) · [17 voice](video-03-malta/VOICES/README.md). Chưa dựng video tập3 vì chưa có clip mới của tập này.
- Tiếp theo: **Chủ đề4—Yana: hai chiếc răng nhỏ hé lộ một quần thể người tiền sử.** Chưa bắt đầu.

## Đọc trước khi tiếp tục

1. [Trạng thái và hàng đợi100 chủ đề](series/SERIES_STATE.json)
2. [Danh sách chủ đề](series/TOPICS_001_100.csv)
3. [Quy trình mỗi tập](series/PRODUCTION_RUNBOOK.md)
4. [17 mã giọng cố định](series/VOICE_PROFILES_LOCKED.json)
5. [Phong cách đọc có nhấn nhá](series/NARRATION_STYLE_LOCKED.json)
6. [Phân tích video nguồn](beringia-video-01/PHAN_TICH_VIDEO_NGUON_VA_QUY_TRINH.txt)
7. [Tài liệu và voice tập3](video-03-malta/)

## Yêu cầu giữ nguyên

Làm một chủ đề mỗi lần. Hoàn thiện kịch bản → bàn giaoTXT/prompt/timeline → mới tạo17 voice. Video chính chỉ dùng tiếng Anh. Mặc định20 phút;22 phút là ngoại lệ riêng tập2. Với bối cảnh trùng, ghiREUSE và clip nguồn; mỗiTXT chứa10 prompt mới.

Giữ science-prehistory-17-v1:16 nam, H’Mông nữ3, đúngengine và mẫu tham chiếu. Từ tập3, người dùng yêu cầu tất cả voice có nhấn nhá: dùng science-documentary-expressive-v1 đã lưu; giữ bản sắc giọng, điều chỉnh nhịp/nghỉ/nhấn trong khả năngengine, không chọn lại giọng hoặc gán mô hình cảm xúc không có. Tính lại tốc độ và đo đủ thời lượng cho từng tập, không dùng tốc độ hậu kỳ tập cũ như hằng số. Bản dịch và phương ngữH’Mông Trắng vẫn cần rà soát bản ngữ.

Khi có clip cho một tập: chọn hình phù hợp và cuốn hút nhất cho30 giây đầu, dựng khớp voice Anh, bỏ mọi tiếng clip; bàn giao video, linkvoice,5 tiêu đề và5 promptthumbnail tương ứng. Không ghi nhận video hoàn chỉnh nếu chỉ có prompt và audio.

## Câu nhắn lần sau

> Tiếp tục chủ đề4. Đọc productions/TIEP_TUC_TU_DAY.md trong repository seotro95/seotro, nhánh codex/beringia-video-01, rồi làm theo quy trình đã lưu.

Nếu người dùng muốn dựng tập2 hoặc3 trước, dùng timeline/voice đã xong và clip họ cung cấp cho đúng tập. Các tập1 và2 chưa được tạo lại theo phong cách mới; chỉ thực hiện nếu người dùng yêu cầu rõ.

## Mẫu làm việc đã lưu theo yêu cầu mới

Áp dụng [quy trình tập3](series/QUY_TRINH_AP_DUNG_TU_CHU_DE_03.md) và [cấu hình mặc định](series/PRODUCTION_DEFAULTS.json) cho các chủ đề sau. Khi bàn giao voice, dùng [tên quốc gia](series/VOICE_FILE_NAMING.json), giữ mã giọng bên trong hồ sơ. Đổi tên không tạo lại tiếng; giữ đúng17giọng và phong cách nhấn nhá. Trạng thái tập3 đã hoàn tất tài liệu/voice, tiếp theo là tập4.

