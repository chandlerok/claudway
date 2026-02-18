import subprocess
from pathlib import Path

import typer

from src.settings import SKIP_NAMES, SKIP_PREFIXES, SKIP_SUFFIXES


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


def ensure_branch(repo: Path, branch: str) -> str:
    """Ensure *branch* exists, prompting the user to create it if needed."""
    if branch_exists(repo, branch):
        return branch
    create = typer.confirm(
        f"Branch '{branch}' does not exist. Create it?", default=True
    )
    if not create:
        raise typer.Abort()
    git(repo, "branch", branch)
    return branch


def resolve_branch(repo: Path, branch: str | None) -> str:
    if branch is not None:
        return ensure_branch(repo, branch)
    branch_name = typer.prompt("Enter a branch name")
    return ensure_branch(repo, branch_name)
