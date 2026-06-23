#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_ddf_workshop.py - assemble a Steam Workshop item that delivers our Russian
translation of the premium module "Dark Dreams of Furiae".

Why this differs from the base-game translation item: the base text lives in the
shared dialog.tlk, which the user override/ folder can replace. A premium campaign
stores its text as embedded LocStrings INSIDE the module's own GFF resources, and
override/ sits BELOW the loaded module in resman priority (12M < module 20M), so it
cannot reach inside the .nwm. The development/ folder sits ABOVE the module
(priority 71M) and DOES override module-internal resources - proven in-game, and
proven to mount the same way from a Workshop item's development/ subfolder
(engine log: KeyTable DEVELOPMENT ID 71000000).

Layout produced:
  <item>/
    thumbnail.png      Workshop preview (<=1 MB, square 512x512 via macOS sips)
    tags.txt           category tag(s), one per line
    development/        the translated module resources (the priority-71M override)
    override/ + ovr/    Cyrillic fonts, so the CP1251 text renders for a subscriber
                        who does not also have the base-translation item

  make_ddf_workshop.py [--out DIR] [--resources DIR] [--fonts DIR] [--thumbnail IMG] [--tags T]
"""
import argparse, os, shutil, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
PROOT = os.path.dirname(HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(PROOT, "build", "workshop", "DDF_Russian_Translation"))
    ap.add_argument("--resources", default=os.path.join(PROOT, "ddf", "override"),
                    help="translated module resources (loose GFF files) -> development/")
    ap.add_argument("--fonts", default=os.path.join(PROOT, "payload", "lang", "en", "data", "ovr"),
                    help="Cyrillic fonts -> override/ and ovr/")
    ap.add_argument("--thumbnail")
    ap.add_argument("--tags", default="override",
                    help="comma-separated Workshop tags (15 allowed: module tileset hak "
                         "compilation persistentworld override singleplayer multiplayer "
                         "music sound voices textures models portraits script)")
    args = ap.parse_args()

    if os.path.exists(args.out):
        shutil.rmtree(args.out)
    os.makedirs(args.out)

    # development/: translated module resources, mounted at 71M (above the module)
    dev = os.path.join(args.out, "development")
    os.makedirs(dev)
    res = sorted(f for f in os.listdir(args.resources) if not f.startswith("."))
    for f in res:
        shutil.copy2(os.path.join(args.resources, f), os.path.join(dev, f))
    print(f"  development/: {len(res)} translated resources")

    # override/ + ovr/: Cyrillic fonts so the text renders standalone
    fonts = sorted(f for f in os.listdir(args.fonts) if not f.startswith("."))
    for d in ("override", "ovr"):
        dd = os.path.join(args.out, d)
        os.makedirs(dd)
        for f in fonts:
            shutil.copy2(os.path.join(args.fonts, f), os.path.join(dd, f))
        print(f"  {d}/: {len(fonts)} fonts")

    if args.thumbnail:
        thumb = os.path.join(args.out, "thumbnail.png")
        subprocess.run(["sips", "-Z", "512", "-s", "format", "png",
                        args.thumbnail, "--out", thumb], check=True, capture_output=True)
        print("  thumbnail.png (<=512x512)")

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    if tags:
        with open(os.path.join(args.out, "tags.txt"), "w") as f:
            f.write("\n".join(tags) + "\n")
        print(f"  tags.txt: {', '.join(tags)}")

    total = sum(os.path.getsize(os.path.join(r, f))
                for r, _, fs in os.walk(args.out) for f in fs)
    print(f"\nWorkshop item ready: {args.out}\n  total size: {total/1e6:.1f} MB")
    print(f"  upload in-game (raw path, no quotes): WorkshopUpload {args.out}")


if __name__ == "__main__":
    main()
