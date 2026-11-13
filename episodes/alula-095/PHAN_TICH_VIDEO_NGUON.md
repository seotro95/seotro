# Phân tích nguồn và cách chuyển sang chủ đề 95

Nguồn: https://github.com/seotro95/seotro/releases/tag/video — `video.c.a.toi.mp4`.
Đã đối chiếu SHA-256 của tệp có sẵn với digest release:
`f1a8659dbccd4db12a79e3c18ea2e1fe08f46f7a03c42bc2250f454f69eff70c`.
Tệp nguồn dài **21:02,933**, khác thời lượng **20:42** được yêu cầu cho phim AlUla.
Metadata: 1280×720, H.264, 60 fps; AAC stereo 44,1 kHz.

Phạm vi quan sát: xem contact sheet lấy mẫu toàn phim; đọc metadata và các số đo
dò chuyển cảnh đã lưu từ đúng tệp; đối chiếu các đoạn nhận dạng lời ở đầu, giữa,
cuối. Bản Whisper tiny tự động là tiếng Nga, có lỗi lặp và nhận dạng, nên không
được coi là bản chép lời nguyên văn. Không tuyên bố đã nghe duyệt toàn bộ nguồn.

## Cách kể chuyện có thể vận dụng

1. **Vật chứng nhỏ mở ra câu hỏi lớn.** Phần mở gắn vật chứng khảo cổ với việc
   con người sống trong khí hậu lạnh. Ở AlUla, thay bằng một giọt nước giữa cát
   khô và câu hỏi vì sao nơi này thành điểm gặp của những đường cổ.
2. **Một luận điểm xuyên suốt.** Nguồn giải thích giữ nhiệt theo nhiều lớp;
   AlUla giải thích quan hệ đá định hình địa hình, nước hỗ trợ cư trú, cư trú
   hỗ trợ mạng lưới dịch chuyển. Đây là cấu trúc lập luận, không sao chép câu chữ.
3. **Cảnh đẹp được nối với bằng chứng và cơ chế.** Khung hình nguồn luân phiên
   toàn cảnh, cận vật liệu, bảo tàng, người nghiên cứu, mô hình cắt lớp. Bộ mới
   luân phiên thung lũng, giếng, kênh tưới, mặt đá, văn khắc và hình giải thích.
4. **Liên hệ quá khứ với hiện tại.** Đoạn sau của nguồn liên hệ nguyên lý giữ
   nhiệt với đời sống hiện đại. Bộ mới nối nhu cầu nước trong lịch sử với canh
   tác, bảo tồn và trách nhiệm hôm nay.
5. **Kết vòng tròn.** Trở về hình ảnh nhỏ đầu phim sau khi người xem đã hiểu
   bối cảnh lớn. Câu hỏi bình luận đặt gần cuối, không cản phần giải thích chính.

## Nhịp dựng và giới hạn đo

Máy dò FFmpeg trên mẫu 2 fps, ngưỡng 0,24 ghi nhận 196 **ứng viên** chuyển cảnh;
khoảng trung vị 5,5 giây, trung bình 6,41 giây. Đây không phải danh sách mọi
điểm cắt chính xác từng frame. Contact sheet cho thấy cảnh vật, vật chứng và
hình giải thích xen kẽ; các mẫu hình không chứng minh loại chuyển cảnh ở mọi chỗ.

Vì người dùng yêu cầu mỗi clip tạo dài 10 giây, bản AlUla dùng 2 giây thiết lập,
6 giây dịch chuyển/hé lộ, 2 giây ổn định. Cảnh kế đổi cỡ và góc máy để giữ nhịp.
Không chèn nhiều chuyển động phức tạp trong một clip. Ưu tiên cắt thẳng trên
lưới 10 giây; dissolve nếu dùng phải nằm trong ô, không làm hụt tổng thời lượng.

Nhạc, tiếng nền, logo, cờ và hình có trẻ em trong nguồn không được chuyển vào
prompt mới. Từng prompt nhắc lại không âm thanh/lời nói và không trẻ em. Lời
thuyết minh được tạo riêng; footage tạo ra phải bỏ mọi track âm thanh khi dựng.

## Cấu trúc AlUla 20:42

| Cảnh | Thời gian | Nội dung |
|---|---|---|
| 1–12 | 00:00–02:00 | Giọt nước, câu hỏi mở và ba mối nối |
| 13–24 | 02:00–04:00 | Sa thạch, phong hóa, thung lũng và đường nước |
| 25–38 | 04:00–06:20 | Giếng, canh tác và lao động duy trì ốc đảo |
| 39–50 | 06:20–08:20 | Mạng lưới hương liệu, điểm dừng và trao đổi |
| 51–62 | 08:20–10:20 | Dadan, dấu tích đô thị và cách đọc bằng chứng |
| 63–74 | 10:20–12:20 | Jabal Ikmah và di sản tư liệu |
| 75–88 | 12:20–14:40 | Hegra: mộ, tay nghề và hệ thống nước |
| 89–100 | 14:40–16:40 | Công việc thường ngày và sự phụ thuộc lẫn nhau |
| 101–112 | 16:40–18:40 | Những tuyến đường về sau và bảo tồn hôm nay |
| 113–124 | 18:40–20:40 | Giải câu hỏi và quay về giọt nước |
| 125 | 20:40–20:42 | Hai giây kết, không lời |

124 cảnh đầu dùng đủ 10 giây; cảnh 125 vẫn tạo 10 giây nhưng chỉ dùng 2 giây
đầu. Tổng 1.242 giây. Những cảnh lịch sử và hình cắt lớp được phân loại trong
prompt/timeline là tái dựng hoặc minh họa, không phải footage cổ hay hồ sơ khảo sát.
