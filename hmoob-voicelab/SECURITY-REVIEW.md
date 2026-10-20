# Điều tra cảnh báo của Windows Defender

**Trạng thái: chưa giải quyết; tạm ngừng phát hành ZIP 1.0.**

Người dùng cung cấp ảnh Windows Security → Protection history cho thấy:

- Tên phát hiện: `Trojan:Script/Ulthar.A!ml`.
- Mức độ hiển thị: Severe.
- Trạng thái: Removed.
- Tệp bị ảnh hưởng: `Hmoob-VoiceLab-1.0-source.zip`, tải từ repository này.

Không khôi phục/cho phép tệp bị chặn, tắt antivirus hoặc đổi tên/định dạng tệp để vượt cảnh báo. Chưa có kết luận đây là cảnh báo nhầm. Các kiểm thử chức năng trước đó không phải kiểm thử antivirus.

## Bằng chứng đã kiểm tra

- Gói phát hành ở commit `ae23a93222a1b3eeb8246eb6f45e527edc08fd6c`.
- SHA-256: `962f0ac81867b4a84eff637a68c196b310723cd3b8a6eedc8679c15132259b1d`.
- Kích thước: 1.018.139 byte; ZIP gồm 27 tệp, không trùng tên, không có đường dẫn thoát thư mục.
- Đã tải lại chính tệp GitHub và đối chiếu: khớp byte với gói phát hành cục bộ. Các tệp bên trong khớp mã nguồn ở commit phát hành.
- Gói không kèm EXE, DLL, thư viện đã cài hoặc trọng số AI. Có Python, JavaScript/HTML/CSS, BAT/shell, tài liệu và hai mẫu MP3.
- Rà soát tĩnh không tìm thấy hành vi mã độc cụ thể: không có PowerShell/encoded command, thay đổi antivirus/registry, persistence hoặc `shell=True`. Đây là phạm vi kiểm tra mã nguồn, không phải bảo đảm an toàn.
- Bộ cài tạo venv, dùng pip để cài phụ thuộc và bộ tải mô hình Hugging Face có kiểm tra checksum. Phụ thuộc và trọng số tải sau không nằm trong gói ZIP bị Defender chặn; chúng cần đánh giá riêng.

## Phần chưa hoàn tất

Máy Linux hiện không có antivirus/signature database cài sẵn. Truy cập hai tệp chữ ký chính thức `https://database.clamav.net/daily.cvd` và `https://database.clamav.net/main.cvd` bị proxy từ chối CONNECT 403, nên chưa có kết quả quét ClamAV. Không dùng nguồn chữ ký không rõ, không bỏ xác minh và không gửi mẫu giọng/tệp của người dùng đến dịch vụ quét bên ngoài.

Cần đánh giá bởi Microsoft hoặc một môi trường Windows có Defender cập nhật để xác định tệp/quy tắc gây phát hiện và hướng xử lý phù hợp. Trang gửi tệp chính thức của Microsoft: https://www.microsoft.com/en-us/wdsi/filesubmission . Chưa có tệp được gửi và chưa có kết luận từ Microsoft.

ZIP được gỡ khỏi nhánh `main` để dừng cung cấp bản tải hiện tại. Lịch sử Git và bộ nhớ đệm bên ngoài có thể còn giữ bản cũ. Không tạo gói khác để né phát hiện; chỉ phát hành lại sau khi giải quyết được cảnh báo và có bằng chứng kiểm tra phù hợp.

## Kiểm tra Windows trên GitHub

Workflow [Investigate VoiceLab Defender detection](https://github.com/seotro95/seotro/actions/workflows/voicelab-defender.yml) quét bằng Defender trên Windows Server 2022. Nó chỉ đọc bản ZIP gốc từ commit phát hành, đối chiếu SHA-256 rồi yêu cầu quét; không chạy tool hoặc bộ cài, không thay đổi cấu hình Defender và không tải lại ZIP làm artifact.

Máy GitHub có sẵn các exclusion và tắt quét archive thông thường. Vì vậy workflow xác minh chữ ký Microsoft của `MpCmdRun.exe`, trợ giúp của đúng phiên bản đã cài và nội dung [tài liệu chính thức](https://learn.microsoft.com/en-us/defender-endpoint/command-line-arguments-microsoft-defender-antivirus) trước khi dùng `-DisableRemediation` cho lượt custom scan trong môi trường kiểm tra. Theo tài liệu đã xác minh trên runner, chế độ phân tích này bỏ qua file exclusions, quét archive và không thực hiện remediation. Không có preference, exclusion hoặc bảo vệ thời gian thực nào bị thay đổi. Không dùng việc thiếu sự kiện phát hiện làm bằng chứng an toàn, vì chế độ này không ghi các sự kiện thông thường.

Kết quả trong `voicelab-defender-report/report.json`: `detection-reported` (có phát hiện), `no-detection-on-this-runner` (lượt quét trên runner này không báo phát hiện), hoặc `indeterminate` (không đủ điều kiện/bằng chứng quét). Không có chữ ký scanner hợp lệ, thiếu bằng chứng semantics từ nhà cung cấp, sai hash, engine không hoạt động, chữ ký dữ liệu cũ hoặc lỗi quét đều không được coi là kết quả không phát hiện.

### Kết quả đã chạy

[Lượt quét Windows số 39454696183](https://github.com/seotro95/seotro/actions/runs/39454696183) hoàn tất trên chính ZIP có SHA-256 nêu trên. Scanner trả mã 0 và ghi:

```text
Scan starting...
Scan finished.
Scanning ...\Hmoob-VoiceLab-1.0-source.zip found no threats.
```

Đây là kết quả **không phát hiện trong lượt quét này**, không phải quyết định của Microsoft rằng cảnh báo trên máy người dùng là nhầm. Ngữ cảnh tải về, chính sách cloud và phiên bản Windows/Defender có thể khác. Cảnh báo `Trojan:Script/Ulthar.A!ml` trên máy người dùng chưa được giải quyết; ZIP vẫn không được phát hành lại.

Bước tiếp theo là cập nhật security intelligence trên máy người dùng và yêu cầu Microsoft thẩm định mẫu/cảnh báo trước khi xem xét phát hành lại. Giữ nguyên trạng thái Removed; không khôi phục, cho phép hoặc tắt bảo vệ để thử. [Hồ sơ thẩm định đã chuẩn bị](MICROSOFT-REVIEW.md) chứa thông tin nhận dạng mẫu và bằng chứng quét. Chưa gửi mẫu cho Microsoft hoặc dịch vụ quét bên ngoài.
