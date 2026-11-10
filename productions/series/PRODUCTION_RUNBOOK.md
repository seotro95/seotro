# Quy trình chuẩn áp dụng từ chủ đề 3

Làm từng chủ đề theo danh sách đã lưu. Mẫu là tập 3 — Mal’ta: kịch bản gốc 3.087 từ, 20 phút, 120 đoạn lời, 100 clip riêng trong 10 TXT và 20 vị trí dùng lại cảnh. Đây là mẫu tổ chức công việc; nội dung và bằng chứng phải nghiên cứu mới cho mỗi tập.

## 1. Đọc hồ sơ tiếp nối

Đọc `SERIES_STATE.json`, danh sách chủ đề, `VOICE_PROFILES_LOCKED.json`, `NARRATION_STYLE_LOCKED.json` và `VOICE_FILE_NAMING.json`. Dùng đúng số chủ đề người dùng yêu cầu. Không tự chạy cả danh sách hoặc làm tập kế tiếp khi chưa được yêu cầu.

Mặc định mỗi tập dài 20 phút. Tập 2 dài 22 phút là ngoại lệ theo yêu cầu riêng. Nếu người dùng đổi thời lượng, tính lại số ô 10 giây, thời gian chương và số mẫu âm thanh; không tự đổi mặc định của cả chuỗi.

## 2. Nghiên cứu và phân biệt điều biết với điều suy luận

Ưu tiên công bố gốc, cơ quan nghiên cứu và dữ liệu có thể kiểm tra. Lưu URL, tác giả, năm, DOI nếu có, phạm vi kết luận và mốc lời sử dụng. Kiểm tra ngày công bố trực tuyến khác ngày số tạp chí; phân biệt tuổi mẫu, thời điểm sự kiện và ngày công bố. Không lấy một video tham chiếu làm nguồn khoa học duy nhất.

Với khảo cổ và di truyền, giữ rõ cá thể khác quần thể; có quan hệ tổ tiên khác tổ tiên trực tiếp; quan hệ gene khác đường di cư đã chứng minh; mẫu tái hiện khác ảnh chứng cứ thật. Bản đồ phải có nguồn, đúng địa lý và ghi rõ đường bờ hiện đại hay cổ. Không cho công cụ sinh hình tự tạo số liệu rồi trình bày như dữ liệu nghiên cứu.

## 3. Viết kịch bản mới tiếng Anh

Giữ cấu trúc kể của mẫu: một vật hoặc chi tiết nhỏ có con người → câu hỏi gây tò mò → cuộc điều tra theo từng lớp bằng chứng → giải thích cơ chế bằng ví dụ dễ hiểu → kết quả và giới hạn → đoạn kết quay về chi tiết ban đầu với ý nghĩa mới.

Luân phiên vật chứng, đời sống, cảnh quan, bản đồ, phòng thí nghiệm và sơ đồ. Nối các phần bằng câu hỏi thật hoặc vấn đề phần trước chưa giải quyết. Không chép lời, logo hay gán một phần mềm cụ thể cho tác giả video tham chiếu khi chưa biết.

Với mục tiêu 20 phút, dự kiến khoảng 2.800–3.200 từ tiếng Anh; số từ chỉ là dự tính. Chia 120 đoạn dự kiến 10 giây, thành 12 chương 100 giây. Tách tệp lời đọc sạch khỏi tệp có mốc thời gian và ghi chú hình.

## 4. Lập timeline và bỏ cảnh trùng

Mỗi ô timeline có ID, mốc đầu/cuối, lời Anh, clip ID, tên tệp, hành động, góc máy, chuyển động máy và nhãn `NEW` hoặc `REUSE`.

Mẫu tập 3 dùng 100 clip riêng và 20 ô dùng lại, nhưng phải xét ý nghĩa hình của từng chủ đề. Nếu cùng thiết lập và cùng thông tin hình, dùng lại clip, ghi rõ nguồn và đánh dấu không tạo mới. Cùng địa điểm nhưng thao tác, vật liệu hoặc thông tin khác có thể cần cảnh riêng. Không thêm cảnh trùng chỉ để làm đầy tệp.

Mỗi prompt tạo một cảnh liên tục 10 giây, một hành động chính, một chuyển động máy phù hợp; 16:9, mục tiêu 1080p/24fps khi công cụ hỗ trợ. Ghi rõ không có audio, lời nói, nhạc, tiếng động hoặc phụ đề sinh tự động. Chữ và số khoa học thêm trong phần mềm dựng. Lập các nhóm 10 prompt mới để mỗi TXT đúng 10 prompt, đánh số liên tục. Số clip riêng khác số cảnh timeline.

