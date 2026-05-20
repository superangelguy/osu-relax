# osu! Relax

> External relax cheat for osu! Standard — auto-clicks circles and holds sliders in sync with any beatmap.

![Platform](https://img.shields.io/badge/platform-Windows-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.8+-yellow?style=flat-square)
![osu!](https://img.shields.io/badge/osu!-Stable%20(Latest)-pink?style=flat-square)

---

## Features

- **Auto-detection** — finds your currently selected beatmap, no manual path entry
- **Tap to sync** — press Z/X for the first note and the script takes over
- **Persistent monitor** — stays running, detects beatmap changes as you browse
- **Pause / Resume** — press Escape to pause, press again to resume (timing compensated)
- **Fail / Retry detection** — auto-resets when the map ends or you retry
- **Slider support** — holds sliders for the correct duration with proper velocity calculation
- **Alternating keys** — switches between Z and X for natural stream patterns
- **Clean console** — minimal output, debounced beatmap detection

## How It Works

1. Connects to the running `osu!.exe` process
2. Scans your `Songs` folder for the most recently accessed `.osu` file
3. Parses `[TimingPoints]` and `[HitObjects]` to build a timeline with correct BPM and slider velocity
4. Waits for you to press Z or X (your first tap in-game)
5. Anchors the wall clock to the beatmap timeline and auto-clicks every note
6. Monitors for Escape (pause), map completion, fail, retry, and beatmap changes

## Installation

```bash
git clone https://github.com/superangelguy/osu-relax.git
cd osu-relax
pip install -r requirements.txt
```

## Usage

```bash
python osu.py
```

1. Open osu! and select a song
2. Run the script — it connects and waits
3. Start playing — press **Z** or **X** for the first note
4. The script handles the rest

### Command-line

```bash
python osu.py "path/to/beatmap.osu"
```

Or drag-and-drop a `.osu` file onto the script.

### Controls

| Key | Action |
|-----|--------|
| `Z` / `X` | First tap syncs the script |
| `Escape` | Pause / Resume |
| `Escape` (terminal) | Exit |

## Requirements

- **Windows** only
- **Python 3.8** or newer
- **osu! Stable (Latest)** release

## Disclaimer

This project is for educational purposes only. Using cheats violates the [osu! terms of service](https://osu.ppy.sh/wiki/en/Legal/Terms) and may result in a permanent account ban. Use at your own risk.

## License

MIT © [superangelguy](https://github.com/superangelguy)
