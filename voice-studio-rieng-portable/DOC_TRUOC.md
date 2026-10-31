# Voice Studio Riêng 1.12.1 · Windows 10/11 x64 Portable

## Máy hai Xeon 28 nhân / 56 luồng, RAM 128 GB, GTX 1060 6 GB

CUDA vẫn dùng một mô hình Q8 để giữ bộ nhớ GPU. Khi chọn CPU, bản 1.12.1 cho
phép các tiến trình native độc lập xử lý câu/đoạn đồng thời và ghép lại đúng thứ
tự. Với 28 nhân vật lý và đủ RAM khả dụng, preset **Tốc độ tối đa** là 7 tác vụ
× 4 luồng, **Mượt khi làm việc** là 6 × 4; **Ít RAM** giữ một tác vụ, tối đa hai
luồng. Ngân sách dựa trên nhân vật lý và RAM đang khả dụng, không nhân đôi theo
56 luồng logic. Tool chừa RAM dự phòng và giới hạn số mô hình nạp đồng thời.

Cấu hình này giúp tận dụng CPU nhiều nhân, không chứng minh tốc độ tạo tiếng
trên máy người dùng. Máy kiểm tra 4 nhân đã chạy được hai tiến trình với mô hình
thật, kiểm tra đủ hai đoạn và WAV đầu ra; chưa đo mô hình GPU hoặc tạo một giờ
tiếng trên GTX 1060. Chọn giọng/ngôn ngữ, đo và nghe mẫu sau khi đổi CPU/CUDA.

## VoxCPM2 native Q8 cho mẫu giọng quốc tế

Bản 1.12 thêm bộ đọc **VoxCPM2 native Q8**, dùng cùng họ mô hình VoxCPM2 và tệp
mẫu giọng đang có, hỗ trợ 30 ngôn ngữ của mô hình. Bộ đọc này không cần runtime
PyTorch quốc tế hoặc chép/nhận dạng lời mẫu. Mô hình Q8 khoảng 2,95 GB và thư viện
CPU/CUDA được ghép vào gói Windows native đầy đủ. Lượng tử hóa có thể làm âm
thanh/phát âm khác; nghe mẫu trước khi dùng cho tài liệu dài.

Chọn giọng và đúng ngôn ngữ, chọn **VoxCPM2 native Q8**, rồi **GPU NVIDIA · CUDA**
hoặc nút dùng GPU ngay cạnh lựa chọn bộ đọc. Chế độ **Nhanh** trên CUDA bật đường
chiếu gộp được upstream hỗ trợ; có thể thay đổi kết quả số học so với Cân bằng.
Số bước VoxCPM2 vẫn là 4/8/10 và được giữ nếu người dùng đã chỉnh riêng. GPU dùng
một mô hình để tiết kiệm VRAM và giữ cache tham chiếu giữa các câu. CUDA không
khởi động được sẽ báo lỗi, giữ lựa chọn đã yêu cầu để người dùng quyết định.

Thư viện CUDA dùng CUDA 12 và có mã `sm_61` để tương thích Pascal/GTX 1060.
Được biên dịch cho một card không đồng nghĩa đã đo tốc độ trên card đó. Phép thử
CPU với mô hình Q8 tạo được PCM Pháp/Nhật, nhưng vẫn chậm hơn Turbo; không tự coi
CPU Q8 là đường chạy nhanh. Chưa có phép đo GPU/GTX 1060 hoặc tạo đủ một giờ tiếng
chứng minh mục tiêu một giờ trong hai phút. Báo cáo chỉ xác nhận mục tiêu 30× trên
một giờ khi tác vụ thực sự tạo ít nhất 3.600 giây tiếng và đạt thông lượng đó;
đoạn mẫu ngắn, ước tính hoặc khoảng im lặng SRT không đủ để xác nhận.

Gói đầy đủ giữ bộ cài 19 mẫu mã hóa của bản cũ: dùng mật khẩu đã có để mở mẫu.
Không ghi đè thư viện `runtime-native` mới bằng bộ DLL OmniVoice cũ. Khi chuyển
dữ liệu, ghép thư mục `.data`/`voice-library`, giữ mô hình Q8 mới và sao lưu trước.

## Bản cập nhật xử lý giọng mẫu 1.11.1

