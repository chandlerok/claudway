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
    # Normalize remote refs (e.g. "origin/foo" -> "foo") to avoid detached HEAD
    if branch.startswith("origin/"):
        branch = branch.removeprefix("origin/")
    if branch_exists(repo, branch):
        return branch
    # If a remote tracking branch exists, create a local branch tracking it
    remote_ref = f"origin/{branch}"
    if branch_exists(repo, remote_ref):
        git(repo, "branch", "--track", branch, remote_ref)
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


def list_local_branches(repo: Path) -> list[str]:
    """Return local branch names sorted by most recent commit first."""
    try:
        output = git(
            repo,
            "branch",
            "--sort=-committerdate",
            "--format=%(refname:short)",
        )
    except subprocess.CalledProcessError:
        return []
    return [b for b in output.stdout.strip().splitlines() if b]


def list_remote_branches(repo: Path) -> list[str]:
    """Return remote branch names (no prefix), sorted by recency."""
    try:
        output = git(
            repo,
            "branch",
            "-r",
            "--sort=-committerdate",
            "--format=%(refname:short)",
        )
    except subprocess.CalledProcessError:
        return []
    branches: list[str] = []
    for b in output.stdout.strip().splitlines():
        if not b or "/HEAD" in b:
            continue
        # Only include branches from origin; other remotes would fail
        # to track/checkout with the hardcoded origin/ assumptions elsewhere.
        if not b.startswith("origin/"):
            continue
        name = b.removeprefix("origin/")
        if name:
            branches.append(name)
    return branches


CREATE_NEW = "+ Create new branch..."


def select_branch(repo: Path) -> str:
    """Show a fuzzy-filterable branch list. Falls back to plain prompt if not a TTY."""
    from src.commands.picker import fuzzy_select, is_interactive

    current = get_current_branch(repo)
    local = [b for b in list_local_branches(repo) if b != current]
    local_set = set(local)
    remote_only = [
        b for b in list_remote_branches(repo) if b not in local_set and b != current
    ]

    if not is_interactive():
        return typer.prompt("Enter a branch name")

    choices: list[str] = [CREATE_NEW]
    choices.extend(local)
    choices.extend(f"origin/{b}" for b in remote_only)

    selected = fuzzy_select("Select a branch:", choices)

    if selected == CREATE_NEW:
        return typer.prompt("Enter a new branch name")
    if selected.startswith("origin/"):
        return selected.removeprefix("origin/")
    return selected


def resolve_branch(repo: Path, branch: str | None, base: str | None = None) -> str:
    if branch is not None:
        return ensure_branch(repo, branch, base=base)
    branch_name = select_branch(repo)
    return ensure_branch(repo, branch_name, base=base)
