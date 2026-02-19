"""Tests for persistent worktree helpers and new commands."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from src.commands.worktree import (
    classify_worktree,
    is_valid_worktree,
    list_worktrees,
    persistent_worktree_dir,
)
from src.settings import PERSISTENT_WORKTREES_DIR


class TestPersistentWorktreeDir:
    def test_deterministic(self) -> None:
        repo = Path("/home/user/repo")
        result1 = persistent_worktree_dir(repo, "feature/foo")
        result2 = persistent_worktree_dir(repo, "feature/foo")
        assert result1 == result2

    def test_sanitizes_slashes(self) -> None:
        repo = Path("/home/user/repo")
        result = persistent_worktree_dir(repo, "feature/foo")
        assert "feature-foo-" in result.name

    def test_different_repos_different_dirs(self) -> None:
        result1 = persistent_worktree_dir(Path("/repo1"), "main")
        result2 = persistent_worktree_dir(Path("/repo2"), "main")
        assert result1 != result2

    def test_parent_is_persistent_dir(self) -> None:
        result = persistent_worktree_dir(Path("/repo"), "branch")
        assert result.parent == PERSISTENT_WORKTREES_DIR

    def test_hash_is_8_chars(self) -> None:
        result = persistent_worktree_dir(Path("/repo"), "branch")
        # Name format: sanitized-hash
        parts = result.name.rsplit("-", 1)
        assert len(parts) == 2
        assert len(parts[1]) == 8


class TestClassifyWorktree:
    def test_main_worktree(self) -> None:
        repo = Path("/home/user/repo")
        assert classify_worktree(repo, repo) == "main"

    def test_persistent_worktree(self) -> None:
        repo = Path("/home/user/repo")
        wt_path = PERSISTENT_WORKTREES_DIR / "feature-abc12345"
        assert classify_worktree(repo, wt_path) == "persistent"

    def test_temporary_worktree(self) -> None:
        repo = Path("/home/user/repo")
        tmpdir = Path(tempfile.gettempdir()) / "cw-xyz123"
        assert classify_worktree(repo, tmpdir) == "temporary"

    def test_unknown_worktree(self) -> None:
        repo = Path("/home/user/repo")
        wt_path = Path("/some/random/path")
        assert classify_worktree(repo, wt_path) == "unknown"


class TestListWorktrees:
    def test_parses_porcelain(self) -> None:
        porcelain = (
            "worktree /home/user/repo\n"
            "HEAD abc123\n"
            "branch refs/heads/main\n"
            "\n"
            "worktree /tmp/cw-xyz\n"
            "HEAD def456\n"
            "branch refs/heads/feature\n"
            "\n"
        )
        with patch("src.commands.worktree.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = porcelain
            result = list_worktrees(Path("/home/user/repo"))

        assert len(result) == 2
        assert result[0]["path"] == "/home/user/repo"
        assert result[0]["branch"] == "main"
        assert result[0]["type"] == "main"
        assert result[1]["path"] == "/tmp/cw-xyz"
        assert result[1]["branch"] == "feature"

    def test_empty_on_failure(self) -> None:
        with patch("src.commands.worktree.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            result = list_worktrees(Path("/repo"))
        assert result == []

    def test_includes_type(self) -> None:
        persistent_path = str(PERSISTENT_WORKTREES_DIR / "feat-12345678")
        porcelain = (
            f"worktree {persistent_path}\nHEAD abc123\nbranch refs/heads/feat\n\n"
        )
        with patch("src.commands.worktree.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = porcelain
            result = list_worktrees(Path("/repo"))

        assert result[0]["type"] == "persistent"


class TestIsValidWorktree:
    def test_found(self) -> None:
        porcelain = "worktree /tmp/cw-xyz\nHEAD abc\nbranch refs/heads/main\n"
        with patch("src.commands.worktree.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = porcelain
            # Use the exact path so resolve() matches
            assert is_valid_worktree(Path("/repo"), Path("/tmp/cw-xyz")) is True

    def test_not_found(self) -> None:
        porcelain = "worktree /tmp/cw-other\nHEAD abc\nbranch refs/heads/main\n"
        with patch("src.commands.worktree.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = porcelain
            assert is_valid_worktree(Path("/repo"), Path("/tmp/cw-xyz")) is False

    def test_git_failure(self) -> None:
        with patch("src.commands.worktree.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            assert is_valid_worktree(Path("/repo"), Path("/tmp/cw-xyz")) is False
