# Defender detection review dossier

Prepared for review; **not submitted to Microsoft**. This document is not a clearance decision.

## Submission status

The owner authorized submission of the original ZIP including its two voice recordings. Authorization is recorded; it is not evidence of a successful upload.

[Portal prerequisite inspection](https://github.com/seotro95/seotro/actions/runs/39457312285) reached the official portal over HTTPS. Selecting the software-developer reporter role and continuing redirected the anonymous browser to `https://login.microsoftonline.com/common/oauth2/v2.0/authorize`, titled **Sign in to your account**, with email/password fields and no file picker. No account information was entered, no challenge was solved and no file was uploaded. **No Microsoft submission ID exists.**

An authenticated reporter must complete submission through Microsoft's supported portal. This automation cannot use the owner's separate browser session and must not bypass sign-in, reuse platform identities or request passwords in chat. The locally running cloud machine also still receives proxy CONNECT 403 for the portal even though its editable draft now permits unrestricted Internet; the draft was preserved without narrowing it.

### Text ready for the review description

```text
Please investigate a possible incorrect Microsoft Defender detection of our locally running text-to-speech source package. We are requesting assessment, not asserting that the package is safe.

File: Hmoob-VoiceLab-1.0-source.zip
SHA-256: 962f0ac81867b4a84eff637a68c196b310723cd3b8a6eedc8679c15132259b1d
Size: 1,018,139 bytes
Reported detection: Trojan:Script/Ulthar.A!ml (Severe; Removed)
Source release commit: ae23a93222a1b3eeb8246eb6f45e527edc08fd6c in github.com/seotro95/seotro

The exact same ZIP was scanned with current Microsoft Defender on Windows Server 2022. The signed scanner returned exit code 0 and "found no threats" in a vendor-documented custom analysis scan. No application/installer code was executed. This does not resolve the original device's cloud/ML detection.

Evidence: https://github.com/seotro95/seotro/actions/runs/39454696183
Full dossier: https://github.com/seotro95/seotro/blob/main/hmoob-voicelab/MICROSOFT-REVIEW.md

Please identify the triggering archive member/content and determine whether this is malicious or an incorrect detection. If corrected, please specify the security-intelligence version carrying the correction. Distribution remains suspended pending review.
```

## Reported detection

- Product: Microsoft Defender Antivirus on the user's Windows device.
- Detection: `Trojan:Script/Ulthar.A!ml`.
- Severity/status shown in the user's screenshot: Severe / Removed.
- Archive: `Hmoob-VoiceLab-1.0-source.zip`.
- SHA-256: `962f0ac81867b4a84eff637a68c196b310723cd3b8a6eedc8679c15132259b1d`.
- Size: 1,018,139 bytes; 27 archive members.
- Repository: `seotro95/seotro` on GitHub.
- Release commit: `ae23a93222a1b3eeb8246eb6f45e527edc08fd6c`.

## Scope and provenance

The GitHub download and local archive were compared byte for byte. Archive contents matched the release source. It contains Python, BAT/shell scripts, JavaScript/HTML/CSS, text documentation and two MP3 voice recordings; no EXE, DLL, installed Python dependencies or AI model weights. The application is a local text-to-speech editor, with optional Python dependency/model installation. Static review found no concrete malicious behavior, but this does not establish safety or a false positive.

The original ZIP was withdrawn from the current main branch. A copy is retained locally as evidence; no replacement archive was published to evade detection. Source and Git history remain available for analysis.

## Independent Windows scan

- [GitHub Actions run 39454696183](https://github.com/seotro95/seotro/actions/runs/39454696183).
- Runner: Windows Server 2022, Microsoft Defender on-demand engine.
- Microsoft Authenticode scanner signature, fresh security intelligence, installed scanner help and official analysis-mode semantics were verified by the workflow before materializing the sample.
- The original Git blob and written ZIP were SHA-256 checked against the exact hash above.
- Custom analysis scan, with no changes to Defender preferences or exclusions; application/installer code was never executed.
- Native exit code: 0. Console: `Scan starting...`, `Scan finished.`, `Scanning ...\Hmoob-VoiceLab-1.0-source.zip found no threats.`
- Report artifact: `voicelab-defender-report`, containing `report.json`, stdout/stderr and the verified vendor reference/help. It contains no evidence ZIP or voice recordings.

This result is limited to the hosted scan. It does not dismiss the original device's cloud/ML detection. The exact file/member triggering that device's detection is not yet known.

## Requested assessment

Determine whether the archive/member is malicious or a false detection, identify the triggering content where possible, and specify any corrected detection/signature version. No user should restore or run the quarantined archive based on this dossier.

The original ZIP includes two voice recordings. The owner has explicitly authorized sending them as part of this sample to Microsoft. No submission has been made because interactive reporter sign-in is still required. Official Microsoft submission portal: https://www.microsoft.com/en-us/wdsi/filesubmission . Do not restore a blocked file or disable protection to prepare a submission.
