"""Chọn nhóm cảnh liền mạch và lên lịch các góc camera."""
from array import array
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


def gameplay_lengths(length):
    if length <= 7:
        return [length]
    if length <= 9:
        return [5, length-5]
    count = (length+3)//6
    base, extra = divmod(length, count)
    return [base+1]*extra + [base]*(count-extra)


def rank_windows(scores, size):
    prefix = list(accumulate(scores, initial=0.0))
    peaks = deque()
    windows = []
    for i, value in enumerate(scores):
        while peaks and scores[peaks[-1]] <= value:
            peaks.pop()
        peaks.append(i)
        start = i-size+1
        if start < 0:
            continue
        while peaks[0] < start:
            peaks.popleft()
        average = (prefix[i+1]-prefix[start])/size
        windows.append((.45*scores[peaks[0]]+.55*average, peaks[0]))
    return windows


def best_sequence(scores, light, labels, first, end, length):
    lengths = gameplay_lengths(length)
    duration = end-first
    gaps = GAPS[1:] if duration >= length + 3*(len(lengths)-1) else GAPS
    local = scores[first:end]
    lookup = {size: rank_windows(local, size) for size in set(lengths)}

    backtracks = []
    previous = []
    elapsed = 0
    for stage, size in enumerate(lengths):
        remaining = length-elapsed-size
        current = [float("-inf")] * (duration-size-remaining+1)
        back = array("i", [-1]) * len(current)
        weight = 1 + .4 * stage / max(1, len(lengths)-1)
        for start in range(elapsed, len(current)):
            score = lookup[size][start][0]
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


def select_short_clips(scores, labels, count, length):
    windows = rank_windows(scores, length)
    order = sorted(range(len(windows)), key=lambda start: windows[start][0], reverse=True)
    occupied = bytearray(len(scores))
    selected = []
    for start in order:
        if any(occupied[start:start+length]):
            continue
        selected.append(start)
        occupied[start:start+length] = b"\1"*length
        if len(selected) == count:
            break
    if len(selected) < count:
        # Nếu các cửa sổ điểm cao chắn nhau, dùng một lưới có đủ chỗ để xuất.
        selected = [start for start in order if start % length == 0][:count]
    return [[Shot(start, length, labels[windows[start][1]])] for start in sorted(selected)]


def events_for_shot(length, offset, total, facecam, speech, stickers):
    effects = []
    for minute in range(max(60, offset//60*60), min(total, offset+length), 60):
        start, end = max(0, minute-offset), min(length, minute+3-offset)
        if start < end:
            effects.append(Effect("bottom", start, end, 1.16))

    if facecam:
        for boundary in range(offset//3*3, offset+length, 3):
            start, end = max(0, boundary-offset), min(length, boundary+3-offset)
            close = boundary % 6 == 0
            effects.append(Effect("near" if close else "wide", start, end, 1.55 if close else 1))
        streak_start = last = None
        inserted = False
        for moment in speech:
            if last is None or moment-last > 1:
                streak_start, inserted = moment, False
            last = moment
            if not inserted and moment >= 0 and moment-streak_start >= 5.5 and moment+2 <= length:
                effects.append(Effect("speech", moment, moment+2, 3.32))
                inserted = True

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


def bottom_filter(effects):
    factors = []
    for effect in effects:
        if effect.name == "bottom":
            start, end = effect.start, effect.end
            ramp = f"clip(min(on/30-{start},{end}-on/30)/.25,0,1)"
            factors.append(f"{effect.zoom-1:.3f}*{ramp}")
    if not factors:
        return ""
    zoom = "1+" + "+".join(factors)
    return f",zoompan=z='{zoom}':x='(iw-iw/zoom)/2':y='ih-ih/zoom':d=1:s=1280x720:fps=30"
