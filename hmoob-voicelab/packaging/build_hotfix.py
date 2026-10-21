"""Build a small text-script overlay for the already verified Windows runtime."""
import argparse
from pathlib import Path
import shutil
import zipfile

from build_windows import SOURCE, sha256, write_launcher


def build_hotfix(output, archive):
    output, archive = Path(output), Path(archive)
    if output.exists():
        raise ValueError('Use a new hotfix output directory; existing files are preserved')
    output.mkdir(parents=True)
    write_launcher(output)
    for name in ('bootstrap.py', 'start.bat'):
        shutil.copy2(SOURCE / name, output / 'hmoob-voicelab' / name)
    (output / 'HUONG-DAN-CAP-NHAT.txt').write_text(
        'BẢN SỬA CỬA SỔ LỆNH TRẮNG — HMOOB VOICELAB\n\n'
        'Đóng cửa sổ tool cũ. Giải nén NỘI DUNG bản sửa này vào đúng thư mục tool '
        'đang có ffmpeg, hmoob-voicelab, runtime. Đồng ý thay thế các tệp script cùng tên.\n'
        'Không xóa .data hoặc thư mục mô hình; bản sửa không chứa hay thay thế dữ liệu của bạn.\n\n'
        'Mở MO_HMOOB_VOICELAB.bat. Cửa sổ sẽ hiện trạng thái ngay và ghi log. '
        'Lần đầu cần Internet để tải khoảng 1,4 GB mô hình; những lần sau dùng lại.\n'
        'Nếu còn lỗi, mở CHAN_DOAN_HMOOB.bat, chờ hoàn tất rồi gửi tệp '
        'hmoob-voicelab/.data/.logs/diagnostic.log. Không tắt Windows Security hoặc cho phép '
        'tệp đã bị bảo vệ chặn.\n', encoding='utf-8')
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for path in sorted(output.rglob('*')):
            if path.is_file():
                bundle.write(path, path.relative_to(output).as_posix())
    checksum = sha256(archive)
    Path(str(archive) + '.sha256').write_text(checksum + '  ' + archive.name + '\n', encoding='ascii')
    print(str(archive), flush=True)
    return checksum


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--archive', required=True, type=Path)
    args = parser.parse_args()
    build_hotfix(args.output, args.archive)
