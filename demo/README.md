# Recording the Demo GIF

The demo GIF is recorded using [VHS](https://github.com/charmbracelet/vhs), a tool that generates terminal GIFs from a simple scripting language.

## Prerequisites

```bash
brew install vhs
```

VHS also requires a Chromium-based browser. If it fails with a connection error, set the `CHROME_PATH` environment variable:

```bash
export CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
```

## Recording

From the repo root:

```bash
CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" vhs demo/demo.tape
```

This outputs `demo/demo.gif`.

## Editing

Modify `demo.tape` to change the recording. See the [VHS documentation](https://github.com/charmbracelet/vhs) for the full tape syntax. Key settings:

- `Set TypingSpeed` — how fast commands are typed
- `Sleep` — pause duration between steps
- `Set Theme` — terminal color theme
- `Set FontSize` / `Set Width` / `Set Height` — dimensions
