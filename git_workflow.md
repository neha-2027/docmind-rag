# Git workflow

Git is a distributed version control system. The command git init creates a repository, git add stages changes, and git commit records the staged changes with a message. The command git push uploads commits to a remote repository such as one hosted on GitHub.

Branches let developers work on features in isolation. The command git checkout -b creates and switches to a new branch. When the work is ready, a pull request asks teammates to review the changes before they are merged into the main branch.

A merge conflict happens when two branches change the same lines. Git marks the conflicting sections in the file, and the developer edits the file to keep the correct version and then commits the result.

The .gitignore file lists files that Git should not track, such as virtual environments, compiled files and local database files.
