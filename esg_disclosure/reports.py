"""Mencari file PDF laporan per perusahaan & tahun dari folder LAPORAN KEBERLANJUTAN."""
from __future__ import annotations

from pathlib import Path
import re

from .pdf_reader import Document, read_pdf

YEAR_RE = re.compile(r"(?<!\d)(19|20)\d{2}(?!\d)")


def find_reports(root: Path) -> dict[str, dict[int, list[Path]]]:
    """{KODE: {tahun: [pdf, ...]}} — nama folder = kode perusahaan, nama file memuat tahun."""
    out: dict[str, dict[int, list[Path]]] = {}
    for folder in sorted(p for p in Path(root).iterdir() if p.is_dir() and not p.name.startswith(".")):
        years: dict[int, list[Path]] = {}
        for pdf in sorted(folder.rglob("*")):
            if pdf.suffix.lower() != ".pdf" or pdf.name.startswith("."):
                continue
            m = YEAR_RE.search(pdf.stem)
            if m:
                years.setdefault(int(m.group(0)), []).append(pdf)
        out[folder.name.strip().upper()] = years   # folder kosong tetap dicatat (kolom dibiarkan kosong)
    return out


def load_report(paths: list[Path]) -> Document:
    """Bila satu tahun terdiri dari beberapa PDF, halamannya digabung."""
    docs = [read_pdf(p) for p in paths]
    if len(docs) == 1:
        return docs[0]
    pages, offset = [], 0
    for d in docs:
        for p in d.pages:
            p.number += offset
            pages.append(p)
        offset += d.page_count
    return Document(paths[0], pages)
