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

from claudway.app import app
from claudway.settings import ClaudwaySettings


console = Console()

# Directory prefixes to skip when syncing untracked files.
# These are large/regenerable and either get symlinked (deps) or aren't needed.
SKIP_PREFIXES = (
    "node_modules/",
    ".venv/",
    "venv/",
    "__pycache__/",
    ".next/",
    ".turbo/",
    ".nuxt/",
    ".cache/",
    "dist/",
    "build/",
    "coverage/",
)

# File extensions/names to skip
SKIP_SUFFIXES = (".sqlite3", ".db", ".pyc")
SKIP_NAMES = frozenset({".DS_Store", ".coverage"})


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


def _resolve_branch(repo: Path, branch: str | None) -> str:
    if branch is not None:
        if not _branch_exists(repo, branch):
            create = typer.confirm(
                f"Branch '{branch}' does not exist. Create it?", default=True
            )
            if not create:
                raise typer.Abort()
            _git(repo, "branch", branch)
        return branch

    branch_name = typer.prompt("Enter a branch name")
    if not _branch_exists(repo, branch_name):
        create = typer.confirm(
            f"Branch '{branch_name}' does not exist. Create it?", default=True
        )
        if not create:
            raise typer.Abort()
        _git(repo, "branch", branch_name)
    return branch_name


# Directories to symlink from the main repo into the worktree
DEP_SYMLINKS = [
    "web/node_modules",
    "mamba/venv",
]


def _link_deps(repo: Path, worktree: Path) -> None:
    for rel_path in DEP_SYMLINKS:
        source = repo / rel_path
        target = worktree / rel_path
        if source.exists() and not target.exists():
            target.symlink_to(source)


class _WorktreeConflict(Exception):
    def __init__(self, path: str) -> None:
        self.path = path


