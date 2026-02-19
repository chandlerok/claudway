"""Tests for src.commands.shell."""

from unittest.mock import patch

from src.commands.shell import build_shell_env


class TestBuildShellEnv:
    def test_strips_virtual_env(self) -> None:
        env_vars = {"VIRTUAL_ENV": "/some/venv", "HOME": "/home"}
        with patch.dict("os.environ", env_vars, clear=True):
            env = build_shell_env()
            assert "VIRTUAL_ENV" not in env
            assert env["HOME"] == "/home"

    def test_strips_claudway_from_path(self) -> None:
        original = "/usr/bin:/home/.local/claudway/venv/bin:/usr/local/bin"
        with patch.dict("os.environ", {"PATH": original}, clear=True):
            env = build_shell_env()
            assert "claudway" not in env["PATH"]
            assert "/usr/bin" in env["PATH"]
