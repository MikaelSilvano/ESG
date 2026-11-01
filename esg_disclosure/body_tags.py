"""Mencari rujukan kode GRI di dalam isi laporan (di luar tabel indeks).

Banyak laporan menandai paragraf dengan kode GRI, mis. "Struktur Kepemilikan (102-5)(102-45)",
"[305-1] [305-2]" atau "GRI 2-1". Paragraf bertanda itu = ada penjelasan dalam laporan.
"""
from __future__ import annotations

from collections import defaultdict
import re

from .codes import BRACKET_RE, GEN2021_IN_TEXT_RE, GRI_PREFIXED_RE, TOPIC_IN_TEXT_RE
from .pdf_reader import Document

_ONLY_CODES = re.compile(r"^[\sGRI0-9\-.,;/&a-z]*$", re.I)


def find_body_tags(doc: Document, skip_pages: set[int]) -> dict[str, list[int]]:
    """kode -> daftar halaman PDF yang memuat tanda kode tersebut."""
    found: dict[str, set[int]] = defaultdict(set)
    for page in doc.pages:
        if page.number in skip_pages:
            continue
        text = page.text.replace("\n", " ")
        for m in BRACKET_RE.finditer(text):
            inner = m.group(1)
            for c in TOPIC_IN_TEXT_RE.findall(inner):
                found[c].add(page.number)
            # kode GRI 2021 ("2-1") hanya jika isi kurung murni kode, mis. "[2-1, 2-6]" / "(GRI 2-9)"
            if _ONLY_CODES.match(inner) and not re.search(r"\b(19|20)\d\d\b", inner):
                for c in GEN2021_IN_TEXT_RE.findall(inner):
                    found[c].add(page.number)
        for c in GRI_PREFIXED_RE.findall(text):
            found[c].add(page.number)
    return {c: sorted(p) for c, p in found.items()}
