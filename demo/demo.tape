# Claudway Demo
Output demo/demo.gif

Set FontSize 16
Set Width 1000
Set Height 600
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 40ms
Set Shell fish
Env SHELL "/opt/homebrew/bin/fish"

# Show help
Type "cw --help"
Enter
Sleep 3s

# Show status
Type "cw status"
Enter
Sleep 3s

# Launch a temporary session on a new branch
Type "cw go demo/add-dark-mode --shell"
Enter
Sleep 2s
Type "y"
Enter
Sleep 5s

# Show the worktree is active
Type "cw status"
Enter
Sleep 3s

# Exit — temporary worktree auto-cleans up
Type "exit"
Enter
Sleep 4s

# Launch a persistent session
Type "cw go demo/refactor-api --shell --persistent"
Enter
Sleep 2s
Type "y"
Enter
Sleep 5s

# Show the persistent worktree is active
Type "cw status"
Enter
Sleep 3s

# Exit — persistent worktree survives
Type "exit"
Enter
Sleep 4s

# Status shows the persistent worktree is still there
Type "cw status"
Enter
Sleep 3s

# Switch back into the persistent worktree
Type "cw switch demo/refactor-api"
Enter
Sleep 3s

# Exit again
Type "exit"
Enter
Sleep 3s

# Remove the persistent worktree
Type "cw rm demo/refactor-api"
Enter
Sleep 2s
Type "y"
Enter
Sleep 3s

# Final status — clean
Type "cw status"
Enter
Sleep 3s
