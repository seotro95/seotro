# Kailasa 007 — 22:32

Bộ sản xuất tài liệu: **Kailasa — Làm thế nào tạc một ngôi đền từ khối núi?** Cave 16, Ellora, Ấn Độ.

- **136 prompt video im lặng**, đánh số 1–136, trong **14 TXT**: 13 tệp × 10 prompt và tệp cuối 6 prompt.
- 135 clip đầu dùng đủ 10 giây; clip cuối tạo 10 giây, dùng hai giây đầu. Tổng đúng **22:32**.
- Kịch bản chính Anh, bản Việt đối chiếu; đủ lời TXT/SRT/JSON cho **16 ngôn ngữ**.
- **16 MP3 giọng nam riêng**, mỗi bản có thời lượng giải mã **1.352 giây**. Anh **Andrew**, Việt **Nam Minh**. Các giọng còn lại: Tây Ban Nha, Pháp, Nhật, Hàn, Đức, Ý, Bồ Đào Nha, Hà Lan, Ba Lan, Thụy Điển, Đan Mạch, Phần Lan, Na Uy và Séc.
- Lưu `VOICE_PROFILES_LOCKED.json` để dùng lại đúng mã giọng, locale và các model hash.
- **5 tiêu đề và 5 prompt thumbnail** có cặp Anh–Việt, khớp nội dung tập.
- Phân tích tham chiếu, hướng dẫn dựng, nguồn khảo cổ, bảng thời lượng và báo cáo kiểm tra kỹ thuật.

## Tải gói

1. `KAILASA_007_TAI_LIEU_22m32s.zip`: toàn bộ kịch bản, prompt, SRT, nguồn, bảng dựng, tiêu đề/thumbnail và cấu hình giọng.
2. `KAILASA_007_14_TXT_PROMPTS.zip`: chỉ 14 TXT prompt.
3. `KAILASA_007_16_VOICES_22m32s.zip`: 16 MP3 và SHA-256; hoặc tải MP3 từng quốc gia bên dưới.

Mọi prompt yêu cầu không có trẻ em, bao gồm tượng/phù điêu và phản chiếu, và không có âm thanh/lời nói. Người dựng cần kiểm tra hình thực tế sau khi tạo. Chưa tạo video hoặc ảnh thumbnail trong gói này.

Kịch bản đi theo phần đá phải giữ và phần phải lấy đi; trình tự chi tiết là mô hình giải thích có nhãn. Không dùng tổng tấn đá, số thợ hoặc số năm lan truyền làm dữ kiện chắc chắn. Hai phép tính 2,8 và 280 tấn là ví dụ giả định, không phải đo di tích.

Âm thanh được tạo mới bằng backend nguồn Melo-Viet-Studio 1.3.1 trên Linux, không chạy EXE/BAT Windows. Đã đối chiếu lời cuối, số cue, waveform, thời lượng giải mã và checksum cho 16 bản. Có kiểm tra ASR bổ trợ trên một số cue Anh/Việt; **chưa có vòng nghe toàn bộ độc lập bởi người bản ngữ cho cả 16 bản**. Đây là bản nháp sản xuất để nghe duyệt trước phát hành.

Đây là **draft release**, chủ tài khoản cần đăng nhập GitHub để tải. Các file tải lên được kiểm tra dung lượng và SHA-256 phía GitHub; xem `GITHUB_DELIVERY_VERIFIED.json`.
