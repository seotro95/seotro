# Hmong Studio 0.3.1 — hai mẫu mặc định và thư viện giọng cục bộ

Chạy trên máy, không cần API key. Hai tệp người dùng gửi được đặt làm mẫu mặc định **Hmong Trắng · Nam** (18,94 giây) và **Hmong Trắng · Nữ** (22,39 giây); bản nữ được chọn khi mở tool. Bản gốc được giữ nguyên để nghe đối chiếu.

Đã có soạn/nhập/xuất TXT, dự án JSON, thu micro, nhập âm thanh, dạng sóng, cắt và chỉnh âm lượng, xuất WAV/MP3, thư viện giọng cá nhân (thêm/nghe/chọn/xóa), chọn đoạn tham chiếu và lưu lời mẫu cho hai giọng mặc định.

**Chưa có bản đọc Hmong mới được kiểm chứng.** Giao diện và xử lý âm thanh hoạt động độc lập với mô hình. Mô hình F5-Hmong cộng đồng là lựa chọn thử nghiệm; chưa xác minh đúng Hmong Trắng, độ giống giọng hoặc giấy phép trọng số. Máy cloud hiện bị từ chối tải Hugging Face (proxy CONNECT 403), nên chưa cài trọng số hoặc chạy inference thật. Các kiểm thử mô phỏng engine không chứng minh chất lượng giọng.

## Khởi động

- Windows: ưu tiên Python 3.12 64-bit, cài FFmpeg/ffprobe, chạy `start.bat`. Launcher tự tìm Python 3.12, 3.11 hoặc 3.10; không chọn Python 3.15.
- Linux/macOS: cài Python 3.10–3.12 và FFmpeg/ffprobe, chạy `bash start.sh`.
- Cloud đã chuẩn bị: trong thư mục này chạy `/workspace/.venvs/seotro-hmong/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8090`.

Giữ dịch vụ trên loopback; tool chưa có đăng nhập. Lần đầu cài thư viện cần Internet, mẫu giọng và dữ liệu của tool lưu trên máy. `.data/profiles` lưu giọng cá nhân, `.data/references` lưu đoạn/lời của hai giọng mặc định. Có thể đổi thư mục dữ liệu bằng `HMONG_STUDIO_DATA`. Dự án trình duyệt chỉ chứa kịch bản/thiết lập, cần tải âm thanh riêng.

## Sửa lỗi PyYAML / Visual C++ khi máy có Python 3.15

Nếu log có `Python315`, `cpython-315`, `Failed building wheel for pyyaml` và `Microsoft Visual C++ 14.0 or greater is required`, bộ cài cũ đã dùng Python quá mới so với các thư viện AI. Dùng Python 3.12 64-bit để nhận các gói đã biên dịch.

1. Cài [Python 3.12.10 Windows 64-bit từ python.org](https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe), bật Python Launcher. Có thể giữ Python 3.15 trên máy.
2. Dùng bản 0.3.1, giải nén toàn bộ vào thư mục mới hoặc sao lưu thư mục tool trước khi cập nhật. Không chỉ chép riêng tệp BAT: cần cả `prepare_env.bat` và `bootstrap.py`.
3. Chạy `start.bat` để mở tool hoặc `install_local_ai.bat` để cài thư viện AI tùy chọn. Bộ chuẩn bị chọn Python 3.10–3.12 64-bit và kiểm tra `.venv` trước khi cài.

Nếu `.venv` cũ dùng Python không hỗ trợ, nó được **đổi tên để giữ lại**, rồi tạo môi trường mới. Không xóa `.data` hoặc các mẫu giọng. Nếu chưa tìm thấy Python phù hợp, bộ cài dừng và chỉ rõ cần cài Python 3.12. Các lệnh cài PyYAML chỉ chấp nhận wheel, tránh chuyển sang biên dịch C++ âm thầm. Bản sửa launcher này không kèm thêm trọng số AI.

## Chuẩn bị hai giọng mặc định

