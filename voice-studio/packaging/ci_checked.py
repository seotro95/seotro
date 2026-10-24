"""Run native checks and expose an actionable failure in GitHub annotations."""
from collections import deque
import subprocess
import sys


def main():
    command = sys.argv[1:]
    if not command:
        raise SystemExit('Pass the command to check.')
    if command[0] == 'python':
        command[0] = sys.executable
    tail = deque(maxlen=80)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding='utf-8', errors='replace')
    for line in process.stdout:
        print(line, end='', flush=True)
        tail.append(line)
    code = process.wait()
    if code:
        detail = ''.join(tail)[-14000:]
        # GitHub truncates a large annotation before its final traceback.
        # Small UTF-8 chunks preserve the actual failure; emit the tail first.
        chunks, current, size = [], [], 0
        for character in detail:
            count = len(character.encode('utf-8'))
            if size + count > 1800:
                chunks.append(''.join(current))
                current, size = [], 0
            current.append(character)
            size += count
        if current:
            chunks.append(''.join(current))
        for index, chunk in enumerate(reversed(chunks), 1):
            escaped = chunk.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
            print(f'::error title=Windows Hmong check failed {index}/{len(chunks)}::' + escaped, flush=True)
    return code


if __name__ == '__main__':
    sys.exit(main())
