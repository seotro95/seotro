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
