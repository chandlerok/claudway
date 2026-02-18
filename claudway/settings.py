from pathlib import Path

import typer
from pydantic import DirectoryPath
from pydantic_settings import BaseSettings, SettingsConfigDict


CONFIG_DIR = Path.home() / ".claudway"
CONFIG_FILE = CONFIG_DIR / "config"

ENV_PREFIX = "CLAUDWAY_"

# Old config paths for one-time migration
_OLD_CONFIG_DIR = Path.home() / ".headway-dev"
_OLD_CONFIG_FILE = _OLD_CONFIG_DIR / "config"
_OLD_ENV_PREFIX = "HEADWAY_DEV_"


def _migrate_config() -> None:
    """Migrate ~/.headway-dev/config to ~/.claudway/config if needed."""
    if CONFIG_FILE.exists() or not _OLD_CONFIG_FILE.exists():
        return

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    old_content = _OLD_CONFIG_FILE.read_text()
    new_content = old_content.replace(_OLD_ENV_PREFIX, ENV_PREFIX)
    CONFIG_FILE.write_text(new_content)


# Run migration on import
_migrate_config()


class ClaudwaySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX,
        env_file=str(CONFIG_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )
    repo_location: DirectoryPath | None = None
    agent: str = "claude"


def save_repo_location(path: Path) -> None:
    """Persist the repo location to the config file at ~/.claudway/config."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Read existing config lines (if any), filtering out old repo_location
    key = f"{ENV_PREFIX}REPO_LOCATION"
    existing_lines: list[str] = []
    if CONFIG_FILE.exists():
        for line in CONFIG_FILE.read_text().splitlines():
            if not line.startswith(f"{key}="):
                existing_lines.append(line)

    existing_lines.append(f"{key}={path.resolve()}")
    CONFIG_FILE.write_text("\n".join(existing_lines) + "\n")


def set_repo_location_with_prompt() -> Path:
    """Interactively prompt the user for a valid repo path."""
    while True:
        raw = typer.prompt("Enter the path to your repository")
        path = Path(raw).expanduser().resolve()
        if path.is_dir():
            save_repo_location(path)
            return path
        typer.echo(f"Error: '{path}' is not a valid directory. Please try again.")


def validate_path(value: str) -> Path:
    """Validate that a string argument is an existing directory."""
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        raise typer.BadParameter(f"'{path}' is not a valid directory.")
    return path
