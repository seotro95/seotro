# Kiểm chứng Voice Studio 3.7.0 · 22/10/2026

## Hồi quy và kiểm tra mã

- Bộ kiểm thử trên Linux/Python 3.12: **148 đạt, 1 bỏ qua**. Ca bỏ qua kiểm tra khóa chia sẻ tệp Win32, cần Windows thật. Một cảnh báo thư viện Starlette/AnyIO về API sắp ngừng dùng; không có lỗi kiểm thử.
- 16 kiểm thử liên quan cài đặt, chuẩn bị model, nhân bản và kiểu đọc chạy lại sau thay đổi installer cuối đều đạt.
- JavaScript: `node --check` qua các tệp trong `static/`; Python compile và cú pháp shell qua.
- Môi trường kiểm tra dùng 90 gói; `uv pip check` báo tương thích. Không cài PyTorch cho Nano/Turbo ONNX. Trình cài ứng dụng bootstrap pip bằng ensurepip trước khi cài thư viện.

## Sinh âm thanh thực tế

Đã tải và kiểm tra mô hình Nano preset, các đồ thị nhân bản Nano, Turbo preset và nhân bản Turbo bằng ONNX CPU. Các lệnh `prepare_models.py vi` và `prepare_models.py vieneu` hoàn tất với âm thanh kiểm tra thật. Marker chỉ được ghi sau khi có WAV đủ mẫu, hữu hạn và không im lặng. Mô hình nhân bản Nano có marker riêng; chỉ tải preset chưa được tính là đã sẵn sàng nhân bản.

Qua API thật, worker đặt chế độ offline:

- Nhập mẫu âm thanh QA tổng hợp, đăng ký Nano clone và tạo **văn bản khác bản mẫu**.
- Tạo TXT/Review thành MP3 dài khoảng 4,665 giây. Tạo SRT/Kể chuyện hai câu, giữ timeline 12 giây.
- Tải MP3/WAV/TXT/SRT đều trả 200 và có nội dung; WAV có tín hiệu hữu hạn, khác im lặng.
- Kiểm thử lỗi có WAV rỗng/hỏng/NaN, thử lại tối đa ba lần, không cache tệp hỏng. Mẫu tham chiếu chỉ mã hóa một lần trong cấu hình model đang dùng; tệp làm sạch được dọn sau khi xử lý.

Qua Chromium với mô hình thật:

- Trang mở vào tạo voice; nhập UTF-8 TXT và UTF-16 có BOM SRT, xuất lại và đối chiếu nội dung/mốc.
- Nano/Review tạo WAV dài 6,645 giây; tải WAV/TXT/SRT thành công.
- Nhập mẫu QA tổng hợp qua form, chọn Nano clone vừa tạo; Kể chuyện sinh WAV mới dài 5,748 giây.
- Không có lỗi JavaScript. Nút sửa model hiện cạnh chọn giọng, gửi đúng engine nhân bản; kiểm tra nút sửa đã chặn yêu cầu tải lại để không tải dư.

Các kiểm tra tín hiệu/luồng dữ liệu không phải đánh giá thính giác về độ tự nhiên, đọc đúng từng từ hoặc độ giống người nói. Chưa đánh giá nhân bản với giọng người thật của người dùng.

## Tốc độ

CPU AMD EPYC 7763, 3 vCPU, không GPU. Nano 4 bước, một tiến trình, hai luồng ONNX; đoạn thử tiếng Việt chia 18 phần:

| Âm thanh đầu ra | Thời gian xử lý | Tốc độ | Ngoại suy 1 giờ |
| --- | --- | --- | --- |
| 89,840 giây | 12,152 giây | 7,39× | 487 giây, khoảng 8,1 phút |

Chưa đạt 30× (2 phút/giờ). Đây là phép đo mẫu đã tải mô hình, không phải chạy đủ một giờ; không gồm cài/tải thư viện/model. Dữ liệu không dùng lại các đoạn đã hoàn tất. Kiểu đọc có khoảng nghỉ hoặc thay nhịp, giọng nhân bản và máy khác có tốc độ khác; không dùng một số đo để cam kết tất cả tác vụ.

## Phạm vi chưa kiểm chứng

- Batch/trình cài trên Windows thật, gói EXE Portable và thao tác GPU.
- Sinh âm thanh Qwen quốc tế; tùy chọn này tải riêng. Chuẩn bị Qwen hiện xác minh nạp mô hình, không có kiểm tra giọng thực tế trong phiên này.
- Bản thu dài đủ một giờ/ba giờ, căn từng từ, khớp khẩu hình hoặc độ giống giọng người dùng.

Gói giao chứa mã nguồn và trình cài/chạy, không chứa runtime/FFmpeg/trọng số hoặc thư mục dữ liệu cá nhân. Mẫu WAV minh họa, nếu kèm theo, là kết quả QA tổng hợp từ giọng có sẵn.
