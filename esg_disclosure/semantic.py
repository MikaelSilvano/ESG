"""Komponen Machine Learning: mendeteksi *penjelasan* item GRI di isi laporan
walaupun paragrafnya tidak diberi tanda kode GRI.

Cara kerja:
1. Setiap halaman laporan (selain tabel indeks) diubah menjadi vektor TF-IDF.
2. Setiap item GRI diwakili deskripsi (judul Indonesia + Inggris + kata kunci).
3. Kemiripan kosinus deskripsi vs halaman -> fitur (maks, rata-rata top-3, cakupan kata kunci).
4. Model Logistic Regression (dilatih dari perusahaan yang sudah dinilai manual, mis. DEWA)
   memberi probabilitas "item dijelaskan". Bila belum ada model, dipakai ambang konservatif.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .pdf_reader import Document

CATALOG_PATH = Path(__file__).parent / "data" / "gri_catalog.json"

STOPWORDS = set("""
yang dan di ke dari untuk dengan pada dalam ini itu atau oleh sebagai adalah tidak akan juga
telah serta secara terhadap kami perusahaan perseroan tahun the of and to in for on with by is are
be as at an a or from that this our its which was were has have been
""".split())


def load_catalog() -> dict[str, tuple[str, list[str]]]:
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    out = {}
    for code, val in raw.items():
        if code.startswith("_"):
            continue
        title, kw = val
        out[code] = (title, [k.strip() for k in kw.split(";") if k.strip()])
    return out


def _norm(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9à-ÿ\s\-]", " ", text)
    return re.sub(r"\s+", " ", text)


@dataclass
class SemanticFeatures:
    max_sim: float
    top3_sim: float
    kw_cover: float      # proporsi frasa kata kunci yang ditemukan di laporan
    best_page: int


class SemanticMatcher:
    def __init__(self, doc: Document, skip_pages: set[int]):
        self.catalog = load_catalog()
        self.pages = [p for p in doc.pages if p.number not in skip_pages and len(p.text) > 200]
        self.page_texts = [_norm(p.text) for p in self.pages]
        self.full_text = " ".join(self.page_texts)
        self.pdf_numbers = [p.number for p in self.pages]
        self.vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1,
                                   stop_words=list(STOPWORDS), max_features=60000)
        if self.page_texts:
            self.matrix = self.vec.fit_transform(self.page_texts)
        else:
            self.matrix = None

    def description(self, code: str, extra_titles: list[str]) -> tuple[str, list[str]]:
        title, kws = self.catalog.get(code, ("", []))
        desc = " ".join([title, *kws, *extra_titles])
        return desc, kws

    def features(self, code: str, extra_titles: list[str]) -> SemanticFeatures:
        desc, kws = self.description(code, extra_titles)
        if self.matrix is None or not desc.strip():
            return SemanticFeatures(0.0, 0.0, 0.0, 0)
        q = self.vec.transform([_norm(desc)])
        sims = cosine_similarity(q, self.matrix).ravel()
        order = np.argsort(sims)[::-1]
        top3 = float(np.mean(sims[order[:3]])) if len(order) else 0.0
        cover = (sum(1 for k in kws if _norm(k).strip() in self.full_text) / len(kws)) if kws else 0.0
        return SemanticFeatures(float(sims[order[0]]), top3, cover, self.pages[order[0]].number)

    def keyword_pages(self, code: str) -> tuple[str, list[int]] | None:
        """Frasa kata kunci yang paling spesifik (paling jarang muncul) beserta halamannya.
        Dipakai sebagai petunjuk 'cek manual' untuk item yang diberi poin 0."""
        _, kws = self.catalog.get(code, ("", []))
        best = None
        for k in kws:
            nk = _norm(k).strip()
            if len(nk) < 6:          # singkatan pendek (mis. 'ODS') terlalu ambigu
                continue
            pages = [n for n, tx in zip(self.pdf_numbers, self.page_texts) if nk in tx]
            if pages and (best is None or len(pages) < len(best[1])):
                best = (k, pages)
        return best
