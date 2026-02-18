import atexit
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
    if name.endswith(SKIP_SUFFIXES):
        return False
    return True


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, result.args,
            output=result.stdout, stderr=result.stderr,
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


def _cleanup(repo: Path, tmpdir: Path) -> None:
    try:
        _git(repo, "worktree", "remove", "--force", str(tmpdir))
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
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
        typer.Option("--command", "-c", help="Command to run instead of the default agent."),
    ] = None,
    shell_only: Annotated[
        bool,
        typer.Option("--shell", "-s", help="Drop straight into a shell without launching the agent."),
    ] = False,
) -> None:
    """Start an isolated dev environment in a git worktree."""
    settings = ClaudwaySettings()
    if settings.repo_location is None:
        console.print("[red]Error:[/red] repo location is not set. Run [bold]cw set-repo-location[/bold] first.")
        raise typer.Exit(1)

    repo = Path(settings.repo_location)
    resolved_branch = _resolve_branch(repo, branch)
    agent_cmd = command or settings.agent
    user_shell = os.environ.get("SHELL", "/bin/sh")

    tmpdir = Path(tempfile.mkdtemp(prefix="cw-"))
    # git worktree add requires the target dir not to exist
    tmpdir.rmdir()
    cleanup_done = False

    def do_cleanup() -> None:
        nonlocal cleanup_done
        if cleanup_done:
            return
        cleanup_done = True
        console.print(f"\n[yellow]Cleaning up worktree ...[/yellow]")
        _cleanup(repo, tmpdir)
        console.print("[green]Done.[/green]")

    atexit.register(do_cleanup)

    original_sigint = signal.getsignal(signal.SIGINT)
    original_sigterm = signal.getsignal(signal.SIGTERM)

    def _signal_handler(signum: int, _frame: object) -> None:
        do_cleanup()
        sys.exit(128 + signum)

    try:
        with console.status("[bold cyan]Creating worktree ...", spinner="dots"):
            try:
                _git(repo, "worktree", "add", str(tmpdir), resolved_branch)
            except subprocess.CalledProcessError as e:
                stderr = (e.stderr or "").strip()
                if "already checked out" in stderr:
                    console.print(f"\n[red]Error:[/red] {stderr}")
                    console.print("Run [bold]git worktree list[/bold] to see existing worktrees, "
                                  "or [bold]git worktree remove <path>[/bold] to clean up a stale one.")
                    raise typer.Exit(1)
                raise
        console.print(f"[green]\u2713[/green] Worktree created for [bold]{resolved_branch}[/bold]")

        with console.status("[bold cyan]Syncing untracked files ...", spinner="dots"):
            untracked = _git(repo, "ls-files", "--others")
            filtered = "\n".join(
                p for p in untracked.stdout.splitlines() if _should_sync(p)
            )
            if filtered:
                subprocess.run(
                    [
                        "rsync", "-a",
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

        # Clear the inherited headway-dev venv and activate mamba's instead
        shell_env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
        shell_env["PATH"] = os.pathsep.join(
            p for p in os.environ.get("PATH", "").split(os.pathsep)
            if "claudway" not in p
        )

        venv_dir = tmpdir / "mamba" / "venv"
        shell_name = Path(user_shell).name
        if shell_name == "fish":
            activate_cmd = f"source {venv_dir}/bin/activate.fish"
            subprocess.run([user_shell, "-C", activate_cmd], cwd=tmpdir, env=shell_env)
        elif shell_name in ("bash", "sh"):
            activate_cmd = f"source {venv_dir}/bin/activate"
            subprocess.run([user_shell, "--rcfile", "/dev/stdin"], cwd=tmpdir, env=shell_env,
                           input=f"[ -f ~/.bashrc ] && source ~/.bashrc; {activate_cmd}\n",
                           text=True)
        else:
            activate_cmd = f"source {venv_dir}/bin/activate"
            subprocess.run([user_shell, "-c", f"{activate_cmd}; exec {user_shell} -i"],
                           cwd=tmpdir, env=shell_env)

        # Restore original handlers
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)
    finally:
        do_cleanup()
