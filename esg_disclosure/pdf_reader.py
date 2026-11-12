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
    src_path: Path | None = None   # file PDF asal & nomor halaman di file itu (untuk OCR)
    src_index: int = 0
    ocr: bool = False


@dataclass
class Document:
    path: Path
    pages: list[Page]

    @property
    def page_count(self) -> int:
        return len(self.pages)


_WS = re.compile(r"[ \t ]+")
_SPLIT_CODE = re.compile(r"^\d{1,3}\s?[-\u2013]\s?\d{1,2}$")


def merge_split_codes(words: list[Word]) -> list[Word]:
    """Gabungkan kode GRI yang terpecah jadi beberapa kata pada baris yang sama,
    mis. "102" "-" "52" atau "102-" "52" (tabel indeks bergaya "GRI 102 - 52") menjadi "102-52"."""
    out: list[Word] = []
    i, n = 0, len(words)
    while i < n:
        w = words[i]
        merged = False
        prev_gri = bool(out) and out[-1].text.upper().rstrip(":") == "GRI" and abs(out[-1].y0 - w.y0) < 3
        if re.fullmatch(r"\d{1,3}-?", w.text) and (len(w.text.rstrip("-")) == 3 or prev_gri):
            for k in (3, 2):
                grp = words[i:i + k]
                if len(grp) < k:
                    continue
                same_line = all(abs(g.y0 - w.y0) < 3 and 0 <= g.x0 - grp[j].x1 < 8 for j, g in enumerate(grp[1:]))
                joined = "".join(g.text for g in grp)
                if same_line and "-" in joined and _SPLIT_CODE.match(joined):
                    out.append(Word(w.x0, min(g.y0 for g in grp), grp[-1].x1, max(g.y1 for g in grp),
                                    joined.replace("\u2013", "-")))
                    i += k
                    merged = True
                    break
        if not merged:
            out.append(w)
            i += 1
    return out




def read_pdf(path: str | Path) -> Document:
    path = Path(path)
    pages: list[Page] = []
    with pymupdf.open(path) as doc:
        for i, p in enumerate(doc):
            words = merge_split_codes([Word(w[0], w[1], w[2], w[3], w[4]) for w in p.get_text("words")])
            text = _WS.sub(" ", p.get_text("text"))
            pages.append(Page(i + 1, text, p.rect.width, p.rect.height, words, path, i))
    return Document(path, pages)


def ocr_page(page: Page, dpi: int = 400) -> bool:
    """Baca halaman berbentuk gambar dengan Tesseract; isi page.words & page.text. True bila berhasil.
    Halaman lanskap berisi dua halaman berdampingan (spread) dibaca per separuh agar kolom tidak tercampur."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return False
    if page.src_path is None:
        return False
    with pymupdf.open(page.src_path) as doc:
        pix = doc[page.src_index].get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    k = 72.0 / dpi
    parts = [(0, img)]
    if page.width > page.height * 1.3:
        h = img.width // 2
        parts = [(0, img.crop((0, 0, h, img.height))), (h, img.crop((h, 0, img.width, img.height)))]
    words = []
    for off, im in parts:
        try:
            d = pytesseract.image_to_data(im, lang="eng", config="--psm 6", output_type=pytesseract.Output.DICT)
        except Exception:
            return False
        for t, x, y, w, hh, conf in zip(d["text"], d["left"], d["top"], d["width"], d["height"], d["conf"]):
            t = t.strip()
            if t and float(conf) > 10:
                words.append(Word((x + off) * k, y * k, (x + off + w) * k, (y + hh) * k, t))
    page.words = merge_split_codes(sorted(words, key=lambda w: (round(w.y0 / 3), w.x0)))
    page.text = _WS.sub(" ", " ".join(w.text for w in page.words))
    page.ocr = True
    return True
