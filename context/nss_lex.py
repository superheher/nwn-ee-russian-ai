#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nss_lex.py - a small NWScript (NSS) lexer + display-string extractor.

Shared by nss_prep.py (extract translatable display strings) and nss_apply.py
(write Russian back + recompile). NSS is C-like; the ONLY safe way to find which
string literals are shown to the player (vs. tags / variable keys / resrefs used
in logic) is to tokenize properly: comments are everywhere (lots of commented-out
SpeakString(...) calls) so a naive grep is wrong.

We translate ONLY string literals that are:
  * arguments in known DISPLAY function slots (SpeakString, SetCustomToken, ...),
  * or right-hand sides of cutscene "string sLine.../sText... = ..." assignments
    (natural-language filtered).
Everything else (comparisons, GetLocalString keys, GetObjectByTag tags, resrefs,
debug PrintString/log) is left untouched -> game logic cannot break.

Offsets are byte offsets (source decoded latin-1 == 1 byte/char), so callers can
splice CP1251 Russian straight into the original bytes.
"""
import re

# display function -> which argument index (0-based) holds player-visible text
DISPLAY_SLOTS = {
    "SpeakString": (0,),
    "ActionSpeakString": (0,),
    "SetCustomToken": (1,),
    "SendMessageToPC": (1,),
    "SendMessageToAllDMs": (0,),
    "FloatingTextStringOnCreature": (0,),
    "PostString": (1,),
}

# cutscene / dialogue string variables whose literal value is spoken/shown
_CUT_VAR = re.compile(r"(?i)(line|text|speak|say|talk|bark|msg|message|reply|"
                      r"dialog|banter|greet|rumor|phrase|words|quote|bubble|"
                      r"taunt|comment|remark|shout|whisper|cry|yell)")


def tokenize(src_bytes):
    """Return list of tokens (kind, text, start, end). kind in
    {'id','str','num','punct'}; comments/whitespace dropped. For 'str', text is
    the INNER content and (start,end) span the inner content (between quotes)."""
    s = src_bytes.decode("latin-1")
    i, n = 0, len(s)
    toks = []
    while i < n:
        c = s[i]
        if c in " \t\r\n":
            i += 1; continue
        if c == "/" and i + 1 < n and s[i + 1] == "/":
            j = s.find("\n", i); i = n if j < 0 else j + 1; continue
        if c == "/" and i + 1 < n and s[i + 1] == "*":
            j = s.find("*/", i + 2); i = n if j < 0 else j + 2; continue
        if c == '"':
            j = i + 1
            while j < n:
                if s[j] == "\\" and j + 1 < n:
                    j += 2; continue
                if s[j] == '"':
                    break
                j += 1
            toks.append(("str", s[i + 1:j], i + 1, j))
            i = j + 1; continue
        if c.isalpha() or c == "_":
            j = i + 1
            while j < n and (s[j].isalnum() or s[j] == "_"):
                j += 1
            toks.append(("id", s[i:j], i, j)); i = j; continue
        if c.isdigit() or (c == "." and i + 1 < n and s[i + 1].isdigit()):
            j = i + 1
            while j < n and (s[j].isalnum() or s[j] in "._"):
                j += 1
            toks.append(("num", s[i:j], i, j)); i = j; continue
        toks.append(("punct", c, i, i + 1)); i += 1
    return toks


def ends_in_block_comment(src_bytes):
    """True if EOF is reached inside an unterminated /* block comment (the BioWare
    'commented-out test main()' idiom that makes nwnsc leak into the parent file)."""
    s = src_bytes.decode("latin-1")
    i, n, in_block = 0, len(s), False
    while i < n:
        c = s[i]
        if in_block:
            if c == "*" and i + 1 < n and s[i + 1] == "/":
                in_block = False; i += 2; continue
            i += 1; continue
        if c == "/" and i + 1 < n and s[i + 1] == "/":
            j = s.find("\n", i); i = n if j < 0 else j + 1; continue
        if c == "/" and i + 1 < n and s[i + 1] == "*":
            in_block = True; i += 2; continue
        if c == '"':
            j = i + 1
            while j < n:
                if s[j] == "\\" and j + 1 < n:
                    j += 2; continue
                if s[j] == '"':
                    break
                j += 1
            i = j + 1; continue
        i += 1
    return in_block


def fix_comments(src_bytes):
    """Close a dangling /* block comment (append */). Returns (new_bytes, changed)."""
    if ends_in_block_comment(src_bytes):
        return src_bytes + b"\n*/\n", True
    return src_bytes, False


def has_entrypoint(src_bytes):
    """True if the script is a compilable unit (has void main / int StartingConditional)."""
    s = re.sub(r"//[^\n]*|/\*.*?\*/", " ", src_bytes.decode("latin-1"), flags=re.S)
    return bool(re.search(r"\bvoid\s+main\s*\(", s) or
                re.search(r"\bint\s+StartingConditional\s*\(", s))


def includes(src_bytes):
    """List of #include "resref" targets (lowercased)."""
    s = re.sub(r"//[^\n]*|/\*.*?\*/", " ", src_bytes.decode("latin-1"), flags=re.S)
    return [m.lower() for m in re.findall(r'#\s*include\s+"([^"]+)"', s)]


