import os
import subprocess
from pathlib import Path


def launch_shell(
    user_shell: str,
    shell_env: dict[str, str],
    cwd: Path,
) -> None:
    """Launch an interactive shell in the worktree."""
    subprocess.run([user_shell, "-i"], cwd=cwd, env=shell_env)


def build_shell_env() -> dict[str, str]:
    """Build a shell environment with the claudway venv stripped out."""
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    env["PATH"] = os.pathsep.join(
        p for p in os.environ.get("PATH", "").split(os.pathsep) if "claudway" not in p
    )
    return env
