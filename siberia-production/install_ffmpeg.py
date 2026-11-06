"""Install a checksum-pinned upstream Linux build for the Actions render job."""
from pathlib import Path
import hashlib,os,shutil,tarfile,urllib.request
root=Path(os.environ['RUNNER_TEMP'])/'ffmpeg-pinned';root.mkdir(exist_ok=True)
archive=root/'ffmpeg.tar.xz'
url='https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-11-06-12-50/ffmpeg-N-128532-g5d85b7bfb2-linux64-gpl.tar.xz'
sha='fa95d3919f4c18b0dab1528daed98456c5f54d777838d4eb1bbc40c53a730302'
with urllib.request.urlopen(url,timeout=180) as response,archive.open('wb') as dest:shutil.copyfileobj(response,dest)
assert hashlib.sha256(archive.read_bytes()).hexdigest()==sha,'FFmpeg archive checksum mismatch'
with tarfile.open(archive,'r:xz') as tar:tar.extractall(root,filter='data')
binary=next(root.rglob('ffmpeg'));binary.chmod(0o755)
probe=next(root.rglob('ffprobe'));probe.chmod(0o755)
with open(os.environ['GITHUB_PATH'],'a') as f:f.write(str(binary.parent)+'\n')
print('Pinned FFmpeg / FFprobe installed from their verified upstream archive.')
