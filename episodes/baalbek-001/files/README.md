# Baalbek 001 — từ mỏ đá đến nền đền

Bộ sản xuất phim tài liệu **20 phút 42 giây**. Tiếng Anh Andrew là bản chính;
tiếng Việt dùng **Nam Minh**. Có **16 tệp MP3 riêng**, tất cả giọng nam:
Anh, Việt, Tây Ban Nha, Pháp, Nhật, Hàn, Đức, Ý, Bồ Đào Nha, Hà Lan,
Ba Lan, Thụy Điển, Đan Mạch, Phần Lan, Na Uy và Séc.

## Tải và dùng

- `BAALBEK_001_TAI_LIEU_20m42s.zip`: kịch bản Anh–Việt có mốc giờ, lời TXT/SRT/JSON
  của 16 ngôn ngữ, bảng cảnh, nguồn kiểm chứng, phân tích mẫu video,
  5 tiêu đề và 5 prompt thumbnail, hồ sơ giọng và báo cáo kiểm tra.
- `BAALBEK_001_13_TXT_PROMPTS.zip`: 13 TXT prompt video, đánh số liên tục 1–125.
  Mười hai tệp đầu có 10 prompt/tệp; tệp cuối có 5 prompt.
- `BAALBEK_001_16_VOICES_20m42s.zip`: toàn bộ 16 MP3. Các MP3 cũng có thể
  tải riêng theo tên ngôn ngữ tại cùng release GitHub.

## Dựng đúng 20:42

Tạo 125 clip, mỗi clip 10 giây. Dùng đủ clip 1–124; clip 125 chỉ lấy 2 giây
đầu. Tổng là 1.242 giây. Mỗi đoạn lời nằm trong cùng ô 10 giây ở mọi ngôn ngữ;
hai giây cuối không lời. Đặt voice từ 00:00, không tự động bỏ khoảng nghỉ.
Nếu chuyển cảnh chồng lấn, bù phần hình trong cùng ô để không làm ngắn phim.

Mỗi prompt đã ghi riêng hình ảnh, cỡ cảnh và chuyển động máy. Tất cả yêu cầu
không âm thanh, không lời nói và không có trẻ em, kể cả ảnh nền, phản chiếu
hoặc người ở xa. Nhân vật nếu có phải rõ là người trưởng thành 30–60 tuổi.
Loại track âm thanh do công cụ video tự sinh trước khi ghép voice.

Đây là **prompt tạo video và thumbnail**, chưa phải phim hay ảnh đã tạo.
Lời đọc được tạo thật và cung cấp thành tệp âm thanh. Cảnh lịch sử, sơ đồ và
phòng thí nghiệm là minh họa; thêm nhãn phục dựng/mô hình trong phần dựng.
Chữ, bản đồ chính xác và số liệu nên thêm bằng phần mềm dựng, không để AI vẽ chữ.

## Giọng đọc và bản dịch

Đã dùng mã nguồn backend gốc của **Melo-Viet Studio 1.3.1** trên Linux CPU,
cùng các mô hình đã lưu của công cụ. Không chạy giao diện EXE/BAT Windows.
Anh và Việt dùng nhánh Edge; các ngôn ngữ khác dùng Piper hoặc Supertonic
theo hồ sơ. Bản Bồ Đào Nha dùng giọng Bồ Đào Nha châu Âu; Na Uy dùng Bokmål.

Anh dùng adapter chia lô nhỏ với metadata mốc từ của cùng thư viện Edge.
Chỉ chấp nhận lô có toàn bộ metadata khớp lời. Mã giọng, tốc độ và cao độ gốc
được giữ. Tệp mới được tạo từ lời của tập Baalbek, không dùng âm thanh tập cũ.

Lời của từng ngôn ngữ đã được biên tập theo từng đoạn từ kịch bản Anh, chú ý
thuật ngữ và số liệu. Chưa có lượt nghe duyệt toàn bộ bởi người bản ngữ độc lập.
Kiểm tra kỹ thuật không phải chứng nhận phát âm bản ngữ.

Các bản có cùng 29.808.000 mẫu mono, 24 kHz, tương ứng đúng 20:42 sau giải mã.
MP3 có phần đệm bộ mã hóa nên một số trình phát có thể hiển thị dài hơn vài
phần trăm giây. Master FLAC được giữ trong workspace. Không cắt mất từ để ép
thời lượng; đoạn quá dài được biên tập lại rồi tạo giọng lại.

`VOICE_PROFILES_LOCKED.json` lưu mã giọng, mô hình và cấu hình để dùng lại
trong các tập sau. Dịch vụ giọng trực tuyến có thể cập nhật mô hình; không
cam kết mọi tệp tương lai giống hệt dạng sóng hiện tại.

Nguồn công cụ:
https://github.com/seotro95/seotro/releases/tag/melo-viet-studio-1.3.1-txt-srt-41595029816

Nguồn video:
https://github.com/seotro95/seotro/releases/tag/video

Phạm vi quan sát video nguồn và các tài liệu khảo cổ nằm trong
`PHAN_TICH_VIDEO_NGUON.md` và `NGUON_KIEM_CHUNG.md`.
