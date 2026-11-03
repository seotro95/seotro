# 10-Slot Video Workstation & Character Sync Studio

Bản web React/TypeScript dựng theo ảnh và bản mô tả Flow do người dùng cung cấp. Chạy độc lập trên máy tính, giao diện tiếng Việt, 10 cảnh, chủ đề slate/indigo. **Không dùng Gemini.**

## Tình trạng kết nối Muse AI

**Chưa kết nối hoặc đăng nhập tài khoản Muse.ai thực tế. Chưa kiểm chứng tạo video AI.** URL người dùng cung cấp là `https://muse.ai/`. Môi trường phát triển hiện bị proxy từ chối truy cập URL này (CONNECT 403). Chưa có tài liệu chứng minh API của dịch vụ đó hỗ trợ `Omni 1.1 Flash`, `Veo 3.1 - Lite`, `Veo 3.1 - Fast` hay R2V theo prompt Flow.

Người dùng đã xác nhận: **Flow tự tạo video, chưa kiểm tra Muse.ai**. Tên mô hình trong giao diện lấy từ bản mô tả, không phải xác nhận nhà cung cấp Muse.ai có các mô hình đó. Muse.ai được biết đến là nền tảng lưu trữ/tìm kiếm video; cần xác minh tính năng tạo video và phương thức xác thực chính thức trước khi tích hợp. Không thể chuyển SDK của một tool Flow sang web độc lập chỉ bằng cách nhập 10 email.

Đã chuẩn bị adapter phía máy chủ để nối dịch vụ tạo video khi có hợp đồng API thật. Adapter này là **giao thức của ứng dụng này**, không phải Muse.ai SDK và không tự triển khai đăng nhập/OAuth, lấy cookie hoặc gọi API riêng chưa được công bố. Chưa có adapter Muse.ai thực tế trong gói.

## Chạy trên máy tính

Cài **Node.js 24 LTS trở lên** từ https://nodejs.org/. Mở thư mục này:

```sh
npm ci
npm run build
npm start
```

Windows: chạy `start.bat`. Linux/macOS: `bash start.sh`. Launcher tự cài thư viện nếu còn thiếu; lần đầu cần Internet đến registry.npmjs.org. Bản ZIP đi kèm có sẵn `dist`, có thể bỏ bước build khi chỉ muốn chạy. Các lệnh trên đã được thử trên Linux; launcher Windows chưa chạy trên Windows thật.

Máy chủ in địa chỉ cục bộ (mặc định cổng 8788). Mở địa chỉ đó bằng trình duyệt trên cùng máy, giữ cửa sổ máy chủ mở; Ctrl+C để dừng. Không mở `index.html` trực tiếp bằng `file://`. Máy chủ chỉ lắng nghe loopback. Các bước khởi động cần lặp lại sau khi khởi động lại máy; tiến trình không nằm trong ZIP/snapshot.

Phát triển: `npm run dev`. Sau khi sửa nguồn, chạy lại `npm run build` để cập nhật bản production.

## Các thao tác đã triển khai

- 10 slot responsive (5 cột trên desktop, 3 cột ở tablet, 2/1 cột trên điện thoại); email sửa inline; bật/tắt từng tài khoản.
- Chọn ảnh PNG/JPG/WebP tối đa 8 MB, ảnh chung tự đồng bộ 10 cảnh, ảnh riêng từng cảnh, dùng lại ảnh chung và gỡ ảnh.
- Chọn mô hình, tỉ lệ, thời lượng và độ phân giải. Veo cố định 8s/720p; Omni có 4/6/8/10s và 360/720p theo mô tả nguồn.
- Nhập TXT/SRT UTF-8 tối đa 2 MB, loại timestamp và số thứ tự SRT, xem trước, 2 kịch bản mẫu. Quá 10 cảnh thì yêu cầu rút gọn; không âm thầm bỏ nội dung. Ít hơn 10 cảnh thì các ô còn lại được xóa prompt.
- Hàng đợi tuần tự, bỏ cảnh đã hoàn tất/tài khoản tắt, tạo lại một cảnh, dừng và tiếp tục, tiến độ, hiển thị lỗi thô và gợi ý. Không gửi thêm yêu cầu nếu chưa có kết nối.
- Video Blob URL, player thật, tải từng video và tải tất cả tuần tự. Trình duyệt có thể hỏi quyền tải nhiều tệp.
- AI Enhance, modifier chung và render thử gọi qua adapter AI; lỗi rõ ràng khi chưa có kết nối. Render thử có thể tốn credit và cần đánh dấu đồng ý. Không đoán credit/GPU nếu API không cung cấp.
- Tự lưu prompt, nhãn email, trạng thái bật/tắt và settings trong localStorage; mở/xuất JSON dự án.

Ảnh, video và lỗi chỉ giữ trong bộ nhớ phiên, không lưu cùng dự án. Tải video cần giữ thì thực hiện trước khi đóng trang. Chỉnh prompt/ảnh/settings sẽ xóa kết quả cũ để tránh tải nhầm video không khớp. Đổi email hoặc trạng thái bật/tắt không xóa video. Email mẫu `@muse.local` là nhãn ban đầu, không phải tài khoản được cấp.

