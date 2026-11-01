"""Membaca tabel *GRI Content Index* (Indeks Isi GRI) di dalam laporan.

Hasilnya: untuk setiap kode GRI yang tercantum di tabel indeks, apakah ada
rujukan halaman/lokasi (mis. "34", "111,116", "AR hal. 45", "www...").
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

from .codes import CODE_TOKEN_RE
from .pdf_reader import Document, Page, Word

HEADER_PAGE_RE = re.compile(
    r"^(halaman|hal\.?|page|pages|page\(s\)|lokasi|location|rujukan)$",
    re.I
)
INDEX_HINT_RE = re.compile(
    r"(content\s+index|indeks\s+(isi|konten)|indeks\s+gri|gri\s+index|indeks\s+standar|"
    r"referensi\s+silang|cross\s+reference|gri\s+standards?|standar\s+gri|indeks\s+gri)",
    re.I,
)
PAGE_TOKEN_RE = re.compile(r"^(hal\.?|p\.?|page)?\d{1,3}([,\-–;/&]+\d{1,3})*[,;.]?$", re.I)
URL_RE = re.compile(r"(www\.|https?://|\.co\.id|\.com\b)", re.I)
OMIT_RE = re.compile(
    r"(tidak\s+(tersedia|relevan|berlaku|dilaporkan|diungkapkan|ada|material)|"
    r"not\s+(applicable|available|reported|disclosed|material)|\bn/?a\b|omitted|dikecualikan)",
    re.I,
)
# lokasi berupa teks, mis. "Laporan Tahunan", "Annual Report", "Appendix/Lampiran", "Website"
ANNUAL_REF_RE = re.compile(r"(laporan\s+tahunan|annual\s+report|\bAR\b|\bLT\b|appendix|lampiran|website|situs)", re.I)
LOCATION_WORD_RE = re.compile(r"^(laporan|tahunan|annual|report|appendix|lampiran|website|situs|AR|LT)[,.;]?$", re.I)


def _is_page_header(text: str) -> bool:
    """'Halaman', 'Page', 'Halaman/Page', 'Halaman|', 'Hal.' ..."""
    parts = [p for p in re.split(r"[/|:]", text.strip()) if p.strip(" .")]
    return bool(parts) and any(HEADER_PAGE_RE.match(p.strip(" .")) for p in parts)


@dataclass
class IndexEntry:
    code: str
    page: int                     # halaman PDF tempat kode tercantum di indeks
    location: str = ""            # isi kolom halaman/lokasi
    row_text: str = ""            # seluruh teks baris (untuk audit)
    via_header: bool = True       # kolom halaman ditemukan dari header "Halaman/Page"

    @property
    def has_location(self) -> bool:
        """Ada rujukan halaman/lokasi: angka halaman, atau lokasi tertulis seperti
        "Appendix/Lampiran", "Laporan Tahunan", alamat website. "-", "N/A", kosong = tidak ada."""
        loc = self.location
        return (any(PAGE_TOKEN_RE.match(t) for t in loc.split())
                or bool(URL_RE.search(loc)) or bool(ANNUAL_REF_RE.search(loc)))

    @property
    def omitted(self) -> bool:
        return not self.has_location and bool(OMIT_RE.search(self.row_text))


@dataclass
class GriIndex:
    entries: dict[str, list[IndexEntry]] = field(default_factory=dict)
    pages: list[int] = field(default_factory=list)

    def add(self, e: IndexEntry) -> None:
        self.entries.setdefault(e.code, []).append(e)

    def has_location(self, code: str) -> bool:
        return any(e.has_location for e in self.entries.get(code, []))

    def listed(self, code: str) -> bool:
        return code in self.entries

    def location(self, code: str) -> str:
        locs = [e.location for e in self.entries.get(code, []) if e.has_location]
        return "; ".join(dict.fromkeys(locs))

    def raw_location(self, code: str) -> str:
        """Isi kolom halaman/lokasi apa adanya (termasuk teks tanpa angka)."""
        return "; ".join(dict.fromkeys(e.location for e in self.entries.get(code, []) if e.location))

    def codes(self) -> set[str]:
        return set(self.entries)


def _code_tokens(page: Page) -> list[tuple[Word, str]]:
    out = []
    words = page.words
    hdr = [w for w in words if _is_page_header(w.text)]
    for i, w in enumerate(words):
        m = CODE_TOKEN_RE.match(w.text.strip())
        if not m:
            continue
        code = m.group("code")
        if code[0] in "23" and code[1] == "-":
            # "2-1" wajib berdiri sendiri (bukan rentang halaman "2-3" di kolom Halaman)
            prev = words[i - 1].text if i > 0 else ""
            if re.fullmatch(r"\d+[,.]?", prev) and abs(words[i - 1].y0 - w.y0) < 2:
                continue
            if any(h.y0 < w.y0 and h.x0 - 10 <= w.xc <= h.x1 + 10 for h in hdr):
                continue
        out.append((w, code))
    return out


def _first_code_y(toks: list[tuple[Word, str]]) -> float:
    """y kode pertama pada kolom kode utama. Kode yang terpisah jauh di atas
    (mis. '[102-55]' pada judul halaman) diabaikan."""
    xs = [round(w.x0) for w, _ in toks]
    col = max(set(xs), key=lambda x: sum(abs(x - o) < 8 for o in xs))
    ys = sorted(w.y0 for w, _ in toks if abs(w.x0 - col) < 8)
    while len(ys) > 1 and ys[1] - ys[0] > 80:
        ys.pop(0)
    return ys[0]


def _index_layout(page: Page) -> tuple[bool, bool]:
    """(tata letak tabel kode?, ada header kolom Halaman/Page di atas kode?)"""
    toks = _code_tokens(page)
    if len(toks) < 5:
        return False, False
    xs = [round(w.x0 / 15) for w, _ in toks]
    top_col = max(xs.count(x) for x in set(xs))
    if top_col < 4:
        return False, False
    first_y = _first_code_y(toks)
    has_header = any(_is_page_header(w.text) and w.y0 < first_y - 3 for w in page.words)
    return True, has_header


def find_index_pages(doc: Document) -> list[int]:
    """Halaman tabel indeks GRI: susunan kolom kode + header 'Halaman/Page'.
    Halaman lanjutan tanpa header tetap diterima bila menyambung halaman indeks sebelumnya."""
    pages: list[int] = []
    for page in doc.pages:
        table, header = _index_layout(page)
        if not table:
            continue
        hint = bool(INDEX_HINT_RE.search(page.text)) or bool(re.search(r"\b(GRI|indeks|index)\b", page.text, re.I))
        if (header and hint) or (pages and pages[-1] >= page.number - 2):
            pages.append(page.number)
    return pages


def _in_margin(page: Page, w: Word) -> bool:
    """Header/footer halaman (nomor halaman laporan, judul bab) diabaikan."""
    return w.y0 > page.height * 0.92 or w.y1 < page.height * 0.06


def _is_location_token(t: Word) -> bool:
    s = t.text.strip()
    if re.fullmatch(r"\d{1,3}([.,]\d{3}){2,}", s) or ",000" in s or ".000" in s:
        return False   # angka ribuan (mis. 1,000,000), bukan nomor halaman
    return bool(PAGE_TOKEN_RE.match(s) or URL_RE.search(s) or LOCATION_WORD_RE.match(s))


def _parse_page(page: Page, index: GriIndex) -> None:
    toks = _code_tokens(page)
    first_code_y = _first_code_y(toks)
    # header kolom "Halaman/Page": harus berada di atas kode pertama (kepala tabel)
    headers = [w for w in page.words if _is_page_header(w.text)
               and w.y0 < first_code_y - 3 and not _in_margin(page, w)]
    if headers:   # hanya baris kepala tabel paling atas (bukan kata "Lokasi" di judul item)
        top = min(h.y0 for h in headers)
        headers = [h for h in headers if h.y0 <= top + 30]
    other_hdr_x = sorted({round(w.x0) for w in page.words if w.y0 < first_code_y - 3 and re.match(
        r"^(omission|alasan|keterangan|pengecualian|reason|sdgs?|pojk|description|deskripsi)$",
        w.text.strip(), re.I)})
    body = [t for t in page.words if not _in_margin(page, t)]

    for w, code in toks:
        below = [t for t, _ in toks if abs(t.x0 - w.x0) < 30 and t.y0 > w.y0 + 3]
        next_y = min((t.y0 for t in below), default=w.y0 + 60)
        y_top, y_bot = w.y0 - 8, min(next_y - 4, w.y0 + 45)
        row_words = [t for t in body if y_top <= t.y0 <= y_bot and t.x0 > w.x1 - 1
                     and not CODE_TOKEN_RE.match(t.text.strip())]
        row_text = " ".join(t.text for t in row_words)

        hdrs = [h for h in headers if h.x0 > w.x1 - 5]
        loc_words: list[Word] = []
        if hdrs:
            # header terdekat di kanan kode (tabel bisa 2 kolom berdampingan)
            h = min(hdrs, key=lambda c: c.x0)
            nxt = [x for x in other_hdr_x if x > h.x1 + 5]
            right = min(min(nxt) - 2 if nxt else page.width, h.x1 + 45)
            left = h.x0 - 50
            loc_words = [t for t in row_words if left <= t.xc <= right and _is_location_token(t)]
        else:
            # tanpa header kolom yang jelas: ambil token angka halaman di sisi kanan baris.
            # (Bila header ada tetapi kolomnya "-" / kosong, artinya TIDAK ada halaman -> poin 0.)
            loc_words = [t for t in row_words if t.x0 > w.x1 + 120 and _is_location_token(t)]
        location = " ".join(t.text for t in sorted(loc_words, key=lambda t: (round(t.y0), t.x0)))
        index.add(IndexEntry(code, page.number, location, row_text, bool(hdrs)))


def parse_gri_index(doc: Document) -> GriIndex:
    index = GriIndex()
    for n in find_index_pages(doc):
        index.pages.append(n)
        _parse_page(doc.pages[n - 1], index)
    return index
