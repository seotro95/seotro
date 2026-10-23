"""Install fixed upstream model revisions for the optional fast Hmong backend.

Weights are downloaded on first use, not redistributed in the application.
The upstream Hmong checkpoint has no explicit license identified; review its
terms before use or redistribution. Availability does not certify native Hmong
pronunciation, voice similarity, or one hour of speech generated in two minutes.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import urllib.error

from hmong_native_models import EngineError, MANIFEST_NAME, MODEL_RECORDS, model_directory, verify_models
from prepare_hmong import SetupError, _download


def install(root):
    """Install only native files; preserve F5 models and all personal data."""
    root = Path(root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    total = sum(record["size"] for record in MODEL_RECORDS.values())
    print(f"Lần đầu tải/kiểm tra khoảng {total / 1_000_000:.0f} MB mô hình Hmong nhanh, OpenVoice V2 và WavMark.", flush=True)
    print("Tải trực tiếp các phiên bản nguồn đã cố định qua HTTPS và kiểm tra SHA-256; không kèm trọng số trong bộ tool.", flush=True)
    print("Checkpoint Hmong chưa có giấy phép rõ ràng; xem điều khoản nguồn trước khi sử dụng/phân phối. "
          "Bản thử nghiệm chưa được xác nhận phát âm bản ngữ hoặc đạt 2 phút/1 giờ voice.", flush=True)
    manifest = {"version": 1, "backend": "hmong_native", "files": {}}
    for relative, record in MODEL_RECORDS.items():
        print("Kiểm tra/tải:", relative, flush=True)
        actual_sha = _download(record["url"], root / relative, record["size"], record["sha256"], None)
        if actual_sha != record["sha256"]:
            raise SetupError("SHA-256 không khớp cho " + relative + "; chưa ghi trạng thái sẵn sàng.")
        manifest["files"][relative] = dict(record)
    fd, temporary = tempfile.mkstemp(prefix="native-manifest-", suffix=".json", dir=root)
    temporary = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        temporary.replace(root / MANIFEST_NAME)
    finally:
        temporary.unlink(missing_ok=True)
    verify_models(root)
    print("Đã kiểm tra toàn bộ SHA-256 mô hình Hmong nhanh. Nghe thử trước khi tạo bài dài.", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Cài mô hình Hmong nhanh thử nghiệm (~580 MB) từ các bản HTTPS cố định.")
    parser.add_argument("--model-dir", type=Path, default=model_directory())
    parser.add_argument("--verify-only", action="store_true", help="Chỉ xác minh SHA-256 tệp đã có; hoàn toàn không tải mạng")
    args = parser.parse_args(argv)
    try:
        if args.verify_only:
            verify_models(args.model_dir)
            print("Kiểm tra SHA-256 mô hình Hmong nhanh thành công; chưa xác nhận phát âm hay tốc độ.")
        else:
            install(args.model_dir)
        return 0
    except (EngineError, SetupError, OSError, urllib.error.URLError, ValueError) as exc:
        print("Chưa cài được mô hình Hmong nhanh:", str(exc), file=sys.stderr)
        print("Giữ kiểm tra TLS/SHA-256. Kiểm tra mạng tới huggingface.co và CDN Hugging Face; "
              "thử tải lại trên mạng được phép nếu gặp 403. Tệp F5 và dữ liệu cá nhân vẫn được giữ.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
