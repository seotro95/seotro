"""Publish one immutable, already tested artifact without rebuilding its contents."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
import time
import urllib.request
import zipfile


REPOSITORY = 'seotro95/seotro'
SOURCE_RUN = 39635826843
SOURCE_COMMIT = 'e24188a8077a515ab820ef752b2a8b91d7593d9d'
ARTIFACT_ID = 12364897379
ARTIFACT_NAME = 'Hmoob-VoiceLab-Windows-x64'
ARCHIVE_NAME = 'Hmoob-VoiceLab-1.1.1-Windows-x64.zip'
EXPECTED_SIZE = 782350627
EXPECTED_SHA256 = 'ebc65ec4cc4a08bcd2a66a318e143fc5009aac2e7f553ba329ad28f5dfa4a74b'
EXPECTED_DIGEST = 'sha256:' + EXPECTED_SHA256
RELEASE_TAG = 'hmoob-voicelab-1.1.1-windows-39635826843'
RELEASE_TITLE = 'Hmoob VoiceLab 1.1.1 - Windows x64'
REQUIRED_FILES = {
    'MO_HMOOB_VOICELAB.bat', 'CHAN_DOAN_HMOOB.bat', 'BAT-DAU.txt', 'BUILD.json',
    'runtime/python.exe', 'runtime/python312.dll',
    'runtime/Lib/site-packages/torch/__init__.py',
    'runtime/Lib/site-packages/torchaudio/__init__.py',
    'ffmpeg/bin/ffmpeg.exe', 'ffmpeg/bin/ffprobe.exe',
    'hmoob-voicelab/bootstrap.py', 'hmoob-voicelab/launch_logged.py',
    'hmoob-voicelab/hmong_f5.py', 'hmoob-voicelab/version.py',
    'hmoob-voicelab/server.py', 'hmoob-voicelab/web/index.html',
    'hmoob-voicelab/assets/voices.json',
    'hmoob-voicelab/assets/default-female.mp3',
    'hmoob-voicelab/assets/default-male.mp3',
}
RELEASE_BODY = f'''Bản Windows x64 đầy đủ, gồm Python, thư viện AI và FFmpeg.

Bản 1.1.1 bỏ bước nạp AI trước khi mở giao diện để xử lý lỗi khởi động dừng quá 120 giây. Khi tạo giọng, giao diện và nhật ký hiển thị từng bước nạp mô hình cùng thời gian đã xử lý.

Tải **{ARCHIVE_NAME}**, giải nén toàn bộ một lần vào thư mục mới như `C:\\Hmoob-1.1.1`, rồi mở **MO_HMOOB_VOICELAB.bat**. Không cần ghép với bản cũ. Giữ cửa sổ lệnh mở trong lúc dùng.

Lần đầu cần Internet để tự tải khoảng **1,4 GB mô hình** có kiểm tra SHA-256. Sau đó có thể tạo giọng nam/nữ bằng CPU trên máy.

Đã kiểm tra giọng nam/nữ thật, chạy BAT sau khi đổi thư mục, mở giao diện không nạp AI trước, xuất WAV/ZIP và lưu lịch sử trên Windows. Windows Defender trên máy kiểm thử không phát hiện mối đe dọa trong các tệp đã đóng gói và ZIP kiểm thử; kết quả này không phải bảo đảm cho mọi máy.

ZIP tải tại đây giữ nguyên từng byte từ artifact đã kiểm thử: https://github.com/{REPOSITORY}/actions/runs/{SOURCE_RUN}

Mã nguồn: `{SOURCE_COMMIT}`

SHA-256 của ZIP:
`{EXPECTED_SHA256}`
'''


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def api(path, *, method='GET', body=None, optional=False):
    command = ['gh', 'api', '--hostname', 'github.com', '--method', method,
               '--header', 'Accept: application/vnd.github+json',
               '--header', 'X-GitHub-Api-Version: 2022-11-28', path]
    if body is not None:
        command += ['--header', 'Content-Type: application/json', '--input', '-']
    result = subprocess.run(command, input=None if body is None else json.dumps(body).encode('utf-8'),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    try:
        value = json.loads(result.stdout)
    except (ValueError, UnicodeError):
        value = None
    if result.returncode:
        missing = (isinstance(value, dict) and str(value.get('status')) == '404') or \
                  '(HTTP 404)' in result.stderr.decode('utf-8', errors='replace')
        if optional and missing:
            return None
        raise RuntimeError(f'GitHub API {method} {path} failed (exit {result.returncode}).')
    require(value is not None, 'GitHub API did not return valid JSON: ' + path)
    return value


def verify_source():
    run = api(f'repos/{REPOSITORY}/actions/runs/{SOURCE_RUN}')
    require(run.get('id') == SOURCE_RUN and run.get('status') == 'completed' and
            run.get('conclusion') == 'success' and run.get('head_sha') == SOURCE_COMMIT and
            run.get('repository', {}).get('full_name') == REPOSITORY,
            'The pinned source workflow did not finish successfully at the expected commit.')
    artifact = api(f'repos/{REPOSITORY}/actions/artifacts/{ARTIFACT_ID}')
    require(artifact.get('id') == ARTIFACT_ID and artifact.get('name') == ARTIFACT_NAME and
            artifact.get('expired') is False and artifact.get('size_in_bytes') == EXPECTED_SIZE and
            artifact.get('digest') == EXPECTED_DIGEST and
            artifact.get('workflow_run', {}).get('id') == SOURCE_RUN and
            artifact.get('workflow_run', {}).get('head_sha') == SOURCE_COMMIT,
            'The artifact metadata does not match the immutable tested Windows download.')
    print(f'Confirmed successful source run {SOURCE_RUN} and pinned artifact {ARTIFACT_ID}.', flush=True)


def verify_archive(archive):
    require(archive.stat().st_size == EXPECTED_SIZE, 'Downloaded ZIP has the wrong size.')
    digest = hashlib.sha256()
    with archive.open('rb') as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b''):
            digest.update(block)
    require(digest.hexdigest() == EXPECTED_SHA256, 'Downloaded ZIP checksum does not match.')
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        require(len(names) == len(set(name.casefold() for name in names)), 'ZIP contains duplicate paths.')
        for name in names:
            require(not PurePosixPath(name).is_absolute() and '\\' not in name and ':' not in name and
                    not any(part in ('.', '..') for part in name.split('/')),
                    'ZIP contains an unsafe path.')
            require(not name.startswith('hmoob-voicelab/.data/'), 'ZIP unexpectedly contains user/model data.')
        require(REQUIRED_FILES.issubset(names), 'ZIP is missing required files at its extract-and-run root.')
        require(bundle.testzip() is None, 'ZIP integrity/CRC verification failed.')
    print(f'Exact ZIP SHA-256, CRC and root layout verified ({len(names)} entries).', flush=True)


def download_archive(work_dir):
    archive = work_dir / ARCHIVE_NAME
    if not archive.exists():
        descriptor, temporary_name = tempfile.mkstemp(prefix='artifact-', suffix='.partial', dir=work_dir)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, 'wb') as output:
                subprocess.run(['gh', 'api', '--hostname', 'github.com',
                                '--header', 'Accept: application/vnd.github+json',
                                '--header', 'X-GitHub-Api-Version: 2022-11-28',
                                f'repos/{REPOSITORY}/actions/artifacts/{ARTIFACT_ID}/zip'],
                               stdout=output, check=True, timeout=900)
            verify_archive(temporary)
            temporary.rename(archive)
        finally:
            temporary.unlink(missing_ok=True)
    else:
        verify_archive(archive)
    return archive


def verify_tag(*, required):
    reference = api(f'repos/{REPOSITORY}/git/ref/tags/{RELEASE_TAG}', optional=not required)
    if reference is None:
        return
    obj = reference.get('object', {})
    for _ in range(8):
        if obj.get('type') == 'commit':
            require(obj.get('sha') == SOURCE_COMMIT, 'Existing release tag points to another commit.')
            return
        require(obj.get('type') == 'tag' and isinstance(obj.get('sha'), str), 'Unexpected release tag object.')
        obj = api(f"repos/{REPOSITORY}/git/tags/{obj['sha']}").get('object', {})
    raise RuntimeError('Release tag nesting is too deep.')


def verify_release(release, *, allow_empty, allow_pending_digest=False):
    require(release.get('tag_name') == RELEASE_TAG and release.get('target_commitish') == SOURCE_COMMIT and
            release.get('prerelease') is False and release.get('name') == RELEASE_TITLE and
            release.get('body') == RELEASE_BODY and isinstance(release.get('draft'), bool),
            'Existing release identity does not match this delivery; it was left unchanged.')
    assets = release.get('assets', [])
    if allow_empty and release.get('draft') is True and not assets:
        return False
    require(len(assets) == 1, 'Existing release has unexpected assets; nothing will be overwritten.')
    asset = assets[0]
    require(asset.get('name') == ARCHIVE_NAME and asset.get('state') == 'uploaded' and
            asset.get('size') == EXPECTED_SIZE,
            'Existing ZIP asset does not match the tested artifact; nothing will be overwritten.')
    if allow_pending_digest and asset.get('digest') in (None, ''):
        return None
    require(asset.get('digest') == EXPECTED_DIGEST,
            'Existing ZIP digest does not match the tested artifact; nothing will be overwritten.')
    return True


def wait_for_asset(release_id):
    deadline = time.monotonic() + 90
    while True:
        release = api(f'repos/{REPOSITORY}/releases/{release_id}')
        if verify_release(release, allow_empty=False, allow_pending_digest=True) is True:
            return release
        require(time.monotonic() < deadline, 'Uploaded asset digest is still missing; release remains unchanged.')
        time.sleep(3)


def verify_anonymous_download(url):
    for attempt in range(4):
        request = urllib.request.Request(url, headers={
            'Range': 'bytes=0-3', 'User-Agent': 'Hmoob-VoiceLab-download-check/1.1',
        })
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                status = response.getcode()
                require(status in (200, 206), 'Anonymous download returned an unexpected HTTP status.')
                require(response.read(4) == b'PK\x03\x04', 'Anonymous download did not return a ZIP header.')
                if status == 206:
                    content_range = re.fullmatch(r'bytes 0-(\d+)/(\d+)', response.headers.get('Content-Range', ''))
                    require(content_range is not None and int(content_range[1]) >= 3 and
                            int(content_range[2]) == EXPECTED_SIZE,
                            'Anonymous download reported an unexpected ZIP range or size.')
                elif response.headers.get('Content-Length'):
                    require(int(response.headers['Content-Length']) == EXPECTED_SIZE,
                            'Anonymous download reported an unexpected ZIP size.')
            print('Anonymous range GET returned the actual ZIP header without GitHub authentication.', flush=True)
            return
        except (OSError, RuntimeError, ValueError):
            if attempt == 3:
                raise RuntimeError('Anonymous ZIP download check failed; no Authorization header was used.') from None
            time.sleep(3)


def publish(archive):
    verify_tag(required=False)
    release = api(f'repos/{REPOSITORY}/releases/tags/{RELEASE_TAG}', optional=True)
    if release is None:
        release = api(f'repos/{REPOSITORY}/releases', method='POST', body={
            'tag_name': RELEASE_TAG, 'target_commitish': SOURCE_COMMIT,
            'name': RELEASE_TITLE, 'body': RELEASE_BODY, 'draft': True,
            'prerelease': False, 'make_latest': 'false',
        })
    complete = verify_release(release, allow_empty=True, allow_pending_digest=True)
    if complete is False:
        subprocess.run(['gh', 'release', 'upload', RELEASE_TAG, str(archive), '--repo', REPOSITORY],
                       check=True, timeout=900)
    if not complete:
        release = wait_for_asset(release['id'])
    verify_release(release, allow_empty=False)
    if release.get('draft') is True:
        verify_tag(required=False)
        release = api(f"repos/{REPOSITORY}/releases/{release['id']}", method='PATCH',
                      body={'draft': False, 'make_latest': 'false'})
    verify_release(release, allow_empty=False)
    require(release.get('draft') is False, 'Release is still a draft.')
    verify_tag(required=True)
    url = release['assets'][0]['browser_download_url']
    expected_url = f'https://github.com/{REPOSITORY}/releases/download/{RELEASE_TAG}/{ARCHIVE_NAME}'
    require(url == expected_url, 'The published ZIP has an unexpected download URL.')
    verify_anonymous_download(url)
    print('Public full ZIP download: ' + url, flush=True)
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as output:
            output.write(f'Bản Windows đầy đủ: [{ARCHIVE_NAME}]({url})\n\n'
                         f'Size: {EXPECTED_SIZE} bytes. SHA-256: `{EXPECTED_SHA256}`\n')
    return url


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--work-dir', type=Path, required=True)
    args = parser.parse_args()
    require(os.environ.get('GITHUB_REPOSITORY', REPOSITORY) == REPOSITORY, 'Unexpected repository.')
    require(bool(os.environ.get('GH_TOKEN')), 'Runner GH_TOKEN is required and was not provided.')
    args.work_dir.mkdir(parents=True, exist_ok=True)
    verify_source()
    archive = download_archive(args.work_dir)
    publish(archive)


if __name__ == '__main__':
    main()
