# Ghi chú về video nguồn và phương án dựng

## Phạm vi đã kiểm tra

Đã kiểm tra metadata của [bản phát hành GitHub do người dùng cung cấp](https://github.com/seotro95/seotro/releases/tag/video), qua [GitHub Releases API](https://api.github.com/repos/seotro95/seotro/releases/tags/video).

- Tên bản phát hành: **Video AI 20 Phút**.
- Tệp đính kèm duy nhất: **video.c.a.toi.mp4**.
- Kích thước ghi trong metadata: **340.611.128 byte**.
- Ngày công bố ghi trong metadata: **09/11/2026**.
- [Liên kết tải MP4](https://github.com/seotro95/seotro/releases/download/video/video.c.a.toi.mp4).
- SHA-256 ghi trong metadata: `f1a8659dbccd4db12a79e3c18ea2e1fe08f46f7a03c42bc2250f454f69eff70c`.
- Nội dung mô tả bản phát hành để trống. Metadata không cung cấp transcript hoặc thời lượng đã đo. Tên “20 Phút” không thay thế việc đo thời lượng thật.

Môi trường Cloud khởi động thất bại với lỗi **503** trước khi có thể tải, mở, trích khung hình, đo thời lượng hoặc nghe âm thanh của MP4. Vì vậy, bộ tài liệu này **không khẳng định đã xem hay phân tích cách dựng thực tế của video nguồn**. Các lựa chọn nhịp kể, máy quay và minh họa dưới đây là đề xuất sản xuất mới.

## Cơ sở của kịch bản mới

Kịch bản Ollantaytambo là nội dung nguyên bản, dựa theo công thức sản xuất mà người dùng đã cung cấp: mở bằng quy mô và câu hỏi, định vị địa hình, đưa bằng chứng, giải thích cơ chế, tăng trở ngại, đối chiếu khả năng, rồi trở lại hình ảnh mở đầu.

Câu chuyện đi theo bài toán địa hình và tổ chức: nguồn đá Kachiqhata/Cachicata → xuống sườn núi → vượt thung lũng và sông Urubamba → lên công trường → cung cấp nhân lực, vật liệu và bảo trì. Bản dựng phải phân biệt dấu tích được quan sát với phương án kỹ thuật đang được minh họa.

Nguồn khảo cổ dùng để kiểm tra nội dung gồm [nghiên cứu của Jean-Pierre Protzen về khai thác và gia công đá Inca](https://veda.wiki/images/2/22/1985_Inca_Quarrying_and_Stonecutting_by_Jean-Pierre_Protzen.pdf) và [chuyên khảo được Thư viện Quốc gia Peru lưu trữ](https://repositoriodigital.bnp.gob.pe/bnp/recursos/2/html/arquitectura-y-construccion-incas/186/). Đường vận chuyển, khối đá bỏ lại và công trình đã dựng hỗ trợ lập luận địa lý; chúng không xác định đầy đủ cách buộc dây, số người hoặc kỹ thuật vượt sông.

## Quy tắc hình ảnh và thời lượng

- Tổng thời lượng dựng: **21 phút 42 giây = 1.302 giây**.
- Cảnh **1–130**: mỗi cảnh dùng **10 giây**.
- Cảnh **131**: tạo nguồn **10 giây**, chỉ dùng **2 giây đầu**; fade được thêm khi dựng. Tổng nguồn tạo là 21:50, cắt bỏ 8 giây ở cảnh cuối.
- Có **131 prompt**, đóng thành **14 tệp TXT**: 13 tệp đầu mỗi tệp 10 prompt, tệp cuối chứa prompt 131.
- Mỗi prompt yêu cầu một cú máy liên tục, hình ngang 16:9, mục tiêu 4K/24fps. Khả năng xuất thực tế tùy hệ thống tạo video.
- Tất cả clip tạo phải **hoàn toàn không có âm thanh, lời nói, lời bình, nhạc, tiếng môi trường hoặc hiệu ứng âm thanh**. Giọng đọc được ghép riêng trong bản dựng.
- **Không có trẻ em, trẻ sơ sinh hoặc thiếu niên.** Mọi người xuất hiện phải rõ ràng là người trưởng thành từ 25 tuổi trở lên.
- Không tạo chữ, phụ đề, logo hay watermark bên trong hình. Nhãn “mô phỏng”, chú thích bản đồ và nguồn được thêm ở phần dựng khi phù hợp.
- Cảnh tái dựng cổ đại dùng bối cảnh Inca cuối thế kỷ XV, vật liệu và trang phục hợp lý. Cảnh khảo sát hiện đại giữ trang bị hiện đại rõ ràng để tránh nhầm thời kỳ.
- Đường dây, xe trượt, con lăn, cơ cấu đòn bẩy và phương án vượt sông chỉ xuất hiện như giả thuyết hoặc mô hình giải thích khi lời bình cho phép. Không biến hình do AI tạo thành bằng chứng khảo cổ.
- Không tự gán trọng lượng từng khối, số công nhân chính xác, đường đi GPS chính xác, cấu hình dây hoặc cách vượt sông là sự thật đã được xác định.

## Gợi ý cách dựng

Xen hình phong cảnh rộng để hiểu địa hình, cận chi tiết để nhìn vật liệu, và mô hình/cắt lớp để hiểu cơ chế. Mỗi cảnh 10 giây có một nhiệm vụ rõ ràng và một chuyển động máy chính; các chuyển cảnh được thực hiện ở phần dựng. Trở lại bố cục bức tường mở đầu gần cuối để người xem thấy cùng một công trình với hiểu biết mới.

Năm tiêu đề và năm prompt thumbnail trong tệp đi kèm là đề xuất mới cho kịch bản Ollantaytambo, không phải nội dung được trích hoặc sao chép từ video nguồn. Dòng chữ thumbnail được thêm thủ công sau khi tạo hình.
