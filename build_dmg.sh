#!/usr/bin/env bash
# build_dmg.sh — build Roulette.app and package it as a .dmg
# Usage: ./build_dmg.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

APP_NAME="Roulette"
DMG_NAME="${APP_NAME}.dmg"
STAGING_DIR="dist/dmg_staging"
APP_PATH="dist/${APP_NAME}.app"
DMG_PATH="dist/${DMG_NAME}"

# ── 1. Ensure build deps ────────────────────────────────────────────────────
echo "→ Installing build dependencies…"
python3 -m pip install --quiet -r requirements.txt -r requirements-build.txt

# Ensure the icon exists before building
if [[ ! -f "app/assets/icon.png" ]]; then
    echo "→ Generating icon…"
    python3 app/assets/generate_icon.py
fi

# ── 2. Build .app with PyInstaller ──────────────────────────────────────────
echo "→ Building ${APP_NAME}.app…"
python3 -m PyInstaller roulette.spec --noconfirm

# ── 3. Package into .dmg ────────────────────────────────────────────────────
echo "→ Creating ${DMG_NAME}…"
rm -rf "$STAGING_DIR" "$DMG_PATH"
mkdir -p "$STAGING_DIR"

# Copy the .app into staging
cp -R "$APP_PATH" "$STAGING_DIR/"

# Add a symlink to /Applications for the drag-install UX
ln -s /Applications "$STAGING_DIR/Applications"

# Create a temporary read/write image, then convert to compressed read-only
TEMP_DMG="dist/${APP_NAME}_tmp.dmg"
hdiutil create \
    -volname "$APP_NAME" \
    -srcfolder "$STAGING_DIR" \
    -ov \
    -format UDRW \
    "$TEMP_DMG"

hdiutil convert "$TEMP_DMG" -format UDZO -o "$DMG_PATH"
rm -f "$TEMP_DMG"
rm -rf "$STAGING_DIR"

echo ""
echo "✓ Done: dist/${DMG_NAME}"
echo ""
echo "Note: On other Macs, users may see a Gatekeeper warning because the app"
echo "is unsigned. They can bypass it with: right-click → Open → Open."
