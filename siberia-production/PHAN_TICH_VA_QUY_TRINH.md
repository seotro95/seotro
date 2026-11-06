# Phân tích video tham chiếu và quy trình sản xuất

Nguồn: https://www.youtube.com/watch?v=-B_y0IPrNmQ — tệp chủ kho cung cấp qua Release `my`.

SHA-256: `ba8cf7542ee761b6073ab75167001f11bb86e4c60105ed3440c1581fcefb4cf2`.

Đã kiểm tra tệp: 225.352.166 byte; hình 1280×720, H.264, 30 fps; âm thanh AAC stereo 44,1 kHz; thời lượng container 1536,02322 giây. Bản mới dùng mốc 1536 giây, tương ứng 25:36.

Phương pháp: chép lời tự động toàn bộ tiếng Tây Ban Nha, lấy khung hình trên toàn bộ video, dò biến đổi cảnh và kiểm tra thêm các khung hình tại mốc cụ thể. Bản chép lời có thể sai tên riêng; mốc ranh giới dưới đây là ranh giới lời dẫn xấp xỉ. Từ MP4 chưa xác minh được công cụ tạo cảnh, nguồn từng ảnh hoặc thư viện nhạc của bản gốc.

## 1. Đây là dạng nội dung gì?

Video khám phá địa lý dạng danh sách, dẫn chuyện ngoài hình, pha yếu tố bí ẩn và truyền thuyết. Nó gồm 11 câu chuyện ngắn về các địa điểm Siberia, không phải một nghiên cứu đơn lẻ hay một câu chuyện nhân vật xuyên suốt.

Sức hút đến từ sự tương phản có thể hình dung ngay: cát cạnh rừng, một tảng đá chênh vênh, hình dạng đá giống người, công trình cổ trên đảo. Lời dẫn dùng kích thước, so sánh đời thường, sự xa xôi và các câu hỏi còn mở để nối những hình phong cảnh.

| Mốc lời dẫn | Nội dung |
|---|---|
| 00:00–00:41 | Phá định kiến về Siberia, đưa hình ảnh gợi tò mò và hứa 11 địa điểm |
| 00:41–03:01 | Patomskiy Crater |
| 03:01–05:27 | Chara Sands |
| 05:27–07:33 | Putorana Plateau |
| 07:33–09:50 | Hanging Stone, Ergaki |
| 09:50–12:18 | Batagaika thaw slump |
| 12:18–14:35 | Kigilyakh/Kisilyakh, các cột đá Yakutia |
| 14:35–16:54 | Por-Bazhyn |
| 16:54–18:51 | Sunduki |
| 18:51–20:58 | Belukha |
| 20:58–23:05 | Vasyugan Mire |
| 23:05–25:29 | Truyền thuyết “Devil’s Cemetery” |
| 25:29–25:36 | Lời kết |

Bản chép lời nhận được khoảng 3.993 từ tiếng Tây Ban Nha, tương đương khoảng 156 từ/phút trên tổng thời lượng. Không dùng con số này như quy đổi trực tiếp sang mọi ngôn ngữ.

## 2. Cách viết lời dẫn có sức hút tương tự

Phần mở đầu của bản gốc đi theo thứ tự: một hình dung quen thuộc → phủ định hình dung đó → ba ví dụ lạ → số lượng câu chuyện → bước vào địa điểm đầu tiên. Thủ pháp hữu ích là cho người xem một vật cụ thể để tưởng tượng trước khi giải thích.

Mỗi câu chuyện có thể viết theo sáu nhịp:

1. Mở bằng hình ảnh hoặc nghịch lý, tránh bắt đầu bằng đoạn giới thiệu hành chính dài.
2. Gọi tên và định vị địa điểm.
3. Cho một chi tiết về hình dạng hoặc quy mô, kèm so sánh dễ hình dung nếu số liệu có nguồn.
4. Đặt câu hỏi thứ hai sâu hơn câu hỏi mở đầu.
5. Giải thích bằng chứng, rồi xác định phần nào vẫn là giả thuyết hoặc truyền thuyết.
6. Trả lời câu hỏi chính và dùng một câu nối tự nhiên sang địa điểm tiếp theo.