1. Chọn mẫu Nam hoặc Nữ, nghe bản gốc.
2. Chọn một đoạn rõ lời dài **3–8 giây**, bấm nghe đoạn đã chọn.
3. Chép đúng lời Hmong của đoạn đó và bấm **Lưu đoạn / lời mẫu**. Người dùng có thể bổ sung sau; tool không đoán bản chép.
4. Sau khi mô hình cục bộ đã cài, chọn giọng tương ứng ở phần đọc và tạo một câu ngắn để nghe kiểm tra.

Giọng cá nhân nhận mẫu 3–30 giây để lưu thư viện; F5 yêu cầu **3–8 giây** với lời khớp đoạn. Có thể nhập mẫu vào bàn biên tập, cắt, rồi bấm dùng âm thanh đang mở. Lưu mẫu là hồ sơ tham chiếu, không tự huấn luyện mô hình.

## Nhân bản cục bộ F5-Hmong (thử nghiệm, chưa inference thật)

Nguồn cộng đồng: https://github.com/YangNobody12/F5-TTS-Hmong ; checkpoint được tác giả dẫn tới https://huggingface.co/Pakorn2112/F5TTS-Hmong . Kiến trúc dùng **F5TTS_Base**, không phải F5TTS_v1_Base. Cần xác nhận vocabulary khớp checkpoint và giấy phép trọng số trước khi sử dụng. Không tự tải mô hình trong lúc bấm tạo giọng.

Cài bộ `f5-tts`/PyTorch phù hợp theo tài liệu upstream https://github.com/SWivid/F5-TTS . Phần tích hợp được đối chiếu API `f5-tts==1.1.22`; chưa cài bộ suy luận này trên máy cloud do chưa lấy được mô hình. Chuẩn bị đầy đủ các tệp cục bộ rồi đặt:

| Biến | Nội dung |
|---|---|
| `HMONG_F5_CHECKPOINT` | Đường dẫn checkpoint Hmong `.safetensors` (tác giả nêu `model_159952.safetensors`) |
| `HMONG_F5_VOCAB` | Tệp vocabulary khớp checkpoint |
| `HMONG_F5_VOCODER` | Thư mục Vocos `charactr/vocos-mel-24khz` chứa `config.yaml` và `pytorch_model.bin` |
| `HMONG_F5_DEVICE` | `cpu` (mặc định), `cuda` hoặc `mps` |

Studio dùng tệp cục bộ, không gọi API và không tự nhận dạng lời mẫu bằng Whisper. Giới hạn F5: 2.000 ký tự/lượt, 10 phút đầu ra và một lượt tạo đồng thời. Cảm xúc riêng chưa được hỗ trợ. Trạng thái sẵn sàng chỉ kiểm tra điều kiện cài đặt; cần tạo và nghe bản đọc thật để đánh giá phát âm/phương ngữ.

Chế độ mặc định `HMONG_ENGINE=local` bỏ qua các URL dịch vụ từ xa cũ. Hợp đồng adapter HTTPS ở tài liệu lịch sử bên dưới chỉ được bật khi người vận hành chủ động đặt `HMONG_ENGINE=remote`.

## Kiểm thử phát triển

```sh
python -m pip install -r requirements.txt pytest
python -m pytest tests -q
node --check static/app.js
```

Các test FFmpeg kiểm tra tệp âm thanh thật, lưu/xóa mẫu và xuất MP3/WAV. Test tích hợp engine dùng mô phỏng, không thay cho inference thật. Chưa thử launcher trên Windows thật.

---

# Tài liệu 0.2 — AI và adapter tùy chọn

**Chưa hoàn thành AI Hmong Trắng.** Bản này bổ sung luồng tạo giọng và nhận dạng dùng mô hình cục bộ hoặc dịch vụ HTTPS, lựa chọn Hmong Trắng / Việt / Anh, và quản lý hai mẫu nam/nữ. Chưa có mô hình Hmong Trắng được xác minh, chưa tải được trọng số trong môi trường kiểm tra (Hugging Face bị chặn 403). Không hứa nhận dạng đúng Hmong, nhân bản hai giọng hoặc cảm xúc giống người thật.

