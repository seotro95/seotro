"""Quét từng khung hình và xuất bảng các mốc cần kiểm tra theo từng giây."""
import argparse
import csv
import math
from pathlib import Path
import re
import subprocess
from collections import defaultdict

import cv2
import numpy as np


def match_scale(before, after, features, matcher):
    def describe(frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (480, max(1, round(480 * gray.shape[0] / gray.shape[1]))))
        return features.detectAndCompute(resized, None)

    old_points, old_desc = describe(before)
    new_points, new_desc = describe(after)
    if old_desc is None or new_desc is None or len(new_desc) < 2:
        return None, 0
    matches = [row[0] for row in matcher.knnMatch(old_desc, new_desc, k=2)
               if len(row) == 2 and row[0].distance < 0.75 * row[1].distance]
    if len(matches) < 8:
        return None, 0
    old = np.float32([old_points[m.queryIdx].pt for m in matches])
    new = np.float32([new_points[m.trainIdx].pt for m in matches])
    affine, mask = cv2.estimateAffinePartial2D(old, new, ransacReprojThreshold=2.5)
    count = int(mask.sum()) if affine is not None else 0
    if count < 8:
        return None, count
    return math.hypot(affine[0, 0], affine[1, 0]), count


def analyze(source, output):
    source = source.resolve()
    scan = subprocess.check_output([
        "ffmpeg", "-v", "error", "-i", str(source), "-map", "0:v:0", "-an",
        "-vf", "setpts=PTS-STARTPTS,scale=320:-2,select='gt(scene,0.20)',metadata=print:file=-",
        "-f", "null", "-"
    ], text=True)
    candidates = [(float(t), float(s)) for t, s in re.findall(
        r"pts_time:([\d.]+)\s+lavfi\.scene_score=([\d.]+)", scan
    )]
    duration = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(source)
    ], text=True))
    cv2.setNumThreads(1)
    video = cv2.VideoCapture(str(source))
    if not video.isOpened():
        raise RuntimeError("OpenCV không mở được video.")
    features = cv2.SIFT_create(nfeatures=500)
    matcher = cv2.BFMatcher()
    events = defaultdict(list)
    candidate = 0
    previous = None
    try:
        while candidate < len(candidates):
            ok, current = video.read()
            if not ok:
                break
            timestamp = video.get(cv2.CAP_PROP_POS_MSEC) / 1000
            while candidate < len(candidates) and timestamp + 0.001 >= candidates[candidate][0]:
                time, score = candidates[candidate]
                scale, inliers = match_scale(previous, current, features, matcher) if previous is not None else (None, 0)
                if scale is None:
                    label = "Đổi hình mạnh, chưa rõ nguyên nhân"
                elif scale >= 1.20:
                    label = "Nghi phóng gần"
                elif scale <= 0.83:
                    label = "Nghi thu xa"
                else:
                    label = "Đổi hình, tỷ lệ khung gần như giữ nguyên"
                events[int(time)].append((time, score, scale, inliers, label))
                candidate += 1
            previous = current
    finally:
        video.release()

    for time, score in candidates[candidate:]:
        events[int(time)].append((time, score, None, 0, "Chưa đối chiếu được khung hình"))

    with output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Giây", "Mốc chính xác (giây)", "Điểm đổi hình", "Tỷ lệ sau / trước",
                         "Điểm ảnh đối sánh", "Phân loại gợi ý"])
        for second in range(math.ceil(duration)):
            for time, score, scale, inliers, label in events.get(
                    second, [(None, None, None, None, "Không có đổi hình vượt ngưỡng")]):
                writer.writerow([second, "" if time is None else f"{time:.3f}",
                                 "" if score is None else f"{score:.4f}",
                                 "" if scale is None else f"{scale:.2f}", inliers, label])
    print(f"Đã quét {math.ceil(duration)} giây, tìm thấy {len(candidates)} mốc đổi hình: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.video.with_name(f"{args.video.stem}-timeline.csv")
    if output.exists():
        parser.exit(1, "Tệp đầu ra đã tồn tại. Chọn đường dẫn khác.\n")
    analyze(args.video, output)
