"""Program utama rasio keuangan. Contoh:

    python3 rasio.py isi    --laporan "SKRIPSI/LAPORAN TAHUNAN" --excel "SKRIPSI/RATIO DATA SKRIPSI.xlsx"
    python3 rasio.py latih  --laporan "SKRIPSI/LAPORAN TAHUNAN" --excel "SKRIPSI/RATIO DATA SKRIPSI.xlsx"
    python3 rasio.py uji    --laporan "SKRIPSI/LAPORAN TAHUNAN" --excel "SKRIPSI/RATIO DATA SKRIPSI.xlsx"
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

from esg_disclosure.reports import find_reports

from . import classify as clf
from .dataset import CompanyData
from .excel import (SHEET_COD, SHEET_KURS, SHEET_VAB, company_rows, ensure_note_header, last_row,
                    num, read_kurs, sum_formula, template_years, total_asset_formula, _style_row)
from .extract import extract_report


def _log(m: str) -> None:
    print(m, flush=True)


def _open(excel: Path):
    if not excel.is_file():
        sys.exit(f"File Excel tidak ditemukan: {excel}")
    wb = openpyxl.load_workbook(excel)
    for s in (SHEET_COD, SHEET_VAB, SHEET_KURS):
        if s not in wb.sheetnames:
            sys.exit(f"Sheet '{s}' tidak ditemukan di {excel}")
    return wb


def _fmt(v) -> str:
    return "-" if v is None else f"{v:,.0f}"


# ============================================================================ isi
def cmd_isi(a) -> None:
    excel, laporan = Path(a.excel), Path(a.laporan)
    out = Path(a.output) if a.output else Path("hasil") / f"{excel.stem} - HASIL.xlsx"
    if not laporan.is_dir():
        sys.exit(f"Folder laporan tahunan tidak ditemukan: {laporan}")
    wb = _open(excel)
    wc, wv = wb[SHEET_COD], wb[SHEET_VAB]
    kurs, kurs_rows = read_kurs(wb[SHEET_KURS])
    vab_years, cod_years = template_years(wv), template_years(wc)
    reports = find_reports(laporan)
    first = str(wv.cell(2, 1).value or "").strip().upper()
    targets = [c.upper() for c in a.perusahaan] if a.perusahaan else [
        c for c in reports if a.timpa or not company_rows(wv, c)]
    model = None if a.tanpa_ml else clf.load(Path(a.model))
    _log(f"Model ML utang berbunga: {'dipakai' if model else 'tidak dipakai'} | "
         f"tahun Vab. X: {vab_years} | tahun CoD: {cod_years}")
    ensure_note_header(wv, 16)
    ensure_note_header(wc, 8)
    ev_data, ev_debt, ev_check = [], [], []

    for code in targets:
        if code not in reports or not reports[code]:
            _log(f"[!] {code}: folder/PDF laporan tahunan tidak ada, dilewati")
            continue
        if company_rows(wv, code) and not a.timpa and not a.perusahaan:
            continue
        _log(f"== {code}")
        cd = CompanyData(code, reports[code], kurs, model)
        for y, rep in sorted(cd.reports.items()):
            _log(f"   LT {y}: neraca hal. {rep.bs_pages}, laba rugi hal. {rep.is_pages}, satuan "
                 f"{rep.unit.label if rep.unit else '?'}" + (f"  [!] {'; '.join(rep.warnings)}" if rep.warnings else ""))
        unit = cd.unit
        if unit is None:
            _log("   [!] satuan tidak terdeteksi, dilewati")
            continue

        # ---------------------------------------------------------- Vab. X
        rows = company_rows(wv, code)
        nxt = last_row(wv) + 1
        vab_row_of: dict[int, int] = {}
        for y in vab_years:
            r = rows.get(y) or nxt
            if r == nxt:
                nxt += 1
            vab_row_of[y] = r
            _style_row(wv, 2, r, 16)
            ta, sales, ni, eq = (cd.value(m, y) for m in ("total_aset", "pendapatan", "laba_bersih", "total_ekuitas"))
            ebit, ebit_name = cd.ebit(y)
            ie = cd.interest(y)
            vals = {"C": ta, "E": sales, "H": ni, "J": eq, "L": ebit, "M": ie}
            wv.cell(r, 1).value, wv.cell(r, 2).value = code, y
            for col, v in vals.items():
                wv[f"{col}{r}"].value = num(v.value) if v else None
            wv[f"D{r}"].value = total_asset_formula(r, unit, kurs_rows.get(y))
            wv[f"F{r}"].value = f"=C{r}/E{r}"
            wv[f"G{r}"].value = f"=LN(D{r})"
            wv[f"I{r}"].value = f"=H{r}/C{r}"
            wv[f"K{r}"].value = f"=C{r}/J{r}"
            wv[f"N{r}"].value = f"=L{r}/M{r}"
            wv[f"O{r}"].value = unit.label
            srcs = sorted({v.source_year for v in vals.values() if v})
            notes = [f"Sumber: LT {', '.join(map(str, srcs))}" + (" (angka komparatif LT tahun berikutnya = data terbaru)" if any(s > y for s in srcs) else "")]
            notes.append(f"EBIT = {ebit_name}" if ebit_name else "EBIT tidak ditemukan")
            conv = {v.note for v in vals.values() if v and v.note}
            notes += sorted(conv)
            missing = [n for n, v in zip(("Total aset", "Penjualan", "Laba bersih", "Ekuitas", "EBIT", "Beban keuangan"),
                                         (ta, sales, ni, eq, ebit, ie)) if v is None]
            if missing:
                notes.append("TIDAK DITEMUKAN: " + ", ".join(missing))
                ev_check.append((code, y, "Vab. X", "Tidak ditemukan: " + ", ".join(missing)))
            wv[f"P{r}"].value = "; ".join(notes)
            for name, v in (("Total aset", ta), ("Penjualan/pendapatan", sales), ("Laba tahun berjalan", ni),
                            ("Total ekuitas", eq), (f"EBIT ({ebit_name})", ebit), ("Beban keuangan", ie)):
                if v:
                    ev_data.append((code, y, name, v.value, unit.label, v.source_year, "tahun berjalan" if v.column == "cur" else "komparatif",
                                    v.page, v.label, v.note))
            _log(f"   {y}: aset {_fmt(ta and ta.value)} | penjualan {_fmt(sales and sales.value)} | laba {_fmt(ni and ni.value)} | "
                 f"ekuitas {_fmt(eq and eq.value)} | EBIT {_fmt(ebit and ebit.value)} | beban keuangan {_fmt(ie and ie.value)}")

        # ---------------------------------------------------------- CoD
        rows = company_rows(wc, code)
        nxt = last_row(wc) + 1
        for y in cod_years:
            r = rows.get(y) or nxt
            if r == nxt:
                nxt += 1
            _style_row(wc, 2, r, 8)
            ie = cd.interest(y)
            d_t, d_p = cd.debt(y), cd.debt_prev(y)
            wc.cell(r, 1).value, wc.cell(r, 2).value = code, y
            if y in vab_row_of:
                wc[f"C{r}"].value = f"='{SHEET_VAB}'!M{vab_row_of[y]}"
            else:
                wc[f"C{r}"].value = num(ie.value) if ie else None
            wc[f"D{r}"].value = sum_formula([v for _, v in d_t.lines]) if d_t else None
            wc[f"E{r}"].value = sum_formula([v for _, v in d_p.lines]) if d_p else None
            wc[f"F{r}"].value = f"=AVERAGE(D{r}:E{r})"
            wc[f"G{r}"].value = f"=C{r}/F{r}"
            notes = [f"Satuan: {unit.label}"]
            for tag, d in (("Utang t", d_t), ("Utang t-1", d_p)):
                if d:
                    notes.append(f"{tag}: LT {d.source_year} hal. {d.page} ({'komparatif' if d.column == 'prev' else 'tahun berjalan'}) = "
                                 + " + ".join(lab for lab, _ in d.lines))
                    if d.note:
                        notes.append(d.note)
                    for lab, v in d.lines:
                        ev_debt.append((code, y, tag, d.source_year, d.page, lab, v, "MASUK", ""))
                    for lab, v, why in d.excluded:
                        ev_debt.append((code, y, tag, d.source_year, d.page, lab, v, "tidak", why))
                    for c in d.to_check:
                        ev_check.append((code, y, f"CoD {tag}", c))
                else:
                    notes.append(f"{tag}: TIDAK DITEMUKAN")
            if ie:
                notes.append(f"Beban keuangan: LT {ie.source_year} hal. {ie.page}")
                if ie.note:
                    notes.append(ie.note)
            wc[f"H{r}"].value = "; ".join(notes)
            _log(f"   CoD {y}: beban keuangan {_fmt(ie and ie.value)} | utang t {_fmt(d_t and d_t.total)} | "
                 f"utang t-1 {_fmt(d_p and d_p.total)}")
        if cd.notes:
            _log("   catatan: " + "; ".join(cd.notes))

    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    bukti = out.with_name(f"BUKTI RASIO - {excel.stem}.xlsx")
    _write_evidence(bukti, ev_data, ev_debt, ev_check)
    _log(f"\nSelesai.\n  Excel hasil : {out}\n  Bukti/audit : {bukti}")


def _write_evidence(path: Path, data, debt, check) -> None:
    wb = openpyxl.Workbook()
    sheets = [("DATA", ["Kode", "Tahun", "Pos", "Nilai", "Satuan", "Sumber LT", "Kolom", "Hal. PDF", "Label di laporan", "Catatan"], data,
               [7, 7, 24, 18, 14, 10, 14, 8, 50, 40]),
              ("UTANG BERBUNGA", ["Kode", "Tahun CoD", "Utang", "Sumber LT", "Hal. PDF", "Pos liabilitas", "Nilai", "Utang berbunga?", "Alasan"], debt,
               [7, 9, 10, 10, 8, 60, 18, 14, 60]),
              ("CEK MANUAL", ["Kode", "Tahun", "Bagian", "Keterangan"], check, [7, 7, 14, 120])]
    for i, (name, head, rows, widths) in enumerate(sheets):
        ws = wb.active if i == 0 else wb.create_sheet()
        ws.title = name
        ws.append(head)
        for r in rows:
            ws.append(list(r))
        for j, w in enumerate(widths):
            ws.column_dimensions[chr(65 + j)].width = w
        for c in ws[1]:
            c.font = Font(bold=True)
            c.alignment = Alignment(horizontal="center")
        ws.freeze_panes = "A2"
        if name == "UTANG BERBUNGA":
            green = PatternFill("solid", fgColor="E2EFDA")
            for row in ws.iter_rows(min_row=2):
                if row[7].value == "MASUK":
                    for c in row:
                        c.fill = green
    wb.save(path)


# ============================================================================ latih / uji
FORMULA_NUM = re.compile(r"\d{4,}")


def _example_components(ws, code: str) -> dict[int, set[int]]:
    """Angka-angka komponen utang pada rumus contoh CoD (kolom D & E) per tahun."""
    out: dict[int, set[int]] = {}
    for y, r in company_rows(ws, code).items():
        for col, yy in (("D", y), ("E", y - 1)):
            v = ws[f"{col}{r}"].value
            if isinstance(v, str) and v.startswith("="):
                nums = {int(n) for n in FORMULA_NUM.findall(v.split("*kurs")[0]) if not (1990 < int(n) < 2100)}
                if nums:
                    out.setdefault(yy, set()).update(nums)
    return out


def cmd_latih(a) -> None:
    wb = _open(Path(a.excel))
    wc = wb[SHEET_COD]
    reports = find_reports(Path(a.laporan))
    comps = [c.upper() for c in a.perusahaan] if a.perusahaan else [str(wc.cell(2, 1).value).upper()]
    X, y = [], []
    for code in comps:
        ex = _example_components(wc, code)
        if not ex or code not in reports:
            _log(f"[!] {code}: tidak ada contoh CoD/laporan, dilewati")
            continue
        for year, paths in sorted(reports[code].items()):
            rep = extract_report(paths[0], year)
            n_pos = 0
            for d in rep.liabilities:
                vals = {round(abs(v)) for v in (d.row.cur, d.row.prev) if v}
                pos_years = [yy for yy in (year, year - 1) if yy in ex]
                if not pos_years:
                    continue
                target = set().union(*(ex[yy] for yy in pos_years))
                hit = any(v in target or v + 1 in target or v - 1 in target for v in vals)
                X.append(f"{d.row.full_label} {d.row.label_en}")
                y.append(1 if hit else 0)
                n_pos += hit
            _log(f"   {code} LT {year}: {len(rep.liabilities)} pos liabilitas, {n_pos} cocok dengan contoh utang berbunga")
    model, n = clf.train(X, y)
    p = clf.save(model, n, {"perusahaan": comps})
    _log(f"\nModel ML utang berbunga disimpan: {p} ({n} contoh; {len(X)} dari laporan contoh)")


def cmd_uji(a) -> None:
    wb = openpyxl.load_workbook(Path(a.excel), data_only=False)
    wv, wc = wb[SHEET_VAB], wb[SHEET_COD]
    kurs, _ = read_kurs(wb[SHEET_KURS])
    reports = find_reports(Path(a.laporan))
    model = None if a.tanpa_ml else clf.load(Path(a.model))
    comps = [c.upper() for c in a.perusahaan] if a.perusahaan else [str(wv.cell(2, 1).value).upper()]
    tot = ok = 0
    for code in comps:
        cd = CompanyData(code, reports[code], kurs, model, harmonize=False)
        _log(f"== {code} (Vab. X: nilai contoh vs program, satuan asli laporan)")
        for y, r in sorted(company_rows(wv, code).items()):
            for col, metric in (("C", "total_aset"), ("E", "pendapatan"), ("H", "laba_bersih"), ("J", "total_ekuitas"),
                                ("L", "ebit"), ("M", "beban_keuangan")):
                gold = wv[f"{col}{r}"].value
                if not isinstance(gold, (int, float)):
                    continue
                v = cd.ebit(y)[0] if metric == "ebit" else cd.value(metric, y)
                got = v.value if v else None
                same = got is not None and abs(got - gold) <= max(2, abs(gold) * 1e-6)
                tot += 1
                ok += same
                if not same:
                    _log(f"   {y} {metric:15s} contoh={gold:>18,.0f} program={_fmt(got):>18} (LT {v.source_year if v else '-'})")
        ex = _example_components(wc, code)
        _log(f"== {code} (CoD: total utang berbunga contoh vs program)")
        for y, nums in sorted(ex.items()):
            d = cd.debt(y)
            got = round(d.total) if d else None
            gold = sum(nums)
            same = got is not None and abs(got - gold) <= 3
            tot += 1
            ok += same
            _log(f"   utang {y}: contoh={gold:>16,} program={_fmt(got):>16} {'OK' if same else 'BEDA'}"
                 + ("" if same or not d else f" (LT {d.source_year})"))
    _log(f"\nKecocokan: {ok}/{tot}")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="rasio.py", description="Ekstraksi data & rasio keuangan dari laporan tahunan (PDF)")
    sub = p.add_subparsers(dest="perintah", required=True)

    def common(sp):
        sp.add_argument("--laporan", default="SKRIPSI/LAPORAN TAHUNAN", help="folder berisi subfolder per kode perusahaan")
        sp.add_argument("--excel", default="SKRIPSI/RATIO DATA SKRIPSI.xlsx", help="Excel RATIO DATA SKRIPSI")
        sp.add_argument("--perusahaan", nargs="*", help="kode perusahaan tertentu")
        sp.add_argument("--model", default=str(clf.MODEL_PATH), help="file model ML utang berbunga")
        sp.add_argument("--tanpa-ml", action="store_true", help="hanya aturan (tanpa model ML)")

    sp = sub.add_parser("isi", help="ekstrak angka & isi sheet CoD dan Vab. X")
    common(sp)
    sp.add_argument("--output", help="file hasil (default: hasil/<nama excel> - HASIL.xlsx)")
    sp.add_argument("--timpa", action="store_true", help="isi ulang perusahaan yang sudah ada")
    sp.set_defaults(func=cmd_isi)
    sp = sub.add_parser("latih", help="latih model ML utang berbunga dari contoh (DEWA)")
    common(sp)
    sp.set_defaults(func=cmd_latih)
    sp = sub.add_parser("uji", help="bandingkan hasil program dengan contoh di Excel")
    common(sp)
    sp.set_defaults(func=cmd_uji)
    a = p.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
