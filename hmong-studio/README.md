# Hmong Studio 0.5.1 — review, SRT và kịch bản dài

Bản này gom toàn bộ ứng dụng, hai mẫu nam/nữ và các bản sửa lỗi vào một ZIP. **Chỉ chạy `CHAY-STUDIO.bat`**: file này tự cài thư viện/công cụ/mô hình còn thiếu, kiểm tra rồi mở Studio trong trình duyệt. Những lần sau cũng dùng chính file đó; bộ máy đã hợp lệ được kiểm tra và dùng lại, không cài đè thư viện.

Mới: **1.000.000 ký tự/lượt**, Review mặc định, nhập TXT/SRT, hiển thị % trên nút Tạo và thanh tiến độ. Bộ máy và đặc trưng mẫu giọng được giữ trong tiến trình để dùng tiếp giữa các lượt. WAV được ghi từng đoạn ra đĩa; bản lớn được phát/tải trực tiếp, không giải mã toàn bộ trong trình duyệt.

**Bản 0.5.1 bỏ thêm phép tính từ vựng ngôn ngữ không dùng trong bộ giải mã giọng.** Phép đo cặp cùng seed tạo WAV giống hệt từng byte: trước sửa 31,426 giây, sau sửa 30,760 giây, cùng WAV 2,110 giây. Phần sinh phổ âm vẫn chiếm khoảng 26 giây. Đây là tối ưu có số đo, **chưa đạt mục tiêu 1 giờ voice trong 2 phút**. Xem `TOC-DO.md` để biết phạm vi đo và phần cứng cần xác định. Chạy `KIEM-TRA-GPU.bat` để xem tên GPU/VRAM; ảnh thẻ System trong dxdiag chỉ cho biết CPU/RAM.

Phép đo CPU đám mây 4 luồng ở bản 0.5.0, Review cùng câu “Nyob zoo, kuv hais lus Hmoob.”: lượt đầu 66,817 giây cho WAV 2,510 giây; lượt dùng lại cache 46,929 giây cho WAV 2,150 giây. Lượt sau bắt đầu suy luận sau 0,012 giây, loại được khoảng 24 giây nạp mô hình/mẫu. Các số đo này không phải trên máy Xeon Windows của bạn và chưa đo GPU. RAM 128 GB giúp xử lý kịch bản dài, không tự bảo đảm tốc độ 30 lần thời gian thực.

CosyVoice Hmong tạo lời đọc mới theo mẫu nam/nữ, chạy trên máy và không cần dịch vụ trả phí hoặc API key. **Mô hình chưa nằm sẵn trong ZIP**: cần Internet lần đầu để tải thư viện và khoảng **5,4 GB** mô hình; tệp đã tải đúng được dùng tiếp. Mẫu âm thanh dùng để lấy âm sắc; không phải huấn luyện lại mô hình.

Gói này giữ bản sửa WinError 2 với tệp `__init__.py.part` sau khi đã tải trọng số. Tệp nguồn rỗng được tạo và kiểm tra checksum trước khi dùng. Nếu đang dùng bản 0.4.x, **đóng Studio và bộ cài, giải nén đè mã mới vào đúng thư mục đang dùng, giữ nguyên `.data`**, rồi chạy `CHAY-STUDIO.bat`.

Bộ cài vẫn tạo môi trường riêng để tránh WinError 32 khi pip cài đè tệp SymPy/Torch đang bị giữ. Nếu vẫn bị tiến trình giữ tệp, khởi động lại Windows trước khi thử lại; không cần chạy quản trị hoặc cài Visual C++ Build Tools.

## Cài trên Windows