Chế độ **Nhanh**, **1 tác vụ** và **khoảng nghỉ 0 giây** ghép các câu TXT ngắn
thành đoạn tối đa 240 ký tự cho giọng quốc tế. Cách này giảm số lượt gọi mô hình
khi đọc liên tục; giọng đã chọn, ngôn ngữ và số bước đang chọn được giữ nguyên.
SRT, dấu nghỉ `[pause=...]`, phần nhấn mạnh, chế độ Cân bằng và tác vụ đang tiếp
tục vẫn giữ cách chia cũ. Khi chạy nhiều tác vụ song song, tool tiếp tục giữ câu
riêng để tránh giảm số tác vụ có thể chạy đồng thời.

Bộ đọc OmniVoice bổ sung cache PCM mẫu giọng có giới hạn trong RAM, không đọc và
giải mã lại cùng tệp mẫu ở từng câu. Đây là tối ưu phần chuẩn bị mẫu, không phải
cam kết tăng tốc suy luận mô hình. Giọng quốc tế VoxCPM2 trên CPU chưa được chứng
minh nhanh ngang Turbo Việt/Anh; không tự đổi giọng quốc tế sang Turbo hoặc sang
một mô hình khác. Nghe kiểm tra phát âm sau khi đổi chế độ đọc.

Phép đo minh họa trên Linux CPU, một mô hình đã nạp, cùng mẫu công khai và 8
bước, lặp với hai thứ tự chạy: thông lượng tiếng Pháp tăng khoảng 11,0%, tiếng
Nhật tăng khoảng 6,8%. Đây không phải số đo toàn bộ pipeline trên máy người
dùng. Độ dài âm thanh hai cách đọc khác nhau; chưa kiểm tra đủ lời/phát âm hoặc
độ giống giọng bằng người nghe. Báo cáo đầy đủ nằm trong
`packaging/benchmarks/international-packing-1.11.1.qa.json` của mã nguồn và
`INTERNATIONAL-PACKING-QA.json` trong ZIP cập nhật.

Bản ZIP cập nhật mã cần tool 1.10/1.11 đầy đủ đã cài trên máy; không chứa Python,
mô hình, thư viện CUDA hoặc bộ mẫu riêng. Đóng tool, sao lưu thư mục cũ rồi chép
thư mục `app` từ gói cập nhật vào cạnh `MO_TOOL.bat`. Giữ nguyên dữ liệu và mô
hình cũ. Xem `DOC_CAP_NHAT.txt` trong gói cập nhật cho hướng dẫn chi tiết.

Giải nén **toàn bộ ZIP** vào thư mục có quyền ghi, ví dụ `D:/VoiceStudio`, rồi mở **MO_TOOL.bat**. Giữ cửa sổ lệnh mở trong khi sử dụng; dùng Ctrl+C để tắt. Bản Portable đã có Python, FFmpeg, Nano và Turbo, dùng cục bộ với các giọng đi kèm.

## Bộ đọc đa ngôn ngữ mới

Với các mẫu Pháp, Nhật, Hàn, Nga, Tây Ban Nha, Thái…, có thể chọn **OmniVoice Q8 · Thử nghiệm** để dùng bộ chạy native thay cho VoxCPM trên CPU. Mẫu giọng và ngôn ngữ đã chọn được giữ; mô hình khác có thể thay đổi âm sắc và phát âm. Turbo Việt–Anh tiếp tục dùng bộ đọc hiện tại.

1. Đóng tool, chạy **TAI_GIONG_DA_NGON_NGU_NHANH.bat** một lần khi có Internet. Bộ tải kiểm tra SHA256 của OmniVoice khoảng 1,35 GB và mô hình nhận dạng mẫu khoảng 145 MB.
2. Mở lại **MO_TOOL.bat**, chọn giọng/ngôn ngữ, rồi chọn bộ đọc **OmniVoice**. Chọn **CUDA** nếu gói có bộ chạy GPU và trình điều khiển NVIDIA hỗ trợ CUDA 12. Bộ chạy CUDA có mã `sm_61` cho GTX 1060; tốc độ trên card này cần đo thực tế.
3. Bấm **Đo giọng đang chọn**, nghe mẫu và xem báo cáo. Thử 16 bước trước; 8 bước có thể nhanh hơn nhưng giảm chất lượng. Chọn CUDA mà không khởi động được sẽ báo lỗi để bạn tự chọn thiết bị khác.

