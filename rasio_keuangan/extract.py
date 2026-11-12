"""Mengambil angka-angka yang dibutuhkan dari satu laporan tahunan."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

import pymupdf

from .classify import classify
from .locate import find_panel_statements, find_statements, half_pages, page_texts
from .parser import Row, parse_pages
from .units import Unit, detect_unit

PL = r"(laba|rugi|\(rugi\)|laba\s*\(rugi\)|\(rugi\)\s*laba|rugi\s*\(laba\))"
METRICS = {
    # nama: (pola label Indonesia, pola label Inggris, laporan)
    "total_aset": (re.compile(r"^(jumlah|total)\s+aset\s*$", re.I),
                   re.compile(r"^total\s+assets\s*$", re.I), "bs"),
    "total_ekuitas": (re.compile(r"^((jumlah|total)\s+)?ekuitas(\s*[-–]\s*(neto|bersih))?\s*$|^(jumlah|total)\s+ekuitas\s*[-–]\s*(neto|bersih)$", re.I),
                      re.compile(r"^total\s+equity\s*$", re.I), "bs"),
    "pendapatan": (re.compile(r"^(pendapatan|penjualan)(\s+(usaha|bersih|neto|kontrak|dari|dan|pokok))*\b(?!.*(lain|bunga|keuangan|komprehensif|investasi))", re.I),
                   re.compile(r"^(net\s+)?(revenues?|sales)\b(?!.*(other|interest|finance))", re.I), "is"),
    "laba_bruto": (re.compile(rf"^{PL}\s+(bruto|kotor)\b", re.I),
                   re.compile(r"^gross\s+(profit|loss|\(loss\)|income)", re.I), "is"),
    "laba_usaha": (re.compile(rf"^{PL}\s+(usaha|operasi(onal)?)\b", re.I),
                   re.compile(r"^(operating\s+(profit|income|loss)|(profit|income|loss)\s+from\s+operations)", re.I), "is"),
    "beban_keuangan": (re.compile(r"^(beban|biaya)\s+(keuangan|bunga|pendanaan)", re.I),
                       re.compile(r"^(finance|financial|financing)\s+(costs?|charges?|expenses?)|^interest\s+expense", re.I), "is"),
    "laba_bersih": (re.compile(rf"^{PL}(\s*/\s*\(?(rugi|laba)\)?)?\s+(bersih\s+|neto\s+)?((tahun|periode)\s+(berjalan|ini))?\s*$|^(laba|rugi)\s+(bersih|neto)\s*$|^{PL}\s+(tahun|periode)\s+berjalan\s*$", re.I),
                    re.compile(r"^(net\s+)?(profit|income|loss|\(loss\)|profit\s*/?\s*\(loss\)|\(loss\)\s*/?\s*profit)\s*(\(loss\)\s*)?(for\s+the\s+(current\s+)?(year|period))?\s*$|^(net\s+)?(loss|income|profit)\s+for\s+the\s+year", re.I), "is"),
}


@dataclass
class Fact:
    cur: float | None
    prev: float | None
    page: int
    label: str


@dataclass
class DebtLine:
    row: Row
    is_debt: bool
    reason: str
    check: bool


@dataclass
class ReportFacts:
    path: Path
    year: int
    unit: Unit | None
    bs_pages: list[int]
    is_pages: list[int]
    facts: dict[str, Fact] = field(default_factory=dict)
    liabilities: list[DebtLine] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: dict = field(default_factory=dict)

    def debt(self, col: str) -> tuple[float, list[DebtLine]]:
        lines = [d for d in self.liabilities if d.is_debt and getattr(d.row, col) not in (None, 0)]
        return sum(getattr(d.row, col) for d in lines), lines


_NI_CTX = re.compile(r"^(laba|rugi|\(rugi\)|laba\s*\(rugi\)|laba\s*/\s*\(rugi\))(\s+bersih)?$", re.I)


def _match_net_income(row: Row) -> bool:
    """Judul laba bersih yang terpotong dua baris: 'LABA' (konteks) + 'TAHUN BERJALAN' / 'FOR THE YEAR'."""
    lab = re.sub(r"\s+", " ", row.label).strip(" :")
    return bool(re.match(r"^(tahun|periode)\s+berjalan$", lab, re.I) and row.context and
                _NI_CTX.match(row.context[-1].strip()) and not re.search(r"kompreh", " ".join(row.context), re.I))


def _match(row: Row, ide, en) -> bool:
    lab = re.sub(r"\s+", " ", row.label).strip(" :")
    lab_en = re.sub(r"\s+", " ", row.label_en).strip(" :")
    full = re.sub(r"\s+", " ", row.full_label).strip(" :")
    return bool(ide.search(lab) or ide.search(full) or en.search(lab_en))


def extract_report(path, year: int, model=None) -> ReportFacts:
    """`path` boleh berupa satu file atau daftar file (laporan tahunan + laporan keuangan terpisah);
    file pertama yang memuat laporan posisi keuangan & laba rugi dipakai."""
    paths = list(path) if isinstance(path, (list, tuple)) else [path]
    first = None
    for p in paths:
        rf = _extract_one(Path(p), year, model)
        first = first or rf
        if rf.bs_pages and rf.is_pages:
            return rf
    return first


def _strategies(doc):
    """Cara menemukan laporan keuangan di dalam PDF, dari yang paling umum:
    (1) halaman penuh; (2) dua laporan berdampingan dalam satu halaman lanskap;
    (3) halaman lanskap dipecah kiri/kanan (spread)."""
    texts = page_texts(doc)
    bs, inc = find_statements(texts)
    if bs and inc:
        yield "halaman penuh", bs, inc, bs
        # halaman lanskap yang di sisi kanannya ada laporan lain (mis. perubahan ekuitas): ambil bagian kiri saja
        wid = lambda p: doc[p - 1].rect.width
        if all(wid(p) > doc[p - 1].rect.height * 1.3 for p in bs + inc):
            clip = lambda p: (p, (0.0, wid(p) * 0.62))
            yield "bagian kiri halaman lanskap", [clip(p) for p in bs], [clip(p) for p in inc], bs
    panel = find_panel_statements(doc)
    if panel:
        mid = doc[panel[0] - 1].rect.width / 2
        yield "dua laporan berdampingan", [(panel[0], (0.0, mid))], [(panel[0], (mid, doc[panel[0] - 1].rect.width))], [panel[0]]
    hp = half_pages(doc)
    h_texts = [t for _, _, t in hp]
    hbs, hinc = find_statements(h_texts)
    if hbs and hinc:
        pick = lambda idx: [(hp[i - 1][0], hp[i - 1][1]) if hp[i - 1][1] is not None else hp[i - 1][0] for i in idx]
        yield "halaman lanskap dipecah", pick(hbs), pick(hinc), [hp[hbs[0] - 1][0]]


def _score(rf: "ReportFacts") -> int:
    return len(rf.facts) * 10 + (5 if rf.unit else 0) + min(len(rf.liabilities), 5)


def _ocr_copy(path: Path, max_pages: int = 90) -> Path | None:
    """PDF yang halaman keuangannya berupa gambar (tanpa teks): halaman bergambar di separuh akhir
    dibaca dengan OCR (Tesseract) dan disimpan sebagai PDF bertulisan. None bila tidak perlu/tidak bisa."""
    try:
        import io
        import pytesseract
        from PIL import Image
    except ImportError:
        return None
    import hashlib, tempfile
    out = Path(tempfile.gettempdir()) / f"ocr_{hashlib.md5(str(path).encode()).hexdigest()[:10]}.pdf"
    if out.exists():
        return out
    src = pymupdf.open(path)
    n = len(src)
    todo = [i for i in range(n // 3, n) if len(src[i].get_text().strip()) < 150 and src[i].get_images()]
    if len(todo) < 5:
        return None
    dst = pymupdf.open()
    for i in range(n):
        pg = src[i]
        if i in todo[:max_pages]:
            pix = pg.get_pixmap(dpi=250)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            pdf = pytesseract.image_to_pdf_or_hocr(img, lang="eng", extension="pdf", config="--psm 6")
            one = pymupdf.open("pdf", pdf)
            dst.insert_pdf(one)
            # sesuaikan ukuran halaman hasil OCR dengan halaman asli agar koordinat sama
            new = dst[-1]
            new.set_mediabox(pymupdf.Rect(0, 0, new.rect.width, new.rect.height))
        else:
            dst.insert_pdf(src, from_page=i, to_page=i)
    dst.save(out)
    return out


def _extract_one(path: Path, year: int, model=None) -> ReportFacts:
    rf = _extract_doc(path, year, model)
    import os
    if len(rf.facts) < 5 and os.environ.get("RASIO_OCR") == "1":   # OCR lambat & kurang akurat: hanya bila diminta
        alt = _ocr_copy(path)
        if alt is not None:
            rf2 = _extract_doc(alt, year, model)
            if _score(rf2) > _score(rf):
                rf2.path = path
                rf2.warnings.append("Laporan keuangan berupa GAMBAR: dibaca dengan OCR - angka WAJIB dicek manual")
                return rf2
    return rf


def _extract_doc(path: Path, year: int, model=None) -> ReportFacts:
    doc = pymupdf.open(path)
    texts = page_texts(doc)
    results = []
    for name, bs_items, is_items, unit_pages in _strategies(doc):
        rf = _extract_pages(doc, texts, path, year, model, bs_items, is_items, unit_pages)
        results.append(rf)
        if len(rf.facts) >= 7 and rf.unit:
            break
    if not results:
        rf = ReportFacts(path, year, None, [], [])
        rf.warnings.append("Laporan posisi keuangan / laba rugi tidak ditemukan")
        return rf
    results.sort(key=_score, reverse=True)
    best = results[0]
    # pos yang belum terbaca pada hasil terbaik dilengkapi dari cara baca lain (mis. neraca dari satu cara, laba rugi dari cara lain)
    for other in results[1:]:
        for k, f in other.facts.items():
            if k not in best.facts:
                best.facts[k] = f
        if not best.liabilities and other.liabilities:
            best.liabilities, best.checks = other.liabilities, other.checks
        if best.unit is None:
            best.unit = other.unit
    best.warnings = [w for w in best.warnings if not any(
        f"'{k}' tidak ditemukan" in w for k in best.facts)]
    if "laba_bruto" in best.facts or "laba_usaha" in best.facts:
        best.warnings = [w for w in best.warnings if "EBIT" not in w]
    if best.unit is not None:
        best.warnings = [w for w in best.warnings if "Satuan nominal" not in w]
    return best


def _extract_pages(doc, texts, path, year, model, bs_items, is_items, unit_pages) -> ReportFacts:
    num = lambda items: [i[0] if isinstance(i, tuple) else i for i in items]
    bs, inc = num(bs_items), num(is_items)
    unit = detect_unit(" ".join(texts[p - 1] for p in unit_pages[:1])) if unit_pages else None
    if unit is None:
        unit = detect_unit(" ".join(texts[p - 1] for p in bs[:2]))
    rf = ReportFacts(path, year, unit, bs, inc)
    if unit is None:
        rf.warnings.append("Satuan nominal tidak terdeteksi")
    rows = {"bs": parse_pages(doc, bs_items), "is": parse_pages(doc, is_items)}
    for name, (ide, en, st) in METRICS.items():
        for r in rows[st]:
            if (r.cur is None and r.prev is None) or not (_match(r, ide, en) or (name == "laba_bersih" and _match_net_income(r))):
                continue
            if name == "pendapatan" and not r.cur and not r.prev:
                continue
            v = lambda x: abs(x) if (x is not None and name == "beban_keuangan") else x
            rf.facts[name] = Fact(v(r.cur), v(r.prev), r.page, r.full_label or r.label_en)
            break
    for r in rows["bs"]:
        if r.section in ("LJP", "LJPJ") and (r.cur or r.prev):
            if r.is_total or re.match(r"^(jumlah|total|sub\s*jumlah|subtotal|\(dipindahkan\)|dipindahkan|carried)", (r.label or r.label_en), re.I):
                continue
            is_debt, why, check = classify(r, model)
            rf.liabilities.append(DebtLine(r, is_debt, why, check))
    # pemeriksaan: jumlah pos liabilitas yang terbaca = "Jumlah liabilitas" di laporan
    for col in ("cur", "prev"):
        total = next((getattr(r, col) for r in rows["bs"] if r.is_total and getattr(r, col) and
                      re.match(r"^(jumlah|total)\s+liabilitas\s*$|^total\s+liabilities\s*$",
                               (r.label or r.label_en).strip(), re.I)), None)
        parsed = sum(getattr(d.row, col) or 0 for d in rf.liabilities)
        rf.checks[col] = (parsed, total)
        ta, eq = rf.facts.get("total_aset"), rf.facts.get("total_ekuitas")
        if total is not None and ta and eq and getattr(ta, col) is not None and getattr(eq, col) is not None:
            diff = getattr(ta, col) - (total + getattr(eq, col))
            if abs(diff) > max(2, abs(getattr(ta, col)) * 1e-6):
                rf.warnings.append(f"total aset != total liabilitas + total ekuitas (selisih {diff:,.0f}) - mohon dicek")
        if total is not None and abs(parsed - total) > max(2, abs(total) * 1e-6):
            rf.warnings.append(f"jumlah pos liabilitas terbaca ({parsed:,.0f}) != total liabilitas ({total:,.0f}) "
                               f"kolom {'tahun berjalan' if col == 'cur' else 'komparatif'} - mohon dicek")
    for k in METRICS:
        if k not in rf.facts and k not in ("laba_bruto", "laba_usaha"):
            rf.warnings.append(f"'{k}' tidak ditemukan")
    if "laba_bruto" not in rf.facts and "laba_usaha" not in rf.facts:
        rf.warnings.append("laba usaha / laba bruto (EBIT) tidak ditemukan")
    return rf
