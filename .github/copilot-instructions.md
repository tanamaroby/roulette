# Roulette — Copilot Instructions

## Project Overview

Roulette is a **macOS and Windows** media-shuffler UI built with **Python 3.9+ / PyQt6** that launches
**mpv** (the command-line media player) as a subprocess. The codebase is intentionally
thin: the UI orchestrates, the core layer does work, and mpv handles all actual playback.

---

## Architecture

```
app/
├── main.py                  ← Entry point. Generates icon, starts QApplication.
├── assets/
│   ├── generate_icon.py     ← Pillow script. Run once; produces icon.png + icon.ico.
│   ├── icon.png             ← Auto-generated. Do NOT commit (in .gitignore).
│   ├── toggle_on.svg        ← Checkbox toggle images (referenced by QSS).
│   └── toggle_off.svg
├── core/                    ← Business logic. Zero Qt imports allowed here.
│   ├── mpv_checker.py       ← Detect / install mpv. Extensible via MpvInstaller ABC.
│   ├── folder_manager.py    ← Persist folders to ~/.config/roulette/folders.json.
│   │                           Extensible via MediaResolver base class.
│   ├── playlist.py          ← Build + shuffle M3U playlists (PlaylistBuilder).
│   ├── player.py            ← MpvFlags dataclass + MpvPlayer subprocess launcher.
│   └── rule34_resolver.py   ← Rule34.xxx API resolver (MediaResolver subclass).
└── ui/                      ← All PyQt6 code lives here.
    ├── main_window.py       ← QMainWindow. Owns layout, stylesheet, mpv lifecycle.
    └── widgets/
        ├── folder_list.py   ← FolderListWidget: drag-drop folder management.
        ├── online_panel.py  ← OnlinePanel: Rule34.xxx fetch UI.
        └── settings_panel.py← SettingsPanel: maps UI controls → MpvFlags.
```

**Critical boundary:** `app/core/` must never import from `app/ui/`. The UI imports core;
core never imports UI. All Qt-related code belongs in `app/ui/`.

---

## Code Style

- **Python 3.9 target.** Always include `from __future__ import annotations` at the top of
  every file so `X | Y` union types and `list[str]` generics work without 3.10+.
- **Full type annotations** on every function signature — parameters and return type.
- **Private helpers** are prefixed with a single underscore (`_build_ui`, `_on_play`).
  Double-underscore name-mangling is not used.
- **No bare `python` or `pip` calls** in shell scripts or macOS docs — always `python3` / `pip3`
  since macOS does not provide a `python` symlink by default. PowerShell scripts for Windows may
  use `python` / `pip` as that is standard on Windows.
- **String quoting:** use single-quoted strings when the content contains double-quotes
  (e.g. `'Click "Add Folder"'`). Do not use Unicode smart-quotes (`"…"`) inside any
  Python string literal — they cause `SyntaxError` on Python 3.9.
- **Imports:** stdlib → third-party → local, each group separated by a blank line.
  No wildcard imports (`from x import *`).

---

## Extension Points (where new features belong)

| Goal                                           | Where to touch                                                                                                                                                 |
| ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| New mpv flag                                   | Add field to `MpvFlags` in `core/player.py`; map it in `_build_args()`; add widget in `ui/widgets/settings_panel.py` and update `get_flags()` / `set_flags()`. |
| New media source (e.g. YouTube, network share) | Subclass `MediaResolver` in `core/folder_manager.py`; implement `resolve(source) -> list[str]`; wire a new UI widget.                                          |
| Install mpv on Linux                           | Subclass `MpvInstaller` in `core/mpv_checker.py`; register in `_get_installer()`.                                                                              |
| New online playlist type                       | Use `PlaylistBuilder` from `core/playlist.py` — it accepts any list of path/URI strings.                                                                       |
| New UI panel / widget                          | Add to `app/ui/widgets/`; import in `main_window.py`; style via the single `_apply_stylesheet()` QSS block.                                                    |
| New online source (e.g. YouTube)               | Subclass `MediaResolver` in `core/folder_manager.py`; add a resolver like `rule34_resolver.py`; wire a new tab/panel in `ui/`.                                 |

---

## UI & Stylesheet Conventions

- All styling lives in a **single `_apply_stylesheet()` method** in `main_window.py`.
  Never use inline `setStyleSheet()` calls on individual widgets for colours or fonts.
