# 007 — Kailasa: Làm thế nào tạc một ngôi đền từ khối núi?

Bộ sản xuất phim tài liệu **22:32**, bản dựng chính tiếng Anh. Địa điểm: **Kailasa, Cave 16, Ellora, Maharashtra, Ấn Độ**. Câu chuyện theo quá trình lấy bỏ vật liệu: chừa phần cần giữ, mở lối tiếp cận, tạc từ phần cao xuống, khoét không gian bên trong và đưa đá vụn ra ngoài.

## Tệp dùng ngay

- `KICH_BAN_ANH_22m32s.txt`: lời chính tiếng Anh, có số đoạn và mốc thời gian.
- `KICH_BAN_VIET_22m32s.txt`: bản Việt đối chiếu.
- `scripts/{mã ngôn ngữ}/voice.txt`, `voice.srt`, `cues.json`: đủ 16 bản lời và phụ đề.
- `prompts/`: **14 TXT, đủ 136 prompt**, số liên tục 1–136. Mười prompt mỗi tệp; tệp cuối có sáu prompt. `KAILASA_007_ALL_136_PROMPTS.txt` gộp toàn bộ.
- `SCENE_VOICE_EDIT.csv`: ghép từng lời, hình, thời lượng và ghi chú dựng.
- `5_TIEU_DE_VA_5_THUMBNAIL.txt`: năm cặp tiêu đề Anh–Việt và năm prompt thumbnail tương ứng.
- `VOICE_PROFILES_LOCKED.json`: lưu chính xác các giọng nam và mã mô hình để dùng lại.
- `VOICE_QA.json`, `DOI_CHIEU_THOI_LUONG_16_VOICE.csv`, `validation/`: kết quả kiểm tra tệp âm thanh thực tế.
- `NGUON_KIEM_CHUNG.md`, `PHAN_TICH_VIDEO_NGUON.md`, `BIEN_TAP_VA_KIEM_CHUNG.md`: nguồn, phương pháp và phạm vi kiểm tra.

Gói âm thanh riêng gồm **16 MP3**, mỗi ngôn ngữ một tệp. Tiếng Anh dùng **Andrew**; tiếng Việt dùng **Nam Minh**. Các ngôn ngữ còn lại: Tây Ban Nha, Pháp, Nhật, Hàn, Đức, Ý, Bồ Đào Nha, Hà Lan, Ba Lan, Thụy Điển, Đan Mạch, Phần Lan, Na Uy Bokmål và Séc. Bồ Đào Nha dùng biến thể Portugal; Tây Ban Nha dùng es-ES. Tất cả là giọng được nhà cung cấp hoặc model card ghi là nam.

## Dựng đúng 22:32

1. Tạo 136 clip bằng các prompt, mỗi clip nguồn **10 giây**, theo thứ tự số. Prompt chỉ định góc máy riêng cho mỗi hình.
2. Dùng đủ 10 giây của clip 1–135: **135 × 10 = 1.350 giây**. Dùng **hai giây đầu** clip 136: tổng **1.352 giây = 22:32**. Phần thừa tám giây của clip cuối không vào bản dựng.
3. Đặt MP3 tiếng Anh từ 00:00. Mỗi bản ngôn ngữ có cùng 135 ô lời 10 giây và hai giây kết im lặng. Đổi ngôn ngữ bằng cách thay tệp voice tại cùng mốc bắt đầu; dùng SRT đúng ngôn ngữ.
4. Các clip tạo bằng AI phải **không có âm thanh và lời nói**. Thêm voice trong phần mềm dựng. Nhạc, nếu tự chọn sau này, cần quyền sử dụng và không được lấn lời.
5. Chữ, bản đồ chính xác, ký hiệu lực, số đo và nhãn “mô hình giả định” thêm trong phần mềm dựng; không nhờ AI vẽ chữ. Phép tính cảnh 63–64 chỉ là ví dụ giả định, không phải đo khối lượng ngôi đền.
6. Mặc định cắt tại mốc cue. Nếu dùng chuyển cảnh, chồng hình trong cùng độ dài timeline; không nối thêm thời gian. Đoạn fade cuối nằm trong 22:30–22:32.

Mọi prompt đều ghi **không trẻ em**, áp dụng cả người sống, nền xa, ảnh, phản chiếu, phù điêu, tượng và thần linh dạng trẻ nhỏ. Người sống xuất hiện phải rõ là người trưởng thành 30–60 tuổi. Nếu hình di tích có nhân vật điêu khắc trẻ, đổi khuôn hình sang phần kiến trúc khác; không bóp méo di sản để xóa nhân vật. Kiểm tra lại hình xuất vì prompt không bảo đảm mô hình tuân thủ tuyệt đối.

## Nhận diện hình và mức chắc chắn

`PRESENT` là minh họa phong cách tư liệu hiện tại; `RECON` là phục dựng giả định Deccan thế kỷ VIII; `DIAGRAM` là mô hình giải thích; `LAB` là minh họa khảo sát/thử nhỏ. Chúng không phải cảnh quay khảo cổ xác thực, ảnh đo đạc mới hay thí nghiệm đã thực hiện tại Kailasa. Dùng ảnh tham chiếu đúng Cave 16; không trộn với Little Kailasa, Cave 30.

Không đưa tổng trọng lượng đá bị bỏ, số công nhân hay số năm hoàn thành thành dữ kiện chắc chắn. Không có bản nhật trình công trường đầy đủ trong nguồn dùng ở đây. Nguyên tắc từ trên xuống và logic chừa đá không cung cấp thứ tự của từng nhát đục.

## Âm thanh và dùng lại giọng

Âm thanh được tổng hợp mới từ bản lời Kailasa bằng **backend nguồn của Melo-Viet-Studio 1.3.1** trên Linux với mô hình đã kiểm tra. Không chạy bản Windows EXE/BAT. Căn cứ nguồn và mã backend trong `TOOL_PROVENANCE.json`.

Mỗi bản có 32.448.000 mẫu âm thanh ở 24 kHz mono, tương đương đúng 1.352 giây sau giải mã; MP3 có thể hiện thêm phần đệm codec trong một số ứng dụng. Căn theo thời lượng giải mã và timeline, không căn theo số làm tròn ở trình quản lý tệp. Giọng được co giãn nhịp có giữ cao độ, không bỏ câu hoặc cắt đuôi lời; khoảng nghỉ được thêm để giữ các mốc chung.

Để làm tập sau, dùng lại mã giọng, speaker ID, model hash và cấu hình trong `VOICE_PROFILES_LOCKED.json`. Dịch vụ giọng online có thể cập nhật nên không cam kết dạng sóng giống tuyệt đối giữa các lần. Đã biên tập từng cue dịch với lời gốc; **chưa có một vòng nghe toàn bộ độc lập bởi người bản ngữ cho cả 16 ngôn ngữ**. Báo cáo kỹ thuật không thay cho bước nghe duyệt trước phát hành.

Gói này gồm kịch bản, prompt và voice thật. Không bao gồm video đã dựng hoặc ảnh thumbnail đã tạo. Nếu được lưu dưới GitHub draft release, chủ tài khoản cần đăng nhập GitHub để tải tài sản nháp.
