# Voice Studio Riêng 1.3 · Nhập TXT/SRT và khớp timeline video

Bản Portable Windows 10/11 x64 có sẵn Python, FFmpeg và mô hình. Giải nén toàn bộ ZIP rồi mở `MO_TOOL.bat`. Liên kết tải đã kiểm tra nằm trong [trang tải](../downloads/voice-studio/README.md).

1. Bấm **Nhập TXT / SRT** hoặc kéo tệp vào ô văn bản. Hỗ trợ UTF-8, UTF-16 và Windows-1258; giữ dấu tiếng Việt và mốc thời gian.
2. Bật **Tự động khớp timeline**. Xem trước các câu/mốc. Nếu TXT chỉ có mốc bắt đầu, nhập **Tổng thời lượng video** để xác định mốc cuối; tool không tự đoán.
3. Chọn **WAV** khi dựng video. Giọng được căn theo từng ô lời thoại; giữ khoảng trống đầu/giữa/cuối và đúng tổng thời lượng. Xuất kèm SRT hoặc TXT có mốc để đưa vào phần mềm dựng.
4. Xem **báo cáo đồng bộ**: số câu khớp, thời lượng đích/thực tế và độ lệch. Câu quá dài để đọc vừa ô sẽ báo rõ; tool không cắt mất lời hoặc âm thầm xuất thiếu nội dung.

Ví dụ TXT:

```text
[00:01.125 - 00:04.875] Xin chào.
[00:06 - 00:08.250] Cảm ơn bạn đã lắng nghe.
```

Hoặc `[00:01] Lời thứ nhất` rồi `[00:05] Lời thứ hai`; cần nhập độ dài video cho mốc kết thúc câu cuối. TXT không có mốc có thể nhập tổng thời lượng để căn cả bài, hoặc tắt căn timeline để đọc tự nhiên.

**Giọng tự nhiên hơn:** chọn Cân bằng 8 bước hoặc Ưu tiên chất lượng 16 bước cho Nano; số bước cao xử lý lâu hơn. Mẫu giọng cần chứa cách nhấn nhá mong muốn, nhất là 5 giây đầu. Nano hỗ trợ chèn thủ công `[cười]`, `[thở dài]`, `[hắng giọng]`. Các lựa chọn Kể chuyện/Bản tin điều chỉnh nhịp đọc, không bảo đảm điều khiển cảm xúc như người thật.

WAV khớp timeline đến từng mẫu âm thanh. MP3 có thông tin đệm mã hóa nên một số phần mềm có thể hiển thị thời lượng gói dài hơn; ưu tiên WAV để dựng chính xác. Khớp timeline không có nghĩa là tự khớp khẩu hình video khi tệp gốc ghi sai mốc.

Giữ 16 giọng quốc tế offline trên CPU, nhân bản tiếng Việt, giới hạn 200.000 ký tự, xuất WAV/MP3/TXT/SRT và dừng/tiếp tục. Chế độ Nhanh 4 bước vẫn có sẵn. Số đo tốc độ cũ trong [HIEU_NANG.md](HIEU_NANG.md) áp dụng cho cấu hình đã đo, không áp dụng tự động cho căn timeline hoặc Nano16.

Khi cập nhật: tắt tool, sao lưu `app/.data`, giải nén bản mới sang thư mục mới. Chuyển các thư mục con `voices`, `jobs`, `audio`, `parts` nếu cần giữ mẫu/lịch sử; giữ các mô hình đi kèm bản mới.

Nếu dùng mã nguồn: cài Python 3.12 x64, chạy `CAI_DAT.bat`, `TAI_GIONG_NHAN_BAN_NHANH.bat` và `TAI_GIONG_QUOC_TE_NHANH.bat` trước khi mở tool.
