# Hmong Studio 0.4.3 — gói đầy đủ, một file chạy

Bản này gom toàn bộ ứng dụng, hai mẫu nam/nữ và các bản sửa lỗi vào một ZIP. **Chỉ chạy `CHAY-STUDIO.bat`**: file này tự cài thư viện/công cụ/mô hình còn thiếu, kiểm tra rồi mở Studio trong trình duyệt. Những lần sau cũng dùng chính file đó; bộ máy đã hợp lệ được kiểm tra và dùng lại, không cài đè thư viện.

CosyVoice Hmong tạo lời đọc mới theo mẫu nam/nữ, chạy trên máy và không cần dịch vụ trả phí hoặc API key. **Mô hình chưa nằm sẵn trong ZIP**: cần Internet lần đầu để tải thư viện và khoảng **5,4 GB** mô hình; tệp đã tải đúng được dùng tiếp. Mẫu âm thanh dùng để lấy âm sắc; không phải huấn luyện lại mô hình.

Gói này giữ bản sửa WinError 2 với tệp `__init__.py.part` sau khi đã tải trọng số. Tệp nguồn rỗng được tạo và kiểm tra checksum trước khi dùng. Nếu đang cài dở bản 0.4.1/0.4.2, **đóng Studio và bộ cài, giải nén đè mã mới vào đúng thư mục đang dùng, giữ nguyên `.data`**, rồi chạy `CHAY-STUDIO.bat`.

Bộ cài vẫn tạo môi trường riêng để tránh WinError 32 khi pip cài đè tệp SymPy/Torch đang bị giữ. Nếu vẫn bị tiến trình giữ tệp, khởi động lại Windows trước khi thử lại; không cần chạy quản trị hoặc cài Visual C++ Build Tools.

## Cài trên Windows

