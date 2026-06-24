#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install_ru.py - install the NWN:EE russifier on macOS (Steam).

Adapts the Windows "NWN: EE/Classic" russifier (ZoG / Lord_Draconis / DragonZH)
to the Mac build of the game. The Windows installer (Inno Setup + Parser_tlk.exe)
does not run on macOS, so:
  - dialog.tlk is built natively (build_tlk.py),
  - the remaining files (fonts, characters, repository.json) are placed at the
    correct paths of the Mac build.

Safe: backs up the originals before replacing them and keeps a manifest.json;
  install_ru.py --uninstall  reverts everything.
Repeatable: can be run again after a Steam update (which restores the English
  dialog.tlk) - the English source is detected automatically.
"""
import argparse, json, os, re, shutil, struct, subprocess, sys, copy

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_GAME = os.path.expanduser(
    "~/Library/Application Support/Steam/steamapps/common/Neverwinter Nights")
DEFAULT_USERDIR = os.path.expanduser("~/Documents/Neverwinter Nights")
DEFAULT_PAYLOAD = os.path.join(HERE, "payload")      # extracted russifier (app/)
BACKUP = os.path.join(HERE, "backup")
MANIFEST = os.path.join(BACKUP, "manifest.json")
BUILT_TLK = os.path.join(HERE, "build", "dialog.tlk")


def _has_game(root):
    return bool(root) and os.path.exists(os.path.join(root, "lang", "en", "data", "dialog.tlk"))


def _steam_library_roots():
    """NWN install dir under every Steam library (parse libraryfolders.vdf) — handles
    games moved to a second library / external drive."""
    out = []
    for v in ("~/Library/Application Support/Steam/steamapps/libraryfolders.vdf",
              "~/.steam/steam/steamapps/libraryfolders.vdf",
              "~/.local/share/Steam/steamapps/libraryfolders.vdf"):
        v = os.path.expanduser(v)
        if os.path.exists(v):
            for path in re.findall(r'"path"\s+"([^"]+)"', open(v, encoding="utf-8", errors="replace").read()):
                out.append(os.path.join(path.replace("\\\\", "/"), "steamapps", "common", "Neverwinter Nights"))
    return out


def find_game():
    """Locate the NWN:EE install without --game: Steam (default + every library),
    common GOG/Beamdog folders, then a macOS Spotlight search (so it also finds GOG
    installs or a copy on an external drive). Returns the game root or None."""
    cands = [DEFAULT_GAME] + _steam_library_roots() + [os.path.expanduser(p) for p in (
        "~/.steam/steam/steamapps/common/Neverwinter Nights",
        "~/.local/share/Steam/steamapps/common/Neverwinter Nights",
        "/Applications/Neverwinter Nights Enhanced Edition",
        "~/Applications/Neverwinter Nights Enhanced Edition",
        "~/GOG Games/Neverwinter Nights Enhanced Edition",
        "~/Library/Application Support/GOG.com/Galaxy/Games/Neverwinter Nights Enhanced Edition")]
    for c in cands:
        if _has_game(c):
            return c
    if sys.platform == "darwin":
        try:
            out = subprocess.run(["mdfind", "-name", "dialog.tlk"],
                                 capture_output=True, text=True, timeout=15).stdout
            for line in out.splitlines():
                tail = "/lang/en/data/dialog.tlk"
                if line.endswith(tail) and _has_game(line[:-len(tail)]):
                    return line[:-len(tail)]
        except Exception:
            pass
    return None

def log(m): print(m)

# ----------------------------------------------------------------- helpers ----
def tlk_strref1_is_english(path):
    """True if strref 1 is pure ASCII (English) rather than already russified."""
    try:
        d = open(path, "rb").read(20 + 2*40 + 64)
        eo = struct.unpack_from("<I", d, 16)[0]
        b = 20 + 1*40
        flags = struct.unpack_from("<I", d, b)[0]
        off = struct.unpack_from("<I", d, b+28)[0]
        sz = struct.unpack_from("<I", d, b+32)[0]
        full = open(path, "rb").read()
        txt = full[eo+off:eo+off+sz] if flags & 1 else b""
        return all(c < 0x80 for c in txt) and len(txt) > 0
    except Exception:
        return False

def load_manifest():
    if os.path.exists(MANIFEST):
        return json.load(open(MANIFEST))
    return {"actions": []}

def save_manifest(m):
    os.makedirs(BACKUP, exist_ok=True)
    json.dump(m, open(MANIFEST, "w"), ensure_ascii=False, indent=2)

def backup_rel(dst, manifest):
    """Back up the original dst once. Return the backup path or None."""
    if not os.path.exists(dst):
        return None
    # already backed up this dst?
    for a in manifest["actions"]:
        if a["dst"] == dst and a.get("backup"):
            return a["backup"]
    rel = os.path.relpath(dst, "/")
    bpath = os.path.join(BACKUP, "orig", rel)
    os.makedirs(os.path.dirname(bpath), exist_ok=True)
    shutil.copy2(dst, bpath)
    return bpath

def record_action(manifest, dst, backup, added):
    """Record an action, deduplicating by dst (a re-run does not pile up entries,
    the original backup is preserved)."""
    for a in manifest["actions"]:
        if a["dst"] == dst:
            if backup and not a.get("backup"):
                a["backup"] = backup; a["added"] = added
            return
    manifest["actions"].append({"dst": dst, "backup": backup, "added": added})

def install_file(src, dst, manifest, dry):
    log(f"  -> {dst}")
    if dry:
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    backup = backup_rel(dst, manifest)
    shutil.copy2(src, dst)
    record_action(manifest, dst, backup, backup is None)

def backup_path_for(dst):
    """Deterministic backup path for dst (mirror of backup_rel)."""
    return os.path.join(BACKUP, "orig", os.path.relpath(dst, "/"))

def remap_cp1251_cps(s):
    """Cyrillic -> U+00xx codepoints (= CP1251 bytes).

    The new EE UI draws campaign names/descriptions from repository.json with a
    bitmap font (256 glyphs, Cyrillic at positions 0..255). Real UTF-8 (U+04xx)
    shows up as '????'. We re-encode every non-ASCII char to its CP1251 byte and
    take chr(byte) - that codepoint lands on the Cyrillic glyph in both the bitmap
    and the TTF russifier fonts. json.dump(ensure_ascii=True) writes them as
    \\u00xx - valid ASCII JSON."""
    out = []
    for ch in s:
        if ord(ch) < 0x80:
            out.append(ch)
        else:
            try:
                out.append(chr(ch.encode("cp1251")[0]))
            except UnicodeEncodeError:
                out.append(ch)            # rare char outside CP1251 - keep as is
    return "".join(out)

def overlay_repo(english, ru, transform):
    """Overlay the Russian name/description by uuid onto the English structure."""
    out = copy.deepcopy(english)
    tr = lambda v: transform(v) if isinstance(v, str) else v
    for f in ("name", "description"):
        if f in ru: out[f] = tr(ru[f])
    for key in ("campaigns", "modules"):
        if isinstance(out.get(key), list) and isinstance(ru.get(key), list):
            by = {it.get("uuid"): it for it in ru[key] if isinstance(it, dict)}
            for it in out[key]:
                if isinstance(it, dict) and it.get("uuid") in by:
                    r = by[it["uuid"]]
                    for f in ("name", "description"):
                        if f in r: it[f] = tr(r[f])
    return out

def install_repository(cur_path, ru_path, manifest, mode, dry):
    """repository.json. mode: remap (encoding fix) | english (no translation) | utf8.
    The English structure comes from the pristine backup (to avoid re-encoding twice)."""
    bp = backup_path_for(cur_path)
    english_src = bp if os.path.exists(bp) else cur_path
    try:
        english = json.load(open(english_src, encoding="utf-8"))
    except Exception as e:
        log(f"  ! {cur_path} skipped ({e})"); return
    if mode == "english":
        out = english
    else:
        try:
            ru = json.load(open(ru_path, encoding="utf-8"))
        except Exception as e:
            log(f"  ! RU repository skipped ({e})"); return
        out = overlay_repo(english, ru, remap_cp1251_cps if mode == "remap" else (lambda s: s))
    log(f"  -> {cur_path} ({mode})")
    if dry: return
    os.makedirs(os.path.dirname(cur_path), exist_ok=True)
    backup = backup_rel(cur_path, manifest)
    with open(cur_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=True, indent=2)
    record_action(manifest, cur_path, backup, backup is None)

# ----------------------------------------------------------------- install ----
def do_install(args):
    game = args.game or find_game()
    if not game:
        sys.exit("ERROR: Neverwinter Nights: EE not found automatically.\n"
                 "Tried Steam (default + libraries), common GOG/Beamdog folders and Spotlight.\n"
                 "Point at the game folder explicitly, e.g.:\n"
                 '  python3 install_ru.py --game "/path/to/Neverwinter Nights"')
    payload = args.payload; patcher = os.path.join(payload, "patcher")
    user = None if args.no_user_dir else args.userdir
    dry = args.dry_run

    live_tlk = os.path.join(game, "lang/en/data/dialog.tlk")
    if not os.path.exists(live_tlk):
        sys.exit(f"ERROR: not a valid game folder (no {live_tlk}).\nCheck the --game path.")
    if not args.game:
        log(f"found game: {game}")
    if not os.path.isdir(patcher):
        sys.exit(f"ERROR: payload/patcher directory not found: {patcher}")

    manifest = load_manifest()
    os.makedirs(BACKUP, exist_ok=True)

    # 1) determine the PRISTINE English dialog.tlk to use as the build source
    en_backup = os.path.join(BACKUP, "english", "dialog.tlk")
    if tlk_strref1_is_english(live_tlk):
        os.makedirs(os.path.dirname(en_backup), exist_ok=True)
        if not dry: shutil.copy2(live_tlk, en_backup)
        english_source = en_backup
        log(f"[i] Live dialog.tlk is English - refreshed the reference: {en_backup}")
    elif os.path.exists(en_backup):
        english_source = en_backup
        log(f"[i] Live dialog.tlk is already russified - building from the reference: {en_backup}")
    else:
        sys.exit("ERROR: dialog.tlk is no longer English and there is no English "
                 "reference backup. Verify the game files in Steam and retry.")

    # 2) build the Russian dialog.tlk (or use our own prebuilt one)
    if args.no_build:
        if not os.path.exists(BUILT_TLK):
            sys.exit(f"ERROR: --no-build set but {BUILT_TLK} does not exist.\n"
                     f"Build it first: python3 context/assemble_tlk.py")
        log(f"[1/5] Using prebuilt dialog.tlk: {BUILT_TLK} (--no-build)")
    else:
        log("[1/5] Building the Russian dialog.tlk ...")
        if not dry:
            os.makedirs(os.path.dirname(BUILT_TLK), exist_ok=True)
            cmd = [sys.executable, os.path.join(HERE, "build_tlk.py"),
                   "--english-tlk", english_source, "--patcher", patcher,
                   "--out", BUILT_TLK, "--variant", args.variant]
            if not args.no_adv: cmd.append("--adv")
            if not args.no_fix_settings: cmd.append("--fix-settings")
            subprocess.run(cmd, check=True)

    # 3) install dialog.tlk
    log("[2/5] Installing dialog.tlk ...")
    install_file(BUILT_TLK, live_tlk, manifest, dry)

    # 4) fonts (Cyrillic) -> lang/en/data/ovr + user override
    log("[3/5] Fonts ...")
    font_src = os.path.join(payload, "lang/en/data/ovr")
    fonts = sorted(os.listdir(font_src)) if os.path.isdir(font_src) else []
    for fn in fonts:
        install_file(os.path.join(font_src, fn),
                     os.path.join(game, "lang/en/data/ovr", fn), manifest, dry)
    if user:
        for fn in fonts:   # mirror into Documents/override to guarantee loading
            install_file(os.path.join(font_src, fn),
                         os.path.join(user, "override", fn), manifest, dry)

    # 5) premade characters (.bic) -> data/lcv + localvault
    log("[4/5] Characters (.bic) ...")
    lcv_src = os.path.join(payload, "data/lcv")
    bics = sorted(f for f in os.listdir(lcv_src) if f.endswith(".bic")) if os.path.isdir(lcv_src) else []
    for fn in bics:
        install_file(os.path.join(lcv_src, fn),
                     os.path.join(game, "data/lcv", fn), manifest, dry)
    if user:
        for fn in bics:
            install_file(os.path.join(lcv_src, fn),
                         os.path.join(user, "localvault", fn), manifest, dry)

    # 6) repository.json (campaign names/descriptions)
    log(f"[5/5] repository.json (mode: {args.repo}) ...")
    for sub in ("mod", "nwm"):
        ru = os.path.join(payload, "data", sub, "repository.json")
        cur = os.path.join(game, "data", sub, "repository.json")
        if os.path.exists(ru) and os.path.exists(cur):
            install_repository(cur, ru, manifest, args.repo, dry)

    if not dry: save_manifest(manifest)
    log("\nDone." + ("  (dry-run, nothing written)" if dry else
        f"\nInstalled files: {len(manifest['actions'])}. "
        f"Uninstall: python3 install_ru.py --uninstall"))

# --------------------------------------------------------------- uninstall ----
def do_uninstall(args):
    if not os.path.exists(MANIFEST):
        sys.exit("No manifest.json - nothing to uninstall.")
    manifest = load_manifest()
    restored = removed = 0
    for a in reversed(manifest["actions"]):
        dst = a["dst"]
        if a.get("backup") and os.path.exists(a["backup"]):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(a["backup"], dst); restored += 1
        elif a.get("added"):
            if os.path.exists(dst): os.remove(dst); removed += 1
    log(f"Uninstall complete: restored {restored}, removed added {removed}.")
    log("(the reference English dialog.tlk and backups are kept under backup/)")

# -------------------------------------------------------------------- main ----
def main():
    ap = argparse.ArgumentParser(description="Install the NWN:EE russifier (macOS)")
    ap.add_argument("--game", default=None,
                    help="game folder; auto-detected if omitted (Steam libraries / GOG / Spotlight)")
    ap.add_argument("--payload", default=DEFAULT_PAYLOAD)
    ap.add_argument("--userdir", default=DEFAULT_USERDIR)
    ap.add_argument("--variant", choices=["main", "zog"], default="main")
    ap.add_argument("--no-build", action="store_true",
                    help="install the prebuilt build/dialog.tlk (e.g. our own "
                         "translation from context/assemble_tlk.py) instead of "
                         "building from the russifier patcher data")
    ap.add_argument("--no-adv", action="store_true", help="without advanced descriptions")
    ap.add_argument("--no-fix-settings", action="store_true")
    ap.add_argument("--repo", choices=["remap", "english", "utf8"], default="remap",
                    help="repository.json: remap=encoding fix (default), "
                         "english=keep campaign names in English, utf8=as-is (broken)")
    ap.add_argument("--no-user-dir", action="store_true",
                    help="do not touch ~/Documents/Neverwinter Nights")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--uninstall", action="store_true")
    args = ap.parse_args()
    (do_uninstall if args.uninstall else do_install)(args)

if __name__ == "__main__":
    main()