# high-precision developer-output marker: "DEBUG: ...", "ERROR: ...", etc. (the
# colon avoids catching natural dialogue that merely starts with one of these words)
_DEBUG_STR = re.compile(r"^\s*(DEBUG|ERROR|WARNING|WARN|TODO|FIXME|ASSERT)\s*:", re.I)


def _has_letter(t):
    return any(("a" <= c <= "z") or ("A" <= c <= "Z") for c in t)


def _is_codey(t):
    """True if a SINGLE-token string looks like code, not player text: a Hungarian/
    camelCase/snake_case identifier, a resref, an ALLCAPS state label, or a function
    trace ('DLA_Mount('). Multi-word strings (a space) are always treated as text."""
    s = t.strip()
    if not s:
        return True
    if s.endswith("(") or s.endswith("::"):
        return True
    if " " in s or "\t" in s:                       # has a space -> real text
        return False
    if re.search(r"[a-z][A-Z]", s):                 # camelCase: nDLAMountState, sHorseTag
        return True
    if "_" in s and re.fullmatch(r"[A-Za-z0-9_]+", s):   # snake_case / resref: nw_cloth022
        return True
    if re.fullmatch(r"[A-Z][A-Z0-9]{3,}", s):       # ALLCAPS label: INITIALIZE, TRUE
        return True
    return False


def looks_translatable(t):
    """Natural-language filter for cutscene-var literals: reject tags / identifiers /
    resrefs / ALL_CAPS constants; accept real words & sentences."""
    if not _has_letter(t):
        return False
    if re.fullmatch(r"[A-Za-z0-9_]+", t):           # single token, no spaces/punct
        if "_" in t or t.isupper() or len(t) <= 2:  # WP_DOOR, DEBUG, tag-like, "OK"
            return False
    return True


def _split_top_level(argtoks, sep="+"):
    """Split a token list at top-level (depth-0) occurrences of a punct operator."""
    pieces, cur, depth = [], [], 0
    for t in argtoks:
        if t[0] == "punct" and t[1] in "([":
            depth += 1
        elif t[0] == "punct" and t[1] in ")]":
            depth -= 1
        if depth == 0 and t[0] == "punct" and t[1] == sep:
            pieces.append(cur); cur = []
        else:
            cur.append(t)
    pieces.append(cur)
    return pieces


def _top_level_ops(argtoks):
    """The set of top-level binary operator chars in an arg (to detect clean concat)."""
    ops, depth, prev = set(), 0, None
    for t in argtoks:
        if t[0] == "punct" and t[1] in "([":
            depth += 1
        elif t[0] == "punct" and t[1] in ")]":
            depth -= 1
        elif depth == 0 and t[0] == "punct" and t[1] in "+-*/%<>=!&|?:":
            ops.add(t[1])
        prev = t
    return ops


