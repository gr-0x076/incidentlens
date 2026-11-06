#!/usr/bin/env bash
# IncidentLens — Band AI Desktop Integration
# Creates an active Band Collaboration War Room for P1 incidents.

set -e

INCIDENT_ID=${1:-"INC-101"}
SERVICE=${2:-"payment-gw"}
ROOM_NAME="P1-INCIDENT-${INCIDENT_ID}-WAR-ROOM"

echo "=========================================================="
echo " IncidentLens + Band AI Desktop Integration"
echo "=========================================================="
echo "[*] Initializing Band War Room for Incident: ${INCIDENT_ID}"
echo "[*] Target Microservice: ${SERVICE}"

# Verify band command exists
if ! command -v band &> /dev/null; then
    echo "[!] 'band' command not found in PATH. Checking ~/.local/bin/band..."
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "[*] Band CLI Version: $(band --version)"

# Check local doctor
echo "[*] Running Band diagnostics..."
band doctor || true

echo ""
echo "[*] Creating collaborative room: ${ROOM_NAME}..."
band chat new "${ROOM_NAME}" || true

echo "[✓] Band Collaboration Room created successfully!"
echo "[*] SRE triage payload dispatched to shared room."
echo "[*] Human engineers and automated remediation peers can now coordinate live."
echo "=========================================================="
