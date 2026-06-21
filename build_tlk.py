#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_tlk.py - native, cross-platform build of the Russian dialog.tlk
for Neverwinter Nights: Enhanced Edition.

Reproduces what Parser_tlk.exe does on Windows in the "Neverwinter Nights:
EE/Classic" russifier (ZoG / Lord_Draconis / DragonZH), EE chain:

    PatchingEE_main.bat       : inject dialog.tlk_RU.txt (-al -txt), then Patch_dialog_EE.csv
    PatchingEE_mod_ADV.bat    : 5 advanced-description CSVs (classes/feat/skills/spells/races)
    PatchingEE_FixSettings.bat: RemoveTextSettings.csv with offset -1 (-plus -1)

The TLK V3.0 format and the escape rules (\\n, \\t, \\r, \\\\, \\", \\xHH)
were verified against the real game and russifier data.
"""
import argparse, csv, io, os, struct, sys

# ---------------------------------------------------------------- TLK V3.0 ----
HEADER = b"TLK V3.0"
REC = 40  # size of one string-table record

class Tlk:
    """Parsed dialog.tlk: language + list of entries (metadata + CP1251 text bytes)."""
    __slots__ = ("language", "entries")
    def __init__(self, language, entries):
        self.language = language
        self.entries = entries  # list of dict(flags,sound,volvar,pitchvar,sndlen,text)

def parse_tlk(path):
    data = open(path, "rb").read()
    if data[:8] != HEADER:
        raise ValueError(f"{path}: not a TLK V3.0 file (sig={data[:8]!r})")
    language    = struct.unpack_from("<I", data, 8)[0]
    count       = struct.unpack_from("<I", data, 12)[0]
    entries_off = struct.unpack_from("<I", data, 16)[0]
    entries = []
    for i in range(count):
        base = 20 + i * REC
        flags    = struct.unpack_from("<I", data, base)[0]
        sound    = data[base+4:base+20]                      # char[16] ResRef
        volvar   = struct.unpack_from("<I", data, base+20)[0]
        pitchvar = struct.unpack_from("<I", data, base+24)[0]
        off      = struct.unpack_from("<I", data, base+28)[0]
        size     = struct.unpack_from("<I", data, base+32)[0]
        sndlen   = struct.unpack_from("<f", data, base+36)[0]
        if flags & 0x1:           # TEXT_PRESENT
            s = entries_off + off
            text = data[s:s+size]
        else:
            text = b""
        entries.append(dict(flags=flags, sound=sound, volvar=volvar,
                            pitchvar=pitchvar, sndlen=sndlen, text=text))
    return Tlk(language, entries)

def write_tlk(tlk, path):
    count = len(tlk.entries)
    entries_off = 20 + count * REC
    table = bytearray()
    blob  = bytearray()
    for e in tlk.entries:
        flags = e["flags"]
        if e["text"]:
            flags |= 0x1                      # text present
            off = len(blob); size = len(e["text"])
            blob += e["text"]
        elif flags & 0x1:                     # TEXT_PRESENT but empty text
            off = len(blob); size = 0
        else:
            off = 0; size = 0
        sound = (e["sound"] + b"\x00"*16)[:16]
        table += struct.pack("<I16sIIIIf", flags, sound, e["volvar"],
                            e["pitchvar"], off, size, e["sndlen"])
    out = bytearray()
    out += HEADER
    out += struct.pack("<III", tlk.language, count, entries_off)
    out += table
    out += blob
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(out)
    os.replace(tmp, path)

# ------------------------------------------------------------- unescape ----
def unescape(b: bytes) -> bytes:
    """Expand Parser_tlk.exe escape sequences at the CP1251 byte level."""
    out = bytearray(); i = 0; n = len(b)
    simple = {0x6E:0x0A, 0x74:0x09, 0x72:0x0D, 0x5C:0x5C, 0x22:0x22}  # n t r \\ "
    while i < n:
        c = b[i]
        if c == 0x5C and i+1 < n:
            nxt = b[i+1]
            if nxt in simple:
                out.append(simple[nxt]); i += 2; continue
            if nxt == 0x78 and i+3 < n:        # \xHH
                hx = b[i+2:i+4]
                try:
                    out.append(int(hx.decode("ascii"), 16)); i += 4; continue
                except ValueError:
                    pass
            out.append(c); i += 1; continue     # unknown escape - keep the backslash
        out.append(c); i += 1
    return bytes(out)

# ------------------------------------------------------------- operations ----
def inject_txt(tlk, txt_path, log):
    """-al -txt: line i (0-based) -> StrRef i. The full text translation."""
    raw = open(txt_path, "rb").read()
    lines = raw.split(b"\r\n")
    if lines and lines[-1] == b"":
        lines.pop()                            # trailing CRLF
    n = len(lines)
    blanked_over_en = 0
    applied = 0
    for i, line in enumerate(lines):
        if i >= len(tlk.entries):
            break
        e = tlk.entries[i]
        new = unescape(line)
        if not new and (e["flags"] & 0x1) and e["text"]:
            blanked_over_en += 1
        e["text"] = new
        e["flags"] |= 0x1
        applied += 1
    log(f"  inject {os.path.basename(txt_path)}: lines={n}, applied={applied}, "
        f"blanked-over-EN={blanked_over_en}")

def patch_csv(tlk, csv_path, delimiter, strref_offset, log):
    """CSV patch. comma: \"strref\",\"snd\",\"text\".  semicolon: \"strref\";\"text\"."""
    raw = open(csv_path, "rb").read().decode("latin-1")  # 1 byte = 1 char
    rdr = csv.reader(io.StringIO(raw), delimiter=delimiter, quotechar='"', doublequote=True)
    applied = skipped = 0
    for row in rdr:
        if not row or not row[0].strip():
            continue
        try:
            ref = int(row[0].strip()) + strref_offset
        except ValueError:
            continue
        text_field = row[-1]                   # text is always the last field
        if ref < 0 or ref >= len(tlk.entries):
            skipped += 1; continue
        tlk.entries[ref]["text"] = unescape(text_field.encode("latin-1"))
        tlk.entries[ref]["flags"] |= 0x1
        applied += 1
    log(f"  patch  {os.path.basename(csv_path)}: applied={applied}, out-of-range={skipped}")

# ------------------------------------------------------------- main ----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--english-tlk", required=True, help="source English dialog.tlk from the game")
    ap.add_argument("--patcher", required=True, help="the russifier's patcher/ directory")
    ap.add_argument("--out", required=True, help="where to write the Russian dialog.tlk")
    ap.add_argument("--variant", choices=["main", "zog"], default="main")
    ap.add_argument("--adv", action="store_true", help="advanced descriptions (mod_ADV)")
    ap.add_argument("--fix-settings", action="store_true", help="revert settings strings to EN (-1)")
    args = ap.parse_args()

    def log(m): print(m)

    P = args.patcher
    log(f"Reading English TLK: {args.english_tlk}")
    tlk = parse_tlk(args.english_tlk)
    log(f"  language={tlk.language}, entries={len(tlk.entries)}")

    # 1) main translation
    main_txt = "dialog.tlk_RU.txt" if args.variant == "main" else "zog_wmg_dialog1.69.tlk.txt"
    log(f"[1] Main translation ({args.variant}):")
    inject_txt(tlk, os.path.join(P, main_txt), log)
    log("[2] EE patch:")
    patch_csv(tlk, os.path.join(P, "Patch_dialog_EE.csv"), ",", 0, log)

    # 2) advanced descriptions
    if args.adv:
        log("[3] Advanced descriptions (mod_ADV):")
        for c in ["classes_DESC_ADV.csv", "feat_DESC_ADV_D.csv", "skills_DESC_ADV.csv",
                  "spells_DESC_ADV_D.csv", "races_DESC_ADV.csv"]:
            patch_csv(tlk, os.path.join(P, c), ",", 0, log)

    # 3) settings fix (UI strings -> EN, StrRef-1)
    if args.fix_settings:
        log("[4] FixSettings (RemoveTextSettings.csv, offset -1):")
        patch_csv(tlk, os.path.join(P, "RemoveTextSettings.csv"), ";", -1, log)

    write_tlk(tlk, args.out)
    sz = os.path.getsize(args.out)
    log(f"\nDone: {args.out} ({sz:,} bytes)")

if __name__ == "__main__":
    main()