OmniVoice giữ một mô hình để dùng lại giữa các câu và mẫu giọng, tránh nhân bản trọng số trong RAM/VRAM. Nếu mẫu chưa có lời chép, tool nhận dạng một lần bằng Whisper trên CPU, lưu kết quả cục bộ rồi dùng lại; lần đầu sẽ lâu hơn. Không gửi bản thu riêng lên mạng để nhận dạng. Bản chép tự động có thể có sai sót, nên cần nghe kiểm tra trước khi tạo bản dài.

Số bước cao hơn chưa bảo đảm đọc tốt hơn: mẫu thử CPU Q8 ở 32 bước đã có trường hợp chỉ phát âm kéo dài, trong khi mẫu 8 bước cùng giọng đọc được lời. Hai chế độ Cân bằng và Chất lượng của OmniVoice hiện đều khởi đầu ở 16 bước; 32 bước là lựa chọn thử riêng. Giữ VoxCPM nếu mẫu của giọng đang chọn không đọc đúng.

Kết quả thử ngắn bằng các bản thu công khai nằm trong `CPU-NATIVE-SHORT-SAMPLES.json`: mẫu Nhật 16 bước qua ứng dụng đọc đúng lời theo nhận dạng tự động và giữ chính xác mốc SRT 5 giây. Đường CPU mới vẫn chậm; báo cáo này chưa đánh giá giọng giống mẫu bằng nghe tay, tốc độ GTX 1060 hay bản thu dài một giờ.

Khi nâng cấp từ 1.10, giải nén bản đầy đủ vào thư mục mới rồi chép **app/.data**, **runtime-international** và **app/voice-library** từ bản cũ, hoặc dùng ZIP cập nhật trên một bản sao của thư mục cũ. Bộ cài 19 giọng vẫn dùng mật khẩu đã có. Đóng tool trước khi sao chép. Bản cập nhật không chứa `.data` hay thư viện mẫu của bạn.

Chưa có số đo chứng minh mọi giọng nhanh bằng Turbo hoặc tạo một giờ lời đọc trong hai phút. Các kết quả CPU dưới đây là số đo lịch sử của các bản trước. Trọng số OmniVoice dùng CC-BY-NC; bộ mã hóa âm thanh dùng giấy phép Boson riêng, khác với giấy phép mã nguồn. Chi tiết nguồn và điều khoản nằm trong `runtime-native` và thư mục mô hình sau khi cài.

## Nhập lời và khớp video

Nhập TXT/SRT UTF-8 hoặc Unicode UTF-16 của Windows, tối đa **1.000.000 ký tự**, 8 MB mỗi tệp. SRT giữ các mốc gốc; TXT có mốc phải xác định được mốc kết thúc. TXT không có mốc được đọc liên tục và xuất SRT dựa trên lời đọc thực.

Chọn **WAV** khi dựng video. Tool tự căn từng câu: câu dài đổi nhịp, câu ngắn giữ khoảng lặng. Câu bị ép quá nhanh cần nghe kiểm tra; tool báo lỗi khi không thể xử lý đầy đủ. Không tự bỏ hoặc viết lại lời. Nút **Tự căn và tiếp tục** dùng lại những mảnh đã tạo của tác vụ cũ.

Ví dụ `00:27:20,519 --> 00:27:23,671` có ô lời dài **3,152 giây**. Nếu đây là câu cuối, WAV giữ timeline từ 0 đến **27:23,671**. MP3 có thể có padding tùy phần mềm giải mã. Chi tiết TXT có mốc nằm trong `HUONG_DAN_CAN_MOC.txt`.

## Chạy nhẹ và giữ giao diện mượt

Bản 1.9 cho giọng Nano/Turbo dùng chung trọng số ONNX trong một tiến trình, mỗi tác vụ vẫn có vùng dữ liệu và khóa giải mã riêng. Nhiều câu dùng chung model thay vì nạp một bản model cho mỗi tác vụ. Giọng, số bước, lời đọc và mốc SRT giữ theo lựa chọn hiện tại. Đổi giữa các giọng cùng bộ đọc có thể dùng lại trọng số đã nạp.

Chọn cấu hình tài nguyên độc lập với chất lượng giọng:

- **Mượt khi làm việc:** ưu tiên giao diện và ứng dụng đang dùng; chừa một ít lõi trên máy nhiều lõi và hạ ưu tiên xử lý nền.
- **Tốc độ tối đa:** dùng toàn bộ ngân sách CPU/RAM cho phép. Không tăng số bước hoặc tự đổi giọng.
- **Ít RAM:** một tác vụ, tối đa hai luồng. Dùng khi muốn máy nhẹ hơn; tốc độ tổng có thể thấp hơn.