Ví dụ mở mới: một cồn cát với núi tuyết phía sau đủ tạo tò mò. Câu tiếp theo nên cho biết điều gì khiến cảnh ấy đáng tìm hiểu. Những từ như “kinh hoàng”, “chấn động” không thể thay cho chi tiết và bằng chứng.

Xen câu ngắn để nhấn với câu dài vừa phải để giải thích. Viết cho tai nghe: một câu nên có một ý chính; đọc số, thuật ngữ và tên riêng theo cách người nghe có thể theo kịp. Mỗi đoạn phải mang thông tin mới hoặc làm thay đổi cách người xem hiểu cảnh trước đó.

Các lời kể dân gian cần được dẫn bằng những cụm tương ứng với “theo truyền thuyết” hoặc “người ta kể”. Bản mới không sử dụng một câu chuyện chưa kiểm chứng như bằng chứng về một hiện tượng vật lý.

## 3. Hình ảnh và hiệu ứng đã quan sát

| Mốc kiểm tra | Điều thấy trong khung hình | Cách tái tạo cho bản mới |
|---|---|---|
| 00:00–00:02 | Cảnh cột đá, chuyển động khung hình chậm | Một chuyển động máy nhẹ; không cộng thêm zoom lớn lên clip đã chuyển động |
| Khoảng 00:03,7–00:04 | Ánh sáng cam/vàng phủ ảnh rồi chuyển sang trắng sáng | Overlay light leak và flash trắng ngắn, khoảng 8–12 frame ở 30 fps là điểm bắt đầu để chỉnh |
| Khoảng 00:12 | Hai phong cảnh cùng xuất hiện trong quá trình hòa hình | Cross dissolve ngắn có phần đầu/cuối clip dư để nối |
| Khoảng 02:14,8–02:17 | Cận đá với chuyển động mạnh, tạo cảm giác rung/lướt nhanh | Chỉ dùng có chủ đích cho một điểm nhấn; kiểm tra không gây khó theo dõi |
| Các mẫu trên toàn video | Phần lớn là phong cảnh, toàn cảnh rộng, chi tiết địa chất; ít chữ trong những mẫu đã xem | Cho lời dẫn làm trục, thay đổi cỡ cảnh thay vì phủ nhiều chữ |

Dò tự động ở ngưỡng chênh cảnh 0,28 cho 151 thời điểm ứng viên; gộp các thời điểm gần nhau còn 129 nhóm. Đây không phải số shot đã được đếm thủ công. Nhiều khoảng chuyển cảnh gần các bội số của 8 giây; một số vùng chuyển động mạnh tạo nhiều ứng viên giả. Nhịp dựng nhìn chung có thời gian để quan sát cảnh, phù hợp video dài.

Đo trên âm thanh gốc: khoảng -15,4 LUFS integrated, LRA 3,3 LU, true peak -0,1 dBTP. Đây là số đo của bản tham chiếu, không phải thông số mặc định để sao chép; bản mới được phối và đo riêng.

Màu sắc thiên về phong cảnh rõ chi tiết: trời xanh, đá tương phản, rừng xanh và cát ấm. Độ tương phản và màu không cần cực đoan để tạo cảm giác điện ảnh.

## 4. Quy trình tạo ảnh và video bằng Muse 1.6.0

Mỗi shot cần một ý hình ảnh, một cỡ cảnh và một chuyển động chính. Prompt nên đi theo thứ tự:

`Địa điểm → đặc điểm vật lý cần giữ → cỡ cảnh/góc máy → ánh sáng → một chuyển động → các chi tiết phải tránh`.

Ví dụ: Chara Sands, cồn cát sáng cạnh rừng taiga, dãy Kodar có tuyết ở xa, toàn cảnh rộng, ánh sáng tự nhiên, máy tiến chậm. Không tạo thành sa mạc vô tận và xóa mất rừng vì điều đó làm sai nghịch lý địa lý cần kể.

Các cảnh cơ chế như dòng xoáy dưới băng là hình minh họa giải thích. Không trình bày chúng như ảnh đo đạc thật. Cảnh tái dựng lịch sử cũng cần được phân biệt với tư liệu lịch sử.

Các dự án JSON Muse giữ schema `version: 1`, mỗi tệp 10 ô; ô không dùng ở lượt cuối được tắt. Chọn chế độ Muse thật. Các model, độ nét và thời lượng trong dự án là yêu cầu gửi đến dịch vụ; cần kiểm tra kết quả thực tế.

