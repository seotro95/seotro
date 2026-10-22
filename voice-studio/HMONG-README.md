# Voice Studio Hmong 1.2.0

Phiên bản riêng của Voice Studio 3.6.2, đọc **Hmong Trắng / Hmoob Daw (mww)** bằng mô hình F5-Hmong. Giao diện và hướng dẫn dùng tiếng Việt. Hai giọng mặc định lấy từ đúng tệp **hmong nam1.MP3** và **hmong nữ.MP3** bạn cung cấp.

## Mở bản Windows đầy đủ

1. Tải **`Voice-Studio-Hmong-1.2.0-Windows-x64.zip`** trong GitHub Releases và giải nén **toàn bộ ZIP** vào một thư mục có quyền ghi. Không chạy bên trong ZIP. Bộ 46 tệp `.py`/`.bat`/hướng dẫn rời thiếu giao diện `static/`, giọng `assets/hmong/` và runtime nên không đủ để chạy.
2. Mở **`MO_VOICE_STUDIO_HMONG.bat`** ở thư mục ngoài cùng. Gói có sẵn Python 3.12 x64, thư viện CPU và FFmpeg; không cần tự cài Python, API key hay GPU. Các lối mở `start.bat`, `start_hmong.bat` và các tệp tương ứng trong `voice-studio-hmong/` đều chuyển tới bộ khởi động Hmong của gói. `install_hmong.bat` hoặc `install.bat` chỉ chuẩn bị lần đầu, sau đó mở tool để dùng.
3. Lần mở đầu cần Internet để tải và kiểm tra khoảng **1,4 GB mô hình** từ Hugging Face. Giữ cửa sổ đang chạy mở. Nếu chuẩn bị thất bại, xem thông báo rồi mở lại sau khi khắc phục kết nối. Các trọng số Hmong không nằm trong ZIP vì nguồn chưa công bố giấy phép phân phối lại rõ ràng.
4. Trình duyệt tự mở khi sẵn sàng. Sau lần chuẩn bị thành công, tạo giọng hoạt động offline. Giữ cửa sổ tool mở trong lúc sử dụng; đóng cửa sổ để dừng máy chủ.

`KIEM_TRA_HMONG.bat` kiểm tra các tệp ứng dụng/giao diện, checksum hai giọng, FFmpeg, thư viện và mô hình đã lưu. Lệnh này không tải thêm và không tạo âm thanh; thông báo PASS không phải đánh giá phát âm. Trước lần chuẩn bị đầu, thông báo thiếu mô hình là bình thường. Nếu thiếu `static/` hoặc `assets/hmong/`, hãy giải nén lại cả gói thay vì chỉ chép các tệp `.py`.

Dữ liệu cá nhân của bản Windows nằm trong **`voice-studio-hmong/.data`**. Sao lưu thư mục này trước khi đổi phiên bản; không ghi đè hoặc xóa hồ sơ giọng và công việc cũ khi giải nén bản mới.

## Tạo giọng và nhân bản

- Nhập văn bản **Hmong chữ Latin RPA**, hoặc nhập TXT/SRT; chọn giọng nam/nữ rồi tạo giọng. Có thể tải WAV, MP3 và xuất nội dung TXT/SRT. Nên nghe một đoạn ngắn trước khi tạo cả kịch bản.
- Mặc định **16 bước**, ưu tiên độ rõ hơn chế độ nháp 4 bước của bản trước. Có thể chọn **4/8 bước để nháp nhanh**, hoặc **32 bước** để nghe so sánh. Chế độ 16/8/32 bước trên CPU mặc định dùng FP32. Khi chọn riêng **nháp 4 bước**, tool tự dùng INT8 nếu CPU hỗ trợ và quay về FP32 nếu không dùng được; không cần chỉnh cấu hình máy. Bản nháp có thể giảm độ rõ và tự nhiên. Mô hình và mẫu tham chiếu được giữ trong RAM để dùng lại, các câu ngắn được gom vào đoạn phù hợp để giảm số lần suy luận.
- Bộ đọc giữ nguyên các chữ cuối ghi thanh điệu RPA như `b/j/v/s/g/m/d`, chuẩn hóa khoảng trắng và dấu câu thông dụng. Văn bản dùng hệ chữ khác hoặc ký tự mô hình chưa hỗ trợ được báo lỗi để sửa, thay vì âm thầm mất chữ. Hãy viết số, chữ viết tắt và tên riêng thành lời Hmong muốn đọc khi cần; tool không tự biết cách đọc mọi tên hoặc số.
- Thời lượng và độ dài đoạn được ước tính theo nhịp âm tiết của **chính mẫu giọng**. Câu rất ngắn có giới hạn thời lượng tối thiểu và cơ chế giảm tốc để tránh ép lời vào đoạn âm thanh quá ngắn. Đây là cách kiểm soát đầu vào, không phải bảo đảm mô hình đọc đúng mọi từ.
- Các kiểu **kể chuyện, review, tin tức** điều chỉnh nhịp, tốc độ và khoảng nghỉ; chất giọng vẫn do mẫu và mô hình quyết định. Nếu có từ thiếu hoặc đọc gấp, thử tốc độ **0,8–0,9**, 16/32 bước và kiểm tra lời mẫu khớp bản thu. Tốc độ quá chậm có thể làm lẫn lời mẫu; luôn nghe thử.
- Hai MP3 gốc có sẵn để nghe và SHA256 để đối chiếu. Khi nạp đúng một trong hai tệp này vào Nhân bản, tool tự chọn đoạn đã xác nhận và điền lời mẫu: nam **0–4,5 giây**, nữ **0–5,3 giây**.
- Với bản thu khác, chọn tệp **3–30 giây**, lấy đoạn rõ tiếng **3–8 giây** bằng mốc bắt đầu/kết thúc, nghe đoạn rồi nhập **đúng lời Hmong trong đoạn đó**. Tránh nhạc nền, nhiều người nói và im lặng dài. Chỉ dùng mẫu bạn có quyền sử dụng; tool không tự đoán lời mẫu Hmong.
- Bấm **Lưu và tạo thử giọng Hmong** để lưu mẫu và tạo câu mới bằng giọng vừa thêm. Kết quả và tiến độ xuất hiện trong tab Tạo giọng. Nút **Lưu giọng cá nhân** chỉ lưu hồ sơ; nhập nội dung rồi bấm Tạo giọng để có bản thu.
- Có thể nhập/sửa phụ đề Hmong thủ công và lồng tiếng theo SRT. Phiên bản này không kèm nhận dạng giọng nói Hmong tự động. Whisper phổ thông không có Hmong trong danh sách ngôn ngữ; một bộ Whisper Hmong cộng đồng đã được thử riêng nhưng không đạt kiểm tra trên hai mẫu, nên không dùng để tự điền hoặc xác nhận lời. Dịch bằng Ollama hoặc dịch vụ khác cần thiết lập riêng.

