import os
import subprocess
from pathlib import Path


def get_activate_cmd(user_shell: str, venv_dir: Path) -> str:
    """Return the virtualenv activation command appropriate for *user_shell*."""
    shell_name = Path(user_shell).name
    if shell_name == "fish":
        return f"source {venv_dir}/bin/activate.fish"
    return f"source {venv_dir}/bin/activate"


def launch_shell(
    user_shell: str,
    shell_env: dict[str, str],
    activate_cmd: str,
    cwd: Path,
) -> None:
    """Launch an interactive shell in the worktree."""
    shell_name = Path(user_shell).name
    if shell_name == "fish":
        subprocess.run([user_shell, "-C", activate_cmd], cwd=cwd, env=shell_env)
    elif shell_name in ("bash", "sh"):
        subprocess.run(
            [user_shell, "--rcfile", "/dev/stdin"],
            cwd=cwd,
            env=shell_env,
            input=f"[ -f ~/.bashrc ] && source ~/.bashrc; {activate_cmd}\n",
            text=True,
        )
    else:
        subprocess.run(
            [user_shell, "-c", f"{activate_cmd}; exec {user_shell} -i"],
            cwd=cwd,
            env=shell_env,
        )


def build_shell_env() -> dict[str, str]:
    """Build a shell environment with the claudway venv stripped out."""
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    env["PATH"] = os.pathsep.join(
        p for p in os.environ.get("PATH", "").split(os.pathsep) if "claudway" not in p
    )
    return env
