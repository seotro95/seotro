"""Select Python 3.10-3.12 and preserve incompatible virtual environments.

This bootstrap deliberately uses only the standard library and syntax accepted
by Python 3.8+, so an unsupported system Python can start the version check.
"""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys


PREFERRED = ((3, 12), (3, 11), (3, 10))
INSTALL_HELP = (
    "Can cai Python 3.12 (64-bit), bat Python Launcher va Add Python to PATH. "
    "Tai tu https://www.python.org/downloads/windows/ . "
    "Sau khi cai, mo lai MO_HMONG_NHANH.bat. Khong can cai Visual C++ de sua loi Python 3.15 nay."
)
_PROBE = (
    "import json,sys,struct; "
    "print(json.dumps({'version':list(sys.version_info[:3]),'executable':sys.executable,'bits':struct.calcsize('P')*8}))"
)


class BootstrapError(Exception):
    pass


def probe_python(command):
    """Read an interpreter version without running shell command text."""
    try:
        result = subprocess.run(
            list(command) + ['-c', _PROBE], check=True, capture_output=True,
            text=True, timeout=15, stdin=subprocess.DEVNULL,
        )
        metadata = json.loads(result.stdout)
        version = metadata['version']
        executable = metadata['executable']
        bits = metadata['bits']
        if (not isinstance(version, list) or len(version) != 3
                or any(type(number) is not int for number in version)
                or not isinstance(executable, str) or not executable
                or type(bits) is not int or bits not in (32, 64)):
            return None
        return {'version': tuple(version), 'executable': executable,
                'command': tuple(command), 'bits': bits}
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        return None


def supported(metadata):
    return bool(metadata and metadata['version'][:2] in PREFERRED and metadata['bits'] == 64)


def interpreter_candidates():
    candidates = []
    for major, minor in PREFERRED:
        if os.name == 'nt':
            candidates.append(('py', '-{}.{}'.format(major, minor)))
        candidates.append(('python{}.{}'.format(major, minor),))
    candidates.extend([(sys.executable,), ('python',), ('python3',)])
    # Avoid duplicate probes while preserving deterministic preference.
    return list(dict.fromkeys(candidates))


def select_python():
    found = []
    for command in interpreter_candidates():
        metadata = probe_python(command)
        if supported(metadata):
            found.append(metadata)
            if metadata['version'][:2] == PREFERRED[0]:
                return metadata
    for version in PREFERRED:
        for metadata in found:
            if metadata['version'][:2] == version:
                return metadata
    raise BootstrapError(INSTALL_HELP)


def venv_python(folder):
    return folder / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def preserve_venv(folder):
    """Rename, never remove, an old environment and never overwrite a backup."""
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    base = folder.with_name(folder.name + '-backup-unsupported-' + stamp)
    destination = base
    suffix = 1
    while destination.exists() or destination.is_symlink():
        destination = base.with_name(base.name + '-' + str(suffix))
        suffix += 1
    try:
        folder.rename(destination)
    except OSError:
        raise BootstrapError(
            "Khong doi ten duoc moi truong cu. Hay dong tool/cua so dang dung .venv "
            "va thu lai. Thu muc cu duoc giu nguyen."
        ) from None
    return destination


def prepare(root, check_only=False):
    root = Path(root)
    folder = root / '.venv'
    # Do not execute or modify an environment redirected outside the package.
    if folder.is_symlink():
        raise BootstrapError(".venv la lien ket. Hay doi ten lien ket truoc; bootstrap khong sua du lieu ben ngoai tool.")
    existing = probe_python((str(venv_python(folder)),)) if folder.exists() else None
    if supported(existing):
        print("Dung moi truong hien co: Python {}.{}.{}".format(*existing['version']))
        return venv_python(folder)

    selected = select_python()
    print("Da chon Python {}.{}.{} (64-bit): {}".format(
        *selected['version'], selected['executable'].encode('ascii', 'backslashreplace').decode('ascii')))
    if check_only:
        if folder.exists():
            print(".venv cu khong tuong thich; se duoc doi ten sao luu khi khoi dong.")
        return Path(selected['executable'])
    if folder.exists():
        backup = preserve_venv(folder)
        print("Da giu moi truong cu tai: " + str(backup).encode('ascii', 'backslashreplace').decode('ascii'))
    try:
        subprocess.run(
            list(selected['command']) + ['-m', 'venv', str(folder)], check=True,
            timeout=180, stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        raise BootstrapError(
            "Khong tao duoc .venv. Kiem tra Python 3.12, quyen ghi va dung luong dia. "
            "Moi truong cu da sao luu (neu co) khong bi xoa."
        ) from None
    created = probe_python((str(venv_python(folder)),))
    if not supported(created):
        raise BootstrapError(".venv moi chua chay duoc voi Python 3.10-3.12. " + INSTALL_HELP)
    return venv_python(folder)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Prepare a supported Hmong Studio Python environment.')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--check', action='store_true', help='Check interpreters without changing files.')
    action.add_argument('--prepare', action='store_true', help='Prepare .venv (the default).')
    args = parser.parse_args(argv)
    try:
        prepare(Path(__file__).resolve().parent, check_only=args.check)
    except BootstrapError as exc:
        print('LOI: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
