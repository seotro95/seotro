# Hmong Nhanh 0.8.0

Bản 0.8 thêm sáu file giọng được gửi vào danh sách mẫu có sẵn, xử lý phụ đề sao chép có dấu ngoặc kép, nhớ giọng đang chọn và giảm việc tạo lại những câu giống hệt nhau.

[Tải Hmong-Nhanh-da-sua.zip](https://github.com/seotro95/seotro/raw/refs/heads/codex/hmong-nhanh-0.8.0/Hmong-Nhanh-da-sua.zip) · [Mã nguồn](hmong-nhanh/) · [Hướng dẫn đầy đủ](hmong-nhanh/HUONG_DAN.txt)

Giải nén rồi mở **MO_HMONG_NHANH.bat**. Khi cập nhật, tắt tool, thay tệp chương trình và **giữ nguyên `.data`** để giữ mô hình, mẫu đã lưu và lịch sử. Cần Python 3.12 64-bit; lần đầu cần mạng tải thư viện và khoảng 1,4 GB trọng số.

## Sáu mẫu có sẵn

Danh sách **Giọng có sẵn** chứa đúng các file: `hmong nữ 3.MP3`, `hmong nữ.MP3`, `ngọc huyền.MP3`, `hmong nam 2.MP3`, `hmong nam1.MP3`, `hmong nữ 2(1).MP3`. Mỗi file giữ nguyên dữ liệu âm thanh; có tên và thiết lập riêng. Hai mẫu Nam/Nữ cũ tiếp tục hoạt động với thiết lập cũ. Tool nhớ giọng được chọn trên cùng trình duyệt.

**Sáu mẫu mới đã được đóng gói, nhưng chưa có lời chép tham chiếu chính xác để bật nhân bản ngay.** Chọn một giọng, nghe đoạn rõ lời 3–8 giây, nhập đúng lời của đoạn đó bằng ngôn ngữ gốc và bấm lưu một lần. Không cần tải lại file. Tool không đoán lời và không thay bằng giọng mặc định khi mẫu chưa sẵn sàng. Có thể tiếp tục nhập các mẫu ngoài khác như bản trước.

## Chỉ đọc lời trong TXT/SRT

```srt
217
00:06:07,200 --> 00:06:08,400
Tae-yong cov ntaub ntawv tus kheej
```

Bộ tạo giọng chỉ nhận **Tae-yong cov ntaub ntawv tus kheej**. Không nhận số `217` hoặc dòng thời gian; số thuộc lời nói và dấu gạch trong tên vẫn được giữ. Hỗ trợ cả dấu ngoặc kép thẳng/cong bao quanh khối phụ đề khi sao chép.

Ở chế độ khớp phụ đề, lời nằm trong khung **367,2–368,4 giây**, dài **1,2 giây**. Nếu đây là đoạn duy nhất, WAV giữ khoảng lặng đầu để ghép video; bấm **Nghe từ lời đầu** để nghe ngay. Chọn **Đọc liền theo nhịp tự nhiên** nếu chỉ muốn đọc lời liên tục. Khung quá ngắn có thể buộc đọc nhanh hoặc cần nới mốc; không cắt mất lời để vừa khung.

Đoạn ngắn có mốc được tự xem trước sau khi ngừng gõ. Với văn bản rất dài, bấm **Kiểm tra lời sẽ đọc**. Giữ giới hạn **1.000.000 ký tự Unicode**, tệp TXT/SRT/VTT tối đa 8 MB, UTF-8 hoặc UTF-16 có BOM.

## Tốc độ

- Tự giới hạn luồng CPU theo số lõi thực sự được cấp, gồm giới hạn container. Không đổi số bước chất lượng để tạo ra kết quả đo nhanh hơn.
- Giữ tối đa **32 MiB / 128 kết quả** trong bộ nhớ của worker. Câu lặp lại với cùng mẫu âm thanh, lời tham chiếu, nội dung, nhịp, chất lượng và mô hình được dùng lại. Câu mới hoặc đổi thiết lập vẫn phải tạo mới. Bộ nhớ này mất khi đóng hoặc dừng worker.
- Mặc định vẫn là **Cân bằng 16 bước**. Có thể chọn **Nhanh 8 bước** để giảm công tính toán, với khả năng giảm độ rõ. Nhịp đọc và tốc độ xử lý là hai thiết lập khác nhau.

Phép đo CPU trên cùng câu ở trên, cùng mẫu, cùng seed và 16 bước: 3 luồng mất **96,329 giây**; 2 luồng mất **69,690 giây**, lần đo lại **56,045 giây**. Máy thử bị giới hạn 2 lõi; vì vậy kết quả không bảo đảm mức cải thiện tương tự trên Windows hoặc máy khác. Đoạn âm thanh tạo mới dài 3,467 giây, chưa căn phụ đề; thời gian nạp mô hình được đo riêng. Đây **không phải** bằng chứng đạt mục tiêu tạo 1 giờ voice trong 2 phút.

## Các chức năng giữ lại

Lịch sử nghe/tải bản hoàn tất; nhập giọng ngoài; sáu kiểu nhịp đọc; Dừng/Tiếp tục; WAV theo phần khoảng 30 phút; tự chọn CUDA tương thích/CPU; `--cpu` và `--gpu`; căn từng khung phụ đề và phát từ lời đầu.

Chưa có đánh giá của người nói Hmong bản ngữ về phát âm hoặc độ giống sáu giọng mới. Bản này không huấn luyện lại mô hình, không bảo đảm nhân bản mọi giọng/ngôn ngữ. Chưa chạy BAT trên Windows thật hoặc đo GPU. Kiểm thử phần mềm không thay thế nghe đánh giá giọng.

Nguồn mô hình: [F5TTS-Hmong](https://huggingface.co/Pakorn2112/F5TTS-Hmong), [Vocos](https://huggingface.co/charactr/vocos-mel-24khz). ZIP không chứa trọng số, môi trường Python hoặc dữ liệu `.data` của người dùng.

## Kiểm tra bản 0.8

**252 kiểm thử tự động đạt**; Chromium kiểm tra giao diện, giọng có sẵn, ghi nhớ lựa chọn, mẫu SRT 217, nhập 1 triệu ký tự và lịch sử. Thử mô hình thật: tạo mới câu Tae-yong ở 16 bước mất 74,492 giây cho 3,467 giây âm thanh; lần lặp lại với bản sao cùng mẫu lấy đúng WAV trong 0,012789 giây. Lần lặp là dùng lại kết quả, không phải tốc độ tạo lời mới. Nút đo tốc độ bỏ qua bộ nhớ kết quả.

ZIP: 2,444,296 bytes; SHA-256 `940bf6d0fc768d6c954be484b60cc8a9c98e1934663d53e3969b3e16f34a9665`.
