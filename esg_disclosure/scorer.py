"""Menggabungkan bukti (tabel indeks, tanda kode di isi laporan, model ML) menjadi poin 0/1
untuk setiap baris item di sheet ESGD, mengikuti aturan penilaian skripsi:

* Poin 1 bila item dijelaskan di laporan ATAU tercantum di indeks GRI dengan rujukan halaman/lokasi.
* Poin 0 bila tidak ada penjelasan dan tidak ada rujukan halaman/lokasi di indeks GRI.
* Tahun 2020-2021 (GRI 2016): setiap baris 102-x dinilai sendiri-sendiri.
  Sub-item 102-7-a-i, 102-8-d, 103-2-c-vi mengikuti item utamanya (102-7, 102-8, 103-2).
* Tahun 2022-2024 (GRI 2021): seluruh baris dalam satu item 2-x diberi nilai yang sama.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math

from .body_tags import find_body_tags
from .codes import is_gen2021, parent_code
from .gri_index import GriIndex, _code_tokens, _index_layout, parse_gri_index
from .pdf_reader import Document
from .template import Template, TemplateRow

GRI2021_FIRST_YEAR = 2022


@dataclass
class CodeEvidence:
    code: str
    index_location: str = ""
    index_listed: bool = False
    tag_pages: list[int] = field(default_factory=list)
    ml_prob: float | None = None
    features: list[float] = field(default_factory=list)

    @property
    def rule_disclosed(self) -> bool:
        return bool(self.index_location) or bool(self.tag_pages)


@dataclass
class RowResult:
    row: int
    item: str
    code_used: str
    score: int
    source: str
    evidence: CodeEvidence | None = None
    ml_disagrees: bool = False


class DocumentAnalyzer:
    """Mengumpulkan bukti untuk satu laporan (satu perusahaan, satu tahun)."""

    def __init__(self, doc: Document, model=None, ml_threshold: float = 0.5):
        self.doc = doc
        self.index: GriIndex = parse_gri_index(doc)
        # halaman tabel daftar kode (indeks GRI, tabel pemetaan SDGs/POJK) bukan "isi laporan"
        table_pages = {p.number for p in doc.pages if _index_layout(p)[0]}
        self.skip_pages = set(self.index.pages) | table_pages
        # sambungan tabel indeks (halaman berikutnya yang masih memuat kode, mis. baris terakhir indeks)
        for n in sorted(self.index.pages):
            nxt = n + 1
            while nxt <= doc.page_count and nxt not in self.skip_pages and _code_tokens(doc.pages[nxt - 1]):
                self.skip_pages.add(nxt)
                nxt += 1
        self.tags = find_body_tags(doc, self.skip_pages)
        self.model = model
        self.ml_threshold = ml_threshold
        self._cache: dict[str, CodeEvidence] = {}

    # Standar GRI yang dipakai laporan (dilihat dari kode di tabel indeks)
    @property
    def n_codes_2021(self) -> int:
        return sum(1 for c in self.index.codes() if c.startswith("2-") and self.index.has_location(c))

    @property
    def n_codes_2016(self) -> int:
        return sum(1 for c in self.index.codes() if c.startswith("102-") and self.index.has_location(c))

    def evidence(self, code: str) -> CodeEvidence:
        if code in self._cache:
            return self._cache[code]
        ev = CodeEvidence(code)
        ev.index_listed = self.index.listed(code)
        ev.index_location = self.index.location(code)
        ev.tag_pages = self.tags.get(code, [])
        ev.features = feature_vector(ev)
        if self.model is not None:
            ev.ml_prob = float(self.model.predict_proba([ev.features])[0][1])
        self._cache[code] = ev
        return ev

    def disclosed(self, code: str, titles: list[str] | None = None) -> tuple[int, str, CodeEvidence]:
        """Aturan skripsi (hanya berdasarkan NOMOR item):
        1 = ada halaman/lokasi di tabel indeks GRI, ATAU nomor item tertulis di isi laporan;
        0 = selain itu (termasuk: tercantum di indeks tetapi kolom halamannya kosong / "-")."""
        ev = self.evidence(code)
        if ev.index_location:
            return 1, f"Indeks GRI hal. {ev.index_location}", ev
        pages = ", ".join(map(str, ev.tag_pages[:8]))
        if ev.tag_pages and ev.index_listed:
            return 1, f"Di indeks tanpa halaman, tetapi nomor item tertulis di laporan hal. PDF {pages}", ev
        if ev.tag_pages:
            return 1, f"Nomor item tertulis di laporan hal. PDF {pages}", ev
        if ev.index_listed:
            loc = self.index.raw_location(code)
            what = f'dengan isi kolom "{loc}" (bukan rujukan halaman/lokasi)' if loc else "tanpa halaman/lokasi"
            return 0, f"Tercantum di indeks GRI {what} & nomor item tidak tertulis di laporan", ev
        return 0, "Nomor item tidak ditemukan", ev


def feature_vector(ev: CodeEvidence) -> list[float]:
    return [
        1.0 if ev.index_location else 0.0,
        1.0 if (ev.index_listed and not ev.index_location) else 0.0,
        math.log1p(len(ev.tag_pages)),
    ]


FEATURE_NAMES = ["indeks_ada_halaman", "indeks_tanpa_halaman", "log_halaman_bernomor_item"]


def _titles(r: TemplateRow) -> list[str]:
    return [r.title2021] + ([r.title2016] if r.title2016 else [])


def score_document(an: DocumentAnalyzer, template: Template, year: int) -> list[RowResult]:
    results: list[RowResult] = []
    mode_2021 = year >= GRI2021_FIRST_YEAR
    # fallback bila laporan memakai standar yang berbeda dari kebiasaan tahunnya
    report_2021_only = an.n_codes_2021 >= 5 and an.n_codes_2016 == 0
    report_2016_only = an.n_codes_2016 >= 5 and an.n_codes_2021 == 0

    groups = template.groups()
    group_cache: dict[str, tuple[int, str, CodeEvidence | None]] = {}

    def score_2016_row(r: TemplateRow) -> tuple[int, str, str, CodeEvidence]:
        code = r.code2016 or r.code2021
        main = parent_code(code)
        s, src, ev = an.disclosed(main, _titles(r))
        if main != code:
            src = f"Mengikuti item utama {main}: {src}"
        return s, src, main, ev

    def score_group_2021(code2021: str) -> tuple[int, str, CodeEvidence | None]:
        if code2021 in group_cache:
            return group_cache[code2021]
        rows = groups[code2021]
        s, src, ev = an.disclosed(code2021, _titles(rows[0]))
        if s == 0 and report_2016_only and any(r.code2016 for r in rows):
            sub = [score_2016_row(r) for r in rows if r.code2016]
            best = max(sub, key=lambda x: x[0])
            if best[0] == 1:
                s, src, ev = 1, f"Laporan memakai GRI 2016 ({best[2]}): {best[1]}", best[3]
        group_cache[code2021] = (s, src, ev)
        return group_cache[code2021]

    for r in template.rows:
        item = r.title2016 or r.title2021
        if r.section == "GOVERNANCE":
            if mode_2021 or (report_2021_only and is_gen2021(r.code2021)):
                s, src, ev = score_group_2021(r.code2021)
                if not mode_2021:
                    src = f"Laporan memakai GRI 2021 ({r.code2021}): {src}"
                results.append(RowResult(r.row, item, r.code2021, s, src, ev))
            else:
                s, src, used, ev = score_2016_row(r)
                results.append(RowResult(r.row, item, used, s, src, ev))
        else:
            s, src, ev = an.disclosed(r.code2021, _titles(r))
            results.append(RowResult(r.row, item, r.code2021, s, src, ev))
    if an.model is not None:
        for r in results:
            if r.evidence is not None and r.evidence.ml_prob is not None:
                r.ml_disagrees = (r.evidence.ml_prob >= an.ml_threshold) != bool(r.score)
    return results


def esg_score(results: list[RowResult], template: Template) -> float:
    """Skor ESG Disclosure = rata-rata seluruh item; baris-baris dalam satu item
    governance (mis. 2-1 = 102-1, 102-3, 102-4, 102-5) dirata-rata dulu."""
    by_row = {r.row: r.score for r in results}
    vals = []
    for code, rows in template.groups().items():
        vals.append(sum(by_row[r.row] for r in rows) / len(rows))
    return sum(vals) / len(vals) if vals else 0.0
