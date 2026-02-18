"""Tests for src.commands.cleanup."""

import pytest

from src.commands.cleanup import print_change_summary


class TestPrintChangeSummary:
    def test_does_not_raise(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        print_change_summary("M  file.py\n?? new.txt")

    def test_truncates_long_list(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        lines = "\n".join(f"M  file{i}.py" for i in range(20))
        print_change_summary(lines)
        captured = capsys.readouterr()
        assert "and 5 more" in captured.out
