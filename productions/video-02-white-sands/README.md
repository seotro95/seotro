# Chủ đề 2 — White Sands, 22 phút

**White Sands: The Footprints That Changed America's Timeline**

Đã bàn giao kịch bản tiếng Anh gốc 3.320 từ và 17 audio riêng, mỗi bản đo đúng 22:00 sau giải mã. Video chính chỉ dùng voice tiếng Anh. Đã xuất và kiểm tra bản dựng hoàn chỉnh 22:00 từ 98 clip người dùng cung cấp; chỉ giữ giọng đọc tiếng Anh gốc.

## Tải tài liệu và voice

- [ZIP kịch bản, prompt và hướng dẫn](https://github.com/seotro95/seotro/releases/download/white-sands-video-02-22min/WHITE_SANDS_VIDEO_02_TAI_LIEU_22_PHUT.zip)
- [Kịch bản tiếng Anh](KICH_BAN_EN_22_PHUT.txt) · [132 mốc lời](KICH_BAN_EN_CO_MOC.txt)
- [100 prompt: 10 TXT, đúng 10 prompt mỗi tệp](PROMPTS/)
- [Timeline 132 cảnh](TIMELINE_132_CANH.csv) · [32 vị trí REUSE, không tạo clip mới](CANH_DUNG_LAI_KHONG_TAO_MOI.csv)
- [Kế hoạch 8 shot trong 30 giây mở đầu](HOOK_30_GIAY_8_SHOT.csv)
- [Một ZIP đủ 17 voice](https://github.com/seotro95/seotro/releases/download/white-sands-video-02-22min/WHITE_SANDS_02_17_VOICES_22m.zip)
- [Bảng tải riêng từng voice](VOICES/README.md) · [Báo cáo và bản dịch](https://github.com/seotro95/seotro/releases/download/white-sands-video-02-22min/WHITE_SANDS_02_VOICE_DETAILS.zip)
- [Hồ sơ 17 giọng cố định](VOICES/VOICE_PROFILES_LOCKED.json) · [Mã kiểm tra audio](VOICES/AUDIO_MANIFEST.json)

## Dựng hình

Kế hoạch prompt gốc gồm 132 ô timeline, mỗi ô 10 giây, dự kiến 100 clip riêng. Bản dựng hoàn chỉnh chọn 66 clip phù hợp từ 98 clip đã nhận và bổ sung 15 sơ đồ; các vị trí sử dụng thực tế nằm trong EDIT/EDIT_TIMELINE.csv. Đặt tên clip WS02_001.mp4 đến WS02_100.mp4; số clip khác số cảnh timeline. 32 ô REUSE đã ghi rõ clip nguồn. Mỗi prompt tạo một cảnh liên tục 10 giây, không âm thanh; loại bỏ mọi âm thanh clip khi dựng. Kế hoạch hook thay cách đặt hình trong 30 giây đầu, không nối thêm thời gian vào voice.

Tham khảo [phân tích cách kể và dựng video nguồn](PHAN_TICH_NGUON_VA_QUY_TRINH.txt). Nhãn địa danh, niên đại và chú thích khoa học thêm khi edit. Hình tạo sinh là minh họa, không trình bày như ảnh khai quật gốc. [Bản đồ tham chiếu](REFERENCES/MAP_REFERENCE_NORTH_AMERICA.png) dùng đường bờ hiện đại để định hướng, không phải bờ biển cổ được tái dựng chính xác.

## Kiểm tra voice

16 giọng nam dùng backend online của Melo-Viet-Studio 1.3.1, giữ đúng ID tập 1. Hmong nữ 3 được tạo bằng Voice-Studio-Hmong 1.6.6 Native VITS + OpenVoice V2 với mẫu tham chiếu đã khóa. Từng MP3 được đo đúng 1.320 giây sau giải mã, tương ứng 63.360.000 mẫu ở 48 kHz. Tiếng Anh căn 132 ô 10 giây; bản dịch căn 12 chương 110 giây, không căn từng từ với tiếng Anh. Tốc độ hậu kỳ được tính lại cho từng tập.

Bản dịch đã sửa những lỗi thuật ngữ được phát hiện nhưng vẫn cần người bản ngữ đọc/nghe rà soát. Phương ngữ Hmong Trắng chưa được xác nhận độc lập. ZIP tài liệu gốc là bản chụp thời điểm bàn giao trước khi tạo voice; hồ sơ voice hoàn tất nằm trong VOICES và release.

Tập 3 đã hoàn tất tài liệu và voice; hàng đợi tiếp theo vẫn là chủ đề 4. Lượt này chỉ dựng video tập 2. Mục tiêu 22 phút là yêu cầu riêng của tập 2.


## Video hoàn chỉnh

- [Tải video 22:00, 720p/24fps](https://github.com/seotro95/seotro/releases/download/white-sands-video-02-final-22min/WHITE_SANDS_02_EN_FINAL_22m_720p.mp4)
- [Xem đoạn mở đầu 30 giây](https://github.com/seotro95/seotro/releases/download/white-sands-video-02-final-22min/WHITE_SANDS_02_OPENING_30s.mp4)
- [Project dựng, code, đồ hoạ và hồ sơ nguồn](https://github.com/seotro95/seotro/releases/download/white-sands-video-02-final-22min/WHITE_SANDS_02_EDIT_PROJECT.zip)
- [5 tiêu đề và 5 prompt thumbnail](https://github.com/seotro95/seotro/releases/download/white-sands-video-02-final-22min/TITLES_AND_THUMBNAIL_PROMPTS.txt)
- [Báo cáo QA](https://github.com/seotro95/seotro/releases/download/white-sands-video-02-final-22min/FINAL_VIDEO_QA.json) · [Timeline dựng](EDIT/EDIT_TIMELINE.csv)

Đoạn mở đầu dùng 8 shot trong đúng 30 giây của voice. Không nhạc, không hiệu ứng âm thanh, không tiếng gốc của clip. Phụ đề tiếng Anh có thể bật/tắt. Sơ đồ định tuổi và bản đồ được biên tập riêng khi hình tạo sinh sai hoặc không phù hợp. Mọi hình tái dựng đều là minh hoạ. Chi tiết kỹ thuật và SHA256 nằm trong project/QA.
