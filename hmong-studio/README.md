# Hmong Studio 0.2 — bản phát triển

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
