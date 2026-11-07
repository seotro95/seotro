# API điều khiển Muse AI Studio 1.8.0

Cổng này điều khiển cửa sổ Studio đang mở trên **cùng máy tính**. Không cần mở trang Muse, sao chép cookie hay cài Node.js để gọi API. Đăng nhập Muse trong Studio trước khi dùng chế độ tạo nội dung thật.

## Bật cổng

1. Mở `Muse AI Studio.exe`, bấm **Cổng API**.
2. Giữ cổng `8790` hoặc chọn cổng trống từ 1024–65535, bấm **Bật / Áp dụng cổng**.
3. Bấm **Sao chép khóa**, đặt vào cấu hình công cụ gọi API. Mọi endpoint cần header `Authorization: Bearer <khóa>`.
4. Địa chỉ mặc định: `http://127.0.0.1:8790`. Chỉ lắng nghe loopback. Không cần mở firewall hoặc chuyển tiếp cổng router.

Cấu hình bật/tắt, cổng và khóa được giữ trên máy khi mở lại Studio. **Đổi khóa API** thu hồi khóa cũ; **Tắt cổng API** ngừng nhận kết nối. API không cung cấp cookie, mã OTP, mật khẩu Muse hoặc chức năng đăng nhập từ xa. Nếu Studio đang tải, trả 503; đợi rồi đọc trạng thái.

## Endpoint

| Phương thức | Đường dẫn | Chức năng |
| --- | --- | --- |
| GET | `/v1/status` | Thiết lập, batchId hiện tại, tiến độ từng ô, tài khoản đã xác minh và danh sách media |
| POST | `/v1/batches` | Nạp và bắt đầu một bộ 1–40 prompt/TXT/SRT |
| POST | `/v1/save` | Lưu bộ kết quả vào thư mục đã chọn trong Studio, có thể lọc batchId/output/sceneIds |
| POST | `/v1/stop` | Dừng cả bộ (`{}`) hoặc một ô (`{"sceneId":2}`) |
| GET | `/v1/media` | Danh sách ảnh/video đã lưu, ID và đường dẫn tải |
| GET | `/v1/media/<id>` | Byte ảnh/video với MIME và phần mở rộng đúng |
| DELETE | `/v1/media` | Xóa toàn bộ thư viện; body phải là `{"confirm":"DELETE_ALL_MEDIA"}` |

Các yêu cầu có body dùng `Content-Type: application/json`, UTF-8. Tối đa 12 MB mỗi yêu cầu. Đọc media không cần gửi lại prompt. 401: thiếu/sai khóa; 400: dữ liệu không hợp lệ; 409: Studio đang bận hoặc chưa đủ kết nối; 429: quá nhiều yêu cầu; 503: cửa sổ Studio chưa sẵn sàng. Phản hồi lỗi có `{ "error": "..." }`.

API dành cho ứng dụng/script trên cùng máy; trang web chạy trong trình duyệt khác không được cấp CORS. Dùng HTTP client trong backend, Python, PowerShell, n8n cài trực tiếp trên máy hoặc ứng dụng tương tự. Với công cụ chạy trong container/máy ảo, loopback của nó khác loopback Windows; bản này không mở cổng ra mạng LAN.

## Tạo bộ

```json
{
  "output": "image",
  "prompts": ["Khu rừng lúc bình minh", "Ngôi làng trên đỉnh núi"],
  "settings": {
    "accountMode": "single",
    "aspectRatio": "16:9",
    "imageResolution": "2k",
    "r2v": false
  }
}
```

Trả **202** với `{ "batchId": "...", "sceneIds": [1,2] }` sau khi Studio nhận và bắt đầu bộ. Đây chưa phải kết quả đã tạo xong. Poll `GET /v1/status`, xem `busy`, trạng thái từng ô và `imageId`/`videoId`, rồi tải media. Kết quả mới có `batchId` trong danh sách media để đối chiếu đúng bộ, kể cả khi giao diện đã bắt đầu một bộ khác. API và giao diện dùng cùng lịch sử, nút Dừng và hạn mức xử lý.

