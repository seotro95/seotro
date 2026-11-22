# Tự dựng highlight gameplay

Công cụ quét bản ghi dài, chọn các đoạn nổi bật và tự ghép theo thứ tự gameplay. Đầu ra là các tệp MP4 720p cùng bảng thời gian cắt và zoom.

## Cài và chạy

1. Cài Python 3 có Tkinter và FFmpeg có libx264. Thêm `ffmpeg` và `ffprobe` vào PATH. Cài thêm **Tesseract OCR** và thêm vào PATH nếu muốn dùng chế độ tự nhận diện tên game.
2. Tải `auto_edit.py`, mở terminal ở thư mục tải xuống và chạy:

   ```bash
   python -m pip install tkinterdnd2
   python auto_edit.py
   ```

   Dùng `py` trên Windows hoặc `python3` trên macOS/Linux nếu lệnh `python` không có.

3. Nhập **Số video** và **Phút mỗi video**, chọn game hoặc thể loại, rồi thả một MP4, MOV, MKV hoặc WebM vào cửa sổ. Dùng ô **Zoom facecam bên trái** nếu bản ghi có webcam giống video mẫu.
4. Mở thư mục `<tên video>-highlights` cạnh tệp gốc. Mỗi video dùng các đoạn nguồn riêng. `timeline.csv` ghi mốc nguồn, mốc đầu ra, mốc zoom vào/ra và tín hiệu nổi bật.

Có thể chạy bằng dòng lệnh mà không cần cài `tkinterdnd2`:

```bash
python auto_edit.py "ban-ghi-5-gio.mp4" --count 3 --minutes 8 --game Minecraft
```

## Cách chọn đoạn và dựng

- Quét tuần tự toàn bộ bản ghi, lấy 2 mẫu chuyển động mỗi giây và phân tích âm lượng. Chấm điểm theo thể loại. Mỗi đoạn ghi tín hiệu mạnh nhất trong số phản ứng facecam, chuyển động gameplay và cao trào âm thanh. Đây là phân loại tín hiệu, chưa nhận diện được các sự kiện như hạ gục hoặc thắng trận.
- Chế độ **Tự nhận diện** dùng OCR để tìm tên game trong danh sách hỗ trợ ở tối đa sáu khung hình. Nếu thiếu bằng chứng hoặc chưa cài OCR, công cụ báo chưa nhận diện và dùng cấu hình Tổng hợp. Bạn có thể chọn game, nhập tên hoặc chọn thể loại trước khi thả tệp.
- Dựng theo nhịp video tham chiếu. Giữ cảnh rộng, xen cú cắt hoặc zoom lên khoảng 1,85× hay 1,95× về phía facecam, dùng một số đoạn cận khoảng 4,23×, rồi trở về toàn cảnh. Cú cận kéo dài khoảng 1,4–1,7 giây. Dùng video gốc, camera nằm bên trái, để hiệu ứng gần mẫu nhất.
- Công cụ xử lý trên máy, đọc bản ghi theo luồng và lưu các đặc trưng nhẹ để lập kế hoạch. Thời gian quét phụ thuộc vào codec, độ phân giải và CPU. Tổng thời lượng yêu cầu cần nằm trong thời lượng nguồn để các video đầu ra không dùng lại đoạn.

## Quét chuyển cảnh theo từng giây

Chế độ phân tích đọc video và xuất CSV, giữ nguyên video đầu vào.

```bash
python -m pip install opencv-python-headless
python analyze_video.py "video-dai.mp4"
```

CSV có ít nhất một dòng mỗi giây. Khi một giây có nhiều lần đổi hình mạnh, mỗi mốc có một dòng riêng. Cột tỷ lệ so sánh kích thước các chi tiết khớp ở hai khung hình liền nhau. Ví dụ, 2,00 gợi ý phóng gần gấp đôi và 0,50 gợi ý thu xa còn một nửa. Nhãn là gợi ý để rà lại bằng mắt. Zoom chậm có thể nằm dưới ngưỡng đổi hình. Màn hình chết, menu, hiệu ứng của game và cắt ghép đều có thể tạo mốc đổi hình.

### Video tham chiếu `videoplayback.mp4`

| Thời gian | Quan sát |
| --- | --- |
| 00:05.067 → 00:06.500 | Phóng gần khoảng 1,85× rồi về bố cục toàn cảnh. Các chi tiết hang đá còn khớp qua hai điểm chuyển. |
| 00:50.133 | Phóng gần khoảng 1,95× về phía facecam. Địa hình cạnh mặt nước còn khớp hai bên điểm chuyển. |
| 02:59.733 → 03:01.433 | Cắt vào cận mặt khoảng 4,23× rồi cắt về gameplay. |
| 03:11.333 | Hiệu ứng hù xuất hiện trong gameplay trong khi bố cục webcam giữ nguyên. Một mốc đổi hình mạnh có thể đến từ game. |
| 07:15.667 → 07:19.867 | Trùng khung hình với đoạn 00:00.867 → 00:05.067. Đây là bằng chứng video thành phẩm có chèn hoặc lặp lại đoạn gameplay. |

[CSV của video tham chiếu](videoplayback-timeline.csv) chứa các mốc tự phát hiện. Các kết luận trong bảng trên dựa thêm vào đối chiếu khung hình. Chỉ có video thành phẩm, nên không thể xác định chắc đoạn nguồn đã bị lược bỏ ở tất cả các điểm nối.
