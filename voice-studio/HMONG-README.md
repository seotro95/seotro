# Voice Studio Hmong 1.0.0

Phiên bản riêng của Voice Studio 3.6.2, đọc **Hmong Trắng / Hmoob Daw (mww)** bằng F5-Hmong. Giao diện và hướng dẫn dùng tiếng Việt.

## Bản Windows đầy đủ

1. Tải `Voice-Studio-Hmong-1.0.0-Windows-x64.zip` trong GitHub Releases và giải nén toàn bộ vào một thư mục có quyền ghi. Không chạy trực tiếp bên trong ZIP.
2. Mở `MO_VOICE_STUDIO_HMONG.bat`. Gói có sẵn Python, thư viện CPU và FFmpeg; không cần tự cài Python, API key hay GPU.
3. Lần mở đầu cần Internet để tải và kiểm tra khoảng **1,4 GB mô hình** từ Hugging Face. Giữ cửa sổ đang chạy mở. Nếu tải bị gián đoạn, mở lại để tiếp tục chuẩn bị. Trọng số không nằm trong ZIP vì nguồn chưa công bố giấy phép phân phối lại rõ ràng.
4. Trình duyệt tự mở khi sẵn sàng. Sau lần chuẩn bị thành công, tạo giọng hoạt động offline. Giữ cửa sổ tool mở trong lúc sử dụng; đóng cửa sổ để dừng máy chủ.

`KIEM_TRA_HMONG.bat` chỉ kiểm tra thư viện và checksum mô hình, không tải thêm và không tạo âm thanh. Trước lần chuẩn bị đầu, thông báo thiếu mô hình là bình thường. Dữ liệu cá nhân nằm trong `voice-studio-hmong/.data`; hãy sao lưu thư mục này trước khi đổi phiên bản.

## Tạo giọng và nhân bản

- Nhập văn bản Hmong chữ Latin RPA hoặc nhập tệp TXT/SRT. Chọn mẫu **nữ** hoặc **nam**, rồi tạo giọng. Có thể tải WAV, MP3 và xuất lại nội dung TXT/SRT.
- Chọn 8 bước để nghe bản nháp nhanh hơn; 16 hoặc 32 bước tốn thời gian hơn. Các kiểu kể chuyện, review, tin tức điều chỉnh nhịp, tốc độ và khoảng nghỉ; chúng không phải các mô hình cảm xúc riêng.
- Để nhân bản giọng, tải đoạn nói sạch **3–8 giây**, một người nói, không nhạc nền, và nhập **đúng lời Hmong trong đoạn mẫu**. Chỉ dùng mẫu bạn có quyền sử dụng. Tool không tự nhận dạng lời Hmong.
- Có thể nhập/sửa phụ đề Hmong thủ công và lồng tiếng theo SRT. Phiên bản này không cung cấp nhận dạng giọng nói Hmong tự động; Whisper không hỗ trợ Hmong. Dịch bằng Ollama hoặc dịch vụ khác cần thiết lập riêng, không thuộc tính năng offline đi kèm.

Tốc độ phụ thuộc CPU, độ dài nội dung và số bước. Không có cam kết tạo một giờ âm thanh trong hai phút. Cần khoảng 8 GB RAM trở lên; 16 GB được khuyến nghị, cùng dung lượng đĩa trống cho mô hình, công việc và bản xuất. Kiểm tra tạo tệp âm thanh không thay thế việc người biết tiếng Hmong nghe đánh giá cách phát âm.

## Khi gặp lỗi tải hoặc 403

Link ZIP là tài sản công khai trong GitHub Releases. Nếu mạng chặn GitHub, thử mạng có quyền truy cập GitHub hoặc mở trang Releases. Lần tải mô hình còn cần `huggingface.co` và các máy chủ CDN `*.huggingface.co`, `*.hf.co`. Tool giữ kiểm tra TLS và checksum; không thể tự gỡ chính sách chặn của mạng. Sau khi tải mô hình thành công, các lần dùng offline không cần các kết nối này.

## Chạy từ mã nguồn

Tạo môi trường riêng, vì F5 và bản Voice Studio tiếng Việt dùng các phiên bản thư viện khác nhau:

```sh
cd voice-studio
python3.12 -m venv .venv-hmong
.venv-hmong/bin/python -m pip install -r requirements-hmong.txt
./start_hmong.sh
```

Trên Windows, dùng `.venv-hmong\Scripts\python.exe` và `start_hmong.bat`. Có thể đặt `VOICE_STUDIO_DATA_DIR` tới thư mục dữ liệu riêng trước khi khởi động. Không dùng chung thư mục dữ liệu hoặc môi trường Python với phiên bản tiếng Việt.

Nguồn mô hình được ghim theo revision và xác minh trong `prepare_hmong.py`; các mẫu tham chiếu nam/nữ lấy từ mẫu đã có lời được xác nhận trong dự án, kèm SHA256 trong `assets/hmong/voices.json`. Bản phát hành Windows chỉ được công bố sau kiểm tra suy luận thật bằng runtime đã di chuyển sang đường dẫn có dấu cách; báo cáo `NATIVE-VALIDATION.json` nằm trong gói.