def _uncommitted_changes(worktree: Path) -> str:
    """Return porcelain status output, or empty string if clean."""
    result = subprocess.run(
        ["git", "-C", str(worktree), "status", "--porcelain", "-unormal"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


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


def _cleanup(repo: Path, tmpdir: Path) -> None:
    with contextlib.suppress(subprocess.CalledProcessError, FileNotFoundError):
        _git(repo, "worktree", "remove", "--force", str(tmpdir))
    if tmpdir.exists():
        shutil.rmtree(tmpdir, ignore_errors=True)


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
            "[red]Error:[/red] repo location is not set. Run [bold]cw set-repo-location[/bold] first."
        )
        raise typer.Exit(1)

    repo = Path(settings.repo_location)
    resolved_branch = _resolve_branch(repo, branch)
    agent_cmd = command or settings.agent
    user_shell = os.environ.get("SHELL", "/bin/sh")

    tmpdir = Path(tempfile.mkdtemp(prefix="cw-"))
    # git worktree add requires the target dir not to exist
    tmpdir.rmdir()
    cleanup_done = False

    # Shell context – populated once the worktree is ready, used by
    # do_cleanup to offer a "return to shell" option.
    shell_ctx: dict[str, object] = {}

    def do_cleanup() -> None:
        nonlocal cleanup_done
        if cleanup_done:
            return
        # If we have shell context and stdin is interactive, check for changes
        if shell_ctx and sys.stdin.isatty() and tmpdir.exists():
            try:
                while changes := _uncommitted_changes(tmpdir):
                    console.print()
                    console.print("[bold yellow]⚠  Uncommitted changes[/bold yellow]")
                    console.print("[dim]These will be lost when the worktree is removed.[/dim]\n")
                    for line in changes.splitlines()[:15]:
                        status, _, name = line.partition(" ")
                        name = name.strip()
                        color = {"M": "yellow", "A": "green", "D": "red", "??": "cyan"}.get(status.strip(), "white")
                        console.print(f"  [{color}]{status}[/{color}] {name}")
                    total = len(changes.splitlines())
                    if total > 15:
                        console.print(f"  [dim]... and {total - 15} more[/dim]")
                    console.print()
                    go_back = typer.confirm("Return to shell to stash/stage/commit?", default=True)
                    if not go_back:
                        break
                    console.print(
                        "[dim]Returning to shell. Type 'exit' when done.[/dim]\n"
                    )
                    _launch_shell(
                        shell_ctx["user_shell"],  # type: ignore[arg-type]
                        shell_ctx["shell_env"],  # type: ignore[arg-type]
                        shell_ctx["activate_cmd"],  # type: ignore[arg-type]
                        tmpdir,
                    )
            except (EOFError, KeyboardInterrupt):
                # User bailed out of the prompt – proceed with cleanup
                pass
        cleanup_done = True
        console.print("\n[yellow]Cleaning up worktree ...[/yellow]")
        _cleanup(repo, tmpdir)
        console.print("[green]Done.[/green]")

    atexit.register(do_cleanup)

    original_sigint = signal.getsignal(signal.SIGINT)
    original_sigterm = signal.getsignal(signal.SIGTERM)

    def _signal_handler(signum: int, _frame: object) -> None:
        do_cleanup()
        sys.exit(128 + signum)

    try:
        try:
            with console.status("[bold cyan]Creating worktree ...", spinner="dots"):
                try:
                    _git(repo, "worktree", "add", str(tmpdir), resolved_branch)
                except subprocess.CalledProcessError as e:
                    stderr = (e.stderr or "").strip()
                    if "already checked out" not in stderr and "already used by worktree" not in stderr:
                        raise
                    # Find the conflicting worktree path from git
                    wt_list = _git(repo, "worktree", "list", "--porcelain")
                    conflict_path = None
                    for line in wt_list.stdout.splitlines():
                        if line.startswith("worktree "):
                            candidate = line.removeprefix("worktree ")
                        elif line.startswith("branch ") and line.endswith(f"/{resolved_branch}"):
                            conflict_path = candidate
                            break
                    if not conflict_path:
                        console.print(f"\n[red]Error:[/red] {stderr}")
                        raise typer.Exit(1)
                    raise _WorktreeConflict(conflict_path)
        except _WorktreeConflict as wc:
            console.print(
                f"[yellow]Branch '{resolved_branch}' is already checked out at:[/yellow]"
                f"\n  {wc.path}"
            )
            remove = typer.confirm("Remove the existing worktree?", default=True)
            if not remove:
                raise typer.Exit(1)
            _cleanup(repo, Path(wc.path))
            with console.status("[bold cyan]Creating worktree ...", spinner="dots"):
                _git(repo, "worktree", "add", str(tmpdir), resolved_branch)
        console.print(
            f"[green]\u2713[/green] Worktree created for [bold]{resolved_branch}[/bold]"
        )

        with console.status("[bold cyan]Syncing untracked files ...", spinner="dots"):
            untracked = _git(repo, "ls-files", "--others")
            filtered = "\n".join(
                p for p in untracked.stdout.splitlines() if _should_sync(p)
            )
            if filtered:
                subprocess.run(
                    [
                        "rsync",
                        "-a",
                        "--files-from=-",
                        f"{repo}/",
                        f"{tmpdir}/",
                    ],
                    input=filtered,
                    text=True,
                    check=False,
                )
        console.print("[green]\u2713[/green] Untracked files synced")

        with console.status("[bold cyan]Linking dependencies ...", spinner="dots"):
            _link_deps(repo, tmpdir)
        console.print("[green]\u2713[/green] Dependencies linked")

        # Trust mise config so the subshell doesn't complain
        if (tmpdir / "mise.toml").exists():
            subprocess.run(["mise", "trust"], cwd=tmpdir, capture_output=True)

        console.print()
        console.print(f"[bold green]Worktree ready![/bold green] [dim]{tmpdir}[/dim]")
        console.print(f"[dim]Branch:[/dim] [bold]{resolved_branch}[/bold]")
        console.print()

        # Install signal handlers while subprocesses are running
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        if not shell_only:
            console.print(f"[bold cyan]Launching:[/bold cyan] {agent_cmd}\n")
            subprocess.run(agent_cmd, cwd=tmpdir, shell=True)

        # Drop into an interactive shell; cleanup happens when it exits
        console.print("[dim]Dropping into shell. Type 'exit' to clean up.[/dim]\n")

        # Clear the inherited claudway venv and activate the project's instead
        shell_env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
        shell_env["PATH"] = os.pathsep.join(
            p
            for p in os.environ.get("PATH", "").split(os.pathsep)
            if "claudway" not in p
        )

        venv_dir = tmpdir / "mamba" / "venv"
        shell_name = Path(user_shell).name
        if shell_name == "fish":
            activate_cmd = f"source {venv_dir}/bin/activate.fish"
        elif shell_name in ("bash", "sh"):
            activate_cmd = f"source {venv_dir}/bin/activate"
        else:
            activate_cmd = f"source {venv_dir}/bin/activate"

        # Populate shell context so do_cleanup can offer re-entry
        shell_ctx.update(
            user_shell=user_shell,
            shell_env=shell_env,
            activate_cmd=activate_cmd,
        )

        _launch_shell(user_shell, shell_env, activate_cmd, tmpdir)

        # Restore original handlers
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)
    finally:
        do_cleanup()
