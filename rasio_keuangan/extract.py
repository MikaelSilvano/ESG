"""Mengambil angka-angka yang dibutuhkan dari satu laporan tahunan."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

import pymupdf

from .classify import classify
from .locate import find_statements, page_texts
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
    "laba_bersih": (re.compile(rf"^{PL}\s+(bersih\s+)?(tahun|periode)\s+(berjalan|ini)\s*$", re.I),
                    re.compile(r"^(net\s+)?(profit|income|loss|\(loss\)|profit\s*\(loss\))\s*(\(loss\)\s*)?for\s+the\s+(current\s+)?(year|period)\s*$", re.I), "is"),
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


def _match(row: Row, ide, en) -> bool:
    lab = re.sub(r"\s+", " ", row.label).strip(" :")
    lab_en = re.sub(r"\s+", " ", row.label_en).strip(" :")
    full = re.sub(r"\s+", " ", row.full_label).strip(" :")
    return bool(ide.search(lab) or ide.search(full) or en.search(lab_en))


def extract_report(path: Path, year: int, model=None) -> ReportFacts:
    doc = pymupdf.open(path)
    texts = page_texts(doc)
    bs, inc = find_statements(texts)
    unit = detect_unit(texts[bs[0] - 1]) if bs else None
    rf = ReportFacts(path, year, unit, bs, inc)
    if not bs or not inc:
        rf.warnings.append("Laporan posisi keuangan / laba rugi tidak ditemukan")
        return rf
    if unit is None:
        rf.warnings.append("Satuan nominal tidak terdeteksi")
    rows = {"bs": parse_pages(doc, bs), "is": parse_pages(doc, inc)}
    for name, (ide, en, st) in METRICS.items():
        for r in rows[st]:
            if (r.cur is None and r.prev is None) or not _match(r, ide, en):
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
