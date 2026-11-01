"""Menulis hasil penilaian ke sheet ESGD dengan format yang sama seperti blok contoh (DEWA)."""
from __future__ import annotations

from copy import copy

from openpyxl.formula.translate import Translator
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from .template import Template

BLOCK_WIDTH = 5  # 5 tahun per perusahaan (2020-2024)


def template_years(ws: Worksheet, t: Template) -> list[int]:
    return [ws.cell(t.year_row, t.first_data_col + i).value for i in range(BLOCK_WIDTH)]


def ensure_company_block(ws: Worksheet, t: Template, company: str) -> int:
    """Kembalikan kolom awal blok perusahaan; buat blok baru (salin format DEWA) bila belum ada."""
    company = company.upper()
    if company in t.companies:
        return t.companies[company]
    start = max(t.companies.values(), default=t.first_data_col - BLOCK_WIDTH) + BLOCK_WIDTH
    src = t.first_data_col
    last_row = t.average_row

    # salin isi & format kolom dari blok contoh
    for off in range(BLOCK_WIDTH):
        sc, dc = src + off, start + off
        sl, dl = get_column_letter(sc), get_column_letter(dc)
        if ws.column_dimensions[sl].width:
            ws.column_dimensions[dl].width = ws.column_dimensions[sl].width
        for r in range(1, last_row + 1):
            s, d = ws.cell(r, sc), ws.cell(r, dc)
            if s.has_style:
                d.font, d.border, d.fill = copy(s.font), copy(s.border), copy(s.fill)
                d.number_format, d.alignment, d.protection = s.number_format, copy(s.alignment), copy(s.protection)
            if r == t.year_row:
                d.value = s.value
            elif r == last_row and isinstance(s.value, str) and s.value.startswith("="):
                d.value = Translator(s.value, origin=s.coordinate).translate_formula(d.coordinate)

    # salin merge cell di dalam blok contoh (judul perusahaan, baris judul bagian)
    src_last = src + BLOCK_WIDTH - 1
    for mr in list(ws.merged_cells.ranges):
        if mr.min_col >= src and mr.max_col <= src_last and mr.max_row <= last_row:
            shift = start - src
            ws.merge_cells(start_row=mr.min_row, end_row=mr.max_row,
                           start_column=mr.min_col + shift, end_column=mr.max_col + shift)
    ws.cell(t.header_row, start).value = company
    t.companies[company] = start
    return start


def write_scores(ws: Worksheet, t: Template, company: str, year: int, scores: dict[int, int | None]) -> None:
    start = ensure_company_block(ws, t, company)
    years = template_years(ws, t)
    if year not in years:
        raise ValueError(f"Tahun {year} tidak ada di template (tersedia: {years})")
    col = start + years.index(year)
    for row, val in scores.items():
        ws.cell(row, col).value = val
