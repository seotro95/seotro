"""Dựng nhiều video highlight từ một bản ghi gameplay dài."""
import argparse
from array import array
from collections import defaultdict
import csv
from contextlib import closing
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

FF = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y"]
WIDTH, HEIGHT, RATE = 80, 46, 2
PROFILES = {
    "Tổng hợp": (1.0, 1.0, 1.0),
    "Kinh dị": (1.2, 0.65, 1.4),
    "Bắn súng": (0.70, 1.45, 1.0),
    "MOBA": (0.65, 1.60, 0.85),
    "Sinh tồn / Sandbox": (1.0, 1.1, 0.8),
    "Đua xe / Thể thao": (0.65, 1.40, 1.0),
}
GAMES = {
    "Minecraft": "Sinh tồn / Sandbox",
    "Roblox": "Sinh tồn / Sandbox",
    "The Forest": "Sinh tồn / Sandbox",
    "Sons of the Forest": "Sinh tồn / Sandbox",
    "Phasmophobia": "Kinh dị",
    "Lethal Company": "Kinh dị",
    "Outlast": "Kinh dị",
    "Valorant": "Bắn súng",
    "Counter-Strike 2": "Bắn súng",
    "Fortnite": "Bắn súng",
    "PUBG": "Bắn súng",
    "Call of Duty": "Bắn súng",
    "League of Legends": "MOBA",
    "Dota 2": "MOBA",
    "Forza Horizon": "Đua xe / Thể thao",
    "EA Sports FC": "Đua xe / Thể thao",
}
AUTO = "Tự nhận diện"
FACE = [y * WIDTH + x for y in range(7, 20, 2) for x in range(1, 17, 2)]
GAME = [y * WIDTH + x for y in range(5, 40, 3) for x in range(22, 76, 3)]
LABELS = ("Phản ứng facecam", "Chuyển động gameplay", "Cao trào âm thanh")


def fixed_blocks(command, size):
    # Giữ một khối trong RAM và để FFmpeg đọc tuần tự cả bản ghi.
    with subprocess.Popen(command, stdout=subprocess.PIPE) as process:
        try:
            while block := process.stdout.read(size):
                yield block
            if process.wait():
                raise RuntimeError("FFmpeg không đọc hết video. Hãy kiểm tra tệp nguồn.")
        finally:
            if process.poll() is None:
                process.kill()


def normalize(text):
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def game_profile(source, duration, video_index, game, report):
    if game in PROFILES:
        return game, game
    for title, profile in GAMES.items():
        if normalize(game) == normalize(title):
            return title, profile
    if game != AUTO:
        return game, "Tổng hợp"
    if not shutil.which("tesseract"):
        report("Chưa có Tesseract. Dùng cấu hình Tổng hợp.")
        return "Chưa nhận diện", "Tổng hợp"

    report("Đang tìm tên game trên các khung hình…")
    evidence = defaultdict(int)
    for moment in sorted({0, min(5, duration/4), min(30, duration/2), duration*.25, duration*.5, duration*.75}):
        still = subprocess.check_output(FF + ["-ss", str(moment), "-i", str(source),
            "-map", f"0:{video_index}", "-frames:v", "1", "-vf", "scale=960:-2",
            "-c:v", "png", "-f", "image2pipe", "-"])
        if not still:
            continue
        ocr = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "11"], input=still,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        words = f" {normalize(ocr.stdout.decode('utf-8', errors='replace'))} "
        for title in GAMES:
            if f" {normalize(title)} " in words:
                evidence[title] += 1
    if evidence:
        titles = sorted(evidence, key=evidence.get, reverse=True)
        if len(titles) == 1 or evidence[titles[0]] > evidence[titles[1]]:
            return titles[0], GAMES[titles[0]]
    return "Chưa nhận diện", "Tổng hợp"


