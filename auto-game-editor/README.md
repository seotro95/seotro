# Tự dựng highlight gameplay

Công cụ quét bản ghi dài, chọn các đoạn nổi bật và tự ghép theo thứ tự gameplay. Đầu ra là các tệp MP4 720p cùng bảng thời gian cắt và zoom.

## Bản tải cho Windows

[Tải tệp ZIP](auto-game-editor-windows.zip), giải nén toàn bộ rồi mở **Cai-dat.cmd**. Tệp này cài các phụ thuộc còn thiếu, tải bộ nhận diện âm thanh, tạo lối tắt **Auto Game Editor** trên Desktop và mở cửa sổ công cụ. Giữ thư mục giải nén để lối tắt tiếp tục hoạt động. Dùng **Kiem-tra.cmd** để kiểm tra hoặc **Khoi-dong.cmd** để mở lại.

Bản này hỗ trợ FFmpeg đã bỏ tùy chọn cũ `-filter_complex_script`. Nếu xử lý thất bại, bấm **Sao chép lỗi** trong cửa sổ để lấy thông báo chi tiết.

## Cài và chạy

1. Cài Python 3 có Tkinter và FFmpeg có libx264. Thêm `ffmpeg` và `ffprobe` vào PATH. Cài thêm **Tesseract OCR** và thêm vào PATH nếu muốn dùng chế độ tự nhận diện tên game.
2. Tải và giải nén ZIP để có các tệp Python và ảnh hiệu ứng. Mở terminal trong thư mục giải nén và chạy:

   ```bash
   python -m pip install tkinterdnd2
   python auto_edit.py
   ```

   Dùng `py` trên Windows hoặc `python3` trên macOS/Linux nếu lệnh `python` không có.

3. Nhập **Số video** và **Phút mặc định**. Dùng **Chỉnh phút từng video…** để đặt thời lượng riêng và **Chọn thư mục lưu…** để chọn nơi xuất. Chọn game hoặc thể loại, rồi thả một tệp MP4, MOV, MKV hoặc WebM vào cửa sổ. Bật **Zoom facecam bên trái** nếu bản ghi có webcam giống video mẫu.
4. Mở thư mục `<tên video>-highlights` tại nơi đã chọn. Nếu chưa chọn thư mục, kết quả nằm cạnh video gốc. `timeline.csv` ghi các đoạn nguồn và `effects.csv` ghi các mốc hiệu ứng.

Có thể chạy bằng dòng lệnh mà không cần cài `tkinterdnd2`:

```bash
python auto_edit.py "ban-ghi-5-gio.mp4" --durations 3 5 8 --game Minecraft --output "D:/Video/Highlight"
```

## Cách chọn đoạn và dựng

- Quét tuần tự toàn bộ bản ghi, lấy 2 mẫu chuyển động mỗi giây và phân tích âm lượng. Chấm điểm theo thể loại. Mỗi đoạn ghi tín hiệu mạnh nhất trong số phản ứng facecam, chuyển động gameplay và cao trào âm thanh. Đây là phân loại tín hiệu, chưa nhận diện được các sự kiện như hạ gục hoặc thắng trận.
- Chế độ **Tự nhận diện** dùng OCR để tìm tên game trong danh sách hỗ trợ ở tối đa sáu khung hình. Nếu thiếu bằng chứng hoặc chưa cài OCR, công cụ báo chưa nhận diện và dùng cấu hình Tổng hợp. Bạn có thể chọn game, nhập tên hoặc chọn thể loại trước khi thả tệp.
- Chọn 5–6 đoạn mỗi video (video dưới 25 giây có thể dùng ít hơn). Giữ thứ tự nguồn và ưu tiên nhóm có cao trào, độ sáng qua điểm nối phù hợp và khoảng bỏ 3–60 giây khi nguồn đủ dài.
- Trước điểm cắt, công cụ ưu tiên cận facecam 3 giây, rồi về rộng 2 giây. Khi phát hiện lời nói kéo dài khoảng 6 giây, công cụ dùng cú cận riêng 2 giây. Với webcam chiếm 20% chiều ngang ảnh gốc, độ phóng khoảng 3,5× tương ứng gần 70% chiều ngang ảnh đầu ra. Tại phút 1, 2, 3… của mỗi video, khung hình dịch xuống mép dưới khoảng 3 giây rồi trở lại. Khi các hiệu ứng cùng mốc, công cụ ưu tiên góc mép dưới và đoạn nói dài rồi dời cặp cận/rộng vào phần trống.
- YAMNet nhận diện tiếng cười hoặc tiếng khóc và hiện mặt tương ứng đúng 1 giây. Mô hình phân loại âm thanh, nên có thể nhầm tiếng trong game hoặc bỏ sót câu đùa không phát ra tiếng cười. Nếu bộ nhận diện chưa cài, công cụ vẫn dựng video với hiệu ứng theo nhịp thông thường. Cài thủ công ngoài Windows bằng `python -m pip install "ai-edge-litert>=2.1,<3"` rồi `python audio_events.py --setup` (Python 3.10 trở lên).
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
