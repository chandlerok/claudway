# Claudway

A CLI tool that creates isolated dev environments for working with AI agents. Spin up temporary git worktrees so you can run multiple Claude Code sessions on different branches simultaneously — without them stepping on each other.

## Installation

```bash
pip install .
```

This installs the `cw` command.

## Quick Start

1. **Set your repo location:**

   ```bash
   cw set-repo-location /path/to/your/repo
   ```

   This saves the path to `~/.claudway/config`. If you skip this step, claudway will prompt you the first time you run a command.

2. **Start a session:**

   ```bash
   cw start my-feature-branch
   ```

   If the branch doesn't exist, claudway will offer to create it for you. If you omit the branch name, you'll be prompted to enter one.

## Usage

```
cw start [BRANCH] [OPTIONS]
```

| Option | Description |
|---|---|
| `BRANCH` | Git branch to work on (prompted if omitted) |
| `-c`, `--command` | Custom command to run instead of the default agent |
| `-s`, `--shell` | Drop into a shell without launching the agent |

### Examples

```bash
# Start Claude Code on a new feature branch
cw start feature/add-auth

# Run a custom command instead of the default agent
cw start bugfix/login -c "cursor"

# Just get a shell in the worktree, no agent
cw start experiment --shell
```

### Other Commands

```bash
# Set or change the repo location
cw set-repo-location [PATH]
```

## How It Works

When you run `cw start`, claudway:

1. **Creates a temporary git worktree** — a separate checkout of your repo on the specified branch, placed in a temp directory. This gives the agent its own working copy so it won't conflict with your main checkout or other sessions.

2. **Syncs untracked files** — copies over untracked files from your main repo (skipping large/generated directories like `node_modules`, `.venv`, `dist`, etc.) so the worktree has your local config files and other non-committed assets.

3. **Symlinks dependencies** — links dependency directories (like `node_modules` and virtualenvs) from the main repo into the worktree to avoid redundant installs.

4. **Launches your agent** — runs `claude` (or whatever command you specify with `-c`) inside the worktree.

5. **Drops into a shell** — after the agent exits, you get an interactive shell in the worktree to inspect changes, run tests, etc.

6. **Cleans up** — when you exit the shell, the worktree is automatically removed. Your branch and its commits are preserved in the main repo.

## Configuration

Claudway stores its config at `~/.claudway/config` as environment variables:

| Variable | Description | Default |
|---|---|---|
| `CLAUDWAY_REPO_LOCATION` | Path to your git repository | _(none, required)_ |
| `CLAUDWAY_AGENT` | Default agent command to run | `claude` |
