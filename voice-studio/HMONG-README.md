# Voice Studio Hmong 1.6.0

Phiên bản riêng của Voice Studio 3.6.2 cho **Hmong Trắng / Hmoob Daw (mww)**. Bản 1.6.0 chỉ có **một ZIP chính để tải** và **một tệp mở ở ngoài cùng: `MO_VOICE_STUDIO_HMONG.bat`**. Tệp này chọn bộ đọc nhanh **VITS + OpenVoice V2**; không còn vô tình mở F5 chậm khi dùng tệp chính. Hai giọng mặc định vẫn là **hmong nam 2.MP3** và **hmong nữ 2(1).MP3** cuối cùng bạn cung cấp.

Bộ nhanh tạo lời Hmong bằng VITS rồi chuyển chất giọng theo mẫu. **Giữ nguyên bộ phát âm Hmong bạn đã xác nhận; chưa đạt mục tiêu 1 giờ lời đọc trong 2 phút và không bảo đảm nhân bản giống 100%.** Kiểm tra đã xác nhận các chữ và ký tự ghi thanh điệu được giữ nguyên, khớp cách xử lý của mô hình gốc. Không thay chúng bằng cách viết giả lập tiếng Việt. Bản này không đổi hoặc huấn luyện lại mô hình phát âm. Nhân bản mẫu ngắn chuyển chất giọng, không huấn luyện lại cách phát âm của mô hình.

## Chọn Nam / Nữ và tạo voice

Bấm **Nam** hoặc **Nữ** ở mục Tạo giọng hay Tạo voice riêng. Lựa chọn dùng chung hai khu vực; mục đang chọn được đánh dấu và bản thu mới dùng đúng mẫu đó. Có thể nghe mẫu gốc nam/nữ trước khi tạo. Chọn một giọng có sẵn từ Thư viện sẽ tự bỏ bộ lọc giọng cá nhân đang che giọng đó, để nút Tạo giọng hoạt động.

Bản 1.5.3 đã sửa hai lỗi chọn giọng: giọng có sẵn bị mất khỏi danh sách sau bộ lọc cá nhân, và chọn nữ ở một khu vực nhưng khu vực khác vẫn gửi giọng nam. Dấu gạch nối trong chữ Hmong được giữ trong kịch bản gốc và chuyển thành ranh giới từ khi đưa vào bộ đọc nhanh; không tự thay chữ hay ký tự thanh điệu. Model của nam/nữ dùng chung, trạng thái tải model được hiển thị nhất quán.

## Kịch bản dài và chia phần

TXT Hmong có thể nhập tối đa **1.000.000 ký tự**; trên 20.000 ký tự được chia chương/phần tự động theo các đoạn đọc đã lập kế hoạch, giữ nguyên thứ tự và điều khiển sắc thái/khoảng nghỉ. Chia chương dài dùng cho TXT không ghép video; SRT phân vai và lồng tiếng video vẫn giữ giới hạn riêng, tối đa ba giờ. Nội dung dài được lập kế hoạch thành chương/phần để xuất từng phần WAV/MP3, kèm TXT/SRT và manifest trong một ZIP. Đây là giới hạn nhập và cách tổ chức công việc; tạo một triệu ký tự vẫn cần thời gian, RAM và dung lượng đĩa tương ứng. Hãy tạo thử một đoạn ngắn trước, giữ cửa sổ tool mở và kiểm tra các phần xuất trước khi dùng.

## Phân giọng nhân vật cho SRT

Trong phần phụ đề của xưởng video, thêm nhân vật, chọn giọng Hmong đã có cho từng nhân vật và gán nhân vật cho từng cue. Cue chưa gán dùng giọng mặc định. Phân vai được lưu riêng với lời SRT, không thêm tên nhân vật vào lời đọc; hỗ trợ tối đa 32 nhân vật trong một kịch bản. Tác vụ ghi lại mẫu và lời tham chiếu của từng giọng để tiếp tục đúng giọng; khi mẫu đã thay hoặc bị xóa, cần tạo tác vụ mới. Hai cue dùng cùng một giọng vẫn giữ đúng thời gian SRT.

