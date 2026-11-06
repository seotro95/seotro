# Bộ sản xuất Siberia 25:36

Kịch bản mới: **Siberia's Impossible Landscapes: Eleven Places That Defy First Impressions**. Tiếng Anh là bản chính. 59 đoạn, 25 phút 36 giây, 46.080 frame ở 30 fps. Các cảnh là minh họa AI có nhãn; các dữ kiện và liên kết nguồn nằm trong `scripts/master_timeline.json`.

## Tải qua GitHub Releases

1. Đăng nhập tài khoản chủ kho `seotro95`, mở https://github.com/seotro95/seotro/releases và tìm **Siberia 25:36 — production assets**. Release đang là bản nháp riêng cho chủ kho.
2. Trong Assets, tải `Siberia_25m36_Production_Kit.zip`, giải nén ra một thư mục bạn có quyền ghi, ví dụ `D:\Siberia`. Tải cả `SHA256SUMS.txt` để kiểm tra nếu cần.
3. Bộ ZIP có giọng Anh, kịch bản, phân tích, shot list, các dự án Muse và chương trình dựng. Mở **TAI_CAC_GIONG.html** trong ZIP để có nút tải riêng từng ngôn ngữ. Các tệp cũng nằm ở Assets: `<mã>.wav`, `<mã>.mp3`, `<mã>.srt` và `<mã>-report.json`. Nếu chưa thấy một mã, bản đó chưa hoàn tất ở thời điểm tải; không coi danh sách dự kiến là tệp đã có.

Mã: `en` Anh, `vi` Việt, `es` Tây Ban Nha, `fr` Pháp, `ja` Nhật, `ko` Hàn, `de` Đức, `it` Ý, `pt` Bồ Đào Nha, `nl` Hà Lan, `pl` Ba Lan, `sv` Thụy Điển, `da` Đan Mạch, `fi` Phần Lan, `no` Na Uy, `cs` Séc, `hi` Hindi.

WAV là tệp để lồng tiếng: mono PCM16, 48 kHz, chính xác 73.728.000 mẫu. Mỗi đoạn dùng cùng mốc với bản Anh. MP3 để nghe thử; độ trễ mã hóa MP3 khiến nó không phải chuẩn đối chiếu theo từng mẫu. SRT là mốc từng đoạn, không phải phụ đề đã căn từng từ.

## Tạo video bằng Muse đang hoạt động trên máy bạn

1. Mở **Muse AI Studio 1.6.0**, dùng tài khoản **Muse 01** đã tạo được ảnh/video và kiểm tra phiên trong tool. Đợi tác vụ khác của Muse xong.
2. Mở thư mục bộ ZIP đã giải nén, nhấp đúp **BAT_DAU_VIDEO.cmd**. Giữ Muse và cửa sổ chạy mở, tắt chế độ ngủ máy trong thời gian tạo cảnh nếu cần.
3. Chương trình kết nối API nội bộ của chính Muse, lần lượt gửi **227 cảnh**, yêu cầu Omni 1.1 Flash, 10 giây, 16:9, 1080p. Một cảnh chỉ gửi một lần trong lượt chạy; media trả về được lưu ngay vào `media`.
4. Khi đủ cảnh, chương trình cắt theo shot list, hòa hình, thêm các điểm nhấn ánh sáng, tên địa điểm, nhãn minh họa, nhạc nền tự tạo và giọng Anh. Tệp đích là **Siberia_EN_25m36.mp4**. Các báo cáo chỉ được tạo sau khi xuất thực tế.

Nếu Windows đã có Node và FFmpeg/FFprobe, bộ chạy dùng chúng. Nếu chưa có Node, nó dùng runtime sẵn trong bản Muse đầy đủ. Nếu thiếu FFmpeg, nó tải bản Windows từ BtbN GitHub, kiểm tra SHA-256 đã ghim trước khi giải nén. Không đổi chính sách hệ thống, không đọc cookie và không chuyển thông tin đăng nhập ra ngoài.