1. Cài **Python 3.12.10 Windows 64-bit** từ https://www.python.org/downloads/release/python-31210/ , bật Python Launcher. Không cần gỡ Python 3.15 đang có.
2. Lần đầu: giải nén ZIP vào thư mục có quyền ghi. Đang dùng `E:\voi hmong\Hmong-Studio-Trang`: đóng Studio/bộ cài, giải nén ZIP vào **`E:\voi hmong\`** và chọn thay thế tệp để cập nhật đúng thư mục `Hmong-Studio-Trang` hiện có. Giữ `.data`; tránh lồng thêm một thư mục `Hmong-Studio-Trang` bên trong thư mục cũ. Không di chuyển `.venv` hoặc các thư mục `.venv-clone-*` sang nơi khác.
3. Bấm đúp **`CHAY-STUDIO.bat`**. Chờ quá trình cài/kiểm tra hoàn tất; Studio sẽ tự mở trong trình duyệt sau khi máy chủ sẵn sàng. Nếu bị ngắt, chạy lại chính file này để tiếp tục; không đổi checksum hoặc tắt TLS. Nếu trình duyệt không tự mở, dùng địa chỉ hiện trong cửa sổ lệnh.
4. Giữ cửa sổ lệnh mở khi dùng Studio. Nhấn Ctrl+C để đóng. Những lần sau chỉ bấm đúp **`CHAY-STUDIO.bat`**; có thể tạo voice cục bộ khi không có Internet sau khi cài xong. Nếu trình duyệt còn giao diện cũ, nhấn Ctrl+F5.

`install_clone_ai.bat` và `start.bat` vẫn có cho việc cài/mở riêng; dùng `CHAY-STUDIO.bat` thì không cần chạy hai file đó. `install_local_ai.bat` gọi bộ cài nhân bản; `install_mms_asr.bat` chỉ dành cho MMS/ASR riêng. Bộ cài tạo môi trường có tên `.venv-clone-<mã>` và chỉ chọn nó sau khi mọi kiểm tra đạt. `.venv` cũ không bị cài đè. Nếu cài lỗi, môi trường đang dùng và mô hình/giọng đã lưu được giữ nguyên; lần thử lại tạo môi trường mới. Hai bộ cài không được chạy cùng lúc.

Bộ cài mới chọn CPython 3.10–3.12 x64, ưu tiên 3.12; giữ bản sao môi trường không tương thích thay vì xóa. Dữ liệu `.data` được giữ riêng. Nếu muốn chuyển mẫu cá nhân từ bản cũ, sao chép `.data/clones` khi cả hai bản đã tắt.

Khuyến nghị **RAM 16 GB trở lên**, chừa ít nhất khoảng 15 GB đĩa trống cho mô hình/thư viện và dung lượng cho sản phẩm. Lượt đầu phải nạp mô hình; CPU có thể chậm. Nếu xuất hiện lỗi DLL của Torch/ONNXRuntime, kiểm tra Microsoft Visual C++2015–2022 x64 Redistributable chính thức; không cần bộ biên dịch Build Tools cho quy trình cài này. Windows launcher chưa được chạy trên Windows thật trong phiên kiểm thử này.

## Tạo voice

- Chọn **Hmong Trắng**, rồi **Giọng nữ** hoặc **Giọng nam**. Hai mẫu chính xác người dùng cung cấp đã đi kèm; không cần thu lại bằng micro.
- Nhập lời Hmong RPA muốn đọc, tối đa **2.000 ký tự/lượt** ở chế độ cục bộ. Đoạn lời mới không cần trùng với lời trong mẫu.
- Chọn cách đọc: Tự nhiên, Review, Kể chuyện, Quảng cáo, Tin tức, Thư giãn, Ấm áp, Vui vẻ hoặc Buồn; điều chỉnh tốc độ nếu cần.
- Bấm **Tạo voice**. Có trạng thái đang chạy; **Dừng** kết thúc worker suy luận. Có thể tạo lại sau khi dừng. Bản thu trước được giữ khi tác vụ thất bại/hủy.
- Khi hoàn tất, nghe và xuất WAV trong **Biên tập âm thanh**. Tải âm thanh trước khi tắt máy chủ; giữ tối đa 10 kết quả tác vụ tạm gần nhất.

CosyVoice dùng tối đa 10 giây đầu mẫu, không yêu cầu bản chép mẫu trong chế độ instruct2. Có thể tải thêm mẫu riêng dài 3–60 giây / 20 MB, nhập tên và xác nhận quyền sử dụng. Ô bản chép là tùy chọn; chỉ dịch vụ ngoài theo hợp đồng cũ có thể yêu cầu nó.

Các cách đọc được gửi thành chỉ dẫn suy luận thực tế, không giả lập nhân bản bằng đổi cao độ. Mức độ biểu cảm, độ giống mẫu và cách phát âm cần nghe kiểm tra; chưa được đánh giá bởi người bản ngữ và không cam kết phát âm chuẩn mọi từ. Micro chỉ dùng khi muốn thu mẫu mới. Lỗi quyền micro không chặn chọn mẫu nam/nữ hoặc tạo voice.

## Đã xác minh

Linux, CPU 4 threads, không GPU:

- Toàn bộ118 tệp mô hình/mã nguồn được đối chiếu SHA256 hoặc Git blob SHA1 theo snapshot được ghim; trọng số chỉ nạp bằng `weights_only=True`.
- Giọng nữ tạo thật câu **“Nyob zoo, kuv hais lus Hmoob.”**: WAV PCM16 mono 24 kHz, 2,71 giây; lượt lạnh khoảng64,7 giây, RAM đỉnh khoảng7,84 GiB.
- Giọng nam, cách đọc Review, cùng câu trên: tạo thật qua giao diện/API, WAV 2,51 giây; lượt này khoảng93,6 giây. Đây là số đo máy kiểm thử, không bảo đảm tốc độ trên máy khác.
- Nút Dừng đã kết thúc worker thật, sau đó tạo lại thành công. Chọn mẫu/generate không yêu cầu micro. Desktop/mobile 390 px không tràn ngang hoặc lỗi JavaScript.
- 83 kiểm thử Python đạt, gồm lỗi tệp rỗng và luồng một file chạy. Đã chạy thật lệnh cài-và-mở: dùng lại môi trường đã cài, mô hình sẵn sàng, phục vụ ứng dụng 0.4.3 rồi đóng đúng tiến trình. Trình duyệt chỉ được mở sau khi máy chủ sẵn sàng; kiểm thử HTTP thật xác nhận điều này, và lỗi khởi động không mở trình duyệt.
- Đã thử thiếu toàn bộ 12 tệp rỗng trên snapshot thật: xác minh đủ 118 tệp mà không gọi mạng hay sửa trọng số lớn. Bản 0.4.1 đã qua kiểm tra môi trường do bộ cài tạo và 8 kiểm tra micro trong Chromium. Đã giải mã WAV và xác minh tín hiệu khác 0; kết quả này không thay thế việc nghe chất lượng/phát âm.

## Nguồn và kỹ thuật

Mô hình: https://huggingface.co/Xuajpaj2026/hmong-tts-weights , revision `5663e0df2589c2ca2403cd327a52702c3ff96e8f`. Tác giả có cấu hình chỉ dẫn White Hmong RPA. Source/license CosyVoice và Matcha được giữ trong snapshot; không chạy wrapper sửa checkpoint của tác giả. App chỉ nạp cấu hình suy luận đã kiểm tra; không cài thành phần huấn luyện CUDA/pyworld.

Mặc định snapshot nằm trong `.data/models/hmong-cosy`; có thể đặt `HMONG_COSY_DIR` trỏ tới snapshot đã xác minh. Chạy Linux: cài Torch/Torchaudio 2.6 CPU khớp nhau, `pip install -r requirements-cosy.txt`, `python prepare_clone_model.py`, rồi `python -m uvicorn app:app --host 127.0.0.1 --port 8090 --no-access-log`. FFmpeg/ffprobe cần có trong PATH. Không công khai trực tiếp dịch vụ lên Internet; app chưa có đăng nhập.

Bộ tải có thể tiếp tục tệp `.part` và chỉ ghi marker ready sau khi toàn bộ checksum đạt. Mã suy luận đặt chế độ offline trước khi nạp thư viện Hub. Nếu chủ động cấu hình `HMONG_CLONE_URL`/`HMONG_TTS_URL`, mẫu/lời có thể gửi tới dịch vụ đó khi dùng luồng từ xa; khi CosyVoice cục bộ sẵn sàng thì mẫu nam/nữ và mẫu riêng ưu tiên xử lý cục bộ.
