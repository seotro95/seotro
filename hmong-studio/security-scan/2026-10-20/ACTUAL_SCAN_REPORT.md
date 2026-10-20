# Actual antivirus scan report — 20 October 2026 UTC

**Both held ZIP files were scanned by ClamAV 1.4.3 with officially signed ClamAV databases. No detections were reported (exit code 0). This is a ClamAV result, not Microsoft Defender clearance or a guarantee that files are safe.**

The prior attempt without databases did not scan any files. That historical failure remains in `baseline-scan-attempt.json` and is superseded by the actual results below.

## Files scanned

| File | Size (bytes) | UTC start | Seconds | Exit | Detections |
| --- | ---: | --- | ---: | ---: | ---: |
| HMONG_VOICE_STUDIO_ULTRA_FAST.zip | 2,940,062 | 2026-10-20T08:40:23.678685+00:00 | 18.63 | 0 | 0 |
| HMONG_VOICE_STUDIO_ULTRA_FAST_0.8.1.zip | 1,636,745 | 2026-10-20T08:40:42.314975+00:00 | 14.09 | 0 | 0 |

SHA-256 identities (checked unchanged before and after scan):

- `HMONG_VOICE_STUDIO_ULTRA_FAST.zip`: `6344d78c6696490fe0b831731bcc5f253f8d4322ac844f3041897ab5f723c3cc`
- `HMONG_VOICE_STUDIO_ULTRA_FAST_0.8.1.zip`: `c2ccad88df5d51cc06457c3f7f49f64a20b55d011a73d0cd0cb4556fbc612aa8`

Each scanner summary counts one top-level ZIP target; archive scanning was enabled, including nested supported archives. ZIP metadata inventories show 90 regular members in the original release (including a nested source backup) and 102 in 0.8.1. No encrypted members were listed. Full commands, stdout, stderr, inventories, and times are saved in `held-release-scan-results.json` and per-ZIP `*-clamav.log` files.

The scanner loaded **3,642,850 signatures**. Options enabled official databases only, archive scanning, all matches, PUA detection, encrypted-file alerts and scan-limit alerts. Limits were 64 archive levels, 100,000 files per container, 128 MiB per member, and 512 MiB total scan data per container. Scan-time limit was disabled. No encrypted-file, scan-limit, engine, or other warnings were printed; stderr was empty.

## Direct file coverage check

To remove ambiguity from top-level ZIP target counts, both releases were safely extracted into separate private scan trees, including the nested historical source backup in its own child tree. Extraction checked all paths and member types before writing: absolute/traversal/backslash/colon paths, duplicate case-insensitive paths, symlinks/special files and encrypted members were rejected; member/total size and depth were bounded. No project content was executed.

One additional combined recursive ClamAV scan ran at **2026-10-20 08:42:38 UTC** with the same official verified databases and limits, plus verbose per-file output and no symlink following. It completed in **16.30 seconds**, exit **0**, with **260 files scanned**, **26 directories**, **0 infected files**, and empty stderr. The 260 expected file paths exactly match 260 per-file `: OK` records, with no missing or unexpected records. This includes **68 extracted members** of the nested historical backup. Extracted contents total 7,602,206 bytes; every SHA-256 was verified unchanged after the scan.

Evidence: `extracted-combined-scan-summary.json`, `extracted-combined-clamav.log` (per-file output), and `extracted-file-inventory.json` (path, source archive/member, depth, byte size and SHA-256).

## Signature source and verification

Direct official updater access to `https://database.clamav.net` remains blocked by the environment proxy (`CONNECT 403`). The supported alternative used was the **official `clamav/clamav:1.4` Docker image**, as documented by Cisco-Talos in:

- https://raw.githubusercontent.com/Cisco-Talos/clamav-docker/main/README.md — identifies `clamav/clamav` as the official ClamAV Docker image.
- https://raw.githubusercontent.com/Cisco-Talos/clamav-docker/main/clamav/README-alpine.md — states that version tags are preloaded with signature databases; `_base` tags exclude them.

The image was obtained through the official Docker registry API with HTTPS. No container or image executable was run. The index, amd64 manifest, config, and the bounded 112,825,214-byte database layer were pinned and SHA-256 verified:

- Index: `sha256:3bba6dd5ac6663d55b80f86a3126e146612d93b593cc2617188d13f637d91260`
- amd64 manifest: `sha256:a1a529c81aa510e3c93c6e303b63c49485fb17599b5657445cd7b8dfbe93f463`
- Config: `sha256:6c33fb72758a6b4470cc86e2119c2bc4e5765896ecd26fd489abac04c117c519`
- Database layer: `sha256:8e3b9766e584d08b33198c57beb76900221b55e3268db143d6a6fcb0c2e01eb8`

Only whitelisted regular `var/lib/clamav/{main,daily,bytecode}.cvd` members were extracted. Every database passed `sigtool --info` with **Verification OK** and exit 0, verifying its ClamAV digital signature as well as the layer hashes.

| Database | Version | Build timestamp | Signatures in CVD | Functionality level |
| --- | ---: | --- | ---: | ---: |
| daily.cvd | 28157 | 18 October 2026 06:24 UTC | 355,765 | 90 |
| main.cvd | 63 | 16 December 2025 23:18 UTC | 3,287,027 | 90 |
| bytecode.cvd | 339 | 11 September 2025 08:29 UTC−04:00 | 80 | 90 |

The daily database is an approximately two-day-old **offline snapshot**, not verified as the latest available release. The image labels report version 1.4.6, built 19 October 2026; the actual scan binary is the separately obtained Debian ClamAV **1.4.3**. Database digital-signature results are in `database-verification.json`; authoritative README snapshots, hashes, manifests, extraction metadata, and provenance are under `official-container/PROVENANCE.json` and adjacent files. Scanner package origin/hashes are in `package-provenance.txt` and `scanner-packages.json`.

## Limits and next action

Microsoft Defender is unavailable in this Linux environment. The user has already supplied a Defender alert for `Trojan:Script/Sabsik.FL.A!ml` (Severe, Removed) naming the unversioned ZIP, and separately reported that 0.8.1 was also blocked. The archive member responsible and the cause of the alert remain unidentified. A ClamAV negative result does not clear Defender, establish a false positive, or justify disabling antivirus. Further diagnosis requires reproduction using Defender or a specific affected member identified by it; no repeated request for the already supplied detection name is needed. No user code or audio was uploaded to a public scanning service. TLS and CVD signature verification were retained.

Local held copies remain preserved as scan evidence. After these scans, the user explicitly requested re-publication to test downloading: only the exact unchanged 0.8.1 ZIP was restored with its original name and SHA256; the unversioned ZIP remains withdrawn. This does not resolve the Defender warning. Scanner binaries, database files, or extracted scan trees are not bundled into an application package. Current release status is documented in the repository-root `HMONG_VOICE_STUDIO_SECURITY_NOTICE.md`.
