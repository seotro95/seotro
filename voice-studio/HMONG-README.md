# Voice Studio Hmong 1.4.0

Phiên bản riêng của Voice Studio 3.6.2, đọc **Hmong Trắng / Hmoob Daw (mww)** bằng mô hình F5-Hmong. Giao diện và hướng dẫn dùng tiếng Việt. Hai giọng mặc định cũ đã được thay bằng đúng tệp **hmong nam 2.MP3** và **hmong nữ 2(1).MP3** bạn cung cấp.

Bản 1.4 sửa cách giữ cả cụm khi nhấn giọng, gom câu mặc định, thêm bộ CUDA NVIDIA riêng và đo tốc độ theo phần lời đọc. **Chưa kiểm chứng đạt 30× (1 giờ lời đọc trong 2 phút), chưa xác nhận mô hình đọc chuẩn các từ `ua, thaj, qab, faib, rov, ris`.** Nút “Đo tốc độ và thử 6 từ Hmong” tạo câu mới để nghe đối chiếu; không thay chữ Hmong bằng cách viết giả lập tiếng Việt.

## Mở bản Windows đầy đủ

1. Tải **`Voice-Studio-Hmong-1.4.0-Windows-x64.zip`** trong GitHub Releases và giải nén **toàn bộ ZIP** vào một thư mục có quyền ghi. Không chạy bên trong ZIP. Bộ 46 tệp `.py`/`.bat`/hướng dẫn rời thiếu giao diện `static/`, giọng `assets/hmong/` và runtime nên không đủ để chạy.
2. Mở **`MO_VOICE_STUDIO_HMONG.bat`** ở thư mục ngoài cùng. Gói có sẵn Python 3.12 x64, thư viện CPU và FFmpeg; không cần tự cài Python, API key hay GPU. Các lối mở `start.bat`, `start_hmong.bat` và các tệp tương ứng trong `voice-studio-hmong/` đều chuyển tới bộ khởi động Hmong của gói. `install_hmong.bat` hoặc `install.bat` chỉ chuẩn bị lần đầu, sau đó mở tool để dùng.
3. Lần mở đầu cần Internet để tải và kiểm tra khoảng **1,4 GB mô hình** từ Hugging Face. Giữ cửa sổ đang chạy mở. Nếu chuẩn bị thất bại, xem thông báo rồi mở lại sau khi khắc phục kết nối. Các trọng số Hmong không nằm trong ZIP vì nguồn chưa công bố giấy phép phân phối lại rõ ràng.
4. Trình duyệt tự mở khi sẵn sàng. Sau lần chuẩn bị thành công, tạo giọng hoạt động offline. Giữ cửa sổ tool mở trong lúc sử dụng; đóng cửa sổ để dừng máy chủ.

`KIEM_TRA_HMONG.bat` kiểm tra các tệp ứng dụng/giao diện, checksum hai giọng, FFmpeg, thư viện và mô hình đã lưu. Lệnh này không tải thêm và không tạo âm thanh; thông báo PASS không phải đánh giá phát âm. Trước lần chuẩn bị đầu, thông báo thiếu mô hình là bình thường. Nếu thiếu `static/` hoặc `assets/hmong/`, hãy giải nén lại cả gói thay vì chỉ chép các tệp `.py`.

Dữ liệu cá nhân của bản Windows nằm trong **`voice-studio-hmong/.data`**. Sao lưu thư mục này trước khi đổi phiên bản; không ghi đè hoặc xóa hồ sơ giọng và công việc cũ khi giải nén bản mới.

Tác vụ mới ghi nhận đúng mẫu giọng và lời tham chiếu để tiếp tục an toàn. Nếu tác vụ cũ dùng giọng mặc định đã thay, tool yêu cầu tạo tác vụ mới để tránh trộn hai giọng trong một bài; các đoạn đã tạo và lịch sử vẫn được giữ.

## Tạo giọng và nhân bản

