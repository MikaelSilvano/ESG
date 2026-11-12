"""Tes untuk perbaikan pembacaan indeks GRI & laporan keuangan (kode terpecah, halaman dalam kurung, satuan ringkas)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from esg_disclosure.gri_index import IndexEntry, _is_location_token
from esg_disclosure.pdf_reader import Word, merge_split_codes
from rasio_keuangan.classify import rule
from rasio_keuangan.parser import Row
from rasio_keuangan.units import Unit, detect_unit


def _w(x0, text):
    return Word(x0, 10, x0 + 5 * len(text), 20, text)


def test_kode_gri_terpecah_digabung():
    words = [_w(0, "GRI"), _w(30, "102"), _w(52, "-"), _w(60, "52"), _w(300, "4"), _w(306, "-"), _w(312, "5")]
    assert [w.text for w in merge_split_codes(words)] == ["GRI", "102-52", "4", "-", "5"]


def test_halaman_dalam_kurung():
    assert _is_location_token(_w(0, "[22]"))
    assert _is_location_token(_w(0, "(41,44)"))
    assert IndexEntry("102-1", 1, "[22]").has_location
    assert not IndexEntry("102-1", 1, "-").has_location


def test_satuan_ringkas():
    assert detect_unit("US$ '000 US$ '000") == Unit("USD", 1000)
    assert detect_unit("(Dalam USD, kecuali dinyatakan lain)") == Unit("USD", 1)
    assert detect_unit("(Dalam jutaan Rupiah)") == Unit("IDR", 1_000_000)
    assert detect_unit("Rp'000") == Unit("IDR", 1000)


def test_pinjaman_lainnya_tetap_utang_berbunga():
    r = lambda lab: Row(1, lab, "", [], 1.0, 1.0)
    assert rule(r("Pinjaman jangka panjang lainnya"))[0] is True
    assert rule(r("Liabilitas keuangan lainnya"))[0] is False
    assert rule(r("Estimasi biaya pembongkaran aset tetap"))[0] is False
