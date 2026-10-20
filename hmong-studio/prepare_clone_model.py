"""Download one pinned model snapshot, verify every artifact, and retain resumable partials."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = Path(__file__).resolve().parent
REPOSITORY = 'Xuajpaj2026/hmong-tts-weights'
REVISION = '5663e0df2589c2ca2403cd327a52702c3ff96e8f'


class _HTTPSRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).scheme != 'https':
            raise RuntimeError('Tu choi chuyen huong tai mo hinh khong dung HTTPS.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open(request, *, timeout=90):
    if urllib.parse.urlsplit(request.full_url).scheme != 'https':
        raise ValueError('Model downloads require HTTPS.')
    return urllib.request.build_opener(_HTTPSRedirect()).open(request, timeout=timeout)


def verified(path, entry):
    if not path.is_file() or path.stat().st_size != entry['size']:
        return None
    sha = hashlib.sha256()
    git = hashlib.sha1(('blob ' + str(entry['size']) + '\0').encode())
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            sha.update(chunk)
            git.update(chunk)
    if entry.get('lfs'):
        if sha.hexdigest() != entry['lfs']['sha256']:
            return None
    elif git.hexdigest() != entry['blobId']:
        return None
    return {'path': entry['rfilename'], 'size': entry['size'], 'sha256': sha.hexdigest()}


def download(root, entry):
    raw_name = entry['rfilename']
    name = PurePosixPath(raw_name)
    if not raw_name or str(name) == '.' or name.is_absolute() or '..' in name.parts or '\\' in str(name):
        raise RuntimeError('Duong dan trong manifest khong hop le.')
    target = root.joinpath(*name.parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise RuntimeError('Duong dan tai mo hinh nam ngoai thu muc dich.')
    result = verified(target, entry)
    if result:
        return result
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + '.part')
    if not partial.resolve().is_relative_to(root.resolve()):
        raise RuntimeError('Tep tai tam nam ngoai thu muc dich.')
    result = verified(partial, entry)
    if result:
        partial.replace(target)
        return result
    if entry['size'] == 0:
        # Empty source files have no bytes to fetch, but still need their pinned
        # checksum checked before promotion. There may be no .part file yet.
        partial.write_bytes(b'')
        result = verified(partial, entry)
        if not result:
            raise RuntimeError('Xac minh checksum that bai: ' + str(name))
        partial.replace(target)
        return result
    offset = partial.stat().st_size if partial.exists() else 0
    if offset >= entry['size']:
        partial.unlink()  # Only an invalid partial created by this downloader.
        offset = 0
    url = ('https://huggingface.co/' + REPOSITORY + '/resolve/' + REVISION + '/'
           + urllib.parse.quote(str(name), safe='/') + '?download=true')
    headers = {'Range': f'bytes={offset}-'} if offset else {}
    with _open(urllib.request.Request(url, headers=headers), timeout=90) as response:
        if offset and response.status == 206:
            if not response.headers.get('Content-Range', '').startswith(f'bytes {offset}-'):
                raise RuntimeError('May chu tra sai khoang du lieu: ' + str(name))
            mode = 'ab'
        else:
            mode = 'wb'
            offset = 0
        total = offset
        last_percent = int(total * 100 / entry['size']) // 10 * 10 if entry['size'] else 0
        with partial.open(mode) as output:
            while chunk := response.read(4 * 1024 * 1024):
                total += len(chunk)
                if total > entry['size']:
                    raise RuntimeError('Kich thuoc vuot manifest: ' + str(name))
                output.write(chunk)
                if entry['size'] > 100 * 1024 * 1024:
                    percent = int(total * 100 / entry['size']) // 10 * 10
                    if percent > last_percent:
                        print(name.name + ': ' + str(percent) + '%', flush=True)
                        last_percent = percent
    result = verified(partial, entry)
    if not result:
        raise RuntimeError('Xac minh checksum that bai: ' + str(name))
    partial.replace(target)
    if entry['size'] > 10 * 1024 * 1024:
        print('Da tai va xac minh: ' + str(name) + f" ({entry['size']/1e6:.1f} MB)", flush=True)
    return result


def prepare(directory):
    manifest = json.loads((BASE / 'clone_model_manifest.json').read_text(encoding='utf-8'))
    if manifest.get('repository') != REPOSITORY or manifest.get('revision') != REVISION:
        raise RuntimeError('Manifest khong dung phien ban da kiem tra.')
    root = Path(directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    marker = root / '.hmong-model-ready.json'
    marker.unlink(missing_ok=True)
    size = sum(entry['size'] for entry in manifest['entries'])
    print(f"Can {size/1e9:.2f} GB cho mo hinh; giu ket noi mang. Tep da dung se duoc tai su dung.", flush=True)
    records = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(download, root, entry) for entry in manifest['entries']]
        for future in as_completed(futures):
            records.append(future.result())
    payload = {'repository': REPOSITORY, 'revision': REVISION, 'files': sorted(records, key=lambda e: e['path'])}
    temporary = marker.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    temporary.replace(marker)
    print('Da tai va xac minh tat ca trong so. Hay khoi dong lai Studio de tao voice.', flush=True)
    return root


if __name__ == '__main__':
    default = os.getenv('HMONG_COSY_DIR', str(BASE / '.data' / 'models' / 'hmong-cosy'))
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', default=default)
    args = parser.parse_args()
    try:
        prepare(args.directory)
    except Exception as exc:
        print('Chua tai xong mo hinh: ' + str(exc), file=sys.stderr)
        print('Cac tep .part duoc giu lai. Sua loi mang/dung luong roi chay lai bo cai; khong tat TLS.', file=sys.stderr)
        sys.exit(1)
