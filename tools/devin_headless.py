#!/usr/bin/env python3
"""Headless wrapper for the Devin CLI on Windows.

While the Devin org has no git provider connected, devin.exe renders an
interactive "Connect your Git provider / Skip for now" nudge on EVERY startup,
even in -p (print) mode. The nudge reads raw console key events, so piped
stdin cannot dismiss it and headless runs hang forever. This wrapper runs
devin.exe inside a hidden ConPTY (pywinpty), dismisses the nudge, and streams
the ANSI-stripped transcript to stdout as it arrives.

Usage:
    python tools/devin_headless.py [--timeout SECS] -- <devin.exe args...>

Example (manager delegation, from repo root):
    python tools/devin_headless.py -- -p "Read AGENTS.md, then execute specs/foo.md exactly." --permission-mode smart
"""
import argparse
import os
import queue
import re
import subprocess
import sys
import threading
import time

from winpty import PtyProcess

DEVIN_EXE = os.path.expandvars(
    r"%LOCALAPPDATA%\Programs\Devin\resources\app\extensions\windsurf\devin\bin\devin.exe"
)
NUDGE_MARKER = "Skip for now"
# If the nudge is still the last thing on screen after this much output
# silence, the previous dismiss attempt did not land — try the next one.
SILENCE_BEFORE_RETRY_S = 4.0
# Escalating key sequences: Esc (skip), then explicit "select option 4 + Enter".
DISMISS_KEYS = ["\x1b", "\x1b", "4\r", "\r", "j\rj\rj\r\r"]
ANSI_RE = re.compile(
    r"\x1b\[[0-9;?]*[A-Za-z]"              # CSI sequences
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"  # OSC sequences
    r"|\x1b[=>]"
    r"|[\x00-\x08\x0b\x0c\x0e-\x1f]"
)


def reader(proc: PtyProcess, q: "queue.Queue[str | None]") -> None:
    while True:
        try:
            chunk = proc.read(4096)
        except (EOFError, OSError):
            break
        if chunk:
            q.put(chunk)
    q.put(None)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--timeout", type=float, default=3600.0,
                    help="kill devin.exe after this many seconds (default 3600)")
    ap.add_argument("devin_args", nargs=argparse.REMAINDER,
                    help="arguments passed through to devin.exe (prefix with --)")
    opts = ap.parse_args()

    args = opts.devin_args
    if args and args[0] == "--":
        args = args[1:]
    if not args:
        ap.error("no devin.exe arguments given (e.g. -- -p \"prompt\")")
    if not os.path.exists(DEVIN_EXE):
        sys.exit(f"devin.exe not found at {DEVIN_EXE}")

    cmdline = subprocess.list2cmdline([DEVIN_EXE, *args])
    proc = PtyProcess.spawn(cmdline, dimensions=(50, 200), cwd=os.getcwd())
    q: "queue.Queue[str | None]" = queue.Queue()
    threading.Thread(target=reader, args=(proc, q), daemon=True).start()

    tail = ""            # last screen-ish of raw output, for nudge detection
    last_data = time.time()
    dismiss_i = 0        # next DISMISS_KEYS index to try
    dismissed_at = 0.0
    deadline = time.time() + opts.timeout
    timed_out = False
    eof = False

    while not eof:
        if time.time() > deadline:
            timed_out = True
            try:
                proc.terminate(force=True)
            except Exception:
                pass
            break
        try:
            chunk = q.get(timeout=1.0)
        except queue.Empty:
            # No output. If the nudge is the last thing rendered and the
            # previous key did not land, escalate to the next dismiss key.
            silent_for = time.time() - last_data
            nudge_pending = NUDGE_MARKER in tail
            if (nudge_pending and silent_for > SILENCE_BEFORE_RETRY_S
                    and time.time() - dismissed_at > SILENCE_BEFORE_RETRY_S
                    and dismiss_i < len(DISMISS_KEYS)):
                try:
                    proc.write(DISMISS_KEYS[dismiss_i])
                except (EOFError, OSError):
                    break
                print(f"[devin_headless] nudge dismiss attempt {dismiss_i + 1}",
                      file=sys.stderr, flush=True)
                dismissed_at = time.time()
                dismiss_i += 1
            if not proc.isalive():
                break
            continue
        if chunk is None:
            eof = True
            break
        last_data = time.time()
        tail = (tail + chunk)[-4000:]
        sys.stdout.write(ANSI_RE.sub("", chunk))
        sys.stdout.flush()
        # New render of the nudge: dismiss immediately (first attempt only;
        # retries are driven by the silence branch above).
        if NUDGE_MARKER in chunk and dismiss_i == 0:
            try:
                proc.write(DISMISS_KEYS[0])
            except (EOFError, OSError):
                break
            print("[devin_headless] nudge dismiss attempt 1", file=sys.stderr, flush=True)
            dismissed_at = time.time()
            dismiss_i = 1

    if timed_out:
        print(f"[devin_headless] TIMEOUT after {opts.timeout}s — devin.exe killed",
              file=sys.stderr, flush=True)
        return 124
    return proc.exitstatus or 0


if __name__ == "__main__":
    sys.exit(main())
