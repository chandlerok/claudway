import subprocess
from pathlib import Path

import typer

from src.settings import SKIP_NAMES, SKIP_PREFIXES, SKIP_SUFFIXES


def detect_repo() -> Path | None:
    """Detect the root of the main git repository from the current directory.

    Works even when CWD is inside an existing worktree.
    Returns None if not inside a git repository.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    git_common_dir = Path(result.stdout.strip())
    # git-common-dir returns the .git directory; its parent is the repo root
    return git_common_dir.parent


def get_current_branch(repo: Path) -> str:
    """Return the current branch name for the given repo."""
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return "HEAD"
    return result.stdout.strip()


def should_sync(path: str) -> bool:
    """Return True if this untracked file should be synced to the worktree."""
    for prefix in SKIP_PREFIXES:
        if prefix in path:
            return False
    name = path.rsplit("/", 1)[-1]
    if name in SKIP_NAMES:
        return False
    return not name.endswith(SKIP_SUFFIXES)


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
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


def branch_exists(repo: Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", branch],
        capture_output=True,
    )
    return result.returncode == 0


def ensure_branch(repo: Path, branch: str, base: str | None = None) -> str:
    """Ensure *branch* exists, prompting the user to create it if needed."""
    if branch_exists(repo, branch):
        return branch
    create = typer.confirm(
        f"Branch '{branch}' does not exist. Create it?", default=True
    )
    if not create:
        raise typer.Abort()
    if base:
        git(repo, "branch", branch, base)
    else:
        git(repo, "branch", branch)
    return branch


def resolve_branch(repo: Path, branch: str | None, base: str | None = None) -> str:
    if branch is not None:
        return ensure_branch(repo, branch, base=base)
    branch_name = typer.prompt("Enter a branch name")
    return ensure_branch(repo, branch_name, base=base)
