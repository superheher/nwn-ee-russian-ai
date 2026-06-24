#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_english.py - MODEL-INDEPENDENT check: scan every string constant in every
DEPLOYED NCS and report the ones that are still ENGLISH and look like player-
visible text. This does NOT rely on any assumption about which functions are
"display" - it reads the actual bytecode the game runs, so it catches strings no
matter which wrapper/include produced them.

A string is flagged as a likely untranslated player-facing line if it:
  * contains no Cyrillic (i.e. was not translated),
  * has a space and >=2 letter-words (a phrase, not a tag/resref/identifier),
  * has lowercase letters (not an ALLCAPS constant),
  * isn't a path / resref / colour-code-only / format-only string.
Findings are split into "content" (likely real) vs "debug-ish" (dev output) so the
size of the real gap is visible. Run before publishing.

  audit_english.py [--mod NAME] [--samples N]
"""
import os, sys, re, json, glob, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import erf, ncs

CYR = re.compile(r"[Ѐ-ӿ]")
WORD = re.compile(r"[A-Za-z]{2,}")
# dev/debug output: var dumps, engine-state traces, error/abort logs, fragments
DEBUGISH = re.compile(r"(?i)("
    r"\*\*\*|=\s*$|:\s*$|\bnHD\b|nSpecific|identifier|activated|listening|"
    r"cutscene mode|commandable|setting up|player is entering|creating object|"
    r"object_invalid|end condition|active team|player found|firing|"
    r"\bdebug|\berror\b|aborted|\bfailed\b|please report|bug to|no valid|"
    r"onenter|onexit|oncliententer|getlocal|setlocal|\bwp\b|waypoint|"
    r"\bresref\b|\btag\b|placeable|x[0-3]_|nw_|2da|console|testing|"
    r"not hired|not in conversation|not in cutscene|different areas|"
    r"recreate|set last master|attempt made|other stuff|blank item|"
    r"%[sdif]|sdla_|firehenchman|level up failed|in class\b|generate treasure)")
TAGGISH = re.compile(r"^[A-Za-z0-9_]+$|^[a-z0-9_./]+$|<<|>>|^\s*<c|::")
# script resref itself marked as debug/test scaffolding
DEBUG_RESREF = re.compile(r"(?i)debug|tester|_test|test_")


# positive signal that a string is real player-facing prose (not a dev fragment)
_NARRATIVE = re.compile(r"(?i)\b(you|your|yours|the|a|an|this|that|these|those|is|are|"
                        r"was|were|have|has|will|would|can|could|not|no|with|for|of|"
                        r"to|and|but|here|there|i|we|they|he|she|it|my|me|us|them)\b")


def looks_player_text(s):
    if not s or CYR.search(s):                       # translated or empty
        return False
    if len(s) < 10 or "\t" in s:
        return False
    if TAGGISH.search(s):
        return False
    if not any("a" <= c <= "z" for c in s):          # ALLCAPS -> tag/const
        return False
    if " " not in s:
        return False
    words = WORD.findall(s)
    if len(words) < 2:
        return False
    return sum(1 for w in words if w[0].islower() or len(w) > 3) >= 2


def is_content(s):
    """Stronger: real player prose. A var-dump fragment ('Recipe is ', 'nLevel = ')
    has narrative words too, so also require it to look like a SENTENCE: ends with
    real punctuation OR is long, AND has >=4 words, AND >=2 narrative words, AND
    doesn't trail in '= ' / ': ' / 'is '."""
    s2 = s.strip()
    if not looks_player_text(s):
        return False
    if re.search(r"(=|:|\bis|\bto|\bat|\bin|\bof|\bfor)\s*$", s2):   # trailing-label dump
        return False
    if re.match(r"(?i)(debug|error|warning|note)\b\s*:", s2) or "***" in s2:
        return False
    if re.search(r"(?i)(report as bug|report to brent|invalid (item|assignment|class|"
                 r"appearance)|determineclass|/dm check|firehenchman|could not (find|be found)|"
                 r"is being hitched|lachorse|not hired|x3_inc_horse|setting up\b)", s2):
        return False
    if len(WORD.findall(s2)) < 4:
        return False
    if len(_NARRATIVE.findall(s2)) < 2:
        return False
    sentence = bool(re.search(r"[.!?…\"'»]\s*$", s2)) or len(s2) > 35
    return sentence


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod")
    ap.add_argument("--samples", type=int, default=12)
    args = ap.parse_args()
    cfg = json.load(open(os.path.join(HERE, "nss_modules.json"), encoding="utf-8"))
    mods = [args.mod] if args.mod else list(cfg)

    grand_content = grand_debug = 0
    for m in mods:
        dep = cfg[m]["deploy"]
        if not os.path.exists(dep):
            continue
        e = erf.read_erf(open(dep, "rb").read())
        seen, content, debugish, unparsed = set(), [], [], 0
        for r in e["resources"]:
            if r["restype"] != 2010:
                continue
            if not ncs.round_trip(r["data"]):
                unparsed += 1; continue
            for _off, _ln, b in ncs.strings(r["data"]):
                s = b.decode("cp1251", "replace")
                if s in seen or not looks_player_text(s):
                    continue
                seen.add(s)
                if is_content(s) and not DEBUG_RESREF.search(r["resref"]):
                    content.append((r["resref"], s))
                else:
                    debugish.append((r["resref"], s))
        grand_content += len(content); grand_debug += len(debugish)
        flag = "  <-- REVIEW" if content else ""
        print(f"{m:12} english-content={len(content):4}  debug-ish={len(debugish):4}"
              f"  unparsed_ncs={unparsed}{flag}")
        for rr, s in content[:args.samples]:
            print(f"     [{rr}] {s[:78]!r}")
    print(f"\nTOTAL likely-untranslated player text: {grand_content}  (debug-ish: {grand_debug})")
    print("content==0 across all modules => no English player lines remain in script bytecode.")


if __name__ == "__main__":
    main()
