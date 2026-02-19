"""Tests for src.commands.git."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from src.commands.git import (
    ensure_branch,
    list_local_branches,
    list_remote_branches,
    should_sync,
)
from src.settings import SKIP_NAMES, SKIP_PREFIXES, SKIP_SUFFIXES


class TestShouldSync:
    def test_normal_file_syncs(self) -> None:
        assert should_sync("src/main.py") is True

    def test_nested_normal_file_syncs(self) -> None:
        assert should_sync("a/b/c/readme.txt") is True

    @pytest.mark.parametrize("prefix", SKIP_PREFIXES)
    def test_skip_prefixes(self, prefix: str) -> None:
        assert should_sync(f"some/{prefix}foo.js") is False

    @pytest.mark.parametrize("suffix", SKIP_SUFFIXES)
    def test_skip_suffixes(self, suffix: str) -> None:
        assert should_sync(f"data/file{suffix}") is False

    @pytest.mark.parametrize("name", SKIP_NAMES)
    def test_skip_names(self, name: str) -> None:
        assert should_sync(f"dir/{name}") is False

    def test_prefix_match_is_substring(self) -> None:
        assert should_sync("web/node_modules/pkg/index.js") is False


def _make_completed(
    stdout: str = "", returncode: int = 0
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=""
    )


REPO = Path("/fake/repo")


class TestListLocalBranches:
    @patch("src.commands.git.git")
    def test_returns_branches_sorted(self, mock_git: patch) -> None:  # type: ignore[type-arg]
        mock_git.return_value = _make_completed("main\nfeature/a\ndev\n")
        result = list_local_branches(REPO)
        assert result == ["main", "feature/a", "dev"]

    @patch("src.commands.git.git")
    def test_returns_empty_on_error(self, mock_git: patch) -> None:  # type: ignore[type-arg]
        mock_git.side_effect = subprocess.CalledProcessError(1, [])
        assert list_local_branches(REPO) == []

    @patch("src.commands.git.git")
    def test_filters_empty_lines(self, mock_git: patch) -> None:  # type: ignore[type-arg]
        mock_git.return_value = _make_completed("main\n\ndev\n")
        assert list_local_branches(REPO) == ["main", "dev"]


class TestListRemoteBranches:
    @patch("src.commands.git.git")
    def test_strips_remote_prefix(self, mock_git: patch) -> None:  # type: ignore[type-arg]
        mock_git.return_value = _make_completed("origin/main\norigin/feature\n")
        assert list_remote_branches(REPO) == ["main", "feature"]

    @patch("src.commands.git.git")
    def test_filters_head(self, mock_git: patch) -> None:  # type: ignore[type-arg]
        mock_git.return_value = _make_completed("origin/HEAD\norigin/main\n")
        assert list_remote_branches(REPO) == ["main"]

    @patch("src.commands.git.git")
    def test_returns_empty_on_error(self, mock_git: patch) -> None:  # type: ignore[type-arg]
        mock_git.side_effect = subprocess.CalledProcessError(1, [])
        assert list_remote_branches(REPO) == []


class TestEnsureBranch:
    @patch("src.commands.git.branch_exists", return_value=True)
    def test_existing_branch_returned(self, _mock: patch) -> None:  # type: ignore[type-arg]
        assert ensure_branch(REPO, "main") == "main"

    @patch("src.commands.git.branch_exists", return_value=True)
    def test_normalizes_origin_prefix(self, _mock: patch) -> None:  # type: ignore[type-arg]
        assert ensure_branch(REPO, "origin/feature") == "feature"

    @patch("src.commands.git.git")
    @patch("src.commands.git.branch_exists")
    def test_creates_tracking_branch_for_remote(
        self,
        mock_exists: patch,
        mock_git: patch,  # type: ignore[type-arg]
    ) -> None:
        # First call: local branch doesn't exist; second: remote ref exists
        mock_exists.side_effect = [False, True]
        mock_git.return_value = _make_completed()
        result = ensure_branch(REPO, "feature")
        assert result == "feature"
        mock_git.assert_called_once_with(
            REPO, "branch", "--track", "feature", "origin/feature"
        )
