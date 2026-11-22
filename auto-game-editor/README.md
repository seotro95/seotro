# Tự dựng highlight gameplay

Thả một video dài vào cửa sổ. Công cụ chọn các đoạn có chuyển động và âm thanh nổi bật, ghép theo thứ tự gốc, rồi xen cảnh gameplay toàn khung với các cú zoom vào người chơi. Tệp `*-highlight.mp4` (720p, H.264/AAC) xuất cạnh video gốc.

## Cài một lần

1. Cài Python 3 có Tkinter và FFmpeg có `libx264`. Thêm `ffmpeg` và `ffprobe` vào PATH để chạy được từ terminal.
2. Tải tệp `auto_edit.py` trong thư mục này.
3. Mở terminal ở thư mục vừa tải và chạy:

   ```bash
   python -m pip install tkinterdnd2
   python auto_edit.py
   ```

   Dùng `py` trên Windows hoặc `python3` trên macOS/Linux nếu lệnh `python` không có.

4. Thả video vào ô **Thả một video vào đây**. Nút **Chọn video** cũng cho kết quả tương tự.

Chạy trực tiếp từ terminal mà không cần cài `tkinterdnd2`:

```bash
python auto_edit.py "video-dai.mp4"
```

## Cách chọn cảnh

- Công cụ chấm điểm chuyển động ở vùng webcam và vùng game, kết hợp mức âm lượng, rồi chọn tối đa 7 đoạn khoảng 8 giây.
- Zoom mặc định nhắm về phía trái, nơi đặt webcam trong video tham chiếu. Xen các cú cắt zoom nhanh và cú zoom tăng dần, sau đó trở lại khung toàn cảnh.
- Phù hợp với video ngang có webcam nằm bên trái ở vị trí tương tự mẫu. Dựng từ video gốc để tránh zoom chồng lên các đoạn đã zoom. Công cụ ước lượng điểm nổi bật bằng chuyển động và âm lượng. Tiếng lớn hoặc chuyển động nhanh có thể được chọn kể cả khi đó không phải khoảnh khắc bạn muốn giữ.
- Công cụ xử lý video trên máy của bạn.

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