## Kiểm thử khi chưa có tài khoản

Mở **Chẩn đoán API → Kiểm thử giao diện**. Chế độ này dùng clip 4s/360p/16:9 có nhãn `TEST CLIP - NOT AI GENERATED`, giống nhau ở mọi cảnh; không sinh nội dung theo prompt, không sử dụng ảnh nhân vật, không trau chuốt bằng AI, không tiêu credit. Dùng để thử player, tải và điều phối hàng đợi.

## Kết nối adapter Muse phía máy chủ

Chỉ dùng sau khi đã có một dịch vụ adapter triển khai API tạo video và xác thực được tài khoản Muse theo phương thức nhà cung cấp hỗ trợ. Không trỏ URL adapter trực tiếp tới trang chủ Muse.ai.

1. Sao chép `.env.example` thành `.env`.
2. Đặt `MUSE_ADAPTER_URL` là URL gốc của adapter tương thích (HTTPS, hoặc HTTP loopback khi phát triển). `MUSE_ADAPTER_TOKEN` là bearer token đến adapter nếu adapter yêu cầu. Không đưa token vào URL.
3. Adapter giữ thông tin xác thực và ánh xạ `accountId` 1–10 đến tài khoản thật. Email trong UI chỉ là nhãn; không gửi mật khẩu/cookie từ trình duyệt.
4. Khởi động lại máy chủ. Chọn kết nối **Muse AI API · Web độc lập**. “Đã khai báo” chỉ xác nhận đã cấu hình URL; dùng render thử để xác minh quyền và tính năng thật.

Backend gọi `POST {MUSE_ADAPTER_URL}/video`:

```json
{
  "accountId": 1,
  "prompt": "Scene prompt\n\nGlobal modifier",
  "modelDisplayName": "Omni 1.1 Flash",
  "aspectRatio": "16:9",
  "durationSeconds": 4,
  "resolution": "360p",
  "referenceImage": {"base64": "...", "mimeType": "image/png"}
}
```

`referenceImage` được bỏ nếu không có ảnh hoặc tắt R2V. Adapter tự upload/chuyển ảnh sang mediaId của dịch vụ và kiểm tra hỗ trợ R2V. Trả về khi render hoàn tất: `{"base64":"...","mimeType":"video/mp4"}`. Các MIME hỗ trợ: MP4, WebM, QuickTime. Giới hạn phản hồi 150 MB, timeout 10 phút. Adapter chịu trách nhiệm polling nếu API upstream là bất đồng bộ. Lỗi: HTTP 4xx/5xx với `{"error":"mã lỗi và mô tả"}`; không đưa bí mật vào lỗi.

Backend gọi `POST {MUSE_ADAPTER_URL}/text` với `{"accountId":1,"prompt":"enhancement instruction..."}`, kỳ vọng `{"text":"rewritten English scene..."}`. Nếu tài khoản không có AI văn bản thì adapter cần trả lỗi rõ, không giả lập Enhance thành công.

Nếu đặt token, backend thêm `Authorization: Bearer ...` khi gọi adapter. Secret không gửi ra frontend hoặc lưu vào dự án. Node chạy với `--use-env-proxy`, giữ proxy/TLS của môi trường. Không cần key Gemini. Dừng hàng đợi ngừng chờ và không gửi cảnh tiếp; không đảm bảo upstream hủy tác vụ đã gửi hoặc hoàn credit.

## Chế độ Flow SDK tùy chọn

Chỉ dùng trong runtime thực sự cung cấp `window.Flow`. Không tìm thấy SDK thì trả lỗi, không giả vờ kết nối. Hợp đồng trong `src/provider.ts` dựa trên prompt người dùng, **chưa xác minh với SDK Flow thực tế**:

- `Flow.media.select({filter:'image'})` → `{mediaId, url?, name?}` hoặc mảng như vậy.
- `Flow.generate.video({prompt, modelDisplayName, referenceImageMediaIds, aspectRatio, durationSeconds, resolution})` → `{base64, mimeType?}`.
- `Flow.generate.text({prompt})` → chuỗi hoặc `{text}`.
- `Flow.download({base64, mimeType, filename})`.

Chọn ảnh qua Flow để có `mediaId`. Chế độ SDK dùng phiên runtime hiện tại; không có chức năng chuyển 10 phiên đăng nhập dựa vào email. Nếu cấu trúc SDK thật khác, sửa adapter theo tài liệu được cung cấp.

## Kiểm tra

```sh
npm run build
npm test
npx playwright install chromium
npm run test:e2e
```

Nếu máy có Chromium hệ thống trên Linux: `CHROMIUM_PATH=/usr/bin/chromium npm run test:e2e`. Test trình duyệt bao gồm layout desktop/mobile, TXT/SRT, đồng bộ ảnh, payload Muse, phát/tải video, vô hiệu hóa kết quả cũ, thứ tự hàng đợi, tài khoản tắt, lỗi và hủy/tiếp tục. Test adapter dùng máy chủ giả cục bộ; không xác nhận đăng nhập, hạn mức, chất lượng AI hoặc R2V của Muse.ai.

Mỗi cloud task đã là môi trường riêng; dùng checkout sẵn có, không tạo Git worktree cho setup.