Giao diện chỉ tải tóm tắt kịch bản khi cập nhật lịch sử, giữ nguyên phần văn bản đầy đủ để tạo giọng và xuất tệp. Lịch sử hiển thị từng nhóm; khi không có tác vụ hoặc tab bị ẩn, giao diện giảm tần suất cập nhật. Mở lại bản thu không tự đặt lại vị trí phát ở mỗi lần cập nhật tiến độ.

Số đo Linux và giới hạn nằm trong **CPU-SHARED-MODEL-BENCHMARK.json**. Số đo so sánh trực tiếp bản dùng chung và bản nhiều tiến trình trên Windows nằm trong **SHARED-MODEL-QA.json**, gồm thời gian nạp lạnh/đã nạp, lời thực và RAM working set của cả cây tiến trình. Trang hệ thống và báo cáo bản thu hiển thị cấu hình thực đã dùng. Các số đo ngắn không chứng minh tạo một giờ trong hai phút.

## Chọn tốc độ và giọng

Bản 1.9 giữ giọng đang chọn và ghi nhớ chế độ tốc độ, ngôn ngữ cùng cấu hình CPU. Chọn **Ưu tiên tốc độ**, nghe mẫu và bấm **Đo tốc độ** để kiểm tra kết quả thực trên máy bạn. Bộ đo dùng câu thử đúng ngôn ngữ của giọng Việt/Anh và giọng mẫu quốc tế.

Với bộ căn FFmpeg, nhiều câu SRT được tạo và căn đồng thời; WSOLA giữ đường xử lý nhanh hiện có. Bước xuất cuối ghép theo thứ tự mốc gốc. Các mảnh đã xong được giữ để tiếp tục, và bản thu chỉ hoàn tất khi đủ lời, đủ câu và đúng timeline.

Bộ giọng quốc tế dùng lại phần mã hóa mẫu, tránh xử lý lại cùng bản thu ở mỗi câu. Với đúng VoxCPM 2.0.3 trên CPU FP32, attention chỉ đọc phần cache đã có dữ liệu; phép tính và trọng số được giữ nguyên. **Nhanh** dùng 4 bước, **Cân bằng** 8 bước và **Chất lượng** 10 bước. Giảm số bước có thể thay đổi phát âm và sắc thái; hãy nghe mẫu trước bản dài.

Đo cùng 10 bước trên máy đám mây dùng 4 luồng cho thấy mẫu Nhật ngắn nhanh hơn khoảng **2,00 lần**, mẫu Thái khoảng **1,79 lần** sau tối ưu và tái sử dụng mẫu. Đây là hai câu thử dài 2–4 giây, chưa phải phép đo một giờ hoặc kết quả trên máy của bạn. Báo cáo chi tiết nằm trong **CPU-SHORT-SPEECH-BENCHMARK.json**. Mẫu Nhật 4 bước bị sai phần cuối khi kiểm tra bằng nhận dạng giọng nói tự động, nên lần mở đầu vẫn dùng Cân bằng; chọn Nhanh khi chấp nhận đánh đổi và đã nghe thử.

Số tiến trình quốc tế được giới hạn riêng theo RAM và lõi vật lý, tối đa 8; mỗi model FP32 được dự trù 16 GiB cùng khoảng trống cho hệ thống. Ví dụ 28 lõi vật lý và 128 GiB RAM còn đủ trống có thể chọn tối đa 7 tiến trình × 4 luồng. Nano/Turbo vẫn có giới hạn và phép tự đo riêng. Không áp số đo Nano cho giọng quốc tế.

Mai Anh/Turbo hỗ trợ nhiều tác vụ song song. Chọn **Ưu tiên tốc độ → Tự đo và tối ưu CPU** để tối ưu giọng đang chọn. Nano và Turbo có cấu hình RAM/CPU và kết quả đo riêng. CPU Xeon E5 v4 dùng Turbo FP32; không ép INT8 trên CPU thiếu VNNI.

Bấm **Chuyển sang Nano và đo tốc độ** khi muốn so sánh bộ giọng nhanh. Chỉ nút đổi giọng chủ động mới chọn Nano; kịch bản giữ nguyên. Bản thu hiện rõ bộ giọng, số tác vụ/luồng và FP32 hoặc số bước Nano thực dùng.

