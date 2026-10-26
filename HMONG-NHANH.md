# Hmong Nhanh 0.8.1

> **Cảnh báo chưa được xử lý xong.** Người dùng tiếp tục báo file tải bị phát hiện vi-rút sau khi nhận bản 0.8.1. Tạm ngừng khuyến nghị tải/chạy gói này trong lúc xác định tên mối đe dọa và tệp bị ảnh hưởng. Không coi kiểm thử phần mềm hoặc SHA-256 là kết quả quét antivirus.

Bản 0.8 được người dùng báo trình duyệt chặn với thông báo **“Đã phát hiện thấy vi-rút”**. Chưa có tên mối đe dọa hoặc kết quả quét Windows Defender để xác định nguyên nhân. Bản 0.8.1 sửa khâu xác minh tệp/mô hình; **chưa xác nhận cảnh báo antivirus đã được giải quyết**.

[Mã nguồn](hmong-nhanh/) · [Hướng dẫn](hmong-nhanh/HUONG_DAN.txt) · [Báo cáo kiểm tra](hmong-nhanh/validation/integrity-0.8.1.json)

## Thay đổi có thể kiểm tra

- Cố định bốn tệp F5-Hmong/Vocos theo đúng commit, kích thước và SHA-256 của các tệp đã dùng kiểm thử. Bộ cài không lấy bản `main` mới nhất làm nguồn tin cậy.
- Kiểm tra các tệp thực tế ngay trước khi nạp/nạp lại mô hình. Cấu hình Vocos bị thay đổi bị chặn trước khi thư viện đọc và khởi tạo lớp Python từ cấu hình.
- Không lấy `verified-models.json` có thể sửa trong thư mục dữ liệu làm nguồn checksum đáng tin duy nhất. Đường dẫn tùy chỉnh vẫn phải chứa đúng các tệp mô hình đã cố định.
- Thêm `release-files.json` chứa kích thước/SHA-256 của các tệp trong gói. Bộ khởi chạy kiểm tra trước khi chuẩn bị môi trường Python, dừng nếu tệp thiếu hoặc không khớp. Có thể chạy riêng `py app\verify_release.py`.

Hash xác nhận tính toàn vẹn so với bản phát hành; **không phải kết quả quét antivirus hay chữ ký số**. Không đổi phần mở rộng, mã hóa ZIP, tắt Defender, thêm ngoại lệ hoặc yêu cầu khôi phục tệp đang bị cách ly.

## Phạm vi kiểm tra

Gói 0.8 cũ có SHA-256 `940bf6d0fc768d6c954be484b60cc8a9c98e1934663d53e3969b3e16f34a9665`, 35 tệp, CRC hợp lệ; không có EXE/DLL đóng sẵn, tệp ZIP mã hóa, đường dẫn thoát thư mục hoặc symlink. Rà các đường khởi chạy/cài đặt không thấy lệnh tắt antivirus, tự khởi động cùng Windows, thu thập thông tin đăng nhập hoặc tự tải dữ liệu người dùng lên mạng.

Đây là rà mã và cấu trúc gói, không chứng minh “không có virus”. Môi trường kiểm thử Linux không có Windows Defender/ClamAV hoặc bộ chữ ký; yêu cầu đến nguồn chữ ký ClamAV chính thức bị mạng quản lý chặn HTTP 403. Không có kết luận cảnh báo là nhầm. Nếu bản mới tiếp tục bị chặn, dừng dùng và lấy **tên mối đe dọa, tệp bị ảnh hưởng** trong Bảo mật Windows → Lịch sử bảo vệ để điều tra tiếp.

## Tài liệu vận hành và dữ liệu giữ lại

Không chạy tệp đang bị phần mềm bảo mật chặn hoặc cách ly. Các chỉ dẫn dưới đây được giữ để tham khảo sau khi nguyên nhân cảnh báo đã được xác định.

Mở `MO_HMONG_NHANH.bat`; cần Python 3.12 64-bit. Bộ cài vẫn tải thư viện PyPI/PyTorch và mô hình Hugging Face qua HTTPS ở lần đầu. Cập nhật bằng cách thay các tệp chương trình và **giữ `.data`**. Mô hình cũ đúng checksum được dùng lại.

Giữ sáu mẫu giọng mới, hai mẫu cũ, nhập giọng ngoài, lịch sử nghe/tải, SRT/TXT chỉ đọc lời, căn thời gian, giới hạn 1 triệu ký tự và tối ưu câu lặp. Sáu mẫu mới cần lời chép chính xác của đoạn 3–8 giây để bật nhân bản. Không có thay đổi mô hình/phát âm hoặc cam kết 1 giờ voice trong 2 phút ở bản này.

Kiểm thử bản 0.8.1: **287 kiểm thử tự động đạt**, gồm phát hiện cấu hình mô hình bị đổi, checksum giả trong biên nhận, tệp thiếu, tải sai hash và chặn chuẩn bị môi trường khi tệp chương trình không khớp. Các kiểm thử này không phải quét antivirus.

ZIP: 2,449,762 bytes; SHA-256 `6ef5e0c70ffc2bc744575c9d386cb3acf949dd8fce7390d073daea6659eefd24`.