Chỉ nhận bộ mới khi Studio không có tác vụ đang chạy. Bộ mới nạp prompt và thiết lập, bật những ô được yêu cầu, tắt các ô còn lại; kết quả trước vẫn có trong lịch sử. Mặc định prompt gán vào ô 1,2,…; có thể gửi `sceneIds`, ví dụ `[3,7]` với hai prompt. Ở chế độ `multiple`, ô 3 dùng tài khoản Muse 03 và ô 7 dùng Muse 07; tất cả tài khoản cần cho bộ phải đã xác minh.

Thay `prompts` bằng `script` để gửi nguyên nội dung TXT/SRT UTF-8. TXT tách dòng/đoạn, SRT tự bỏ số thứ tự và mốc thời gian; tối đa 40 cảnh. Không gửi cả `prompts` và `script` cùng lúc.

`GET /v1/status` trả thêm `slotCount`, `requestedConcurrency`, `executionConcurrency` và `concurrencyWarning` để phân biệt số ô/yêu cầu với khả năng thực tế. Bộ mới có ID ô cao hơn sẽ tự mở thêm ô, tối đa 40.

`output`: `image` hoặc `video`. Các mục `settings` được phép:

- `slotCount`: số ô từ 1–40; `requestedConcurrency`: số luồng yêu cầu từ 1–40.
- `accountMode`: `single` hoặc `multiple`.
- `mode`: `muse` (tạo thật qua phiên đã xác minh) hoặc `demo` (tệp mẫu có nhãn, không tạo AI).
- `model`: `Omni 1.1 Flash`, `Veo 3.1 - Lite`, `Veo 3.1 - Fast`; Veo yêu cầu 8 giây.
- `aspectRatio`: `16:9`, `9:16`; `duration`: 4,6,8,10.
- `resolution`: `360p`, `720p`, `1080p`, `2k`, `4k`; `imageResolution`: `2k`, `4k`.
- `videoInput`: `text` hoặc `image`; `r2v`, `autoSync`: boolean; `modifier`: chuỗi tối đa 2.000 ký tự.

Các thiết lập bỏ qua giữ theo Studio hiện tại. Với video từ ảnh, gửi `sourceMediaId` là ID của ảnh đã có trong thư viện, hoặc `referenceImage:{"mimeType":"image/png","base64":"..."}` (PNG/JPEG/WebP, tối đa 8 MB). Ảnh này áp dụng cho các ô được yêu cầu. Không truyền đường dẫn máy tính hoặc URL vào trường ảnh. Với ảnh mới không có reference, tool không tự dùng ảnh tham chiếu còn lại từ bộ trước.

## Tránh chạy trùng

Gửi header `Idempotency-Key` khác nhau cho mỗi bộ, ví dụ một UUID. Khi cùng khóa và cùng nội dung được gửi lại trong một phiên mở tool, Studio trả lại batchId đã nhận mà không khởi chạy thêm. Cùng khóa với nội dung khác trả 409. Tối đa giữ 128 yêu cầu gần đây trong RAM; bộ nhớ này mất khi đóng tool hoặc đổi khóa API. Không tự gửi lại bộ khi timeout: kiểm tra trạng thái/lịch sử trước, nhất là sau khi khởi động lại.

## PowerShell trên Windows

Đặt khóa đã sao chép trong biến môi trường `MUSE_STUDIO_KEY` của công cụ đang gọi. Ví dụ sau gửi hai prompt; UTF-8 được chỉ định để giữ tiếng Việt trên Windows PowerShell.

