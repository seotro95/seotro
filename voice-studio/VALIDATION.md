# Kết quả xác minh

Đã chạy trên Linux x86_64, Python 3.12.14, CPU AMD EPYC (5 vCPU), không có GPU NVIDIA.

- `pytest -q tests`: **8 đạt**, một cảnh báo deprecation của Starlette/AnyIO; không có kiểm thử bị bỏ qua.
- `pip check`: không có lỗi phụ thuộc. `install.sh` đã chạy lại thành công với môi trường Python ngoài checkout.
- Chromium thật: điều hướng 4 màn hình, văn bản mẫu, thông báo mô hình thiếu, thư viện giọng, lịch sử; không có lỗi JavaScript. Bố cục máy tính 1440 px và điện thoại 390 px; không tràn ngang trên điện thoại.
- FFmpeg thật: nhập mẫu, chuyển mono 24 kHz, kiểm tra thời lượng, từ chối tệp hỏng/mẫu quá ngắn; trả lại mẫu, xóa mẫu, quản lý hàng đợi và bản thu.

## Suy luận thực tế qua API của ứng dụng

Tất cả lượt dưới đây chạy tiến trình worker với `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, dùng đường dẫn snapshot cục bộ cho Qwen. Đã kiểm tra HTTP trả âm thanh thành công, tệp giải mã được, thời lượng trên 1 giây và biên độ khác 0.

| Luồng | Mô hình | Đầu ra |
|---|---|---|
| Việt · Mai Anh | VieNeu v3 Turbo ONNX | WAV, 48 kHz, 4.72 giây |
| Việt · Nhân bản mẫu tổng hợp | VieNeu v3 Turbo ONNX | MP3 192 kbps, 48 kHz, 3.82 giây |
| Anh · Nhân bản mẫu tổng hợp | Qwen3-TTS 0.6B Base | WAV, 24 kHz, 2.95 giây |
| Anh · Aiden | Qwen3-TTS 0.6B CustomVoice | WAV, 24 kHz, 3.00 giây |
| Nhật · Ono Anna | Qwen3-TTS 0.6B CustomVoice | WAV, 24 kHz, 4.92 giây |
| Hàn · Sohee | Qwen3-TTS 0.6B CustomVoice | WAV, 24 kHz, 6.44 giây |

Mẫu nhân bản trong QA là âm thanh tổng hợp từ mô hình, không phải giọng một người dùng thật. Hồ sơ mẫu QA đã được xóa sau kiểm tra. Bản thu thử thành công được giữ trong lịch sử cục bộ; không đưa trọng số hoặc âm thanh vào gói mã nguồn.

## Giới hạn đã biết

- Chưa đánh giá nghe thủ công, độ giống một người nói thật, MOS hoặc chất lượng thương mại/phòng thu. Không hứa nhân bản chính xác 100%.
- US/UK cùng ngôn ngữ English; giọng vùng phụ thuộc mẫu/người nói. Chưa xác minh một mẫu giọng Anh Anh thực tế.
- Các ngôn ngữ còn lại lấy từ danh sách hỗ trợ chính thức của mô hình, chưa tạo âm thanh kiểm thử từng ngôn ngữ.
- Windows BAT, macOS và NVIDIA GPU chưa được chạy thử trong môi trường Linux CPU này.
- Qwen SDK in cảnh báo thiếu flash-attn (tùy chọn cho GPU) và SoX khi import. Luồng tokenizer 12 Hz được dùng ở đây vẫn vượt qua kiểm tra suy luận thật; FFmpeg được dùng để xử lý/xuất âm thanh.
- Đã sửa lỗi nạp Qwen offline bằng snapshot cục bộ; đã sửa vị trí tệp tạm VieNeu bằng lớp kế thừa cục bộ, không chỉnh sửa thư viện bên thứ ba.
- Snapshot cloud mới sau Publish chưa được xác minh. Gói mã nguồn không kèm mô hình (~5.3 GB cache); máy mới cần tải trọng số một lần.