def build_units(argtoks, src, nl_filter):
    """Turn an argument/RHS token list into translation units.

    Returns a list of dicts:
      simple literal -> {kind:'s', start, end, en}
      concat group   -> {kind:'c', span:(start,end), codes:[(s,e),...],
                         lits:[(s,e),...], en:<template with {k}>}
        span  = byte range of the WHOLE concat expression (apply rewrites it
                wholesale, so the translator may freely move {k} insertions).
        codes = byte ranges of the non-literal pieces, in placeholder order.
    `src` is the latin-1 decoded source (for slicing code pieces / verifying).
    `nl_filter` True -> apply natural-language filter (cutscene vars).
    """
    # top-level string tokens
    top_strs, depth = [], 0
    for t in argtoks:
        if t[0] == "punct" and t[1] in "([":
            depth += 1
        elif t[0] == "punct" and t[1] in ")]":
            depth -= 1
        elif depth == 0 and t[0] == "str":
            top_strs.append(t)
    if not top_strs:
        return []

    ops = _top_level_ops(argtoks)
    clean_concat = ops <= {"+"} and "+" in ops

    def ok(text):
        if not _has_letter(text) or _DEBUG_STR.match(text) or _is_codey(text):
            return False
        return looks_translatable(text) if nl_filter else True

    # OUTER byte range of a token (string tokens carry inner content; the span we
    # rewrite must include their surrounding quotes).
    def outer(t):
        return (t[2] - 1, t[3] + 1) if t[0] == "str" else (t[2], t[3])

    units = []
    if clean_concat:
        pieces = [pc for pc in _split_top_level(argtoks, "+") if pc]
        # classify each piece: single str token -> LIT; else -> CODE
        template, lits, codes, codek = [], [], [], 0
        for pc in pieces:
            if len(pc) == 1 and pc[0][0] == "str":
                template.append(pc[0][1]); lits.append((pc[0][2], pc[0][3]))
            else:                                   # code piece (verbatim source span)
                codes.append((outer(pc[0])[0], outer(pc[-1])[1]))
                template.append("{%d}" % codek); codek += 1
        if len(lits) == 1 and codek == 0:
            t = top_strs[0]
            if ok(t[1]):
                units.append({"kind": "s", "start": t[2], "end": t[3], "en": t[1]})
        elif lits and any(_has_letter(x) for x in template if not re.fullmatch(r"\{\d+\}", x)):
            en = "".join(template)
            bare = re.sub(r"\{\d+\}", " ", en)      # natural-language check, placeholders aside
            if not _DEBUG_STR.match(en) and not _is_codey(re.sub(r"\{\d+\}", "", en)) \
                    and ((not nl_filter) or looks_translatable(bare)):
                span = (outer(argtoks[0])[0], outer(argtoks[-1])[1])
                units.append({"kind": "c", "span": span, "codes": codes,
                              "lits": lits, "en": en})
    else:
        for t in top_strs:                          # ternary / mixed -> each independent
            if ok(t[1]):
                units.append({"kind": "s", "start": t[2], "end": t[3], "en": t[1]})
    return units


_KEYWORDS = {"if", "while", "for", "switch", "return", "do", "else"}

# wrapper functions whose name marks them as developer/debug output (their string
# arg is a debug message, NOT player-facing) -> never treated as a display slot.
_DEBUG_FN = re.compile(r"(?i)(debug|dbg|log|trace|dump|assert|spam|verbose|"
                       r"console|report|printc|wrlog|_pr\b|monitor|\btest)")


def _parse_paren(toks, op):
    """Given op = index of a '(' token, return (args, close_idx). args is a list of
    argument token-lists split on top-level commas (the outer parens excluded)."""
    depth, k, args, cur = 0, op, [], []
    while k < len(toks):
        t = toks[k]
        if t[0] == "punct" and t[1] in "([":
            depth += 1
            if depth > 1:
                cur.append(t)
        elif t[0] == "punct" and t[1] in ")]":
            depth -= 1
            if depth == 0:
                args.append(cur); return args, k
            cur.append(t)
        elif t[0] == "punct" and t[1] == "," and depth == 1:
            args.append(cur); cur = []
        elif depth >= 1:
            cur.append(t)
        k += 1
    return args, k


def _param_name(pc):
    eq = next((i for i, t in enumerate(pc) if t[0] == "punct" and t[1] == "="), len(pc))
    ids = [t[1] for t in pc[:eq] if t[0] == "id"]
    return ids[-1] if ids else None


def _iter_calls(toks):
    """Yield (funcname, args, call_index) for every function-call in a token list."""
    i = 0
    while i < len(toks) - 1:
        t = toks[i]
        if t[0] == "id" and t[1] not in _KEYWORDS \
                and toks[i + 1] == ("punct", "(", toks[i + 1][2], toks[i + 1][3]):
            args, close = _parse_paren(toks, i + 1)
            yield t[1], args, i
            i = i + 1
        else:
            i += 1


def discover_display_slots(sources):
    """Find module-defined display WRAPPER functions: any function that forwards one
    of its string parameters into a known display slot (transitively). Returns a
    {func_name: set(arg_index)} map seeded with the engine functions. This catches
    SceneSpeak/cs_*/csll_*/SpeakWrapper/PartyGotEntry etc. without hard-coding."""
    slots = {k: set(v) for k, v in DISPLAY_SLOTS.items()}
    defs = []                                       # (name, [param_names], body_tokens)
    for data in sources.values():
        toks = tokenize(data)
        i, n = 0, len(toks)
        while i < n - 2:
            j = i + 1 if (toks[i][0] == "id" and toks[i][1] == "struct") else i
            if toks[j][0] == "id" and j + 2 < n and toks[j + 1][0] == "id" \
                    and toks[j + 2] == ("punct", "(", toks[j + 2][2], toks[j + 2][3]):
                name = toks[j + 1][1]
                params, close = _parse_paren(toks, j + 2)
                if close + 1 < n and toks[close + 1] == ("punct", "{", toks[close + 1][2], toks[close + 1][3]):
                    pnames = [_param_name(pc) for pc in params]
                    depth, k, body = 0, close + 1, []
                    while k < n:
                        t = toks[k]
                        if t[0] == "punct" and t[1] == "{":
                            depth += 1
                        elif t[0] == "punct" and t[1] == "}":
                            depth -= 1
                            if depth == 0:
                                break
                        body.append(t); k += 1
                    defs.append((name, pnames, body))
                    i = k + 1; continue
            i += 1
    changed = True
    while changed:
        changed = False
        for name, pnames, body in defs:
            if _DEBUG_FN.search(name):              # debug/log wrapper -> not display
                continue
            for fn, args, _ in _iter_calls(body):
                for slot in slots.get(fn, ()):
                    if slot < len(args) and len(args[slot]) == 1 and args[slot][0][0] == "id" \
                            and args[slot][0][1] in pnames:
                        pos = pnames.index(args[slot][0][1])
                        if pos not in slots.get(name, set()):
                            slots.setdefault(name, set()).add(pos); changed = True
    return slots


