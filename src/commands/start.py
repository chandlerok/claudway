import atexit
import contextlib
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from src.app import app
from src.settings import (
    DEP_SYMLINKS,
    SKIP_NAMES,
    SKIP_PREFIXES,
    SKIP_SUFFIXES,
    ClaudwaySettings,
)


console = Console()


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _should_sync(path: str) -> bool:
    """Return True if this untracked file should be synced to the worktree."""
    for prefix in SKIP_PREFIXES:
        if prefix in path:
            return False
    name = path.rsplit("/", 1)[-1]
    if name in SKIP_NAMES:
        return False
    return not name.endswith(SKIP_SUFFIXES)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            result.args,
            output=result.stdout,
            stderr=result.stderr,
        )
    return result


def _branch_exists(repo: Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", branch],
        capture_output=True,
    )
    return result.returncode == 0


def _ensure_branch(repo: Path, branch: str) -> str:
    """Ensure *branch* exists, prompting the user to create it if needed."""
    if _branch_exists(repo, branch):
        return branch
    create = typer.confirm(
        f"Branch '{branch}' does not exist. Create it?", default=True
    )
    if not create:
        raise typer.Abort()
    _git(repo, "branch", branch)
    return branch


def _resolve_branch(repo: Path, branch: str | None) -> str:
    if branch is not None:
        return _ensure_branch(repo, branch)
    branch_name = typer.prompt("Enter a branch name")
    return _ensure_branch(repo, branch_name)


# ---------------------------------------------------------------------------
# Shell helpers
# ---------------------------------------------------------------------------


def _get_activate_cmd(user_shell: str, venv_dir: Path) -> str:
    """Return the virtualenv activation command appropriate for *user_shell*."""
    shell_name = Path(user_shell).name
    if shell_name == "fish":
        return f"source {venv_dir}/bin/activate.fish"
    return f"source {venv_dir}/bin/activate"


