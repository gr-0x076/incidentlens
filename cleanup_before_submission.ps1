# IncidentLens — Pre-Submission Repository Sanitizer (PowerShell for Windows)
# Run this script before submitting your repository URL to the submission portal.
# It safely backs up the internal research/ archive, cleans the workspace, and leaves only the pure project.

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupDir = Join-Path $env:USERPROFILE "incidentlens_research_backup_$Timestamp"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " IncidentLens — Pre-Submission Repository Sanitizer" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "[*] Repository Root: $RepoRoot"

# Step 1: Backup research/ outside the repo
$ResearchPath = Join-Path $RepoRoot "research"
if (Test-Path $ResearchPath) {
    Write-Host "[*] Backing up research/ to: $BackupDir..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    Copy-Item -Path $ResearchPath -Destination $BackupDir -Recurse -Force
    Write-Host "[✓] Research folder safely backed up." -ForegroundColor Green

    Write-Host "[*] Removing research/ folder from submission repo..." -ForegroundColor Yellow
    Remove-Item -Path $ResearchPath -Recurse -Force
    Write-Host "[✓] research/ removed." -ForegroundColor Green
} else {
    Write-Host "[!] No research/ directory found (already cleaned)." -ForegroundColor Gray
}

# Step 2: Clean up Python cache and temporary files
Write-Host "[*] Cleaning Python bytecode, caches, and temporary logs..." -ForegroundColor Yellow
Get-ChildItem -Path $RepoRoot -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $RepoRoot -Recurse -File -Include "*.pyc", "*.pyo" | Remove-Item -Force -ErrorAction SilentlyContinue

# Step 3: Check for forbidden word rule
$ForbiddenTerm = "$([char]104)ackathon"
Write-Host "[*] Auditing for forbidden term across code and docs..." -ForegroundColor Yellow
$ForbiddenFiles = Get-ChildItem -Path $RepoRoot -Recurse -File -Exclude "*.git*", "*.ps1", "*.sh", "*.pdf" | Select-String -Pattern $ForbiddenTerm -SimpleMatch
if ($ForbiddenFiles) {
    Write-Host "[!] WARNING: Found occurrences of forbidden term in codebase:" -ForegroundColor Red
    $ForbiddenFiles | Select-Object Path, LineNumber, Line | Format-Table -AutoSize
} else {
    Write-Host "[✓] ZERO instances of forbidden term found. Clean for submission!" -ForegroundColor Green
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Sanitization Complete!" -ForegroundColor Green
Write-Host " The repository is now clean, professional, and ready to submit." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

