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

Ban đầu ClamAV chưa có dữ liệu vì proxy chặn HTTPS `database.clamav.net` với 403 Forbidden. Những lần thử đó trả exit 2 và quét 0 tệp; log cũ trong `hmong-studio/security-scan/` và sidecar `.scan.json`/`.scan.txt` là bằng chứng thất bại lịch sử, không phải kết quả hiện tại. **Sau đó đã lấy được dữ liệu có chữ ký xác thực từ nguồn phân phối container chính thức và quét thành công như dưới đây.** Các báo cáo nằm bên trong ZIP 0.8.1 phản ánh thời điểm trước khi nhận ảnh và trước lần quét thành công này.

Môi trường điều tra là Linux, không có Windows Defender để tái hiện. Chưa gửi mã nguồn hoặc các mẫu giọng lên dịch vụ quét công khai. Không phát hành thêm ZIP chỉ để thử tránh phát hiện. Cảnh báo Defender vẫn chưa được định vị/giải quyết dù kết quả ClamAV bên dưới không phát hiện mã độc; chưa có thay đổi mã nào được xác nhận xử lý đúng cảnh báo.

Đã lưu bản nháp cấu hình môi trường, bổ sung duy nhất `database.clamav.net` bên cạnh ba miền Hmong đang có. Các preset mạng, tập lệnh cài đặt, hướng dẫn khởi động và yêu cầu bí mật được giữ nguyên. Công cụ trả `status: saved`, `requires_publish: true`; truy cập trực tiếp vẫn 403. Bản nháp chưa được xác nhận áp dụng vào máy đang chạy. Lần quét dùng dữ liệu ngoại tuyến chính thức bên dưới không cần chờ thay đổi này; cập nhật freshclam trực tiếp vẫn cần quyền mạng có hiệu lực.

## Kết quả quét thực tế — 20/10/2026 (UTC+7)

**ClamAV 1.4.3 không phát hiện mã độc trong hai ZIP đã lưu và toàn bộ 260 tệp sau giải nén, bao gồm bản sao nguồn lồng nhau. Đây không phải xác nhận Windows Defender đã chấp nhận tệp hoặc chứng minh báo nhầm. Hai ZIP tiếp tục được giữ khỏi nhánh tải.**

| Đối tượng | Bắt đầu (UTC+7) | Thời gian | Mã thoát | Kết quả |
| --- | --- | ---: | ---: | --- |
| ZIP không có số phiên bản, hash `6344d78c…c3cc` | 15:40:23 | 18,63 giây | 0 | Không phát hiện |
| ZIP 0.8.1, hash `c2ccad88…2aa8` | 15:40:42 | 14,09 giây | 0 | Không phát hiện |
| Quét trực tiếp toàn bộ nội dung sau giải nén | 15:42:38 | 16,30 giây | 0 | 260/260 tệp có kết quả OK; 0 phát hiện |

Đã kiểm tra SHA256 trước/sau quét khớp nguyên bản nêu trên. Quét archive được bật, có cảnh báo nếu vượt giới hạn hoặc gặp dữ liệu mã hóa; không có lỗi/cảnh báo trong log. Lần quét trực tiếp kiểm tra đủ 260 đường dẫn riêng biệt, gồm 68 tệp của bản sao nguồn lồng; không thiếu/thừa đường dẫn. Tất cả hash nội dung giải nén giữ nguyên sau quét. Không chạy mã hoặc nội dung của app trong quá trình quét.

Nguồn dữ liệu: image **`clamav/clamav:1.4`** do Cisco Talos công bố chính thức, image version 1.4.6. Chỉ tải lớp dữ liệu, xác minh chuỗi SHA256 của index/manifest/config/layer, giải nén ba CVD được cho phép; không chạy container hoặc binary trong image. `sigtool --info` xác minh cả ba CVD thành công (`Verification OK`, exit 0). Công cụ thực sự chạy quét là bản Debian **ClamAV 1.4.3**, không phải engine 1.4.6 trong image.

- `daily.cvd`: phiên bản **28157**, tạo **18/10/2026 13:24 (UTC+7)**.
- `main.cvd`: phiên bản **63**; `bytecode.cvd`: phiên bản **339**.
- Tổng số mẫu nhận diện được engine nạp: **3.642.850**.

Đây là **snapshot ngoại tuyến khoảng hai ngày tuổi**, chưa xác minh là dữ liệu mới nhất. Không suy rộng kết quả sang thư viện, FFmpeg hoặc trọng số tải khi cài đặt vốn không có trong hai ZIP. Một lượt quét ClamAV không thay thế việc tái hiện bằng đúng Defender đang báo trên Windows.

[Báo cáo đầy đủ](hmong-studio/security-scan/2026-10-20/ACTUAL_SCAN_REPORT.md), [kết quả hai ZIP](hmong-studio/security-scan/2026-10-20/held-release-scan-results.json), [kết quả 260 tệp](hmong-studio/security-scan/2026-10-20/extracted-combined-scan-summary.json), [log từng tệp](hmong-studio/security-scan/2026-10-20/extracted-combined-clamav.log), [nguồn/chữ ký dữ liệu](hmong-studio/security-scan/2026-10-20/official-container/PROVENANCE.json). Báo cáo/log gốc dùng UTC; bảng trên đã đổi sang UTC+7. Chỉ công bố log/metadata, không đưa scanner, database, bản ZIP đang giữ hay cây tệp giải nén vào bản phát hành mới.

## Xử lý trên máy người dùng

Giữ tệp ở trạng thái đã xóa/cách ly; không chọn Restore hoặc Allow và không thêm ngoại lệ cho thư mục app. Giữ bảo vệ Windows bật. Nếu đã chạy gói trước khi bị chặn, dùng Windows Security để chạy Full scan và xử lý các mục phát hiện theo hướng dẫn của Defender. Không cần tải hoặc chạy lại gói để xác nhận cảnh báo.

Nếu thư mục app đã giải nén từ trước vẫn còn, có thể bấm chuột phải thư mục đó → **Scan with Microsoft Defender** để kiểm tra bằng đúng sản phẩm đang báo. Không mở/chạy app hoặc khôi phục ZIP để thực hiện bước này. Nếu Defender chỉ ra tệp con cụ thể, tên tệp cùng tên phát hiện sẽ giúp định vị nguyên nhân; nếu không phát hiện trong thư mục, điều đó vẫn chưa chứng minh phát hiện ở ZIP là báo nhầm.