- The stylesheet is built with an **f-string** so absolute asset paths (toggle SVGs) can
  be injected. Keep f-string braces as `{{` / `}}` for literal CSS braces.
- **Object names** are the selector mechanism — always set `setObjectName("...")` and
  match it in the QSS with `QWidget#objectName { ... }`. Do not style by class alone
  unless you intend to affect every instance of that widget class.
- **Layout margins:** 24px outer window margins; 16px inside group boxes; 16px row spacing
  in form layouts. Do not tighten these — the "cramped" look is the main UX complaint.
- **Toggle checkboxes** are rendered via `toggle_on.svg` / `toggle_off.svg` SVG images.
  If you add new `QCheckBox` controls, the existing QSS rule applies automatically.
- The horizontal scrollbar on the settings scroll area is permanently hidden
  (`ScrollBarAlwaysOff`). Keep it that way.

---

## mpv Subprocess Rules

- mpv is **always** launched via `MpvPlayer.play(playlist_path)` — never call
  `subprocess.Popen` with mpv directly from UI code.
- `MpvPlayer._build_args()` is the sole place that translates `MpvFlags` fields into
  CLI arguments. All flag logic belongs there.
- The playlist is written to a **temp M3U8 file** (`PlaylistBuilder.write_temp_m3u()`).
  Callers must ensure `_cleanup_temp()` is called on stop/close — see `main_window.py`.
- mpv exit callbacks run on a **background thread** (`_wait()`). Do not manipulate
  Qt widgets directly inside `on_exit` callbacks; post to the main thread if needed.

---

## Config & Persistence

- User folder list: `~/.config/roulette/folders.json`
- Written by `FolderManager.save()` — called automatically on every add/remove.
- No other persistent config exists yet. If you add settings persistence, use the same
  `~/.config/roulette/` directory and a new JSON file. Do not use `QSettings`.

---

## Running & Testing

```bash
# First time setup
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt

# Run
./run.sh                    # auto-installs deps, activates venv, launches app
python3 -m app.main         # run directly from repo root

# Syntax-check all modules
python3 -m py_compile app/ui/main_window.py app/ui/widgets/settings_panel.py \
    app/ui/widgets/folder_list.py app/ui/widgets/online_panel.py \
    app/core/mpv_checker.py app/core/folder_manager.py \
    app/core/player.py app/core/playlist.py \
    app/core/rule34_resolver.py app/main.py

# Regenerate icon (if deleted)
python3 app/assets/generate_icon.py
```

`requirements.txt` contains only: `PyQt6>=6.6.0`, `Pillow>=10.0.0`.  
`requirements-build.txt` contains: `pyinstaller>=6.0.0`.  
mpv itself is installed at runtime — via Homebrew on macOS, via winget on Windows.

---

## Packaging

### macOS

Builds use **PyInstaller** + `hdiutil` to produce a self-contained `.dmg`.

```bash
./build_dmg.sh          # produces dist/Roulette.dmg
```

### Windows

Builds use **PyInstaller** to produce a directory bundle, then zip it.

```powershell
powershell -ExecutionPolicy Bypass -File build_windows.ps1
# produces dist\Roulette-Windows.zip
```

Key files:

- `roulette.spec` — single PyInstaller spec for both platforms; wraps in `.app` on macOS only
- `build_dmg.sh` — macOS build pipeline: PyInstaller → staging → DMG
- `build_windows.ps1` — Windows build pipeline: PyInstaller → ZIP
- `.github/workflows/release.yml` — CI: builds DMG (macos-latest) + ZIP (windows-latest) on version tag push, uploads both to GitHub Releases

Do NOT embed mpv in the bundle — it is installed at runtime by `mpv_checker.py`.

---

## What NOT to Do

- Do not add docstrings, comments, or type annotations to code you didn't change.
- Do not add error handling for scenarios that cannot happen (internal-only calls).
- Do not introduce third-party libraries beyond PyQt6 and Pillow without discussion.
- Do not import Qt modules (`PyQt6.*`) anywhere inside `app/core/`.
- Do not call `subprocess.run` / `Popen` from UI files — delegate to `MpvPlayer`.
- Do not hardcode paths. Use `Path(__file__).parent` relative anchors.
- Do not use `QSettings` for persistence — use JSON in `~/.config/roulette/`.