def extract(src_bytes, slots=None):
    """Extract translation units from one comment-fixed NSS source.

    `slots` = {func: set(arg_idx)} display map (default: engine functions only; pass
    discover_display_slots(all_sources) to also catch module wrapper functions).
    Returns units (see build_units) in source order: display-function args first,
    then cutscene 'string sLine.. = ..' assignments over still-unclaimed literals."""
    if slots is None:
        slots = {k: set(v) for k, v in DISPLAY_SLOTS.items()}
    toks = tokenize(src_bytes)
    s = src_bytes.decode("latin-1")
    claimed = set()                                 # inner-start offsets already taken
    units = []

    # pass 1: display-function (incl. discovered wrapper) call arguments.
    # Also record bare-identifier args sitting in a display slot (a variable spoken
    # later) so pass 2 can pull its literal assignment.
    display_vars = set()
    for fn, args, ci in _iter_calls(toks):
        if fn not in slots:
            continue
        for slot in slots[fn]:
            if slot < len(args):
                arg = args[slot]
                if len(arg) == 1 and arg[0][0] == "id":
                    display_vars.add(arg[0][1])
                for u in build_units(arg, s, nl_filter=False):
                    starts = [u["start"]] if u["kind"] == "s" else [a for a, b in u["lits"]]
                    for st in starts:
                        claimed.add(st)
                    units.append(u)

    # vars compared against a literal (VAR == / != ...) must NOT have their assignment
    # translated, or the comparison would break -> drop them from the dataflow set.
    compared = set()
    for k in range(len(toks)):
        if toks[k][0] == "punct" and toks[k][1] in "=!" and k + 1 < len(toks) \
                and toks[k + 1] == ("punct", "=", toks[k + 1][2], toks[k + 1][3]):
            for nb in (k - 1, k + 2):
                if 0 <= nb < len(toks) and toks[nb][0] == "id":
                    compared.add(toks[nb][1])
    flow_vars = display_vars - compared

    # pass 2: literal assignments to (a) a variable spoken via a display slot [dataflow,
    # any scope] or (b) a cutscene-named "string sLine.. = .." var [name heuristic, top
    # level]. e.g. const string S_NARRATION_1 = "..."; ... cs_SpeakString(o, S_NARRATION_1)
    depth = 0
    i = 0
    while i < len(toks):
        tk = toks[i]
        if tk[0] == "punct" and tk[1] in "([{":
            depth += 1; i += 1; continue
        if tk[0] == "punct" and tk[1] in ")]}":
            depth -= 1; i += 1; continue
        is_assign = (tk[0] == "id" and i + 1 < len(toks)
                     and toks[i + 1] == ("punct", "=", toks[i + 1][2], toks[i + 1][3])
                     and not (i + 2 < len(toks) and toks[i + 2] == ("punct", "=", toks[i + 2][2], toks[i + 2][3]))
                     and not (toks[i - 1][0] == "punct" and toks[i - 1][1] in "=!<>"))
        flow = is_assign and tk[1] in flow_vars
        named = is_assign and depth == 0 and tk[1][0] in "sS" and bool(_CUT_VAR.search(tk[1]))
        if flow or named:
            rhs, j, d = [], i + 2, 0
            while j < len(toks):
                x = toks[j]
                if x[0] == "punct" and x[1] in "([":
                    d += 1
                elif x[0] == "punct" and x[1] in ")]":
                    d -= 1
                elif x[0] == "punct" and x[1] == ";" and d == 0:
                    break
                rhs.append(x); j += 1
            if any(x[0] == "str" and x[2] not in claimed for x in rhs):
                for u in build_units(rhs, s, nl_filter=not flow):
                    starts = [u["start"]] if u["kind"] == "s" else [a for a, b in u["lits"]]
                    if any(st in claimed for st in starts):
                        continue
                    for st in starts:
                        claimed.add(st)
                    units.append(u)
            i = j; continue
        i += 1

    units.sort(key=lambda u: u["start"] if u["kind"] == "s" else u["lits"][0][0])
    return units