- Nhập văn bản **Hmong chữ Latin RPA**, hoặc nhập TXT/SRT; chọn giọng nam/nữ rồi tạo giọng. Có thể tải WAV, MP3 và xuất nội dung TXT/SRT. Nên nghe một đoạn ngắn trước khi tạo cả kịch bản.
- Mặc định **16 bước**, ưu tiên độ rõ hơn chế độ nháp 4 bước của bản trước. Có thể chọn **4/8 bước để nháp nhanh**, hoặc **32 bước** để nghe so sánh. Chế độ 16/8/32 bước trên CPU mặc định dùng FP32. Khi chọn riêng **nháp 4 bước**, tool tự dùng INT8 nếu CPU hỗ trợ và quay về FP32 nếu không dùng được; không cần chỉnh cấu hình máy. Bản nháp có thể giảm độ rõ và tự nhiên. Mô hình và mẫu tham chiếu được giữ trong RAM để dùng lại, các câu ngắn được gom vào đoạn phù hợp để giảm số lần suy luận.
- Bộ đọc giữ nguyên các chữ cuối ghi thanh điệu RPA như `b/j/v/s/g/m/d`, chuẩn hóa khoảng trắng và dấu câu thông dụng. Văn bản dùng hệ chữ khác hoặc ký tự mô hình chưa hỗ trợ được báo lỗi để sửa, thay vì âm thầm mất chữ. Hãy viết số, chữ viết tắt và tên riêng thành lời Hmong muốn đọc khi cần; tool không tự biết cách đọc mọi tên hoặc số.
- Thời lượng và độ dài đoạn được ước tính theo nhịp âm tiết của **chính mẫu giọng**. Câu rất ngắn có giới hạn thời lượng tối thiểu và cơ chế giảm tốc để tránh ép lời vào đoạn âm thanh quá ngắn. Đây là cách kiểm soát đầu vào, không phải bảo đảm mô hình đọc đúng mọi từ.
- Mặc định chọn **Kể chuyện · Ấm áp**, giữ cả cụm và **tắt chèn nghỉ tự động** để giảm số lần tạo. Có thể chọn sắc thái Tự nhiên, Ấm áp, Tươi vui, Trầm lắng, Nghiêm túc hoặc Hồi hộp. Đây là điều khiển nhịp, cường độ và khoảng nghỉ; mô hình F5-Hmong không có bộ diễn xuất cảm xúc đã được huấn luyện hoặc bảo đảm giống người thật.
- Nhịp tự động giữ các ranh giới câu để chèn nghỉ và có thể tạo lâu hơn. Mặc định tắt **Nhịp tự động** để gom câu, ưu tiên tốc độ; có thể bật lại để thêm khoảng nghỉ theo câu. Không uốn cao độ hay thêm rung giọng tùy ý vì Hmong có thanh điệu mang nghĩa. Chất giọng và cách phát âm vẫn phụ thuộc bản thu, lời mẫu và mô hình.
- Hai MP3 mới có sẵn để nghe và SHA256 để đối chiếu. Khi nạp đúng tệp, tool dùng đoạn **0–4,7 giây** cho cả nam và nữ, rồi điền **đúng lời Hmong bạn đã cung cấp và xác nhận ngày 23/10/2026**. Bản nữ rút gọn `hmong nữ 2(1).MP3` đã thay bản nữ dài. Lời vẫn sửa được và tool giữ lại nội dung bạn chỉnh. Hai giọng cũ không còn là mẫu mặc định.
- Với bản thu khác, chọn tệp **3–30 giây**, lấy đoạn rõ tiếng **3–8 giây** bằng mốc bắt đầu/kết thúc, nghe đoạn rồi nhập **đúng lời Hmong trong đoạn đó**. Tránh nhạc nền, nhiều người nói và im lặng dài. Chỉ dùng mẫu bạn có quyền sử dụng; tool không tự đoán lời mẫu Hmong.
- Bấm **Lưu và tạo thử giọng Hmong** để lưu mẫu và tạo câu mới bằng giọng vừa thêm. Kết quả và tiến độ xuất hiện trong tab Tạo giọng. Nút **Lưu giọng cá nhân** chỉ lưu hồ sơ; nhập nội dung rồi bấm Tạo giọng để có bản thu.
- Có thể nhập/sửa phụ đề Hmong thủ công và lồng tiếng theo SRT. Phiên bản này không kèm nhận dạng giọng nói Hmong tự động. Whisper phổ thông không có Hmong trong danh sách ngôn ngữ; phân tích ban đầu được chạy cục bộ, không gửi audio ra dịch vụ bên ngoài. Lời nhận dạng gợi ý đã được thay bằng lời bạn gửi; lời xác nhận này dùng cho mẫu tham chiếu, không có nghĩa mọi bản thu AI đã được người bản ngữ kiểm tra. Dịch bằng Ollama hoặc dịch vụ khác cần thiết lập riêng.

