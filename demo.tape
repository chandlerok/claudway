# Claudway Demo
Output demo.gif

Set FontSize 16
Set Width 1000
Set Height 600
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 40ms
Set Shell fish

# Show help
Type "cw --help"
Enter
Sleep 3s

# Show status
Type "cw status"
Enter
Sleep 3s

# Launch an isolated session on a new branch
Type "cw go demo/add-dark-mode --shell"
Enter
Sleep 5s

# Show we're in the worktree
Type "git branch --show-current"
Enter
Sleep 2s

# Exit and watch cleanup
Type "exit"
Enter
Sleep 3s
