# Defender detection review dossier

Prepared for review; **not submitted to Microsoft**. This document is not a clearance decision.

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

The original ZIP includes two voice recordings. External sample submission requires the owner's explicit authorization and a supported submission route; none has been made. Official Microsoft submission portal: https://www.microsoft.com/en-us/wdsi/filesubmission . Do not restore a blocked file or disable protection to prepare a submission.
