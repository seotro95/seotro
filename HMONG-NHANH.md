# Hmong Nhanh 0.7.0

Bản 0.7 thêm **Lịch sử tạo voice** để tìm, nghe và tải lại các bản hoàn tất; làm rõ quy trình nhập giọng ngoài; hỗ trợ bản ghi điện thoại M4A/AAC và căn các khung phụ đề ngắn.

[Tải Hmong-Nhanh-da-sua.zip](https://github.com/seotro95/seotro/raw/refs/heads/codex/hmong-nhanh-0.7.0/Hmong-Nhanh-da-sua.zip) · [Mã nguồn](hmong-nhanh/) · [Hướng dẫn](hmong-nhanh/HUONG_DAN.txt)

Giải nén rồi mở **MO_HMONG_NHANH.bat**. Cần Python 3.12 64-bit kèm Python Launcher. Lần đầu cần mạng để tải thư viện và khoảng 1,4 GB trọng số. Khi cập nhật, tắt tool, giải nén đè tệp chương trình vào thư mục cũ và **giữ nguyên `.data`**. Nếu dùng thư mục mới, chép `.data` sang cạnh BAT mới; giữ bản sao cũ đến khi kiểm tra xong.

## Lịch sử và giọng ngoài

**Lịch sử tạo voice** luôn hiện trên giao diện, có tên, ngày, giọng, trạng thái và thời lượng. Tìm kiếm hoặc lọc **Đã hoàn tất**, rồi nghe/tải WAV trực tiếp. Bấm **Mở bản đọc** để xem tất cả các phần. Lịch sử còn sau khi khởi động lại nếu giữ đúng `.data` và các tệp âm thanh.

Để nhân bản giọng:

1. Đặt tên, chọn WAV/MP3/FLAC/OGG/M4A/AAC/MP4/WebM có tiếng, tối đa **50 MB, dài 3–600 giây**, rồi tải mẫu lên tool.
2. Chọn đoạn rõ lời **3–8 giây**, nghe và lưu lời chép chính xác bằng **ngôn ngữ gốc**. Không dịch lời tham chiếu sang Hmong; tool không tự nhận dạng hoặc đoán lời mẫu.
3. Chọn giọng vừa lưu, nhập lời Hmong cần tạo. Thông báo dưới nút tạo chỉ rõ bước còn thiếu.

Bộ cài bổ sung `imageio-ffmpeg` để đọc các định dạng điện thoại; không cần cài FFmpeg riêng. Tệp quá dài bị từ chối, không cắt âm thầm. Mẫu ngoài được giữ riêng, không thay bằng Nam/Nữ khi gặp lỗi. Mỗi bản đọc giữ cặp mẫu/lời từ lúc bắt đầu để tiếp tục với đúng giọng.

## Phụ đề của bạn

```srt
196
00:05:33,366 --> 00:05:34,533
nws tsis txhawj txog nws tus kheej ntau
```

Chỉ câu Hmong được đưa vào bộ tạo giọng; bỏ `196` và dòng thời gian. Số thuộc lời nói vẫn được giữ. Cửa sổ lời dài **1,167 giây**, bắt đầu tại **333,366 giây** và kết thúc tại **334,533 giây**. Nếu đây là đoạn duy nhất, WAV gồm khoảng lặng đầu và có tổng độ dài **334,533 giây** để khớp vị trí video.

| Chế độ | Hành vi |
| --- | --- |
| **Khớp phụ đề, cho phép đọc nhanh** — mặc định | Căn từng khung bằng xử lý giữ cao độ, tăng nhịp tối đa 4 lần; cảnh báo khi trên 2 lần. |
| **Khớp mốc, ưu tiên rõ lời** | Giới hạn tăng nhịp 2 lần; khung không vừa được báo lỗi, không cắt từ. |
| **Đọc liền theo nhịp tự nhiên** | Bỏ mốc/số thứ tự, đọc lời liên tục và không giữ thời gian phụ đề. |

Khung dài chỉ làm chậm tối đa 2 lần rồi thêm im lặng đến hết khung. Nếu khung vẫn quá ngắn ở mức 4 lần, cần sửa mốc hoặc chọn đọc tự nhiên. Câu mẫu có 8 từ trong 1,167 giây nên khớp thời gian có thể đọc rất nhanh và giảm độ rõ; không thể bảo đảm nhịp tự nhiên cho mọi khung ngắn.

Nút **Tạo lại đọc liền** ở bản phụ đề lỗi tạo một tác vụ mới từ toàn bộ lời và đúng mẫu đã lưu; giữ nguyên bản cũ trong lịch sử. Âm thanh gốc đã tạo trước lỗi căn nhịp được giữ để thử tiếp khi phù hợp.

Nhập TXT/SRT/VTT **UTF-8 hoặc UTF-16 có BOM**, tối đa **8 MB và 1.000.000 ký tự Unicode**. Mốc chồng lấn/sai thứ tự được báo trước khi căn; giới hạn thời gian 168 giờ. TXT không có đủ cặp mốc chỉ đọc tự nhiên, không suy đoán thời lượng từ số ký tự.

## Chất lượng Hmong và các chức năng giữ lại

Mặc định mới là **Cân bằng 16 bước**; vẫn có 4/8/16/32 bước. Khi cần ưu tiên độ rõ, thử **Chất lượng 32 bước** với mẫu sạch, ít nhạc/nhiễu và nghe trước khi tạo dài. Nhiều bước tốn thời gian hơn.

**Chưa xác nhận phát âm chuẩn Hmong bởi người bản ngữ hoặc độ giống cho mọi giọng/ngôn ngữ.** Bản này không huấn luyện mô hình mới. Checkpoint F5-Hmong có giới hạn ngôn ngữ/từ vựng tham chiếu; mẫu khác ngôn ngữ được nhận nhưng không có bảo đảm nhân bản chính xác. Tool không tự dịch kịch bản.

Giữ Nam/Nữ riêng, sáu kiểu nhịp đọc, tiến độ, Dừng/Tiếp tục sau khi mở lại, các phần WAV khoảng 30 phút, bộ nhớ mô hình giữa các lượt và tự chọn CUDA tương thích/CPU. Hỗ trợ `--cpu` và `--gpu`. **Chưa xác nhận đạt 1 giờ voice trong 2 phút (30×)**; kết quả đo trên CPU/GPU và chất lượng phụ thuộc máy, mẫu, chế độ. Khoảng lặng thêm không được tính là tăng tốc tạo lời.

`.data` chứa mô hình, giọng ngoài, lời tham chiếu, văn bản, tiến độ và WAV. Một giờ WAV mono 24 kHz,16-bit khoảng 173 MB; cả đoạn để tiếp tục và WAV ghép thường cần khoảng 346 MB/giờ lời đọc, chưa tính dữ liệu khác và khoảng lặng dài. Giữ `HMONG_STUDIO_DATA_DIR` nếu đã cấu hình.

Các kiểm thử phần mềm xác nhận xử lý nội dung, mẫu, thời lượng và lưu/đọc lại; chúng không thay thế đánh giá phát âm/độ giống bằng tai. Chưa chạy BAT trên Windows thật, đo GPU hoặc tạo toàn bộ 1 triệu ký tự thành âm thanh thật trong môi trường thử này.

Nguồn: [F5TTS-Hmong](https://huggingface.co/Pakorn2112/F5TTS-Hmong), [Vocos](https://huggingface.co/charactr/vocos-mel-24khz). Trọng số được tải qua HTTPS và kiểm tra checksum; ZIP không chứa trọng số, môi trường Python hoặc dữ liệu tham chiếu riêng đã lưu.

Thử tích hợp thật 0.7: tải mẫu tiếng Anh công khai ở định dạng M4A, lưu lời chép gốc và tạo đúng câu Hmong trong mẫu SRT trên ở chế độ Cân bằng 16 bước. WAV 24 kHz dài đúng 334,533 giây, gồm 333,366 giây im lặng đầu và khung lời 1,167 giây. Sau khi khởi động lại máy chủ, giọng ngoài, bản hoàn tất và đường tải WAV vẫn đọc được. Đây là bằng chứng hoạt động của luồng nhập mẫu/căn thời gian/lịch sử, chưa đánh giá phát âm hoặc độ giống bằng tai.

Với SRT bắt đầu ở phút thứ 5, WAV giữ khoảng lặng đầu để ghép đúng video. Bấm “Nghe từ lời đầu” trong bản đọc hoặc Lịch sử để nghe ngay lời nói; file tải xuống vẫn giữ đầy đủ thời gian phụ đề.

Kiểm tra bản 0.7: 205 kiểm thử tự động đạt, gồm mẫu SRT 196, codec âm thanh thật, lịch sử sau khởi động lại, tải WAV và xử lý đường dẫn tiếng Việt của worker.

Chromium đã kiểm tra giao diện với API mô phỏng, gồm nhập 1.000.000 ký tự Unicode, Nam/Nữ, dừng/tiếp tục và phát/tải từng phần.

Gói ZIP: 802,023 bytes; SHA-256 `86b85d6f9d17fa6bd56bb0444f9b048c7bfc8fa1b2af70a64815d4623f06ba50`. Không chứa dữ liệu chạy, trọng số, môi trường Python hoặc lời tham chiếu riêng đã lưu.
