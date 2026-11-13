# Dựng tập 36 — Nan Madol — 22:18

Video chính dùng tiếng Anh Andrew. Các MP3 ngôn ngữ khác là những lựa chọn lồng tiếng riêng, không xếp nối nhau.

1. Tạo clip 20 giây từ prompt 1–67, giữ thứ tự. Mỗi TXT có 10 prompt. Prompt 68–70 chỉ dự phòng.
2. Dùng đầy đủ 20 giây cho cảnh 1–66, lấy 18 giây đầu cảnh 67. Tổng chính xác 1.338 giây.
3. Cue lời 1–133 dài 10 giây, cue 134 dài 8 giây. Mỗi cảnh hình chứa hai cue liên tiếp. Bảng `scene-voice-edit.csv` có timecode và lời Anh, Việt.
4. Dùng cắt thẳng hoặc transition nằm trong ô; không tự trừ thời lượng do chồng clip. Đầu và cuối không thêm logo hay intro ngoài timeline.
5. Loại âm thanh mọi clip tạo sinh, ví dụ bằng FFmpeg `-an`. Ghép một MP3 ngôn ngữ đã chọn từ giây 0. Phụ đề lấy đúng SRT của ngôn ngữ đó.
6. Cảnh kết đã có lời trong 8 giây cuối. Nếu fade hình, giữ fade bên trong 22:16–22:18. Không cắt câu cuối hoặc thêm khoảng đen sau 22:18.

Mọi hình tạo sinh cần kiểm tra: không trẻ em kể cả nền xa; người rõ ràng trưởng thành; không chuyển động môi; không chữ/logo sai; đá có trọng lực, nền có thực; không tưởng tượng cung điện chìm, người ngoài hành tinh hoặc mở mộ.

Âm thanh bàn giao là narration sạch, không nhạc. Chuẩn kỹ thuật: mono 24 kHz, MP3 96 kbps, master FLAC PCM16; cân âm hai lượt theo mục tiêu -18 LUFS, -2 dBTP. Tốc độ được chỉnh giữ cao độ để nằm trong cue, không cắt từ để ép thời lượng. Các khoảng nghỉ giữ nhịp cảnh. MP3 có thể hiển thị dư vài phần nghìn giây ở phần container do khung mã hóa; số mẫu giải mã là tiêu chí thời lượng phát chính xác.

Lưu `VOICE_PROFILES.json` cho tập sau: dùng đúng ID, model hash, preset và mẫu nữ H’Mông, thay kịch bản và thời lượng theo tập. Andrew và Nam Minh là giọng Microsoft trực tuyến nên máy chủ có thể cập nhật âm sắc theo thời gian. Bản Linux gọi backend Python thật đi kèm hai công cụ của người dùng, không giả rằng đã chạy EXE Windows.
