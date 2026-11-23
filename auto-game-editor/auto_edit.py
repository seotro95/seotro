"""Dựng nhiều video highlight từ một bản ghi gameplay dài."""
import argparse
from array import array
from collections import defaultdict
import csv
from contextlib import closing

from audio_events import AudioEvents
from editing import bottom_filter, events_for_shot, select_shots, select_short_clips, time_test
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
ASSETS = Path(__file__).resolve().parent / "editor-assets"
AUTO = "Tự nhận diện"
FACE = [y * WIDTH + x for y in range(7, 20, 2) for x in range(1, 17, 2)]
GAME = [y * WIDTH + x for y in range(5, 40, 3) for x in range(22, 76, 3)]
LABELS = ("Phản ứng facecam", "Chuyển động gameplay", "Cao trào âm thanh")


def fixed_blocks(command, size):
    # Giữ một khối trong RAM và để FFmpeg đọc tuần tự cả bản ghi.
    with tempfile.TemporaryFile() as errors, subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=errors
    ) as process:
        try:
            while block := process.stdout.read(size):
                yield block
            if process.wait():
                errors.seek(max(0, errors.tell() - 8192))
                raise subprocess.CalledProcessError(process.returncode, command, stderr=errors.read())
        finally:
            if process.poll() is None:
                process.kill()


def error_message(error):
    if not isinstance(error, subprocess.CalledProcessError):
        return str(error), str(error)
    program = Path(error.cmd[0]).stem
    details = (error.stderr or b"").decode("utf-8", errors="replace").strip()
    heading = f"{program} thất bại (mã {error.returncode})"
    first = next((line.strip() for line in details.splitlines() if line.strip()), "")
    return (f"{program}: {first[:180]}" if first else heading,
            f"{heading}\n{details[-6000:]}" if details else heading)


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
            "-c:v", "png", "-f", "image2pipe", "-"], stderr=subprocess.PIPE)
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
        features.append([face, game, 0.0, sum(frame[::32]) / len(frame[::32])])
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


