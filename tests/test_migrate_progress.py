"""Progress helpers for long migrate runs."""

from __future__ import annotations

from casa.prisms.shared import migrate_progress as mp


def test_progress_respects_enabled(capsys) -> None:
    mp.set_progress_enabled(True)
    mp.progress("hello")
    err = capsys.readouterr().err
    assert "hello" in err

    mp.set_progress_enabled(False)
    mp.progress("hidden")
    assert "hidden" not in capsys.readouterr().err


def test_step_timer_logs(capsys) -> None:
    mp.set_progress_enabled(True)
    with mp.StepTimer("load", "10 MiB"):
        pass
    err = capsys.readouterr().err
    assert "load" in err