1. Cài **Python 3.12.10 Windows 64-bit** từ https://www.python.org/downloads/release/python-31210/ , bật Python Launcher. Không cần gỡ Python 3.15 đang có.
2. Lần đầu: giải nén ZIP vào thư mục có quyền ghi. Đang dùng `E:\voi hmong\Hmong-Studio-Trang`: đóng Studio/bộ cài, giải nén ZIP vào **`E:\voi hmong\`** và chọn thay thế tệp để cập nhật đúng thư mục `Hmong-Studio-Trang` hiện có. Giữ `.data`; tránh lồng thêm một thư mục `Hmong-Studio-Trang` bên trong thư mục cũ. Không di chuyển `.venv` hoặc các thư mục `.venv-clone-*` sang nơi khác.
3. Bấm đúp **`CHAY-STUDIO.bat`**. Chờ quá trình cài/kiểm tra hoàn tất; Studio sẽ tự mở trong trình duyệt sau khi máy chủ sẵn sàng. Nếu bị ngắt, chạy lại chính file này để tiếp tục; không đổi checksum hoặc tắt TLS. Nếu trình duyệt không tự mở, dùng địa chỉ hiện trong cửa sổ lệnh.
4. Giữ cửa sổ lệnh mở khi dùng Studio. Nhấn Ctrl+C để đóng. Những lần sau chỉ bấm đúp **`CHAY-STUDIO.bat`**; có thể tạo voice cục bộ khi không có Internet sau khi cài xong. Nếu trình duyệt còn giao diện cũ, nhấn Ctrl+F5.

`install_clone_ai.bat` và `start.bat` vẫn có cho việc cài/mở riêng; dùng `CHAY-STUDIO.bat` thì không cần chạy hai file đó. `install_local_ai.bat` gọi bộ cài nhân bản; `install_mms_asr.bat` chỉ dành cho MMS/ASR riêng. Bộ cài tạo môi trường có tên `.venv-clone-<mã>` và chỉ chọn nó sau khi mọi kiểm tra đạt. `.venv` cũ không bị cài đè. Nếu cài lỗi, môi trường đang dùng và mô hình/giọng đã lưu được giữ nguyên; lần thử lại tạo môi trường mới. Hai bộ cài không được chạy cùng lúc.

Bộ cài mới chọn CPython 3.10–3.12 x64, ưu tiên 3.12; giữ bản sao môi trường không tương thích thay vì xóa. Dữ liệu `.data` được giữ riêng. Nếu muốn chuyển mẫu cá nhân từ bản cũ, sao chép `.data/clones` khi cả hai bản đã tắt.

Khuyến nghị **RAM 16 GB trở lên**, chừa ít nhất khoảng 15 GB đĩa trống cho mô hình/thư viện và dung lượng cho sản phẩm. Lượt đầu phải nạp mô hình; CPU có thể chậm. Nếu xuất hiện lỗi DLL của Torch/ONNXRuntime, kiểm tra Microsoft Visual C++2015–2022 x64 Redistributable chính thức; không cần bộ biên dịch Build Tools cho quy trình cài này. Windows launcher chưa được chạy trên Windows thật trong phiên kiểm thử này.

**Nếu có GPU NVIDIA:** đóng Studio rồi chạy `CAI-NVIDIA.bat`. File này cài PyTorch/Torchaudio 2.6 CUDA 12.4 vào môi trường riêng, kiểm tra GPU bằng phép tính thật rồi mới chọn nó. Máy cần driver tương thích; không dùng file này cho AMD/Intel hoặc máy chỉ có CPU. Cài GPU lỗi sẽ giữ môi trường cũ. Sau khi cài GPU thành công, các lần sau chạy `CHAY-STUDIO.bat` sẽ tiếp tục dùng cấu hình GPU đó. Chưa thử GPU thực tế trong phiên này, không cam kết tốc độ hoặc VRAM cho mọi card.

## Tạo voice

- Chọn **Hmong Trắng**, rồi **Giọng nữ** hoặc **Giọng nam**. Hai mẫu chính xác người dùng cung cấp đã đi kèm; không cần thu lại bằng micro.
- Nhập lời Hmong RPA, tối đa **1.000.000 ký tự/lượt** khi dùng mẫu giọng với CosyVoice cục bộ. Có thể nhập TXT/SRT hoặc dự án JSON tối đa 8 MB; đoạn lời mới không cần trùng với lời trong mẫu. Tệp SRT tính cả mốc thời gian vào giới hạn ký tự.
- Review được chọn sẵn; có thể đổi sang Tự nhiên, Kể chuyện, Quảng cáo, Tin tức, Thư giãn, Ấm áp, Vui vẻ hoặc Buồn. Thanh tốc độ điều chỉnh nhịp đọc, không phải tốc độ tính toán.
- Bấm **Tạo voice**. Nút và thanh tiến độ hiện % theo các đoạn đã xử lý, kèm số đoạn, thời gian đã chạy và thời lượng âm thanh. Đây là tiến độ công việc, không phải dự đoán thời gian còn lại; đoạn dài có thể giữ cùng % trong lúc mô hình suy luận. Chỉ đạt 100% sau khi WAV đã hoàn tất và được kiểm tra.
- **Dừng** kết thúc tiến trình suy luận và dọn tệp tạm của lượt đó; lượt sau cần nạp lại mô hình. Hoàn tất bình thường thì giữ mô hình/mẫu trong bộ nhớ cho lượt kế tiếp. Bản thu trước được giữ khi tác vụ thất bại/hủy.
- Khi hoàn tất, nghe và bấm **Tải toàn bộ WAV**. Bản trên 25 MB dùng phát/tải trực tiếp để tiết kiệm RAM; công cụ cắt chỉ dùng cho bản ngắn. WAV tối đa 24 giờ/lượt (khoảng 4,15 GB mono 24 kHz PCM16), cần chừa dung lượng tương ứng và giữ Studio mở. Tải trước khi tắt máy chủ; chỉ giữ tối đa 10 kết quả tạm. Kịch bản tạo ra hơn 24 giờ cần chia nhỏ.

## Review theo mốc thời gian SRT

Chọn **Tự nhận dạng** hoặc **SRT**, nhập tệp `.srt` hay dán như sau. Nút **Mẫu review SRT** cũng nạp ví dụ; tệp đi kèm là `examples/review-hmong.srt`.

```srt
1
00:00:00,200 --> 00:00:02,700
Nyob zoo.

