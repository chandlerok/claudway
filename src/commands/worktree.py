import contextlib
import shutil
import subprocess
from pathlib import Path

import typer
from rich.console import Console

from src.commands.git import git, should_sync
from src.settings import DEP_SYMLINKS


console = Console()


def link_deps(repo: Path, worktree: Path) -> None:
    for rel_path in DEP_SYMLINKS:
        source = repo / rel_path
        target = worktree / rel_path
        if source.exists() and not target.exists():
            target.symlink_to(source)


def uncommitted_changes(worktree: Path) -> str:
    """Return porcelain status output, or empty string if clean."""
    result = subprocess.run(
        ["git", "-C", str(worktree), "status", "--porcelain", "-unormal"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def cleanup_worktree(repo: Path, tmpdir: Path) -> None:
    with contextlib.suppress(subprocess.CalledProcessError, FileNotFoundError):
        git(repo, "worktree", "remove", "--force", str(tmpdir))
    if tmpdir.exists():
        shutil.rmtree(tmpdir, ignore_errors=True)


def create_worktree(repo: Path, tmpdir: Path, branch: str) -> None:
    """Create a git worktree, resolving conflicts interactively."""
    try:
        git(repo, "worktree", "add", str(tmpdir), branch)
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        already_used = (
            "already checked out" in stderr or "already used by worktree" in stderr
        )
        if not already_used:
            raise

        conflict_path = find_conflicting_worktree(repo, branch)
        if not conflict_path:
            console.print(f"\n[red]Error:[/red] {stderr}")
            raise typer.Exit(1) from None

        console.print(
            f"[yellow]Branch '{branch}' is already checked out at:"
            f"[/yellow]\n  {conflict_path}"
        )
        if not typer.confirm("Remove the existing worktree?", default=True):
            raise typer.Exit(1) from None
        cleanup_worktree(repo, Path(conflict_path))
        git(repo, "worktree", "add", str(tmpdir), branch)


def find_conflicting_worktree(repo: Path, branch: str) -> str | None:
    """Return the path of an existing worktree that has *branch* checked out."""
    wt_list = git(repo, "worktree", "list", "--porcelain")
    candidate = ""
    for line in wt_list.stdout.splitlines():
        if line.startswith("worktree "):
            candidate = line.removeprefix("worktree ")
        elif line.startswith("branch ") and line.endswith(f"/{branch}"):
            return candidate
    return None


def sync_untracked_files(repo: Path, worktree: Path) -> None:
    """Rsync untracked (non-ignored) files from *repo* into *worktree*."""
    untracked = git(repo, "ls-files", "--others")
    filtered = "\n".join(p for p in untracked.stdout.splitlines() if should_sync(p))
    if filtered:
        subprocess.run(
            [
                "rsync",
                "-a",
                "--files-from=-",
                f"{repo}/",
                f"{worktree}/",
            ],
            input=filtered,
            text=True,
            check=False,
        )