- **Nhanh:** Nano 4 bước, nhiều tác vụ dùng chung trọng số theo tài nguyên máy, bộ căn WSOLA. Cần nghe lại chất lượng.
- **Cân bằng:** Nano 8 bước. **Chất lượng:** Nano 16 bước; ưu tiên chất lượng thay vì số đo tốc độ.
- Nano và Turbo hỗ trợ tối đa **32 tác vụ CPU**. Ở cấu hình Tốc độ tối đa, máy 56 luồng / 28 lõi vật lý, đủ RAM có thể dùng 28 tác vụ × 1 luồng; tool không coi luồng ảo là lõi vật lý.
- Chọn **giọng Nano → Ưu tiên tốc độ → Tự đo và tối ưu CPU**. Tool thử nhiều cấu hình bằng lời thật và lưu cấu hình nhanh nhất đo được; số bước tạo giọng giữ theo chế độ đã chọn. Thử nhiều cấu hình lần đầu có thể mất vài phút.
- Bấm **Sao chép kết quả đo** để gửi số liệu, không kèm kịch bản riêng. Có thể dừng quá trình đo bằng nút Dừng tạo.
- Số đo dùng thời lượng lời đã tạo, loại khoảng lặng SRT. Kết quả phân biệt lượt nạp model và lượt model đã sẵn sàng; hãy kiểm tra cả kịch bản dài để xác nhận mốc 2 phút/1 giờ.
- Có 10 nhịp/thể loại: Tự nhiên, Tin tức, Review, Kể chuyện, Kinh dị nhịp chậm, Cổ tích, Thuyết minh, Quảng cáo, Chậm rãi, Sôi nổi.
- Gợi ý giọng dùng mẫu đọc tin tức/kể chuyện có sẵn. Sắc thái phụ thuộc mẫu giọng và dấu câu; bộ chọn thể loại điều chỉnh nhịp/nghỉ, không bảo đảm diễn xuất như người thật.
- `**từ nhấn**`, `[pause=0.8]` điều chỉnh chủ động. VieNeu nhận `[cười]`, `[thở dài]`, `[hắng giọng]` khi bạn tự thêm; tool không tự thêm các âm thanh này.

**Không bảo đảm đạt 30× thời gian thực hoặc tạo 1 giờ trong 2 phút.** Hiệu năng phụ thuộc CPU, RAM, giọng, độ dài đoạn và nạp model. Lượt đo ngắn chỉ là ước tính; nhiều tiến trình có thể chậm hơn nếu máy thiếu tài nguyên.

## Thư viện giọng mẫu và giọng quốc tế

Bản 1.9 đọc thư viện giọng mặc định trong **app/voice-library**. Nếu có gói giọng riêng, cài gói cập nhật vào thư mục Portable đang dùng, sau khi đóng tool. Các giọng xuất hiện trong nhóm mẫu mặc định; bấm nghe thử để chọn. Mẫu và giọng cá nhân trong **app/.data/voices** vẫn được giữ. Các bản ghi âm riêng chỉ được đưa vào bản GitHub ở dạng mã hóa; mật khẩu được gửi riêng. Khi mở bộ 19 giọng, chỉ thư viện giọng được thêm, mã ứng dụng hiện tại được giữ để tránh quay lại bản cũ.

Mẫu tiếng Anh dùng Turbo đã đi kèm. Với mẫu tiếng Hàn, Nga, Nhật, Pháp, Tây Ban Nha và Thái, chạy **TAI_GIONG_DA_NGON_NGU.bat** một lần khi có Internet. Bộ cài tải model **VoxCPM2 khoảng 5 GB** cùng các thư viện CPU vào **runtime-international** riêng; cần thêm dung lượng cho thư viện, tệp tải tạm và quá trình cài đặt. Runtime Nano/Turbo hiện có được giữ nguyên. Giấy phép, nguồn và checksum model được lưu cùng bộ model.

Cài đặt và nạp model lần đầu có thể mất nhiều thời gian. Chỉ khi kiểm tra tạo lời thành công, giọng quốc tế mới báo sẵn sàng. Mở lại tool sau khi hoàn tất; những lần tạo tiếp theo dùng model cục bộ. Bộ này mặc định chạy CPU FP32, có cấu hình Nhanh/Cân bằng/Chất lượng cùng số đo riêng; không dùng số đo Nano/Turbo để suy ra tốc độ quốc tế hoặc cam kết 2 phút/1 giờ. Độ giống giọng và cảm xúc phụ thuộc mẫu, lời đọc và model; nghe kiểm tra trước khi dựng video.

