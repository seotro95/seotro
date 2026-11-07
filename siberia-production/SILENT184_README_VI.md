# 184 prompt Muse có góc quay — Siberia 25:36

Đây là bộ prompt và kế hoạch dựng theo bản voice tiếng Anh đã chốt. Chưa có clip Muse hay video hoàn chỉnh trong gói. Bộ này thay kế hoạch 227 cảnh khi tạo từng clip 10 giây.

## Số lượng đã tính

- 25:36 = **1.536 giây**; 1.536 / 10 = 153,6 → **154 clip là mức tối thiểu lý thuyết**. Nếu ghép nguyên theo lưới này, dùng 153 clip trọn 10 giây và 6 giây của clip cuối; nhiều clip sẽ vượt qua ranh giới đoạn voice.
- Tách riêng theo 59 đoạn voice cần tổng `ceil(thời lượng đoạn / 10)` = **182 clip**.
- Đoạn mở đầu đầu tiên gọi tên bốn hình khác nhau; dùng 4 clip thay vì 2 → **184 prompt được chọn**.
- Tạo 184 × 10 giây = **30:40** nguồn. Chỉ dùng phần ghi trong bảng, bỏ **5:04**, còn **25:36**. Không ghép nguyên 184 clip.
- **19 bộ**, mỗi bộ 10 prompt; bộ 19 chỉ bật 4 ô. Mỗi prompt tạo đúng một clip 10 giây.

## Chạy trong Muse AI Studio 1.6.0

1. Giải nén toàn bộ ZIP. Mở `MUSE_184_STORYBOARD_VI.txt` để xem lời Anh, nghĩa Việt, hình cần tạo, góc máy, tiêu cự, diễn tiến và mốc cắt của từng cảnh.
2. Chọn Video từ văn bản, tỉ lệ 16:9, thời lượng 10 giây, đầu ra yêu cầu 1080p. Có thể giữ model đang tạo được clip 10 giây trên máy bạn; JSON gợi ý Omni 1.1 Flash. Thông số thực tế phụ thuộc model.
3. Mở `batches/video-01.txt`, dán lần lượt mỗi đoạn vào một ô Muse. Một đoạn đầy đủ bắt đầu bằng “Create one continuous…” và kết thúc bằng yêu cầu AUDIO. Không dán tên cảnh/mốc thời gian từ storyboard vào prompt.
4. Nếu bản Muse của bạn nhập được dự án định dạng version 1, dùng `batches/video-01.json`. JSON được lập theo mẫu dự án của Muse đã có; chưa thử nhập trên máy Windows của bạn. TXT dùng được khi không nhập JSON.
5. Tải và đổi tên theo thứ tự `0001.mp4` … `0184.mp4`. Tiếp tục đến bộ 19. Kiểm tra clip thật đủ thời lượng, đúng hình và chuyển động; clip lỗi cần tạo lại trước khi dựng.

## Góc máy và sự liên tục

Mỗi clip có **một góc máy liên tục**, không cắt nội bộ. Bộ prompt đã chọn cỡ cảnh, góc nhìn, tiêu cự tương đương và chuyển động riêng. Nhịp chung: 0–2 giây thấy ngay chủ thể; 2–8 giây chuyển máy nhẹ hoặc mô phỏng một quá trình; 8–10 giây giữ khung. Với cảnh dùng ngắn, cắt đúng phần nguồn được ghi; không chờ đến cuối clip mới cho xuất hiện ý chính.

- Dùng đại cảnh nhìn chéo cho cấu trúc địa hình; góc gần vuông 90° cho vòng băng/hình dạng trên mặt đất.
- Dùng cận/đặc tả cho mẫu đá, vòng cây, băng, đất than bùn; giữ rõ kết cấu.
- Khối đá Hanging Stone cần thấy cả khối đá và điểm tựa, không cho đá rung hoặc rơi.
- Belukha ưu tiên máy ổn định, để mây và ánh sáng chuyển động. Sơ đồ khoa học dùng máy trực giao cố định.
- Không đổi mùa/ánh sáng đột ngột giữa các cảnh cùng địa danh. Khi chọn được ảnh đẹp cho địa danh, dùng ảnh đó làm tham chiếu cho các cảnh tiếp nếu model hỗ trợ. Cảnh chuyển địa danh đã ghi chủ thể mới ngay trong prompt.

Đây là yêu cầu sáng tạo cho model, không phải thông số máy quay đo từ video gốc. Hình tạo sinh cần đối chiếu địa danh với nguồn tham khảo; sơ đồ và cảnh tái dựng là minh họa, không phải dữ liệu đo hay tư liệu lịch sử. Khi dựng, ghi nhãn “AI VISUALISATION”, “SCHEMATIC” hoặc “RECONSTRUCTION” thích hợp, bằng phần mềm dựng.