Bộ nhanh giữ tối đa **16 mẫu tham chiếu đã dùng gần nhất** trong RAM và dùng lại khi đổi qua lại giữa các giọng. Đây là bộ đệm có giới hạn, không phải thêm 16 giọng vào model hay huấn luyện lại phát âm. Chất lượng nhân bản vẫn phụ thuộc bản thu, lời mẫu và mô hình; không có bảo đảm giống bản thu 100%.

Khi chuẩn hóa âm lượng, hệ số khuếch đại được giới hạn theo đỉnh tín hiệu để tránh tự tạo các đỉnh bị cắt phẳng. Đoạn mẫu có chỉ dẫn về mức âm, khoảng yên lặng và tín hiệu sát toàn thang; các số đo này chỉ là gợi ý để nghe/chọn mẫu, không nhận dạng lời nói hay chấm điểm độ giống giọng.

## Sửa lỗi không mở được tool ở bản 1.5.0

Bản 1.5.1 sửa lỗi “Voice Studio đã chạy với thư mục dữ liệu này” khi bấm mở lần hai. Tool tự nhận đúng phiên đang chạy và mở lại địa chỉ của phiên đó; bài đang tạo tiếp tục bình thường. Tệp `server.lock` còn lại sau khi tắt hoặc tệp rỗng không bị coi là một phiên đang chạy. Lỗi quyền ghi hay ổ đĩa không hỗ trợ khóa được báo riêng.

Khi đổi từ bản cũ, đóng tool và sao lưu **`voice-studio-hmong/.data`**, rồi giữ hoặc chép thư mục dữ liệu này sang gói mới. Đây là nơi chứa model, giọng cá nhân và lịch sử. Không còn bản vá ZIP riêng cần lựa chọn; tải gói chính bên dưới. Không xóa dữ liệu cá nhân để xử lý lỗi khóa.

## Mở bản Windows đầy đủ

1. Tải **`Voice-Studio-Hmong-1.6.0-Windows-x64.zip`** trong GitHub Releases và giải nén **toàn bộ ZIP** vào thư mục có quyền ghi. Không chạy bên trong ZIP. Các thư mục `runtime`, `ffmpeg`, `voice-studio-hmong` và `tools` là thành phần cần thiết để tool chạy.
2. Mở **`MO_VOICE_STUDIO_HMONG.bat`** ở ngoài cùng. Python 3.12, thư viện CPU và FFmpeg đã có sẵn; không cần tự cài Python hoặc API key. Bộ mở chính chọn VITS + OpenVoice. Các công cụ nâng cao được gom trong `tools/`.
3. Lần đầu cần Internet để tải và kiểm tra khoảng **580 MB model của bộ nhanh**. Không cần tải F5 để dùng bộ chính. Các trọng số Hmong không đóng trong ZIP vì nguồn chưa công bố giấy phép phân phối lại rõ ràng. Giữ cửa sổ tool mở; sau khi chuẩn bị xong có thể tạo giọng offline.
4. Giao diện tự mở khi sẵn sàng. Nhập Hmong chữ Latin RPA hoặc TXT/SRT, chọn giọng nam/nữ hay giọng cá nhân rồi tạo voice. Xuất WAV/MP3/TXT/SRT trong giao diện.

`tools/KIEM_TRA_HMONG.bat` kiểm tra các tệp ứng dụng, checksum giọng, FFmpeg, thư viện và model đã lưu; không tải thêm và không tạo audio. Thiếu model trước lần chuẩn bị đầu là bình thường. Các báo cáo kiểm tra và MP3 do tool tạo được gom trong `reports/`; chúng không phải bản thu nguồn hay chứng nhận phát âm đúng.