```powershell
$studioBase = 'http://127.0.0.1:8790'
$studioHeaders = @{ Authorization = "Bearer $env:MUSE_STUDIO_KEY" }
Invoke-RestMethod "$studioBase/v1/status" -Headers $studioHeaders

$studioHeaders['Idempotency-Key'] = [guid]::NewGuid().ToString()
$studioBody = @{
  output = 'image'
  prompts = @('Khu rừng lúc bình minh', 'Ngôi làng trên núi')
  settings = @{ accountMode = 'single'; imageResolution = '2k' }
} | ConvertTo-Json -Depth 6
Invoke-RestMethod "$studioBase/v1/batches" -Method Post -Headers $studioHeaders `
  -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($studioBody))

# Khi đã hoàn tất: tải một kết quả, dùng phần mở rộng đúng loại media.
$studioMedia = (Invoke-RestMethod "$studioBase/v1/media" -Headers $studioHeaders).media[0]
$studioExt = @{ 'image/png'='png'; 'image/jpeg'='jpg'; 'image/webp'='webp'; 'video/mp4'='mp4'; 'video/webm'='webm'; 'video/quicktime'='mov' }[$studioMedia.mimeType]
Invoke-WebRequest ($studioBase + $studioMedia.download) -Headers $studioHeaders `
  -OutFile ("scene-" + $studioMedia.sceneId + "-" + $studioMedia.id + "." + $studioExt)
```

Để nạp tệp, thay trường `prompts` trong body bằng `script = Get-Content 'D:\kich-ban.srt' -Raw -Encoding UTF8`.

## Python (thư viện chuẩn)

```python
import json, os, uuid, urllib.request
base = 'http://127.0.0.1:8790'
headers = {
    'Authorization': 'Bearer ' + os.environ['MUSE_STUDIO_KEY'],
    'Content-Type': 'application/json',
    'Idempotency-Key': str(uuid.uuid4()),
}
body = json.dumps({
    'output': 'image',
    'prompts': ['Khu rừng lúc bình minh', 'Ngôi làng trên núi'],
    'settings': {'accountMode': 'single', 'imageResolution': '2k'},
}, ensure_ascii=False).encode('utf-8')
request = urllib.request.Request(base + '/v1/batches', data=body, headers=headers)
with urllib.request.urlopen(request, timeout=130) as response:
    print(json.load(response))
```

## Xóa thư viện

Nút **Xóa toàn bộ** trong Studio có bước xác nhận. API yêu cầu chuỗi xác nhận như bảng endpoint. Chỉ xóa kết quả/lịch sử trong thư viện tool; giữ prompt, tài khoản, ảnh tham chiếu và bộ đếm tải. Tệp đã xuất ra thư mục máy tính không bị xóa. Không cho xóa khi đang tạo hoặc tải bộ để tránh kết quả xuất hiện lại ngay sau khi xóa.

Chế độ một tài khoản mặc định kiểm tra hai hội thoại riêng trước lần tạo đầu. Khi đủ khả năng, gửi hai yêu cầu cùng lúc và xếp những ô còn lại chờ hai chỗ trống. Nếu Muse không cung cấp hội thoại riêng, giữ đủ ô đã chọn và trả `executionConcurrency:1` kèm cảnh báo; bộ vẫn chạy hàng đợi một luồng. Chỉ lỗi đăng nhập/kết nối mới từ chối bộ. Có thể chủ động chọn 1 luồng trong Studio. Tốc độ render và khả năng thực tế do Muse quyết định. Chế độ nhiều tài khoản vẫn giới hạn một yêu cầu trên mỗi tài khoản.

## Bộ kết nối MCP cho Codex cùng máy

`POST /mcp` dùng cùng khóa Bearer, hỗ trợ initialize, tools/list và tools/call qua MCP Streamable HTTP. Có các công cụ studio_status/configure_layout/set_scene/create_batch/run/stop/list_media/save_results/clear_library. Xem MCP-CODEX.md để thêm vào Codex; mẫu cấu hình không chứa khóa. Lệnh tạo hỗ trợ requestId để tránh lặp; lệnh lưu trả thư mục/tệp, không đưa byte video lớn vào hội thoại.
