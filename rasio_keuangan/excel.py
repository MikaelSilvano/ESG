"""Menulis hasil ke sheet 'CoD' dan 'Vab. X' (format mengikuti baris contoh DEWA)."""
from __future__ import annotations

from copy import copy

from openpyxl.styles import Font
from openpyxl.worksheet.worksheet import Worksheet

from .units import Unit

SHEET_COD, SHEET_VAB, SHEET_KURS = "CoD", "Vab. X", "kurs"


def read_kurs(ws: Worksheet) -> tuple[dict[int, float], dict[int, int]]:
    """{tahun: kurs}, {tahun: nomor baris} dari sheet kurs."""
    kurs, rows = {}, {}
    for r in range(1, ws.max_row + 1):
        for c in range(1, ws.max_column):
            y, k = ws.cell(r, c).value, ws.cell(r, c + 1).value
            if isinstance(y, int) and 1990 < y < 2100 and isinstance(k, (int, float)) and k > 1000:
                kurs[y], rows[y] = float(k), r
                kurs_col = c + 1
    return kurs, rows


def company_rows(ws: Worksheet, code: str) -> dict[int, int]:
    return {ws.cell(r, 2).value: r for r in range(2, ws.max_row + 1)
            if str(ws.cell(r, 1).value or "").strip().upper() == code}


def template_years(ws: Worksheet) -> list[int]:
    first = str(ws.cell(2, 1).value or "").strip().upper()
    return sorted(y for y, _ in company_rows(ws, first).items() if isinstance(y, int))


def last_row(ws: Worksheet) -> int:
    r = ws.max_row
    while r > 1 and all(ws.cell(r, c).value in (None, "") for c in range(1, 4)):
        r -= 1
    return r


def _style_row(ws: Worksheet, src: int, dst: int, ncol: int) -> None:
    for c in range(1, ncol + 1):
        s, d = ws.cell(src, c), ws.cell(dst, c)
        if s.has_style:
            d.font, d.border, d.fill = copy(s.font), copy(s.border), copy(s.fill)
            d.number_format, d.alignment = s.number_format, copy(s.alignment)


def num(v: float | None):
    if v is None:
        return None
    return int(round(v)) if abs(v - round(v)) < 1e-6 or abs(v) >= 1000 else round(v, 2)


def sum_formula(values: list[float]) -> str:
    vals = [num(v) for v in values if v]
    if not vals:
        return "=0"
    return "=" + "+".join(str(v) for v in vals).replace("+-", "-")


def total_asset_formula(row: int, unit: Unit, kurs_row: int | None) -> str:
    """Total aset dalam ribuan Rupiah (kolom D), mengikuti contoh DEWA."""
    c = f"C{row}"
    if unit.currency == "USD":
        k = f"kurs!C{kurs_row}"
        return {1: f"=({c}*{k})/10^3", 1000: f"={c}*{k}", 1_000_000: f"={c}*{k}*10^3"}[unit.scale]
    return {1: f"={c}/10^3", 1000: f"={c}", 1_000_000: f"={c}*10^3"}[unit.scale]


def ensure_note_header(ws: Worksheet, col: int, text: str = "Catatan") -> None:
    if not ws.cell(1, col).value:
        ws.cell(1, col).value = text
        ws.cell(1, col).font = Font(bold=True)
        ws.column_dimensions[ws.cell(1, col).column_letter].width = 60
