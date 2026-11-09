# Tiếp tục chuỗi video khoa học tiền sử

Dự án đã lưu trong repository **seotro95/seotro**, nhánh **codex/beringia-video-01**.

## Điểm tiếp tục

- Chủ đề 1, **Beringia**, đã bàn giao tài liệu, 17 tệp voice và video tiếng Anh hoàn chỉnh **20:00**; bản dựng đã vượt qua kiểm tra kỹ thuật.
- Đang thực hiện: **Chủ đề 2 — White Sands**, theo yêu cầu mới dài **22 phút**. [Kịch bản, 100 prompt và 32 cảnh dùng lại](video-02-white-sands/README.md) đã bàn giao. [Tạo 16 giọng nam trên GitHub](https://github.com/seotro95/seotro/actions/runs/42685972541) đang chạy; Hmong nữ 3 được tạo bằng tool Native riêng.
- Sau đó: **Chủ đề 3 — Đứa trẻ Mal'ta và mối liên hệ bất ngờ giữa Siberia với tổ tiên người châu Mỹ.**
- Chủ đề 2 đã có 3.320 từ tiếng Anh, 132 ô lời 10 giây, 12 chương 110 giây và mục tiêu 17 audio riêng, mỗi bản 1.320 giây. Giữ đúng profile giọng tập 1. Chủ đề 3 chưa bắt đầu.
- [Tải video hoàn chỉnh](https://github.com/seotro95/seotro/releases/download/beringia-video-01-final-20min/BERINGIA_01_EN_FINAL_20m_720p.mp4) · [Tải một ZIP đủ 17 giọng](https://github.com/seotro95/seotro/releases/download/beringia-video-01-final-20min/BERINGIA_01_17_VOICES.zip) · [Hồ sơ dựng, tiêu đề và prompt thumbnail](beringia-video-01/EDITING/README.md).
- Bản dựng: 720p/24 fps, 190 đoạn hình, 6 chuyển cảnh hòa ngắn; 30 giây đầu gồm 8 cảnh. Âm thanh clip đầu vào đã được bỏ, giữ voice tiếng Anh, có phụ đề tùy chọn và 12 chương.
- Mỗi lần có clip cho tập mới: ưu tiên dựng kỹ 30 giây đầu, khớp voice tiếng Anh, bỏ âm thanh clip, rồi bàn giao link video/voice và 5 tiêu đề với 5 prompt thumbnail.
- Các bản dịch vẫn cần được người bản ngữ rà soát. Phương ngữ Hmong Trắng chưa được xác nhận độc lập; giữ đúng trạng thái này khi báo cáo.

## Đọc trước khi làm tiếp

1. [Trạng thái và hàng đợi 100 chủ đề](series/SERIES_STATE.json)
2. [Danh sách chủ đề dạng CSV](series/TOPICS_001_100.csv)
3. [Quy trình thực hiện cho mỗi tập](series/PRODUCTION_RUNBOOK.md)
4. [Hồ sơ 17 giọng cố định](series/VOICE_PROFILES_LOCKED.json)
5. [Phân tích video tham chiếu](beringia-video-01/PHAN_TICH_VIDEO_NGUON_VA_QUY_TRINH.txt)
6. [Tài liệu và voice chủ đề 1](beringia-video-01/)
7. [Bảng tải 17 voice chủ đề 1](beringia-video-01/VOICES/README.md)

## Yêu cầu giữ nguyên cho các tập sau

Làm từng chủ đề theo danh sách. Video chính tiếng Anh, mục tiêu 20 phút. Mỗi tập có 120 đoạn lời và 120 clip nguồn 10 giây; prompt chia 12 TXT, đúng 10 prompt mỗi TXT, đánh số liên tục 001–120. Clip tạo sinh không cần âm thanh. Chọn hành động và góc máy phù hợp từng cảnh.

Thứ tự người dùng yêu cầu: **hoàn thiện kịch bản → bàn giao TXT và prompt → rồi mới tạo voice**. Không cần tự thêm một bước xin phép, trừ khi thiếu thông tin thực sự hoặc người dùng yêu cầu duyệt trước.

Giữ 16 giọng nam và Hmong nữ. Dùng đúng mã giọng, ngôn ngữ, engine và mẫu tham chiếu trong hồ sơ cố định; không tự chọn lại từ đầu.

## Câu nhắn để tiếp tục ở lần sau

> Tiếp tục chủ đề 2. Đọc productions/TIEP_TUC_TU_DAY.md trong repository seotro95/seotro, nhánh codex/beringia-video-01, rồi làm theo quy trình đã lưu.

Nếu mở cuộc trò chuyện mới, đưa kèm đường dẫn tệp này để trợ lý đọc lại trạng thái từ GitHub. Tệp lưu trữ là nguồn tiếp nối công việc; không phụ thuộc vào việc trợ lý tự nhớ cuộc trò chuyện cũ.


## Ngoại lệ thời lượng cho chủ đề 2

Theo yêu cầu mới, chủ đề 2 dài 22 phút: 132 mốc lời, 100 prompt mới trong 10 TXT, 32 vị trí REUSE không tạo clip trùng. Tiếng Anh là voice duy nhất của video chính; các ngôn ngữ khác xuất thành audio riêng. Không tự đổi mọi tập sau sang 22 phút.
