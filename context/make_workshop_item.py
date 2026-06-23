#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_workshop_item.py - assemble a Steam Workshop item directory for our own
Russian translation of NWN:EE, ready for the in-game `WorkshopUpload <path>`.

Layout mirrors a known-good NWN:EE translation Workshop item: the base
dialog.tlk and the Cyrillic fonts are placed in BOTH override/ (= user
Documents/.../override) and ovr/ (= game lang/en/data/ovr) so the game loads
them whichever search path it uses. A root thumbnail.png is the Workshop
preview (Steam caps it at 1 MB; we downscale to 512x512 via macOS `sips`).

Experimental: --with-repo also drops our translated, remapped repository.json
under data/mod and data/nwm (campaign/module selection screen). Not present in
the reference item, so treat as unproven until tested in-game.

  make_workshop_item.py --thumbnail IMG [--with-repo] [--out DIR]
"""
import argparse, json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROOT = os.path.dirname(HERE)
sys.path.insert(0, PROOT)
import install_ru  # reuse the verified remap + overlay logic (no side effects on import)

DEFAULT_GAME = os.path.expanduser(
    "~/Library/Application Support/Steam/steamapps/common/Neverwinter Nights")


def remapped_repo(sub, game, payload):
    """English structure (pristine backup) + our RU overlay (payload), remapped
    to U+00xx so the bitmap UI font renders Cyrillic - same as install_ru."""
    cur = os.path.join(game, "data", sub, "repository.json")
    bp = install_ru.backup_path_for(cur)
    english = json.load(open(bp if os.path.exists(bp) else cur, encoding="utf-8"))
    ru = json.load(open(os.path.join(payload, "data", sub, "repository.json"),
                       encoding="utf-8"))
    return install_ru.overlay_repo(english, ru, install_ru.remap_cp1251_cps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(PROOT, "build", "workshop", "nwn_ru_own"))
    ap.add_argument("--thumbnail")
    ap.add_argument("--game", default=DEFAULT_GAME)
    ap.add_argument("--tlk", default=os.path.join(PROOT, "build", "dialog.tlk"))
    ap.add_argument("--fonts", default=os.path.join(PROOT, "payload", "lang", "en", "data", "ovr"))
    ap.add_argument("--payload", default=os.path.join(PROOT, "payload"))
    ap.add_argument("--with-repo", action="store_true",
                    help="include experimental data/{mod,nwm}/repository.json")
    ap.add_argument("--tags", default="override",
                    help="comma-separated Workshop category tags -> tags.txt, one per line. "
                         "NWN:EE predefined tags ONLY: module tileset hak compilation "
                         "persistentworld override singleplayer multiplayer music sound "
                         "voices textures models portraits script")
    args = ap.parse_args()

    if os.path.exists(args.out):
        shutil.rmtree(args.out)
    os.makedirs(args.out)

    fonts = sorted(f for f in os.listdir(args.fonts) if not f.startswith("."))
    for d in ("override", "ovr"):
        dd = os.path.join(args.out, d)
        os.makedirs(dd)
        shutil.copy2(args.tlk, os.path.join(dd, "dialog.tlk"))
        for f in fonts:
            shutil.copy2(os.path.join(args.fonts, f), os.path.join(dd, f))
        print(f"  {d}/: dialog.tlk + {len(fonts)} fonts")

    if args.with_repo:
        for sub in ("mod", "nwm"):
            d = os.path.join(args.out, "data", sub)
            os.makedirs(d)
            data = remapped_repo(sub, args.game, args.payload)
            json.dump(data, open(os.path.join(d, "repository.json"), "w", encoding="utf-8"),
                      ensure_ascii=True, indent=2)
            print(f"  data/{sub}/repository.json (remapped, experimental)")

    if args.thumbnail:
        thumb = os.path.join(args.out, "thumbnail.png")
        subprocess.run(["sips", "-Z", "512", "-s", "format", "png",
                        args.thumbnail, "--out", thumb], check=True, capture_output=True)
        print(f"  thumbnail.png (<=512x512)")

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    if tags:
        with open(os.path.join(args.out, "tags.txt"), "w") as f:
            f.write("\n".join(tags) + "\n")
        print(f"  tags.txt: {', '.join(tags)}")

    # total size
    total = sum(os.path.getsize(os.path.join(r, f))
                for r, _, fs in os.walk(args.out) for f in fs)
    print(f"\nWorkshop item ready: {args.out}\n  total size: {total/1e6:.1f} MB")
    print(f"  upload in-game: WorkshopUpload {args.out}")


if __name__ == "__main__":
    main()