## Tắt toàn bộ tiếng của clip

Mọi prompt đều yêu cầu **VIDEO ONLY, ABSOLUTELY SILENT** và không tạo track âm thanh. Model vẫn có thể xuất kèm tiếng; yêu cầu trong prompt không đảm bảo file không có audio.

Cách nhanh: trong phần mềm dựng, tắt/mute mọi track tiếng gắn với clip Muse, chỉ bật track voice riêng. Không mute track voice của bạn.

Cách xuất clip thật sự không có audio:

1. Đặt các clip gốc vào thư mục `clips` cạnh file `TAT_TIENG_CLIP.cmd` (tạo thư mục nếu chưa có).
2. Mở Muse AI Studio trước, rồi chạy `TAT_TIENG_CLIP.cmd`. Công cụ dùng Node.js 22+ nếu có; nếu chưa có, nó thử runtime Electron của ứng dụng Muse đang mở. Nếu runtime Muse không chạy script được, cài Node.js chính thức: https://nodejs.org/en/download rồi chạy lại.
3. Công cụ tìm FFmpeg/FFprobe sẵn có. Nếu chưa có trên Windows, nó tải bản FFmpeg upstream đã ghim SHA-256 (~202 MB), giải nén và giữ cả gói giấy phép. Lần đầu cần mạng; lần sau dùng lại.
4. Lấy clip trong thư mục **SILENT** để dựng. File gốc được giữ nguyên. Video được chép luồng, không mã hóa lại; mọi đầu ra được kiểm tra không còn audio stream. Báo cáo ở `SILENT/SILENCE_REPORT.json`.

Lệnh tương đương khi đã có FFmpeg: `ffmpeg -i input.mp4 -map 0:v:0 -c:v copy -an -sn -dn output.mp4`.

## Dựng khớp voice

1. Tạo timeline **30 fps**, 16:9, 1920×1080 nếu clip cho phép. Đặt `en.wav` hoặc bản phối `Siberia_EN_FINAL_MIX_25m36.wav` vào đầu 00:00.
2. Dùng `MUSE_184_TIMELINE.csv`: `source_in_seconds` / `source_out_seconds` là phần cắt trong clip; `timeline_start_30fps` / `timeline_end_30fps` là vị trí đặt. Mốc frame có dạng giờ:phút:giây:frame, không phải mili giây.
3. Ghép cắt thẳng theo bảng. Không chồng các clip bằng dissolve rồi làm ngắn timeline. Nếu thêm chuyển cảnh, giữ đúng các mốc đã ghi và kiểm tra phần dư của clip.
4. Mọi mốc hình đều liền nhau, không khe hở; toàn phim **46.080 frame = 25:36**. Cue voice đã kiểm tra theo 59 đoạn; sai số làm tròn ranh giới hình tối đa 1/2 frame. **Chưa căn từng từ**; xem và nghe từng cảnh để chỉnh điểm cắt nhỏ nếu hình cần xuất hiện đúng một từ cụ thể.
5. Dùng `en.srt` để đối chiếu lời. Không kéo giãn tốc độ track voice đã chốt. Nếu chỉnh cắt bên trong một đoạn, giữ nguyên đầu/cuối đoạn để các phần sau vẫn khớp.

Voice gốc được đối chiếu SHA-256: `31ddc272cb789f24e5a383159c5674918bc3562e1c9da088f3f28385ed943c68`. Nếu dùng bản voice khác lời hoặc khác mốc, bảng này phải căn lại.

## Các tệp chính

- `MUSE_184_SILENT_PROMPTS.txt`: toàn bộ 184 prompt thuần, theo thứ tự.
- `MUSE_184_STORYBOARD_VI.txt`: lời voice + nghĩa Việt + góc quay + nhịp 10 giây + mốc cắt + prompt đầy đủ.
- `MUSE_184_TIMELINE.csv`: 184 dòng để dựng và theo dõi file.
- `shot_plan_184.json`: kế hoạch với toàn bộ mốc frame và cấu hình máy quay.
- `batches/video-01.txt` … `video-19.txt` và JSON cùng tên: từng bộ để nhập Muse.
- `en.srt`, `en-report.json`, `MUSE_184_QA.json`: mốc lời và kết quả đối chiếu.
- `CONTENTS_SHA256SUMS.txt`: kiểm tra nguyên vẹn các tệp bên trong gói.

Các giọng ngôn ngữ khác có cùng tổng thời lượng và mốc 59 đoạn. Các bản dịch có thể đảo thứ tự từ; cần nghe lại nếu muốn hình xuất hiện khớp từng từ ở từng ngôn ngữ.
