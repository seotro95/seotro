# Voice Studio Riêng Portable 1.2 · Đa quốc gia, ưu tiên tốc độ

**[Tải ZIP Windows 10/11 x64, 2,02 GB](https://github.com/seotro95/seotro/releases/download/voice-standalone-portable-39002758326/Voice-Studio-Rieng-1.2.0-Portable-Windows-x64.zip)**

1. Giải nén **toàn bộ ZIP** sang thư mục mới.
2. Mở **MO_TOOL.bat**. Không cần cài Python, FFmpeg, thư viện, API key hoặc tải mô hình.

Bổ sung **16 giọng có sẵn theo quốc gia**: Mỹ, Anh, Pháp, Đức, Tây Ban Nha, Ý, Brazil, Nga, Hà Lan, Bỉ, Ba Lan, Thụy Điển, Ukraine, Séc, Đan Mạch và Romania. Tìm quốc gia/ngôn ngữ, chọn giọng và tạo mẫu nghe thử. Các giọng quốc tế Piper chạy offline trên CPU.

**Nhân bản tiếng Việt** mặc định tự chọn Nano 4 bước, CPU/RAM tự động, giữ đúng mẫu giọng của bạn. Có thể chọn 8/16 bước hoặc Tiêu chuẩn nếu cần chất lượng cao hơn; ít bước có thể giảm độ tự nhiên/độ giống mẫu. Nút Ưu tiên tốc độ giữ nguyên giọng và ngôn ngữ đang chọn. Quốc tế Piper là giọng có sẵn; gói không kèm mô hình nhân bản quốc tế Qwen.

Tối đa **200.000 ký tự**; nhập TXT/SRT, xuất WAV/MP3/TXT/SRT; có lời đọc, kể chuyện, bản tin/review theo kịch bản, lịch sử, dừng/tiếp tục và ghép các đoạn thành bản thu hoàn chỉnh.

**Đã kiểm tra trực tiếp [Windows](https://github.com/seotro95/seotro/actions/runs/39002758326)**: toàn bộ kiểm tra ứng dụng, thư viện, Python đi kèm sau khi chuyển thư mục có khoảng trắng, chặn mạng bên ngoài, tạo giọng/nhân bản Nano và Turbo, tạo âm thanh thật với đủ 16 giọng Piper, xuất tệp và mở launcher. Gói đã qua CRC và SHA256 trước khi tải lên. Dữ liệu kiểm thử được dọn trước đóng gói.

Hai phép đo bản dài trên máy thử **Linux AMD EPYC, hạn mức 4 lõi CPU / 32 GiB RAM, không NVIDIA**:

| Giọng | Âm thanh WAV | Thời gian đầu cuối |
| --- | --- | --- |
| Nhân bản Việt Nano, mặc định 4 bước | 64 phút 55,5 giây | 82,9 giây |
| Mỹ Joe, Piper | 69 phút 55,3 giây | 78,7 giây |

Đều tạo mới tất cả các đoạn, giữ đủ lời và đúng thứ tự, không tăng số đo bằng khoảng lặng. Mẫu nhân bản là âm thanh tổng hợp kỹ thuật; chưa đánh giá độ giống người thật. **Tốc độ thực tế phụ thuộc máy, giọng và ngôn ngữ**; toàn bộ một giờ chưa được đo trên máy Windows của bạn. Dùng Đo tốc độ thực trong tool. [Báo cáo kiểm tra](validation-1.2.0.json).

Khi cập nhật: tắt tool, sao lưu `app/.data`, giải nén bản mới sang thư mục mới. Nếu giữ dữ liệu cũ, chuyển các thư mục con `voices`, `jobs`, `audio`, `parts` vào `app/.data` mới; dùng mô hình đi kèm bản mới.

SHA256: `1ef741296c4f50413fcdc9cdb24a7278dddcb9e51ab9a1de4d9041947441362a`

[Thông tin tệp](portable-1.2.0.json) · [Mã nguồn](../../voice-studio-standalone) · [Trang tải dự phòng](https://github.com/seotro95/seotro/releases/tag/voice-standalone-portable-39002758326)

---

## Các bản cũ

# Bản đầy đủ Portable 1.1.1 — Giải nén rồi mở tool

**[Tải ZIP Portable Windows 10/11 x64, khoảng 1,17 GB](https://github.com/seotro95/seotro/releases/download/voice-standalone-portable-38999293928/Voice-Studio-Rieng-1.1.1-Portable-Windows-x64.zip)**

1. Giải nén **toàn bộ ZIP**.
2. Mở **MO_TOOL.bat**.

Có sẵn Python, toàn bộ thư viện chạy giọng, FFmpeg, Nano/Nano nhân bản và Turbo tiếng Việt. Không cần cài đặt, API key hoặc tải thêm mô hình tiếng Việt. Chọn mẫu giọng của bạn rồi bấm **Ưu tiên tốc độ** nếu cần nhân bản nhanh trên CPU. Gói này không kèm Qwen quốc tế.

Đã vượt qua [kiểm tra trực tiếp Windows](https://github.com/seotro95/seotro/actions/runs/38999293928): chạy bằng Python đi kèm tại đường dẫn có khoảng trắng, chặn kết nối tải bên ngoài, tạo giọng và nhân bản Nano/Turbo thật, xuất WAV/MP3/TXT/SRT và mở launcher. Dữ liệu kiểm thử đã được dọn khỏi gói; mẫu và bản thu của bạn lưu ở `app/.data`. Sao lưu thư mục này khi cập nhật.

SHA256: `07abd12010ae348356c6295bd57f87ca73aa21dd5270f423ef80d0fc1a6ef3b5`

---

## Gói mã nguồn/bộ cài cũ

# Voice Studio Riêng 1.1 · Nhân bản tiếng Việt trên CPU

**[Tải bản cập nhật 1.1 cho Windows 10/11 x64](./Voice-Studio-Rieng-1.1.0-Windows-10-11.zip?raw=true)**

Giải nén toàn bộ ZIP. Gói cần Python 3.12 64-bit và Internet để cài thư viện/tải mô hình lần đầu. Mã nguồn có thể xem trong [voice-studio-standalone](../../voice-studio-standalone).

## Dùng giọng nhân bản nhanh

1. Nếu cài mới, chạy `CAI_DAT.bat`.
2. Chạy `TAI_GIONG_NHAN_BAN_NHANH.bat` một lần để chuẩn bị mô hình nhân bản Nano.
3. Chạy `MO_TOOL.bat`, chọn mẫu giọng tiếng Việt của bạn rồi bấm **Ưu tiên tốc độ**. Tool giữ nguyên mẫu, dùng Nano 4 bước và CPU tự động.
4. Bấm **Đo tốc độ thực** để đo trên máy hoặc **Tạo giọng nói** để xử lý văn bản.

Giới hạn 200.000 ký tự mỗi tác vụ, nhập TXT/SRT và xuất WAV/MP3/TXT/SRT. Giọng tiêu chuẩn, quốc tế và Windows vẫn có lựa chọn riêng. Nano 4 bước có thể giảm độ tự nhiên/độ giống giọng; nghe thử rồi chọn 8/16 bước hoặc nhân bản tiêu chuẩn khi cần.

## Kết quả kiểm chứng

Máy thử Linux AMD EPYC có hạn mức **4 lõi CPU / 32 GiB RAM**, không dùng NVIDIA, đã tạo **64 phút 56,6 giây âm thanh nhân bản trong 80,5 giây**, gồm nạp mô hình và mã hóa mẫu từ worker lạnh. Tạo WAV rồi xuất thêm MP3 tổng **92,1 giây**. Đủ 844 đoạn từ 80.053 ký tự, không dùng lại WAV, không chèn khoảng lặng để tăng số đo. Mẫu giọng kiểm tra là âm thanh tổng hợp do tool tạo; chưa đánh giá mức độ giống người thật hay phát âm từng từ.

Đây là kết quả trên máy thử, **chưa kiểm chứng trực tiếp máy Windows của bạn**. Xem [HIEU_NANG.md](../../voice-studio-standalone/HIEU_NANG.md) và [BENCHMARK_RESULT.json](../../voice-studio-standalone/BENCHMARK_RESULT.json) để biết cách đo.

## Cập nhật an toàn

Tắt tool, sao lưu `app/.data`, rồi chép tệp mới vào thư mục cũ; giữ nguyên `.venv` và `app/.data`. Chạy bộ tải nhân bản nhanh và mở lại tool, kiểm tra phiên bản 1.1.0. Hướng dẫn đầy đủ trong [DOC_TRUOC.md](../../voice-studio-standalone/DOC_TRUOC.md).

Gói không chứa môi trường Python đã cài, trọng số mô hình, dữ liệu giọng cá nhân hoặc API key. Tên ZIP không có số phiên bản được cập nhật thành cùng bản 1.1 để liên kết tải cũ tiếp tục dùng được.

SHA256: `4b6917e46c16beee0fe8ef6eb470a01cbe6b303f8dc5ee4b274f6e855af2a158`
