# Claudway

A CLI tool that creates isolated dev environments for working with AI agents. Spin up temporary git worktrees so you can run multiple Claude Code sessions (or anything else) on different branches simultaneously — without them stepping on each other.

![claudway demo](./demo/demo.gif)

## Installation

```bash
git clone git@github.com:chandlerok/claudway.git && cd claudway
uv tool install .
```

This installs the `cw` command.

## Quick Start

`cd` into your git repository and run:

```bash
cw go feature/my-branch
```

Claudway auto-detects the repo from your current directory and creates a temporary worktree on the specified branch. New branches are forked from your current branch.

## Usage

### `cw go`

Start an isolated dev environment in a git worktree.

```
cw go [BRANCH] [OPTIONS]
```

| Option | Description |
|---|---|
| `BRANCH` | Git branch to work on (fzf-like picker if omitted) |
| `-c`, `--command` | Custom command to run instead of the default agent |
| `-s`, `--shell` | Drop into a shell without launching the agent |
| `-p`, `--persistent` | Create a persistent worktree that survives shell exit |

When run without a branch name, `cw go` presents a fuzzy-searchable picker listing local branches first (sorted by most recent commit), followed by remote-only branches (also sorted by most recent commit). You can type to filter, select with arrow keys, or choose "+ Create new branch..." to start fresh. Remote branches are automatically checked out as local tracking branches.

#### Examples

```bash
# Pick a branch interactively
cw go

# Start Claude Code on a new feature branch
cw go feature/add-auth

# Run a custom command instead of the default agent
cw go bugfix/login -c "cursor ."

# Just get a shell in the worktree, no agent
cw go experiment --shell

# Create a persistent worktree that sticks around after you exit
cw go feature/long-running -p

# Re-enter an existing persistent worktree (picks up where you left off)
cw go feature/long-running -p
```

#### Persistent vs Temporary Worktrees

By default, worktrees are **temporary** — they are automatically cleaned up when you exit the shell. This is great for quick, one-off tasks.

With the `-p` / `--persistent` flag, worktrees are stored in `~/.local/share/claudway/worktrees/` and **survive shell exit**. When you run `cw go -p` for the same branch again, the existing worktree is reused with all your changes intact. This is useful for long-running tasks where you want to come back later.

Persistent worktrees can be removed explicitly with `cw rm`.

### `cw switch`

Open a shell in an existing worktree without launching an agent. Useful for inspecting changes or running commands in a worktree created by another session.

```
cw switch [BRANCH]
```

When run without a branch name, presents a fuzzy picker listing all active worktrees (main, persistent, and temporary). Warns when switching into a temporary worktree, since it will be deleted when its original session exits.

### `cw rm`

Remove a persistent or temporary worktree.

```
cw rm [BRANCH] [OPTIONS]
```

| Option | Description |
|---|---|
| `BRANCH` | Branch name of the worktree to remove (picker if omitted) |
| `-f`, `--force` | Remove without prompting, even with uncommitted changes |

If there are uncommitted changes, `cw rm` shows a summary and asks for confirmation before deleting.

### `cw set-default-command`

Set or change the default command. If the command is omitted, you will be prompted interactively.

```bash
cw set-default-command [COMMAND]
```

#### Examples

```bash
# CLI AI Agents
cw set-default-command "claude" # default
cw set-default-command "opencode"

# IDEs
cw set-default-command "cursor ."
cw set-default-command "code ."
cw set-default-command "zed ."

# TUI text editors
cw set-default-command "vim"
cw set-default-command "nvim"
cw set-default-command "hx"
cw set-default-command "nano"
```

### Show current configuration and active worktrees
```bash
cw status
```

## How It Works

When you run `cw go`, claudway:

1. **Detects your git repository** — finds the repo root from your current directory, even if you're inside an existing worktree.

2. **Creates a temporary git worktree** — a separate checkout of your repo on the specified branch, placed in a temp directory. New branches are forked from your current branch. This gives the agent its own working copy so it won't conflict with your main checkout or other sessions.

3. **Syncs untracked files** — copies over untracked files from your main repo (skipping large/generated directories like `node_modules`, `.venv`, `dist`, etc.) so the worktree has your local config files and other non-committed assets.

4. **Symlinks dependencies** — links dependency directories (like `node_modules` and virtualenvs) from the main repo into the worktree to avoid redundant installs.

5. **Launches your agent** — runs `claude` (or whatever command you specify with `-c`) inside the worktree.

6. **Drops into a shell** — after the agent exits, you get an interactive shell in the worktree to inspect changes, run tests, etc.

7. **Guards against lost work** — when exiting a temporary worktree, checks for uncommitted changes and warns you before cleanup, giving you a chance to go back and commit or stash.

8. **Cleans up** — when you exit the shell, temporary worktrees are automatically removed. Persistent worktrees (`-p`) are kept for later reuse. Your branches and commits are always preserved in the main repo.

## Configuration

Claudway stores its config at `~/.config/claudway/config.toml`:

```toml
default_command = "claude"
```

| Key | Description | Default |
|---|---|---|
| `default_command` | Default command to run in new sessions | `claude` |
