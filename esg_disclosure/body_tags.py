"""Mencari NOMOR item GRI di dalam isi laporan (di luar tabel indeks GRI).

Aturan skripsi: yang dihitung hanya nomor item yang tertulis (mis. "102-52", "(102-5)",
"[305-1]", "GRI 2-1"). Pembahasan topik tanpa menuliskan nomor item TIDAK dihitung.
"""
from __future__ import annotations

from collections import defaultdict
import re

from .codes import BRACKET_RE, GEN2021_IN_TEXT_RE, GRI_PREFIXED_RE, TOPIC_IN_TEXT_RE
from .pdf_reader import Document

_ONLY_CODES = re.compile(r"^[\sGRI0-9\-.,;/&a-z]*$", re.I)


def find_body_tags(doc: Document, skip_pages: set[int]) -> dict[str, list[int]]:
    """kode -> daftar halaman PDF (di luar tabel indeks GRI) yang menuliskan nomor item tsb."""
    found: dict[str, set[int]] = defaultdict(set)
    for page in doc.pages:
        if page.number in skip_pages:
            continue
        text = page.text.replace("\n", " ")
        # kode GRI 2016/2018/2020 (3 digit): dihitung di mana pun nomornya tertulis
        for c in TOPIC_IN_TEXT_RE.findall(text):
            found[c].add(page.number)
        # kode GRI 2021 ("2-1") rawan tertukar dengan angka biasa, jadi harus
        # di dalam kurung yang isinya murni kode ("[2-1, 2-6]") atau diawali "GRI" ("GRI 2-9")
        for m in BRACKET_RE.finditer(text):
            inner = m.group(1)
            if _ONLY_CODES.match(inner) and not re.search(r"\b(19|20)\d\d\b", inner):
                for c in GEN2021_IN_TEXT_RE.findall(inner):
                    found[c].add(page.number)
        for c in GRI_PREFIXED_RE.findall(text):
            found[c].add(page.number)
    return {c: sorted(p) for c, p in found.items()}
