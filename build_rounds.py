"""Generate rounds.js for the "Which game is it?" mini-game.

Reads the canonical *-dialog-only.txt extracts under ../../../docs/games/,
filters them down to playable scenes, and writes a compact JS literal that
defines window.QUIZ_DATA so index.html can load it via a plain <script>
tag (no fetch, no server required).
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
DOCS_GAMES = REPO_ROOT / "docs" / "games"

GAMES = [
    {
        "id": "dott-en",
        "title": "Day of the Tentacle",
        "file": DOCS_GAMES / "dott" / "dott-dialog-only.txt",
    },
    {
        "id": "dott-de",
        "title": "Day of the Tentacle (German)",
        "file": DOCS_GAMES / "dott" / "dott-dialog-only-german.txt",
    },
    {
        "id": "mi1dos",
        "title": "The Secret of Monkey Island",
        "file": DOCS_GAMES / "mi1dos" / "mi1dos-dialog-only.txt",
    },
    {
        "id": "mi2dos",
        "title": "Monkey Island 2: LeChuck's Revenge",
        "file": DOCS_GAMES / "mi2dos" / "mi2dos-dialog-only.txt",
    },
    {
        "id": "indy4",
        "title": "Indiana Jones and the Fate of Atlantis",
        "file": DOCS_GAMES / "indy4" / "indy4-dialog-only.txt",
    },
    {
        "id": "samnmax",
        "title": "Sam & Max Hit the Road",
        "file": DOCS_GAMES / "samnmax" / "samnmax-dialog-only.txt",
    },
    {
        "id": "dig",
        "title": "The Dig",
        "file": DOCS_GAMES / "The Dig (CD DOS)" / "the-dig-cd-dos-dialog-only.txt",
    },
]

ROUND_CAP_PER_GAME = 400
MIN_LINE_LEN = 2
SCENE_WINDOW = 10  # lines per "scene" chunk (full reveal size)
SCENE_STRIDE = 10  # non-overlapping chunks
SEED = 0xD077

PIPE_SPLIT = re.compile(r"\s+\|\s+")
ROOM_RE = re.compile(r"_room_(\d+)", re.IGNORECASE)
SCRIPT_FILENAME_RE = re.compile(r"^(\d{3,5})_(.+?)\.scu$", re.IGNORECASE)
DIG_TAG_RE = re.compile(r"^/[A-Z][A-Z0-9_]*\.\d+/")
WHITESPACE_RE = re.compile(r"\s+")


def parse_dialog_file(path: Path) -> list[dict]:
    """Return a list of {script, type, speaker, text} dicts in file order."""
    rows: list[dict] = []
    if not path.exists():
        print(f"  WARN: missing file {path}")
        return rows
    text = path.read_text(encoding="utf-8", errors="replace")
    for raw in text.splitlines():
        line = raw.strip()
        if not line or "|" not in line:
            continue
        parts = PIPE_SPLIT.split(line)
        if len(parts) < 3:
            continue
        script = parts[0].strip()
        # Typed: script | type | speaker | line
        # Legacy: script | speaker | line
        maybe_type = parts[1].strip().upper()
        if maybe_type in ("SPOKEN", "CHOICE") and len(parts) >= 4:
            row_type = maybe_type
            speaker = (parts[2].strip() or "Unknown")
            body = " | ".join(parts[3:]).strip()
        else:
            row_type = "SPOKEN"
            speaker = (parts[1].strip() or "Unknown")
            body = " | ".join(parts[2:]).strip()
        if not script or not body:
            continue
        rows.append({
            "script": script,
            "type": row_type,
            "speaker": speaker,
            "text": body,
        })
    return rows


def clean_text_for_display(s: str, *, is_dig: bool) -> str:
    t = s
    if is_dig:
        t = DIG_TAG_RE.sub("", t)
    t = WHITESPACE_RE.sub(" ", t).strip()
    return t


def script_display(script_path: str) -> str:
    base = script_path.rsplit("/", 1)[-1]
    m_room = ROOM_RE.search(base)
    if m_room:
        return f"Room {int(m_room.group(1))}"
    m_file = SCRIPT_FILENAME_RE.match(base)
    if m_file:
        prefix, slug = m_file.group(1), m_file.group(2)
        return f"{prefix} - {slug}"
    return base


def group_scenes(rows: list[dict]) -> list[list[dict]]:
    """Group rows by contiguous identical script value."""
    scenes: list[list[dict]] = []
    current: list[dict] = []
    current_script: str | None = None
    for row in rows:
        if row["script"] != current_script:
            if current:
                scenes.append(current)
            current = [row]
            current_script = row["script"]
        else:
            current.append(row)
    if current:
        scenes.append(current)
    return scenes


def build_rounds_for_game(game: dict, rng: random.Random) -> list[dict]:
    is_dig = game["id"] == "dig"
    rows = parse_dialog_file(game["file"])
    if not rows:
        return []

    spoken: list[dict] = []
    for r in rows:
        if r["type"] != "SPOKEN":
            continue
        if "%" in r["text"]:
            continue
        text = clean_text_for_display(r["text"], is_dig=is_dig)
        if len(text) < MIN_LINE_LEN:
            continue
        spoken.append({
            "script": r["script"],
            "speaker": r["speaker"],
            "text": text,
        })

    script_groups = group_scenes(spoken)
    rounds: list[dict] = []
    for group in script_groups:
        # Slice each script-group into bounded chunks so we get multiple
        # rounds per room and the "full scene" reveal stays readable.
        for start in range(0, len(group), SCENE_STRIDE):
            chunk = group[start:start + SCENE_WINDOW]
            if len(chunk) < 3:
                continue
            previews = [s["text"] for s in chunk[:3]]
            if len(set(previews)) == 1:
                continue
            script_path = chunk[0]["script"]
            rounds.append({
                "gameId": game["id"],
                "scriptPath": script_path,
                "scriptDisplay": script_display(script_path),
                "preview": previews,
                "full": [{"speaker": s["speaker"], "text": s["text"]} for s in chunk],
            })

    if len(rounds) > ROUND_CAP_PER_GAME:
        rng.shuffle(rounds)
        rounds = rounds[:ROUND_CAP_PER_GAME]
    return rounds


def main() -> None:
    rng = random.Random(SEED)
    all_rounds: list[dict] = []
    games_meta: list[dict] = []
    print(f"repo root: {REPO_ROOT}")
    for game in GAMES:
        per_game_rng = random.Random((SEED, game["id"]).__hash__() & 0xFFFFFFFF)
        rounds = build_rounds_for_game(game, per_game_rng)
        print(f"  {game['id']:<10} -> {len(rounds):>4} rounds")
        all_rounds.extend(rounds)
        games_meta.append({"id": game["id"], "title": game["title"]})

    rng.shuffle(all_rounds)

    payload = {"games": games_meta, "rounds": all_rounds}
    out_path = HERE / "rounds.js"
    json_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    js_text = "window.QUIZ_DATA = " + json_text + ";\n"
    out_path.write_text(js_text, encoding="utf-8")
    size_kb = out_path.stat().st_size / 1024
    print(f"wrote {out_path} ({size_kb:.1f} KB, {len(all_rounds)} rounds, {len(games_meta)} games)")


if __name__ == "__main__":
    main()
