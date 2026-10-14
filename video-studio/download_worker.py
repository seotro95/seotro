"""Separate process allows cancelling both yt-dlp and FFmpeg children."""
import os
from pathlib import Path
import sys
import shutil
import yt_dlp


def main(url, folder):
    suffix = '.exe' if os.name == 'nt' else ''
    executable_root = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
    local_ffmpeg = executable_root / ('ffmpeg' + suffix)
    ffmpeg = str(local_ffmpeg) if local_ffmpeg.is_file() else shutil.which('ffmpeg')
    if not ffmpeg:
        raise ValueError('FFmpeg is required')
    options = {'outtmpl': str(Path(folder) / '%(title).80s_%(id)s.%(ext)s'),
               'noplaylist': True, 'merge_output_format': 'mp4',
               'format': 'bv*[height<=1080]+ba/b[height<=1080]/best',
               'ffmpeg_location': str(Path(ffmpeg).parent),
               'socket_timeout': 30, 'retries': 2, 'fragment_retries': 2,
               'quiet': True, 'no_warnings': True, 'continuedl': True,
               'overwrites': False}
    cookie = os.environ.get('YTDLP_COOKIES_FILE', '')
    if cookie:
        options['cookiefile'] = cookie
    with yt_dlp.YoutubeDL(options) as downloader:
        downloader.download([url])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
