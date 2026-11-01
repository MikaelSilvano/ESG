"""Tes end-to-end kecil: PDF sintetis berisi tabel indeks GRI + template ESGD mini."""
from pathlib import Path

import openpyxl
import pymupdf
import pytest

from esg_disclosure.excel_writer import write_scores
from esg_disclosure.pdf_reader import read_pdf
from esg_disclosure.scorer import DocumentAnalyzer, esg_score, score_document
from esg_disclosure.template import read_template


def make_pdf(path: Path, index_rows, body_pages=()):
    doc = pymupdf.open()
    for text in body_pages:
        p = doc.new_page()
        p.insert_textbox(pymupdf.Rect(50, 80, 550, 780), text, fontsize=10)
    p = doc.new_page()
    p.insert_text((60, 60), "Indeks GRI Standards / GRI Content Index", fontsize=11)
    p.insert_text((60, 100), "No.", fontsize=9)
    p.insert_text((150, 100), "Judul", fontsize=9)
    p.insert_text((470, 100), "Halaman", fontsize=9)
    y = 130
    for code, title, page in index_rows:
        p.insert_text((60, y), code, fontsize=9)
        p.insert_text((150, y), title, fontsize=9)
        if page:
            p.insert_text((475, y), page, fontsize=9)
        y += 22
    doc.save(path)


def make_template(path: Path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ESGD"
    ws["A1"], ws["D1"], ws["E1"] = "DISCLOSURE GRI STANDARD 2021", "DISCLOSURE GRI STANDARD 2016", "DEWA"
    ws["A3"], ws["B3"] = "No", "GOVERNANCE (GENERAL DISCLOSURES)"
    for i, y in enumerate([2020, 2021, 2022, 2023, 2024]):
        ws.cell(3, 5 + i).value = y
    ws["A4"] = "1. Organisasi"
    rows = [
        (1, "GRI 2", "2-1 Rincian organisasi", "102-1 Name of the organization"),
        (None, None, None, "102-3 Location of headquarters"),
        (2, None, "2-7 Tenaga kerja", "102-7-a-i Scale of the organization (total employees)"),
        (None, None, None, "102-8 Information on employees"),
    ]
    r = 5
    for a, b, c, d in rows:
        ws.cell(r, 1).value, ws.cell(r, 2).value, ws.cell(r, 3).value, ws.cell(r, 4).value = a, b, c, d
        r += 1
    ws.cell(r, 1).value, ws.cell(r, 2).value = "No", "ENVIRONMENTAL (MATERIAL TOPICS)"
    r += 1
    ws.cell(r, 1).value, ws.cell(r, 2).value, ws.cell(r, 3).value = 1, "GRI 305", "305-1 Emisi GRK (Cakupan 1)"
    r += 1
    ws.cell(r, 1).value, ws.cell(r, 3).value = 2, "305-6 Emisi zat perusak ozon"
    r += 1
    ws.cell(r, 1).value = "RATA-RATA POIN PENGUNGKAPAN ESG"
    ws.cell(r, 5).value = "=AVERAGE(AVERAGE(E5:E6),AVERAGE(E7:E8),E10:E11)"
    wb.save(path)


@pytest.fixture()
def tmpl(tmp_path):
    p = tmp_path / "DATA SKRIPSI.xlsx"
    make_template(p)
    wb = openpyxl.load_workbook(p)
    return wb, wb["ESGD"], read_template(wb["ESGD"])


def test_template(tmpl):
    _, _, t = tmpl
    assert [r.code2016 for r in t.rows[:4]] == ["102-1", "102-3", "102-7-a-i", "102-8"]
    assert [r.code2021 for r in t.rows] == ["2-1", "2-1", "2-7", "2-7", "305-1", "305-6"]
    assert t.companies == {"DEWA": 5}


def test_gri2016_report(tmp_path, tmpl):
    wb, ws, t = tmpl
    pdf = tmp_path / "2020.pdf"
    make_pdf(pdf, [("102-1", "Nama organisasi", "12"), ("102-3", "Lokasi kantor pusat", ""),
                   ("102-7", "Skala organisasi", "20, 21"), ("305-1", "Emisi langsung", "45"),
                   ("305-6", "Emisi ODS", "Tidak relevan")],
             body_pages=["Informasi karyawan (102-8) jumlah karyawan tetap dan kontrak."])
    an = DocumentAnalyzer(read_pdf(pdf))
    res = {r.row: r.score for r in score_document(an, t, 2020)}
    # 102-1 ada halaman; 102-3 tanpa halaman; 102-7-a-i ikut 102-7; 102-8 dari tanda kode di isi
    assert [res[5], res[6], res[7], res[8], res[10], res[11]] == [1, 0, 1, 1, 1, 0]


def test_gri2021_report_group_scoring(tmp_path, tmpl):
    wb, ws, t = tmpl
    pdf = tmp_path / "2023.pdf"
    make_pdf(pdf, [("2-1", "Rincian organisasi", "8"), ("2-6", "Aktivitas", "9"), ("2-7", "Karyawan", ""),
                   ("2-9", "Struktur tata kelola", "30"), ("305-1", "Emisi langsung", "45")])
    an = DocumentAnalyzer(read_pdf(pdf))
    res = score_document(an, t, 2023)
    by_row = {r.row: r.score for r in res}
    # semua baris 2-1 bernilai sama (1), semua baris 2-7 sama (0)
    assert [by_row[5], by_row[6], by_row[7], by_row[8]] == [1, 1, 0, 0]
    assert esg_score(res, t) == pytest.approx((1 + 0 + 1 + 0) / 4)

    write_scores(ws, t, "ABCD", 2023, by_row)
    assert ws.cell(1, 10).value == "ABCD"
    assert ws.cell(5, 13).value == 1
    assert ws.cell(t.average_row, 10).value.startswith("=AVERAGE(AVERAGE(J5:J6)")
