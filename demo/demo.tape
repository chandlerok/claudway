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
Type "cw --help # lets take a look at the api"
Enter
Sleep 3s

# Show status
Type "cw status # currently we have no additional worktrees"
Enter
Sleep 3s

# Launch a temporary session on a new branch
Type "cw go # lets create one!"
Enter
Sleep 1s
Type "demo"
Sleep 2s
Backspace
Backspace
Backspace
Backspace
Sleep 1s
Enter
Type "demo/add-dark-mode"
Enter
Sleep 1s
Type "y"
Enter
Sleep 1s
Type "y"
Enter
Sleep 2s
Enter
Sleep 5s

# Show the worktree is active
Type "exit"
Enter
Sleep 2s
Type "cw status # we're still in the temporary worktree right now"
Enter
Sleep 3s

# Exit — temporary worktree auto-cleans up
Type "exit # upon exiting the originating shell, it will be cleaned up"
Enter
Sleep 4s

# Show the worktree has been cleaned up
Type "cw status # see, its gone!"
Enter
Sleep 3s

# Launch a persistent session
Type "cw go demo/refactor-api --shell --persistent # lets create a persistent worktree and just go straight to the shell"
Enter
Sleep 2s
Type "y"
Enter
Sleep 2s
Type "y"
Enter
Sleep 5s

# Exit — persistent worktree survives
Type "exit"
Enter
Sleep 4s

# Show the persistent worktree is active
Type "cw status # even though we exited, we'll see that the persistent worktree is still there"
Enter
Sleep 3s

# Switch back into the persistent worktree
Type "cw switch # now lets re-enter it!"
Enter
Sleep 1s
Type "demo"
Enter
Sleep 3s

# Exit again
Type "exit"
Enter
Sleep 3s

# Remove the persistent worktree
Type "cw rm # lets get rid of it now"
Enter
Sleep 1s
Type "demo"
Enter
Sleep 2s
Type "y"
Enter
Sleep 3s

# Final status — clean
Type "cw status # its gone now!"
Enter
Sleep 3s

# Show that the branches are still there
Type "git branch # ...but our branches are still here!"
Enter
Sleep 5s