Tốc độ phụ thuộc CPU/GPU, số bước, độ dài và nhịp đọc. Bản CPU không cần GPU nhưng vẫn cần đủ RAM; khoảng 8 GB RAM trở lên, 16 GB được khuyến nghị, cùng dung lượng đĩa cho mô hình, công việc và bản xuất. Không có cam kết tạo một giờ âm thanh trong hai phút hay tốc độ bằng nhau trên mọi máy. Mô hình cộng đồng vẫn có thể đọc sai một số từ hoặc đoạn dài; cần người biết Hmong nghe đánh giá phát âm và độ giống giọng.

## Khi gặp lỗi tải hoặc 403

Tải đúng **tệp ZIP trong Assets của GitHub Releases**. Nếu trình duyệt mở một trang lỗi hoặc tải ra HTML, chưa có gói cài đặt hợp lệ. Link tải có thể bị chặn bởi mạng hoặc hết hạn nếu sao chép địa chỉ CDN tạm; hãy mở lại trang Releases và bấm tên ZIP. Nếu mạng chặn GitHub, dùng mạng có quyền truy cập GitHub.

Lần tải mô hình còn cần `huggingface.co` và các máy chủ CDN `*.huggingface.co`, `*.hf.co`. Tool giữ kiểm tra TLS và checksum; không thể tự gỡ chính sách chặn của mạng. Sau khi tải mô hình thành công, tạo giọng offline không cần các kết nối này.

## Chạy từ mã nguồn đầy đủ

Trên Windows, tải/clone **toàn bộ kho mã nguồn**, mở thư mục `voice-studio`, chạy **`install_hmong.bat`**, sau đó **`start_hmong.bat`**. Bản nguồn cần Python **3.12 x64** để tạo môi trường riêng **`.venv-hmong`**. Bộ cài kiểm tra giao diện, giọng mẫu và FFmpeg; khi cần, nó dùng bộ tải FFmpeg có kiểm tra SHA256 trong kho. Không dùng bộ 46 tệp rời hoặc môi trường `.venv` của bản tiếng Việt.

Trên Linux, cài Python 3.12 và FFmpeg/ffprobe, rồi tạo môi trường riêng:

```sh
cd voice-studio
python3.12 -m venv .venv-hmong
.venv-hmong/bin/python -m pip install -r requirements-hmong.txt
.venv-hmong/bin/python -m pip check
./start_hmong.sh
```

Bản mã nguồn mặc định lưu dữ liệu ở `.data-hmong`. Có thể đặt `VOICE_STUDIO_DATA_DIR` tới thư mục riêng trước khi khởi động. Không dùng chung dữ liệu hoặc môi trường Python với phiên bản tiếng Việt. Người chạy mã nguồn có thể đặt `HMOOB_PRECISION=fp32` để giữ FP32 kể cả khi chọn nháp 4 bước; `HMOOB_PRECISION=int8` là tùy chọn thử nghiệm trên CPU hỗ trợ. INT8 chưa được xác nhận tương đương phát âm với FP32.

Nguồn mô hình được ghim theo revision và checksum trong `prepare_hmong.py`; SHA256 mẫu nam/nữ nằm trong `assets/hmong/voices.json`. Bản phát hành có báo cáo `NATIVE-VALIDATION.json` để đối chiếu kiểm tra Windows bằng suy luận thật. Các kiểm tra tệp, thư viện và âm thanh không thay thế đánh giá của người bản ngữ. Xem chi tiết trong `VALIDATION-HMONG.md`.
