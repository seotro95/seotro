# Video Affiliate Studio — bản đầu

Ứng dụng cục bộ tiếng Việt, độc lập với Voice Studio hiện có. Python 3.10 trở lên và FFmpeg (có ffprobe, libx264, drawtext, subtitles). Không cần API key.

## Windows

1. Cài Python từ python.org, bật Python Launcher. Cài FFmpeg theo liên kết Windows từ https://ffmpeg.org/download.html, thêm thư mục bin vào PATH. Mở cửa sổ lệnh mới; kiểm tra `ffmpeg -version` và `ffprobe -version`.
2. Chạy `install.bat` một lần. Cần Internet để tải thư viện Python.
3. Chạy `start.bat`, mở địa chỉ được in trong cửa sổ. Giữ cửa sổ chạy khi dựng video.
4. Chọn video, mốc bắt đầu và độ dài; có thể thêm tiêu đề, logo, nhạc thay âm gốc và SRT. SRT tính tương đối từ đầu đoạn xuất. Nhập sản phẩm, link, nội dung giới thiệu, hashtag và giờ dự kiến đăng.
5. Bấm dựng; xem trước, tải MP4/caption hoặc gói ZIP có thêm kế hoạch JSON. Duyệt trước khi đăng thủ công. Ctrl+C để tắt.

## Linux / môi trường cloud

```sh
cd /workspace/seotro/affiliate-studio
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

FFmpeg và ffprobe cần có trong PATH. Chỉ lắng nghe loopback; không đưa trực tiếp dịch vụ này lên Internet. Dữ liệu và kết quả lưu trong `.data`, không gửi đến nền tảng bên ngoài. Xóa thư mục tác vụ trong `.data` khi ứng dụng tắt để dọn dung lượng. Video nguồn tối đa 500 MB; nhạc 50 MB, logo 10 MB, SRT UTF-8 2 MB. Tệp hỏng sẽ được báo trong hàng đợi. Một tác vụ dựng chạy mỗi lần; tác vụ bị ngắt khi tắt máy cần tạo lại. Chưa có hủy tác vụ, vì vậy chờ hoàn tất hoặc dừng ứng dụng.

## Phạm vi

Đã có cắt đoạn, crop giữa 9:16 720p, tiêu đề, phụ đề nhập SRT, logo góc trên phải, thay nhạc và gói nội dung affiliate. Nhạc sẽ lặp để đủ đoạn. Caption theo mẫu từ dữ liệu người dùng, không tự tạo bằng AI. Tiêu đề dài có thể vượt chiều ngang; kiểm tra preview, dùng tiêu đề ngắn. Crop giữa có thể cắt chủ thể.

Chưa có tải YouTube, tự chọn cảnh nổi bật, tự nhận dạng phụ đề, hiệu ứng chuyển cảnh, kho sản phẩm, theo dõi hoa hồng hoặc API đăng Facebook/TikTok. Giờ dự kiến chỉ là dữ liệu kế hoạch, không phải bộ lập lịch chạy nền. Link trong caption không tự gắn sản phẩm vào cửa hàng nền tảng. Voice Studio bên cạnh có nhận dạng/voice riêng nhưng bản này chưa nối trực tiếp. Không cần cung cấp mật khẩu mạng xã hội.

Windows launchers được cung cấp; kiểm thử dựng thực hiện trên Linux, chưa xác nhận chạy trên máy Windows thật.
