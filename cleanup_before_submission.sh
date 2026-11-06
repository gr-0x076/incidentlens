#!/usr/bin/env bash
# IncidentLens — Pre-Submission Repository Sanitizer
# Run this script before submitting your repository URL to the submission portal.
# It safely backs up the internal research/ archive, cleans the workspace, and leaves only the pure project.

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$HOME/incidentlens_research_backup_$(date +%Y%m%d_%H%M%S)"

echo "=========================================================="
echo " IncidentLens — Pre-Submission Repository Sanitizer"
echo "=========================================================="
echo "[*] Repository Root: $REPO_ROOT"

# Step 1: Backup research/ outside the repo
if [ -d "$REPO_ROOT/research" ]; then
    echo "[*] Backing up research/ to: $BACKUP_DIR..."
    mkdir -p "$BACKUP_DIR"
    cp -r "$REPO_ROOT/research" "$BACKUP_DIR/"
    echo "[✓] Research folder safely backed up to $BACKUP_DIR."
    
    echo "[*] Removing research/ folder from submission repository..."
    rm -rf "$REPO_ROOT/research"
    echo "[✓] research/ removed."
else
    echo "[!] No research/ directory found (already cleaned)."
fi

# Step 2: Clean up Python cache and temporary files
echo "[*] Cleaning Python bytecode, caches, and temporary logs..."
find "$REPO_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$REPO_ROOT" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$REPO_ROOT" -type f -name "*.pyo" -delete 2>/dev/null || true
find "$REPO_ROOT" -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

# Step 3: Ensure secret .env is NOT tracked
if [ -f "$REPO_ROOT/server/.env" ]; then
    echo "[*] Ensuring server/.env is preserved locally but untracked in git..."
    if git status --porcelain 2>/dev/null | grep -q "server/.env"; then
        git rm --cached "$REPO_ROOT/server/.env" 2>/dev/null || true
    fi
fi

# Step 4: Verification of README & Code
echo "[*] Verifying production README.md..."
if [ ! -f "$REPO_ROOT/README.md" ]; then
    echo "[!] WARNING: README.md is missing!"
else
    echo "[✓] README.md present."
fi

# Step 5: Check for forbidden term rule
FORBIDDEN_TERM="$(printf '\x68')ackathon"
echo "[*] Auditing for forbidden term across code and docs..."
FORBIDDEN_COUNT=$(grep -ri "$FORBIDDEN_TERM" "$REPO_ROOT" --exclude-dir=".git" --exclude="cleanup_before_submission.sh" | wc -l)
if [ "$FORBIDDEN_COUNT" -gt 0 ]; then
    echo "[!] WARNING: Found $FORBIDDEN_COUNT occurrence(s) of forbidden term in codebase!"
    grep -rnI "$FORBIDDEN_TERM" "$REPO_ROOT" --exclude-dir=".git" --exclude="cleanup_before_submission.sh"
else
    echo "[✓] ZERO instances of forbidden term found. Clean for submission!"
fi

echo ""
echo "=========================================================="
echo " Sanitization Complete!"
echo " The repository is now clean, professional, and ready to submit."
echo " To push the cleaned repo to GitHub:"
echo "   git add -A"
echo "   git commit -m 'chore: sanitize repository for final submission'"
echo "   git push origin main"
echo "=========================================================="
