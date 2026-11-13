# Hướng dẫn dựng — tập 85 Angkor — 21:32

## Thời lượng và số clip

**129 đoạn × 10 giây + 2 giây kết = 1.292 giây = 21:32.** Có 100 clip cần tạo, mỗi clip 10 giây; 29 ô dùng lại clip đã có; ô cuối giữ khung hình kết 2 giây. Tổng: 1.000 + 290 + 2 = 1.292 giây.

Bộ giao gồm **10 TXT**, mỗi TXT đúng 10 prompt, số liên tục 1–100. Đây là số lượng đã đổi theo yêu cầu mới của người dùng. Bỏ prompt trùng không có nghĩa xóa ô dùng lại khỏi timeline.

Đặt tên `clip-001.mp4` đến `clip-100.mp4`. `BANG-TINH-130-DOAN.md`, `scene-voice-edit.csv` và `shot-reuse-map.json` chỉ rõ mã clip ở từng ô. Ô 129 chạy 21:20–21:30. Ô 130 chạy 21:30–21:32, giữ khung hình cuối của clip dùng ở ô 129; không cần tạo thêm prompt.

## Thao tác dựng

1. Tạo 100 clip theo 10 TXT. Kiểm tra toàn bộ khung hình: không trẻ em, thiếu niên, hình người nhỏ, âm thanh hay lời nói.
2. Tạo sequence 16:9 dài đúng 21:32, chọn 25 hoặc 30 fps để chia tròn cả 10 giây và 2 giây kết.
3. Điền 129 ô 10 giây theo bảng. Các ô ghi dùng lại giữ đủ 10 giây. Có thể thay crop nhẹ khi nguồn đủ nét, giữ nguyên bối cảnh và hướng địa lý.
4. Dùng cắt thẳng ở mốc đã tính. Chuyển mềm nằm trong ô, không cộng thêm thời gian vào cuối. Có thể cắt từ toàn cảnh sang crop chi tiết trong cùng clip để tăng nhịp.
5. Xóa hoặc tắt mọi âm thanh do mô hình video sinh ra. Đặt một MP3 ngôn ngữ tương ứng từ 00:00; các track còn lại là phương án thay thế, không nối sau bản Anh.
6. Dùng SRT đúng ngôn ngữ. Có 129 cue, kết ở 21:30; 2 giây cuối là khoảng kết không lời. Đặt điểm xuất cuối ở 21:32.

Mỗi MP3 được giải mã đúng **31.008.000 mẫu ở 24 kHz = 1.292 giây**. Một số trình đọc metadata có thể hiện thêm vài mili giây do khung mã hóa MP3; không kéo giãn lại voice vì phần sai khác hiển thị này.

## Cấu trúc và nhịp kể

- 00:00–02:40: vệt nước, đền và đô thị rộng hơn.
- 02:40–05:20: mùa mưa, mùa khô, địa hình, Tonle Sap và dòng chảy.
- 05:20–08:00: baray, cửa vào/ra, trầm tích và công năng.
- 08:00–10:40: mạng lưới, nút giao và chiều thời gian.
- 10:40–13:20: hộ gia đình, ruộng, lao động, vật liệu và sự tiếp nối.
- 13:20–16:00: lidar, khảo sát, trầm tích và bằng chứng khí hậu.
- 16:00–18:40: hạn, mưa mạnh, áp lực mạng lưới và thay đổi chính trị.
- 18:40–21:30: di sản sống, bảo tồn và trở lại vệt nước.
- 21:30–21:32: giữ khung hình kết, không lời.

Học từ nguồn cách bắt đầu bằng vật chứng nhỏ, mở câu hỏi lớn, xen cảnh rộng với cận chi tiết rồi quay về hình đầu. Lời được viết mới. Mỗi clip gợi ý 2 giây thiết lập, 6 giây phát triển, 2 giây ổn định. Không cần sao chép mọi nhát cắt của nguồn.

## Hình minh họa và giọng

Thêm nhãn biên tập phù hợp, chẳng hạn “Illustrative model”, cho mô hình địa hình, dòng chảy và cảnh quan quá khứ. Prompt không yêu cầu mô hình tự viết chữ. Không dùng hình minh họa làm ảnh khảo sát thực hoặc dựng một sự kiện hủy diệt đã được chứng minh.

Giữ nguyên `VOICE_PROFILES.json` cho tập sau: Andrew, Nam Minh và các model/preset nam đã lưu; ngoại lệ H’Mông Trắng nữ female-3. Dùng backend Python của Melo-Viet Studio 1.3.1 và Voice Studio Hmong 1.6.6 trên Linux cloud, không chạy Windows EXE.

Bộ giao có kịch bản, SRT, MP3, prompt, hồ sơ giọng và bảng dựng. Chưa chứa 100 clip được sinh hoặc phim MP4 dựng hoàn chỉnh. Lời dịch và phát âm chưa được duyệt toàn bộ bởi người bản ngữ.
