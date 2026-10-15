# Engine và model được sử dụng

- **CTranslate2** (MIT) và **SentencePiece** (Apache-2.0): chạy model dịch trên CPU. Model lấy từ danh mục chính thức của Argos Open Technologies, giữ lại metadata và README của từng gói. Model Anh → Việt được đóng gói từ OPUS-MT, tác giả Jörg Tiedemann và Santhosh Thottingal; README ghi giấy phép CC-BY 4.0.
- **Piper TTS** (GPL-3.0): tạo giọng đọc cục bộ. Model được tải từ `rhasspy/piper-voices`, xác minh SHA256 LFS chính thức, và giữ `MODEL_CARD` cạnh model. Giọng `vi_VN-vais1000-medium` dùng dữ liệu VAIS-1000 Vietnamese Speech Synthesis Corpus, giấy phép CC-BY 4.0, tinh chỉnh từ giọng Lessac tiếng Anh. Xem https://ieee-dataport.org/documents/vais-1000-vietnamese-speech-synthesis-corpus và MODEL_CARD cho thông tin nguồn.
- **faster-whisper** (MIT): nhận dạng lời nói, sử dụng các model Whisper chuyển đổi từ `Systran/faster-whisper-*`. Model tự tải qua Hugging Face, giữ cache để dùng offline.
- **yt-dlp**, **FastAPI**, **Uvicorn**, **HTTPX**, **Pydantic**, **PyAV**, **langdetect** và **ONNX Runtime**: tải nội dung, giao diện local, đọc media và chạy inference. Thông tin giấy phép đầy đủ của engine nằm trong các gói Python cài đặt.
- **FFmpeg/FFprobe**: người dùng cung cấp bản binary phù hợp và giấy phép đi kèm; ZIP của tool không chứa FFmpeg hoặc các tệp EXE của VideoToolsPro.

Gói tool không chứa model/binary của VideoToolsPro, cookie, khóa kích hoạt hoặc tài khoản AI. Mã nguồn ứng dụng này được xây dựng riêng theo mô tả chức năng; model công khai được tải từ nguồn upstream ghi ở trên.

- **edge-tts 7.3.1** (LGPL-3.0): thư viện mã nguồn mở https://github.com/rany2/edge-tts, truy cập giọng online Microsoft Edge. Danh mục/âm thanh thuộc dịch vụ Microsoft và chịu điều kiện sử dụng của nhà cung cấp. Không phải thư viện CapCut và không phải sản phẩm Microsoft chính thức.
- **OpenAI Responses API / Google Gemini generateContent API**: kết nối HTTPS tùy chọn; người dùng cung cấp API key và chịu hạn mức tài khoản. Tool không phân phối tài khoản hoặc key.
