"""Membaca PDF per halaman: teks lengkap + posisi kata (untuk membaca tabel indeks GRI)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

import pymupdf


@dataclass
class Word:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str

    @property
    def xc(self) -> float:
        return (self.x0 + self.x1) / 2


@dataclass
class Page:
    number: int          # nomor halaman fisik PDF (mulai 1)
    text: str
    width: float
    height: float
    words: list[Word] = field(default_factory=list)


@dataclass
class Document:
    path: Path
    pages: list[Page]

    @property
    def page_count(self) -> int:
        return len(self.pages)


_WS = re.compile(r"[ \t ]+")


def read_pdf(path: str | Path) -> Document:
    path = Path(path)
    pages: list[Page] = []
    with pymupdf.open(path) as doc:
        for i, p in enumerate(doc):
            words = [Word(w[0], w[1], w[2], w[3], w[4]) for w in p.get_text("words")]
            text = _WS.sub(" ", p.get_text("text"))
            pages.append(Page(i + 1, text, p.rect.width, p.rect.height, words))
    return Document(path, pages)
