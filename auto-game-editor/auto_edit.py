"""Kéo video vào cửa sổ để tự dựng. Cần Python 3, FFmpeg và FFprobe."""
import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
from array import array

FF = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y"]
W, H, RATE = 80, 46, 2


def edit(source, target, report=print):
    info = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(source)
    ]))
    video = next(stream for stream in info["streams"] if stream["codec_type"] == "video"
                 and not stream.get("disposition", {}).get("attached_pic"))
    audio = any(stream["codec_type"] == "audio" for stream in info["streams"])
    duration = float(video.get("duration") or info["format"]["duration"])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Không đọc được thời lượng video.")
    index = video["index"]
    report("Đang tìm đoạn nổi bật…")
    raw = subprocess.check_output(FF + ["-i", str(source), "-map", f"0:{index}",
        "-vf", f"fps={RATE},scale={W}:{H},format=gray", "-an", "-threads", "1", "-f", "rawvideo", "-"])
    pcm = array("h")
    if audio:
        pcm.frombytes(subprocess.check_output(FF + ["-i", str(source), "-vn",
            "-ac", "1", "-ar", "2000", "-f", "s16le", "-"]))
        if __import__("sys").byteorder != "little":
            pcm.byteswap()

    stride = W * H
    face = [y * W + x for y in range(7, 20, 2) for x in range(1, 17, 2)]
    game = [y * W + x for y in range(4, 39, 3) for x in range(21, 76, 3)]
    scores = [0.0]
    for i in range(1, len(raw) // stride):
        now, before = i * stride, (i - 1) * stride
        reaction = sum(abs(raw[now+j] - raw[before+j]) for j in face) / len(face)
        action = sum(abs(raw[now+j] - raw[before+j]) for j in game) / len(game)
        samples = pcm[i * 1000:(i + 1) * 1000]
        volume = sum(abs(s) for s in samples) / max(1, len(samples))
        scores.append(1.2 * min(35, reaction) + 0.6 * min(28, action) + 0.008 * min(4500, volume))
    candidates = sorted(range(len(scores)), key=lambda i: sum(scores[max(0, i-1):i+2]), reverse=True)
    clips = []
    goal = min(7, max(1, round(duration / 18)))
    for i in candidates:
        peak = i / RATE
        length = min(8, duration)
        start = max(0, min(peak - 3, duration - length))
        if all(abs(start - other[0]) >= length + 0.5 for other in clips):
            clips.append((start, length, peak - start))
        if len(clips) >= goal:
            break
    clips.sort()

    with tempfile.TemporaryDirectory(prefix="auto_edit_") as directory:
        folder = Path(directory)
        for n, (start, length, peak) in enumerate(clips):
            report(f"Đang dựng đoạn {n+1}/{len(clips)}…")
            onset = max(0.25, min(peak - 0.40, length - 1.8))
            # Hard cut on stronger punch-ins, eased push on alternating clips.
            ramp = 0.23 if n % 3 == 1 else 0.001
            factor = 2.5 if n % 3 == 2 else 1.85
            progress = f"clip((on/30-{onset:.3f})/{ramp},0,1)"
            zoom = f"if(between(on/30,{onset:.3f},{onset+1.45:.3f}),1+{factor-1}*(1-cos(PI*{progress}))/2,1)"
            filters = (
                "fps=30,scale=1280:720:force_original_aspect_ratio=decrease:"
                "force_divisible_by=2,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,"
                f"zoompan=z='{zoom}':x='clip(iw*.11-iw/zoom*.22,0,iw-iw/zoom)':"
                "y='clip(ih*.30-ih/zoom*.44,0,ih-ih/zoom)':d=1:s=1280x720:fps=30"
            )
            command = FF + ["-ss", str(start), "-i", str(source)]
            if not audio:
                command += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
            command += ["-map", f"0:{index}", "-map", "0:a:0" if audio else "1:a:0",
                        "-vf", filters, "-af", "apad,afade=t=in:d=0.025,"
                        f"afade=t=out:st={max(0, length-.04)}:d=0.04",
                        "-t", str(length), "-c:v", "libx264", "-preset", "veryfast",
                        "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000",
                        "-ac", "2", str(folder / f"{n}.mp4")]
            subprocess.run(command, check=True)
        listing = folder / "clips.txt"
        listing.write_text("".join(f"file '{n}.mp4'\n" for n in range(len(clips))), encoding="utf-8")
        subprocess.run(FF + ["-f", "concat", "-safe", "1", "-i", str(listing), "-c", "copy",
                             "-movflags", "+faststart", str(target)], check=True)
    report(f"Đã xuất {target}")


def gui():
    import tkinter as tk
    from tkinter import filedialog
    from tkinterdnd2 import DND_FILES, TkinterDnD
    import threading
    from queue import Empty, Queue

    root = TkinterDnD.Tk()
    root.title("Tự dựng highlight game")
    root.geometry("530x260")
    root.configure(bg="#111827")
    messages = Queue()
    busy = False
    status = tk.StringVar(value="MP4, MOV, MKV hoặc WebM")
    tk.Label(root, text="Tự dựng highlight game", bg="#111827", fg="#f9fafb",
             font=("Arial", 22, "bold")).pack(pady=(23, 12))
    zone = tk.Label(root, text="Thả một video vào đây", bg="#273449", fg="#ffffff",
                    font=("Arial", 15), padx=45, pady=24)
    zone.pack(fill="x", padx=28)
    tk.Label(root, textvariable=status, bg="#111827", fg="#e5e7eb", wraplength=460).pack(pady=8)

    def start(path):
        nonlocal busy
        if busy or not path:
            return
        source = Path(path)
        target = source.with_name(f"{source.stem}-highlight.mp4")
        suffix = 2
        while target.exists():
            target = source.with_name(f"{source.stem}-highlight-{suffix}.mp4")
            suffix += 1
        busy = True
        status.set("Đang mở video…")

        def run():
            try:
                edit(source, target, messages.put)
            except Exception as error:
                messages.put(f"Lỗi: {error}")
            finally:
                messages.put(None)

        threading.Thread(target=run, daemon=True).start()

    def drop(event):
        paths = root.tk.splitlist(event.data)
        if len(paths) == 1:
            start(paths[0])
        else:
            status.set("Mỗi lần chỉ thả một video.")

    def poll():
        nonlocal busy
        try:
            while True:
                message = messages.get_nowait()
                if message is None:
                    busy = False
                else:
                    status.set(message)
        except Empty:
            pass
        root.after(100, poll)

    zone.drop_target_register(DND_FILES)
    zone.dnd_bind("<<Drop>>", drop)
    tk.Button(root, text="Chọn video", command=lambda: start(filedialog.askopenfilename())).pack()
    poll()
    root.mainloop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("video", nargs="?", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not all(shutil.which(program) for program in ("ffmpeg", "ffprobe")):
        parser.exit(1, "Cần cài FFmpeg và FFprobe rồi thêm vào PATH.\n")
    if args.video:
        destination = (args.output or args.video.with_name(f"{args.video.stem}-highlight.mp4")).resolve()
        if destination.exists():
            parser.exit(1, "Tệp đầu ra đã tồn tại. Chọn đường dẫn khác.\n")
        edit(args.video, destination)
    else:
        gui()
