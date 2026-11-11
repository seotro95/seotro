# AutoDoc Studio 2.2 — tự động edit đa ngôn ngữ

## Bản sửa 2.2.1: model VAD đi kèm bộ ZIP

Bản 2.2.0 đã loại nhầm `silero_vad_v6.onnx` ở bước đóng gói, sau khi kiểm thử EXE. Bản 2.2.1 chỉ bỏ các model ví dụ không dùng của ONNX Runtime và luôn giữ model VAD bắt buộc của faster-whisper. Bộ kiểm tra xác minh hash, khởi tạo ONNX và chạy suy luận VAD.

CI còn giải nén **đúng ZIP giao cho người dùng**, vô hiệu thư mục build gốc, chạy nhận dạng và xuất video Anh/Việt rồi mở GUI preview từ bản giải nén. Bộ ZIP 2.2.0 gốc được tải lại để tái hiện lỗi; bản vá nhỏ phải làm quy trình tự động chạy lại được mà không đổi EXE cũ. Xem `POST_PACKAGE_TEST_REPORT.json` trong release cho kết quả và hash ZIP đã thử.

Người đang dùng 2.2.0 có thể giải nén `SUA_LOI_VAD_2.2.0.zip` vào thư mục chứa `AutoDocStudio.exe`, hoặc dùng bộ Full 2.2.1. Không cần xóa cache/model đã tải hoặc các dự án. Model VAD nhỏ đã kèm trong ZIP; model Whisper/CLIP lớn và FFmpeg vẫn được tải riêng lần đầu.

Ngôn ngữ mặc định **auto**. Nhận lời theo ngôn ngữ gốc, giữ nguyên file voice làm âm thanh chính và giữ phụ đề gốc. Với voice ngoại ngữ, tool tạo bản lời **tiếng Anh cùng mốc** để CLIP so khớp hình; không dùng trực tiếp văn bản Việt/Nhật/Hàn với bộ so khớp tiếng Anh. Có thể cung cấp **Tham chiếu Anh** TXT/SRT để kiểm soát nội dung cần minh họa; SRT phải khớp thời gian voice.

Hỗ trợ các ngôn ngữ của Whisper, gồm Anh, Việt, Tây Ban Nha, Pháp, Nhật, Hàn, Đức, Ý, Bồ Đào Nha, Hà Lan, Ba Lan, Thụy Điển, Đan Mạch, Phần Lan, Na Uy và Séc. Có lựa chọn ngôn ngữ cụ thể khi tự nhận diện sai. Mặc định Whisper **base** để cải thiện lời ngoại ngữ; tiny nhanh hơn, small thường chính xác hơn nhưng chậm hơn. Tên khoa học/tên riêng vẫn có thể sai.

**H’Mông không có ASR đáng tin cậy trong Whisper.** Chọn `hmn`, nhập SRT tiếng Anh đúng mốc ở Tham chiếu Anh. Có thể thêm SRT H’Mông ở ô Phụ đề để giữ phụ đề H’Mông; nếu không, lời hiển thị sẽ lấy từ tham chiếu Anh. Tool giữ nguyên audio H’Mông, không giả lập việc nhận dạng H’Mông.

Cảnh có điểm khớp ý thấp được tô nền vàng trên timeline và ghi trong báo cáo. AI chọn cảnh gần nghĩa nhất trong nguồn bạn cung cấp, không bảo đảm từng chi tiết khoa học hay cảnh thiếu nguồn đều đúng. Hãy xem các cảnh được đánh dấu trước khi đăng. SRT gốc tiếng Anh hoặc tham chiếu Anh đúng mốc có thể bỏ bước dịch; SRT ngoại ngữ không có tham chiếu Anh vẫn cần dịch voice để chọn hình. Nhật/Hàn cần phông có bộ chữ tương ứng nếu ghi phụ đề vào hình.

**TỰ ĐỘNG EDIT & XUẤT**: chọn voice, thư mục ảnh/video và nơi lưu rồi bấm một lần. Tool nhận lời (hoặc dùng TXT/SRT), chọn cảnh, dựng mở đầu, ghép voice, áp dụng logo/phụ đề theo cài đặt, xuất video và lưu dự án. Không dừng để yêu cầu bấm Xuất lần nữa. Các lần xuất trùng tên được đánh số để giữ bản trước. Có thể mở dự án đi kèm để sửa tiếp.