## 5. Chuẩn bị 30 giây đầu

Chọn hình mạnh và đúng nội dung mở đầu. Mẫu tập 3 có 8 shot trong 30 giây, lấy từ chính kho clip đã lập. Ghi rõ clip nguồn, source-in, source-out và vị trí đặt trên timeline. Kế hoạch này thay cách đặt hình trong 30 giây đầu, không cộng thêm intro vào voice.

Ưu tiên cắt trực tiếp theo ý kể. Chỉ hoà cảnh ngắn khi có lý do đổi thời gian hoặc bối cảnh. Crop nhẹ không phải một góc máy quay mới. Giữ vật liệu, ánh sáng và nhân vật nhất quán.

## 6. Bàn giao tài liệu trước khi tạo voice

Xuất TXT kịch bản sạch, TXT có mốc, SRT dự kiến, các TXT prompt, timeline CSV/JSON, CSV cảnh dùng lại, kế hoạch hook, nguồn kiểm chứng và hướng dẫn dựng. Có bản đồ thì đính kèm tham chiếu và chú thích nguồn.

Kiểm tra số đoạn, tổng timeline, số prompt, đúng 10 prompt mỗi TXT và nguồn của mọi ô dùng lại. Đóng ZIP, lưu trên GitHub, gửi link tài liệu rồi mới bắt đầu tạo voice. Không yêu cầu xác nhận lại các lựa chọn đã được người dùng cho phép.

## 7. Dịch và biên tập 16 ngôn ngữ còn lại

Dịch theo ngữ cảnh chương, giữ đúng ý và cách nói phù hợp ngôn ngữ đích. Kiểm tra tên riêng, mã mẫu, năm và thuật ngữ; thay nghĩa ẩn dụ bằng cách nói rõ khi máy dịch dễ hiểu sai. Không chấp nhận lỗi đã biết chỉ để đủ số tệp.

Lưu bản dịch dùng thực tế, nguồn lời Anh và trạng thái rà soát. Đặc biệt với H’Mông, giữ chữ thanh điệu RPA, phân biệt Amelikas là châu Mỹ với tên một quốc gia và không tự nhận đã xác minh phương ngữ H’Mông Trắng. Kiểm tra toàn bộ đầu vào bằng bộ kiểm tra của engine trước khi tạo hết audio.

Mã như `MA-1` có thể cần dạng đọc riêng để engine native không gặp chữ số dính với chữ cái. Ghi từ điển phát âm vào hồ sơ, giữ tên hiển thị đúng trong tài liệu; không âm thầm xoá ký tự hay thay đổi ý.

## 8. Giữ nguyên giọng và đọc có nhấn nhá

Giữ `science-prehistory-17-v1`: 16 giọng nam và H’Mông nữ 3. Mã giọng, locale, engine và hash mẫu tham chiếu nằm trong hồ sơ; đổi tên tệp theo quốc gia không phải đổi voice ID.

Các giọng nam dùng backend của Melo-Viet-Studio 1.3.1, nguồn đã khoá tại commit `4f4fa1d72d976d6e2b9c94f906b0e12c6a2cf043`, qua Edge. H’Mông dùng Voice-Studio-Hmong 1.6.6 Native VITS + OpenVoice V2, commit `061430d958b8d5fc14d04209c6f0cd20492382c2`, preset `hmong-female-3`, profile `clear-v1`; mẫu có SHA-256 `ffa26422055a9da069ba8d7a9d780405b6504c27ce70fa5ad3ffed84f5b2dc17`.

Dùng `science-documentary-expressive-v1`: thân thiện, nhấn câu hỏi và ý quan trọng vừa phải, ngắt nghỉ theo ý, hạ nhịp ở đoạn kết. Giữ bản sắc giọng và cao độ. Melo dùng adapter tốc độ khoảng -4% đến +3%, nghỉ 0,07–0,16 giây và nhấn âm lượng nhẹ theo mốc từ khi dịch vụ cung cấp. H’Mông dùng tốc độ, âm lượng và nghỉ theo cụm; không có mốc từng từ hay mô hình cảm xúc được chứng nhận.

Tạo bản thử 30 giây để kiểm tra trước khi chạy toàn bộ; kiểm tra thời lượng, lời và điều khiển nhấn nhá. Có thể gửi bản thử cho người dùng nghe nhưng không tự thêm một bước chờ duyệt nếu họ không yêu cầu.

