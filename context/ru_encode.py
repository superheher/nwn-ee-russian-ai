#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ru_encode.py - encode our Russian to the bytes NWN reads.

NWN text is CP1251, but not every byte in a string is text: a colour tag is
literally "<c" + three raw RGB bytes + ">", and those bytes reach us as the
Latin-1 characters an English read produced (`<c ÿÿ>` = 20 FF FF). A plain
`.encode("cp1251", "replace")` turns each of them into '?' = 0x3F, which both
loses the colour and rewrites it as near-black - the item description the player
was meant to read comes out dark grey on dark grey.

So: CP1251 for text, and any character CP1251 has no room for goes back as the
single byte it came in as, if it has one.
"""


def cp1251_bytes(s):
    """Russian -> CP1251 bytes, preserving raw bytes carried as Latin-1 chars."""
    out = bytearray()
    for ch in s:
        try:
            out += ch.encode("cp1251")
        except UnicodeEncodeError:
            try:
                out += ch.encode("cp1252")      # the byte it was read as
            except UnicodeEncodeError:
                out += b"?"
    return bytes(out)


def en_bytes(s):
    """English source text -> the bytes it was read from (Latin-1/CP1252)."""
    return s.encode("cp1252", "replace")
