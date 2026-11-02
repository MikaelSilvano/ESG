"""Tes unit untuk paket rasio_keuangan (tanpa PDF asli)."""
import pymupdf
import pytest

from rasio_keuangan.classify import rule
from rasio_keuangan.excel import sum_formula, total_asset_formula
from rasio_keuangan.parser import Row, parse_amount, parse_pages
from rasio_keuangan.units import Unit, convert, detect_unit


def row(label, section="LJP", sub="", ctx=None, en=""):
    return Row(1, label, en, ctx or [], 1.0, 1.0, section, sub)


def test_parse_amount():
    assert parse_amount("1,234,567") == 1234567
    assert parse_amount("1.234.567") == 1234567
    assert parse_amount("(85,149,412)") == -85149412
    assert parse_amount("-") == 0
    assert parse_amount("--") == 0


def test_units():
    assert detect_unit("(Disajikan dalam Jutaan Rupiah, kecuali dinyatakan lain)") == Unit("IDR", 1_000_000)
    assert detect_unit("(Dinyatakan dalam ribuan Dolar AS, kecuali nilai nominal)") == Unit("USD", 1000)
    assert detect_unit("(Dalam Dolar Amerika Serikat, kecuali dinyatakan lain)") == Unit("USD", 1)
    assert detect_unit("(Disajikan Dalam Ribuan Rupiah, kecuali dinyatakan lain)") == Unit("IDR", 1000)
    # 1.000 dolar AS (ribuan) x kurs 15.000 = 15.000.000 Rupiah = 15.000 ribuan Rupiah
    assert convert(1, Unit("USD", 1000), Unit("IDR", 1000), 15000) == pytest.approx(15000)
    assert convert(2, Unit("IDR", 1_000_000), Unit("IDR", 1000), None) == 2000


@pytest.mark.parametrize("label,sec,sub,expected", [
    ("Utang bank", "LJP", "jatuh tempo satu tahun", True),
    ("Pinjaman bank jangka pendek", "LJP", "", True),
    ("Liabilitas sewa", "LJPJ", "", True),
    ("Utang sewa pembiayaan", "LJPJ", "", True),
    ("Utang obligasi - bersih", "LJPJ", "", True),
    ("Senior Notes", "LJPJ", "", True),
    ("Utang Lain-lain - Pihak Ketiga", "LJP", "jatuh tempo satu tahun", True),
    ("Utang Lain-lain - Pihak Ketiga", "LJPJ", "", True),
    ("Utang lain-lain - Pihak ketiga", "LJP", "", False),   # utang lain-lain operasional
    ("Utang usaha - Pihak ketiga", "LJP", "", False),
    ("Utang pajak", "LJP", "", False),
    ("Pendapatan diterima di muka", "LJP", "", False),
    ("Uang muka pelanggan", "LJP", "", False),
    ("Utang pihak berelasi", "LJPJ", "", False),
    ("Liabilitas pajak tangguhan", "LJPJ", "", False),
    ("Liabilitas imbalan pascakerja", "LJPJ", "", False),
    ("Beban akrual", "LJP", "", False),
])
def test_interest_bearing_rules(label, sec, sub, expected):
    assert rule(row(label, sec, sub))[0] is expected


def test_excel_formulas():
    assert sum_formula([10, 20.0, 0, 5]) == "=10+20+5"
    assert total_asset_formula(3, Unit("USD", 1), 8) == "=(C3*kurs!C8)/10^3"
    assert total_asset_formula(3, Unit("USD", 1000), 8) == "=C3*kurs!C8"
    assert total_asset_formula(3, Unit("IDR", 1000), 8) == "=C3"
    assert total_asset_formula(3, Unit("IDR", 1_000_000), 8) == "=C3*10^3"


def test_parse_statement_page(tmp_path):
    """Halaman neraca sintetis: label, kolom catatan, 2 kolom angka, bagian liabilitas."""
    doc = pymupdf.open()
    p = doc.new_page()
    put = lambda x, y, t: p.insert_text((x, y), t, fontsize=8)
    put(60, 60, "LAPORAN POSISI KEUANGAN KONSOLIDASIAN")
    put(200, 90, "Catatan/"), put(270, 90, "2024"), put(350, 90, "2023")
    lines = [("LIABILITAS JANGKA PENDEK", None, None), ("Utang usaha", "1.000", "900"),
             ("Utang bank", "2.500", "3.000"), ("Liabilitas sewa", "(300)", "-"),
             ("Jumlah Liabilitas Jangka Pendek", "3.200", "3.900"),
             ("LIABILITAS JANGKA PANJANG", None, None), ("Utang bank", "4.000", "5.000"),
             ("Liabilitas imbalan kerja", "700", "650"), ("Jumlah Liabilitas Jangka Panjang", "4.700", "5.650")]
    y = 110
    for lab, a, b in lines:
        put(60, y, lab)
        if a:
            put(300 - len(a) * 4, y, a), put(380 - len(b) * 4, y, b)
        y += 14
    rows = parse_pages(doc, [1])
    got = {(r.section, r.label): (r.cur, r.prev) for r in rows}
    assert got[("LJP", "Utang bank")] == (2500, 3000)
    assert got[("LJP", "Liabilitas sewa")] == (-300, 0)
    assert got[("LJPJ", "Utang bank")] == (4000, 5000)