def scan(source, index, audio_index, duration, report):
    report("Đang phân tích chuyển động…")
    stride = WIDTH * HEIGHT
    previous = None
    features = []
    command = FF + ["-i", str(source), "-map", f"0:{index}", "-vf",
        f"fps={RATE},scale={WIDTH}:{HEIGHT},format=gray",
        "-an", "-threads", "1", "-f", "rawvideo", "-"]
    for i, frame in enumerate(fixed_blocks(command, stride)):
        if len(frame) != stride:
            break
        face = game = 0
        if previous is not None:
            face = sum(abs(frame[j] - previous[j]) for j in FACE) / len(FACE)
            game = sum(abs(frame[j] - previous[j]) for j in GAME) / len(GAME)
        features.append([face, game, 0.0])
        previous = frame
        if i and i % 600 == 0:
            report(f"Đang đọc hình ảnh · {min(100, int(i/RATE/duration*100))}%")
    if not features:
        raise ValueError("Không tìm thấy khung hình để phân tích.")

    if audio_index is not None:
        report("Đang phân tích âm thanh…")
        command = FF + ["-i", str(source), "-map", f"0:{audio_index}", "-vn",
                        "-ac", "1", "-ar", "2000", "-f", "s16le", "-"]
        audio_blocks = fixed_blocks(command, 4000 // RATE)
        with closing(audio_blocks):
            for i, block in enumerate(audio_blocks):
                if i >= len(features):
                    break
                samples = array("h")
                samples.frombytes(block)
                if sys.byteorder != "little":
                    samples.byteswap()
                features[i][2] = sum(abs(value) for value in samples) / max(1, len(samples))
                if i and i % 600 == 0:
                    report(f"Đang đọc âm thanh · {min(100, int(i/RATE/duration*100))}%")
    return features


def plan(features, duration, count, seconds, profile, has_facecam):
    weights = PROFILES[profile]
    baselines = []
    for column, floor in enumerate((1.5, 2.0, 120.0)):
        values = sorted(row[column] for row in features)
        baselines.append(max(floor, values[len(values)*3//4]))
    scores = []
    for face, game, volume in features:
        signals = (face if has_facecam else 0, game, volume)
        parts = [weight * min(4.0, value/base)
                 for value, base, weight in zip(signals, baselines, weights)]
        scores.append((sum(parts), max(range(3), key=parts.__getitem__)))
    length_count = max(1, math.ceil(seconds / 18))
    short, extras = divmod(seconds, length_count)
    lengths = [short+1] * extras + [short] * (length_count-extras)
    pool = defaultdict(list)
    for cycle_start in range(0, math.floor(duration)-seconds+1, seconds):
        start = cycle_start
        for length in lengths:
            first = start * RATE
            last = min(len(scores), (start + length) * RATE)
            if first < last:
                eligible = range(min(last-1, first+RATE), max(min(last-1, first+RATE)+1, last-RATE))
                peak = max(eligible, key=lambda i: sum(s[0] for s in scores[max(first,i-1):min(last,i+2)]))
                score = sum(s[0] for s in scores[max(first,peak-1):min(last,peak+2)]) / 3
                pool[length].append((score, start, length, peak/RATE-start, LABELS[scores[peak][1]]))
            start += length
    for length in pool:
        pool[length].sort(reverse=True)
    if any(len(pool[length]) < count * lengths.count(length) for length in set(lengths)):
        raise ValueError("Không đủ khung hình cho số lượng và thời lượng đã yêu cầu.")
    outputs = [[] for _ in range(count)]
    for length in set(lengths):
        for i, clip in enumerate(pool[length][:count * lengths.count(length)]):
            outputs[i % count].append(clip)
    return [sorted(clips, key=lambda clip: clip[1]) for clips in outputs]


def render_clip(source, path, index, audio_index, clip, serial, facecam):
    _, start, length, peak, label = clip
    onset = max(.10, min(peak - .40, length-1.8))
    hold = min(1.7 if serial % 4 == 2 else 1.43, length-onset)
    zoom = facecam and length >= 2
    factor = 4.23 if serial % 4 == 2 else (1.95 if serial % 4 == 1 else 1.85)
    ramp = .22 if serial % 4 == 1 else .001
    filters = ("fps=30,scale=1280:720:force_original_aspect_ratio=decrease:"
               "force_divisible_by=2,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1")
    if zoom:
        progress = f"clip((on/30-{onset:.3f})/{ramp},0,1)"
        curve = f"if(between(on/30,{onset:.3f},{onset+hold:.3f}),1+{factor-1}*(1-cos(PI*{progress}))/2,1)"
        filters += (f",zoompan=z='{curve}':x='clip(iw*.10-iw/zoom*.44,0,iw-iw/zoom)':"
                    "y='clip(ih*.31-ih/zoom*.49,0,ih-ih/zoom)':d=1:s=1280x720:fps=30")
    command = FF + ["-ss", str(start), "-i", str(source)]
    if audio_index is None:
        command += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    command += ["-map", f"0:{index}", "-map", f"0:{audio_index}" if audio_index is not None else "1:a:0",
                "-vf", filters + ",tpad=stop_mode=clone:stop_duration=1",
                "-af", f"apad,afade=t=in:d=0.025,afade=t=out:st={max(0,length-.04)}:d=0.04",
                "-t", str(length), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-pix_fmt", "yuv420p", "-threads", "4", "-c:a", "aac", "-ar", "48000",
                "-ac", "2", str(path)]
    subprocess.run(command, check=True)
    return (round(onset, 3), round(onset+hold, 3), factor) if zoom else ("", "", "")


def edit(source, destination, count, minutes, game, facecam=True, report=print):
    if count < 1 or not math.isfinite(minutes) or minutes <= 0:
        raise ValueError("Số video và số phút phải lớn hơn 0.")
    seconds = round(minutes * 60)
    if not seconds:
        raise ValueError("Thời lượng tối thiểu là một giây.")
    info = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(source)
    ]))
    video = next((s for s in info["streams"] if s["codec_type"] == "video"
                  and not s.get("disposition", {}).get("attached_pic")), None)
    if video is None:
        raise ValueError("Tệp không có luồng video.")
    audio_index = next((s["index"] for s in info["streams"] if s["codec_type"] == "audio"), None)
    durations = (video.get("duration"), info.get("format", {}).get("duration"))
    duration = float(next((value for value in durations if value and value != "N/A"), 0))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Không đọc được thời lượng nguồn.")
    if count * seconds > math.floor(duration):
        raise ValueError(f"Cần ít nhất {count*seconds/60:.2f} phút nguồn để không dùng lại đoạn.")
    title, profile = game_profile(source, duration, video["index"], game, report)
    features = scan(source, video["index"], audio_index, duration, report)
    timeline = plan(features, duration, count, seconds, profile, facecam)
    if destination.exists():
        raise FileExistsError(f"Đích đã tồn tại: {destination}")

    with tempfile.TemporaryDirectory(prefix=".highlight-", dir=destination.parent) as staging:
        stage = Path(staging)
        publish = stage / "result"
        publish.mkdir()
        rows = []
        for n, clips in enumerate(timeline, 1):
            with tempfile.TemporaryDirectory(dir=stage) as parts:
                folder = Path(parts)
                offset = 0
                for i, clip in enumerate(clips):
                    report(f"{title} · Đang dựng video {n}/{count}, đoạn {i+1}/{len(clips)}")
                    a, b, scale = render_clip(source, folder/f"{i}.mp4", video["index"],
                                              audio_index, clip, i, facecam)
                    _, start, length, _, label = clip
                    rows.append([n, offset, offset+length, start, start+length,
                                 "" if a == "" else round(offset+a, 3),
                                 "" if b == "" else round(offset+b, 3), scale, label, title, profile])
                    offset += length
                listing = folder/"clips.txt"
                listing.write_text("".join(f"file '{i}.mp4'\nduration {clip[2]}\n"
                                           for i, clip in enumerate(clips)), encoding="utf-8")
                subprocess.run(FF + ["-f", "concat", "-safe", "1", "-i", str(listing),
                    "-c", "copy", "-movflags", "+faststart", str(publish/f"highlight-{n:02}.mp4")], check=True)
        with (publish/"timeline.csv").open("w", encoding="utf-8-sig", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(["Video", "Đầu ra bắt đầu (s)", "Đầu ra kết thúc (s)",
                "Nguồn bắt đầu (s)", "Nguồn kết thúc (s)", "Vào zoom (s)", "Về toàn cảnh (s)",
                "Mức zoom", "Tín hiệu nổi bật", "Game", "Thể loại"])
            writer.writerows(rows)
        publish.rename(destination)
    report(f"Xong {count} video · {title} · {destination}")


def destination_for(source):
    folder = source.with_name(f"{source.stem}-highlights")
    number = 2
    while folder.exists():
        folder = source.with_name(f"{source.stem}-highlights-{number}")
        number += 1
    return folder


def gui():
    import tkinter as tk
    from tkinter import filedialog, ttk
    from tkinterdnd2 import DND_FILES, TkinterDnD
    import threading
    from queue import Empty, Queue

    root = TkinterDnD.Tk()
    root.title("Tự dựng highlight gameplay")
    root.minsize(580, 390)
    root.configure(bg="#111827")
    messages = Queue()
    busy = False
    count = tk.StringVar(value="1")
    minutes = tk.StringVar(value="5")
    game = tk.StringVar(value=AUTO)
    facecam = tk.BooleanVar(value=True)
    status = tk.StringVar(value="MP4, MOV, MKV hoặc WebM")
    tk.Label(root, text="Tự dựng highlight gameplay", bg="#111827", fg="#f9fafb",
             font=("Arial", 22, "bold")).pack(pady=(23, 14))
    settings = ttk.Frame(root, padding=12)
    settings.pack(fill="x", padx=28, pady=(0, 12))
    ttk.Label(settings, text="Số video").grid(row=0, column=0, sticky="w", padx=(0, 10))
    ttk.Spinbox(settings, from_=1, to=1000, textvariable=count, width=8).grid(row=0, column=1, sticky="w")
    ttk.Label(settings, text="Phút mỗi video").grid(row=0, column=2, sticky="w", padx=(14, 8))
    ttk.Entry(settings, textvariable=minutes, width=9).grid(row=0, column=3, sticky="w")
    ttk.Label(settings, text="Game / thể loại").grid(row=1, column=0, sticky="w", pady=8)
    ttk.Combobox(settings, values=(AUTO, *GAMES, *PROFILES), textvariable=game, width=28).grid(
        row=1, column=1, columnspan=3, sticky="w", pady=8
    )
    ttk.Checkbutton(settings, text="Zoom facecam bên trái", variable=facecam).grid(
        row=2, column=0, columnspan=4, sticky="w"
    )
    zone = tk.Label(root, text="Thả một video vào đây", bg="#26354d", fg="#ffffff",
                    font=("Arial", 16), pady=21)
    zone.pack(fill="x", padx=28)
    tk.Label(root, textvariable=status, bg="#111827", fg="#e5e7eb", wraplength=520).pack(pady=9)

    def start(path):
        nonlocal busy
        if busy or not path:
            return
        try:
            amount = int(count.get())
            length = float(minutes.get().replace(",", "."))
            title = game.get().strip() or AUTO
            with_facecam = facecam.get()
            if amount < 1 or not math.isfinite(length) or length <= 0:
                raise ValueError()
        except ValueError:
            status.set("Nhập số video nguyên dương và số phút lớn hơn 0.")
            return
        source = Path(path)
        target = destination_for(source)
        busy = True
        status.set("Đang mở video…")

        def run():
            try:
                edit(source, target, amount, length, title, with_facecam, messages.put)
            except Exception as error:
                status_detail = str(error)
                if isinstance(error, subprocess.CalledProcessError):
                    status_detail = f"FFmpeg xử lý thất bại (mã {error.returncode})."
                messages.put(f"Lỗi: {status_detail}")
            finally:
                messages.put(None)

        threading.Thread(target=run, daemon=True).start()

    def drop(event):
        paths = root.tk.splitlist(event.data)
        if len(paths) == 1:
            start(paths[0])
        elif not busy:
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
    ttk.Button(root, text="Chọn video", command=lambda: start(filedialog.askopenfilename())).pack()
    poll()
    root.mainloop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", nargs="?", type=Path)
    parser.add_argument("--output", type=Path, help="Thư mục kết quả")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--minutes", type=float, default=1)
    parser.add_argument("--game", default=AUTO, help="Tên game hoặc thể loại")
    parser.add_argument("--no-facecam", action="store_true")
    args = parser.parse_args()
    if not all(shutil.which(program) for program in ("ffmpeg", "ffprobe")):
        parser.exit(1, "Cần cài FFmpeg và FFprobe rồi thêm vào PATH.\n")
    if args.video:
        try:
            source = args.video.resolve()
            destination = (args.output or destination_for(source)).resolve()
            edit(source, destination, args.count, args.minutes, args.game, not args.no_facecam)
        except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError) as error:
            parser.exit(1, f"{error}\n")
    else:
        gui()
