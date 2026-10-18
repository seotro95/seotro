"""Run regressions with bounded waits and file-backed Windows diagnostics."""
from __future__ import annotations

import faulthandler
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile


class Progress:
    def pytest_runtest_logstart(self, nodeid: str, location: tuple) -> None:
        # Parameter IDs may contain a complete 200,000-character import fixture.
        print(f"\nSTART {nodeid[:180]}", flush=True)


def run_child(paths: list[str]) -> int:
    # Cover collection as well as individual tests and interpreter shutdown.
    faulthandler.enable()
    faulthandler.dump_traceback_later(90, exit=True)
    import pytest

    result = pytest.main([
        "-q", "-o", "faulthandler_timeout=90",
        "-o", "faulthandler_exit_on_timeout=true", *paths,
    ], plugins=[Progress()])
    faulthandler.enable()
    faulthandler.dump_traceback_later(30, exit=True)
    return int(result)


def run_parent(paths: list[str]) -> int:
    with tempfile.TemporaryDirectory(prefix="voice-regressions-") as directory:
        stdout_path = Path(directory) / "stdout.log"
        stderr_path = Path(directory) / "stderr.log"
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            child = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "--child", *paths],
                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                start_new_session=os.name != "nt",
            )
            try:
                result = child.wait(timeout=300)
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(child.pid), "/T", "/F"],
                        stdout=stderr, stderr=stderr, timeout=20, check=False,
                    )
                else:
                    os.killpg(child.pid, signal.SIGKILL)
                child.kill()
                child.wait(timeout=20)
                result = 1
                stderr.write(b"Regression process exceeded the five-minute limit.\n")
        output = stdout_path.read_text(encoding="utf-8", errors="replace")
        errors = stderr_path.read_text(encoding="utf-8", errors="replace")
        print(output, end="", flush=True)
        print(errors, end="", file=sys.stderr, flush=True)
        if result and os.environ.get("GITHUB_ACTIONS") == "true":
            details = "\n".join(output.splitlines()[-15:] + errors.splitlines()[-100:])
            details = details.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            print(f"::error title=Voice regression diagnostics::{details}", flush=True)
        return result


if __name__ == "__main__":
    arguments = sys.argv[1:]
    if arguments[:1] == ["--child"]:
        raise SystemExit(run_child(arguments[1:] or ["tests"]))
    raise SystemExit(run_parent(arguments or ["tests"]))
