"""Tests for src.commands.worktree."""

from pathlib import Path
from unittest.mock import patch

from src.commands.worktree import find_conflicting_worktree


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
        with patch("src.commands.worktree.git") as mock_git:
            mock_git.return_value.stdout = porcelain
            result = find_conflicting_worktree(Path("/repo"), "feature")
            assert result == "/tmp/cw-xyz"

    def test_no_conflict(self) -> None:
        porcelain = (
            "worktree /home/user/repo\n"
            "HEAD abc123\n"
            "branch refs/heads/main\n"
        )
        with patch("src.commands.worktree.git") as mock_git:
            mock_git.return_value.stdout = porcelain
            result = find_conflicting_worktree(Path("/repo"), "feature")
            assert result is None
