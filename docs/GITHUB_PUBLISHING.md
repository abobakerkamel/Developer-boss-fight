# Publishing to GitHub

## Recommended repository name

`developer-boss-fight`

## Option A — GitHub CLI (fastest)

1. Install Git and GitHub CLI.
2. Authenticate once:

```powershell
gh auth login
```

3. Open PowerShell inside the repository and run:

```powershell
.\scripts\publish_to_github.ps1 -RepoName "developer-boss-fight" -Visibility public
```

The script initializes Git, creates the first commit, creates the GitHub repository, sets `origin`, and pushes `main`.

## Option B — Browser + Git

Create an empty repository named `developer-boss-fight` on GitHub, then run:

```bash
git init
git add .
git commit -m "Release Developer Boss Fight V2.5"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/developer-boss-fight.git
git push -u origin main
```

## Suggested GitHub About text

> Real-time AR computer-vision boss fight controlled by hand gestures, built with Python, OpenCV and MediaPipe.

## Suggested topics

`computer-vision`, `opencv`, `mediapipe`, `python`, `augmented-reality`, `gesture-recognition`, `hand-tracking`, `game-development`, `human-computer-interaction`, `vfx`

## Before publishing

- Run all tests.
- Check that no private videos/screenshots are committed.
- Review `ASSETS_NOTICE.md`.
- Add a short demo GIF/video link to the README after publishing your social demo.
