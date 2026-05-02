# Which game is it?

Single-file browser quiz built from the dialog extracts in `docs/games/`.

### How to play

Open `index.html` in any modern browser (works from `file://`, no server needed).

Each round shows three consecutive lines from one scene of a LucasArts adventure. Pick which game they came from. After you guess, the full scene is revealed along with the game title and the scene's script id.

### Source data

Rounds are baked into `rounds.js` from these dialog-only extracts:

- `docs/games/dott/dott-dialog-only.txt` — Day of the Tentacle
- `docs/games/dott/dott-dialog-only-german.txt` — Day of the Tentacle (German)
- `docs/games/mi1dos/mi1dos-dialog-only.txt` — The Secret of Monkey Island
- `docs/games/mi2dos/mi2dos-dialog-only.txt` — Monkey Island 2: LeChuck's Revenge
- `docs/games/indy4/indy4-dialog-only.txt` — Indiana Jones and the Fate of Atlantis
- `docs/games/samnmax/samnmax-dialog-only.txt` — Sam & Max Hit the Road
- `docs/games/The Dig (CD DOS)/the-dig-cd-dos-dialog-only.txt` — The Dig

Row format is the canonical pipe-separated dialog lookup defined in `docs/extraction/DIALOG-LOOKUP-STANDARD.md`.

### Regenerate `rounds.js`

```
python build_rounds.py
```

The generator filters to `SPOKEN` lines, drops MI2 `%placeholder%` rows, strips Dig `/BUNDLE.NNN/` tags from displayed text, groups consecutive lines from the same script file into a "scene", and emits up to 400 rounds per game (seeded random sample). The output file defines `window.QUIZ_DATA` so `index.html` can load it with a plain `<script>` tag and run on `file://`.

### Notes

- DOTT German is its own answer choice, so German-language rounds are intentionally easy.
- Wrong answers are sampled from the other six titles per round.
- No external assets, no fetch, no build step beyond the optional Python regenerator.