def _launch_shell(
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


def _build_shell_env() -> dict[str, str]:
    """Build a shell environment with the claudway venv stripped out."""
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    env["PATH"] = os.pathsep.join(
        p
        for p in os.environ.get("PATH", "").split(os.pathsep)
        if "claudway" not in p
    )
    return env


# ---------------------------------------------------------------------------
# Worktree operations
# ---------------------------------------------------------------------------


class _WorktreeConflictError(Exception):
    def __init__(self, path: str) -> None:
        self.path = path


def _link_deps(repo: Path, worktree: Path) -> None:
    for rel_path in DEP_SYMLINKS:
        source = repo / rel_path
        target = worktree / rel_path
        if source.exists() and not target.exists():
            target.symlink_to(source)


def _uncommitted_changes(worktree: Path) -> str:
    """Return porcelain status output, or empty string if clean."""
    result = subprocess.run(
        ["git", "-C", str(worktree), "status", "--porcelain", "-unormal"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _cleanup_worktree(repo: Path, tmpdir: Path) -> None:
    with contextlib.suppress(subprocess.CalledProcessError, FileNotFoundError):
        _git(repo, "worktree", "remove", "--force", str(tmpdir))
    if tmpdir.exists():
        shutil.rmtree(tmpdir, ignore_errors=True)


def _create_worktree(repo: Path, tmpdir: Path, branch: str) -> None:
    """Create a git worktree, resolving conflicts interactively."""
    try:
        _git(repo, "worktree", "add", str(tmpdir), branch)
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        already_used = (
            "already checked out" in stderr
            or "already used by worktree" in stderr
        )
        if not already_used:
            raise

        conflict_path = _find_conflicting_worktree(repo, branch)
        if not conflict_path:
            console.print(f"\n[red]Error:[/red] {stderr}")
            raise typer.Exit(1) from None

        console.print(
            f"[yellow]Branch '{branch}' is already checked out at:[/yellow]"
            f"\n  {conflict_path}"
        )
        if not typer.confirm("Remove the existing worktree?", default=True):
            raise typer.Exit(1) from None
        _cleanup_worktree(repo, Path(conflict_path))
        _git(repo, "worktree", "add", str(tmpdir), branch)


def _find_conflicting_worktree(repo: Path, branch: str) -> str | None:
    """Return the path of an existing worktree that has *branch* checked out."""
    wt_list = _git(repo, "worktree", "list", "--porcelain")
    candidate = ""
    for line in wt_list.stdout.splitlines():
        if line.startswith("worktree "):
            candidate = line.removeprefix("worktree ")
        elif line.startswith("branch ") and line.endswith(f"/{branch}"):
            return candidate
    return None


def _sync_untracked_files(repo: Path, worktree: Path) -> None:
    """Rsync untracked (non-ignored) files from *repo* into *worktree*."""
    untracked = _git(repo, "ls-files", "--others")
    filtered = "\n".join(
        p for p in untracked.stdout.splitlines() if _should_sync(p)
    )
    if filtered:
        subprocess.run(
            ["rsync", "-a", "--files-from=-", f"{repo}/", f"{worktree}/"],
            input=filtered,
            text=True,
            check=False,
        )


# ---------------------------------------------------------------------------
# Cleanup orchestration
# ---------------------------------------------------------------------------


def _prompt_uncommitted_changes(
    worktree: Path,
    user_shell: str,
    shell_env: dict[str, str],
    activate_cmd: str,
) -> None:
    """If the worktree has uncommitted changes, warn and optionally re-enter shell."""
    if not sys.stdin.isatty() or not worktree.exists():
        return
    try:
        while changes := _uncommitted_changes(worktree):
            console.print()
            console.print("[bold yellow]\u26a0  Uncommitted changes[/bold yellow]")
            console.print(
                "[dim]These will be lost when the worktree is removed.[/dim]\n"
            )
            _print_change_summary(changes)
            keep_going = typer.confirm(
                "Return to shell to stash/stage/commit?", default=True
            )
            if not keep_going:
                break
            console.print("[dim]Returning to shell. Type 'exit' when done.[/dim]\n")
            _launch_shell(user_shell, shell_env, activate_cmd, worktree)
    except (EOFError, KeyboardInterrupt):
        pass


def _print_change_summary(changes: str) -> None:
    """Pretty-print a short summary of porcelain status output."""
    lines = changes.splitlines()
    for line in lines[:15]:
        status, _, name = line.partition(" ")
        name = name.strip()
        color = {"M": "yellow", "A": "green", "D": "red", "??": "cyan"}.get(
            status.strip(), "white"
        )
        console.print(f"  [{color}]{status}[/{color}] {name}")
    if len(lines) > 15:
        console.print(f"  [dim]... and {len(lines) - 15} more[/dim]")
    console.print()


# ---------------------------------------------------------------------------
# Main command
# ---------------------------------------------------------------------------


@app.command()
def start(
    branch: Annotated[
        str | None,
        typer.Argument(help="Git branch to work on. If omitted, you will be prompted."),
    ] = None,
    command: Annotated[
        str | None,
        typer.Option(
            "--command", "-c", help="Command to run instead of the default agent."
        ),
    ] = None,
    shell_only: Annotated[
        bool,
        typer.Option(
            "--shell",
            "-s",
            help="Drop straight into a shell without launching the agent.",
        ),
    ] = False,
) -> None:
    """Start an isolated dev environment in a git worktree."""
    settings = ClaudwaySettings()
    if settings.repo_location is None:
        console.print(
            "[red]Error:[/red] repo location is not set. "
            "Run [bold]cw set-repo-location[/bold] first."
        )
        raise typer.Exit(1)

    repo = Path(settings.repo_location)
    resolved_branch = _resolve_branch(repo, branch)
    agent_cmd = command or settings.agent
    user_shell = os.environ.get("SHELL", "/bin/sh")

    tmpdir = Path(tempfile.mkdtemp(prefix="cw-"))
    tmpdir.rmdir()  # git worktree add requires the target dir not to exist
    cleanup_done = False

    # Shell context - populated once the worktree is ready, used by cleanup
    # to offer a "return to shell" option.
    shell_ctx: dict[str, str] = {}

    def do_cleanup() -> None:
        nonlocal cleanup_done
        if cleanup_done:
            return
        if shell_ctx and tmpdir.exists():
            _prompt_uncommitted_changes(
                tmpdir,
                shell_ctx["user_shell"],
                shell_ctx["shell_env"],  # type: ignore[arg-type]
                shell_ctx["activate_cmd"],
            )
        cleanup_done = True
        console.print("\n[yellow]Cleaning up worktree ...[/yellow]")
        _cleanup_worktree(repo, tmpdir)
        console.print("[green]Done.[/green]")

    atexit.register(do_cleanup)
    original_sigint = signal.getsignal(signal.SIGINT)
    original_sigterm = signal.getsignal(signal.SIGTERM)

    def _signal_handler(signum: int, _frame: object) -> None:
        do_cleanup()
        sys.exit(128 + signum)

    try:
        with console.status("[bold cyan]Creating worktree ...", spinner="dots"):
            _create_worktree(repo, tmpdir, resolved_branch)
        console.print(
            f"[green]\u2713[/green] Worktree created for [bold]{resolved_branch}[/bold]"
        )

        with console.status("[bold cyan]Syncing untracked files ...", spinner="dots"):
            _sync_untracked_files(repo, tmpdir)
        console.print("[green]\u2713[/green] Untracked files synced")

        with console.status("[bold cyan]Linking dependencies ...", spinner="dots"):
            _link_deps(repo, tmpdir)
        console.print("[green]\u2713[/green] Dependencies linked")

        if (tmpdir / "mise.toml").exists():
            subprocess.run(["mise", "trust"], cwd=tmpdir, capture_output=True)

        console.print()
        console.print(f"[bold green]Worktree ready![/bold green] [dim]{tmpdir}[/dim]")
        console.print(f"[dim]Branch:[/dim] [bold]{resolved_branch}[/bold]")
        console.print()

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        if not shell_only:
            console.print(f"[bold cyan]Launching:[/bold cyan] {agent_cmd}\n")
            subprocess.run(agent_cmd, cwd=tmpdir, shell=True)

        console.print("[dim]Dropping into shell. Type 'exit' to clean up.[/dim]\n")

        shell_env = _build_shell_env()
        venv_dir = tmpdir / "mamba" / "venv"
        activate_cmd = _get_activate_cmd(user_shell, venv_dir)

        shell_ctx.update(
            user_shell=user_shell,
            shell_env=shell_env,  # type: ignore[dict-item]
            activate_cmd=activate_cmd,
        )

        _launch_shell(user_shell, shell_env, activate_cmd, tmpdir)

        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)
    finally:
        do_cleanup()
