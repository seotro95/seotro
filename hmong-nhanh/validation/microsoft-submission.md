# Microsoft Defender analysis request: Hmong Nhanh 0.8.1

Prepared on 2026-10-27. **Draft only; not submitted through Microsoft's analysis portal.** No Microsoft case number or final determination exists in this report. The controlled Defender scan below used cloud protection; it is not an analyst submission or final determination.

## Requested analysis

Please investigate Microsoft Defender Antivirus's `Trojan:Script/Ulthar.A!ml` detection on the two public source files below. They belong to a local Hmong text-to-speech application. A read-only source review has not identified malicious behavior in the flagged files, but this is not an antivirus verdict and does not establish that the detection is incorrect. Please determine whether the files are malicious, unwanted, or incorrectly classified, and identify any actionable issue if available.

## Observed report

- The user's browser blocked downloading `Hmong-Nhanh-da-sua.zip`.
- Windows Security Protection History shows detection `Trojan:Script/Ulthar.A!ml`, severity `Severe`, heading `Remediation incomplete`, and status `Failed`.
- The screenshot displays 10/27/2026 6:36 AM for the entry and 6:37 AM in its details; the device's timezone was not provided.
- Affected archive members are `Hmong-Nhanh/app/static/app.js` and `Hmong-Nhanh/app/static/index.html`.
- The screenshot's source URL pins the package to commit `70e9e208b61c6a5c7a846180ee96dec7e7373eda` in public repository `seotro95/seotro`.
- No execution of the downloaded application has been reported. This evidence does not establish that the user's device was compromised.
- The original device's Defender engine, platform and security intelligence versions, OS build, cloud protection settings, and downloaded-file hash were not supplied. Do not invent them in the submission form.

## Exact public samples

| Sample | Bytes | SHA-256 |
| --- | ---: | --- |
| `app.js` | 41,288 | `228237914853428524ad9c81417cbb9601b860127b41c7de19f96275185ece56` |
| `index.html` | 11,080 | `ba1257e173ec822b9b358bf04d2683debe86ec6d77b79b34e749612bf1bb463a` |
| Original `Hmong-Nhanh-da-sua.zip` | 2,449,762 | `6ef5e0c70ffc2bc744575c9d386cb3acf949dd8fce7390d073daea6659eefd24` |

The two local source files were compared byte-for-byte with their members in the original ZIP and matched. These hashes identify the published samples; the user device's downloaded bytes were not independently acquired.

- [Public JavaScript source](https://github.com/seotro95/seotro/blob/70e9e208b61c6a5c7a846180ee96dec7e7373eda/hmong-nhanh/app/static/app.js)
- [Public HTML source](https://github.com/seotro95/seotro/blob/70e9e208b61c6a5c7a846180ee96dec7e7373eda/hmong-nhanh/app/static/index.html)
- [Original archive, for analyst investigation only](https://raw.githubusercontent.com/seotro95/seotro/70e9e208b61c6a5c7a846180ee96dec7e7373eda/Hmong-Nhanh-da-sua.zip)

## Intended behavior and limited review

The browser interface lets a user enter/import text or subtitles, choose/upload a voice reference, start local speech synthesis, and play/download local audio results. The HTML loads local `/static/style.css` and `/static/app.js`. The reviewed JavaScript uses a single fetch wrapper whose callers use root-relative `/api` routes. Imported text is decoded locally, and selected voice files are posted to the local API following a user action. The reviewed rendering uses `textContent`, `value`, and `Option`, rather than an HTML parser sink. The source review found no `eval`, dynamic `Function`, encoded payload execution, shell invocation, credential collection, or external telemetry endpoint in these two files.

These source observations do not reproduce or refute the Microsoft detection. The separate measured scan below did not reproduce it in that environment; it does not replace the user's positive detection with a general claim that the application is safe.

## Controlled Defender scan

[GitHub Actions run 40450978700](https://github.com/seotro95/seotro/actions/runs/40450978700) scanned the exact three public samples above on Windows Server 2022 (OS version 10.0.20348.0), starting 2026-10-27 at 04:40:04 UTC and completing at 04:40:35 UTC. Recorded result: **`no_detection_in_this_scan`**.

| Component | Measured version |
| --- | --- |
| Defender engine | `1.1.26090.9` |
| Defender platform | `4.18.26090.9` |
| Security intelligence | `1.461.217.0` |
| GitHub runner image | `20261022.344.1` |

The diagnostic enabled archive, script, real-time, behavioral, and download scanning on the disposable runner, removed the runner's default path exclusions, and verified that each sample path was not excluded. It updated security intelligence, verified the scanner's Authenticode status, and successfully validated the MAPS cloud connection. `MpCmdRun -Scan -ScanType 3 -File` reported no threats for each sample. All three files remained present with identical SHA-256 hashes after scanning; threat history and relevant detection/remediation events contained no findings. The structured evidence is in `defender-report-2026-10-27.json` alongside this document.

This was a controlled file scan, **not** a reproduction of the user's Windows client and browser download flow. The application was not executed. The original device's security intelligence version and file bytes remain unknown. A scan with these settings and versions does not establish a false positive, a guarantee of safety, a Microsoft analyst determination, or that the user's download alert is resolved.

## Submission fields

- Role: **Software developer** when submitted by the maintainer.
- Product: **Microsoft Defender Antivirus**; select the original affected Windows version if known.
- Detection name: `Trojan:Script/Ulthar.A!ml`.
- Definition version: leave unspecified unless measured on the affected device.
- Additional information: use the accompanying `microsoft-submission-details.txt` (under the portal's 1,900-character limit).
- Samples: submit the two exact flagged source files individually. They contain no user voice recordings, private transcripts, or account data. Supply the original public archive URL as context; do not add unrelated application files to the initial sample.

Microsoft's [submission guide](https://learn.microsoft.com/en-us/defender-xdr/submission-guide) directs developers disputing a detection to submit the file as a software developer and wait for the final determination; it states that submission requires signing in. The [official submission portal](https://www.microsoft.com/en-us/wdsi/filesubmission) requests the specific files to analyze and provides a review step. The submitting account holder must review any sign-in, consent, and verification prompts. This draft does not grant consent or submit anything on the user's behalf.

## Hướng dẫn ngắn

Hồ sơ đã soạn sẵn, **chưa gửi qua cổng phân tích Microsoft**. Quét Defender trên Windows Server 2022 không phát hiện mối đe dọa trong ba tệp đã đối chiếu hash; **chưa xác nhận cảnh báo trên máy người dùng đã hết hoặc là báo nhầm**. Người duy trì ứng dụng có thể mở [cổng Microsoft](https://www.microsoft.com/en-us/wdsi/filesubmission), đăng nhập, chọn **Software developer**, gửi riêng hai tệp nguồn bị báo và dán nội dung tệp `microsoft-submission-details.txt`. Giữ nguyên chặn trên máy người dùng; không khôi phục tệp cách ly hoặc thêm ngoại lệ để lấy mẫu. Chờ kết luận cuối cùng của Microsoft trước khi gọi đây là cảnh báo nhầm.
