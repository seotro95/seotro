# Hmong Nhanh 0.8.1

> **Cảnh báo chưa được xử lý xong.** Người dùng tiếp tục báo file tải bị phát hiện vi-rút sau khi nhận bản 0.8.1. Ảnh Lịch sử bảo vệ đã xác định Microsoft Defender báo `Trojan:Script/Ulthar.A!ml` tại `app/static/app.js` và `app/static/index.html` trong đúng gói 0.8.1. Tạm ngừng khuyến nghị tải/chạy gói này trong lúc kiểm tra. Không coi kiểm thử phần mềm hoặc SHA-256 là kết quả quét antivirus.

Bản 0.8 được người dùng báo trình duyệt chặn với thông báo **“Đã phát hiện thấy vi-rút”**. Đã có tên mối đe dọa và tệp bị ảnh hưởng từ ảnh người dùng; nguyên nhân chưa được xác nhận. Bản 0.8.1 sửa khâu xác minh tệp/mô hình; **chưa xác nhận cảnh báo antivirus đã được giải quyết**.

[Mã nguồn](hmong-nhanh/) · [Hướng dẫn](hmong-nhanh/HUONG_DAN.txt) · [Báo cáo kiểm tra](hmong-nhanh/validation/integrity-0.8.1.json)

## Thay đổi có thể kiểm tra

- Cố định bốn tệp F5-Hmong/Vocos theo đúng commit, kích thước và SHA-256 của các tệp đã dùng kiểm thử. Bộ cài không lấy bản `main` mới nhất làm nguồn tin cậy.
- Kiểm tra các tệp thực tế ngay trước khi nạp/nạp lại mô hình. Cấu hình Vocos bị thay đổi bị chặn trước khi thư viện đọc và khởi tạo lớp Python từ cấu hình.
- Không lấy `verified-models.json` có thể sửa trong thư mục dữ liệu làm nguồn checksum đáng tin duy nhất. Đường dẫn tùy chỉnh vẫn phải chứa đúng các tệp mô hình đã cố định.
- Thêm `release-files.json` chứa kích thước/SHA-256 của các tệp trong gói. Bộ khởi chạy kiểm tra trước khi chuẩn bị môi trường Python, dừng nếu tệp thiếu hoặc không khớp. Có thể chạy riêng `py app\verify_release.py`.

Hash xác nhận tính toàn vẹn so với bản phát hành; **không phải kết quả quét antivirus hay chữ ký số**. Không đổi phần mở rộng, mã hóa ZIP, tắt Defender, thêm ngoại lệ hoặc yêu cầu khôi phục tệp đang bị cách ly.

## Kết quả quét Defender ngày 27/10/2026

Đã quét nguyên gói ZIP và riêng hai tệp bị báo lỗi trên **Windows Server 2022**, dùng Microsoft Defender engine `1.1.26090.9`, platform `4.18.26090.9`, bộ nhận diện `1.461.217.0`. Cả ba lần quét hoàn tất và báo **không phát hiện mối đe dọa trong lần quét này**. SHA-256 của các tệp không đổi sau quét, không có sự kiện phát hiện/cách ly hay lỗi.

Đã bật bảo vệ thời gian thực, quét script/ZIP và bảo vệ đám mây; xác minh kết nối MAPS, bỏ các ngoại lệ mặc định của máy kiểm thử rồi kiểm tra từng đường dẫn không bị loại trừ. Không chạy ứng dụng trong phép quét.

[Nhật ký GitHub Actions](https://github.com/seotro95/seotro/actions/runs/40450978700) · [Dữ liệu kết quả](hmong-nhanh/validation/defender-report-2026-10-27.json) · [Tình trạng điều tra](hmong-nhanh/validation/antivirus-report.json)

Kết quả trên máy kiểm thử **không chứng minh cảnh báo trên máy người dùng đã hết hoặc là cảnh báo nhầm**. Môi trường Windows/trình duyệt/bộ nhận diện có thể khác. Bản ZIP và hai tệp nguồn được giữ nguyên để đối chiếu; không phát hành gói thay tên hay đổi nội dung để né cảnh báo.

## Xử lý trên máy đang bị chặn

1. Vào **Windows Security → Virus & threat protection → Protection updates → Check for updates** để cập nhật bộ nhận diện.
2. Trong **Protection history**, giữ chặn và dùng **Remove/Quarantine** nếu có. Không chọn **Allow/Restore**. Nếu xử lý vẫn thất bại, đóng trình duyệt, xóa bản ZIP lỗi còn trong Downloads và quét lại bằng Defender.
3. Hồ sơ phân tích Microsoft đã [soạn sẵn](hmong-nhanh/validation/microsoft-submission.md), kèm [nội dung để gửi](hmong-nhanh/validation/microsoft-submission-details.txt). **Chưa gửi và chưa có kết luận Microsoft**; cổng chính thức yêu cầu chủ tài khoản đăng nhập và xem lại nội dung.

Nguồn hướng dẫn: [Microsoft về cập nhật và xử lý lỗi loại bỏ](https://support.microsoft.com/en-us/defender/troubleshoot-problems-with-detecting-and-removing-malware), [Microsoft về gửi mẫu phân tích](https://learn.microsoft.com/en-us/defender-xdr/submission-guide).

## Tài liệu vận hành và dữ liệu giữ lại

Không chạy tệp đang bị phần mềm bảo mật chặn hoặc cách ly. Các chỉ dẫn dưới đây được giữ để tham khảo sau khi nguyên nhân cảnh báo đã được xác định.

Mở `MO_HMONG_NHANH.bat`; cần Python 3.12 64-bit. Bộ cài vẫn tải thư viện PyPI/PyTorch và mô hình Hugging Face qua HTTPS ở lần đầu. Cập nhật bằng cách thay các tệp chương trình và **giữ `.data`**. Mô hình cũ đúng checksum được dùng lại.

Giữ sáu mẫu giọng mới, hai mẫu cũ, nhập giọng ngoài, lịch sử nghe/tải, SRT/TXT chỉ đọc lời, căn thời gian, giới hạn 1 triệu ký tự và tối ưu câu lặp. Sáu mẫu mới cần lời chép chính xác của đoạn 3–8 giây để bật nhân bản. Không có thay đổi mô hình/phát âm hoặc cam kết 1 giờ voice trong 2 phút ở bản này.

Kiểm thử bản 0.8.1: **287 kiểm thử tự động đạt**, gồm phát hiện cấu hình mô hình bị đổi, checksum giả trong biên nhận, tệp thiếu, tải sai hash và chặn chuẩn bị môi trường khi tệp chương trình không khớp. Các kiểm thử này không phải quét antivirus.

ZIP: 2,449,762 bytes; SHA-256 `6ef5e0c70ffc2bc744575c9d386cb3acf949dd8fce7390d073daea6659eefd24`.
