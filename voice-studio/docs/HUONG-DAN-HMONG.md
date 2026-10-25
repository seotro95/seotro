# Hướng dẫn đầy đủ Voice Studio Hmong

Hướng dẫn cho người dùng **Voice Studio Hmong 1.6.2 trên Windows** lần đầu: tải gói đầy đủ, mở tool, tạo giọng Hmong Nam/Nữ, thêm giọng của mình, đọc TXT hoặc sách dài, phân vai SRT và xuất video. Tool dùng **Hmong Trắng / Hmoob Daw, chữ Latin RPA**. Giao diện hiển thị ngôn ngữ này là Hmong Trắng hoặc `mww`.

**Bắt đầu nhanh:** tải ZIP Windows đầy đủ → giải nén toàn bộ → mở `MO_VOICE_STUDIO_HMONG.bat` ở ngoài cùng → chờ tải mô hình lần đầu → chọn **Văn bản thành giọng nói** → chọn **Giọng Nam** hoặc **Giọng Nữ** → nhập câu Hmong → bấm **Tạo giọng nói** → nghe và tải WAV/MP3.

Bạn **không cần cài Python, không cần API key, không cần GPU** để tạo giọng Hmong bằng gói Windows đầy đủ. Lần đầu cần Internet và khoảng **580 MB mô hình**, ngoài dung lượng của ZIP, bộ chạy và các bản thu. Khi chuẩn bị xong, phần tạo giọng chạy trên máy và có thể dùng offline. Chức năng AI viết/dịch là tùy chọn riêng.

**Khi bấm Tạo giọng:** đọc trạng thái ngay dưới nút. Nếu studio chưa kết nối, chờ kiểm tra hoặc bấm **Thử kết nối lại**; lời đang soạn được giữ nguyên. Nếu báo ký tự chưa hỗ trợ, sửa đúng ký tự được chỉ ra rồi tạo lại. Ví dụ viết số `2` thành từ Hmong `ob` khi đúng nghĩa câu của bạn; URL, emoji và ký tự lạ cần sửa hoặc bỏ trước khi đọc. Tool không tự đoán hay đổi chính tả. Khi đã nhận công việc, trạng thái sẽ chuyển sang hàng đợi/đang tạo và hiện audio khi hoàn tất.

## Mục lục