Đối với địa hình có hình dạng đặc trưng, so lại ảnh kết quả với nguồn tham khảo trước khi làm chuyển động. Kiểm tra hình dạng đá, đường chân trời, hướng mặt trời, sông/hồ và sự nhất quán giữa các góc nhìn. Không coi mọi cảnh đẹp được mô hình tạo ra là hình ảnh đúng của địa điểm đã đặt tên.

## 5. Kịch bản mới và việc đồng bộ 17 bản giọng

Bản mới có tên “Siberia’s Impossible Landscapes: Eleven Places That Defy First Impressions”. Lời được viết mới, đổi cách sắp xếp và bổ sung nội dung như vòng băng Baikal, Lena Pillars và Tunguska; không phải bản dịch nguyên lời video gốc.

Phần mở đầu được giữ ngắn, khoảng 40 giây. Toàn bộ 59 đoạn tạo thành mốc 25:36. Nguồn cho các phát biểu quan trọng nằm trong `master_timeline.json`, gồm NASA, USGS, UNESCO và nghiên cứu về Por-Bazhyn.

Tiếng Anh là bản chuẩn. Các tiếng Việt, Tây Ban Nha, Pháp, Nhật, Hàn, Đức, Ý, Bồ Đào Nha, Hà Lan, Ba Lan, Thụy Điển, Đan Mạch, Phần Lan, Na Uy, Séc và Hindi phải giữ cùng mốc từng đoạn. Dịch đúng ý và điều chỉnh câu theo thời gian đọc, thay vì chỉ ép toàn bộ tệp vào một thời lượng.

Dùng Melo + Việt Studio 1.3.1 theo đúng mã nguồn đã ghim. Chọn ID giọng do công cụ liệt kê; ghi lại engine và giọng thực tế trong báo cáo. Các bản WAV được kiểm tra ở mono PCM 16-bit, 48 kHz, đúng 73.728.000 mẫu. MP3 dùng để nghe; WAV là chuẩn khi lồng tiếng. Mốc SRT phục vụ đồng bộ đoạn, không phải căn chính xác từng từ.

Nếu một đoạn quá dài, sửa câu hoặc cách diễn đạt trong ngôn ngữ đó rồi tạo lại. Nếu một đoạn quá ngắn, chỉnh nhịp hoặc câu phù hợp; không che phần thiếu bằng một khoảng im lặng dài ở cuối video.

## 6. Dựng và kiểm tra bản cuối

1. Khóa thời gian giọng Anh và các mốc chung trước.
2. Đặt hình theo nội dung từng đoạn; giữ media dư ở hai đầu để làm dissolve mà không làm tổng timeline ngắn đi.
3. Dùng phần lớn là cắt thẳng, xen hòa hình khi đổi không khí. Light leak/flash là điểm nhấn ở số ít chỗ chuyển chương.
4. Đặt tên địa điểm ngắn, rõ; thêm nhãn cho hình AI/tái dựng. Bản chính tiếng Anh có thể dùng nhãn tên riêng chung cho các bản lồng tiếng.
5. Giữ nhạc và hiệu ứng dưới lời dẫn, giảm nền thêm khi có tên riêng hoặc dữ kiện. Cân bằng và đo lại chính bản xuất; mục tiêu -16 đến -14 LUFS integrated, true peak không quá -1 dBTP là thông số đề xuất cho bản mới.
6. Xuất 1920×1080, 30 fps, H.264 và AAC. Ghi rõ độ phân giải nguồn thực tế nếu có clip cần phóng lên.
7. Kiểm tra đủ đầu/cuối câu, khớp mốc, chất lượng hình, lỗi chữ, âm thanh bị méo và khoảng đen. Xem bản MP4 đã xuất, không chỉ xem timeline.

## Trạng thái cần phân biệt

Phân tích tệp gốc và kịch bản mới đã được chuẩn bị. Việc tạo voice được kiểm chứng bằng báo cáo từng tệp. Các JSON/prompt và chương trình gọi Muse là tài liệu sản xuất; chúng không chứng minh rằng Muse đã tạo xong media. MP4 chỉ được coi là hoàn tất sau khi có media thật từ Muse, dựng xong và kiểm tra bản xuất.
