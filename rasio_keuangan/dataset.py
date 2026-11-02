"""Menggabungkan angka dari beberapa laporan tahunan satu perusahaan.

Aturan "ikuti data terbaru": nilai tahun Y diambil dari kolom komparatif laporan tahun Y+1
(bila ada, karena bisa memuat koreksi/penyajian kembali); bila tidak ada, dari laporan tahun Y.
Semua nilai satu perusahaan diseragamkan ke satu satuan & mata uang (satuan laporan terbaru).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .extract import DebtLine, ReportFacts, extract_report
from .units import Unit, convert


@dataclass
class Value:
    value: float | None
    source_year: int          # laporan tahunan sumber
    column: str               # "cur" / "prev"
    page: int
    label: str
    note: str = ""


@dataclass
class DebtValue:
    total: float
    lines: list[tuple[str, float]]     # (label, nilai) komponen utang berbunga
    source_year: int
    column: str
    page: int
    note: str = ""
    excluded: list[tuple[str, float, str]] = field(default_factory=list)
    to_check: list[str] = field(default_factory=list)


class CompanyData:
    def __init__(self, code: str, files: dict[int, list[Path]], kurs: dict[int, float], model=None,
                 harmonize: bool = True):
        self.code = code
        self.harmonize = harmonize
        self.kurs = kurs
        self.reports: dict[int, ReportFacts] = {}
        for y, paths in sorted(files.items()):
            self.reports[y] = extract_report(paths[0], y, model)
        units = [r.unit for _, r in sorted(self.reports.items()) if r.unit]
        self.unit: Unit | None = units[-1] if units else None   # satuan laporan terbaru
        self.notes: list[str] = []
        if len(set(units)) > 1:
            self.notes.append("Satuan/mata uang berbeda antar laporan: " +
                              ", ".join(f"LT {y}={r.unit.label}" for y, r in sorted(self.reports.items()) if r.unit) +
                              f"; diseragamkan ke {self.unit.label}")

    # ------------------------------------------------------------------ util
    def _conv(self, v: float | None, rep: ReportFacts, value_year: int) -> tuple[float | None, str]:
        if v is None or rep.unit is None or self.unit is None or rep.unit == self.unit or not self.harmonize:
            return v, ""
        kurs = self.kurs.get(value_year)
        out = convert(v, rep.unit, self.unit, kurs)
        note = f"dikonversi dari {rep.unit.label} ke {self.unit.label}"
        if rep.unit.currency != self.unit.currency:
            note += f" (kurs {value_year} = {kurs:,.0f})"
        return out, note

    def _sources(self, year: int) -> list[tuple[ReportFacts, str]]:
        """Urutan sumber untuk nilai tahun `year`: laporan Y+1 (komparatif) lalu laporan Y."""
        out = []
        if year + 1 in self.reports:
            out.append((self.reports[year + 1], "prev"))
        if year in self.reports:
            out.append((self.reports[year], "cur"))
        return out

    # ------------------------------------------------------------------ angka
    def value(self, metric: str, year: int) -> Value | None:
        for rep, col in self._sources(year):
            f = rep.facts.get(metric)
            if f is None or getattr(f, col) is None:
                continue
            v, note = self._conv(getattr(f, col), rep, year)
            return Value(v, rep.year, col, f.page, f.label, note)
        return None

    def ebit(self, year: int) -> tuple[Value | None, str]:
        """EBIT = laba usaha bila disajikan; bila tidak, laba bruto (sesuai contoh DEWA)."""
        for rep, col in self._sources(year):
            for metric, name in (("laba_usaha", "Laba usaha"), ("laba_bruto", "Laba bruto")):
                f = rep.facts.get(metric)
                if f is not None and getattr(f, col) is not None:
                    v, note = self._conv(getattr(f, col), rep, year)
                    return Value(v, rep.year, col, f.page, f.label, note), name
        return None, ""

    def debt(self, year: int, sources: list[tuple[ReportFacts, str]] | None = None) -> DebtValue | None:
        for rep, col in (sources or self._sources(year)):
            if not rep.liabilities:
                continue
            lines: list[DebtLine] = [d for d in rep.liabilities if getattr(d.row, col) not in (None, 0)]
            if not lines:
                continue
            note = ""
            comps, excl, check = [], [], []
            for d in lines:
                v, note_c = self._conv(getattr(d.row, col), rep, year)
                note = note or note_c
                lab = d.row.full_label or d.row.label_en
                if d.is_debt:
                    comps.append((lab, v))
                else:
                    excl.append((lab, v, d.reason))
                if d.check:
                    check.append(f"{lab} ({'masuk' if d.is_debt else 'tidak masuk'}: {d.reason})")
            page = lines[0].row.page
            return DebtValue(sum(v for _, v in comps), comps, rep.year, col, page, note, excl, check)
        return None

    def debt_prev(self, year: int) -> DebtValue | None:
        """Utang tahun t-1 untuk CoD tahun t: data terbaru = kolom komparatif laporan tahun t."""
        if year in self.reports:
            d = self.debt(year - 1, [(self.reports[year], "prev")])
            if d:
                return d
        return self.debt(year - 1)

    def interest(self, year: int) -> Value | None:
        return self.value("beban_keuangan", year)
