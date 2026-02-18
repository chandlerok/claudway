"""Tests for extracted helper functions in claudway."""

from pathlib import Path
from unittest.mock import patch

import pytest
from claudway.commands.start import (
    _build_shell_env,
    _find_conflicting_worktree,
    _get_activate_cmd,
    _print_change_summary,
    _should_sync,
)
from claudway.settings import SKIP_NAMES, SKIP_PREFIXES, SKIP_SUFFIXES


# ---------------------------------------------------------------------------
# _should_sync
# ---------------------------------------------------------------------------


class TestShouldSync:
    def test_normal_file_syncs(self) -> None:
        assert _should_sync("src/main.py") is True

    def test_nested_normal_file_syncs(self) -> None:
        assert _should_sync("a/b/c/readme.txt") is True

    @pytest.mark.parametrize("prefix", SKIP_PREFIXES)
    def test_skip_prefixes(self, prefix: str) -> None:
        assert _should_sync(f"some/{prefix}foo.js") is False

    @pytest.mark.parametrize("suffix", SKIP_SUFFIXES)
    def test_skip_suffixes(self, suffix: str) -> None:
        assert _should_sync(f"data/file{suffix}") is False

    @pytest.mark.parametrize("name", SKIP_NAMES)
    def test_skip_names(self, name: str) -> None:
        assert _should_sync(f"dir/{name}") is False

    def test_prefix_match_is_substring(self) -> None:
        # "node_modules/" anywhere in the path should be skipped
        assert _should_sync("web/node_modules/pkg/index.js") is False


# ---------------------------------------------------------------------------
# _get_activate_cmd
# ---------------------------------------------------------------------------


class TestGetActivateCmd:
    def test_fish_shell(self) -> None:
        cmd = _get_activate_cmd("/opt/homebrew/bin/fish", Path("/tmp/venv"))
        assert cmd == "source /tmp/venv/bin/activate.fish"

    def test_bash_shell(self) -> None:
        cmd = _get_activate_cmd("/bin/bash", Path("/tmp/venv"))
        assert cmd == "source /tmp/venv/bin/activate"

    def test_zsh_shell(self) -> None:
        cmd = _get_activate_cmd("/bin/zsh", Path("/tmp/venv"))
        assert cmd == "source /tmp/venv/bin/activate"

    def test_sh_shell(self) -> None:
        cmd = _get_activate_cmd("/bin/sh", Path("/tmp/venv"))
        assert cmd == "source /tmp/venv/bin/activate"


# ---------------------------------------------------------------------------
# _build_shell_env
# ---------------------------------------------------------------------------


class TestBuildShellEnv:
    def test_strips_virtual_env(self) -> None:
        env_vars = {"VIRTUAL_ENV": "/some/venv", "HOME": "/home"}
        with patch.dict("os.environ", env_vars, clear=True):
            env = _build_shell_env()
            assert "VIRTUAL_ENV" not in env
            assert env["HOME"] == "/home"

    def test_strips_claudway_from_path(self) -> None:
        original_path = "/usr/bin:/home/.local/claudway/venv/bin:/usr/local/bin"
        with patch.dict("os.environ", {"PATH": original_path}, clear=True):
            env = _build_shell_env()
            assert "claudway" not in env["PATH"]
            assert "/usr/bin" in env["PATH"]


# ---------------------------------------------------------------------------
# _find_conflicting_worktree
# ---------------------------------------------------------------------------


class TestFindConflictingWorktree:
    def test_finds_conflict(self) -> None:
        porcelain = (
            "worktree /home/user/repo\n"
            "HEAD abc123\n"
            "branch refs/heads/main\n"
            "\n"
            "worktree /tmp/cw-xyz\n"
            "HEAD def456\n"
            "branch refs/heads/feature\n"
        )
        with patch("claudway.commands.start._git") as mock_git:
            mock_git.return_value.stdout = porcelain
            result = _find_conflicting_worktree(Path("/repo"), "feature")
            assert result == "/tmp/cw-xyz"

    def test_no_conflict(self) -> None:
        porcelain = (
            "worktree /home/user/repo\n"
            "HEAD abc123\n"
            "branch refs/heads/main\n"
        )
        with patch("claudway.commands.start._git") as mock_git:
            mock_git.return_value.stdout = porcelain
            result = _find_conflicting_worktree(Path("/repo"), "feature")
            assert result is None


# ---------------------------------------------------------------------------
# _print_change_summary
# ---------------------------------------------------------------------------


class TestPrintChangeSummary:
    def test_does_not_raise(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Smoke test - just make sure it doesn't explode
        _print_change_summary("M  file.py\n?? new.txt")

    def test_truncates_long_list(self, capsys: pytest.CaptureFixture[str]) -> None:
        lines = "\n".join(f"M  file{i}.py" for i in range(20))
        _print_change_summary(lines)
        captured = capsys.readouterr()
        assert "and 5 more" in captured.out
