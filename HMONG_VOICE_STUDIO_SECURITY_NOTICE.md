# Cảnh báo bảo mật — Hmong Voice Studio

Cập nhật ngày **20/10/2026**, múi giờ **UTC+7**.

## Phát hiện do người dùng cung cấp

Ảnh Windows Security → Protection history ghi nhận:

- Phát hiện: **Trojan:Script/Sabsik.FL.A!ml**.
- Mức độ: **Severe**.
- Trạng thái: **Removed**.
- Tên tệp: `HMONG_VOICE_STUDIO_ULTRA_FAST.zip`.
- Đường dẫn tải: `raw.githubusercontent.com/seotro95/seotro/refs/heads/hmong-studio-0.3-download/HMONG_VOICE_STUDIO_ULTRA_FAST.zip`.

Ảnh ghi tên ZIP và nguồn tải, không chỉ rõ tệp con trong ZIP. Không suy ra báo nhầm từ tên phát hiện hoặc hậu tố `!ml`. Không suy ra máy đã an toàn hoặc đã bị xâm nhập chỉ từ trạng thái Removed.

Cả gói không có số phiên bản và gói 0.8.1 đã được rút khỏi HEAD của nhánh tải để ngừng phân phối trong khi chưa xác minh. Người dùng xác nhận 0.8.1 cũng bị chặn; hiện chưa có ảnh chi tiết riêng hoặc hash bản tải về 0.8.1. Bản cũ vẫn có trong lịch sử Git để điều tra; không viết lại lịch sử và không đóng gói đổi tên để vượt cảnh báo. Bản sao nguồn ban đầu được giữ nguyên.

## Đối chiếu và điều tra

Gói cũ trong repository trước khi rút:

- Phiên bản mã trong ZIP: **0.8.0**.
- Kích thước: **2.940.062 byte**, 90 mục ZIP.
- SHA256: `6344d78c6696490fe0b831731bcc5f253f8d4322ac844f3041897ab5f723c3cc`.
- Commit lưu gói trước khi rút: `0d4408e421982f0eaf8c0b583ed65abe150c353a`.

Tên và URL trong ảnh khớp đường dẫn của gói này. Không có hash tệp thực tế trên máy người dùng nên **chưa thể chứng minh bản tải về có cùng byte**. Không yêu cầu khôi phục tệp bị cách ly để lấy hash.

Đã kiểm tra CRC/cấu trúc ZIP và đọc lại 56 tệp script ngoài bộ kiểm thử, tính cả bản sao nguồn ZIP lồng. Chưa tìm thấy bằng chứng cụ thể về mã PowerShell mã hóa, ngoại lệ antivirus, lưu trú khởi động, lấy thông tin đăng nhập hoặc cơ chế nhận lệnh từ máy chủ bên ngoài. Lệnh GPU PowerShell trong bản cũ chỉ đọc thông tin; chưa có bằng chứng nó gây phát hiện. Những kết quả kiểm tra tĩnh này **không phủ định phát hiện của Defender và không xác nhận gói sạch**. Chưa xác định được thay đổi mã nguồn nào xử lý đúng phát hiện này.

## Trạng thái bản 0.8.1

`HMONG_VOICE_STUDIO_ULTRA_FAST_0.8.1.zip` là gói đã công bố trước khi nhận ảnh chi tiết; nay cũng được người dùng báo bị chặn và đã rút khỏi nhánh tải. Hash gói lưu trong lịch sử: `c2ccad88df5d51cc06457c3f7f49f64a20b55d011a73d0cd0cb4556fbc612aa8` (1.636.745 byte, 102 tệp).

Các gia cố HTTPS và chẩn đoán GPU trong 0.8.1 không phải bằng chứng đã khắc phục phát hiện Sabsik. **Bản này chưa được xác nhận qua Windows Defender; không coi việc đổi phiên bản hoặc hash là bằng chứng an toàn.** 363 kiểm thử phần mềm đạt, một kiểm thử CUDA bỏ qua; các kiểm thử đó không phải quét antivirus.

ClamAV 1.4.3 đã chạy được, nhưng dữ liệu nhận diện chính thức vẫn không tải được do proxy chặn HTTPS `database.clamav.net` với 403 Forbidden, kể cả kiểm tra lại sau khi nhận ảnh. Các lần thử quét báo exit 2, 0 tệp được quét; **chưa có lần quét antivirus thành công**. Log/báo cáo trước đó nằm trong `hmong-studio/security-scan/` và các sidecar `.scan.json`/`.scan.txt` của 0.8.1. Các báo cáo trong ZIP 0.8.1 phản ánh thông tin trước ảnh chi tiết; thông báo này bổ sung tên phát hiện hiện đã biết.

Môi trường điều tra là Linux, không có Windows Defender để tái hiện. Chưa gửi mã nguồn hoặc các mẫu giọng lên dịch vụ quét công khai. Không phát hành thêm ZIP chỉ để thử tránh phát hiện. Cần tái hiện bằng Defender hoặc kiểm tra antivirus có dữ liệu nhận diện cập nhật để xác định và xử lý nguyên nhân trước khi xác nhận bản phát hành đã qua kiểm tra.

Đã lưu bản nháp cấu hình môi trường, bổ sung duy nhất `database.clamav.net` bên cạnh ba miền Hmong đang có. Các preset mạng, tập lệnh cài đặt, hướng dẫn khởi động và yêu cầu bí mật được giữ nguyên. Công cụ trả `status: saved`, `requires_publish: true`; thay đổi **chưa được xác nhận áp dụng vào máy đang chạy**. Cần xem/lưu thay đổi và xuất bản qua giao diện Môi trường, sau đó kiểm tra lại truy cập/tải dữ liệu trước khi quét. Không coi lưu bản nháp là đã mở mạng hoặc đã quét thành công.

## Xử lý trên máy người dùng

Giữ tệp ở trạng thái đã xóa/cách ly; không chọn Restore hoặc Allow và không thêm ngoại lệ cho thư mục app. Giữ bảo vệ Windows bật. Nếu đã chạy gói trước khi bị chặn, dùng Windows Security để chạy Full scan và xử lý các mục phát hiện theo hướng dẫn của Defender. Không cần tải hoặc chạy lại gói để xác nhận cảnh báo.
