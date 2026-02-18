import tomllib
from pathlib import Path

import tomli_w
import typer
from pydantic import BaseModel, DirectoryPath


CONFIG_DIR = Path.home() / ".config" / "claudway"
CONFIG_FILE = CONFIG_DIR / "config.toml"


class ClaudwaySettings(BaseModel):
    default_repo_location: DirectoryPath | None = None
    default_command: str = "claude"

    @classmethod
    def load(cls) -> "ClaudwaySettings":
        """Load settings from the TOML config file."""
        if not CONFIG_FILE.exists():
            return cls()
        data = tomllib.loads(CONFIG_FILE.read_text())
        return cls.model_validate(data)


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

SKIP_SUFFIXES = (".sqlite3", ".db", ".pyc")
SKIP_NAMES = frozenset({".DS_Store", ".coverage"})

# Directories to symlink from the main repo into the worktree
DEP_SYMLINKS = (
    "web/node_modules",
    "mamba/venv",
)


def save_setting(key: str, value: str) -> None:
    """Persist a single setting to the TOML config file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    data: dict[str, str] = {}
    if CONFIG_FILE.exists():
        data = tomllib.loads(CONFIG_FILE.read_text())
    data[key] = value
    CONFIG_FILE.write_bytes(tomli_w.dumps(data).encode())


def save_default_repo_location(path: Path) -> None:
    """Persist the default repo location to the TOML config file."""
    save_setting("default_repo_location", str(path.resolve()))


def set_default_repo_location_with_prompt() -> Path:
    """Interactively prompt the user for a valid repo path."""
    while True:
        raw = typer.prompt("Enter the path to your repository")
        path = Path(raw).expanduser().resolve()
        if path.is_dir():
            save_default_repo_location(path)
            return path
        typer.echo(f"Error: '{path}' is not a valid directory. Please try again.")


def validate_path(value: str) -> Path:
    """Validate that a string argument is an existing directory."""
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        raise typer.BadParameter(f"'{path}' is not a valid directory.")
    return path
