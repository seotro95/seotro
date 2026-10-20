# Kiểm tra gói Hmong Voice Studio 0.8.1

**Cập nhật sau phát hành:** đã nhận tên phát hiện Defender `Trojan:Script/Sabsik.FL.A!ml` và xác nhận của người dùng rằng 0.8.1 cũng bị chặn. Cả hai ZIP đã rút khỏi nhánh tải. Sau đó ClamAV 1.4.3 với dữ liệu chính thức đã xác minh chữ ký quét hai ZIP và **260/260 tệp giải nén, exit 0, không phát hiện**; daily 28157 tạo 18/10/2026. [Báo cáo quét thực tế](security-scan/2026-10-20/ACTUAL_SCAN_REPORT.md). **Cảnh báo Defender chưa được giải quyết.** Các phần bên dưới là ghi chép lịch sử trước ảnh và trước lần quét thành công; trạng thái hiện tại ở [thông báo bảo mật](../HMONG_VOICE_STUDIO_SECURITY_NOTICE.md). Không coi báo cáo này hoặc việc đổi phiên bản là xác nhận an toàn.

Ngày kiểm tra: **20/10/2026 UTC**. Nguồn: component `hmong-studio`, repository `seotro95/seotro`; bản trước khi sửa là commit `8f4b6ad` (0.8.0).

## Kết luận và giới hạn

**CHƯA QUÉT ANTIVIRUS THÀNH CÔNG. Không xác nhận gói sạch virus; chưa xác nhận hết cảnh báo tải.** Người dùng báo cảnh báo từ tệp tải về nhưng chưa có tên mối đe dọa, phần mềm chặn hoặc đường dẫn tệp con. Chưa xác định được nguyên nhân; không kết luận báo nhầm.

Đã cài công cụ ClamAV thật, phiên bản **1.4.3**, bằng cách lấy gói Debian 13 chính thức qua HTTPS và kiểm tra metadata APT có chữ ký. Công cụ được giải nén trong workspace, không nằm trong ZIP app. Gói Debian không có sẵn dữ liệu nhận diện. `freshclam` tải dữ liệu chính thức thất bại, exit **11**. Các yêu cầu HTTPS tới `https://database.clamav.net/{daily,main,bytecode}.cvd` bị proxy từ chối **403 Forbidden**, kể cả sau khi được cấp quyền mạng. Không đổi máy chủ sang nguồn không tin cậy, không tắt TLS.

Lần gọi ClamAV cho ZIP 0.8.0 trả exit **2**, nạp **0** mẫu nhận diện và quét **0** tệp. Dòng `Infected files: 0` trong log lỗi **không phải kết quả sạch**. Phiên bản/ngày cơ sở dữ liệu: **không có**. Bằng chứng gốc ở `security-scan/`: log cập nhật, lỗi mạng, nguồn/hash gói ClamAV và lần thử quét. Lần thử cho ZIP 0.8.1 được công bố riêng ở tệp `HMONG_VOICE_STUDIO_ULTRA_FAST_0.8.1.zip.scan.json` cạnh ZIP; không sửa ZIP sau khi ghi hash/lần thử đó.

Môi trường là Linux, không có Microsoft Defender hoặc Windows/GTX 1060 thật. Không chạy hoặc kiểm chứng hành vi của toàn bộ phần mềm trên Windows. Không tải mã hoặc hai mẫu giọng lên dịch vụ quét công khai. Thư viện Python, trọng số mô hình và FFmpeg được tải lúc cài đặt **không có trong ZIP và không được bao phủ bởi kiểm tra gói này**. Cần quét antivirus với dữ liệu nhận diện cập nhật trước khi mô tả bản này là đã quét.

## Phạm vi kiểm tra mã/gói

- Kiểm tra CRC và đường dẫn ZIP trước khi sửa; đọc cả bản sao nguồn ZIP lồng trong bản 0.8.0. Không thấy đường dẫn vượt thư mục hoặc tệp thực thi PE/ELF nhúng trong lần kiểm tra này.
- Rà soát mã tải/cài đặt, lệnh hệ thống và chẩn đoán GPU. Chưa thấy bằng chứng cụ thể về thu thập thông tin đăng nhập, tắt bảo vệ Windows, tạo ngoại lệ antivirus, lưu trú khởi động, PowerShell mã hóa hoặc mã bị làm rối. Kiểm tra tĩnh không thay thế antivirus hay phân tích hành vi.
- Các tệp BAT/Python là mã nguồn đọc được; trình cài dùng pip/tải mô hình/FFmpeg cho chức năng app. Các lệnh hủy cây tiến trình phục vụ dừng tiến trình con của app. `eval()` của mô hình là chế độ suy luận PyTorch.
- Kiểm tra gói bằng danh sách tệp và SHA256; loại `.data`, môi trường Python, `.env`, cache và tệp ngoài danh sách phát hành. `FILE_SHA256SUMS.txt` phục vụ kiểm tra toàn vẹn, không phải chứng nhận an toàn.

## Thay đổi 0.8.1

1. `prepare_clone_model.py`: buộc URL ban đầu và các chuyển hướng tải mô hình dùng HTTPS. Giữ nguyên revision, kích thước, hash, tải tiếp và xác minh trước khi dùng. Thêm kiểm thử từ chối HTTP/FTP/file/data/javascript và chấp nhận chuyển hướng HTTPS.
2. `gpu_info.py`, `KIEM-TRA-GPU.bat`, `setup_env.bat`: công cụ xem GPU chỉ đọc bằng Python/Windows API và câu lệnh NVIDIA cố định, giới hạn thời gian/dữ liệu. Khi thiếu Python có hướng dẫn xem dxdiag. Không cài hoặc sửa driver; không còn cần PowerShell cho chẩn đoán này. **Không có bằng chứng câu lệnh chẩn đoán cũ gây cảnh báo.**
3. ZIP mới chỉ chứa nguồn hiện tại, mẫu, hướng dẫn, kiểm thử và bằng chứng. Không lồng bản sao nguồn lịch sử; bản sao vẫn giữ riêng trong repository. Không xóa chức năng, không đổi model/giọng hoặc cơ chế tính tốc độ.
4. Đổi phiên bản thành 0.8.1, thêm báo cáo và danh sách hash. Không tắt bảo vệ Windows, mã hóa ZIP hoặc che giấu loại tệp.

## Kiểm thử

Kết quả hồi quy được ghi trong `security-scan/regression-tests.txt`. Các kết quả đo TTS trước đó ở `PERFORMANCE_REPORT.md` và `benchmark-results/` được giữ nguyên; bản 0.8.1 không tuyên bố tăng tốc hoặc đạt 120 giây/giờ. Chưa kiểm chứng trực tiếp Windows, CUDA hoặc cảnh báo antivirus trên máy người dùng.

## Khi phần mềm bảo vệ tiếp tục cảnh báo

Giữ bảo vệ bật. Trong Windows Security → Virus & threat protection → Protection history, xem tên mối đe dọa và `Affected items`; nếu trình duyệt chặn thì lấy nguyên văn thông báo trong mục tải xuống. Dùng tên cụ thể để xác định tệp/hành vi cần điều tra tiếp. Không khôi phục hoặc chạy tệp đang bị cách ly chỉ dựa trên báo cáo này.