def plan(features, duration, lengths, profile, has_facecam, short_clips=False):
    weights = PROFILES[profile]
    baselines = []
    for column, floor in enumerate((1.5, 2.0, 120.0)):
        values = sorted(row[column] for row in features)
        baselines.append(max(floor, values[len(values)*3//4]))
    scores, light, labels = [], [], []
    for second in range(min(math.floor(duration), len(features) // RATE)):
        section = features[second*RATE:(second+1)*RATE]
        face, game, volume, brightness = [sum(series)/RATE for series in zip(*section)]
        signals = (.65*face if has_facecam else 0, game, volume)
        parts = [weight * min(4.0, value/base)
                 for value, base, weight in zip(signals, baselines, weights)]
        scores.append(sum(parts))
        light.append(brightness)
        labels.append(LABELS[max(range(3), key=parts.__getitem__)])
    if len(scores) < sum(lengths):
        raise ValueError("Không đủ khung hình cho số lượng và thời lượng yêu cầu.")
    if short_clips:
        return select_short_clips(scores, labels, len(lengths), lengths[0])
    return select_shots(scores, light, labels, lengths)


def render_clip(source, path, index, audio_index, shot, effects):
    start, length = shot.start, shot.length
    filters = ("fps=30,scale=1280:720:force_original_aspect_ratio=decrease:"
               "force_divisible_by=2,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1")
    filters += ",tpad=stop_mode=clone:stop_duration=1"
    command = FF + ["-ss", str(start), "-i", str(source)]
    if audio_index is None:
        command += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    graph = [f"[0:{index}]{filters}[base]"]
    foregrounds = []
    for name, width, height, y in (("near", 418, 310, "85-5*sin(t*2)"),
                                    ("speech", 896, 664, "35-9*sin(t*2)")):
        enabled = "+".join(time_test(e.start, e.end, "t") for e in effects if e.name == name)
        if enabled:
            foregrounds.append((width, height, y, enabled))
    game = "base"
    if foregrounds:
        # Khung webcam trong video mẫu ở bên trái, rộng 21%, từ 13% đến 40% chiều cao.
        labels = "".join(f"[camera{i}]" for i in range(len(foregrounds)))
        graph.append(f"[base]split={len(foregrounds)+1}[game]{labels}")
        game = "game"
        for i, (width, height, y, enabled) in enumerate(foregrounds):
            graph.append(f"[camera{i}]crop=270:200:0:92,scale={width}:{height},setsar=1[face{i}]")
            graph.append(f"[{game}][face{i}]overlay=x=0:y='{y}':enable='{enabled}'[view{i}]")
            game = f"view{i}"
    graph.append(f"[{game}]null{bottom_filter(effects)}[frame0]")
    layers = 0
    for name in ("laugh", "cry"):
        times = "+".join(time_test(e.start, e.end, "t") for e in effects if e.name == name)
        if not times:
            continue
        input_index = layers + (1 if audio_index is not None else 2)
        command += ["-i", str(ASSETS / (name + ".png"))]
        graph.append(f"[frame{layers}][{input_index}:v]overlay=W-w-30:30:enable='{times}'[frame{layers+1}]")
        layers += 1
    with tempfile.TemporaryDirectory(dir=path.parent) as folder:
        # Một số video dài có nhiều hiệu ứng, lưu filter vào tệp để tránh giới hạn lệnh Windows.
        script = Path(folder) / "filters.txt"
        script.write_text(";".join(graph), encoding="ascii")
        command += ["-filter_complex_threads", "1", "-/filter_complex", str(script),
                    "-map", f"[frame{layers}]",
                    "-map", f"0:{audio_index}" if audio_index is not None else "1:a:0",
                    "-af", f"apad,afade=t=in:d=0.025,afade=t=out:st={max(0,length-.04)}:d=0.04",
                    "-t", str(length), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-threads", "4", "-c:a", "aac", "-ar", "48000",
                    "-ac", "2", "-movflags", "+faststart", str(path)]
        try:
            subprocess.run(command, stderr=subprocess.PIPE, check=True)
        except subprocess.CalledProcessError as error:
            # Các bản FFmpeg trước khi có cú pháp đọc tùy chọn từ tệp vẫn dùng tên cũ.
            if b"Unrecognized option '/filter_complex'" not in (error.stderr or b""):
                raise
            command[command.index("-/filter_complex")] = "-filter_complex_script"
            subprocess.run(command, stderr=subprocess.PIPE, check=True)


def edit(source, destination, count, minutes, game, facecam=True, report=print, durations=None,
         clip_seconds=None):
    if clip_seconds is None:
        minutes_by_video = list(durations) if durations is not None else [minutes] * count
        if not minutes_by_video or any(not math.isfinite(m) or m < 1/60 for m in minutes_by_video):
            raise ValueError("Mỗi video cần ít nhất một giây.")
        lengths = [round(m * 60) for m in minutes_by_video]
    else:
        if count < 1 or clip_seconds not in (5, 6, 7):
            raise ValueError("Chọn số clip hợp lệ và độ dài 5, 6 hoặc 7 giây.")
        lengths = [clip_seconds] * count
    count = len(lengths)
    info = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(source)
    ], stderr=subprocess.PIPE))
    video = next((s for s in info["streams"] if s["codec_type"] == "video"
                  and not s.get("disposition", {}).get("attached_pic")), None)
    if video is None:
        raise ValueError("Tệp không có luồng video.")
    audio_index = next((s["index"] for s in info["streams"] if s["codec_type"] == "audio"), None)
    durations = (video.get("duration"), info.get("format", {}).get("duration"))
    duration = float(next((value for value in durations if value and value != "N/A"), 0))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Không đọc được thời lượng nguồn.")
    if sum(lengths) > math.floor(duration):
        raise ValueError(f"Cần ít nhất {sum(lengths)/60:.2f} phút nguồn để không dùng lại đoạn.")
    title, profile = game_profile(source, duration, video["index"], game, report)
    features = scan(source, video["index"], audio_index, duration, report)
    timeline = plan(features, duration, lengths, profile, facecam, clip_seconds is not None)
    if destination.exists():
        raise FileExistsError(f"Đích đã tồn tại: {destination}")

    audio_events = None
    if audio_index is not None:
        try:
            audio_events = AudioEvents()
        except (ImportError, OSError, RuntimeError, ValueError) as error:
            report(f"Chưa có nhận diện giọng/cảm xúc. Chạy Cai-dat.cmd ({error}).")

    with tempfile.TemporaryDirectory(prefix=".highlight-", dir=destination.parent) as staging:
        stage = Path(staging)
        publish = stage / "result"
        publish.mkdir()
        rows = []
        effect_rows = []
        for n, clips in enumerate(timeline, 1):
            with tempfile.TemporaryDirectory(dir=stage) as parts:
                folder = Path(parts)
                offset = 0
                for i, clip in enumerate(clips):
                    report(f"{title} · Đang dựng video {n}/{count}, đoạn {i+1}/{len(clips)}")
                    speech, stickers = [], []
                    if audio_events:
                        lead = min(6, clip.start) if facecam else 0
                        speech, stickers = audio_events.read(
                            source, audio_index, clip.start-lead, clip.length+lead
                        )
                        speech = [time-lead for time in speech]
                        stickers = [(time-lead, name, score) for time, name, score in stickers if time >= lead]
                    effects = events_for_shot(clip.length, offset, lengths[n-1], facecam, speech, stickers)
                    render_clip(source, folder/f"{i}.mp4", video["index"], audio_index, clip, effects)
                    rows.append([n, offset, offset+clip.length, clip.start, clip.start+clip.length,
                                 clip.label, title, profile])
                    effect_rows.extend([n, e.name, offset+e.start, offset+e.end, e.zoom] for e in effects)
                    offset += clip.length
                output_path = publish/f"highlight-{n:02}.mp4"
                if len(clips) == 1:
                    (folder/"0.mp4").rename(output_path)
                    continue
                listing = folder/"clips.txt"
                listing.write_text("".join(f"file '{i}.mp4'\nduration {clip.length}\n"
                                           for i, clip in enumerate(clips)), encoding="utf-8")
                subprocess.run(FF + ["-f", "concat", "-safe", "1", "-i", str(listing),
                    "-c", "copy", "-movflags", "+faststart", str(output_path)], stderr=subprocess.PIPE, check=True)
        with (publish/"timeline.csv").open("w", encoding="utf-8-sig", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(["Video", "Đầu ra bắt đầu (s)", "Đầu ra kết thúc (s)",
                "Nguồn bắt đầu (s)", "Nguồn kết thúc (s)", "Tín hiệu nổi bật", "Game", "Thể loại"])
            writer.writerows(rows)
        with (publish/"effects.csv").open("w", encoding="utf-8-sig", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(["Video", "Hiệu ứng", "Bắt đầu (s)", "Kết thúc (s)", "Mức zoom"])
            writer.writerows(effect_rows)
        publish.rename(destination)
    report(f"Xong {count} video · {title} · {destination}")


def destination_for(source, parent=None):
    parent = parent or source.parent
    folder = parent / f"{source.stem}-highlights"
    number = 2
    while folder.exists():
        folder = parent / f"{source.stem}-highlights-{number}"
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
    root.minsize(620, 500)
    root.configure(bg="#111827")
    messages = Queue()
    busy = False
    count = tk.StringVar(value="1")
    minutes = tk.StringVar(value="5")
    short_seconds = tk.StringVar(value="6")
    short_mode = tk.BooleanVar(value=False)
    game = tk.StringVar(value=AUTO)
    facecam = tk.BooleanVar(value=True)
    status = tk.StringVar(value="MP4, MOV, MKV hoặc WebM")
    error_details = ""
    output_dir = tk.StringVar(value="")
    output_label = tk.StringVar(value="Cạnh video gốc")
    duration_label = tk.StringVar(value="Đang dùng số phút mặc định")
    overrides = []
    tk.Label(root, text="Tự dựng highlight gameplay", bg="#111827", fg="#f9fafb",
             font=("Arial", 22, "bold")).pack(pady=(23, 14))
    settings = ttk.Frame(root, padding=12)
    settings.pack(fill="x", padx=28, pady=(0, 12))
    ttk.Label(settings, text="Số video").grid(row=0, column=0, sticky="w", padx=(0, 10))
    ttk.Spinbox(settings, from_=1, to=1000, textvariable=count, width=8).grid(row=0, column=1, sticky="w")
    time_label = ttk.Label(settings, text="Phút mặc định")
    time_label.grid(row=0, column=2, sticky="w", padx=(14, 8))
    minutes_field = ttk.Entry(settings, textvariable=minutes, width=9)
    minutes_field.grid(row=0, column=3, sticky="w")
    seconds_field = ttk.Spinbox(settings, from_=5, to=7, textvariable=short_seconds, width=9)
    seconds_field.grid(row=0, column=3, sticky="w")
    seconds_field.grid_remove()
    ttk.Label(settings, text="Game / thể loại").grid(row=1, column=0, sticky="w", pady=8)
    ttk.Combobox(settings, values=(AUTO, *GAMES, *PROFILES), textvariable=game, width=28).grid(
        row=1, column=1, columnspan=3, sticky="w", pady=8
    )
    ttk.Checkbutton(settings, text="Đổi góc facecam bên trái mỗi 3 giây", variable=facecam).grid(
        row=2, column=0, columnspan=4, sticky="w"
    )
    def choose_output():
        current = output_dir.get()
        path = filedialog.askdirectory(parent=root, initialdir=current or str(Path.home()), mustexist=True)
        if path:
            output_dir.set(path)
            output_label.set(path)

    def edit_durations():
        try:
            amount = int(count.get())
            if not 1 <= amount <= 1000:
                raise ValueError
        except ValueError:
            status.set("Nhập số video từ 1 đến 1000.")
            return
        dialog = tk.Toplevel(root)
        dialog.title("Thời lượng từng video")
        dialog.transient(root)
        dialog.grab_set()
        body = ttk.Frame(dialog, padding=14)
        body.pack(fill="both", expand=True)
        canvas = tk.Canvas(body, width=295, height=min(310, 38*amount), highlightthickness=0)
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        fields = ttk.Frame(canvas, padding=(8, 4))
        canvas.create_window((0, 0), window=fields, anchor="nw")
        fields.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        variables = []
        for i in range(amount):
            value = overrides[i] if i < len(overrides) else ""
            var = tk.StringVar(master=dialog, value=value)
            variables.append(var)
            ttk.Label(fields, text=f"Video {i+1}").grid(row=i, column=0, padx=(0, 20), pady=5)
            ttk.Entry(fields, textvariable=var, width=12).grid(row=i, column=1, pady=5)
            ttk.Label(fields, text="phút").grid(row=i, column=2, padx=8)
        message = tk.StringVar(master=dialog, value="Để trống để dùng số phút mặc định.")
        ttk.Label(body, textvariable=message).grid(row=1, column=0, columnspan=2, pady=(8, 2))

        def save():
            values = [var.get().strip() for var in variables]
            try:
                for value in values:
                    if value:
                        read_minutes(value)
            except ValueError:
                message.set("Mỗi thời lượng phải từ một giây trở lên.")
                return
            overrides[:] = values
            duration_label.set(f"{sum(bool(value) for value in values)} video có thời lượng riêng")
            dialog.destroy()

        ttk.Button(body, text="Lưu thời lượng", command=save).grid(row=2, column=0, pady=(8, 0))
        dialog.bind("<Escape>", lambda _event: dialog.destroy())

    def read_minutes(value):
        result = float(value.replace(",", "."))
        if not math.isfinite(result) or result < 1/60:
            raise ValueError
        return result

    duration_button = ttk.Button(settings, text="Chỉnh phút từng video…", command=edit_durations)
    duration_button.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))
    duration_hint = ttk.Label(settings, textvariable=duration_label)
    duration_hint.grid(row=3, column=2, columnspan=2, sticky="w", padx=(14, 0), pady=(8, 0))
    ttk.Button(settings, text="Chọn thư mục lưu…", command=choose_output).grid(
        row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))
    ttk.Label(settings, textvariable=output_label, wraplength=310).grid(
        row=4, column=2, columnspan=2, sticky="w", padx=(14, 0), pady=(8, 0))

    def set_export_mode():
        if short_mode.get():
            time_label.configure(text="Giây mỗi clip")
            minutes_field.grid_remove()
            seconds_field.grid()
            duration_button.grid_remove()
            duration_hint.grid_remove()
        else:
            time_label.configure(text="Phút mặc định")
            minutes_field.grid()
            seconds_field.grid_remove()
            duration_button.grid()
            duration_hint.grid()

    ttk.Checkbutton(settings, text="Xuất từng clip 5–7 giây", variable=short_mode,
                    command=set_export_mode).grid(row=5, column=0, columnspan=4, sticky="w", pady=(8, 0))

    zone = tk.Label(root, text="Thả một video vào đây", bg="#26354d", fg="#ffffff",
                    font=("Arial", 16), pady=21)
    zone.pack(fill="x", padx=28)
    tk.Label(root, textvariable=status, bg="#111827", fg="#e5e7eb", wraplength=520).pack(pady=9)

    def start(path):
        nonlocal busy, error_details
        if busy or not path:
            return
        try:
            amount = int(count.get())
            if not 1 <= amount <= 1000:
                raise ValueError
            clip_length = int(short_seconds.get()) if short_mode.get() else None
            if clip_length is not None and clip_length not in (5, 6, 7):
                raise ValueError
            lengths = None
            if clip_length is None:
                values = (overrides + [""]*amount)[:amount]
                lengths = [read_minutes(value or minutes.get()) for value in values]
            title = game.get().strip() or AUTO
            with_facecam = facecam.get()
        except ValueError:
            status.set("Nhập số clip hợp lệ và độ dài 5, 6 hoặc 7 giây." if short_mode.get()
                       else "Nhập số video hợp lệ và thời lượng từ một giây trở lên.")
            return
        source = Path(path)
        parent = Path(output_dir.get()) if output_dir.get() else None
        target = destination_for(source, parent)
        busy = True
        error_details = ""
        copy_error.pack_forget()
        status.set("Đang mở video…")

        def run():
            try:
                edit(source, target, amount, 1, title, with_facecam, messages.put,
                     durations=lengths, clip_seconds=clip_length)
            except Exception as error:
                messages.put(error_message(error))
            finally:
                messages.put(None)

        threading.Thread(target=run, daemon=True).start()

    def drop(event):
        paths = root.tk.splitlist(event.data)
        if len(paths) == 1:
            start(paths[0])
        elif not busy:
            status.set("Mỗi lần chỉ thả một video.")

    def copy_error_text():
        if error_details:
            root.clipboard_clear()
            root.clipboard_append(error_details)
            copy_error.configure(text="Đã sao chép lỗi")

    def poll():
        nonlocal busy, error_details
        try:
            while True:
                message = messages.get_nowait()
                if message is None:
                    busy = False
                elif isinstance(message, tuple):
                    summary, error_details = message
                    status.set(f"Lỗi: {summary}")
                    copy_error.configure(text="Sao chép lỗi")
                    copy_error.pack(side="left", padx=4)
                else:
                    status.set(message)
        except Empty:
            pass
        root.after(100, poll)

    zone.drop_target_register(DND_FILES)
    zone.dnd_bind("<<Drop>>", drop)
    actions = ttk.Frame(root)
    actions.pack()
    ttk.Button(actions, text="Chọn video", command=lambda: start(filedialog.askopenfilename())).pack(side="left", padx=4)
    copy_error = ttk.Button(actions, text="Sao chép lỗi", command=copy_error_text)
    root.after_idle(root.lift)
    poll()
    root.mainloop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", nargs="?", type=Path)
    parser.add_argument("--output", type=Path, help="Thư mục kết quả")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--minutes", type=float, default=1)
    parser.add_argument("--durations", type=float, nargs="+", help="Số phút riêng của từng video")
    parser.add_argument("--clip-seconds", type=int, choices=(5, 6, 7),
                        help="Xuất từng clip riêng với độ dài này, dùng cùng --count")
    parser.add_argument("--game", default=AUTO, help="Tên game hoặc thể loại")
    parser.add_argument("--no-facecam", action="store_true")
    args = parser.parse_args()
    if not all(shutil.which(program) for program in ("ffmpeg", "ffprobe")):
        parser.exit(1, "Cần cài FFmpeg và FFprobe rồi thêm vào PATH.\n")
    if args.video:
        try:
            source = args.video.resolve()
            destination = (args.output or destination_for(source)).resolve()
            edit(source, destination, args.count, args.minutes, args.game, not args.no_facecam,
                 durations=args.durations, clip_seconds=args.clip_seconds)
        except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError) as error:
            _, details = error_message(error)
            parser.exit(1, f"{details}\n")
    else:
        gui()
