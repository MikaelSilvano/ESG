"""Membaca baris-baris tabel laporan keuangan (label + angka tahun berjalan & tahun lalu)
berdasarkan posisi kata di halaman PDF."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import re

import pymupdf

AMOUNT_RE = re.compile(r"^\(?-?\d{1,3}(?:[.,]\d{3})+\)?$|^\(?-?\d{1,3}\)?$")
DASH_RE = re.compile(r"^[-–—]{1,2}$")
YEAR_RE = re.compile(r"^(?:19|20)\d{2}[/,:]?$")


@dataclass
class Word:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str

    @property
    def yc(self):
        return (self.y0 + self.y1) / 2


@dataclass
class Row:
    page: int
    label: str                 # label bahasa Indonesia (baris yang memuat angka)
    label_en: str
    context: list[str]         # baris-baris judul/label tanpa angka tepat di atasnya
    cur: float | None          # nilai tahun berjalan
    prev: float | None         # nilai tahun sebelumnya (komparatif)
    section: str = ""          # ASET / LJP (liabilitas jangka pendek) / LJPJ (jangka panjang) / EKUITAS
    sub: str = ""              # mis. "jatuh tempo dalam satu tahun"
    raw: str = ""
    is_total: bool = False

    @property
    def full_label(self) -> str:
        """Label lengkap: baris lanjutan (mis. '- Pihak ketiga', 'jatuh tempo dalam satu tahun')
        digabung dengan baris-baris judul di atasnya sampai awal label."""
        lab = self.label
        if not lab:
            return self.context[-1] if self.context else self.label_en
        parts = [lab]
        cont = lambda t: bool(t) and (t[0].islower() or t[0] in "-–(" or bool(re.match(r"^(pihak|third|related)", t, re.I)))
        i = len(self.context) - 1
        while cont(parts[0]) and i >= 0:
            parts.insert(0, self.context[i])
            i -= 1
        return " ".join(parts)

    @property
    def text(self) -> str:
        return " ".join([*self.context[-2:], self.label, self.label_en]).strip()


def parse_amount(s: str) -> float | None:
    s = s.strip()
    if DASH_RE.match(s):
        return 0.0
    neg = s.startswith("(") or s.endswith(")") or s.startswith("-")
    digits = re.sub(r"[^\d]", "", s)
    if not digits:
        return None
    v = float(digits)
    return -v if neg else v


def _words(page: pymupdf.Page) -> list[Word]:
    ws = [Word(w[0], w[1], w[2], w[3], w[4]) for w in page.get_text("words")]
    # gabungkan "(" yang terpisah dari angkanya, mis. "(" "5.430.580.843)"
    out: list[Word] = []
    for w in sorted(ws, key=lambda w: (round(w.yc), w.x0)):
        if out and out[-1].text in {"(", "(-"} and abs(out[-1].yc - w.yc) < 3 and re.match(r"^[\d.,]+\)?$", w.text):
            p = out.pop()
            w = Word(p.x0, min(p.y0, w.y0), w.x1, max(p.y1, w.y1), "(" + w.text)
        out.append(w)
    return out


def _group_rows(words: list[Word], tol: float = 3.0) -> list[list[Word]]:
    rows: list[list[Word]] = []
    for w in sorted(words, key=lambda w: w.yc):
        if rows and abs(rows[-1][0].yc - w.yc) <= tol:
            rows[-1].append(w)
        else:
            rows.append([w])
    return [sorted(r, key=lambda w: w.x0) for r in rows]


def _is_amount(w: Word) -> bool:
    return bool(AMOUNT_RE.match(w.text) or DASH_RE.match(w.text))


def _columns(words: list[Word], width: float) -> list[float]:
    """Tepi kanan kolom angka [tahun berjalan, tahun lalu].

    Kolom = kelompok angka yang rata kanan. Bila ada >2 kolom (mis. penyajian kembali:
    2023 | 2022* | 1 Januari 2022*), tahun di kepala kolom dipakai untuk memilih."""
    big = [w for w in words if re.match(r"^\(?-?\d{1,3}(?:[.,]\d{3})+\)?$", w.text) and w.x0 > width * 0.25]
    edges = Counter(round(w.x1 / 6) for w in big)
    cols: list[float] = []
    for e, n in edges.most_common():
        if n < 3:
            break
        if all(abs(e - c) > 4 for c in cols):
            cols.append(e)
    cols = sorted(c * 6 for c in cols[:4])
    if len(cols) <= 2:
        return cols
    first_y = min((w.y0 for w in big), default=0)
    years = [w for w in words if YEAR_RE.match(w.text) and w.y1 <= first_y + 2]
    tagged = []
    for c in cols:
        near = [int(w.text[:4]) for w in years if abs(w.x1 - c) <= 45 or (w.x0 <= c <= w.x1 + 40)]
        tagged.append((c, max(near) if near else None))
    if all(y is not None for _, y in tagged):
        cur = max(tagged, key=lambda t: (t[1], -t[0]))
        prevs = [t for t in tagged if t[1] == cur[1] - 1]
        if prevs:
            return [cur[0], min(prevs, key=lambda t: abs(t[0] - cur[0]))[0]]
    return cols[:2]


def _notes_x(words: list[Word]) -> tuple[float, float] | None:
    for w in words:
        if re.match(r"^(catatan|notes?)\W*$", w.text, re.I):
            return (w.x0 - 12, w.x1 + 12)
    return None


SEC_PATTERNS = [
    ("EKUITAS", re.compile(r"^(ekuitas|equity)\b", re.I)),
    ("LJPJ", re.compile(r"^(liabilitas\s+jangka\s+panjang|liabilitas\s+tidak\s+lancar|non-?current\s+liabilities|long-term\s+liabilities)\s*$", re.I)),
    ("LJP", re.compile(r"^(liabilitas\s+jangka\s+pendek|liabilitas\s+lancar|current\s+liabilities|short-term\s+liabilities)\s*$", re.I)),
    ("ASET", re.compile(r"^(aset|assets)\s*$", re.I)),
]
SUB_CM = re.compile(r"(jatuh\s+tempo\s+dalam\s+(waktu\s+)?satu\s+tahun|current\s+(maturities|portion))", re.I)
SUB_NET = re.compile(r"(setelah\s+dikurangi|net\s+of\s+current)", re.I)


def parse_pages(doc: pymupdf.Document, pages: list[int]) -> list[Row]:
    out: list[Row] = []
    section, sub = "", ""
    cl_closed = False   # sudah melewati "Jumlah liabilitas jangka pendek"
    last_ctx: list[str] = []
    for pno in pages:
        page = doc[pno - 1]
        width = page.rect.width
        words = _words(page)
        cols = _columns(words, width)
        if len(cols) < 2:
            continue
        cur_x, prev_x = cols[0], cols[1]
        notes = _notes_x(words)
        left_limit = cur_x - 70
        pending: list[str] = []
        for r in _group_rows(words):
            amts: dict[str, Word] = {}
            label_w, en_w = [], []
            for w in r:
                in_notes = notes and notes[0] <= (w.x0 + w.x1) / 2 <= notes[1] and not re.match(r"^\(?\d{1,3}(?:[.,]\d{3})+", w.text)
                if _is_amount(w) and not in_notes and w.x1 > left_limit:
                    if abs(w.x1 - cur_x) <= 14 and "cur" not in amts:
                        amts["cur"] = w
                        continue
                    if abs(w.x1 - prev_x) <= 14 and "prev" not in amts:
                        amts["prev"] = w
                        continue
                if in_notes:
                    continue
                if w.x1 < left_limit + 40:
                    label_w.append(w.text)
                elif w.x0 > prev_x + 2:
                    en_w.append(w.text)
            label = " ".join(label_w).strip()
            label = re.sub(r"(\s+\d{1,2}[a-z]?(,\s?\d{0,2}[a-z]{0,2}\d?)*)+$", "", label).strip()   # buang nomor catatan
            label_en = " ".join(en_w).strip()
            if not amts:
                txt = label or label_en
                for name, pat in SEC_PATTERNS:
                    if pat.match(label) or pat.match(label_en):
                        if name == "LJPJ" and section == "LJP" and not cl_closed:
                            # "Liabilitas jangka panjang / jatuh tempo dalam satu tahun" di dalam liabilitas lancar
                            sub = "jatuh tempo satu tahun"
                        else:
                            section, sub = name, ""
                        pending = []
                        break
                else:
                    if SUB_CM.search(label + " " + label_en) and section == "LJP" and not SUB_NET.search(label + " " + label_en):
                        sub = "jatuh tempo satu tahun"
                    elif SUB_NET.search(label + " " + label_en):
                        sub = "bagian jangka panjang"
                    if txt:
                        pending.append(label or label_en)
                        pending = pending[-4:]
                continue
            cur = parse_amount(amts["cur"].text) if "cur" in amts else None
            prev = parse_amount(amts["prev"].text) if "prev" in amts else None
            if not label and pending:
                label = pending.pop()
            if not label and not label_en:
                pending = []
                continue   # subtotal tanpa label
            if re.search(r"\b(19|20)\d\d\b", label) and re.search(r"desember|december", label, re.I) and \
                    (cur is None or prev is None or max(abs(cur or 0), abs(prev or 0)) < 100):
                pending = []
                continue   # baris judul tanggal (mis. "31 DESEMBER 2020 DAN 2019"), bukan pos laporan
            ctx = list(pending)
            if not ctx and label and (label[0] in "-–" or re.match(r"^(pihak|third|related)", label, re.I)):
                ctx = list(last_ctx)          # sub-pos berikutnya (mis. 2nd "Pihak ketiga") memakai induk yang sama
            row = Row(pno, label, label_en, ctx, cur, prev, section, sub,
                      " ".join(w.text for w in r))
            last_ctx = ctx
            out.append(row)
            low = " ".join([pending[-1] if pending else "", label, label_en]).lower().strip()
            is_total = bool(re.match(r"^(jumlah|total)\b", label.lower()) or re.match(r"^(jumlah|total)\b", label_en.lower())
                            or (pending and re.match(r"^(jumlah|total)\b", pending[-1].lower())))
            row.is_total = is_total
            if is_total and section in ("LJP", "LJPJ") and re.search(r"liabilit", low):
                sub = ""
                if section == "LJP":
                    cl_closed = True
                    section = "LJPJ"
            pending = []
    return out