## Windows

1. Cài Python 3.10–3.12, chọn Add Python to PATH.
2. Giải nén ZIP, chạy `start.bat`, giữ cửa sổ lệnh mở.
3. Mở địa chỉ hiện trong cửa sổ lệnh bằng trình duyệt trên cùng máy.
4. Muốn dùng AI cục bộ, chạy `install_local_ai.bat`. Cần Internet và vài trăm MB cho thư viện, thêm vài GB cho mô hình ASR. Nên có ít nhất 8 GB RAM trống. Cài FFmpeg từ https://ffmpeg.org/download.html và thêm vào PATH để nhận dạng audio.
5. Khởi động lại tool sau khi thay đổi biến môi trường. Không công khai máy chủ trực tiếp lên Internet: bản này không có đăng nhập.

Chạy Linux/macOS trong thư mục `hmong-studio`:

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8090
```

AI cục bộ: cài PyTorch phù hợp từ https://pytorch.org/get-started/locally/, rồi `pip install -r requirements-local.txt`. Không tắt xác minh TLS/chữ ký để tải mô hình. Launcher Windows chưa được thử trên Windows.

## Tính năng

- Kịch bản TXT, dự án JSON, lưu/mở/xóa trên trình duyệt; tối đa 10.000 ký tự. AI cục bộ nhận tối đa 2.000 ký tự/lượt.
- Hai mẫu Hmong Trắng nam/nữ do người dùng cung cấp; nghe nguyên bản, không biến mẫu thành giọng AI tự động. Không có Hmong Hoa.
- Thu micro tối đa 10 phút, nhập audio tối đa 50 MB, nghe/dạng sóng, cắt, chỉnh âm lượng và xuất WAV PCM 16-bit. Micro cần localhost hoặc HTTPS.
- Giọng nói → văn bản từ audio hiện tại, sửa kết quả, chuyển vào kịch bản hoặc tải TXT. Dùng **bản gốc**, không dùng khoảng cắt trên màn hình. ASR cục bộ chia khối 20 giây; từ ở ranh giới khối có thể sai.
- Chọn ngôn ngữ cho cả hai chiều; chọn nam/nữ và cảm xúc chỉ được mở nếu dịch vụ đã được cấu hình hỗ trợ. MMS gốc chỉ có giọng mô hình, không giả lập giới tính bằng đổi cao độ.
- Nút Lời Hmong mẫu nạp đoạn “Kuv twb hais qhia rau koj…” do người dùng gửi. Đoạn này **không khớp** hai MP3, không phải bản chép/nhãn huấn luyện.

Âm thanh không được lưu trong JSON/localStorage; tải WAV riêng trước khi đóng hoặc đổi dự án. Dự án 0.1 Hmong Trắng vẫn mở được; lựa chọn mẫu cũ chuyển về giọng gốc nếu bộ xử lý không hỗ trợ nhân bản.

## AI cục bộ

TTS dùng `AutoTokenizer` + `VitsModel`, ASR dùng `AutoProcessor` + `Wav2Vec2ForCTC`. Chỉ hỗ trợ mô hình tương thích hai kiến trúc đó; không chạy mã tùy ý từ Hub (`trust_remote_code=False`).

| Biến môi trường | Mặc định / ý nghĩa |
|---|---|
| `HMONG_LOCAL_TTS_MODEL` | Chưa đặt. Phải là model ID hoặc thư mục VITS đã xác minh đọc **Hmong Trắng**. Không tự đoán ID mô hình. |
| `STUDIO_TTS_MODEL_VI` | `facebook/mms-tts-vie` |
| `STUDIO_TTS_MODEL_EN` | `facebook/mms-tts-eng` |
| `HMONG_LOCAL_ASR_MODEL` | `facebook/mms-1b-all` hoặc thư mục mô hình tương thích |
| `HMONG_ASR_CODE` | `hmn` là mã **ứng viên**, chưa xác minh có adapter và đúng Hmong Trắng. Nếu không có trong vocab thì báo lỗi, không dùng tiếng Anh thay thế. |

Mã ASR Việt/Anh là `vie`/`eng`. Lần đầu thư viện có thể tải mô hình. Cần mở mạng tới Hugging Face và các CDN mà Hub chỉ định; có thể dùng thư mục đã tải sẵn để chạy offline. Kiểm tra `processor.tokenizer.vocab.keys()` theo tài liệu MMS để xác nhận mã ngôn ngữ. Cần cặp âm thanh và bản chép khớp để đo độ chính xác Hmong Trắng; chưa có cặp đó trong dự án này.

MMS công bố giấy phép **CC-BY-NC 4.0**; đọc giấy phép từng mô hình trước khi dùng thương mại. Tài liệu chính thức: https://github.com/facebookresearch/fairseq/tree/main/examples/mms và https://huggingface.co/docs/transformers/model_doc/mms .

## Dịch vụ có nhân bản giọng / cảm xúc

Chỉ cấu hình sau khi có dịch vụ hoặc adapter thực sự hỗ trợ Hmong Trắng. Khóa chỉ đặt trong biến môi trường máy chủ, không ghi vào Git.

TTS: `HMONG_TTS_URL` (HTTPS), tùy chọn `HMONG_TTS_TOKEN`. POST JSON:

```json
{"text":"Nyob zoo", "dialect":"mww", "voice":"hmong-white-female", "emotion":"neutral", "speed":1.0}
```

`dialect`: `mww`/`vi`/`en`; `voice`: `model-default`/`hmong-white-female`/`hmong-white-male`; `emotion`: `neutral`/`storytelling`/`warm`/`cheerful`/`sad`; tốc độ 0.5–2. Trả bytes WAV/MP3/OGG và Content-Type tương ứng, tối đa 50 MB, 120 giây, không redirect. Adapter phải tự ánh xạ ID mẫu tới hai MP3 trong `static/voices` và sử dụng mô hình nhân bản; tool không tự gửi mẫu cho dịch vụ. Chỉ đặt `HMONG_TTS_CLONING=1` và/hoặc `HMONG_TTS_EMOTIONS=1` sau khi adapter hỗ trợ thật. Các cờ chỉ khai báo cấu hình, không tự tạo năng lực cho mô hình.

ASR: `HMONG_ASR_URL` (HTTPS), tùy chọn `HMONG_ASR_TOKEN`. Nhận POST bytes audio `application/octet-stream`, query `language=mww|vi|en`. Trả JSON `{"text":"..."}`, tối đa 1 MB/50.000 ký tự, 180 giây. Nội dung được gửi tới dịch vụ tương ứng khi bấm xử lý. Không tự dịch lời.

Đây là hợp đồng adapter của studio, không phải API mặc định của nhà cung cấp. Chưa có nhà cung cấp nào được tích hợp hoặc xác minh trong bản này.

## Kết quả kiểm tra

- API/validation và luồng chuyển tiếp được kiểm tra bằng pytest; inference trong test dùng mock, **không chứng minh** chất lượng mô hình.
- Đã thử Chromium: nhập MP3, chọn ngôn ngữ, lưu dự án, xuất WAV stereo đúng 1 giây; hiển thị và chuyển kết quả ASR giả lập vào kịch bản. Không có lỗi JavaScript trong lượt thử.
- Đã cài PyTorch CPU/Transformers và import được lớp mô hình. Chưa inference với trọng số thật vì bị chặn tải từ Hugging Face (403).
- Chưa xác minh giọng Hmong Trắng, nam/nữ nhân bản, cảm xúc, nhận dạng Hmong hoặc launcher Windows. Không coi bản này là tool Hmong hoàn chỉnh.

```sh
python -m pytest tests -q
node --check static/app.js
```
