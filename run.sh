#!/usr/bin/env bash
# run.sh — Launch Roulette from the project root.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Activate venv if present ──────────────────────────────────────────
if [[ -f ".venv/bin/activate" ]]; then
    source ".venv/bin/activate"
fi

# ── Install Python deps if needed ────────────────────────────────────
python3 -c "import PyQt6" 2>/dev/null || {
    echo "Installing Python dependencies…"
    pip3 install -r requirements.txt
}

python3 -c "import PIL" 2>/dev/null || pip3 install Pillow

# ── Run ───────────────────────────────────────────────────────────────
exec python3 -m app.main "$@"
