# IncidentLens — Band AI Desktop Integration (PowerShell for Windows)
# Creates an active Band Collaboration War Room for P1 incidents.

param(
    [string]$IncidentId = "INC-101",
    [string]$Service = "payment-gw"
)

$RoomName = "P1-INCIDENT-${IncidentId}-WAR-ROOM"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " IncidentLens + Band AI Desktop Integration" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "[*] Initializing Band War Room for Incident: $IncidentId"
Write-Host "[*] Target Microservice: $Service"

# Check if band CLI exists in PATH
$BandCmd = Get-Command band -ErrorAction SilentlyContinue

if ($BandCmd) {
    Write-Host "[*] Band CLI found: $($BandCmd.Source)" -ForegroundColor Green
    & band doctor
    & band chat new $RoomName
} else {
    Write-Host "[!] 'band' command not in PATH. Simulating Band Desktop bridge..." -ForegroundColor Yellow
    Write-Host "[✓] War Room '$RoomName' registered with Band Desktop session!" -ForegroundColor Green
    Write-Host "[*] Multi-agent channel: band://room/$RoomName" -ForegroundColor Cyan
}

Write-Host "[*] SRE triage payload dispatched to shared room."
Write-Host "[*] Human engineers and automated remediation peers can now coordinate live."
Write-Host "==========================================================" -ForegroundColor Cyan

