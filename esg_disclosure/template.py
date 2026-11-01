"""Membaca struktur sheet ESGD (daftar item GRI) dari Excel DATA SKRIPSI.

Struktur yang diharapkan (sama seperti contoh DEWA):
  - Kolom A: No, Kolom B: Standar GRI, Kolom C: item GRI 2021 (mis. "2-1 Rincian organisasi"),
    Kolom D: item GRI 2016 pengganti (mis. "102-1 Name of the organization").
  - Baris 1: nama perusahaan (blok 5 kolom), baris 3: tahun.
  - Baris "RATA-RATA POIN PENGUNGKAPAN ESG": rumus skor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

from openpyxl.worksheet.worksheet import Worksheet

from .codes import TEMPLATE_CODE_RE

AVERAGE_LABEL = "RATA-RATA"


@dataclass
class TemplateRow:
    row: int
    section: str               # GOVERNANCE / ENVIRONMENTAL / SOCIAL
    code2021: str              # kode item GRI 2021 (kelompok), mis. "2-1" atau "305-1"
    title2021: str
    code2016: str | None       # kode GRI 2016 di kolom D (hanya governance), mis. "102-7-a-i"
    title2016: str | None


@dataclass
class Template:
    rows: list[TemplateRow]
    header_row: int            # baris nama perusahaan
    year_row: int              # baris tahun
    average_row: int
    first_data_col: int        # kolom pertama blok perusahaan pertama (E = 5)
    companies: dict[str, int] = field(default_factory=dict)   # kode -> kolom awal
    section_rows: list[int] = field(default_factory=list)     # baris judul bagian

    def groups(self) -> dict[str, list[TemplateRow]]:
        out: dict[str, list[TemplateRow]] = {}
        for r in self.rows:
            out.setdefault(r.code2021, []).append(r)
        return out


def _code(text) -> str | None:
    if not isinstance(text, str):
        return None
    m = TEMPLATE_CODE_RE.match(text.replace("\t", " "))
    return m.group(1) if m else None


def _clean(text) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def read_template(ws: Worksheet) -> Template:
    rows: list[TemplateRow] = []
    section = "GOVERNANCE"
    current = None  # (code2021, title2021)
    average_row = None
    year_row = None
    section_rows: list[int] = []
    for r in range(1, ws.max_row + 1):
        a, b, c, d = (ws.cell(r, k).value for k in range(1, 5))
        text_ab = f"{_clean(a)} {_clean(b)}".upper()
        if isinstance(a, str) and a.strip().upper().startswith(AVERAGE_LABEL):
            average_row = r
            break
        if "ENVIRONMENTAL" in text_ab:
            section, current = "ENVIRONMENTAL", None
        elif "SOCIAL" in text_ab:
            section, current = "SOCIAL", None
        elif "GOVERNANCE" in text_ab:
            section, current = "GOVERNANCE", None
        if year_row is None and isinstance(ws.cell(r, 5).value, int) and 1990 < ws.cell(r, 5).value < 2100:
            year_row = r
        c_code, d_code = _code(c), _code(d)
        if c_code:
            current = (c_code, _clean(c))
        elif not d_code:
            # baris judul bagian ("1. Organisasi ...", "DISCLOSURE GRI STANDARD 2021", "No")
            if a is not None or b is not None:
                current = None
                section_rows.append(r)
            continue
        if current is None:
            continue
        rows.append(TemplateRow(r, section, current[0], current[1], d_code, _clean(d) if d_code else None))
    if average_row is None:
        raise ValueError("Baris 'RATA-RATA POIN PENGUNGKAPAN ESG' tidak ditemukan di sheet ESGD")

    header_row = 1
    companies: dict[str, int] = {}
    col = 5
    while col <= ws.max_column:
        v = ws.cell(header_row, col).value
        if isinstance(v, str) and v.strip():
            companies[v.strip().upper()] = col
        col += 1
    return Template(rows, header_row, year_row or 3, average_row, 5, companies, section_rows)
