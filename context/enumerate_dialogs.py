#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enumerate_dialogs.py - reconstruct every conversation in the game.

Sources:
  base_dialog.bif   - generic / system conversations (indexed by nwn_base.key)
  data/nwm/*.nwm    - campaign modules (ERF archives) holding their own .dlg

For each .dlg it reconstructs the readable conversation tree (context) and the
set of unique translatable lines (StrRef, role, English). Output:

  context/dialogs/<source>.json   per-source bundle for the translation workflow
      {source, conversations:[{resref, n_lines, script, lines:[{strref,role,en}]}]}
  context/dialog_index.json       global index + the full set of dialog StrRefs
"""
import os, sys, json, struct, glob
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nwn

DLG = 2029
SCRIPT_MAX = 500   # cap on the reconstructed context tree (unique lines are always complete)


def load_bif_index(path):
    b = open(path, "rb").read()
    assert b[:8] == b"BIFFV1  ", b[:8]
    var_count, _, var_off = struct.unpack_from("<III", b, 8)
    idx, o = {}, var_off
    for _ in range(var_count):
        rid, roff, rsize, _ = struct.unpack_from("<IIII", b, o)
        idx[rid & 0xFFFFF] = (roff, rsize)
        o += 16
    return b, idx


def erf_list_dlg(path):
    """Yield (resref, blob) for every .dlg in an ERF (MOD V1.0)."""
    e = open(path, "rb").read()
    (_, _, entry_count, _, off_keys, off_res) = struct.unpack_from("<IIIIII", e, 8)
    ko, ro = off_keys, off_res
    out = []
    for _ in range(entry_count):
        rr = e[ko:ko + 16].split(b"\x00")[0].decode("ascii", "replace").lower()
        _, rtype, _ = struct.unpack_from("<IHH", e, ko + 16)
        if rtype == DLG:
            roff, rsize = struct.unpack_from("<II", e, ro)
            out.append((rr, e[roff:roff + rsize]))
        ko += 24
        ro += 8
    return out


def unique_lines(entries, replies, tlk):
    seen, items = set(), []
    for role, arr in (("NPC", entries), ("PC", replies)):
        for n in arr:
            t = n.get("Text", {})
            sr = t.get("strref", -1) if isinstance(t, dict) else -1
            if sr is None or sr < 0 or sr in seen:
                continue
            en = tlk(sr)
            if not en:
                continue
            seen.add(sr)
            items.append({"strref": sr, "role": role, "en": en})
    items.sort(key=lambda x: x["strref"])
    return items


def process(source, dlg_iter, tlk):
    """dlg_iter yields (resref, blob). Returns (bundle, strref_set, fails)."""
    convos, all_sr, fails = [], set(), []
    for resref, blob in dlg_iter:
        try:
            entries, replies, lines = nwn.reconstruct(blob, tlk, max_lines=SCRIPT_MAX)
        except Exception as ex:                       # malformed / non-GFF
            fails.append((resref, str(ex)[:60]))
            continue
        items = unique_lines(entries, replies, tlk)
        if not items:
            continue
        for it in items:
            all_sr.add(it["strref"])
        convos.append({
            "resref": resref,
            "n_entries": len(entries), "n_replies": len(replies),
            "n_unique": len(items),
            "script": "\n".join(lines),
            "lines": items,
        })
    convos.sort(key=lambda c: c["resref"])
    return {"source": source, "n_conversations": len(convos),
            "conversations": convos}, all_sr, fails


def main():
    game = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.expanduser("~/Library/Application Support/Steam/steamapps/"
                           "common/Neverwinter Nights")
    tlk = nwn.load_tlk(os.path.join(HERE, "..", "backup", "english", "dialog.tlk"))
    outdir = os.path.join(HERE, "dialogs")
    os.makedirs(outdir, exist_ok=True)

    index = {"sources": [], "totals": {}}
    global_sr = set()
    all_fails = []

    # 1) base_dialog.bif via KEY
    bifs, res = nwn.parse_key(os.path.join(game, "data", "nwn_base.key"))
    base_idx = next(i for i, p in enumerate(bifs) if p.endswith("base_dialog.bif"))
    bdata, bmap = load_bif_index(os.path.join(game, bifs[base_idx]))
    def base_iter():
        for (rr, rt), (bi, ri) in sorted(res.items()):
            if rt == DLG and bi == base_idx and ri in bmap:
                off, size = bmap[ri]
                yield rr, bdata[off:off + size]
    bundle, sr, fails = process("base_dialog", base_iter(), tlk)
    json.dump(bundle, open(os.path.join(outdir, "base_dialog.json"), "w"),
              ensure_ascii=False, indent=1)
    global_sr |= sr; all_fails += [("base_dialog", *f) for f in fails]
    index["sources"].append({"source": "base_dialog",
                             "n_conversations": bundle["n_conversations"],
                             "n_unique_strref": len(sr)})
    print(f"base_dialog: convos={bundle['n_conversations']:<5} strrefs={len(sr):<6} fails={len(fails)}")

    # 2) every .nwm module
    for nwm in sorted(glob.glob(os.path.join(game, "data", "nwm", "*.nwm"))):
        name = os.path.splitext(os.path.basename(nwm))[0]
        safe = name.replace(" ", "_")
        bundle, sr, fails = process(name, erf_list_dlg(nwm), tlk)
        json.dump(bundle, open(os.path.join(outdir, f"{safe}.json"), "w"),
                  ensure_ascii=False, indent=1)
        global_sr |= sr; all_fails += [(name, *f) for f in fails]
        index["sources"].append({"source": name, "file": f"{safe}.json",
                                 "n_conversations": bundle["n_conversations"],
                                 "n_unique_strref": len(sr)})
        print(f"{name:<22} convos={bundle['n_conversations']:<5} strrefs={len(sr):<6} fails={len(fails)}")

    index["totals"] = {
        "sources": len(index["sources"]),
        "conversations": sum(s["n_conversations"] for s in index["sources"]),
        "unique_dialog_strrefs": len(global_sr),
        "parse_failures": len(all_fails),
    }
    index["all_dialog_strref"] = sorted(global_sr)
    json.dump(index, open(os.path.join(HERE, "dialog_index.json"), "w"),
              ensure_ascii=False, indent=1)

    t = index["totals"]
    print(f"\nTOTAL: sources={t['sources']} conversations={t['conversations']} "
          f"unique dialog StrRefs={t['unique_dialog_strrefs']} fails={t['parse_failures']}")
    if all_fails:
        print("parse failures (first 10):")
        for f in all_fails[:10]:
            print("  ", f)


if __name__ == "__main__":
    main()
