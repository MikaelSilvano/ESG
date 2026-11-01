"""Program utama. Contoh:

    python esg.py nilai  --laporan "SKRIPSI/LAPORAN KEBERLANJUTAN" --excel "SKRIPSI/DATA SKRIPSI.xlsx"
    python esg.py latih  --laporan "SKRIPSI/LAPORAN KEBERLANJUTAN" --excel "SKRIPSI/DATA SKRIPSI.xlsx"
    python esg.py uji    --laporan "SKRIPSI/LAPORAN KEBERLANJUTAN" --excel "SKRIPSI/DATA SKRIPSI.xlsx" --perusahaan DEWA
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

from . import model as ml
from .excel_writer import template_years, write_scores
from .reports import find_reports, load_report
from .scorer import DocumentAnalyzer, esg_score, score_document
from .template import read_template

SHEET = "ESGD"


def _log(msg: str) -> None:
    print(msg, flush=True)


def _open_template(excel: Path):
    if not excel.is_file():
        sys.exit(f"File Excel tidak ditemukan: {excel}\n"
                 f"Pastikan nama & lokasinya benar, atau tulis lokasinya dengan --excel \"...\"")
    wb = openpyxl.load_workbook(excel)
    if SHEET not in wb.sheetnames:
        sys.exit(f"Sheet '{SHEET}' tidak ditemukan di {excel}")
    ws = wb[SHEET]
    return wb, ws, read_template(ws)


def _analyze(paths, model, threshold):
    t0 = time.time()
    doc = load_report(paths)
    an = DocumentAnalyzer(doc, model=model, ml_threshold=threshold)
    chars = sum(len(p.text.strip()) for p in doc.pages)
    if chars < 200 * max(1, doc.page_count) * 0.2:
        _log("      [!] Teks PDF sangat sedikit - kemungkinan PDF hasil scan (gambar). Hasil bisa tidak akurat.")
    if not an.index.pages:
        _log("      [!] Tabel indeks GRI tidak terdeteksi - penilaian hanya dari tanda kode & ML.")
    std = "GRI 2021" if an.n_codes_2021 >= an.n_codes_2016 and an.n_codes_2021 else (
        "GRI 2016" if an.n_codes_2016 else "tanpa indeks GRI")
    _log(f"      {doc.page_count} halaman, indeks GRI di hal. PDF "
         f"{_ranges(an.index.pages) or '-'} ({std}), {time.time() - t0:.0f} dtk")
    return an


def _ranges(nums: list[int]) -> str:
    if not nums:
        return ""
    out, s, p = [], nums[0], nums[0]
    for n in nums[1:] + [None]:
        if n is not None and n == p + 1:
            p = n
            continue
        out.append(f"{s}-{p}" if s != p else f"{s}")
        if n is not None:
            s = p = n
    return ", ".join(out)


# ----------------------------------------------------------------------------- nilai
def cmd_nilai(a) -> None:
    excel, laporan = Path(a.excel), Path(a.laporan)
    out = Path(a.output) if a.output else Path("hasil") / f"{excel.stem} - HASIL.xlsx"
    wb, ws, t = _open_template(excel)
    years = template_years(ws, t)
    if not laporan.is_dir():
        sys.exit(f"Folder laporan tidak ditemukan: {laporan}")
    reports = find_reports(laporan)
    if not reports:
        sys.exit(f"Tidak ada folder perusahaan di {laporan}")
    targets = [c.upper() for c in a.perusahaan] if a.perusahaan else [
        c for c in reports if a.timpa or c not in t.companies]
    model, meta = (None, {}) if a.tanpa_ml else ml.load(Path(a.model))
    _log(f"Model ML: {'dipakai (dilatih dari ' + ', '.join(meta.get('perusahaan', [])) + ')' if model else 'tidak dipakai (ambang konservatif)'}")
    evidence_rows, summary = [], []
    for comp in targets:
        if comp in t.companies and not a.timpa and not a.perusahaan:
            continue
        if comp not in reports:
            _log(f"[!] {comp}: folder tidak ditemukan di {laporan}, dilewati")
            continue
        if not reports[comp]:
            _log(f"[!] {comp}: folder kosong (belum ada PDF) -> blok dibuat, kolom dibiarkan kosong")
        _log(f"== {comp}")
        for year in years:
            if year not in reports[comp]:
                _log(f"   {year}: PDF tidak ada -> kolom dibiarkan kosong")
                write_scores(ws, t, comp, year, {r.row: None for r in t.rows})
                summary.append((comp, year, None, "PDF tidak ada"))
                continue
            _log(f"   {year}: {', '.join(p.name for p in reports[comp][year])}")
            an = _analyze(reports[comp][year], model, a.ambang)
            res = score_document(an, t, year)
            write_scores(ws, t, comp, year, {r.row: r.score for r in res})
            sc = esg_score(res, t)
            n_ml = sum(1 for r in res if r.ml_disagrees)
            summary.append((comp, year, sc, f"{n_ml} baris: model ML tidak setuju dengan aturan (cek)" if n_ml else ""))
            _log(f"      skor ESG Disclosure = {sc:.4f}")
            for r in res:
                src = r.source + (" | ML tidak setuju - mohon dicek" if r.ml_disagrees else "")
                evidence_rows.append((comp, year, r.row, r.item, r.code_used, r.score, src))
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    bukti = out.with_name(f"BUKTI PENILAIAN - {excel.stem}.xlsx")
    _write_evidence(bukti, summary, evidence_rows)
    _log(f"\nSelesai.\n  Excel hasil : {out}\n  Bukti/audit : {bukti}")


def _write_evidence(path: Path, summary, rows) -> None:
    wb = openpyxl.Workbook()
    s = wb.active
    s.title = "RINGKASAN"
    s.append(["Kode", "Tahun", "Skor ESG Disclosure", "Catatan"])
    for comp, year, sc, note in summary:
        s.append([comp, year, round(sc, 4) if sc is not None else None, note])
    d = wb.create_sheet("DETAIL")
    d.append(["Kode", "Tahun", "Baris Excel", "Item GRI", "Kode yang dinilai", "Poin", "Sumber bukti"])
    yellow = PatternFill("solid", fgColor="FFF2CC")   # model ML tidak setuju dengan aturan -> mohon dicek
    orange = PatternFill("solid", fgColor="FCE4D6")   # di indeks tanpa halaman -> poin 0
    for row in rows:
        d.append(list(row))
        src = str(row[6])
        fill = yellow if "ML tidak setuju" in src else orange if src.startswith("Tercantum di indeks") else None
        if fill:
            for c in d[d.max_row]:
                c.fill = fill
    for ws, widths in ((s, [10, 8, 20, 40]), (d, [8, 8, 11, 70, 16, 6, 90])):
        for i, w in enumerate(widths):
            ws.column_dimensions[chr(65 + i)].width = w
        for c in ws[1]:
            c.font = Font(bold=True)
            c.alignment = Alignment(horizontal="center")
        ws.freeze_panes = "A2"
    wb.save(path)


# ----------------------------------------------------------------------------- latih / uji
def _labelled(a, companies):
    wb, ws, t = _open_template(Path(a.excel))
    years = template_years(ws, t)
    reports = find_reports(Path(a.laporan))
    for comp in companies:
        if comp not in t.companies:
            _log(f"[!] {comp} belum ada di Excel, dilewati")
            continue
        start = t.companies[comp]
        for i, year in enumerate(years):
            if year not in reports.get(comp, {}):
                continue
            gold = {r.row: ws.cell(r.row, start + i).value for r in t.rows}
            if all(v is None for v in gold.values()):
                continue
            yield comp, year, t, reports[comp][year], gold


def cmd_latih(a) -> None:
    wb, ws, t = _open_template(Path(a.excel))
    comps = [c.upper() for c in a.perusahaan] if a.perusahaan else list(t.companies)
    X, y, used = [], [], []
    for comp, year, t, paths, gold in _labelled(a, comps):
        _log(f"== {comp} {year}")
        an = _analyze(paths, None, 0.5)
        seen = set()
        for r in score_document(an, t, year):
            if r.evidence is None or gold.get(r.row) not in (0, 1):
                continue
            key = (r.code_used, gold[r.row])
            if key in seen:
                continue
            seen.add(key)
            X.append(r.evidence.features)
            y.append(int(gold[r.row]))
        used.append(f"{comp} {year}")
    if not X:
        sys.exit("Tidak ada data latih (perusahaan contoh belum punya PDF di folder laporan).")
    clf = ml.train(X, y)
    path = ml.save(clf, Path(a.model), {"perusahaan": sorted({u.split()[0] for u in used}), "dokumen": used,
                                        "jumlah_data": len(y)})
    _log(f"\nModel disimpan di {path} ({len(y)} data dari {len(used)} laporan)")


def cmd_uji(a) -> None:
    wb, ws, t = _open_template(Path(a.excel))
    comps = [c.upper() for c in a.perusahaan] if a.perusahaan else list(t.companies)
    model, _ = (None, {}) if a.tanpa_ml else ml.load(Path(a.model))
    tot = ok = 0
    for comp, year, t, paths, gold in _labelled(a, comps):
        _log(f"== {comp} {year}")
        an = _analyze(paths, model, a.ambang)
        res = score_document(an, t, year)
        diff = [r for r in res if gold.get(r.row) in (0, 1) and r.score != gold[r.row]]
        n = sum(1 for r in res if gold.get(r.row) in (0, 1))
        tot += n
        ok += n - len(diff)
        gold_score = esg_score([type(r)(r.row, r.item, r.code_used, int(gold[r.row] or 0), "") for r in res], t)
        _log(f"      cocok {n - len(diff)}/{n} baris | skor program {esg_score(res, t):.4f} vs manual {gold_score:.4f}")
        for r in diff:
            _log(f"        baris {r.row:3d} {r.code_used:8s} program={r.score} manual={gold[r.row]} | {r.source}")
    if tot:
        _log(f"\nAkurasi keseluruhan: {ok}/{tot} = {ok / tot:.1%}")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="esg.py", description="Penilaian skor ESG Disclosure (GRI) otomatis")
    sub = p.add_subparsers(dest="perintah", required=True)

    def common(sp):
        sp.add_argument("--laporan", default="SKRIPSI/LAPORAN KEBERLANJUTAN",
                        help="folder berisi subfolder per kode perusahaan (isi: 2020.pdf, 2021.pdf, ...)")
        sp.add_argument("--excel", default="SKRIPSI/DATA SKRIPSI.xlsx", help="file Excel DATA SKRIPSI (sheet ESGD)")
        sp.add_argument("--perusahaan", nargs="*", help="kode perusahaan tertentu, mis. DOID ITMG")
        sp.add_argument("--model", default=str(ml.DEFAULT_MODEL_PATH), help="lokasi file model ML")
        sp.add_argument("--ambang", type=float, default=0.5, help="ambang probabilitas ML (default 0.5)")
        sp.add_argument("--tanpa-ml", action="store_true", help="hanya aturan indeks GRI + tanda kode")

    sp = sub.add_parser("nilai", help="nilai laporan & isi Excel")
    common(sp)
    sp.add_argument("--output", help="file Excel hasil (default: hasil/<nama excel> - HASIL.xlsx)")
    sp.add_argument("--timpa", action="store_true", help="nilai ulang perusahaan yang sudah terisi di Excel")
    sp.set_defaults(func=cmd_nilai)

    sp = sub.add_parser("latih", help="latih model ML dari perusahaan yang sudah dinilai manual")
    common(sp)
    sp.set_defaults(func=cmd_latih)

    sp = sub.add_parser("uji", help="bandingkan hasil program dengan penilaian manual")
    common(sp)
    sp.set_defaults(func=cmd_uji)

    a = p.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
