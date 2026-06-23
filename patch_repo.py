#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_repo.py - russify the campaign-selection screen (launcher "Official" tab).

The launcher's campaign names/descriptions are read from
<install>/data/{mod,nwm}/repository.json (gamedata), NOT from dialog.tlk. This data
is read ONLY from the install tree: it cannot be delivered through Steam Workshop
(verified exhaustively - no override/hak/development/modules/userdir layer feeds the
launcher's "Official" repository group; Workshop content lands in a separate
"Community" group). So a Workshop subscription russifies everything EXCEPT this one
screen. This script patches those two install files directly.

Cross-platform (macOS / Linux / Windows), idempotent, keeps an English backup
(<file>.en.bak) next to each file. Safe to run on EVERY launch - e.g. set Steam
Launch Options to:
    python3 /full/path/patch_repo.py && %command%
so that if a Steam update restores the English files, they are re-patched before
the game starts.

  patch_repo.py [--game DIR] [--ru-dir DIR] [--restore]
"""
import argparse, copy, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

# common install locations, checked in order when --game is not given
CANDIDATES = [
    "~/Library/Application Support/Steam/steamapps/common/Neverwinter Nights",      # macOS Steam
    "~/.local/share/Steam/steamapps/common/Neverwinter Nights",                     # Linux Steam
    "~/.steam/steam/steamapps/common/Neverwinter Nights",                           # Linux Steam (alt)
    "~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/common/Neverwinter Nights",  # Flatpak
    "C:/Program Files (x86)/Steam/steamapps/common/Neverwinter Nights",             # Windows Steam
    "C:/GOG Games/Neverwinter Nights Enhanced Edition",                             # Windows GOG
    "C:/Program Files (x86)/GOG Galaxy/Games/Neverwinter Nights Enhanced Edition",  # Windows GOG (Galaxy)
]


def find_game(explicit):
    if explicit:
        return os.path.expanduser(explicit)
    for c in CANDIDATES:
        p = os.path.expanduser(c)
        if os.path.isfile(os.path.join(p, "data", "nwm", "repository.json")):
            return p
    return None


def remap_cp1251_cps(s):
    """Cyrillic -> U+00xx codepoints (= CP1251 bytes). The launcher draws these
    names with a 256-glyph bitmap font, so real UTF-8 shows as '????'; re-encoding
    each char to its CP1251 byte lands it on the Cyrillic glyph. ensure_ascii=True
    then writes them as \\u00xx (valid ASCII JSON)."""
    out = []
    for ch in s:
        if ord(ch) < 0x80:
            out.append(ch)
        else:
            try:
                out.append(chr(ch.encode("cp1251")[0]))
            except UnicodeEncodeError:
                out.append(ch)
    return "".join(out)


def overlay(english, ru):
    """Overlay RU name/description (by uuid) onto the English structure, remapped."""
    out = copy.deepcopy(english)
    tr = lambda v: remap_cp1251_cps(v) if isinstance(v, str) else v
    for f in ("name", "description"):
        if f in ru:
            out[f] = tr(ru[f])
    for key in ("campaigns", "modules"):
        if isinstance(out.get(key), list) and isinstance(ru.get(key), list):
            by = {it.get("uuid"): it for it in ru[key] if isinstance(it, dict)}
            for it in out[key]:
                if isinstance(it, dict) and it.get("uuid") in by:
                    r = by[it["uuid"]]
                    for f in ("name", "description"):
                        if f in r:
                            it[f] = tr(r[f])
    return out


def nonascii(d):
    return sum(1 for c in json.dumps(d, ensure_ascii=False) if ord(c) > 0x7F)


def patch_one(sub, game, ru_dir):
    cur = os.path.join(game, "data", sub, "repository.json")
    ru_path = os.path.join(ru_dir, "data", sub, "repository.json")
    bak = cur + ".en.bak"
    if not os.path.isfile(cur):
        print(f"  skip data/{sub}: no repository.json in install"); return
    if not os.path.isfile(ru_path):
        print(f"  skip data/{sub}: no RU source ({ru_path})"); return
    current = json.load(open(cur, encoding="utf-8"))
    # Pick the English source. The russified file has thousands of non-ASCII
    # codepoints; English has ~0-2. So >50 == already russified -> use the backup
    # as the pristine English source (avoids re-remapping). Otherwise current IS
    # English -> refresh the backup from it.
    if nonascii(current) > 50 and os.path.isfile(bak):
        english = json.load(open(bak, encoding="utf-8"))
    else:
        english = current
        if nonascii(current) <= 50:
            json.dump(english, open(bak, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    ru = json.load(open(ru_path, encoding="utf-8"))
    json.dump(overlay(english, ru), open(cur, "w", encoding="utf-8"), ensure_ascii=True, indent=2)
    print(f"  patched data/{sub}/repository.json")


def restore_one(sub, game):
    cur = os.path.join(game, "data", sub, "repository.json")
    bak = cur + ".en.bak"
    if os.path.isfile(bak):
        json.dump(json.load(open(bak, encoding="utf-8")),
                  open(cur, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"  restored data/{sub}/repository.json")
    else:
        print(f"  no backup for data/{sub}")


def main():
    ap = argparse.ArgumentParser(description="Russify the launcher campaign-selection screen")
    ap.add_argument("--game", help="NWN:EE install dir (auto-detected if omitted)")
    ap.add_argument("--ru-dir", default=os.path.join(HERE, "payload"),
                    help="dir holding data/{mod,nwm}/repository.json RU source (default: payload/)")
    ap.add_argument("--restore", action="store_true", help="restore English from .en.bak backups")
    args = ap.parse_args()
    game = find_game(args.game)
    if not game:
        sys.exit("ERROR: NWN:EE install not found. Pass --game <path>.")
    print(f"game: {game}")
    for sub in ("mod", "nwm"):
        if args.restore:
            restore_one(sub, game)
        else:
            patch_one(sub, game, os.path.abspath(args.ru_dir))
    print("done.")


if __name__ == "__main__":
    main()
