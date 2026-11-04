# Xác minh bản 1.1.0

## Đã kiểm tra trên Linux

- `npm ci --cache /workspace/.cache/seotro-npm --no-audit --no-fund`: cài từ lockfile thành công, có Playwright Core ở dependencies runtime.
- `npm run build`: TypeScript và Vite thành công. Cảnh báo `use client` từ bộ icon trong ứng dụng client-only không ngăn build.
- `npm test`: 6 bài parser/state, 6 bài máy chủ adapter trong một nhóm, 3 bài lệnh mở trình duyệt đều qua; không bỏ qua bài nào.
- `CHROMIUM_PATH=/usr/bin/chromium npm run test:e2e`: **10/10** bài trình duyệt qua. Bao gồm kết nối/kiểm tra slot, chỉ bật slot đã xác minh, batch chỉ chạy đúng slot, hết phiên khóa tạo lại nhưng giữ video cũ, metadata video quan sát được, nhập SRT và đồng bộ ảnh.
- `CHROMIUM_PATH=/usr/bin/chromium npm run test:browser-bridge`: **7 kịch bản** cầu nối trong một nhóm qua. Dùng trang có giao diện tương tự Muse chạy trên loopback cùng Chromium và hồ sơ tạm.
- Các kịch bản cầu nối kiểm tra: không suy đoán đăng nhập từ thư mục; gửi prompt/ảnh và đọc video mới; AI văn bản chỉ lấy lượt mới; không ghi đè/chuyển hồ sơ khi có bản nháp; tách hồ sơ và mở lại phiên; không lấy video cũ khi lượt mới không trả video; giữ lỗi/dừng yêu cầu; kiểm tra lại phiên trước mọi lần gửi khi cookie giả lập hết hạn.
- Clip fixture đọc được metadata 640×360, 4 giây; dữ liệu video trả về đúng byte của clip. Đây là clip kiểm thử, không phải video AI được tạo trong lần kiểm tra.
- `node --check server.mjs`, `node --check muse-browser.mjs`, `bash -n start.sh` và kiểm tra whitespace của Git thành công.

## Chưa xác minh

- **Chưa đăng nhập hoặc tạo video thật trên Muse.ai.** Môi trường không có phiên tài khoản và proxy từ chối truy cập trực tiếp muse.ai (CONNECT 403). Cần người dùng đăng nhập bằng nút Kết nối trên máy chạy tool rồi thử một cảnh.
- Cầu nối trình duyệt là tích hợp không chính thức. Selector và `/api/auth/check` tham khảo từ client community; Muse có thể thay đổi chúng.
- Các model/thời lượng/khung hình được gửi dưới dạng yêu cầu trong prompt, chưa xác nhận Muse thực hiện chính xác. UI hiển thị metadata trả về; chưa xác minh được model đã dùng, chất lượng AI hoặc độ đồng nhất nhân vật.
- Chromium/headless trên trang giả lập không chứng minh đăng nhập Chrome/Edge trên Muse thật hoạt động. Launcher Windows chưa chạy trên Windows thật.
- Không đọc/xuất cookie hoặc token thật. Kiểm thử login dùng cookie tổng hợp trên máy chủ fixture cục bộ, không dùng tài khoản người dùng.
- Quy trình SDK ghép thiết bị của Muse không được triển khai; bản này chọn phương án đăng nhập qua cửa sổ trình duyệt riêng.