## 9. Tạo voice có checkpoint

Tách audio theo locale trong thư mục làm việc. Với các bản dịch, cắt theo câu trong đoạn ngắn, giữ nguyên các nhóm số như `24.000`, `24,000`, `24 000`; không để dấu phân cách hàng nghìn trở thành ranh giới câu.

Lưu từng phần đã tạo và thiết lập nhấn nhá để tiếp tục khi lỗi. Dùng số tác vụ vừa phải; tôn trọng thời gian chờ và giới hạn dịch vụ. Sau khi cả lượt kết thúc, chỉ chạy lại phần thất bại, không tạo lại giọng đã đạt kiểm tra. Không huỷ các giọng đang gần hoàn tất chỉ để gộp cùng nhóm lỗi. Không tự thay mã giọng khi dịch vụ lỗi.

## 10. Căn và đo thời lượng thực

Với tập 20 phút: Anh căn 120 ô 10 giây; bản dịch căn 12 chương 100 giây. Có thể điều chỉnh tốc độ giữ cao độ trong mức phù hợp; nếu không vừa, sửa lời hoặc cách chia. Không cắt mất câu và không chèn khoảng im lặng dài để giả đủ phút.

Đo PCM và giải mã MP3 để kiểm tra: 1.200 giây bằng 57.600.000 mẫu tại 48 kHz. Nếu mục tiêu khác, tính `target_seconds × sample_rate`. Lưu số đo, sai số mẫu, ID giọng, engine, hash audio, thiết lập nhấn nhá, mức tốc độ hậu kỳ và trạng thái ngôn ngữ. Kiểm tra SRT Anh có đủ đoạn và khớp nguyên văn kịch bản. Khớp tổng/chương không có nghĩa khớp từng từ giữa các ngôn ngữ.

## 11. Đặt tên voice theo quốc gia và đóng gói

Trong xử lý nội bộ, giữ locale để tránh nhầm engine. Khi bàn giao, dùng `VOICE_FILE_NAMING.json` và mẫu `{topic_prefix}_{delivery_slug}.mp3`, ví dụ `MALTA_03_Viet_Nam.mp3`, `MALTA_03_Phap.mp3`. Bản Anh dùng `My_Tieng_Anh` theo giọng Mỹ đã chọn. H’Mông dùng `Hmong_Trang_Nu`, không gán thành quốc gia.

Tên tệp dùng tiếng Việt không dấu để tương thích Windows và URL; bảng tải ghi tên có dấu đầy đủ. Lưu CSV ánh xạ tên quốc gia, locale, voice ID, giới tính, tệp và SHA-256. Khi chỉ đổi tên, giữ nguyên từng byte audio, không tổng hợp lại; so sánh hash để chứng minh âm thanh không đổi.

Bàn giao 17 MP3 riêng, ZIP đủ 17 bản theo tên quốc gia và ZIP hồ sơ gồm script, SRT, báo cáo, manifest, mã giọng và nhấn nhá. Bảng tải ưu tiên tên quốc gia/ngôn ngữ, không bắt người dùng đoán từ locale. Giữ đường dẫn cũ hoạt động khi bổ sung tên mới.

## 12. Lưu hồ sơ để tiếp tục

Mỗi tập có thư mục riêng trong `productions/`, giữ tài liệu, bảng tải, script, báo cáo, manifest và mã xử lý cần thiết. Lưu quy trình thực tế đã áp dụng và các điều chỉnh riêng của tập. Cập nhật `SERIES_STATE.json`, `TIEP_TUC_TU_DAY.md` và chủ đề kế tiếp sau khi bàn giao thành công. Không ghi nhận đã dựng video khi mới có prompt và voice.

Giữ trạng thái rà soát ngôn ngữ riêng với việc tạo tệp thành công. Hồ sơ giọng và mẫu tham chiếu giúp duy trì tính liên tục; nhà cung cấp có thể thay đổi mô hình dù ID giữ nguyên.

## 13. Khi người dùng gửi clip

Dựng khớp voice Anh, bỏ toàn bộ tiếng clip, ưu tiên 30 giây đầu như kế hoạch, giữ độ phân giải đầu vào phù hợp. Kiểm tra đồng bộ, thời lượng và lỗi hình/âm trước khi xuất. Sau đó bàn giao link video hoàn chỉnh, voice các nước, 5 tiêu đề và 5 prompt thumbnail phù hợp. Không tạo video thành phẩm bằng cách lấy clip của tập trước làm chứng cứ cho tập mới.
