# Bộ 16 giọng nam — Maya 055

- Mỹ — tiếng Anh: `en-US-GuyNeural`.
- Việt Nam: `vi-VN-NamMinhNeural`.
- Tây Ban Nha: `es-ES-AlvaroNeural`.
- Pháp: `fr-FR-HenriNeural`.
- Nhật Bản: `ja-JP-KeitaNeural`.
- Hàn Quốc: `ko-KR-InJoonNeural`.
- Đức: `de-DE-ChristophNeural`.
- Ý: `it-IT-DiegoNeural`.
- Bồ Đào Nha: `pt-PT-DuarteNeural`.
- Hà Lan: `nl-NL-MaartenNeural`.
- Ba Lan: `pl-PL-MarekNeural`.
- Thụy Điển: `sv-SE-MattiasNeural`.
- Đan Mạch: `da-DK-JeppeNeural`.
- Phần Lan: `fi-FI-HarriNeural`.
- Na Uy: `nb-NO-FinnNeural`.
- Séc: `cs-CZ-AntoninNeural`.

Giữ nguyên 16 giọng từ Akrotiri 051, gồm Việt Nam Minh, Anh Guy và Đức Christoph. Yêu cầu tập này không có Hmong. Dùng backend online của Melo-Viet-Studio 1.3.1, commit `4f4fa1d72d976d6e2b9c94f906b0e12c6a2cf043`, chạy trên Linux. Không chạy giao diện Windows. Mã nguồn được kiểm tra SHA256 và giọng được đối chiếu danh mục nam trước tổng hợp.

Lưu VoiceID, nguồn mã, phong cách, tốc độ, nhấn nhẹ và tham chiếu âm thanh. Giữ pitch +0 Hz, tốc độ câu +6% đến +13%, sau đó căn thời lượng bằng điều chỉnh giữ cao độ. Nhà cung cấp có thể cập nhật mô hình; giữ VoiceID không bảo đảm dạng sóng bất biến.

Bản Anh có 4.222 từ, khoảng 186 từ/phút, căn theo 137 mốc. Mười lăm bản địa hóa căn theo 14 chương: 13 × 100 giây và chương cuối 62 giây. Mọi MP3 giải mã đúng 1.362 giây, tức 65.376.000 mẫu ở 48 kHz. Căn theo chương và tổng không đồng nghĩa từng câu khớp từng clip 10 giây.

Bản Việt, Nhật, Hàn được biên tập ngữ cảnh; 12 bản còn lại có bản dịch máy, rà thuật ngữ và sửa các đoạn được ghi trong hồ sơ. Chưa có nghe duyệt bản ngữ độc lập.

Âm thanh làm việc dùng bộ nhớ tạm. Bản giao bền vững nằm trên GitHub Release, có SHA256 và link tải từng nước. Sau xuất bản, lưu thêm bản tham chiếu Anh và Việt trong workspace; chỉ mục tải và hồ sơ giữ đủ 16 giọng cho lần sau.
