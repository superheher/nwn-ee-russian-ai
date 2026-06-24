#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ncs.py - reader / string-patcher for compiled NWScript (NCS V1.0) bytecode.

Used to translate hard-coded display strings in scripts that CANNOT be recompiled
(their source #includes an unshipped library, e.g. Ossian's hf_in_*). Instead of
recompiling, we patch the string constants in the stock NCS in place and relocate
the byte offsets of jump instructions so the program stays valid.

NCS layout:
  header: "NCS V1.0" (8) + 0x42 (1) + uint32 BE total-size (4) = 13 bytes
  body:   instructions, each = opcode(1) + type(1) + operands(per-opcode)

The opcode table below is validated by round_trip(): parse -> re-emit must equal
the original bytes for every stock NCS. If a script fails round-trip we never
patch it (we'd risk corrupting it).
"""
import struct

MAGIC = b"NCS V1.0"
# operands AFTER the 2-byte (opcode,type) pair, by opcode. None = special (CONST).
_OPLEN = {
    0x01: 6,  # CPDOWNSP   int32 off, int16 size
    0x02: 0,  # RSADD
    0x03: 6,  # CPTOPSP
    0x04: None,  # CONST (type-dependent)
    0x05: 3,  # ACTION     int16 routine, int8 argc
    0x06: 0, 0x07: 0, 0x08: 0, 0x09: 0, 0x0A: 0,  # LOGAND..BOOLAND
    0x0B: None, 0x0C: None,  # EQUAL/NEQUAL (struct variant has int16 size)
    0x0D: 0, 0x0E: 0, 0x0F: 0, 0x10: 0,  # GEQ GT LT LEQ
    0x11: 0, 0x12: 0, 0x13: 0,  # SHLEFT SHRIGHT USHRIGHT
    0x14: 0, 0x15: 0, 0x16: 0, 0x17: 0, 0x18: 0, 0x19: 0, 0x1A: 0,  # ADD..COMP
    0x1B: 4,  # MOVSP      int32
    0x1C: 0,  # STORESTATEALL (no operand; rare)
    0x1D: 4,  # JMP        int32 rel
    0x1E: 4,  # JSR        int32 rel
    0x1F: 4,  # JZ         int32 rel
    0x20: 0,  # RETN
    0x21: 6,  # DESTRUCT   int16 size, int16 off, int16 size
    0x22: 0,  # NOT
    0x23: 4,  # DECISP     int32
    0x24: 4,  # INCISP     int32
    0x25: 4,  # JNZ        int32 rel
    0x26: 6,  # CPDOWNBP
    0x27: 6,  # CPTOPBP
    0x28: 4,  # DECIBP
    0x29: 4,  # INCIBP
    0x2A: 0,  # SAVEBP
    0x2B: 0,  # RESTOREBP
    0x2C: 8,  # STORESTATE int32 bp, int32 sp
    0x2D: 0,  # NOP
    0x42: 0,  # T (only appears in header; never in body)
}
JUMPS = {0x1D, 0x1E, 0x1F, 0x25}


def _instr_len(d, p):
    """Total length (incl. opcode+type) of the instruction at offset p, or None
    if the opcode/type is unknown (caller treats as un-parseable)."""
    op, t = d[p], d[p + 1]
    if op == 0x04:                                  # CONST
        if t == 0x05:                               # string: int16 len + bytes
            return 4 + struct.unpack_from(">H", d, p + 2)[0]
        return 2 + 4                                 # int/float/object/location/...: 4-byte operand
    if op in (0x0B, 0x0C):                          # EQUAL / NEQUAL
        return 2 + (2 if t == 0x24 else 0)          # struct compare carries int16 size
    n = _OPLEN.get(op)
    return None if n is None else 2 + n


def parse(d):
    """Walk the body. Returns (instrs, ok). instrs = list of dicts with offset 'o',
    length 'len', opcode 'op'. ok=False if we hit an unknown opcode (don't patch)."""
    assert d[:8] == MAGIC and d[8] == 0x42
    total = struct.unpack_from(">I", d, 9)[0]
    instrs = []
    p = 13
    n = len(d)
    while p < n:
        ln = _instr_len(d, p) if p + 1 < n else None
        if not ln or p + ln > n:
            return instrs, False
        instrs.append({"o": p, "len": ln, "op": d[p]})
        p += ln
    return instrs, (p == n and total == n)


def round_trip(d):
    """True if the file parses cleanly end-to-end and the size header matches."""
    instrs, ok = parse(d)
    return ok


def jumps_valid(d):
    """True if every jump operand lands exactly on an instruction boundary."""
    instrs, ok = parse(d)
    if not ok:
        return False
    bound = set(ins["o"] for ins in instrs)
    bound.add(len(d))
    for ins in instrs:
        if ins["op"] in JUMPS:
            rel = struct.unpack_from(">i", d, ins["o"] + 2)[0]
            if ins["o"] + rel not in bound:
                return False
    return True


def compared_strings(d):
    """Set of string-constant VALUES used as an operand of a STRING EQUAL/NEQUAL
    (translating them would break game logic). Precise: only EQUAL/NEQUAL with the
    string-comparison type byte 0x23 (EQUALSS); int compares (0x20) near a string
    assignment do NOT count. Looks back a few instructions for the string operand."""
    instrs, ok = parse(d)
    out = set()
    if not ok:
        return out
    for i, ins in enumerate(instrs):
        if ins["op"] in (0x0B, 0x0C) and d[ins["o"] + 1] == 0x23:   # string EQUAL/NEQUAL
            for j in range(max(0, i - 4), i):
                b = instrs[j]
                if b["op"] == 0x04 and d[b["o"] + 1] == 0x05:
                    sl = struct.unpack_from(">H", d, b["o"] + 2)[0]
                    out.add(d[b["o"] + 4:b["o"] + 4 + sl])
    return out


def strings(d):
    """List of (offset_of_string_bytes, length, bytes) for every CONST-string."""
    out = []
    instrs, ok = parse(d)
    if not ok:
        return out
    for ins in instrs:
        if ins["op"] == 0x04 and d[ins["o"] + 1] == 0x05:
            slen = struct.unpack_from(">H", d, ins["o"] + 2)[0]
            out.append((ins["o"] + 4, slen, d[ins["o"] + 4:ins["o"] + 4 + slen]))
    return out


def patch_strings(d, repl):
    """Return new NCS bytes with English string constants replaced. `repl` maps
    english-bytes -> russian-bytes. Relocates jump offsets that span length
    changes and fixes the header size. Returns (new_bytes, n_patched) or
    (None, 0) if the script can't be parsed (never patch a non-round-tripping file)."""
    instrs, ok = parse(d)
    if not ok:
        return None, 0

    # 1) decide edits: list of (str_bytes_offset, old_len, new_str_bytes)
    edits = []
    for ins in instrs:
        if ins["op"] == 0x04 and d[ins["o"] + 1] == 0x05:
            so = ins["o"] + 4
            slen = struct.unpack_from(">H", d, ins["o"] + 2)[0]
            old = d[so:so + slen]
            if old in repl and repl[old] != old:
                new = repl[old]
                if len(new) <= 0xFFFF:
                    edits.append((so, slen, new))
    if not edits:
        return bytes(d), 0

    # 2) cumulative byte delta at each original offset (sorted by offset)
    edits.sort()
    # delta_before(orig_off) = sum of (newlen-oldlen) for edits whose string starts < orig_off
    def new_offset(orig):
        delta = 0
        for so, slen, new in edits:
            if so + slen <= orig:                   # whole edited string lies before orig
                delta += len(new) - slen
            elif so < orig < so + slen:             # inside an edited string: clamp to its start (jumps never target mid-string)
                delta += 0
        return orig + delta

    # 3) rebuild body, fixing jump operands
    out = bytearray(d[:13])
    # map each instruction's old offset -> new offset
    # (build by emitting instructions in order, applying string edits)
    emap = {}
    cur = 13
    for ins in instrs:
        emap[ins["o"]] = cur
        seg = bytearray(d[ins["o"]:ins["o"] + ins["len"]])
        if ins["op"] == 0x04 and d[ins["o"] + 1] == 0x05:
            so = ins["o"] + 4
            slen = struct.unpack_from(">H", d, ins["o"] + 2)[0]
            old = d[so:so + slen]
            if old in repl and repl[old] != old and len(repl[old]) <= 0xFFFF:
                new = repl[old]
                seg = bytearray(d[ins["o"]:ins["o"] + 2]) + struct.pack(">H", len(new)) + new
        out += seg
        cur += len(seg)
    new_total = len(out)
    emap[len(d)] = new_total                         # jumps may target end-of-program

    # 4) relocate jumps: operand is int32 BE relative to the JUMP instruction's own offset
    n_patched = sum(1 for _ in edits)
    for ins in instrs:
        if ins["op"] in JUMPS:
            old_off = ins["o"]
            rel = struct.unpack_from(">i", d, old_off + 2)[0]
            old_target = old_off + rel
            new_src = emap[old_off]
            new_target = emap.get(old_target)
            if new_target is None:                  # target not an instruction boundary -> bail (safety)
                return None, 0
            struct.pack_into(">i", out, new_src + 2, new_target - new_src)

    struct.pack_into(">I", out, 9, new_total)
    # 5) verify: patched file walks cleanly AND every jump still lands on a boundary
    out = bytes(out)
    if not round_trip(out) or not jumps_valid(out):
        return None, 0
    return out, n_patched
