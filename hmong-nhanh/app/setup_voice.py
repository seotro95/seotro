"""Install the exact model artifacts pinned by this application release.

Remote metadata and local receipts are never trust anchors. Downloads use fixed
Hugging Face commit URLs and release-owned SHA-256/size values before publication.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

from model_files import EngineError, model_directory, verify_models
from model_manifest import MODEL_RELEASE, PINNED_MODELS, SOURCES


class SetupError(RuntimeError):
    pass


class _HTTPSRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        if urllib.parse.urlparse(newurl).scheme.lower() != 'https':
            raise SetupError('Máy chủ chuyển hướng khỏi HTTPS; không tải mô hình.')
        return super().redirect_request(request, fp, code, message, headers, newurl)


def _verified(path, size, sha256):
    if not path.is_file() or path.stat().st_size != size:
        return None
    digest = hashlib.sha256()
    total = 0
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            total += len(block)
            digest.update(block)
    return sha256 if total == size and digest.hexdigest() == sha256 else None


def _download(url, destination, size, sha256):
    if urllib.parse.urlparse(url).scheme.lower() != 'https':
        raise SetupError('Mô hình chỉ được tải qua HTTPS.')
    existing = _verified(destination, size, sha256)
    if existing:
        print('Đã xác minh, dùng lại:', destination.name, flush=True)
        return existing
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=destination.name + '.', suffix='.part', dir=destination.parent)
    temporary = Path(temporary)
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Hmong-Nhanh/0.8.1'})
        # Preserve the normal proxy and TLS trust handling; only disallow an
        # HTTPS-to-HTTP downgrade when the host redirects to its model CDN.
        opener = urllib.request.build_opener(_HTTPSRedirectHandler())
        with os.fdopen(fd, 'wb') as output, opener.open(request, timeout=120) as response:
            total = 0
            last_report = 0
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > size:
                    raise SetupError('Tệp tải về vượt kích thước đã cố định; không cài tệp này.')
                output.write(block)
                if total - last_report >= 64 * 1024 * 1024:
                    print(f'  {destination.name}: {total // (1024 ** 2)}/{size // (1024 ** 2)} MiB', flush=True)
                    last_report = total
        actual_sha = _verified(temporary, size, sha256)
        if actual_sha is None:
            raise SetupError('Checksum/kích thước không khớp cho ' + destination.name + '; không cài tệp này.')
        temporary.replace(destination)
        return actual_sha
    finally:
        temporary.unlink(missing_ok=True)


def install(root):
    root = Path(root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    manifest = {
        'version': 1, 'release': MODEL_RELEASE,
        'sources': [{'repository': repository, 'revision': revision} for repository, revision in SOURCES],
        'files': {},
    }
    for relative, record in PINNED_MODELS.items():
        print('Kiểm tra/tải bản đã cố định:', relative, flush=True)
        actual_sha = _download(record['url'], root / relative, record['size'], record['sha256'])
        manifest['files'][relative] = {'sha256': actual_sha, 'size': record['size'], 'url': record['url']}
    # Verify from the release pins once more. The receipt is informational and
    # cannot authorize different weights/configuration if edited later.
    verify_models(root)
    fd, temporary = tempfile.mkstemp(prefix='manifest-', suffix='.json', dir=root)
    temporary = Path(temporary)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        temporary.replace(root / 'verified-models.json')
    finally:
        temporary.unlink(missing_ok=True)
    print('Đã xác minh bộ mô hình đã cố định. Cần nhập lời khớp đoạn mẫu và nghe thử trước khi đọc dài.', flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Cài F5-Hmong/Vocos từ commit và SHA-256 đã cố định trong bản tool.')
    parser.add_argument('--model-dir', type=Path, default=model_directory())
    parser.add_argument('--verify-only', action='store_true', help='Chỉ xác minh tệp đã tải, không dùng mạng')
    args = parser.parse_args(argv)
    try:
        if args.verify_only:
            verify_models(args.model_dir)
            print('Kiểm tra SHA-256 theo bản phát hành thành công.')
        else:
            install(args.model_dir)
        return 0
    except (EngineError, SetupError, OSError, urllib.error.URLError, ValueError) as exc:
        print('Chưa cài được giọng:', str(exc), file=sys.stderr)
        print('Giữ nguyên TLS và kiểm tra checksum. Kiểm tra mạng tới huggingface.co và các CDN Hugging Face; '
              'mở lại bước cài đặt sau khi kết nối được.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