2
00:00:03,000 --> 00:00:09,000
Hnub no peb saib qhov no ua ke.
```

Tool chỉ đọc lời, không đọc số thứ tự hoặc mốc giờ. WAV bắt đầu từ 0; giữ khoảng lặng trước, giữa và sau lời trong từng mốc. Lời vượt khoảng thời gian được tăng tốc giữ cao độ tối đa 2 lần; nếu vẫn quá dài thì báo rõ đoạn cần nới thời gian hoặc rút ngắn lời, không cắt mất câu. Mốc chồng lấn, sai thứ tự, thiếu lời hoặc quá 24 giờ sẽ bị từ chối trước khi tạo. SRT cần bộ máy CosyVoice cục bộ và mẫu nam/nữ hoặc mẫu riêng.

CosyVoice dùng tối đa 10 giây đầu mẫu, không yêu cầu bản chép mẫu trong chế độ instruct2. Có thể tải thêm mẫu riêng dài 3–60 giây / 20 MB, nhập tên và xác nhận quyền sử dụng. Ô bản chép là tùy chọn; chỉ dịch vụ ngoài theo hợp đồng cũ có thể yêu cầu nó.

Các cách đọc được gửi thành chỉ dẫn suy luận thực tế, không giả lập nhân bản bằng đổi cao độ. Mức độ biểu cảm, độ giống mẫu và cách phát âm cần nghe kiểm tra; chưa được đánh giá bởi người bản ngữ và không cam kết phát âm chuẩn mọi từ. Micro chỉ dùng khi muốn thu mẫu mới. Lỗi quyền micro không chặn chọn mẫu nam/nữ hoặc tạo voice.

## Đã xác minh

Linux, CPU 4 threads, không GPU:

- Toàn bộ118 tệp mô hình/mã nguồn được đối chiếu SHA256 hoặc Git blob SHA1 theo snapshot được ghim; trọng số chỉ nạp bằng `weights_only=True`.
- Giọng nữ tạo thật câu **“Nyob zoo, kuv hais lus Hmoob.”**: WAV PCM16 mono 24 kHz, 2,71 giây; lượt lạnh khoảng64,7 giây, RAM đỉnh khoảng7,84 GiB.
- Giọng nam, cách đọc Review, cùng câu trên: tạo thật qua giao diện/API, WAV 2,51 giây; lượt này khoảng93,6 giây. Đây là số đo máy kiểm thử, không bảo đảm tốc độ trên máy khác.
- Nút Dừng đã kết thúc worker thật, sau đó tạo lại thành công. Chọn mẫu/generate không yêu cầu micro. Desktop/mobile 390 px không tràn ngang hoặc lỗi JavaScript.
- 152 kiểm thử Python đạt, gồm kiểm tra Qwen thật cỡ nhỏ: trạng thái ẩn và bộ nhớ KV khớp chính xác qua bước đầu và hai bước có cache, trọng số không đổi, phép tính từ vựng không chạy. Giữ các kiểm tra cache mẫu, ghi WAV ra đĩa, worker dùng lại, giới hạn 1 triệu ký tự, SRT, tiến độ, cài GPU và tải Range. Kết quả 1 giờ WAV trong kiểm thử streaming là dữ liệu thử, không phải đã tạo 1 giờ lời Hmong thật; cũng chưa tạo đủ 1 triệu ký tự bằng mô hình thật.
- 7 nhóm kiểm tra Chromium mới và 8 kiểm tra micro đạt: Review mặc định, tiến độ không tự nhảy, Dừng giữ bản thu trước, nhập 1 triệu ký tự, kết quả nhiều GB dùng URL trực tiếp, dự án cũ và giao diện mobile. Giữ nguyên kiểm chứng mở trình duyệt sau khi máy chủ sẵn sàng từ bản trước.
- Đã thử thiếu toàn bộ 12 tệp rỗng trên snapshot thật: xác minh đủ 118 tệp mà không gọi mạng hay sửa trọng số lớn. Bản 0.4.1 đã qua kiểm tra môi trường do bộ cài tạo và 8 kiểm tra micro trong Chromium. Đã giải mã WAV và xác minh tín hiệu khác 0; kết quả này không thay thế việc nghe chất lượng/phát âm.

## Nguồn và kỹ thuật

Mô hình: https://huggingface.co/Xuajpaj2026/hmong-tts-weights , revision `5663e0df2589c2ca2403cd327a52702c3ff96e8f`. Tác giả có cấu hình chỉ dẫn White Hmong RPA. Source/license CosyVoice và Matcha được giữ trong snapshot; không chạy wrapper sửa checkpoint của tác giả. App chỉ nạp cấu hình suy luận đã kiểm tra; không cài thành phần huấn luyện CUDA/pyworld.

Mặc định snapshot nằm trong `.data/models/hmong-cosy`; có thể đặt `HMONG_COSY_DIR` trỏ tới snapshot đã xác minh. Chạy Linux: cài Torch/Torchaudio 2.6 CPU khớp nhau, `pip install -r requirements-cosy.txt`, `python prepare_clone_model.py`, rồi `python -m uvicorn app:app --host 127.0.0.1 --port 8090 --no-access-log`. FFmpeg/ffprobe cần có trong PATH. Không công khai trực tiếp dịch vụ lên Internet; app chưa có đăng nhập.

Bộ tải có thể tiếp tục tệp `.part` và chỉ ghi marker ready sau khi toàn bộ checksum đạt. Mã suy luận đặt chế độ offline trước khi nạp thư viện Hub. Nếu chủ động cấu hình `HMONG_CLONE_URL`/`HMONG_TTS_URL`, mẫu/lời có thể gửi tới dịch vụ đó khi dùng luồng từ xa; khi CosyVoice cục bộ sẵn sàng thì mẫu nam/nữ và mẫu riêng ưu tiên xử lý cục bộ.
