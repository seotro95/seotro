"""Compile the 132 narration cues without changing existing audio or voice choices."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def stamp(seconds):
    hours, rest = divmod(seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d},000'

def main():
    master = json.loads((ROOT / 'scripts/en.json').read_text())
    for path in sorted((ROOT / 'scripts').glob('*.lines.txt')):
        rows = []
        for line in path.read_text().splitlines():
            if not line.strip(): continue
            number, text = line.split('\t', 1)
            n = int(number)
            rows.append(dict(scene=n, start_seconds=(n-1)*10,
                             duration_seconds=10, text=text.strip()))
        assert len(rows) == 132 and [r['scene'] for r in rows] == list(range(1,133)), path
        assert all(r['text'] for r in rows)
        target = path.with_name(path.name.split('.')[0] + '.json')
        target.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
    counts = {}
    for path in sorted((ROOT / 'scripts').glob('*.json')):
        rows = json.loads(path.read_text())
        assert len(rows) == 132 and sum(r['duration_seconds'] for r in rows) == 1320, path
        path.with_suffix('.txt').write_text('\n\n'.join(r['text'] for r in rows)+'\n', encoding='utf-8-sig')
        path.with_suffix('.srt').write_text('\n\n'.join(
            f"{r['scene']}\n{stamp(r['start_seconds'])} --> {stamp(r['start_seconds']+r['duration_seconds'])}\n{r['text']}"
            for r in rows)+'\n', encoding='utf-8-sig')
        counts[path.stem] = len(rows)
    print(json.dumps(counts))

if __name__ == '__main__': main()
