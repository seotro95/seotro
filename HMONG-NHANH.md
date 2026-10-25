# Hmong Nhanh 0.6.0

Bản 0.6 nhận TXT/SRT/VTT, bỏ mốc thời gian và số thứ tự phụ đề khỏi lời đọc, giữ số nằm trong câu, và có thể căn WAV theo thời gian phụ đề. Thêm thư viện giọng từ tệp bên ngoài; mỗi bản đọc dùng đúng đoạn mẫu và lời chép của giọng đã chọn.

[Tải Hmong-Nhanh-da-sua.zip](https://github.com/seotro95/seotro/raw/refs/heads/codex/hmong-nhanh-0.6.0/Hmong-Nhanh-da-sua.zip) · [Mã nguồn](hmong-nhanh/) · [Hướng dẫn đầy đủ](hmong-nhanh/HUONG_DAN.txt)

Giải nén rồi mở **MO_HMONG_NHANH.bat**. Cần Python 3.12 64-bit kèm Python Launcher. Lần đầu cần mạng để cài thư viện và tải khoảng 1,4 GB trọng số F5-Hmong/Vocos; bộ thư viện CPU/CUDA cần thêm dung lượng. Không cần FFmpeg riêng.

## Lời đọc và thời gian phụ đề

Nhập tệp UTF-8 tối đa 8 MB và **1.000.000 ký tự Unicode**, rồi bấm **Kiểm tra lời sẽ đọc**. Phần xem trước không thay đổi nội dung gốc hoặc cắt ngắn bản đọc.

```srt
27
00:04:28,533 --> 00:04:29,333
Kuv muaj 25 xyoo.
```

Chỉ `Kuv muaj 25 xyoo.` được đưa vào bộ tạo giọng: bỏ số thứ tự `27` và dòng thời gian; giữ `25` trong câu. Hỗ trợ dấu phẩy/dấu chấm mili giây, dạng giờ:phút:giây hoặc phút:giây, nhiều dòng, thẻ phụ đề thông dụng và cặp mốc chép trong TXT.

| Chế độ | Kết quả |
| --- | --- |
| **Khớp mốc phụ đề nếu có** | Giữ thời điểm bắt đầu, kết thúc và khoảng lặng. Ví dụ trên bắt đầu nói tại 4:28,533; WAV kết thúc tại 4:29,333 và gồm khoảng lặng đầu. |
| **Đọc liền theo nhịp tự nhiên** | Bỏ các mốc/số thứ tự và đọc lời liên tục theo tùy chọn nhịp. |
| TXT không có đủ cặp mốc | Đọc tự nhiên; không suy đoán thời lượng từ văn bản. Mốc đầu dòng thông dụng như `[00:12.50]` được bỏ. |

Căn thời gian dùng xử lý giữ cao độ, giới hạn từ **0,5 đến 2 lần** so với âm thanh vừa tạo. Câu không vừa khung sẽ báo đoạn cần sửa, không cắt mất từ; sửa mốc hoặc chọn đọc tự nhiên. Khi giữ mốc, khoảng nghỉ của kiểu kể không kéo dài ngoài khung phụ đề. Mốc sai hoặc chồng lấn được báo trước khi căn; chế độ tự nhiên có thể đọc mốc hợp lệ chồng lấn theo thứ tự tệp. Giới hạn thời gian phụ đề: 168 giờ.

## Nhân bản giọng từ bên ngoài

1. Mở **Nhân bản giọng từ tệp âm thanh**, đặt tên và tải WAV/MP3/FLAC/OGG tối đa 50 MB, dài 3–600 giây, mono hoặc stereo.
2. Chọn đoạn rõ lời **3–8 giây**; nghe và lưu lời chép chính xác bằng **ngôn ngữ gốc của mẫu**. Không dịch lời tham chiếu sang Hmong.
3. Chọn giọng vừa tải, nhập lời cần tạo bằng tiếng Hmong. Nên thử **Cân bằng 16 bước** hoặc **Chất lượng 32 bước** và nghe trước khi tạo dài.

Mẫu ngoài được lưu riêng; thiếu mẫu báo lỗi, không thay bằng giọng Nam/Nữ mặc định. Mỗi bản đọc chụp lại cặp âm thanh/lời chép khi bắt đầu, nên sửa thư viện không đổi giọng của bản đang chạy hoặc tiếp tục.

**Không bảo đảm nhân bản chính xác mọi giọng/ngôn ngữ.** Mẫu được phép nói ngôn ngữ khác Hmong, nhưng checkpoint F5-Hmong có giới hạn ngôn ngữ/từ vựng tham chiếu. Kiểm thử xác nhận dùng đúng mẫu, chưa chứng nhận độ giống bằng tai cho mọi người nói. Nội dung cần đọc vẫn phải là tiếng Hmong; tool không tự dịch kịch bản.

## Các chức năng giữ nguyên

Giữ Nam/Nữ riêng, giới hạn 1 triệu ký tự, sáu kiểu nhịp đọc (Tự nhiên, Kể chuyện, Review phim, Tin tức, Quảng cáo, Thư giãn), bốn mức 4/8/16/32 bước, Dừng/Tiếp tục sau khi mở lại, tiến độ và nghe/tải WAV từng phần khoảng 30 phút. Chỉ xử lý một bản đọc mỗi lần. Kiểu kể điều chỉnh nhịp/khoảng nghỉ, không tự viết kịch bản hoặc thêm mô hình cảm xúc.

Bộ cài tự chọn CUDA khi NVIDIA/driver tương thích; nếu không dùng CPU. Giữ mô hình giữa các lượt; hỗ trợ `MO_HMONG_NHANH.bat --cpu` và `--gpu`. **Chưa xác nhận đạt 1 giờ voice trong 2 phút (30×).** Mẫu ngắn CPU của bản 0.5 tạo 3,467 giây âm thanh trong 59,528 giây lượt đầu hoặc 55,949 giây khi mô hình đã nạp; chưa đo đủ một giờ hay đo GPU. Khoảng lặng thêm không được tính là tăng tốc lời nói.

## Kiểm tra và dữ liệu

**173 kiểm thử tự động đã đạt**: parser phụ đề, giữ số trong lời, căn thời lượng và cao độ, checkpoint/tiếp tục, thư viện mẫu ngoài, chọn đúng mẫu và lời chép ngôn ngữ gốc. Chưa tạo âm thanh thật cho toàn bộ 1.000.000 ký tự, chưa chạy BAT trên Windows thật và chưa xác nhận phát âm Hmong Trắng/độ giống mọi giọng.

Khi cập nhật, tắt tool rồi chép `.data` từ bản cũ sang cạnh BAT mới; giữ bản sao cũ đến khi kiểm tra xong. `.data` chứa mô hình, giọng ngoài, lời tham chiếu, văn bản, tiến độ và WAV. Nếu đã dùng `HMONG_STUDIO_DATA_DIR`, giữ đường dẫn đó. Thư mục `app` cần thiết để chạy.

WAV 24 kHz mono 16-bit dùng khoảng 173 MB/giờ; giữ cả đoạn để tiếp tục và WAV ghép có thể cần khoảng 346 MB/giờ lời đọc, chưa tính tệp tạm và các dữ liệu khác. Khoảng lặng dài trong phụ đề cũng tốn đĩa.

Nguồn: [F5TTS-Hmong](https://huggingface.co/Pakorn2112/F5TTS-Hmong), [Vocos](https://huggingface.co/charactr/vocos-mel-24khz). Mô hình được tải qua HTTPS, kiểm tra checksum; ZIP không kèm trọng số, môi trường Python hoặc dữ liệu tham chiếu riêng đã lưu.

Thử tích hợp thật 0.6: tải mẫu tiếng Anh công khai, lưu lời chép gốc, tạo câu Hmong ở chế độ Cân bằng 16 bước, căn SRT từ 00:00:01,000 đến 00:00:06,000. WAV 24 kHz có đúng 144.000 mẫu (6 giây), 1 giây đầu im lặng và 5 giây trong khung lời; CPU xử lý khoảng 130,4 giây. Đây là bằng chứng dùng mẫu ngoài và khớp thời lượng, chưa đánh giá độ giống giọng bằng tai. Chromium cũng đã kiểm tra luồng giao diện với API mô phỏng, gồm tải mẫu ngoài, SRT/VTT/TXT, 1 triệu ký tự và dừng/tiếp tục.

Chromium đã kiểm tra giao diện với API mô phỏng, gồm nhập 1.000.000 ký tự Unicode, Nam/Nữ, dừng/tiếp tục và phát/tải từng phần.

Gói ZIP: 793,439 bytes; SHA-256 `5f511940e67d22f100f9b7a5e0f31f0be89623c80b33bb4f730bb955091f6307`. Không chứa dữ liệu chạy, trọng số, môi trường Python hoặc lời tham chiếu riêng đã lưu.
