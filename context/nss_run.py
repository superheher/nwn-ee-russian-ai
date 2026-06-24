#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nss_run.py - drive nss_prep / nss_apply over every premium module from one table
(context/nss_modules.json). Scripts live only in the .nwm/.mod (content haks have
none), so each module is a single-archive job.

  nss_run.py prep  [mod|all]            # extract display strings -> dlc/<mod>_scripts
  nss_run.py apply [mod|all] [--deploy] # splice RU, recompile, inject (+deploy)
  nss_run.py stat  [mod|all]            # unique display-string count per module
"""
import os, sys, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CFG = json.load(open(os.path.join(HERE, "nss_modules.json"), encoding="utf-8"))


def outdirs(mod):
    return (os.path.join(ROOT, "dlc", mod + "_scripts"),
            os.path.join(ROOT, "tools", mod + "_src"),
            os.path.join(ROOT, "tools", mod + "_build"))


def prep(mod):
    c = CFG[mod]; out, nssdir, _ = outdirs(mod)
    subprocess.run([sys.executable, os.path.join(HERE, "nss_prep.py"),
                    "--erf", c["src"], "--out", out, "--nssdir", nssdir], check=True)


def apply(mod, deploy):
    c = CFG[mod]; out, _, build = outdirs(mod)
    arch = os.path.basename(c["src"])
    mp = f'{arch} => {os.path.join(ROOT, c["ru"])} => {c["deploy"]}'
    cmd = [sys.executable, os.path.join(HERE, "nss_apply.py"),
           "--index", os.path.join(out, "index.json"),
           "--translated", os.path.join(out, "translated"),
           "--build", build, "--map", mp]
    if deploy:
        cmd.append("--deploy")
    subprocess.run(cmd, check=True)


def stat(mod):
    out, _, _ = outdirs(mod)
    p = os.path.join(out, "index.json")
    if not os.path.exists(p):
        print(f"{mod:12} (not prepped)"); return 0
    idx = json.load(open(p, encoding="utf-8"))
    n = len(idx["id2en"]); occ = sum(len(v) for v in idx["id2occ"].values())
    conc = sum(1 for v in idx["id2occ"].values() for o in v if o["k"] == "c")
    print(f"{mod:12} unique={n:5}  occ={occ:5}  concat={conc:4}")
    return n


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stat"
    sel = sys.argv[2] if len(sys.argv) > 2 else "all"
    deploy = "--deploy" in sys.argv
    mods = list(CFG) if sel == "all" else [sel]
    total = 0
    for m in mods:
        if cmd == "prep":
            print(f"\n=== prep {m} ===");  prep(m)
        elif cmd == "apply":
            print(f"\n=== apply {m} ==="); apply(m, deploy)
        elif cmd == "stat":
            total += stat(m)
    if cmd == "stat" and sel == "all":
        print(f"{'TOTAL':12} unique={total}")


if __name__ == "__main__":
    main()
