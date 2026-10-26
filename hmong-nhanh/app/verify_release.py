"""Check shipped files against the release inventory, without network access.

This is an integrity check, not an antivirus engine or a digital signature.
The ZIP checksum published on GitHub is the independent comparison point.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys


class ReleaseIntegrityError(RuntimeError):
    pass


def verify_package(root):
    root = Path(root).resolve()
    manifest = root / 'release-files.json'
    try:
        if manifest.stat().st_size > 1_000_000:
            raise ValueError('inventory too large')
        data = json.loads(manifest.read_text(encoding='utf-8'))
        records = data['files']
        if data['version'] != 1 or not isinstance(records, dict) or not 1 <= len(records) <= 500:
            raise ValueError('invalid inventory')
        for relative, record in records.items():
            name = PurePosixPath(relative)
            if (not isinstance(relative, str) or name.is_absolute() or '\\' in relative
                    or ':' in relative or '..' in name.parts or not name.parts
                    or any(part in ('.data', '.venv') for part in name.parts)):
                raise ValueError('invalid inventory path')
            path = root.joinpath(*name.parts)
            resolved = path.resolve()
            if root not in resolved.parents or path.is_symlink():
                raise ValueError('redirected inventory path')
            expected = record['sha256']
            size = record['bytes']
            if (not isinstance(expected, str) or len(expected) != 64
                    or any(ch not in '0123456789abcdef' for ch in expected)
                    or type(size) is not int or size < 0 or path.stat().st_size != size):
                raise ValueError('invalid inventory record')
            digest = hashlib.sha256()
            with path.open('rb') as source:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    digest.update(block)
            if digest.hexdigest() != expected:
                raise ValueError('changed release file')
        return len(records)
    except (OSError, ValueError, KeyError, TypeError):
        raise ReleaseIntegrityError(
            'Tep chuong trinh bi thieu hoac khong khop ban phat hanh. Dung khoi dong; '
            'doi chieu SHA-256 voi ban tren GitHub va quet bang phan mem bao mat. '
            'Giu nguyen .data; khong tat antivirus hoac khoi phuc tep dang bi cach ly.'
        ) from None


def main():
    try:
        count = verify_package(Path(__file__).resolve().parent.parent)
    except ReleaseIntegrityError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print('Toan ven goi: {} tep khop SHA-256.'.format(count))
    print('Day khong phai ket qua quet antivirus hay chung nhan an toan.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
