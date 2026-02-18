"""Tests for src.commands.git."""

import pytest

from src.commands.git import should_sync
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
