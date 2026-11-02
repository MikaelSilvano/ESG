"""Menemukan halaman laporan posisi keuangan (neraca) dan laporan laba rugi konsolidasian
di dalam laporan tahunan (bagian laporan keuangan auditan)."""
from __future__ import annotations

import re

import pymupdf

BS_TITLE = re.compile(r"(laporan\s+posisi\s+keuangan|statements?\s+of\s+financial\s+position)", re.I)
IS_TITLE = re.compile(r"(laporan\s+laba\s+rugi|statements?\s+of\s+profit\s+or\s+loss|"
                      r"statements?\s+of\s+(comprehensive\s+)?income)", re.I)
NOTES_HDR = re.compile(r"\b(catatan|notes)\b", re.I)
NOT_STATEMENT = re.compile(r"(catatan\s+atas\s+laporan\s+keuangan\s+konsolidasian\s*\n?\s*\d|"
                           r"ikhtisar|highlights|tinjauan\s+keuangan|financial\s+review)", re.I)


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", t)


def page_texts(doc: pymupdf.Document) -> list[str]:
    return [_norm(p.get_text()) for p in doc]


def _has_amount_rows(text: str) -> bool:
    return len(re.findall(r"\(?\d{1,3}(?:[.,]\d{3}){1,}\)?", text)) >= 8


def find_statements(texts: list[str]) -> tuple[list[int], list[int]]:
    """Kembalikan (halaman neraca, halaman laba rugi) — nomor halaman PDF (mulai 1).

    Neraca = 1-4 halaman berurutan berjudul 'laporan posisi keuangan' yang memuat kolom
    'Catatan/Notes' dan angka; laporan laba rugi = halaman berikutnya (<= 4 halaman setelahnya)."""
    n = len(texts)

    def is_bs(i):
        t = texts[i]
        head = t[:900]
        return bool(BS_TITLE.search(head) and NOTES_HDR.search(t) and _has_amount_rows(t))

    def is_is(i):
        t = texts[i]
        head = t[:900]
        return bool(IS_TITLE.search(head) and NOTES_HDR.search(t) and _has_amount_rows(t)
                    and re.search(r"(beban|biaya)\s+(keuangan|bunga)|finance\s+(cost|charge|expense)|"
                                  r"interest\s+expense|financial\s+charges", t, re.I))

    for i in range(n):
        if not is_bs(i):
            continue
        run = [i]
        j = i + 1
        while j < n and len(run) < 4 and is_bs(j):
            run.append(j)
            j += 1
        # laba rugi dalam 0-4 halaman setelah neraca
        for k in range(j, min(n, j + 4)):
            if is_is(k):
                inc = [k]
                if k + 1 < n and IS_TITLE.search(texts[k + 1][:900]) and _has_amount_rows(texts[k + 1]) \
                        and not BS_TITLE.search(texts[k + 1][:900]):
                    inc.append(k + 1)
                return [p + 1 for p in run], [p + 1 for p in inc]
    return [], []
