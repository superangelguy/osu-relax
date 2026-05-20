# osu! Relax Cheat

External relax hack for osu! Standard — auto-clicks circles and holds sliders in sync with the beatmap.

Runs as a persistent monitor: detects beatmap changes, syncs to your first tap, and handles pause/fail/retry automatically.

## How It Works

1. Reads the currently selected `.osu` beatmap by finding the most recently accessed file in your Songs folder
2. Parses hit objects and timing points to build a playable timeline
3. Waits for you to start playing (detects Z/X keypress)
4. Auto-clicks circles and holds sliders in time with the music
5. Detects pause (Escape), fail, retry, and beatmap changes — adapts automatically

## Requirements

- Windows
- Python 3.8+
- osu! Stable (Latest)

## Installation

```bash
git clone https://github.com/yourname/osu-relax.git
cd osu-relax
pip install -r requirements.txt
```

## Usage

```bash
python osu.py
```

1. Make sure osu! is running with a song selected
2. Run the script — it connects to osu! and waits
3. Start playing in osu! — press Z or X for the first note
4. The script takes over and clicks the rest of the map

### Controls

| Key | Action |
|-----|--------|
| `Z` / `X` | First tap syncs the script (then it auto-clicks) |
| `Escape` | Pause / Resume the engine |
| `Escape` (in terminal) | Exit the script |

### Command-line

You can also pass a beatmap path directly:

```bash
python osu.py "C:\Users\...\Songs\123 Artist - Title\Artist - Title (Mapper) [Difficulty].osu"
```

Or drag-and-drop a `.osu` file onto the script.

## Notes

- Uses wall-clock timing (may drift slightly on very long maps)
- Requires osu! to be running before the script starts
- Only supports osu! Standard mode
- Run as Administrator if you encounter permission issues

## Disclaimer

This is an educational project. Use at your own risk. Cheating violates osu! terms of service and may result in a ban.
