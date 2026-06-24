#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nss_apply.py - write translated display strings (CP1251) back into a module's
scripts, recompile ONLY the affected scripts, and inject the NCS into the
(GFF-translated) _ru module/hak. Companion to nss_prep.py.

Idempotent: always starts from the pristine English sources prep wrote (offsets
in index.json are valid only against those), copies them into a scratch build
dir, edits the copies, compiles from there (so #include'd files resolve to their
Russian versions too).

Steps:
  1. load index.json + translated/*.json (id -> ru). Report coverage.
  2. copy pristine English NSS (meta.nssdir) -> build dir; splice CP1251 Russian
     into every translated occurrence (inside the quotes only; concat literals
     mapped back from the {k} template). Descending offset order per file.
  3. include graph: affected = changed files + everything that #include's them
     (transitively). compile (nwnsc, no -o, matches stock) the affected scripts
     that have an entrypoint (void main / int StartingConditional).
  4. inject fresh NCS into the _ru target ERF(s); re-read to verify. --deploy
     copies the result over the module on the game mount (.orig backup must
     already exist; never touched).

  nss_apply.py --index dlc/<mod>_scripts/index.json
               --translated dlc/<mod>_scripts/translated
               --build tools/<mod>_build
               --map 'SRC_ARCHIVE_BASENAME => LOCAL_RU_FILE [=> MOUNT_DEPLOY_PATH]'
               [--map ...] [--deploy]
"""
import os, sys, re, json, glob, shutil, subprocess, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import erf, nss_lex, ncs

NSS, NCS = 2009, 2010
INSTALL = os.path.expanduser(
    "~/Library/Application Support/Steam/steamapps/common/Neverwinter Nights")
PLACEHOLDER = re.compile(r"\{\d+\}")


def load_ru(tdir):
    m = {}
    for p in sorted(glob.glob(os.path.join(tdir, "*.json"))):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception as ex:
            print(f"  ! skip {p}: {ex}"); continue
        for k, v in d.items():
            if str(k).lstrip("-").isdigit() and isinstance(v, str) and v.strip():
                m[str(k)] = v
    return m


def sanitize(ru):
    """Make a Russian string safe to splice into an NSS literal: no raw newlines
    (-> \\n escape), no bare double quotes (-> guillemets)."""
    ru = ru.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
    ru = ru.replace('"', "»")          # » ; opening « is cosmetic, closing here is safe
    return ru


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--translated", required=True)
    ap.add_argument("--build", required=True)
    ap.add_argument("--map", action="append", required=True,
                    help="'src_archive_basename => local_ru_file [=> mount_deploy_path]'")
    ap.add_argument("--install", default=INSTALL)
    ap.add_argument("--deploy", action="store_true")
    args = ap.parse_args()

    idx = json.load(open(args.index, encoding="utf-8"))
    id2en, id2occ = idx["id2en"], idx["id2occ"]
    archives = idx["meta"]["archives"]
    nssdir = idx["meta"]["nssdir"]
    ru = load_ru(args.translated)

    total = len(id2occ)
    have = sum(1 for i in id2occ if i in ru)
    if total == 0:
        print("no display strings in this module's scripts; nothing to do."); return
    print(f"coverage: {have}/{total} unique strings translated ({100*have/total:.1f}%)")
    miss = [i for i in id2occ if i not in ru]
    if miss:
        print(f"  {len(miss)} untranslated (stay English), e.g. {miss[:6]}")

    # ---- 2: build dir = pristine English + Russian splices --------------------
    if os.path.isdir(args.build):
        shutil.rmtree(args.build)
    shutil.copytree(nssdir, args.build)

    # per-file list of (start, end, ru_bytes) edits
    edits = {}
    skipped = 0
    for i, occs in id2occ.items():
        if i not in ru:
            continue
        for o in occs:
            f = o["f"]
            if o["k"] == "s":
                rub = sanitize(ru[i]).encode("cp1251", "replace")
                edits.setdefault(f, []).append((o["r"][0], o["r"][1], rub))
            else:                                   # concat: rebuild the whole expression
                codes = o["codes"]
                parts, okc = [], True
                for p in re.split(r"(\{\d+\})", ru[i]):
                    m = re.fullmatch(r"\{(\d+)\}", p)
                    if m:
                        k = int(m.group(1))
                        if k >= len(codes):
                            okc = False; break      # placeholder with no code piece
                        parts.append(codes[k])
                    elif p != "":
                        parts.append('"' + sanitize(p) + '"')
                if not okc or not parts:
                    skipped += 1; continue
                expr = " + ".join(parts).encode("cp1251", "replace")
                edits.setdefault(f, []).append((o["span"][0], o["span"][1], expr))
    if skipped:
        print(f"  ! {skipped} concat occurrences skipped (placeholder count mismatch)")

    changed = sorted(edits)
    nedit = overlap = 0
    for f in changed:
        clean, last = [], -1                        # drop overlapping spans (rare nested display)
        for a, b, rub in sorted(edits[f], key=lambda x: x[0]):
            if a < last:
                overlap += 1; continue
            clean.append((a, b, rub)); last = b
        p = os.path.join(args.build, f + ".nss")
        data = open(p, "rb").read()
        for a, b, rub in sorted(clean, key=lambda x: -x[0]):      # apply descending
            data = data[:a] + rub + data[b:]
        open(p, "wb").write(data); nedit += len(clean)
    print(f"spliced {nedit} edits into {len(changed)} scripts -> {args.build}"
          + (f"  ({overlap} overlapping skipped)" if overlap else ""))

    # ---- 3: include graph -> affected entrypoints -> compile ------------------
    srcs = {os.path.basename(p)[:-4]: open(p, "rb").read()
            for p in glob.glob(os.path.join(args.build, "*.nss"))}
    includers = {}
    for rr, data in srcs.items():
        for inc in nss_lex.includes(data):
            includers.setdefault(inc, set()).add(rr)
    affected, stack = set(), list(changed)
    while stack:
        x = stack.pop()
        if x in affected:
            continue
        affected.add(x)
        stack.extend(includers.get(x, ()))
    to_compile = sorted(rr for rr in affected
                        if rr in srcs and nss_lex.has_entrypoint(srcs[rr]))
    print(f"changed scripts: {len(changed)} | transitively affected: {len(affected)} | "
          f"to compile (entrypoints): {len(to_compile)}")

    outdir = os.path.join(args.build, "_ncs")
    if os.path.isdir(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir)
    nwnsc = os.path.join(HERE, "..", "tools", "nwnsc")
    build_abs, out_abs = os.path.abspath(args.build), os.path.abspath(outdir)

    def compile_batch(names, stock_compat):
        # cwd=build so -b writes flat basenames. No -o (matches stock/pilot NCS).
        c = [nwnsc, "-n", args.install, "-i", build_abs, "-q", "-y", "-b", out_abs]
        if stock_compat:
            c.append("-s")                          # tolerate BioWare warts (base-include proto mismatch)
        c += [rr + ".nss" for rr in names]
        r = subprocess.run(c, cwd=args.build, capture_output=True, text=True)
        return [l for l in (r.stdout + r.stderr).splitlines()
                if re.search(r"\berror\b", l, re.I) and "0 error" not in l.lower()]

    def made():
        return {os.path.basename(p)[:-4]: p for p in glob.glob(os.path.join(outdir, "*.ncs"))}

    errs = compile_batch(to_compile, False)         # pass 1: strict (matches proven pilot output)
    produced = made()
    fail1 = [rr for rr in to_compile if rr not in produced]
    rescued = []
    if fail1:                                       # pass 2: -s only for strict-failures
        compile_batch(fail1, True)
        produced = made()
        rescued = [rr for rr in fail1 if rr in produced]
    failed = [rr for rr in to_compile if rr not in produced]
    print(f"compiled {len(produced)}/{len(to_compile)} NCS"
          + (f"  | -s rescued {len(rescued)}" if rescued else "")
          + (f"  | FAILED: {failed[:10]}" if failed else ""))
    for l in errs[:6]:
        print("   nwnsc:", l)
    if failed:
        print("  ! failed scripts keep their stock (English) NCS - not injected")

    # piece map (english bytes -> russian bytes) for direct NCS byte-patching of
    # scripts that could NOT be recompiled (e.g. #include an unshipped hf_in_* lib).
    pmap = {}
    for i, e in id2en.items():
        if i not in ru:
            continue
        eps = PLACEHOLDER.split(e); rps = PLACEHOLDER.split(ru[i])
        if len(eps) != len(rps):
            continue
        for ep, rp in zip(eps, rps):
            if ep.strip() and ep != rp:
                pmap[ep.encode("latin-1", "replace")] = rp.encode("cp1251", "replace")

    # ---- 4: inject NCS into the _ru target(s) + optional deploy ---------------
    targets = []
    for m in args.map:
        parts = [s.strip() for s in m.split("=>")]
        src_arch, ru_file = parts[0], parts[1]
        deploy = parts[2] if len(parts) > 2 else None
        targets.append((src_arch, ru_file, deploy))

    for src_arch, ru_file, deploy in targets:
        # resrefs that came from this archive and were successfully compiled
        want = {rr: produced[rr] for rr in produced
                if archives.get(rr, "").lower() == src_arch.lower()}
        arch_set = {rr for rr in archives if archives[rr].lower() == src_arch.lower()}
        e = erf.read_erf(open(ru_file, "rb").read())
        n = npatch = npstr = 0
        for res in e["resources"]:
            if res["restype"] != NCS:
                continue
            rr = res["resref"].lower()
            if rr in want:                          # recompiled (proven) NCS wins
                res["data"] = open(want[rr], "rb").read(); n += 1
            elif rr in arch_set:                    # couldn't recompile -> byte-patch stock NCS
                new, k = ncs.patch_strings(res["data"], pmap)
                if new is not None and k:
                    res["data"] = new; npatch += 1; npstr += k
        stem, ext = os.path.splitext(ru_file)
        out = stem + "_scr" + ext
        open(out, "wb").write(erf.write_erf(e))
        erf.read_erf(open(out, "rb").read())        # verify re-read
        print(f"[{src_arch}] injected {n} recompiled NCS + byte-patched {npatch} ({npstr} strings) "
              f"-> {os.path.relpath(out, HERE)} ({os.path.getsize(out):,} b); re-read OK")
        if args.deploy and deploy:
            if not os.path.exists(deploy):
                print(f"  ! mount target missing: {deploy}"); continue
            if not os.path.exists(deploy + ".orig"):
                shutil.copy2(deploy, deploy + ".orig"); print("  backed up -> .orig")
            shutil.copy2(out, deploy)
            print(f"  deployed -> {deploy}")


if __name__ == "__main__":
    main()
