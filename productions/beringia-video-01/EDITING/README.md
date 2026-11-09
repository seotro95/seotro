# Beringia — bản dựng hoàn chỉnh, tiếng Anh

- [Tải video MP4 20 phút](https://github.com/seotro95/seotro/releases/download/beringia-video-01-final-20min/BERINGIA_01_EN_FINAL_20m_720p.mp4)
- [Xem riêng đoạn mở đầu 30 giây](https://github.com/seotro95/seotro/releases/download/beringia-video-01-final-20min/BERINGIA_01_OPENING_30s.mp4)
- [Tải một ZIP đủ 17 giọng](https://github.com/seotro95/seotro/releases/download/beringia-video-01-final-20min/BERINGIA_01_17_VOICES.zip)
- [Tải riêng từng giọng](https://github.com/seotro95/seotro/blob/codex/beringia-video-01/productions/beringia-video-01/VOICES/README.md)
- [5 tiêu đề và 5 prompt thumbnail](TITLES_AND_THUMBNAIL_PROMPTS.txt)
- [Phụ đề tiếng Anh SRT](https://github.com/seotro95/seotro/releases/download/beringia-video-01-final-20min/BERINGIA_01_EN_SUBTITLES.srt)
- [Hồ sơ dự án dựng](https://github.com/seotro95/seotro/releases/download/beringia-video-01-final-20min/BERINGIA_01_EDIT_PROJECT.zip)

Video giữ độ phân giải gốc **1280 × 720, 24 fps**, dài **20:00**, có một luồng lời đọc tiếng Anh. Toàn bộ âm thanh từ clip đầu vào đã được bỏ. Giọng, câu chữ và thứ tự lời dẫn tiếng Anh được giữ nguyên; mức âm lượng được cân để nghe rõ. Không thêm nhạc nền.

30 giây đầu có **8 cảnh**, đi từ biển hiện tại sang bản đồ kết nối cổ, gia đình tiền sử, đồng bằng và đàn thú. Toàn bộ bản dựng có **190 đoạn hình**, gồm **6 chuyển cảnh hòa ngắn**. Các cảnh còn lại dùng cắt trực tiếp theo ý, thay đổi toàn/cận có chủ đích, nhãn chương và chú thích địa điểm hoặc niên đại khi cần.

Phụ đề tiếng Anh được nhúng dưới dạng tùy chọn, không ép hiện trên mọi trình phát. Có SRT riêng để tải lên YouTube. MP4 có 12 chương, mỗi chương 100 giây.

Đã kiểm tra: 28.800 khung hình; 120 cảnh dựng, mỗi cảnh 240 khung; một luồng audio tiếng Anh; khớp voice ở 13 cửa sổ xuyên suốt video; không có khoảng đen từ 0,5 giây theo ngưỡng kiểm tra; giải mã toàn tệp không báo lỗi. Âm lượng đo: **-16.07 LUFS**, đỉnh thực **-1.26 dBTP**. Chi tiết trong FINAL_VIDEO_QA.json.

Đã kiểm tra hình đại diện của toàn bộ 118 clip khác nhau, cùng các khung hình sau dựng ở mở đầu, sơ đồ, nhãn chương và kết. Đây không phải tuyên bố đã xem thủ công từng khung hình của cả 20 phút.

Trong 129 tệp đính kèm, 128 tệp tải được, có 10 bản trùng; một tệp vượt giới hạn truyền 32 MiB. Bản dựng dùng các cảnh phù hợp đã kiểm tra và sơ đồ giải thích để phủ đủ timeline. Các cảnh bản đồ sai khu vực, con người dường như đứng dưới nước, biểu đồ di truyền bịa nhãn hoặc vật hiện đại lẫn trong bối cảnh tiền sử đã được loại.

Đồ họa đường bờ hiện đại dùng dữ liệu Natural Earth 1:110m, phạm vi đất cổ và tuyến di chuyển ghi rõ là sơ đồ. Hình tạo sinh chỉ minh họa cho lời kể, không phải hình thực địa hay vật chứng vừa được phát hiện. Phần Beringia dưới biển được phân biệt với các vùng Siberia, Alaska, Yukon vẫn ở trên cạn.

17 bản MP3 giữ nguyên hồ sơ giọng đã khóa. Mỗi bản có 1.200 giây âm thanh sau giải mã. Các bản dịch khớp tổng thời lượng và 12 chương, chưa được căn từng từ theo bản tiếng Anh; các bản ngôn ngữ khác vẫn cần người bản ngữ rà soát, đặc biệt phương ngữ Hmong Trắng chưa được xác nhận độc lập.

Các tệp dự án gồm bảng dựng, mã nguồn xử lý, đồ họa, bảng tên và SHA-256 của clip. ZIP dự án không chứa lại toàn bộ clip gốc; hãy giữ bộ clip đã gửi nếu muốn dựng lại. Mã hiện dùng thư mục /workspace/work/beringia/edit; điều chỉnh đường dẫn nếu chạy ở máy khác. Cần FFmpeg/FFprobe, Python, NumPy, Pillow và Matplotlib.

Để làm chủ đề 2, đọc productions/TIEP_TUC_TU_DAY.md trên nhánh codex/beringia-video-01. Không thay đổi danh sách chủ đề hoặc 17 hồ sơ giọng đã khóa.