Tab **AI / xuất** chọn độ phân giải, FPS, chất lượng, CPU/GPU, MP4/MKV và tên video tự động trước khi bắt đầu. Mặc định 720p/24 FPS, chỉ giữ voice. Thư mục `TU_DONG_EDIT` chứa các dự án tự động; file `.autodoc.json` cùng tên video là bản dự án của đúng lần xuất đó.

Bản Full chứa toàn bộ chức năng và 20 preset hiệu ứng sẵn có, không cần mua thêm hoặc cài Python. Lần đầu vẫn cần Internet để tool tự tải FFmpeg và model AI vào cache; ZIP không kèm các tệp lớn này. Những lần sau dùng lại cache.

Tool Windows dựng phim từ voice và thư mục **ảnh + video**, có xem trước và chỉnh cảnh. Voice quyết định thời lượng. Các tệp nguồn được giữ nguyên.

## Dùng bản Windows

1. Giải nén ZIP, giữ thư mục `_internal` cạnh `AutoDocStudio.exe`, rồi mở EXE. Windows 10/11 x64, khuyến nghị RAM 8 GB trở lên.
2. Chọn voice, thư mục ảnh/video, nơi lưu dự án. Có thể thêm TXT/SRT. Bấm **Tự xếp cảnh**. Lần đầu cần mạng tải FFmpeg và model từ nguồn chính thức; các lần sau dùng cache. Không cần API trả phí.
3. Chọn cảnh trên timeline để phát hình + đoạn voice tương ứng. Chọn nguồn, điểm lấy, tốc độ, phóng/cắt, tâm cắt, hiệu ứng và chuyển cảnh. Bấm **Áp dụng và xem trước**. Có chia cảnh tại con trỏ, gộp cảnh trước, đổi nguồn lên/xuống; tổng thời lượng lời không đổi. Bấm lên khung hình để đặt tâm cắt, không phải di chuyển logo.
4. Tab **Logo / tiếng**: chọn logo (PNG giữ alpha), vị trí, cỡ %, độ hiện. Mặc định **tắt tiếng clip gốc**. Bỏ chọn để trộn tiếng clip cùng voice theo âm lượng 0–1. Ảnh không sinh âm thanh.
5. Tab **Phụ đề**: nhập/xuất TXT/SRT, sửa từng câu và mốc giây, chọn phông đã cài trên máy, màu, cỡ, đậm/nghiêng, viền, nền và vị trí. Chọn `burn` để ghi kiểu chữ vào hình; `soft` để có đường phụ đề bật/tắt trong trình phát (kiểu hiển thị phụ thuộc trình phát, preview tích hợp không hiện đường mềm); `none` để xuất hình không phụ đề. Cỡ chữ tính ở 720p và tự tăng theo độ phân giải.
6. **Lưu dự án** lưu JSON để mở sửa lần sau. Giữ voice, media gốc và thư mục cache của dự án đúng vị trí; JSON không gói media vào bên trong. Việc xếp cảnh lưu dự án ban đầu tự động. Video hoàn chỉnh chỉ xuất khi bấm **Xuất video…**: chọn 720/1080p, 24/25/30/60 FPS, MP4/MKV, chất lượng, bộ mã hóa và tên/nơi lưu.
7. Tab Cảnh có **Tải gói hiệu ứng bổ sung**. Tool tự tìm manifest chính thức, kiểm SHA256, cài danh sách preset tương thích. Có sẵn các hiệu ứng cơ bản và chuyển cảnh khi không có mạng. Không tự tải DLL/plugin lạ hoặc cài driver GPU.

## Tăng tốc

