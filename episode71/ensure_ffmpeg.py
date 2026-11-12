import os,shutil,subprocess,sys
from pathlib import Path
if shutil.which('ffmpeg'):
 print('Existing FFmpeg ready',flush=True)
else:
 import imageio_ffmpeg
 binary=Path(imageio_ffmpeg.get_ffmpeg_exe()).resolve();assert binary.is_file()
 subprocess.run([str(binary),'-version'],stdout=subprocess.DEVNULL,check=True)
 folder=Path(os.environ['RUNNER_TEMP'])/'episode71-ffmpeg';folder.mkdir(exist_ok=True)
 link=folder/'ffmpeg'
 if not link.exists():link.symlink_to(binary)
 with open(os.environ['GITHUB_PATH'],'a') as f:f.write(str(folder)+'\n')
 print('Portable FFmpeg runtime verified and added to PATH',flush=True)