Dữ liệu cá nhân của bản Windows nằm trong **`voice-studio-hmong/.data`**. Sao lưu thư mục này trước khi đổi phiên bản; không ghi đè hoặc xóa hồ sơ giọng và công việc cũ khi giải nén bản mới.

Tác vụ mới ghi nhận đúng mẫu giọng và lời tham chiếu để tiếp tục an toàn. Nếu tác vụ cũ dùng giọng mặc định đã thay, tool yêu cầu tạo tác vụ mới để tránh trộn hai giọng trong một bài; các đoạn đã tạo và lịch sử vẫn được giữ.

## Dùng bộ đọc nhanh thử nghiệm

Bộ đọc nhanh là mặc định của **`MO_VOICE_STUDIO_HMONG.bat`** trong gói 1.6.0. Lần đầu bộ này tải và kiểm tra khoảng **580 MB** mô hình VITS, OpenVoice V2 và thành phần đánh dấu âm thanh AI. Không cần tải bộ F5 1,4 GB để dùng riêng lựa chọn này. Sau khi chuẩn bị xong, việc tạo giọng diễn ra cục bộ, offline; tệp mẫu không được gửi tới dịch vụ suy luận bên ngoài.

Giao diện ghi **Hmong nhanh thử nghiệm** và ẩn lựa chọn số bước F5. Hai mẫu nam/nữ, hồ sơ giọng đã lưu, nhập/xuất TXT/SRT/WAV/MP3, sắc thái và phép thử sáu từ vẫn dùng được. Bộ đọc này không có bước 4/8/16/32; giảm số bước F5 không áp dụng cho nó. Hãy tạo tác vụ mới khi đổi bộ đọc, không nối một bài đang dở bằng bộ khác. Nếu muốn nghe so sánh với F5, đóng tool rồi mở **`tools/MO_F5_HMONG.bat`**. F5 là tùy chọn nâng cao, cần chuẩn bị riêng khoảng 1,4 GB model và thường chậm hơn nhiều trên CPU.

Bộ đọc nhanh và chuyển chất giọng có thể làm sai phát âm, thanh điệu hoặc độ giống mẫu; cần nghe kiểm tra cả nam và nữ. Tốc độ phải tính cả tạo lời, chuyển giọng và xuất tệp. Mục tiêu 1 giờ / 2 phút chưa đạt; không có cam kết tốc độ độc lập cấu hình máy. Bộ mới thử gắn WavMark khi đoạn đủ dài; đoạn quá ngắn không được gắn dấu và chưa kiểm chứng dấu còn nhận được sau xử lý/xuất MP3. Trọng số không được đóng vào ZIP; nguồn VITS Hmong chưa nêu giấy phép rõ ràng. Xem [hướng dẫn bộ đọc thử nghiệm](docs/HMONG-NATIVE.md) để biết cách chọn từ mã nguồn, nguồn mô hình và giới hạn.

## Tạo giọng và nhân bản

