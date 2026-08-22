param(
    [string]$RepoName = "developer-boss-fight",
    [ValidateSet("public", "private")]
    [string]$Visibility = "public"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is not installed or is not available in PATH."
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) is not installed. Install it, then run: gh auth login"
}

if (-not (Test-Path ".git")) {
    git init
    git branch -M main
}

git add .

$changes = git status --porcelain
if ($changes) {
    git commit -m "Release Developer Boss Fight V2.5"
}

$visibilityFlag = if ($Visibility -eq "private") { "--private" } else { "--public" }

gh repo create $RepoName $visibilityFlag --source=. --remote=origin --push

Write-Host "Repository published successfully." -ForegroundColor Green
