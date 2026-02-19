import contextlib
import hashlib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import typer
from rich.console import Console

from src.commands.git import git, should_sync
from src.settings import DEP_SYMLINKS, PERSISTENT_WORKTREES_DIR


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
    """Create a git worktree. Raises WorktreeConflict if already checked out."""
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

        raise WorktreeConflictError(conflict_path) from None


class WorktreeConflictError(Exception):
    """Raised when a branch is already checked out in another worktree."""

    def __init__(self, existing_path: str) -> None:
        self.existing_path = existing_path
        super().__init__(f"Branch already checked out at {existing_path}")


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


def persistent_worktree_dir(repo: Path, branch: str) -> Path:
    """Return the deterministic persistent worktree path for a branch in a repo."""
    sanitized = re.sub(r"[/\\]", "-", branch)
    key = f"{branch}:{repo}"
    short_hash = hashlib.sha256(key.encode()).hexdigest()[:8]
    return PERSISTENT_WORKTREES_DIR / f"{sanitized}-{short_hash}"


def list_worktrees(repo: Path) -> list[dict[str, str]]:
    """Return a list of worktree dicts with 'path', 'branch', and 'type' keys."""
    result = subprocess.run(
        ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []

    worktrees: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            current = {"path": line.removeprefix("worktree ")}
        elif line.startswith("HEAD "):
            current["head"] = line.removeprefix("HEAD ")
        elif line.startswith("branch "):
            current["branch"] = line.removeprefix("branch refs/heads/")
        elif line == "detached":
            head = current.get("head", "")
            current["branch"] = f"(detached at {head[:7]})" if head else "(detached)"
        elif line == "bare":
            current["branch"] = "(bare)"
        elif line == "" and current:
            current.setdefault("branch", "(unknown)")
            current["type"] = classify_worktree(repo, Path(current["path"]))
            worktrees.append(current)
            current = {}
    if current:
        current.setdefault("branch", "(unknown)")
        current["type"] = classify_worktree(repo, Path(current["path"]))
        worktrees.append(current)
    return worktrees


def classify_worktree(repo: Path, wt_path: Path) -> str:
    """Classify a worktree as 'main', 'persistent', or 'temporary'."""
    try:
        if wt_path.resolve() == repo.resolve():
            return "main"
    except OSError:
        pass
    wt_resolved = wt_path.resolve()
    if wt_resolved.is_relative_to(PERSISTENT_WORKTREES_DIR.resolve()):
        return "persistent"
    tmpdir = Path(tempfile.gettempdir()).resolve()
    wt_resolved_str = str(wt_resolved)
    if wt_resolved_str.startswith(str(tmpdir)) and "/cw-" in wt_resolved_str:
        return "temporary"
    return "unknown"


def is_valid_worktree(repo: Path, path: Path) -> bool:
    """Check if the given path is registered in git worktree list."""
    result = subprocess.run(
        ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            wt_path = line.removeprefix("worktree ")
            if Path(wt_path).resolve() == path.resolve():
                return True
    return False


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
