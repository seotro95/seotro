"""Chọn nhóm cảnh liền mạch và lên lịch các góc camera."""
from collections import deque
from dataclasses import dataclass
from itertools import accumulate


@dataclass(frozen=True)
class Shot:
    start: int
    length: int
    label: str


@dataclass(frozen=True)
class Effect:
    name: str
    start: float
    end: float
    zoom: float = 1.0


GAPS = (0, 3, 5, 8, 12, 18, 25, 35, 45, 60)


def best_sequence(scores, light, labels, first, end, length):
    count = min(6 if length >= 60 else 5, max(1, length // 5))
    base, extra = divmod(length, count)
    lengths = [base+1]*extra + [base]*(count-extra)
    duration = end-first
    gaps = GAPS[1:] if duration >= length + 3*(count-1) else GAPS
    local = scores[first:end]
    prefix = list(accumulate(local, initial=0.0))
    lookup = {}
    for size in set(lengths):
        # Cửa sổ xếp hạng theo điểm cao trào và mức hoạt động cả đoạn.
        peaks = deque()
        windows = []
        for i, value in enumerate(local):
            while peaks and local[peaks[-1]] <= value:
                peaks.pop()
            peaks.append(i)
            start = i-size+1
            if start < 0:
                continue
            while peaks[0] < start:
                peaks.popleft()
            average = (prefix[i+1]-prefix[start])/size
            windows.append((.65*local[peaks[0]]+.35*average, peaks[0]))
        lookup[size] = windows

    backtracks = []
    previous = []
    elapsed = 0
    for stage, size in enumerate(lengths):
        remaining = length-elapsed-size
        current = [float("-inf")] * (duration-size-remaining+1)
        back = [-1] * len(current)
        for start in range(elapsed, len(current)):
            score = lookup[size][start][0]
            weight = 1 + .08*stage
            if not stage:
                current[start] = score*weight
                continue
            previous_size = lengths[stage-1]
            for gap in gaps:
                prior = start-previous_size-gap
                if not 0 <= prior < len(previous):
                    continue
                tail = prior+previous_size-1
                jump = abs(light[first+tail] - light[first+start]) / 255
                prior_score = lookup[previous_size][prior][0]
                gap_cost = (0.08 if gap == 0 else gap*0.006) if duration > length else 0
                value = previous[prior] + score*weight - .75*jump - gap_cost
                value += .08*min(2.0, max(-2.0, score-prior_score))
                if value > current[start]:
                    current[start], back[start] = value, prior
        previous = current
        elapsed += size
        backtracks.append(back)

    location = max(range(len(previous)), key=previous.__getitem__)
    if previous[location] == float("-inf"):
        raise ValueError("Không đủ hình ảnh để chọn nhóm cảnh.")
    shots = []
    for size, back in zip(reversed(lengths), reversed(backtracks)):
        _, peak = lookup[size][location]
        shots.append(Shot(first+location, size, labels[first+peak]))
        location = back[location]
    return list(reversed(shots))


def select_shots(scores, light, labels, lengths):
    # Chia các phần liên tiếp theo thời lượng yêu cầu, giữ video đầu ra không trùng nguồn.
    available = len(scores)
    total = sum(lengths)
    if available < total:
        raise ValueError("Không đủ khung hình cho số lượng và thời lượng yêu cầu.")
    outputs = []
    passed = first = 0
    for length in lengths:
        passed += length
        end = available*passed//total
        outputs.append(best_sequence(scores, light, labels, first, end, length))
        first = end
    return outputs


def events_for_shot(length, offset, total, facecam, speech, stickers):
    effects = []
    for minute in range(max(60, offset//60*60), min(total, offset+length), 60):
        start, end = max(0, minute-offset), min(length, minute+3-offset)
        if start < end:
            effects.append(Effect("bottom", start, end, 1.16))

    def free(start, end):
        return all(end <= e.start or start >= e.end for e in effects)

    if facecam:
        streak_start = last = None
        inserted = False
        for moment in speech:
            if last is None or moment-last > 1.0:
                streak_start, inserted = moment, False
            last = moment
            # Lời nói kéo dài ít nhất sáu giây, có thể có khoảng ngắt ngắn.
            if not inserted and moment-streak_start >= 5.5 and moment+2 <= length and free(moment, moment+2):
                effects.append(Effect("speech", moment, moment+2, 3.5))
                inserted = True

        # Ưu tiên điểm nối. Dịch sớm nếu trùng đoạn nói dài hoặc góc mép dưới.
        for start in range(length-5, -1, -1):
            if free(start, start+5):
                effects.extend((Effect("near", start, start+3, 1.95),
                                Effect("wide", start+3, start+5)))
                break

    chosen = []
    for moment, name, confidence in sorted(stickers, key=lambda item: item[2], reverse=True):
        if length < 1:
            break
        moment = min(moment, length-1)
        if all(abs(moment-event.start) >= 2 for event in chosen):
            chosen.append(Effect(name, moment, moment+1))
    return sorted(effects+chosen, key=lambda event: (event.start, event.name))


def time_test(start, end, variable):
    return f"gte({variable},{start})*lt({variable},{end})"


def framing_filter(effects):
    zoom = "1"
    y = "clip(ih*.31-ih/zoom*.49,0,ih-ih/zoom)"
    for effect in reversed(effects):
        if effect.zoom <= 1:
            continue
        start, end = effect.start, effect.end
        active = time_test(start, end, "on/30")
        factor = str(effect.zoom)
        if effect.name == "bottom":
            ramp = f"clip(min(on/30-{start},{end}-on/30)/.25,0,1)"
            factor = f"1+{effect.zoom-1:.3f}*{ramp}"
            y = f"if({active},ih-ih/zoom,{y})"
        zoom = f"if({active},{factor},{zoom})"
    if zoom == "1":
        return ""
    bottom = "+".join(time_test(e.start, e.end, "on/30") for e in effects if e.name == "bottom") or "0"
    x = f"if({bottom},(iw-iw/zoom)/2,clip(iw*.10-iw/zoom*.44,0,iw-iw/zoom))"
    return f",zoompan=z='{zoom}':x='{x}':y='{y}':d=1:s=1280x720:fps=30"
