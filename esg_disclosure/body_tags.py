"""Mencari NOMOR item GRI di dalam isi laporan (di luar tabel indeks GRI).

Aturan skripsi: yang dihitung hanya nomor item yang tertulis (mis. "102-52", "(102-5)",
"[305-1]", "GRI 2-1"). Pembahasan topik tanpa menuliskan nomor item TIDAK dihitung.

Pengecualian: daftar panjang nomor item tanpa kurung di judul/pembuka bab, mis.
"GRI ▶ 301-1, 301-2, 302-1, 302-2 ..." (INDY 2020). Itu hanya daftar isi bab, bukan
penjelasan item, sehingga tidak dihitung.
"""
from __future__ import annotations

from collections import defaultdict
import re

from .codes import BRACKET_RE, GEN2021_IN_TEXT_RE, GRI_PREFIXED_RE, TOPIC_CODE, TOPIC_IN_TEXT_RE
from .pdf_reader import Document

_ONLY_CODES = re.compile(r"^[\sGRI0-9\-.,;/&a-z]*$", re.I)
_CODE = rf"(?:{TOPIC_CODE})(?!\d)"
# >= 3 nomor item berurutan dipisah koma/titik koma (daftar kode tanpa kurung)
CODE_LIST_RE = re.compile(rf"(?<![\d\-./]){_CODE}(?:\s*[,;]\s*{_CODE}){{2,}}")
_EN_DASH_CODE = re.compile(r"(?<!\d)([1-4]\d{2})\s?[–—]\s?(\d{1,2})(?!\d)")


def _blank(text: str, spans) -> str:
    chars = list(text)
    for a, b in spans:
        chars[a:b] = " " * (b - a)
    return "".join(chars)


def find_body_tags(doc: Document, skip_pages: set[int]) -> dict[str, list[int]]:
    """kode -> daftar halaman PDF (di luar tabel indeks GRI) yang menuliskan nomor item tsb."""
    found: dict[str, set[int]] = defaultdict(set)
    for page in doc.pages:
        if page.number in skip_pages:
            continue
        text = _EN_DASH_CODE.sub(r"\1-\2", page.text.replace("\n", " "))   # "102–18" -> "102-18"
        brackets = list(BRACKET_RE.finditer(text))
        for m in brackets:
            inner = m.group(1)
            # nomor item di dalam kurung = tanda paragraf/judul subbab, mis. "(102-5)" "[305-1] [305-2]"
            for c in TOPIC_IN_TEXT_RE.findall(inner):
                found[c].add(page.number)
            # kode GRI 2021 ("2-1") hanya jika isi kurung murni kode, mis. "[2-1, 2-6]"
            if _ONLY_CODES.match(inner) and not re.search(r"\b(19|20)\d\d\b", inner):
                for c in GEN2021_IN_TEXT_RE.findall(inner):
                    found[c].add(page.number)
        # di luar kurung: abaikan daftar kode panjang (daftar isi bab), hitung sisanya
        rest = _blank(text, [m.span() for m in brackets])
        rest = _blank(rest, [m.span() for m in CODE_LIST_RE.finditer(rest)])
        rest = re.sub(r"GRI\s*[▶►>:]\s*", " ", rest)
        for c in TOPIC_IN_TEXT_RE.findall(rest):
            found[c].add(page.number)
        for c in GRI_PREFIXED_RE.findall(rest):
            found[c].add(page.number)
    return {c: sorted(p) for c, p in found.items()}
