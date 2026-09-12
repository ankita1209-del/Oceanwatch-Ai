<#
PowerShell helper to configure git author, commit all changes, and push.
Usage examples:
  .\push_changes.ps1 -Branch main -RepoUrl https://github.com/AngelicaDolare/your-repo.git
  .\push_changes.ps1 -Branch main -UseSsh

Notes:
- For HTTPS pushes you'll be prompted for credentials (use a GitHub Personal Access Token as password).
- For SSH, ensure your public key is added to your GitHub account.
#>

param(
    [string]$RepoUrl = "",
    [string]$Branch = "main",
    [string]$AuthorName = "AngelicaDolare",
    [string]$AuthorEmail = "angelicadolare@gmail.com",
    [switch]$UseSsh
)

Write-Host "Using branch: $Branch"

# Configure local git author
git config user.name "$AuthorName"
git config user.email "$AuthorEmail"

if ($RepoUrl -ne "") {
    # If origin not set, add remote
    $remote = git remote
    if (-not ($remote -match 'origin')) {
        git remote add origin $RepoUrl
        Write-Host "Added remote origin -> $RepoUrl"
    } else {
        Write-Host "Remote 'origin' already exists"
    }
}

# Optional: create SSH key if requested and not present
if ($UseSsh) {
    $sshKeyPath = "$env:USERPROFILE\.ssh\id_rsa.pub"
    if (-not (Test-Path $sshKeyPath)) {
        Write-Host "No SSH public key found. Generating one..."
        ssh-keygen -t rsa -b 4096 -C $AuthorEmail -f "$env:USERPROFILE\.ssh\id_rsa" -N ""
        Write-Host "Public key generated. Add the contents of $sshKeyPath to your GitHub account settings -> SSH and GPG keys."
        Get-Content $sshKeyPath | clip
        Write-Host "Public key copied to clipboard. Open GitHub and paste it. Press Enter when done."
        Read-Host
    } else {
        Write-Host "SSH public key exists; copying to clipboard for convenience."
        Get-Content $sshKeyPath | clip
        Write-Host "Public key copied to clipboard. Add it to GitHub if not already added. Press Enter when done."
        Read-Host
    }
}

# Pull latest (rebase) from origin
try {
    git pull --rebase origin $Branch
} catch {
    Write-Host "Warning: git pull failed. Continuing to add/commit." -ForegroundColor Yellow
}

# Stage and commit
git add -A

$msg = Read-Host "Enter commit message (default: 'Add Member 3 data+pipeline scripts')"
if ([string]::IsNullOrWhiteSpace($msg)) { $msg = "Add Member 3 data+pipeline scripts" }

# Use explicit author for the commit
git commit --author="$AuthorName <$AuthorEmail>" -m "$msg" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "No changes to commit or commit failed." -ForegroundColor Yellow
} else {
    Write-Host "Committed changes with author $AuthorName <$AuthorEmail>"
}

# Push
Write-Host "Pushing to origin/$Branch..."
git push origin $Branch

Write-Host "Done. Verify on GitHub that the commit appears under the account for '$AuthorEmail'."
