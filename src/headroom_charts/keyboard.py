"""Ticket #14: read a keypress without taking the terminal's Ctrl-C away with it.

Kept out of `app.py` so it stays inside the linted, typechecked half of the package; the
vendored renderer gains one `with` and one `if`.
"""

from __future__ import annotations

import os
import select
import sys
import termios
import time
import tty
from types import TracebackType


class QuitKey:
    """Watches for `q` on the terminal `stream` for as long as it is entered.

    `wait` is the redraw tick and the keypress in one call, so a quit lands immediately
    rather than on the next second.
    """

    def __init__(self, stream=None) -> None:
        self._stream = sys.stdin if stream is None else stream
        self._fd: int | None = None
        self._saved: list | None = None

    def __enter__(self) -> QuitKey:
        fd = self._terminal_fd()
        if fd is not None:
            self._fd = fd
            self._saved = termios.tcgetattr(fd)
            # setcbreak, not setraw: setraw clears ISIG, and Ctrl-C is the exit this
            # ticket promises to keep. setcbreak drops only ECHO and ICANON.
            tty.setcbreak(fd)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._fd is not None and self._saved is not None:
            termios.tcsetattr(self._fd, termios.TCSANOW, self._saved)
        self._fd = None
        self._saved = None

    def wait(self, seconds: float) -> bool:
        """Sleep the whole tick on a pipe; on a terminal, return early if `q` arrives."""
        if self._fd is None:
            time.sleep(seconds)
            return False
        if not select.select([self._fd], [], [], seconds)[0]:
            return False
        try:
            return os.read(self._fd, 1) in (b"q", b"Q")
        except OSError:
            return False

    def _terminal_fd(self) -> int | None:
        try:
            if not self._stream.isatty():
                return None
            return self._stream.fileno()
        except (AttributeError, ValueError, OSError):
            return None
