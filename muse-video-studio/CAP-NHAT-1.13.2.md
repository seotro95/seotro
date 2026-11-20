# Muse AI Studio 1.13.2 — song song trong cùng chat và tự chuyển tuần tự

Bản Windows x64 đầy đủ, không cần bản cũ, Node.js hoặc Chrome cài riêng. Giải nén toàn bộ ZIP vào thư mục mới, đóng bản cũ rồi mở **Muse AI Studio.exe** hoặc **BAT_DAU.bat**. Tài khoản, kịch bản và thư viện tiếp tục ở `%LOCALAPPDATA%\Muse AI Studio`.

## Hành vi mới

- Vẫn chọn 1–10 ô cho mỗi tài khoản. Nếu Muse không có **New chat**, tool gửi nhiều tin nhắn liên tiếp trong **cùng cuộc trò chuyện**, không đợi video trước hoàn tất. Chỉ khóa thao tác nhập/gửi để các prompt không ghi đè nhau; các tác vụ chờ kết quả đồng thời.
- Với chế độ cùng chat, tối đa 6 yêu cầu đang xử lý theo thông tin hạn mức bạn cung cấp: chọn 2–6 thì gửi tương ứng, chọn 10 giữ đủ 10 ô và chạy 6 ô cùng lúc, ô xong nhường chỗ cho ô chờ. Nếu Muse hỗ trợ hội thoại riêng, chế độ đó vẫn được giữ.
- Mỗi yêu cầu có mã tệp riêng để nhận đúng kết quả dù các phản hồi xen kẽ. Tên tải về vẫn dùng tên TXT/SRT của bạn. Kết quả chưa xác định được ô không bị gán theo thứ tự đoán.
- Không dùng được cả chế độ cùng chat và các trang riêng, không dùng được phiên đăng nhập trong trang luồng riêng hoặc lỗi trước khi gửi: tự chuyển tài khoản đó về một luồng. Các ô còn lại chờ và tiếp tục lần lượt, giữ số ô, thứ tự, tên tệp và prompt.
- Chế độ tuần tự dùng ngay trang Muse đã đăng nhập, kể cả khi đang chọn chế độ một tài khoản. Không bắt buộc trang chạy phụ phải xác thực được mới chạy tiếp.
- Lỗi xảy ra sau khi chuẩn bị song song: đợi các yêu cầu đang hoạt động kết thúc rồi chạy phần chưa gửi theo một luồng. Tác vụ chưa gửi chỉ được tự thử lại một lần. Khi Muse báo rõ không nhận vì giới hạn tác vụ đồng thời, thử lại một lần ở chế độ tuần tự.
- Prompt đã gửi mà chưa rõ kết quả hoặc bị lẫn hội thoại không bị tự gửi lại. Ô đó giữ lỗi để kiểm tra lịch sử Muse; các ô chưa gửi tiếp tục tuần tự.
- Giữ số luồng yêu cầu trong thiết lập, hiển thị số luồng thực tế và thông báo tự chuyển. Tài khoản khác vẫn chạy theo số luồng riêng. Có thể bấm **Kiểm tra luồng** để thử lại song song; khởi động lại cũng thử lại theo lựa chọn.
- Dừng riêng một ô chỉ hủy ô đó trong hàng chờ; Dừng tất cả hủy cả lượt. Không bỏ bớt kịch bản khi chuyển tuần tự.

Nhận tên TXT/SRT dạng `[1] nam`, `[4]thang`, `[ 1 ] tên`, tên khi tải, bộ đếm không tên, IP proxy và khôi phục Studio vẫn được giữ.

## Kiểm tra

Kiểm thử Chromium/Electron với dịch vụ mô phỏng: một tài khoản/một trang, 2 yêu cầu đến trước kết quả đầu tiên; 10 ô giữ tối đa 6 yêu cầu và ghép đúng ảnh trả lệch thứ tự; hủy một ô giữ chỗ cho tác vụ Muse đã nhận đến khi kết thúc; 2/10 ô không mở được hội thoại mới hoặc không xác thực được trang phụ; lỗi cả nhóm trước Enter; Muse từ chối vì giới hạn đồng thời; chuyển tuần tự giữ đủ kết quả; không phát lại yêu cầu đã gửi nhưng chưa rõ kết quả. Kiểm tra lại luồng song song, tên TXT/SRT, proxy, khởi động và EXE đóng gói trên Windows.

Chưa dùng tài khoản hoặc credit Muse thật trong kiểm thử. Muse quyết định giới hạn và thời gian xử lý thực tế.