Với giọng quốc tế, **Tiết kiệm RAM (INT8)** là lựa chọn chủ động; mặc định vẫn là **FP32**. INT8 chỉ lượng tử hóa các lớp Linear trong hai bộ ngôn ngữ, giữ model gốc trên đĩa cùng bộ mã hóa/giải mã âm thanh và diffusion. Mỗi lần nạp model mới vào RAM phải chuyển đổi model, có thể thêm khoảng 19 giây trên máy đo; đây không phải bước chỉ chạy một lần khi cài đặt. Cần dự trù khoảng 20 GiB RAM cho mỗi tác vụ đang khởi tạo cùng khoảng trống hệ thống, tương đương tối thiểu khoảng 24 GiB RAM khả dụng cho một tác vụ INT8. RAM khi đã nạp thấp hơn không có nghĩa mức dùng RAM cao nhất khi nạp cũng thấp. Tool giới hạn số tác vụ theo cả mức nạp đầu này. Nghe thử mẫu đúng giọng/ngôn ngữ trước bản dài; không có cam kết tự nhiên hoặc chính xác tuyệt đối cho mọi kịch bản.

Đo bảy câu thử ngắn bằng bảy ngôn ngữ cho thấy INT8 tăng thông lượng lời thực khoảng **1,42 lần** so với FP32; phép đo RAM riêng sau khi nạp cho thấy **10,267 → 7,693 GiB**, giảm khoảng **25%**, với đỉnh khởi tạo **19,832 GiB**. Nhận dạng tự động không phát hiện thêm từ bị mất trong bảy mẫu này; mẫu Tây Ban Nha và Thái vẫn có sai khác một ký tự như FP32. Đây không phải kiểm chứng bằng người nghe, cảm xúc, toàn bộ giọng hoặc bản một giờ. Báo cáo **CPU-INTERNATIONAL-INT8-BENCHMARK.json** ghi đầy đủ giới hạn và cách đo.

## Dữ liệu và phạm vi

Mẫu cá nhân, bản thu, lịch sử và model nằm trong **app/.data**. Sao lưu trước cập nhật. Giải nén sang thư mục mới; giữ bản cũ để bảo toàn dữ liệu. Bản công khai không chứa lời hoặc khóa riêng; nếu kèm bộ giọng riêng thì bộ đó được mã hóa, không công khai bản thu ở dạng đọc được. Gói giọng riêng chứa các mẫu được đưa vào thư viện và cần được giữ riêng.

Tối đa **24 giờ** mỗi tác vụ. Một triệu ký tự có thể vượt thời lượng hoặc dung lượng đĩa; chia kịch bản để đọc hết. WAV mono 24 kHz dài 24 giờ cần khoảng 4,15 GB, chưa tính cache/tệp tạm. Tool báo khi không thể xuất đầy đủ.

Gói chỉ tạo âm thanh, không dựng video. Qwen quốc tế không được đóng gói. Giọng Windows chỉ hiện nếu máy có SAPI tương ứng. Giao diện chỉ mở trên máy cục bộ; không mở cổng dịch vụ ra Internet.

## Kiểm tra bản phát hành

Builder chỉ tạo ZIP sau kiểm tra Windows bằng Python đóng gói tại đường dẫn đã di chuyển: inference Nano/Turbo ngoại tuyến, nhịp tin tức bằng Nano, căn SRT với FFmpeg/WSOLA, giữ cao độ và phần đầu/cuối âm thanh thử, xuất WAV/MP3/TXT/SRT và khởi động giao diện HTTP. Kết quả mẫu lạnh/ấm nằm trong **PORTABLE-QA.json** và **BUILD_INFO.json**. Đây là số đo máy dựng gói, không phải cam kết với máy của bạn hoặc thử toàn bộ một triệu ký tự.

SHA256 của ZIP và manifest từng tệp đi kèm bản phát hành. Giấy phép Python, thư viện, FFmpeg và model đi kèm được giữ trong gói; bộ quốc tế tải riêng giữ giấy phép cạnh model. Không tắt TLS, checksum hoặc phần mềm bảo vệ để xử lý lỗi tải.

Nếu bạn chủ động dùng **bản mã nguồn**, có thể dùng Python 3.12 x64 cùng các BAT cài đặt của mã nguồn. Đây là quy trình khác; người dùng gói Portable chỉ cần giải nén và mở MO_TOOL.bat.