## Nhấn nhá và đổi sắc thái trong một bài

Chọn sắc thái và mức độ trên giao diện. Dùng `**cụm từ**` để nhấn một cụm, `[pause=0.5]` để nghỉ nửa giây, hoặc `[emotion=warm]` để đổi sắc thái từ vị trí đó. Các dấu điều khiển được tách trước khi tạo tiếng, không đọc thành lời. Nhấn được áp dụng cho **cả cụm đọc chứa phần đánh dấu**, giúp từ không bị tách thành một lượt tạo riêng. Tool chưa có căn chỉnh âm thanh chính xác từng từ. Không đặt dấu ** vào giữa chữ RPA; tool sẽ báo lỗi để tránh tách mất chữ thanh điệu. Giá trị được hỗ trợ: `neutral`, `warm`, `joyful`, `sad`, `serious`, `suspense`.

```text
[emotion=warm] Nyob zoo, kuv zoo siab tau ntsib nej.
[pause=0.4]
[emotion=suspense] **Hnub ntawd muaj dab tsi tshwm sim?**
```

Lời gốc của công việc vẫn giữ các thẻ để chỉnh sửa; phụ đề đi kèm âm thanh chỉ hiển thị lời đọc, không in thẻ điều khiển.

Trong TXT, sắc thái duy trì đến thẻ đổi tiếp theo. Trong SRT, mỗi cue bắt đầu lại bằng sắc thái đã chọn trên giao diện; các mốc thời gian vẫn được giữ, lời quá dài được báo để chỉnh thay vì cắt mất từ. Nên nhấn một cụm đủ nghĩa thay vì tách từng âm tiết.

Tốc độ phụ thuộc CPU/GPU, số bước, độ dài và nhịp đọc. Bản CPU không cần GPU nhưng vẫn cần đủ RAM; khoảng 8 GB RAM trở lên, 16 GB được khuyến nghị, cùng dung lượng đĩa cho mô hình, công việc và bản xuất. Không có cam kết tạo một giờ âm thanh trong hai phút hay tốc độ bằng nhau trên mọi máy. Mô hình cộng đồng vẫn có thể đọc sai một số từ hoặc đoạn dài; cần người biết Hmong nghe đánh giá phát âm và độ giống giọng.

## Dùng GPU NVIDIA

Bộ ZIP mặc định vẫn chạy CPU. Nếu máy có NVIDIA và driver tương thích CUDA 12.8, chạy **`install_hmong_cuda.bat`** rồi mở lại tool bằng `MO_VOICE_STUDIO_HMONG.bat`. Bộ cài cần Internet và vài GB dung lượng, tạo môi trường GPU riêng trong thư mục dữ liệu; không thay PyTorch CPU hoặc xóa giọng/công việc. Cần đóng tool trước khi cài để lượt mở tiếp theo dùng đúng bộ chạy.

Tool chỉ lưu trạng thái sẵn sàng sau khi đúng phiên bản PyTorch/torchaudio chạy được phép tính trên GPU. Khi mở lại, nó kiểm tra GPU trước khi chuyển bộ chạy; bộ GPU thiếu/hỏng hoặc bị chuyển thư mục sẽ có hướng dẫn cài lại, còn bộ CPU vẫn dùng được. Máy không có NVIDIA sẽ được báo ngay, trước khi tải thư viện. Đặt `HMOOB_DEVICE=cpu` để chọn CPU rõ ràng. Người chạy mã nguồn Linux có thể dùng `python hmong_launcher.py --install-cuda` trong môi trường Hmong đã cài.

Kiểm tra tensor CUDA thành công **không chứng minh tốc độ 30× hoặc phát âm chuẩn**. Môi trường kiểm tra hiện tại không có NVIDIA nên chưa chạy suy luận GPU thật. Với máy chỉ có CPU, sửa mã và giảm số bước không đủ để hứa mục tiêu 1 giờ / 2 phút.

Báo cáo tốc độ loại thời gian nghỉ/phụ đề do tool chèn thêm; khoảng yên lặng nằm bên trong một đoạn do model tạo vẫn được giữ. Mẫu dưới 60 giây chưa dùng để kết luận tốc độ duy trì. Chỉ lượt thực sự tạo ít nhất 3.600 giây đoạn lời đọc trong tối đa 120 giây mới được ghi nhận đã kiểm chứng mục tiêu một giờ; lượt tiếp tục từ bộ đệm không dùng để đo lại tốc độ.

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
