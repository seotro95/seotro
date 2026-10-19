# Hmong Studio

Studio riêng, giao diện tiếng Việt, chỉ dùng Hmong Trắng (`mww`), với mẫu giọng nam và nữ do người dùng cung cấp.

## Chạy

```sh
cd /workspace/seotro/hmong-studio
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8090
```

Windows: dùng `.venv\Scripts\python` và `.venv\Scripts\pip` thay đường dẫn trên. Mở địa chỉ máy chủ trong trình duyệt. Micro cần localhost hoặc HTTPS.

Hoặc trên Windows có Python 3.10+, chạy `start.bat` để tạo môi trường, cài thư viện và mở máy chủ (launcher Windows chưa được thử trong môi trường Linux này).

## Đã triển khai

- Soạn/nhập/xuất TXT (10.000 ký tự), tốc độ và chọn mẫu nam/nữ.
- Lưu nhiều dự án trên trình duyệt, mở/xóa, nhập/xuất JSON. JSON chỉ chứa lời và thiết lập, không chứa âm thanh.
- Thu micro tối đa 10 phút, nhập audio tối đa 50 MB, nghe lại, dạng sóng, cắt theo giây, chỉnh âm lượng và xuất WAV PCM 16-bit.
- Bộ chuyển tiếp TTS với giới hạn đầu vào/đầu ra và thông báo lỗi. Không có giọng Hmong cài sẵn, dịch, nhận dạng hay nhân bản giọng. Tốc độ AI chỉ áp dụng nếu dịch vụ thực thi đúng hợp đồng.

## Kết nối mô hình Hmong

Chưa xác minh mô hình hỗ trợ Hmong Trắng. Cần dịch vụ hoặc adapter thực sự đọc đúng Hmong; không dùng VieNeu/Qwen hiện có của Voice Studio để giả lập hỗ trợ Hmong.

Thiết lập `HMONG_TTS_URL` phía máy chủ tới endpoint **HTTPS** tin cậy và tùy chọn `HMONG_TTS_TOKEN` qua biến môi trường (không ghi khóa vào Git). Khởi động lại máy chủ. Endpoint nhận POST JSON:

```json
{"text":"Lời Hmong", "dialect":"mww", "voice":"hmong-white-female", "speed":1.0}
```

`dialect` chỉ là `mww`; `voice` là `hmong-white-female` hoặc `hmong-white-male`, tốc độ 0.5–2. Endpoint phải trả trực tiếp bytes WAV/MP3/OGG với Content-Type tương ứng; tối đa 50 MB, thời hạn 120 giây, không chuyển hướng. Đây là hợp đồng adapter của studio, không phải API mặc định của một nhà cung cấp. Cần viết adapter nếu API của nhà cung cấp khác hợp đồng. Xác nhận cách phát âm với người bản ngữ trước khi dùng chính thức.

Ứng dụng không có đăng nhập; chỉ chạy trên localhost. Không công khai trực tiếp khi chưa bổ sung xác thực và giới hạn lưu lượng. Nội dung gửi tới dịch vụ TTS khi bấm tạo giọng; bản thu được biên tập tại trình duyệt. Không tự động lưu âm thanh, hãy tải WAV trước khi đóng/mở dự án khác.

## Kiểm tra

```sh
python -m pytest tests -q
node --check static/app.js
```

Kiểm tra API không chứng minh chất lượng phát âm. Thu micro và luồng tải WAV cần kiểm tra trên trình duyệt thật.

## Mẫu giọng Hmong Trắng

Hai MP3 gốc nằm trong `static/voices/`, nghe thử bằng trình phát mẫu. Dự án lưu lựa chọn nam/nữ; dự án Hmong Trắng cũ chưa có lựa chọn sẽ dùng nữ. Dự án phương ngữ khác không được nhập hoặc hiển thị, dữ liệu cũ trong localStorage không tự bị ghi lại khi mở trang. Bộ chuyển tiếp chỉ gửi ID `voice`, không gửi mẫu âm thanh. Adapter TTS phải tự ánh xạ hai ID đến mẫu tương ứng và triển khai nhân bản giọng; hai MP3 không tự biến thành mô hình TTS.
