"""Repackage the verified original Nano/Turbo distribution; no model downloads.

Only a pristine published archive is accepted. Existing user installations are
never read, pruned or overwritten. Windows execution of this new overlay is a
separate check, explicitly not inherited from the original package.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from build_windows import safe_zip_path
from build_clean_bundle import removal_reason


SOURCE = Path(__file__).resolve().parents[1]
BASE_SHA256 = '65446c1a1799699b3aadad616461e97cf66c049597c7ae9a5cbf3887f20312f6'
ROOT = 'Voice-Studio-Compact-19-Windows-x64'
REQUIRED = {'runtime/python.exe', 'ffmpeg/bin/ffmpeg.exe', 'ffmpeg/bin/ffprobe.exe',
            'app/.data/models/vieneu.ready', 'app/.data/models/vieneu_nano.ready',
            'delivery/voices.vspack', 'delivery/manifest.json', 'CAI_19_GIONG.bat',
            'install_secure_voices.ps1', 'BUILD_INFO.json'}
GUIDE = '''VOICE STUDIO GỌN — GIỮ BỘ 19 MẪU GIỌNG

Giải nén toàn bộ ZIP vào thư mục mới có quyền ghi rồi mở MO_TOOL.bat.
Python, FFmpeg, Nano và Turbo đã có sẵn như gói gốc. Đây là ZIP đầy đủ,
không phải trình tải, không cần ghép part001/002/003.

GIỮ GIỌNG VÀ DỮ LIỆU
Bộ 19 mẫu mã hóa được giữ nguyên byte. Chạy CAI_19_GIONG.bat với mật khẩu
cũ nếu cần mở lại. Bản dựng này không biết mật khẩu và chưa giải mã mẫu.
Muốn chuyển dữ liệu cũ: đóng tool, sao lưu thư mục cũ rồi chép các thư mục
app\\voice-library, app\\.data\\voices, audio, jobs, parts, cache nếu cần.
Các tên audio/jobs/parts/cache ở đây đều nằm trong app\\.data của bản cũ.
Không ghi đè thư mục models hoặc runtime của bản mới bằng toàn bộ bản cũ.

TẠO NHANH HƠN
Chọn đúng mẫu giọng, mở Điều chỉnh nâng cao, bấm Tận dụng CPU · Giữ số bước.
Turbo ở chế độ Cân bằng nay dùng các lượt đọc độc lập, mỗi lượt một luồng
CPU thay cho đội 2 luồng kế thừa từ Nano. Giữ nguyên FP32 và giọng đã chọn.
Cấu hình vẫn giới hạn theo CPU/RAM; có thể dùng Tự đo và tối ưu CPU để đo
trên máy của bạn. Cấu hình đã lưu trong trình duyệt được giữ nguyên.
Nano 4 bước là lựa chọn nháp nhanh riêng; không tự đổi giọng mẫu sang Nano.

PHẠM VI GÓI GỌN
Nano: tiếng Việt. Turbo: Việt/Anh và mẫu giọng được hỗ trợ.
19 tệp mẫu không phải 19 mô hình. Giữ mẫu Hàn/Pháp/Nhật/Thái không làm
Turbo đọc được các tiếng đó. Các bộ đọc Qwen/VoxCPM2/OmniVoice vẫn là
thành phần tùy chọn, không đóng kèm để tránh tăng gói lên 11 GB. Chỉ tải bộ
cần dùng theo ngôn ngữ; không xóa bản cũ nếu đang cần các bộ đọc ấy.
Các giọng Qwen công khai chưa cài được ẩn; 19 mẫu riêng không bị lọc/xóa.

KIỂM CHỨNG
Xem COMPACT-CPU-QA.json để biết đo suy luận thật trên Linux, dùng giọng
công khai. Chưa chạy bản sửa này trên Windows/GTX1060 hoặc với mẫu riêng.
Không cam kết 1 giờ lời đọc trong 2 phút. Không tăng tốc phát lại, cắt lời
hoặc chèn im lặng để tính thành tích. BUILD_INFO.json ghi rõ phạm vi này.
'''


def sha(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def build(base, output, *, source=SOURCE, evidence=None, expected=BASE_SHA256):
    base, output, source = Path(base), Path(output), Path(source)
    if output.exists():
        raise FileExistsError('Use a new output file; existing packages are preserved')
    if len(expected) != 64 or sha(base) != expected:
        raise ValueError('Original package SHA256 mismatch')
    payloads = {}
    for path in sorted((source/'app').rglob('*')):
        relative = path.relative_to(source/'app')
        if (path.is_file() and not any(p in {'tests', '__pycache__', '.data', 'voice-library'} for p in relative.parts)
                and path.suffix in {'.py', '.ps1', '.js', '.html', '.css'}):
            payloads['app/'+relative.as_posix()] = path.read_bytes()
    payloads['MO_TOOL.bat'] = (source/'packaging/MO_TOOL.bat').read_bytes()
    payloads['DOC_TRUOC.txt'] = GUIDE.encode('utf-8-sig')
    payloads['DISTRIBUTION.json'] = json.dumps({'schema': 1, 'profile': 'compact-19',
        'bundled_engines': ['vieneu', 'vieneu_nano']}, indent=2).encode()
    if evidence is not None:
        record = json.loads(Path(evidence).read_text(encoding='utf-8'))
        if (record.get('engine') != 'vieneu' or record.get('private_voices_tested') is not False
                or not record.get('trials') or record.get('target_30x_verified') is not False):
            raise ValueError('Expected scoped real CPU benchmark evidence')
        payloads['COMPACT-CPU-QA.json'] = Path(evidence).read_bytes()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.building')
    if temporary.exists():
        raise FileExistsError('Existing incomplete build is preserved')
    hashes, removed = {}, []
    try:
        with zipfile.ZipFile(base) as original:
            entries, roots, folded = {}, set(), set()
            if len(original.infolist()) > 50000 or sum(i.file_size for i in original.infolist()) > 8*1024**3:
                raise ValueError('Unexpected original archive size')
            for entry in original.infolist():
                parts = safe_zip_path(entry)
                roots.add(parts[0])
                if entry.is_dir():
                    continue
                name = '/'.join(parts[1:])
                if not name or name.casefold() in folded:
                    raise ValueError('Duplicate package member')
                folded.add(name.casefold()); entries[name] = entry
            if len(roots) != 1 or not REQUIRED <= entries.keys():
                raise ValueError('Incomplete original Nano/Turbo/19-voice package')
            private_digest = hashlib.sha256(original.read(entries['delivery/voices.vspack'])).hexdigest()
            inherited = json.loads(original.read(entries['BUILD_INFO.json']))
            if inherited.get('encrypted_private_voice_count') != 19:
                raise ValueError('Original metadata does not identify the 19-voice package')
            with zipfile.ZipFile(temporary, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=4, allowZip64=True) as result:
                for name, entry in entries.items():
                    reason = removal_reason(name, entry.file_size)
                    if name.startswith('app/') and not name.startswith('app/.data/models/'):
                        reason = 'replace-application-with-current-source'
                    if name in {'MANIFEST.sha256', 'BUILD_INFO.json', 'DOC_TRUOC.md', 'DOC_TRUOC.txt'}:
                        reason = 'replace-manifest-metadata-or-guide'
                    if name.startswith(('CPU-', 'Windows-')) and name.endswith('.json'):
                        reason = 'inherited-benchmark-not-current-validation'
                    if name in payloads:
                        reason = 'current-source-overlay'
                    if reason:
                        removed.append({'name': name, 'reason': reason}); continue
                    digest = hashlib.sha256()
                    with original.open(entry) as stream, result.open(ROOT+'/'+name, 'w', force_zip64=True) as target:
                        while block := stream.read(4*1024**2):
                            digest.update(block); target.write(block)
                    hashes[name] = digest.hexdigest()
                payloads['BUILD_INFO.json'] = json.dumps({'product': 'Voice Studio Rieng',
                    'version': '1.12.2+compact.1', 'profile': 'compact-19',
                    'verified_original_sha256': expected, 'bundled_engines': ['vieneu', 'vieneu_nano'],
                    'encrypted_private_pack_sha256': private_digest,
                    'encrypted_private_pack_byte_identical': True,
                    'inherited_private_voice_count': 19, 'private_voice_unlock_tested': False,
                    'current_windows_validation': 'not_run', 'gpu_tested': False,
                    'target_30x_guaranteed': False, 'source_files_sha256': {
                        n: hashlib.sha256(b).hexdigest() for n,b in payloads.items() if n.startswith('app/')},
                    'base_windows_validation': inherited.get('native_windows_offline_smoke')}, indent=2).encode()
                payloads['COMPACT-CLEANUP.json'] = json.dumps(removed, indent=2).encode()
                for name, content in sorted(payloads.items()):
                    result.writestr(ROOT+'/'+name, content)
                    hashes[name] = hashlib.sha256(content).hexdigest()
                result.writestr(ROOT+'/MANIFEST.sha256', ''.join(h+'  '+n+'\n' for n,h in sorted(hashes.items())))
        if temporary.stat().st_size >= 2*1024**3:
            raise ValueError('Compact ZIP exceeds 2 GiB')
        with zipfile.ZipFile(temporary) as result:
            expanded = 0
            for entry in result.infolist():
                name = entry.filename.removeprefix(ROOT+'/')
                expanded += entry.file_size
                if name == 'MANIFEST.sha256': continue
                with result.open(entry) as stream:
                    actual = hashlib.file_digest(stream, 'sha256').hexdigest()
                if actual != hashes[name]:
                    raise ValueError('Output manifest mismatch: '+name)
        temporary.replace(output)
        digest = sha(output)
        output.with_suffix('.zip.sha256').write_text(digest+'  '+output.name+'\n')
        return {'archive': output.name, 'archive_bytes': output.stat().st_size,
                'expanded_bytes': expanded, 'sha256': digest, 'verified_member_count': len(hashes),
                'private_pack_preserved': hashes['delivery/voices.vspack'] == private_digest,
                'windows_tested': False, 'gpu_tested': False}
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.base, args.output, evidence=args.evidence), indent=2), flush=True)


if __name__ == '__main__':
    main()
