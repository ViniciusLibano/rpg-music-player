# Sound Helper

RPG Soundboard — play multiple YouTube audio tracks simultaneously with crossfade transitions.

## Requirements

- Arch Linux with `mpv`, `gtk3`, `python-gobject` installed
- Python 3.11+

```bash
sudo pacman -S mpv gtk3 python-gobject python
```

## Setup

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt

# Ensure yt-dlp is on PATH (already included in run.sh)
mkdir -p ~/.local/bin
ln -sf "$(pwd)/.venv/bin/yt-dlp" ~/.local/bin/yt-dlp
```

## Run

```bash
./run.sh
```

Or bind a key in Hyprland:

```ini
bind = $mainMod, S, exec, /path/to/sound-helper/run.sh
```

## Usage

1. Paste a YouTube URL into a track's text field.
2. Click **Play** to start playback.
3. Adjust **volume** with the slider.
4. Toggle **Loop** for continuous playback.
5. With a track playing, paste a URL into another track and click **Crossfade to this** — the source fades out while the destination fades in.

## Presets

- **Save** — stores all URLs, volumes, loop states and fade duration.
- **Load** — restores a saved preset.
- **Delete** — removes a preset.

Presets are stored in `~/.config/sound-helper/presets/`.