Các con số 1080p/10 giây là yêu cầu gửi đến Muse. Thời lượng và kích thước tệp trả về được đo lại. Cảnh quá ngắn sẽ dừng để kiểm tra, cảnh nguồn có độ nét thấp hơn được ghi rõ trong báo cáo. Dự kiến cần khoảng 15–25 GB chỗ trống cho clip nguồn, bản dựng và MP4; lượng thực tế tùy dung lượng Muse trả về. Tạo nhiều cảnh dùng hạn mức của chính tài khoản Muse.

## Khi dừng giữa chừng

Chạy lại `BAT_DAU_VIDEO.cmd`: các clip đã xác nhận hoàn tất và còn đúng checksum được bỏ qua. Chương trình dừng nếu có yêu cầu đã gửi nhưng chưa rõ kết quả, để tránh gửi trùng.

Nếu có cảnh báo `uncertain` hoặc `needs_review`, xem số cảnh trong `generation-state.json` và đối chiếu lịch sử Muse. Nếu muốn chủ động tạo lại cảnh số 12 sau khi đã kiểm tra, mở Command Prompt trong thư mục và chạy:

```
BAT_DAU_VIDEO.cmd generate --retry-shot 12
```

Lệnh này cho phép gửi lại đúng cảnh đó, rồi tiếp tục hàng đợi. Nếu nhiều cảnh cần xem lại, mỗi cảnh vẫn phải được xử lý riêng. Không xóa `generation-state.json` để thử lại toàn bộ.

Chỉ tạo cảnh, chưa dựng:

```
BAT_DAU_VIDEO.cmd generate
```

Chỉ dựng lại từ các cảnh đã có:

```
BAT_DAU_VIDEO.cmd render
```

Nếu muốn đổi sang giọng Việt, đặt `vi.wav` trong `audio`, `vi.srt` trong `scripts`, rồi chạy `BAT_DAU_VIDEO.cmd render --voice vi`. Chương trình tái sử dụng các shot đã dựng và tạo lại phần phối âm. Video chính vẫn là bản tiếng Anh.

## Dùng giao diện Muse để xem hoặc chỉnh từng bộ

`muse-projects/video-01.json` đến `video-23.json` là các bộ nhập 10 ô đúng schema Muse 1.6.0. Bộ cuối tắt những ô dư. Các tệp `image-xx.json` dùng cùng prompt để tạo ảnh tham khảo trước. Quy trình tự động dùng text-to-video; không nói rằng ảnh đã được tạo nếu mới có prompt.

Các prompt yêu cầu không đốt chữ vào hình. Tên địa điểm và nhãn được thêm bằng bộ dựng để tránh lỗi chữ AI. `SHOT_LIST.csv` có số cảnh, đoạn lời tương ứng, mốc và kiểu chuyển cảnh. Mở bảng này để kiểm tra hình có minh họa đúng ý đang nói hay không.

## Kiểm tra trước khi sử dụng bản cuối

- Xem MP4 đã xuất: địa hình, ánh sáng, sự liên tục, câu đầu/cuối và tên riêng. So hình với nguồn địa lý trong kịch bản. Các mô hình tạo sinh có thể tạo một cảnh đẹp nhưng sai hình dạng địa điểm.
- Kiểm tra `FINAL_REPORT.json`: đúng 46.080 frame; liệt kê những cảnh bị phóng từ nguồn thấp hơn 1080p. Xem `FINAL_AUDIO_MEASUREMENT.txt` để đối chiếu âm lượng sau mã hóa.
- Nhạc và các tiếng chuyển chương được tổng hợp mới bằng dao động âm và nhiễu lọc; không lấy nhạc từ video tham chiếu. Nhạc này mang tính nền ambient đơn giản.
- Các giọng là giọng tổng hợp có sẵn mà Melo liệt kê cho từng ngôn ngữ, không phải nhân bản giọng người đọc gốc. Bản dịch được hỗ trợ bằng mô hình và kiểm tra các dữ kiện chính; vẫn cần người thành thạo ngôn ngữ nghe duyệt phát âm và cách diễn đạt trước khi phát hành.

## Trạng thái bàn giao

ZIP là bộ sản xuất và tự động hóa tại máy bạn. Nó **không phải MP4 đã hoàn tất**. Chỉ khi Muse trả về media thật và bước dựng chạy xong mới có video. Các kiểm thử của bộ dựng dùng media tổng hợp có nhãn TEST, không được tính là cảnh Muse.