- Nhập văn bản **Hmong chữ Latin RPA**, hoặc nhập TXT/SRT; chọn giọng nam/nữ rồi tạo giọng. Có thể tải WAV, MP3 và xuất nội dung TXT/SRT. Nên nghe một đoạn ngắn trước khi tạo cả kịch bản.
- Với **F5 tùy chọn**, chọn **16 bước** để ưu tiên độ rõ hơn chế độ nháp 4 bước của bản trước. Có thể chọn **4/8 bước để nháp nhanh**, hoặc **32 bước** để nghe so sánh. Chế độ 16/8/32 bước trên CPU mặc định dùng FP32. Khi chọn riêng **nháp 4 bước**, tool tự dùng INT8 nếu CPU hỗ trợ và quay về FP32 nếu không dùng được; không cần chỉnh cấu hình máy. Bản nháp có thể giảm độ rõ và tự nhiên. Mô hình và mẫu tham chiếu được giữ trong RAM để dùng lại, các câu ngắn được gom vào đoạn phù hợp để giảm số lần suy luận. Bộ VITS + OpenVoice không dùng lựa chọn số bước này.
- Bộ đọc giữ nguyên các chữ cuối ghi thanh điệu RPA như `b/j/v/s/g/m/d`, chuẩn hóa khoảng trắng và dấu câu thông dụng. Văn bản dùng hệ chữ khác hoặc ký tự mô hình chưa hỗ trợ được báo lỗi để sửa, thay vì âm thầm mất chữ. Hãy viết số, chữ viết tắt và tên riêng thành lời Hmong muốn đọc khi cần; tool không tự biết cách đọc mọi tên hoặc số.
- Với F5, thời lượng và độ dài đoạn được ước tính theo nhịp âm tiết của **chính mẫu giọng**. Câu rất ngắn có giới hạn thời lượng tối thiểu và cơ chế giảm tốc để tránh ép lời vào đoạn âm thanh quá ngắn. Bộ VITS tạo lời trước khi chuyển chất giọng theo mẫu. Đây là cách xử lý đầu vào, không phải bảo đảm mô hình đọc đúng mọi từ.
- Mặc định chọn **Kể chuyện · Ấm áp**, giữ cả cụm và **tắt chèn nghỉ tự động** để giảm số lần tạo. Có thể chọn sắc thái Tự nhiên, Ấm áp, Tươi vui, Trầm lắng, Nghiêm túc hoặc Hồi hộp. Đây là điều khiển nhịp, cường độ và khoảng nghỉ; cả hai bộ đọc chưa có bộ diễn xuất cảm xúc đã được huấn luyện hoặc bảo đảm giống người thật.
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

Bộ ZIP mặc định vẫn chạy CPU. Nếu máy có NVIDIA và driver tương thích CUDA 12.8, chạy **`tools/install_hmong_cuda.bat`** rồi mở lại `MO_VOICE_STUDIO_HMONG.bat`. Công cụ F5 nâng cao nằm ở `tools/MO_F5_HMONG.bat`. Bộ cài cần Internet và vài GB dung lượng, tạo môi trường GPU riêng trong thư mục dữ liệu; không thay PyTorch CPU hoặc xóa giọng/công việc. Cần đóng tool trước khi cài để lượt mở tiếp theo dùng đúng bộ chạy.

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

Bản mã nguồn mặc định lưu dữ liệu ở `.data-hmong`. Có thể đặt `VOICE_STUDIO_DATA_DIR` tới thư mục riêng trước khi khởi động. Không dùng chung dữ liệu hoặc môi trường Python với phiên bản tiếng Việt. Để chọn bộ thử nghiệm từ môi trường Hmong đã cài, chạy `HMOOB_BACKEND=native ./start_hmong.sh` trên Linux; bỏ biến này hoặc đặt `HMOOB_BACKEND=f5` để dùng F5. Người chạy F5 có thể đặt `HMOOB_PRECISION=fp32` để giữ FP32 kể cả khi chọn nháp 4 bước; `HMOOB_PRECISION=int8` là tùy chọn thử nghiệm trên CPU hỗ trợ. INT8 chưa được xác nhận tương đương phát âm với FP32 và lựa chọn này không áp dụng cho bộ VITS + OpenVoice.

Nguồn mô hình được ghim theo revision và checksum trong `prepare_hmong.py` (F5) và `hmong_native_models.py`, được tải bằng `prepare_hmong_native.py` (VITS + OpenVoice); SHA256 mẫu nam/nữ nằm trong `assets/hmong/voices.json`. Bản phát hành có báo cáo `NATIVE-VALIDATION.json` để đối chiếu kiểm tra Windows bằng suy luận thật; “native” trong tên báo cáo này chỉ môi trường Windows chạy thật, không xác nhận phát âm bản ngữ. Các kiểm tra tệp, thư viện và âm thanh không thay thế đánh giá của người biết Hmong. Xem chi tiết trong `VALIDATION-HMONG.md`.