- `fast`: beam 1, một ảnh mẫu cho mỗi đoạn nguồn 10 giây. `balanced/quality`: lấy ba mẫu và beam 5; có thể chọn Whisper base/small để tăng độ chính xác, tốn thêm thời gian/RAM.
- **SRT đúng mốc bỏ qua bước chép lời gốc**. SRT tiếng Anh hoặc tham chiếu Anh đúng mốc không cần dịch; SRT ngoại ngữ có thể cần dịch voice sang Anh để chọn hình. TXT chỉ có lời, không có mốc: tool căn theo Whisper khi xếp lần đầu; nhập TXT vào dự án có sẵn sẽ căn theo mốc lời hiện có. Tỷ lệ khớp thấp được báo để sửa lại.
- Đọc khung hình video qua PyAV, dùng cache đặc trưng CLIP theo nội dung tệp giữa nhiều dự án. Xuất hai cảnh song song, cache riêng từng cảnh và từng phiên bản cài đặt. Chỉnh cảnh nào chỉ dựng lại phần bị ảnh hưởng; đổi logo/kiểu phụ đề burn tác động mọi cảnh.
- `auto` thử mã hóa thật với NVIDIA / Intel / AMD, rồi dùng CPU nếu không khả dụng. Có thể chọn CPU/GPU thủ công; nếu GPU lỗi lúc dựng sẽ thử lại CPU. Tốc độ thực tế tùy máy, nguồn, độ phân giải và hiệu ứng, không cam kết số lần nhanh hơn.
- Không cần bật **giải mã toàn phim** cho mỗi bản nháp. Khi tắt, tool vẫn kiểm thời lượng, số khung và đối chiếu mẫu voice nếu chỉ giữ tiếng voice. Khi chủ động trộn tiếng clip, bỏ kiểm tương quan mẫu vì âm thanh đã trộn; vẫn kiểm luồng/thời lượng và giải mã nếu được chọn.

## Quy trình tự động

Whisper/SRT → CLIP nhận diện ảnh và video → xếp cảnh theo đoạn lời, mở đầu 10 cảnh/30 giây khi đủ nguồn → chỉnh tay/xem trước → logo, phụ đề, chuyển cảnh → xuất → kiểm tra → lưu video và báo cáo `.qa.json`.

AI chọn cảnh theo tương đồng, không đảm bảo hiểu đúng mọi chi tiết. Lọc trẻ em cũng là ước lượng; nên chỉ đưa nguồn phù hợp và xem lại trước đăng. Tool không tự tải cảnh bên ngoài hoặc tạo bảng chữ để bù clip thiếu. Nó có thể dùng lại nguồn liên quan, lặp video ngắn hoặc tạo chuyển động cho ảnh người dùng đã cung cấp.

## Cài từ mã nguồn / CLI

Python 3.12 x64: chạy `CAI_DAT.bat`, sau đó `MO_TOOL.bat`. Linux cần FFmpeg trong PATH và thư viện Tk; giọng preview dùng MCI trên Windows, trên Linux preview hình vẫn hoạt động.

```text
python main.py --auto-edit --voice narration.wav --media media_folder --output projects --settings settings.json --result-json result.json
python main.py --voice narration.wav --media media_folder --output projects --prepare-only --result-json result.json
python main.py --project project.autodoc.json --export-to finished.mp4 --result-json result.json
```

Không có `--prepare-only`, CLI tự xếp và xuất. `--videos` là tên thay thế của `--media`. JSON cài đặt tùy chọn gồm `subtitle_path`, `subtitle_mode`, `logo_path`, `mute_source`, `resolution`, `fps`, `quality`, `encoder`; xem `autodoc/project.py` cho giá trị mặc định. Build Windows bằng `build_windows.ps1`; script kiểm EXE thật trước đóng gói.

Model/FFmpeg dùng chung cache v1 tại `%LOCALAPPDATA%/AutoDocStudio`; không cần tải CLIP lại nếu đã có. Dự án v2 dùng schema mới, không nhập trực tiếp project v1. Không xóa dữ liệu v1.

Lỗi xem trong khung nhật ký và `%LOCALAPPDATA%/AutoDocStudio/last_error.log`, `application.log`. Có thể dừng tác vụ; cache cảnh đã xong được giữ. Không sửa/xóa nguồn để khắc phục lỗi. Dự án phim dài cần ổ đủ chỗ cho file xuất, voice PCM và cache cảnh; thường nên dành vài GB.