1. [Chọn đúng gói và giải nén](#1-chọn-đúng-gói-và-giải-nén)
2. [Mở tool và tải mô hình lần đầu](#2-mở-tool-và-tải-mô-hình-lần-đầu)
3. [Tạo bản thu Nam và Nữ đầu tiên](#3-tạo-bản-thu-nam-và-nữ-đầu-tiên)
4. [Nhập và xuất TXT, SRT, WAV, MP3](#4-nhập-và-xuất-txt-srt-wav-mp3)
5. [Viết Hmong RPA để tool đọc](#5-viết-hmong-rpa-để-tool-đọc)
6. [Nhịp đọc, nhấn cụm, khoảng nghỉ và sắc thái](#6-nhịp-đọc-nhấn-cụm-khoảng-nghỉ-và-sắc-thái)
7. [Nhân bản giọng từ mẫu 3–8 giây](#7-nhân-bản-giọng-từ-mẫu-38-giây)
8. [Đọc sách dài đến một triệu ký tự](#8-đọc-sách-dài-đến-một-triệu-ký-tự)
9. [Tạo voice theo SRT và phân giọng nhân vật](#9-tạo-voice-theo-srt-và-phân-giọng-nhân-vật)
10. [Lồng tiếng và xuất video](#10-lồng-tiếng-và-xuất-video)
11. [Lưu và mở lại dự án](#11-lưu-và-mở-lại-dự-án)
12. [Dừng, tiếp tục và tắt tool](#12-dừng-tiếp-tục-và-tắt-tool)
13. [Sao lưu và chuyển sang bản mới](#13-sao-lưu-và-chuyển-sang-bản-mới)
14. [GPU NVIDIA và bộ F5 nâng cao](#14-gpu-nvidia-và-bộ-f5-nâng-cao)
15. [AI viết và dịch tùy chọn](#15-ai-viết-và-dịch-tùy-chọn)
16. [Sửa các lỗi thường gặp](#16-sửa-các-lỗi-thường-gặp)
17. [Kiểm tra trước khi dùng bản thu](#17-kiểm-tra-trước-khi-dùng-bản-thu)

## 1. Chọn đúng gói và giải nén

1. Mở trang phát hành chính thức: [github.com/seotro95/seotro/releases](https://github.com/seotro95/seotro/releases). Chọn bản **Voice Studio Hmong** và mở danh sách **Assets**.
2. Tải tệp đầy đủ **`Voice-Studio-Hmong-1.6.2-Windows-x64.zip`** trong bản phát hành 1.6.2. Hai mục **Source code (zip)** và **Source code (tar.gz)** là mã nguồn, không phải gói chạy sẵn. Không dùng vài tệp `.py` hoặc `.bat` tải rời để thay cho gói đầy đủ.
3. Trong File Explorer, bấm phải ZIP → **Extract All… / Giải nén tất cả…** → chọn thư mục có quyền ghi, ví dụ `D:\VoiceStudioHmong` hoặc một thư mục trong Documents → **Extract / Giải nén**. Với 7-Zip, chọn **Extract to… / Giải nén vào…**.
4. Mở **thư mục đã giải nén**. Tại thư mục ngoài cùng phải thấy `MO_VOICE_STUDIO_HMONG.bat` cùng các thư mục `runtime`, `ffmpeg`, `voice-studio-hmong` và `tools`. Nếu chúng nằm trong một thư mục con, mở tiếp thư mục đó.
5. Giữ nguyên cả bộ thư mục. Không kéo riêng tệp BAT ra Desktop, không chạy khi File Explorer vẫn đang mở nội dung bên trong ZIP, không chép chồng gói mới lên bộ đang chạy. Có thể tạo **shortcut** của BAT ra Desktop nếu muốn mở nhanh.

Gói dành cho **Windows x64**. Khoảng 8 GB RAM trở lên là mức tham khảo, 16 GB được khuyến nghị cho công việc dài; tốc độ tùy máy. Để đủ chỗ cho ZIP, thư mục giải nén, mô hình và audio, kiểm tra ổ đĩa còn trống trước khi tải hoặc tạo sách dài. WAV chiếm nhiều dung lượng hơn MP3. Nên dùng ổ cục bộ; thư mục mạng hoặc đồng bộ đang khóa tệp có thể gây lỗi lưu dữ liệu.

Nếu bạn đã dùng bản cũ, làm phần **Sao lưu và chuyển sang bản mới** trước. Gói Windows có sẵn bộ chạy; các tệp `install_hmong.bat` trong mã nguồn dành cho người tự cài môi trường, không phải bước bắt buộc của người dùng ZIP.

## 2. Mở tool và tải mô hình lần đầu

1. Bấm đúp **`MO_VOICE_STUDIO_HMONG.bat` ở thư mục ngoài cùng**. Một cửa sổ dòng lệnh hiện ra. Giữ cửa sổ này mở trong lúc dùng tool.
2. Tool kiểm tra tệp ứng dụng, FFmpeg và **thực sự nạp thử thư viện, chạy phép tính âm thanh** trước khi mở giao diện. Lần đầu, cửa sổ sẽ ghi đang tải/kiểm tra mô hình Hmong nhanh, OpenVoice V2 và thành phần đánh dấu âm thanh AI, tổng khoảng **580 MB**. Thời gian phụ thuộc mạng và máy; không đóng cửa sổ chỉ vì giao diện chưa mở ngay.
3. Chờ tải và kiểm tra SHA-256 xong. Trình duyệt sẽ tự mở địa chỉ nội bộ có dạng **`http://127.0.0.1:8770`**. Cổng thực tế có thể khác; dùng đúng địa chỉ sau chữ **`Studio:`** trong cửa sổ dòng lệnh.
4. Nếu trình duyệt không tự mở, sao chép đúng địa chỉ `Studio:` rồi dán vào thanh địa chỉ Edge hoặc Chrome. Không gõ đường dẫn thư mục hay mở trực tiếp `static/index.html`.
5. Trong giao diện, bộ chính phải được ghi là **Hmong nhanh thử nghiệm**. Khi mô hình đã sẵn sàng, chọn giọng để tạo thử theo phần tiếp theo.

**Lần đầu cần mạng đến Hugging Face:** `huggingface.co` cùng CDN của Hugging Face, như các tên miền kết thúc bằng `.huggingface.co` hoặc `.hf.co`. Nếu mạng chặn, thực hiện hướng dẫn lỗi 403 ở cuối tài liệu. Tool kiểm tra TLS và SHA-256; đừng thay mô hình bằng tệp tải từ nguồn không rõ hoặc bỏ kiểm tra này.

Mở lại BAT lần sau sẽ dùng mô hình đã lưu nếu tệp hợp lệ. Bạn không phải tải lại 580 MB mỗi lần và không cần tải mô hình F5 khoảng 1,4 GB để dùng bộ chính. Nếu tải gián đoạn, tool tự thử lại tối đa **ba lần trong một lượt**, giữ tệp tải dở **`.part`** để tiếp tục khi mở lại. Máy chủ nguồn phải hỗ trợ tải tiếp; nếu không, phần đó được tải lại từ đầu. Tệp sai kích thước hoặc SHA-256 sẽ không được cài. Chỉ đóng tab trình duyệt không làm máy chủ dừng; bấm lại BAT khi cùng bộ đang chạy thường sẽ mở lại phiên đó.

**Mở hướng dẫn ngay trong tool:** bấm nút **?** → **Mở hướng dẫn đầy đủ · có thể in**. Tài liệu mở ở địa chỉ nội bộ `/help/hmong`; bấm **In / Lưu PDF** để in hoặc chọn Save as PDF trong hộp thoại in. Khi tool chưa mở, bạn có thể mở tệp HTML hướng dẫn đi kèm bằng trình duyệt.

### Ba mức kiểm tra: bộ chạy, mô hình và giọng thật

Không coi thông báo “đủ tệp” là đã tạo được lời đọc. Bản 1.6.2 có các lệnh sau; chạy sau khi lưu công việc và đóng phiên tạo giọng. Mở thư mục ngoài cùng trong File Explorer, bấm thanh địa chỉ, gõ `cmd` rồi Enter để mở dòng lệnh đúng thư mục. Gõ **một lệnh cần dùng**, bấm Enter và chờ kết quả:

| Lệnh | Kiểm tra gì? | Có tải model / tạo lời không? |
| --- | --- | --- |
| `MO_VOICE_STUDIO_HMONG.bat --probe-runtime` | Nạp thư viện thật, thử phép tính PyTorch/NumPy và đọc ghi/xử lý âm thanh. Lưu `runtime-check.json`. | Offline, không tải trọng số, không tạo lời đọc. |
| `MO_VOICE_STUDIO_HMONG.bat --check` | Thử bộ chạy như trên, sau đó kiểm tra tệp và SHA-256 mô hình đã lưu. `tools\KIEM_TRA_HMONG.bat` dùng mức này. | Offline, không tải thêm, không tạo lời đọc. |
| `MO_VOICE_STUDIO_HMONG.bat --test-voice` | Thử bộ chạy, chuẩn bị mô hình nếu thiếu rồi **thực sự tạo hai WAV Nam và Nữ**. Lưu `speech-check.json`. | Có tải model nếu cần; có suy luận và tạo lời thật. |

Báo cáo và hai tệp nghe thử nằm trong gói Windows tại:

```text
voice-studio-hmong\.data\diagnostics\runtime-check.json
voice-studio-hmong\.data\diagnostics\speech-check.json
voice-studio-hmong\.data\diagnostics\test-male.wav
voice-studio-hmong\.data\diagnostics\test-female.wav
```

Mở hai WAV để nghe; lệnh kiểm tra giọng không thêm chúng vào Lịch sử bản thu. Báo cáo kiểm tra tệp audio có tín hiệu, thời lượng và định dạng hợp lệ, **không chấm phát âm hay độ giống giọng**. `--check` báo thiếu model trên máy mới là bình thường; mở BAT chính hoặc dùng `--test-voice` với mạng được phép để chuẩn bị model. Nếu bộ chạy lỗi trước khi tới bước tải, đọc thông báo và `runtime-check.json` để sửa đúng thành phần.

## 3. Tạo bản thu Nam và Nữ đầu tiên

1. Chọn tab **Văn bản thành giọng nói** ở thanh bên. Trong **Định dạng lời**, chọn **TXT · đọc liên tục**.
2. Dán câu thử này vào khung **Nội dung của bạn**:

```text
Nyob zoo. Kuv zoo siab tau ntsib koj. Ua tsaug rau koj mloog.
```

3. Trong **Thiết lập giọng đọc**, kiểm tra ngôn ngữ là Hmong Trắng, bấm **Giọng Nam**. Dòng **Đang chọn:** phải hiển thị đúng giọng Nam. Trình phát **Nghe mẫu tham chiếu (bản thu gốc)** là mẫu người nói dùng để tham chiếu, chưa phải kết quả AI đọc câu bạn nhập.
4. Lần thử đầu giữ tốc độ **1×**, nhịp **Kể chuyện**, sắc thái **Ấm áp**, mức độ khoảng **65%**, tắt **Tự chia nhịp kể chuyện cho TXT**, nghỉ bổ sung **0 giây**. Nếu bạn đã đổi nhiều thiết lập, dùng các giá trị này để có điểm so sánh nhất quán.
5. Chọn **Định dạng xuất** là **WAV** hoặc **MP3**. Bấm **Tạo giọng nói** một lần. Theo dõi phần trăm và trạng thái; mô hình nạp lần đầu có thể lâu hơn lượt kế tiếp.
6. Khi trạng thái **Hoàn tất**, bấm phát trong khung kết quả. Nghe đủ câu, sau đó bấm liên kết **Tải…** để lưu tệp về máy. Trình duyệt thường lưu vào Downloads hoặc hỏi nơi lưu tùy cài đặt.
7. Bấm **Giọng Nữ**, kiểm tra lại dòng **Đang chọn:**, giữ nguyên văn bản rồi bấm **Tạo giọng nói** để có bản thứ hai. Đổi giọng chỉ có hiệu lực với lượt tạo mới; bản thu đã có giữ giọng cũ.
8. Mở **Lịch sử bản thu** để nghe lại cả hai bản và tải lại khi cần.

Hai giọng mặc định dùng mẫu Nam **`hmong nam 2.MP3`** và mẫu Nữ rút gọn **`hmong nữ 2(1).MP3`**. Hai nút Nam/Nữ dùng chung lựa chọn giữa tab tạo giọng và phần tạo voice của xưởng video. Với giọng cá nhân, chọn tên hồ sơ trong **Giọng đọc** hoặc chọn **Sử dụng giọng** trong **Thư viện giọng** rồi kiểm tra dòng đang chọn.

Để thử các từ dễ cần đối chiếu, bấm **Đo tốc độ và thử 6 từ Hmong**. Tool tạo một bản thu thử riêng chứa `ua`, `thaj`, `qab`, `faib`, `rov`, `ris`; lời bạn đang soạn được giữ. Nghe cả Nam lẫn Nữ. Phép đo mẫu ngắn không chứng minh tốc độ khi tạo cả sách.

Muốn kiểm tra nhanh **chính giọng đang chọn**, bấm **?** → **Tạo thử giọng đang chọn**. Tool gửi một câu ngắn để tạo WAV thật, chuyển về khung kết quả và **giữ nguyên bản nháp bạn đang soạn**. Chờ hoàn tất rồi nghe/tải WAV; thử Nam, đổi sang Nữ rồi thử lại nếu muốn so sánh. Nút này cần model sẵn sàng. Hai WAV của lệnh `--test-voice` ở phần 2 là phép thử riêng, không thay cho việc kiểm tra hồ sơ cá nhân đang chọn.

## 4. Nhập và xuất TXT, SRT, WAV, MP3

**TXT** là lời đọc liên tục. **SRT** có mốc bắt đầu/kết thúc cho từng câu. **WAV/MP3** là âm thanh. **JSON dự án** lưu thêm phân vai và thiết lập phụ đề; xem phần dự án.

### Nhập văn bản

1. Chuẩn bị tệp `.txt` hoặc `.srt`, nên lưu mã hóa **UTF-8** để giữ chữ và dấu chính xác. Trong Notepad, dùng **Save as / Lưu thành**, chọn mã hóa UTF-8 và kiểm tra tên tệp không thành `ten-bai.srt.txt`.
2. Ở **Văn bản thành giọng nói**, bấm **Nhập TXT / SRT** cạnh khung nội dung, chọn tệp rồi kiểm tra **Định dạng lời** và nội dung đã nạp. Bạn cũng có thể dán văn bản trực tiếp.
3. Với TXT, tùy chọn **Không đọc mốc phút–giây ở đầu dòng** dùng khi bản chép lời có tiền tố thời gian. Với SRT cần bám thời gian, chọn đúng định dạng **SRT**, không dán như TXT rồi mong mốc tự căn.
4. Kiểm tra bộ đếm ký tự trước khi tạo. TXT Hmong tối đa 1.000.000 ký tự; video và SRT có giới hạn riêng bên dưới.

### Xuất đúng loại tệp

| Bạn muốn lấy gì? | Thao tác |
| --- | --- |
| Lời đang chỉnh sửa | Bấm **Xuất TXT** hoặc **Xuất SRT** cạnh khung kịch bản. |
| WAV hoặc MP3 đã tạo | Chọn định dạng trước khi tạo, sau đó tải từ kết quả hoặc **Lịch sử bản thu**. |
| SRT theo lời TXT đã được đọc | Tạo xong bản thu từ đúng nội dung, giữ nguyên nội dung rồi bấm **Xuất SRT**. Tool cần thời gian thực của bản thu, nên chưa tạo xong sẽ chưa có SRT đúng mốc. |
| Lời/phụ đề trong xưởng video | Dùng **Xuất lời TXT đã sửa**, **Xuất TXT có phút + lời** hoặc **Xuất phụ đề SRT đã sửa**. |
| Lời thực sự của voice trong xưởng video | Trong **Xuất riêng voice / lời đọc**, chọn TXT hoặc SRT rồi bấm **Xuất tệp đã chọn**. |
| Sách đã chia nhiều phần | Tải **ZIP**; audio, TXT và SRT của từng phần nằm trong đó. |

SRT từ TXT bám các đoạn đọc đã tạo, không phải căn âm thanh chính xác từng từ. Nếu đã sửa lời sau khi tạo, phải tạo bản mới để xuất SRT khớp lời mới. Bản xuất lời đã đọc loại thẻ điều khiển; bản kịch bản hoặc dự án để chỉnh sửa có thể giữ thẻ. Luôn mở kiểm tra tệp trước khi dùng làm phụ đề trên màn hình.

## 5. Viết Hmong RPA để tool đọc

Giữ đúng chính tả Hmong RPA và **các chữ cuối ghi thanh điệu**, chẳng hạn `b`, `j`, `v`, `s`, `g`, `m`, `d`. Chúng là thành phần của từ, không phải ký tự thừa. Không tự bỏ đuôi chữ, không đổi sang cách viết mô phỏng tiếng Việt và không để AI sửa chúng theo chính tả tiếng Anh.

1. Viết câu rõ ràng, có dấu cách đúng giữa các âm tiết và dấu câu hợp lý. Ví dụ: `Peb ua hauj lwm. Thaj chaw no zoo nkauj.`
2. Nếu tool báo **Ký tự chưa hỗ trợ** hoặc **Mô hình không có các ký tự**, tìm đúng ký tự được chỉ ra. Đổi số, ký hiệu, chữ viết tắt hoặc từ mượn thành cách nói bằng chữ Hmong mà bạn muốn nghe. Tool không tự đoán cách đọc mọi con số hay tên riêng.
3. Với số như `2026` hoặc ký hiệu `%`, viết thành lời Hmong tương ứng theo nội dung và nhờ người biết Hmong kiểm tra. Không dùng công cụ “xóa ký tự lạ” hàng loạt vì có thể làm đổi nghĩa.
4. Dùng dấu câu đơn giản như dấu chấm, phẩy, hỏi; bỏ emoji hoặc ký tự của hệ chữ khác nếu mô hình báo không hỗ trợ. Dấu nháy cong, gạch dài và dấu ba chấm thông dụng có thể được chuẩn hóa để xử lý.
5. Nếu báo **một từ hoặc cụm không có dấu cách vượt giới hạn**, kiểm tra đoạn bị dính chữ. Thêm dấu cách đúng chỗ giữa các âm tiết; không chẻ ngẫu nhiên một từ và không tách chữ ghi thanh điệu.

Bộ nhanh giữ chữ RPA, chuyển gạch nối thành ranh giới từ khi tạo tiếng và giữ cách viết gốc trong kịch bản. Việc đầu vào được giữ đúng **không chứng minh mọi từ sẽ được đọc đúng**. Hãy nghe các tên riêng, từ hiếm, thanh điệu và câu dài.

## 6. Nhịp đọc, nhấn cụm, khoảng nghỉ và sắc thái

**Nhịp đọc** điều chỉnh cách đọc chung. **Sắc thái** có sáu lựa chọn dưới đây; thanh **Mức độ sắc thái** tăng/giảm mức tác động. Đây là điều chỉnh nhịp, cường độ và khoảng nghỉ, chưa phải mô hình diễn xuất cảm xúc như người thật. Tool không đổi cao độ tùy ý để tránh làm sai thanh điệu Hmong.

| Nút / lựa chọn | Thẻ tương ứng | Cách dùng tham khảo |
| --- | --- | --- |
| Tự nhiên | `[emotion=neutral]` | Bản thử để nghe phát âm và nhịp cơ bản. |
| Ấm áp | `[emotion=warm]` | Chào hỏi, kể chuyện gần gũi. |
| Tươi vui | `[emotion=joyful]` | Lời chào vui, đoạn có không khí sáng. |
| Trầm lắng | `[emotion=sad]` | Đoạn chậm, suy tư. |
| Nghiêm túc | `[emotion=serious]` | Thông báo hoặc thuyết minh trang trọng. |
| Hồi hộp | `[emotion=suspense]` | Đoạn truyện cần nhịp ngắt rõ hơn. |

### Đặt sắc thái cho cả bài hoặc một câu

1. Muốn cả bài dùng một sắc thái: chọn ở danh sách **Sắc thái**, chọn mức độ rồi tạo lại.
2. Muốn riêng một câu trong TXT: bôi đen **cả câu hoặc cả cụm**, rồi bấm nút **Ấm áp**, **Tươi vui**… ngay dưới khung nội dung. Tool chèn thẻ trước phần chọn và thẻ trở về sắc thái chung phía sau.
3. Nếu chỉ đặt con trỏ rồi bấm nút, sắc thái áp dụng từ vị trí đó đến thẻ tiếp theo. Muốn trở lại trung tính, chèn `[emotion=neutral]`.
4. Dùng `**cụm từ**` để nhấn; đặt dấu sao bên ngoài cả từ/cụm. Nhấn tác động vào cụm đọc chứa phần đánh dấu, không phải tách riêng đúng một từ trong âm thanh. Ví dụ đúng: `**Ua tsaug rau koj.**`; không đặt `**` giữa các chữ của một từ RPA.
5. Dùng `[pause=0.5]` để nghỉ nửa giây. Viết dấu chấm thập phân; thời gian được hỗ trợ từ 0 đến 10 giây. Trong SRT, khoảng nghỉ vẫn phải nằm trong thời gian của cue.

### Ví dụ TXT có đổi sắc thái

Sao chép cả khối vào chế độ TXT. Các thẻ điều khiển không được đọc thành lời:

```text
[emotion=warm] Nyob zoo, kuv zoo siab tau ntsib nej.
[pause=0.5]
[emotion=joyful] **Hnub no peb yuav mloog ib zaj dab neeg.**
[pause=0.4]
[emotion=suspense] Hnub ntawd muaj dab tsi tshwm sim?
[pause=0.6]
[emotion=serious] Peb yuav tsum ua tib zoo mloog.
[emotion=warm] Ua tsaug rau nej mloog.
```

Trong TXT, sắc thái duy trì sang các dòng/đoạn sau đến khi gặp thẻ mới. Trong SRT, **mỗi cue bắt đầu lại từ sắc thái chung trên giao diện**. Muốn riêng một cue có sắc thái khác, đặt thẻ trong cue đó. Bản SRT giữ thẻ để chỉnh sửa có thể hiển thị thẻ khi dùng làm phụ đề trực tiếp; với bản thử video đầu tiên, dùng lời SRT sạch như ví dụ phần 9 và chọn sắc thái chung trên giao diện.

**Tự chia nhịp kể chuyện cho TXT** thêm ranh giới/nghỉ theo câu, có thể làm tạo lâu hơn. Mặc định tắt để gom câu và ưu tiên tốc độ. Nếu bật, bắt đầu với mức nghỉ nhỏ rồi nghe thử. Muốn nghỉ đúng vị trí, dùng `[pause=…]`; đừng chèn quá nhiều thẻ vào giữa từng âm tiết.

## 7. Nhân bản giọng từ mẫu 3–8 giây

Hồ sơ giọng lưu **mẫu tham chiếu** để tool dùng khi đọc nội dung mới. Lưu hồ sơ không phải huấn luyện một mô hình mới. Bộ chính tạo lời Hmong trước rồi chuyển chất giọng; độ giống người nói, phát âm và cảm xúc vẫn cần nghe đánh giá, không có bảo đảm giống 100%.

### Chuẩn bị mẫu

1. Dùng giọng của bạn hoặc giọng đã được chủ giọng cho phép sử dụng. Chọn đoạn **một người nói**, rõ tiếng, không nhạc, không vọng mạnh, không có người nói chồng lên nhau.
2. Tệp tải lên dài **3–30 giây**, tối đa **20 MB**; hỗ trợ WAV, MP3, M4A, FLAC, OGG, WEBM. Nếu bản gốc dài hơn, dùng phần mềm cắt audio để lấy một tệp trong giới hạn này trước.
3. Trong tệp đó, chọn đoạn nói rõ dài **3–8 giây**. Tránh chọn phần đầu chỉ có im lặng, tiếng thở hoặc đoạn bị cắt giữa từ.
4. Chuẩn bị **đúng lời Hmong đã nói trong chính đoạn được chọn**. Không điền lời cả tệp dài, bản dịch tiếng Việt hoặc câu bạn muốn tool tạo sau này.

### Lưu và thử giọng

1. Mở **Nhân bản giọng nói**, nhập **Tên giọng**, ví dụ `Maiv · kể chuyện`, chọn ngôn ngữ Hmong Trắng.
2. Bấm **Chọn mẫu âm thanh của bạn**, chọn tệp và đợi tool kiểm tra. Thanh trạng thái phải chuyển khỏi trạng thái đang xử lý.
3. Điền **Bắt đầu đoạn mẫu (giây)** và **Kết thúc đoạn mẫu (giây)**. Ví dụ, bắt đầu `1.2`, kết thúc `6.2` là đoạn dài 5 giây. Hai mốc phải nằm trong tệp và chênh nhau từ 3 đến 8 giây.
4. Bấm **Nghe đúng đoạn mẫu đã chọn**. Nghe lại từ đầu đến cuối đúng đoạn này; nếu mất đầu/cuối từ, sửa mốc rồi nghe lại.
5. Ở **Kiểm tra / sửa lời Hmong cho khớp đoạn mẫu 3–8 giây (bắt buộc)**, gõ đúng từng từ vừa nghe, giữ đủ chữ thanh điệu. Khi thay mốc, phải kiểm tra và sửa lời tương ứng. Tool không tự nhận dạng lời Hmong của mẫu khác.
6. Tích ô xác nhận quyền sử dụng giọng.
7. Bấm **Lưu và tạo thử giọng Hmong** để vừa lưu vừa tạo câu thử mới. Tool chuyển về tab tạo giọng, chọn giọng vừa lưu và tạo câu `Nyob zoo. Ua tsaug rau koj mloog.`. Theo dõi tiến độ, nghe và tải WAV/MP3 khi xong.
8. Nếu chỉ muốn lưu để dùng sau, bấm **Lưu hồ sơ giọng**. Sau đó nhập lời mới và bấm **Tạo giọng nói**; chỉ lưu hồ sơ sẽ chưa có một bản audio mới.

Ví dụ tự thu: đọc câu `Nyob zoo, kuv zoo siab tau ntsib koj.` rõ ràng, tự nhiên. Chỉ dùng câu đó làm lời tham chiếu nếu bạn nghe thấy đúng câu ấy trong đoạn 3–8 giây đã chọn. Nếu đoạn chỉ chứa `kuv zoo siab tau ntsib koj`, lời tham chiếu cũng phải bắt đầu bằng `kuv`, không chép thêm `Nyob zoo`.

Với **đúng hai MP3 gốc đi kèm**, tool nhận diện tệp bằng SHA-256, chọn đoạn **0–4,7 giây** và điền lời Hmong đã được cung cấp/xác nhận cho đoạn đó. Bạn vẫn phải nghe và có thể sửa. Tệp đã cắt, đổi mã hóa hoặc chỉ trùng tên sẽ không nhất thiết được nhận diện; khi ấy chọn đoạn và gõ lời thủ công.

Nếu giọng nghe kém giống, thử mẫu khác rõ lời hơn và kiểm tra lại sự khớp giữa lời/mốc trước khi đổi nhiều thiết lập. Không xóa hồ sơ đang được tác vụ dở dùng nếu bạn muốn tiếp tục tác vụ đó.

## 8. Đọc sách dài đến một triệu ký tự

Chế độ sách dài áp dụng cho **TXT Hmong không ghép video**. Tối đa **1.000.000 ký tự** cho kịch bản gốc. Khi nội dung **trên 20.000 ký tự**, tool tự lập nhiều phần khoảng **10.000 ký tự lời đọc mỗi phần**, tách ở ranh giới đoạn đã lập kế hoạch để giữ thứ tự và thẻ sắc thái/khoảng nghỉ.

1. Chia sách thành đoạn văn rõ ràng trong tệp TXT UTF-8; rà chính tả, số và tên riêng. Giữ một bản gốc bên ngoài tool.
2. Lấy một đoạn đại diện ngắn của sách để thử Nam/Nữ hoặc giọng cá nhân. Nghe phát âm, tốc độ, nhịp nghỉ; chốt giọng và thiết lập trước khi chạy cả sách.
3. Mở **Văn bản thành giọng nói** → chọn **TXT · đọc liên tục** → **Nhập TXT / SRT** → chọn tệp TXT. Kiểm tra không vượt 1.000.000 ký tự.
4. Chọn giọng và định dạng từng phần: WAV để chỉnh sửa âm thanh, MP3 để tệp nhẹ hơn. Sau đó bấm **Tạo giọng nói** một lần.
5. Giữ cửa sổ tool mở, máy có nguồn điện ổn định và đủ dung lượng. Nếu máy vào Sleep, việc xử lý có thể bị gián đoạn; lưu các công việc khác rồi điều chỉnh thời gian ngủ của máy nếu cần.
6. Khi hoàn tất, dùng **Chọn phần để nghe** để nghe từng phần. Bấm **Tải ZIP · … phần WAV/MP3** để tải toàn bộ kết quả.
7. Giải nén ZIP kết quả. Bên trong có audio, TXT và SRT riêng cho từng phần, kịch bản gốc và manifest mô tả thứ tự. Mốc SRT của từng phần ứng với audio của phần đó; dùng tên/thứ tự phần khi nhập vào phần mềm dựng.

Đây là **nhiều phần**, không phải một WAV duy nhất hoặc một video tự nối. Tổng sách có thể vượt ba giờ nhờ chia phần; mỗi phần vẫn phải nằm trong giới hạn âm thanh ba giờ. SRT phân vai và video không sử dụng cách chia sách TXT này. Muốn nghe nhiều giọng theo nhân vật, dùng SRT theo phần 9 và chia dự án phù hợp giới hạn.

Giới hạn một triệu ký tự là giới hạn nhập, không phải cam kết máy đọc xong trong vài phút. Nếu cần dừng, làm theo phần 12; các phần/đoạn đã xong được giữ để tiếp tục trong cùng tác vụ. Đừng bấm **Xóa bản thu** khi chưa dùng xong các đoạn đó.

## 9. Tạo voice theo SRT và phân giọng nhân vật

SRT gồm số thứ tự, dòng thời gian, lời thoại và dòng trống ngăn câu. Cue là một ô phụ đề có thời điểm bắt đầu/kết thúc. Mốc phải tăng dần, không chồng nhau, có lời và kết thúc trong ba giờ. Tối đa **10.000 cue**. Trong dự án video còn giới hạn **200.000 ký tự tổng** và **4.000 ký tự mỗi cue**.

### Ví dụ SRT hai nhân vật

Lưu khối sau thành `hoi-thoai-hmong.srt` với UTF-8. Đây là ví dụ lời sạch để dùng cả âm thanh lẫn phụ đề. Cần video dài ít nhất **20 giây** nếu nhập vào xưởng video. Thời gian là ví dụ; nếu giọng của bạn đọc chưa vừa cue, sửa lời hoặc tăng khoảng thời gian theo hướng dẫn bên dưới.

```srt
1
00:00:00,000 --> 00:00:05,000
Nyob zoo, Maiv.

2
00:00:05,000 --> 00:00:10,000
Nyob zoo. Kuv zoo siab tau ntsib koj.

3
00:00:10,000 --> 00:00:15,000
Hnub no koj puas nyob zoo?

4
00:00:15,000 --> 00:00:20,000
Kuv nyob zoo. Ua tsaug rau koj.
```

### Một giọng đọc cả SRT, không cần video

1. Trong **Văn bản thành giọng nói**, nhập tệp SRT hoặc dán cả khối và chọn **SRT · theo mốc từng câu**.
2. Chọn giọng Nam/Nữ/cá nhân, chọn sắc thái chung và định dạng audio.
3. Bấm **Tạo giọng nói**, nghe lại và tải kết quả. Đây là cách tạo SRT một giọng; việc gán nhân vật nằm trong trình sửa phụ đề của xưởng video.

### Gán Nam và Nữ cho từng câu

1. Mở **Lồng tiếng video**. Ở mục **1. Chọn video**, chọn video trong **Video đã tải trên máy** hoặc chọn tệp rồi bấm **Tải video vào studio**.
2. Ở mục **2. Ngôn ngữ và giọng đọc**, chọn Hmong Trắng và giọng dẫn chuyện mặc định. Chọn sắc thái chung **Ấm áp**, mức độ vừa phải cho bản thử đầu tiên.
3. Kéo xuống **Sửa phút–giây và lời ngay trên video** → **Nhân vật và giọng lồng tiếng** → bấm **Nhập SRT / dự án JSON** → chọn `hoi-thoai-hmong.srt`.
4. Bấm **+ Thêm nhân vật**. Sửa **Tên nhân vật** thành `Nraug`, chọn **Giọng riêng** là Hmong Nam.
5. Bấm **+ Thêm nhân vật** lần nữa. Đặt tên `Maiv`, chọn **Giọng riêng** là Hmong Nữ. Bạn có thể chọn một hồ sơ Hmong cá nhân đã lưu thay cho giọng mặc định.
6. Trong ô **Nhân vật** của câu 1 và 3, chọn `Nraug`; câu 2 và 4 chọn `Maiv`. Cue để **Dẫn chuyện · giọng đang chọn** sẽ dùng giọng mặc định ở mục 2.
7. Bấm **Lưu phụ đề đã sửa**, chờ thông báo đã lưu số câu và nhân vật. Bấm **Xuất dự án JSON** để có bản sao phân vai ngoài tool.
8. Bấm **Tạo voice riêng theo phụ đề**. Khi xong, nghe cùng video và mở **Kiểm tra voice khớp từng câu** để xem căn thời gian. Muốn chỉ lấy audio, chọn MP3/WAV tại **Xuất riêng voice / lời đọc** rồi **Xuất tệp đã chọn**.

Tối đa **32 nhân vật** trong một dự án. **Tên nhân vật không được đọc thành lời** vì được lưu riêng; đừng thêm `Nraug:` hoặc `Maiv:` vào nội dung nếu bạn không muốn giọng đọc cả tên. Một tệp SRT thông thường không mang theo phân vai; **JSON dự án** mới lưu ánh xạ nhân vật–giọng và gán từng cue.

Muốn cue riêng có sắc thái khác khi tạo audio, có thể viết `[emotion=joyful] Nyob zoo.` trong cue ấy. Mỗi cue sẽ tự trở về sắc thái chung khi bắt đầu cue tiếp theo. `[pause=…]` và nhấn cụm cũng dùng được nhưng chiếm thời gian trong cue. Bản SRT/JSON chỉnh sửa giữ các thẻ; nếu cần chữ sạch trên video, kiểm tra bản phụ đề sẽ xuất và dùng SRT lời đã đọc đã bỏ thẻ. Ví dụ trên dùng sắc thái chung để bạn bắt đầu mà không cần thẻ trong phụ đề.

### Khi lời không vừa thời gian

1. Mở **Kiểm tra voice khớp từng câu**, xem cue báo lỗi và bấm vào cue để đến đúng mốc.
2. Ưu tiên rút gọn lời, tăng thời gian cue nếu video có khoảng trống, hoặc chia một cue dài thành hai cue không chồng nhau. Trong trình sửa, mốc `01:30.500` nghĩa là 1 phút 30,5 giây.
3. **Khớp voice với phụ đề** có hai cách: **Giữ nguyên mốc phụ đề · đọc đúng từng câu** hoặc **Cho phép nới kết thúc vào khoảng trống**. Cách thứ hai chỉ có thể dùng khoảng trống sau cue, không lấn vào cue kế tiếp hoặc vượt video.
4. **Giới hạn căn tốc độ từng câu** có các mức 1,25×, 1,5× hoặc 2×. Tăng mức có thể làm lời đọc quá nhanh; nghe trước khi chọn. Các công cụ SRT nâng cao cũ có giới hạn riêng khoảng 1,5×, nên không dùng chúng thay cho thiết lập của xưởng phụ đề.
5. Sau khi sửa, bấm **Lưu phụ đề đã sửa**, rồi **Tạo lại voice sau khi sửa**. Bản voice cũ không tự đổi theo câu vừa sửa. Tool báo quá dài để bạn sửa, không tự cắt mất từ cho vừa.

## 10. Lồng tiếng và xuất video

Video đầu vào tối đa **2 GB và ba giờ**. Phụ đề video tối đa **200.000 ký tự**, 10.000 câu, 4.000 ký tự/câu; mốc nằm trong video, không chồng nhau. Sách TXT một triệu ký tự phải tạo riêng, không đưa toàn bộ vào một video nếu vượt các giới hạn này.

1. Trong **Lồng tiếng video**, chọn/tải video. Nếu trình duyệt không phát được codec, ưu tiên chuyển bản gốc sang **MP4 H.264** rồi tải lại.
2. Nhập SRT bằng **Nhập SRT / dự án JSON**, hoặc đến mốc trong video rồi bấm **Thêm câu tại thời điểm đang xem**, sửa lời và thời gian từng câu. Bản này **chưa có nhận dạng lời Hmong từ video**, nên cần SRT hoặc lời nhập thủ công. Phụ đề chỉ nằm sẵn trong hình ảnh cũng không được tự lấy ra thành văn bản Hmong.
3. Chọn Hmong Trắng và giọng, gán nhân vật nếu cần. Chọn **Ngôn ngữ của lời đang sửa** là Hmong khi lời đã là Hmong. Không bật dịch nếu chỉ muốn đọc nguyên lời đã nhập.
4. Bấm **Lưu phụ đề đã sửa**. Chọn phông, cỡ, màu, viền, nền và vị trí trong **Màu, phông và kiểu phụ đề**.
5. Bấm **Tạo voice riêng theo phụ đề**, chờ xong. Bật **Nghe voice đã tạo cùng video** rồi xem các mốc quan trọng. Có thể dùng **Xem thử bằng voice đã tạo · 10 giây** tại vị trí đang xem để kiểm tra trước khi xuất dài.
6. Nếu sửa lời, mốc, giọng hoặc nhịp, bấm **Tạo lại voice sau khi sửa** trước khi xuất. Thay đổi trong trình sửa làm bản voice hiện tại không còn khớp.
7. Tại **4. Xuất kết quả**, chọn độ phân giải và chất lượng. Bắt đầu với độ phân giải gốc hoặc 1080p và **Cân bằng**; chọn 4K không phục hồi chi tiết từ video nhỏ và có thể tốn thêm thời gian/dung lượng.
8. Bấm **Xuất video + phụ đề + voice đã tạo** để lấy video có cả lời mới và phụ đề. Chờ hoàn tất rồi bấm **Tải video MP4**.

Phân biệt các nút xuất: **Xuất video có phụ đề đã sửa** gắn chữ và giữ âm thanh gốc; **Xuất video MP4 · không gắn phụ đề mới** không thêm các phụ đề bạn đang sửa. Muốn thay lời bằng voice mới, dùng đúng nút **Xuất video + phụ đề + voice đã tạo**.

Trong phần nâng cao, **Giữ âm thanh gốc ở 15% âm lượng** có thể vẫn để lọt lời người nói cũ. Tắt nếu bạn muốn nghe riêng lời mới. Tool chưa tự khớp khẩu hình. Nếu muốn che logo, khoanh vùng trên video và xem thử 10 giây; nội suy vùng logo không khôi phục được chi tiết bị che và logo chuyển động có thể cần cách xử lý khác.

Tác vụ xuất video/dịch bị gián đoạn có thể phải chạy lại; khả năng **Tiếp tục** trong lịch sử áp dụng cho tác vụ tạo giọng có các đoạn đã lưu, không phải mọi bước mã hóa video.

## 11. Lưu và mở lại dự án

**Bản thu** và **dự án phụ đề** là hai loại dữ liệu khác nhau. Lịch sử bản thu lưu công việc tạo audio. Dự án phụ đề lưu lời, mốc, nhân vật, giọng gán và kiểu chữ gắn với video đã tải.

1. Sau mỗi đợt sửa lời/mốc/phân vai, bấm **Lưu phụ đề đã sửa**. Chờ dòng **Đã lưu … câu và … nhân vật trên máy**; đừng chỉ đóng tab khi còn thông báo chưa lưu.
2. Bấm **Xuất dự án JSON** để tải bản dự án ra một thư mục riêng. Đặt tên dễ nhớ, ví dụ `truyen-01-phan-vai.json`, và lưu thêm SRT/TXT nếu cần trao đổi với phần mềm khác.
3. Lần mở sau, chọn đúng video ở **Video đã tải trên máy**. Tool mở lại phụ đề và nhân vật đã lưu cho video ấy. Lời mới chưa gửi tạo giọng trong khung TXT nên được xuất TXT trước khi đóng; không coi khung nháp là bản sao lưu.
4. Muốn nhập JSON, chọn video phù hợp trước rồi bấm **Nhập SRT / dự án JSON** và chọn tệp. Video phải đủ dài cho các mốc trong dự án.
5. Nếu nhập trên máy khác, cần có video và các hồ sơ giọng tương ứng. JSON lưu mã giọng, **không kèm audio mẫu, mô hình, video hoặc bản voice đã tạo**. Nếu báo giọng không còn, chọn lại **Giọng riêng** cho nhân vật rồi lưu và tạo lại.

Xuất SRT/TXT giữ lời và mốc tương ứng nhưng không đóng gói toàn bộ phân vai. Để giữ trọn công việc khi chuyển máy hoặc cập nhật, sao lưu cả `.data` theo phần 13.

## 12. Dừng, tiếp tục và tắt tool

### Dừng và tiếp tục tạo giọng

1. Bấm **Dừng tạo giọng** ở kết quả, **Dừng tạo voice riêng** trong khung voice, hoặc **Dừng** ở thẻ công việc trong **Lịch sử bản thu**.
2. Chờ trạng thái chuyển từ **Đang dừng** sang **Đã dừng**. Các đoạn hoàn tất được giữ; đoạn đang tạo có thể phải làm lại khi tiếp tục.
3. Mở **Lịch sử bản thu**, tìm đúng bài có trạng thái **Đã dừng** hoặc **Có lỗi** rồi bấm **Tiếp tục**. Tool dùng văn bản, giọng và thiết lập đã lưu của chính bài đó.
4. Nếu mất điện hoặc tắt ứng dụng giữa chừng, mở lại BAT chính rồi vào lịch sử. Công việc bị ngắt có thể hiện **Có lỗi** kèm hướng dẫn tiếp tục từ các đoạn đã tạo.
5. Nếu đã sửa kịch bản, muốn đổi giọng hoặc đổi bộ đọc, tạo **tác vụ mới**. Nút **Tiếp tục** không lấy nội dung đang sửa để thay vào bài cũ.

Muốn tiếp tục, cần giữ dữ liệu tác vụ, các đoạn tạm và đúng mẫu giọng ban đầu. Nếu hồ sơ bị xóa, mẫu/lời tham chiếu đã đổi hoặc bản cũ chưa ghi đủ danh tính mẫu, tool có thể yêu cầu tạo tác vụ mới để tránh trộn giọng. Bản thu/đoạn cũ vẫn được giữ. **Xóa bản thu** còn xóa dữ liệu của bài đó; chỉ xóa khi không cần nghe lại hay tiếp tục.

### Tắt tool

Lưu dự án và TXT nháp, dừng công việc rồi chờ trạng thái đã dừng. Chuyển sang cửa sổ dòng lệnh, bấm **Ctrl+C** và đợi tiến trình tắt. Đóng cửa sổ dòng lệnh cũng làm tool mất kết nối; đóng riêng tab trình duyệt thường không tắt máy chủ. Lần mở sau dùng tab mới do BAT mở để tránh theo dõi cổng cũ.

## 13. Sao lưu và chuyển sang bản mới

Trong **gói Windows**, dữ liệu nằm ở:

```text
thư-mục-tool\voice-studio-hmong\.data
```

Trong `.data` có mô hình, hồ sơ và mẫu giọng cá nhân, lịch sử/công việc, đoạn đã tạo, video, dự án phụ đề và các tệp xuất. Bản mã nguồn có thư mục mặc định `.data-hmong`; đó là đường dẫn khác, không phải thư mục của gói Windows đang nói ở đây.

### Sao lưu đủ dữ liệu

1. Dừng công việc, lưu dự án và **tắt tool**.
2. Mở `voice-studio-hmong`, sao chép **nguyên thư mục `.data`** sang ổ/thư mục sao lưu. Nếu không thấy, bật **View → Show → Hidden items / Hiện mục ẩn** trong File Explorer rồi kiểm tra lại.
3. Giữ thêm các TXT gốc, JSON dự án và bản audio/video quan trọng ở nơi dễ tìm. Chỉ chép thư mục `models` sẽ không giữ lịch sử và giọng cá nhân; chỉ chép JSON cũng không giữ mẫu giọng/video.

### Chuyển sang gói mới

1. Tải ZIP đầy đủ mới, giải nén vào **thư mục mới**. Đừng ghi đè bộ cũ đang chạy.
2. Đảm bảo cả bộ cũ lẫn mới đã tắt. Sao lưu `.data` cũ như trên.
3. Chép `.data` cũ vào **`voice-studio-hmong` của gói mới**, để được đúng đường dẫn `voice-studio-hmong\.data`, không lồng thành `.data\.data`.
4. Mở BAT ở ngoài cùng của gói mới. Kiểm tra **Thư viện giọng**, **Lịch sử bản thu** và một dự án video trước khi dọn bộ cũ.
5. Tạo một câu ngắn để nghe thử. Công việc cũ dùng mẫu mặc định khác có thể không tiếp tục được; giữ bản cũ/đoạn cũ và tạo tác vụ mới bằng mẫu hiện tại khi tool yêu cầu.

Không xóa toàn bộ `.data` để sửa lỗi khóa hoặc lỗi tải model. Thư mục này chứa dữ liệu cá nhân và các đoạn có thể tiếp tục.

## 14. GPU NVIDIA và bộ F5 nâng cao

Gói mặc định dùng CPU. Nếu máy có **GPU NVIDIA và driver phù hợp**, có thể đóng tool rồi chạy **`tools\install_hmong_cuda.bat`**. Bộ cài cần Internet và vài GB trống, tạo bộ chạy GPU riêng trong dữ liệu. Cài xong mở lại `MO_VOICE_STUDIO_HMONG.bat` và tạo một câu thử. Máy không có NVIDIA cứ dùng bộ CPU; không cần cài CUDA để tool hoạt động.

Bộ cài kiểm tra khả năng tính toán CUDA trước khi đánh dấu sẵn sàng. Nếu lựa chọn NVIDIA đã lưu không còn chạy được, launcher **báo rõ rồi chuyển sang CPU** để bạn tiếp tục dùng; bộ NVIDIA hợp lệ vẫn được dùng. Bạn có thể cài lại bộ NVIDIA trong `tools` khi cần. Kiểm tra CUDA thành công không chứng minh tốc độ hoặc chất lượng của một dự án dài. Không chép các tệp DLL hoặc PyTorch ngẫu nhiên vào `runtime`.

Nếu máy còn biến cấu hình F5 cũ **`HMOOB_PRECISION=int8`**, bản 1.6.2 nhận ra cấu hình này và thông báo bộ nhanh vẫn chạy **FP32**. Bạn không cần đổi chính tả Hmong hay chọn mô hình phát âm khác; đây là xử lý tương thích cấu hình, không phải đổi bộ phát âm. Bộ nhanh vẫn giữ cách xử lý chữ và thanh điệu như trước.

**F5 là lựa chọn so sánh nâng cao:** đóng phiên hiện tại rồi mở **`tools\MO_F5_HMONG.bat`**. Lần đầu cần mô hình riêng khoảng **1,4 GB**. F5 có các mức **4/8/16/32 bước**: 16 bước là mặc định, 4/8 dành cho nháp có thể kém rõ, 32 có thể chậm hơn. Bộ nhanh VITS + OpenVoice **không có các số bước này**; không tìm cách giảm bước F5 để tăng tốc bộ chính.

Khi đổi bộ đọc, đóng phiên cũ và tạo công việc mới; bấm lại một BAT khi phiên kia còn chạy có thể chỉ mở lại bộ đang chạy. Đừng tiếp tục/nối một bài đang dở bằng bộ đọc khác.

Không có cam kết **nhân bản giống 100%**, và mục tiêu **một giờ lời đọc trong hai phút (30×) chưa được xác nhận**. Tốc độ phụ thuộc phần cứng, nội dung, mẫu, nhịp và cả bước chuyển giọng/xuất tệp. Các khoảng trống SRT không phải thời gian AI tạo lời; không dùng bản có nhiều im lặng để suy ra tốc độ đọc.

## 15. AI viết và dịch tùy chọn

Bạn có thể bỏ qua toàn bộ phần AI viết/dịch nếu đã có lời Hmong. **Tạo giọng Hmong không cần ChatGPT/Gemini, API key hoặc Ollama.**

Tab **AI viết · ChatGPT / Gemini** và các nút dịch cho phép chuẩn bị lời bằng dịch vụ riêng. **Ollama** cần cài/mở Ollama và tải model viết/dịch phù hợp trên máy; không cần key nhưng cần thêm dung lượng/RAM. **ChatGPT / OpenAI API** và **Gemini API** cần API key của nhà cung cấp, có thể tính phí và gửi văn bản/lời thoại đến dịch vụ khi bạn bấm viết/dịch. Key chỉ giữ trong bộ nhớ máy chủ đến khi tắt ứng dụng, không nằm trong JSON dự án.

Nếu sử dụng, chọn nhà cung cấp/model → **Kiểm tra AI** hoặc **Kết nối / kiểm tra dịch vụ dịch** → thử một câu → đọc và sửa kết quả → **Đưa sang tạo giọng**. Kiểm tra Hmong RPA và nghĩa với người biết tiếng Hmong trước khi tạo cả bài. Chọn ngôn ngữ giọng Hmong không tự dịch văn bản tiếng Việt thành Hmong. Kết nối dịch thành công không có nghĩa model giọng đã tải, và model giọng sẵn sàng không có nghĩa dịch vụ dịch đang kết nối.

## 16. Sửa các lỗi thường gặp

### Tải ZIP gặp 403, tải ra trang HTML hoặc không mở được ZIP

1. Mở lại [trang Releases chính thức](https://github.com/seotro95/seotro/releases), bấm tên ZIP trong **Assets** để lấy yêu cầu tải mới. Địa chỉ CDN sao chép từ lần cũ có thể đã hết hạn.
2. Kiểm tra tệp tải là `.zip`, kích thước hợp lý, không phải `.html` hoặc một trang báo lỗi đổi tên. Tải lại nếu tệp chưa xong/hỏng; nếu có SHA-256 do bản phát hành cung cấp, đối chiếu với tệp đó.
3. Nếu mạng chặn GitHub/CDN, dùng mạng được phép truy cập hoặc nhờ quản trị mạng cho phép nguồn tải. Tool không tự gỡ được quy định chặn mạng.

### Tải mô hình gặp 403, lỗi mạng hoặc SHA-256 không đạt

1. Giữ lại thông báo trong cửa sổ dòng lệnh để phân biệt tải ZIP và tải model. Model được tải từ Hugging Face sau khi bạn mở tool.
2. Kiểm tra mạng đến `huggingface.co` và CDN `.huggingface.co`/`.hf.co`, ngày giờ Windows và dung lượng đĩa. Nếu mạng cơ quan chặn, thử mạng được phép hoặc nhờ quản trị cho phép đúng nguồn.
3. Đợi tối đa ba lần thử tự động trong lượt tải. Nếu vẫn thất bại, đóng cửa sổ đã báo lỗi và mở lại BAT chính khi mạng đã hoạt động. Tool dùng lại thành phần đã xác minh, giữ phần tải dở `.part` để tiếp tục khi nguồn hỗ trợ. Không xóa `.part` chỉ vì mạng vừa ngắt, và không cần xóa thư mục giọng/lịch sử.
4. Nếu sai kích thước hoặc checksum, tệp đó không được cài; phần tải dở hỏng bị loại để tải bản hợp lệ. Nếu lỗi lặp lại, giữ nguyên kiểm tra và lưu thông báo tên tệp để nhờ hỗ trợ. Cơ chế thử lại/tải tiếp **không tắt TLS hoặc SHA-256**. Không chỉnh manifest thành “ready” và không xóa cả `.data`.

### Giao diện báo chưa tải model hoặc giọng chưa sẵn sàng

1. Kiểm tra đã mở đúng BAT ngoài cùng của đúng thư mục giải nén và hoàn tất lần tải đầu.
2. Trong giao diện, chọn giọng Hmong rồi bấm **Tải model giọng đã chọn** hoặc **Tải model cho giọng đang chọn**. Giữ cửa sổ CMD mở, đợi trạng thái sẵn sàng, rồi **Cập nhật giọng** hoặc tải lại tab.
3. Nếu đang chạy bộ F5, nó cần model F5 riêng. Muốn dùng bộ chính khoảng 580 MB, đóng tool và mở lại BAT chính.
4. Có thể chạy `tools\KIEM_TRA_HMONG.bat` sau khi đã tải để kiểm tra. Nó không thay cho bước tải đầu. Hai giọng Nam/Nữ dùng chung bộ mô hình, không phải mỗi giọng tải riêng 580 MB.

### “Voice Studio đã chạy với thư mục dữ liệu này”, lỗi khóa hoặc quyền ghi

1. Nếu phiên đang chạy, dùng đúng địa chỉ **Studio:** của cửa sổ đó. Mở BAT lần hai thường mở lại phiên đang có; không cần chạy thêm một bản cùng dữ liệu.
2. Nếu thấy **Một cửa sổ đang khởi động tool**, chờ cửa sổ khởi động đầu tiên hoàn tất tải/chuẩn bị; tránh bấm nhiều lần.
3. Nếu phiên cũ treo, lưu/dừng công việc nếu còn dùng được rồi tắt cửa sổ cũ bằng Ctrl+C. Khi cần, dùng Task Manager để kết thúc đúng tiến trình của **bộ tool đó**, không kết thúc mọi tiến trình Python đang chạy trên máy. Mở lại sau khi phiên cũ đã tắt; khởi động lại Windows nếu không xác định được phiên còn giữ khóa.
4. Với lỗi **Không mở/khóa được thư mục dữ liệu** hoặc ổ mạng không hỗ trợ khóa, tắt tool, chép **toàn bộ thư mục tool** sang ổ cục bộ có quyền ghi, ví dụ Documents hoặc ổ D:, rồi mở BAT ở chỗ mới. Kiểm tra thư mục không bị đặt chỉ đọc hoặc bị phần mềm bảo vệ chặn ghi; chỉ điều chỉnh quyền cho thư mục tin cậy khi chính sách máy cho phép.
5. Tệp `server.lock` còn lại sau một lần tắt không tự chứng minh tool đang chạy. **Không xóa `.data`, giọng cá nhân hay lịch sử để “mở khóa”.**

### Trình duyệt không kết nối hoặc báo mất kết nối

Kiểm tra cửa sổ CMD còn mở và không có lỗi. Dùng đúng địa chỉ sau chữ **Studio:**, thường trong dải cổng 8770–8789, và mở tab mới từ BAT. Tắt tab cũ đang trỏ đến cổng khác. Nếu tất cả các cổng trong dải đều bận, đóng các phiên Voice Studio cũ rồi mở lại. Không mở trang `index.html` bằng cách bấm đúp từ thư mục.

### Không nghe thấy tiếng

1. Chờ **Hoàn tất**; trạng thái đang tạo chưa phải bản audio có thể phát đủ.
2. Kiểm tra nút phát, âm lượng của trình phát, âm lượng Windows, tab bị tắt tiếng và thiết bị đầu ra Bluetooth/tai nghe/loa.
3. **Tải WAV/MP3 xuống** và mở bằng một trình phát trên Windows. Nếu tệp tải phát được, kiểm tra/trở lại Edge hoặc Chrome; đây có thể là lỗi phát của trình duyệt.
4. Nếu audio chỉ yên lặng, kiểm tra mẫu tham chiếu có tiếng nói rõ trong chính đoạn 3–8 giây đang chọn, lời mẫu đúng và nội dung không chỉ có `[pause=…]`.
5. Tạo lại một câu ngắn bằng giọng Nam hoặc Nữ mặc định. Nếu cả hai vẫn không có tiếng, giữ thông báo lỗi và tệp kết quả để hỗ trợ kiểm tra; đừng tạo ngay lại cả cuốn sách.

### SRT báo mốc sai, chồng nhau hoặc câu quá dài

Mốc tệp phải có dạng `00:00:05,000 --> 00:00:10,000`, sau đó có lời và một dòng trống trước cue kế tiếp. Mốc kết thúc phải lớn hơn bắt đầu; cue sau bắt đầu từ lúc cue trước kết thúc hoặc muộn hơn, không vượt video/ba giờ. Bấm **Sắp xếp theo mốc** nếu thứ tự sai rồi sửa các chỗ chồng nhau; sắp xếp không tự chữa chồng mốc. Lời không vừa thì rút gọn, nới thời gian vào khoảng trống, tách cue hoặc chọn giới hạn căn tốc độ phù hợp như phần 9. Giảm khoảng nghỉ trong cue nếu bạn đã chèn nhiều thẻ pause.

### Báo RPA/ký tự chưa hỗ trợ, số hoặc từ dính quá dài

Tìm đúng ký tự/cụm mà thông báo chỉ ra; viết số và chữ viết tắt thành lời Hmong, bỏ/đổi ký hiệu không thuộc từ vựng mô hình, sửa dấu cách đúng giữa các âm tiết. Giữ các chữ đuôi thanh điệu. Nếu từ nghe sai dù không báo lỗi, thử câu ngắn để đối chiếu và sửa nội dung bằng người biết Hmong; mô hình vẫn có thể đọc sai đầu vào hợp lệ.

### Bấm lưu giọng nhưng chưa có audio, hoặc không thấy giọng

**Lưu hồ sơ giọng** chỉ lưu mẫu. Chọn hồ sơ đó rồi nhập lời và **Tạo giọng nói**, hoặc dùng **Lưu và tạo thử giọng Hmong**. Nếu danh sách trống, chọn **Tất cả nguồn / Tất cả giọng**, bấm **Cập nhật giọng** và kiểm tra lại tên đang chọn. Với mẫu mới, đợi kiểm tra tệp xong và điền đủ lời khớp đoạn trước khi lưu.

### Thiếu runtime, FFmpeg, bundle_check hoặc thư viện

Bạn có thể đang mở mã nguồn, giải nén thiếu hoặc kéo BAT ra ngoài bộ tool. Tải lại ZIP **Windows-x64 đầy đủ**, giải nén **toàn bộ** vào thư mục mới, kiểm tra các thư mục ngoài cùng như phần 1 rồi mở BAT chính. Không sửa bằng cách tải thêm từng `.py` hoặc cài Python bất kỳ. Sao lưu dữ liệu trước khi thay bộ. Nếu phần mềm bảo vệ máy đã cách ly tệp, xem lịch sử bảo vệ và kiểm tra nguồn phát hành; không tắt bảo vệ toàn máy để thử.

Với lỗi DLL, thư viện hoặc phép tính âm thanh, chạy **`MO_VOICE_STUDIO_HMONG.bat --probe-runtime`** để thử bộ chạy mà không cần tải model. Xem thông báo và **`voice-studio-hmong\.data\diagnostics\runtime-check.json`**. Khi phép thử này qua, dùng **`--check`** để kiểm tra model hoặc **`--test-voice`** để xác nhận tạo được cả Nam và Nữ. Nếu tool báo cấu hình NVIDIA cũ bị lỗi rồi đã chuyển CPU, có thể thử giọng bằng CPU trước; không cần thay model Hmong.

Nếu thông báo DLL yêu cầu **Microsoft Visual C++ 2015–2022 x64**, cài bộ x64 chính thức theo [hướng dẫn Microsoft Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist), rồi mở lại tool và chạy phép thử bộ chạy. Không tải riêng DLL từ các trang chia sẻ tệp. Nếu báo thiếu RAM/VRAM, đóng ứng dụng nặng, dùng CPU hoặc giảm công việc đang chạy; nếu nhắc pagefile Windows, kiểm tra **Virtual memory** đang để Windows quản lý và ổ hệ thống còn đủ chỗ.

### Công việc báo lỗi tạo giọng hoặc worker dừng

Đọc phần lỗi trên kết quả hoặc thẻ **Lịch sử bản thu**. Bản 1.6.2 hiển thị hướng xử lý và dòng **Nhật ký tác vụ:** kèm đường dẫn tệp log cục bộ của chính công việc. Mở đúng tệp log đó bằng Notepad nếu cần xem thêm, hoặc lưu lại thông báo và đường dẫn để nhờ hỗ trợ. Sửa nguyên nhân được chỉ ra như thiếu RAM, thư viện/DLL, cấu hình, model hoặc dung lượng; sau đó dùng **Tiếp tục** nếu tác vụ còn các đoạn đã tạo. Đừng chỉ bấm tạo lại liên tục hay gửi toàn bộ `.data`; log có thể chứa nội dung công việc nên chỉ chia sẻ phần bạn muốn cung cấp.

### Tạo giọng chậm, phần trăm đứng lâu hoặc không tiếp tục được

Lần nạp model và câu dài có thể mất thời gian; xem trạng thái CMD và mức CPU/RAM/đĩa trong Task Manager. Dùng câu ngắn để kiểm tra, đóng ứng dụng nặng không cần thiết, giảm thẻ nghỉ tự động và giữ tốc độ/nhịp hợp lý. Nếu muốn dừng, dùng nút Dừng và chờ trạng thái, không bấm tạo lặp lại làm đầy hàng đợi. Nếu hết dung lượng, dừng trước, giải phóng các tệp không còn dùng và giữ `.data/parts` của bài cần tiếp tục. Nếu mẫu đã đổi/bị xóa hoặc tool yêu cầu danh tính mẫu mới, tạo tác vụ mới thay vì sửa hồ sơ của bài cũ.

## 17. Kiểm tra trước khi dùng bản thu

1. Nghe thử một câu và một đoạn đại diện trước khi tạo toàn bộ; kiểm tra Nam/Nữ hoặc hồ sơ đang chọn bằng dòng **Đang chọn:**.
2. Nhờ người hiểu Hmong nghe phát âm, thanh điệu, tên riêng, số, câu dài và độ giống giọng. Mẫu tham chiếu có lời đúng không có nghĩa mọi lời AI tạo đã đúng.
3. Với SRT/video, kiểm tra đoạn đầu, giữa, cuối, các chỗ đổi nhân vật và cue bị căn tốc độ; xem phụ đề có còn thẻ điều khiển hay không.
4. Tải một tệp về máy, mở bằng trình phát bên ngoài và nghe trước khi chia sẻ. Lưu TXT gốc, JSON phân vai và sao lưu `.data` khi công việc quan trọng.
5. Đây là âm thanh AI. Bộ nhanh có thử gắn dấu WavMark với đoạn đủ dài, nhưng đoạn quá ngắn có thể bỏ qua và chưa xác nhận dấu còn nhận được sau mọi kiểu xử lý/xuất. Không coi mọi tệp đều đã có dấu chắc chắn.

Nguồn và giấy phép mô hình được ghi trong `MODEL-SOURCES.json` của gói và [tài liệu bộ Hmong nhanh trực tuyến](https://github.com/seotro95/seotro/blob/release/voice-studio-hmong-1.6.2/voice-studio/docs/HMONG-NATIVE.md). Trọng số được tải từ nguồn, không đóng sẵn trong ZIP. Kho trọng số Hmong chưa nêu giấy phép rõ ràng; xem điều kiện của nguồn trước khi phân phối lại hoặc dùng thương mại. Tải và kiểm tra tệp thành công không xác nhận quyền sử dụng hay phát âm chuẩn.

Khi cần nhờ hỗ trợ, gửi số phiên bản đang hiện, tên BAT đã mở, nội dung lỗi trong CMD, giọng/bộ đọc đã chọn và một câu ngắn tái hiện. Với lỗi tải, cho biết đó là tải ZIP hay model. Chỉ gửi mẫu giọng hoặc nội dung riêng tư khi bạn chủ động muốn chia sẻ chúng.
