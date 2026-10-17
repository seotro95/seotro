"""Portable entry point: the bundled Windows interpreter owns all dependencies."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    python = root / 'runtime/python.exe'
    if not python.is_file() or not (root / 'tools/ffmpeg/bin/ffmpeg.exe').is_file():
        raise RuntimeError('Hay giai nen TOAN BO ZIP, khong chay tool ben trong cua so ZIP.')
    env = dict(os.environ, PYTHONHOME=str(root / 'runtime'), PYTHONNOUSERSITE='1', PYTHONUTF8='1',
               VOICE_STUDIO_DATA_DIR=str(root / 'app/.data'), HF_HOME=str(root / 'app/.data/models/cache'),
               HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', VOICE_STUDIO_PORTABLE='1')
    env.pop('PYTHONPATH', None)
    env['PATH'] = str(root / 'tools/ffmpeg/bin') + os.pathsep + str(root / 'runtime') + os.pathsep + env.get('PATH', '')
    if args.check:
        command = [str(python), '-c', 'import json,app; print(json.dumps(app._config_values(),ensure_ascii=True,indent=2))']
    else:
        command = [str(python), str(root / 'app/launcher.py')]
        if args.no_browser:
            command.append('--no-browser')
    try:
        return subprocess.call(command, cwd=root / 'app', env=env)
    except KeyboardInterrupt:
        return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print('LOI: ' + str(exc), file=sys.stderr)
        sys.exit(1)
