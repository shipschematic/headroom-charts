"""Ticket #14: `q` closes the dashboard the way Ctrl-C does.

Two properties carry more weight than the key itself: raw mode must leave ISIG switched
on, or the escape hatch the ticket promises to keep stops working; and the terminal must
be handed back even when the redraw loop dies mid-paint, or a crash leaves the user's
shell in a state they cannot type into.

Verified against a real pty, because termios on a pipe is not the thing under test.
"""

from __future__ import annotations

import os
import pty
import termios
import time

import pytest

from headroom_charts import app
from headroom_charts.keyboard import QuitKey

FIXTURE = os.path.join(os.path.dirname(__file__), "data", "events.jsonl")


@pytest.fixture
def tty():
    """A real terminal, with the far end of the wire kept so a test can type into it."""
    master, slave = pty.openpty()
    stream = os.fdopen(slave, "r")
    try:
        yield stream, master
    finally:
        stream.close()
        os.close(master)


def test_q_reaches_the_caller(tty) -> None:
    stream, master = tty
    with QuitKey(stream) as keys:
        os.write(master, b"q")
        assert keys.wait(5.0) is True


def test_a_key_that_is_not_q_does_not_end_the_loop(tty) -> None:
    stream, master = tty
    with QuitKey(stream) as keys:
        os.write(master, b"j")
        assert keys.wait(0.2) is False


def test_a_quiet_terminal_still_takes_the_whole_tick(tty) -> None:
    """The wait doubles as the redraw timer, so it may not return early."""
    stream, _master = tty
    with QuitKey(stream) as keys:
        started = time.monotonic()
        assert keys.wait(0.3) is False
        assert time.monotonic() - started >= 0.25


def test_raw_mode_leaves_the_interrupt_signal_switched_on(tty) -> None:
    """ECHO and ICANON off is what makes `q` arrive without Enter; ISIG on is what
    means Ctrl-C still reaches the app. Turning it off would be the cheaper setting
    and would break the ticket's second acceptance criterion."""
    stream, _master = tty
    with QuitKey(stream):
        flags = termios.tcgetattr(stream.fileno())[3]
        assert flags & termios.ISIG
        assert not flags & termios.ECHO
        assert not flags & termios.ICANON


def test_the_terminal_is_handed_back_as_it_was_found(tty) -> None:
    stream, _master = tty
    before = termios.tcgetattr(stream.fileno())
    with QuitKey(stream):
        pass
    assert termios.tcgetattr(stream.fileno()) == before


def test_the_terminal_is_handed_back_when_the_body_raises(tty) -> None:
    stream, _master = tty
    before = termios.tcgetattr(stream.fileno())
    with pytest.raises(RuntimeError), QuitKey(stream):
        raise RuntimeError("the redraw loop died")
    assert termios.tcgetattr(stream.fileno()) == before


def test_a_pipe_is_not_put_into_raw_mode(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`headroom-charts < /dev/null` and a piped stdin have no terminal to take over.
    The tick falls back to the sleep the original loop used, rather than selecting on
    a file descriptor that would report readable forever at EOF."""
    from headroom_charts import keyboard

    slept: list[float] = []
    monkeypatch.setattr(keyboard.time, "sleep", slept.append)
    quiet = tmp_path / "quiet.txt"
    quiet.write_text("")
    with quiet.open() as pipe, QuitKey(pipe) as keys:
        assert keys.wait(9.0) is False
    assert slept == [9.0]


class ScriptedKeys:
    """Stands in for a terminal a test can type into, one answer per wait()."""

    def __init__(self, answers: list[bool]) -> None:
        self.answers = answers
        self.waits = 0

    def __enter__(self) -> ScriptedKeys:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def wait(self, _seconds: float) -> bool:
        self.waits += 1
        if not self.answers:
            return True  # the script running out quits, so no test can hang
        return self.answers.pop(0)


class RecordingLive:
    def __init__(self, renderable, **kwargs) -> None:
        self.kwargs = kwargs
        self.updates = 0

    def __enter__(self) -> RecordingLive:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def update(self, renderable: object) -> None:
        self.updates += 1


@pytest.fixture
def live_stub(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(app, "SAVINGS_FILE", FIXTURE)
    made: list[RecordingLive] = []

    def make_live(renderable, **kwargs):
        live = RecordingLive(renderable, **kwargs)
        made.append(live)
        return live

    monkeypatch.setattr(app, "Live", make_live)
    return made


def test_q_stops_the_loop_and_exits_cleanly(live_stub, monkeypatch: pytest.MonkeyPatch) -> None:
    keys = ScriptedKeys([False, True])
    monkeypatch.setattr(app, "QuitKey", lambda *a: keys)
    app.run()
    assert keys.waits == 2
    assert live_stub[0].updates == 1


def test_the_loop_keeps_redrawing_while_nothing_is_pressed(
    live_stub, monkeypatch: pytest.MonkeyPatch
) -> None:
    keys = ScriptedKeys([False, False, False])
    monkeypatch.setattr(app, "QuitKey", lambda *a: keys)
    app.run()
    assert live_stub[0].updates == 3
    assert keys.waits == 4  # three redraws, then the script running out closes the loop


def test_the_live_display_settings_are_unchanged(
    live_stub, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#14 must not quietly change the repaint cadence or drop the alternate screen."""
    monkeypatch.setattr(app, "QuitKey", lambda *a: ScriptedKeys([True]))
    app.run()
    assert live_stub[0].kwargs == {"refresh_per_second": 1, "screen": True}
