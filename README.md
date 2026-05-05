# Roulette 🎲

**Roulette** is a modern macOS media-shuffler built on top of [mpv](https://mpv.io/).  
Add folders, hit Play, and let it shuffle everything — fullscreen, looping forever, no fuss.

---

## Features

| Feature | Default |
|---|---|
| Shuffle all media in saved folders | ✅ On |
| Fullscreen playback | ✅ On |
| Infinite playlist loop | ✅ On |
| Per-file loop | Off |
| Hardware decoding (`videotoolbox`) | Auto |
| Subtitle auto-load | Fuzzy match |
| Volume, speed, mute | Adjustable |
| Always-on-top / borderless window | Toggleable |
| Raw mpv flag passthrough | Supported |
| Drag-and-drop folder import | ✅ |
| Auto-install mpv via Homebrew | ✅ |

Supported media formats: `.mkv` `.mp4` `.avi` `.mov` `.webm` `.flv` `.m4v` `.wmv` `.ts` `.m2ts` `.mpg` `.mpeg` `.ogv` `.3gp` `.divx` `.rm` `.rmvb` `.mp3` `.flac` `.aac` `.ogg` `.wav` `.m4a` `.opus` `.wma`

---

## Requirements

| Requirement | Version |
|---|---|
| Python | ≥ 3.10 |
| PyQt6 | ≥ 6.6 |
| Pillow | ≥ 10.0 (icon generation) |
| mpv | any recent build |

mpv is installed automatically on first run if missing (via Homebrew).

---

## Installation

```bash
# 1. Clone
git clone https://github.com/your-username/roulette.git
cd roulette

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Run
./run.sh
# or directly:
python -m app.main
```

---

## Usage

1. Click **+ Add Folder** (or drag folders onto the list) to register media directories.  
2. Adjust playback settings in the right panel — all changes take effect immediately on next play.  
3. Click **▶ Play** to launch mpv with the built playlist.  
4. Click **⏹ Stop** to terminate mpv at any time.

Folder list is persisted to `~/.config/roulette/folders.json`.

---

## Project Structure

```
roulette/
├── app/
│   ├── main.py                  ← entry point
│   ├── assets/
│   │   ├── generate_icon.py     ← generates icon.png with Pillow
│   │   └── icon.png             ← auto-generated on first run
│   ├── core/
│   │   ├── mpv_checker.py       ← detect / install mpv
│   │   ├── folder_manager.py    ← persist & resolve media folders
│   │   ├── playlist.py          ← build & shuffle M3U playlists
│   │   └── player.py            ← MpvFlags dataclass + subprocess launch
│   └── ui/
│       ├── main_window.py       ← QMainWindow
│       └── widgets/
│           ├── folder_list.py   ← drag-drop folder list widget
│           └── settings_panel.py← mpv flags UI
├── requirements.txt
├── run.sh
└── README.md
```

---

## Extending Roulette

### Add a new mpv flag

1. Add a field to `MpvFlags` in [app/core/player.py](app/core/player.py).  
2. Map it to a CLI argument in `MpvPlayer._build_args()`.  
3. Add a matching widget in [app/ui/widgets/settings_panel.py](app/ui/widgets/settings_panel.py) and update `get_flags()` / `set_flags()`.

### Add an online playlist source (e.g. YouTube)

1. Subclass `MediaResolver` in [app/core/folder_manager.py](app/core/folder_manager.py).  
2. Implement `resolve(source: str) -> list[str]` — return yt-dlp or direct URIs.  
3. Surface a new UI widget to accept URLs/playlist IDs.  
4. Pass the resolved URIs to `PlaylistBuilder` as usual.

### Add a Linux / Windows installer

Subclass `MpvInstaller` in [app/core/mpv_checker.py](app/core/mpv_checker.py) and register it in `_get_installer()`.

---

## License

MIT
