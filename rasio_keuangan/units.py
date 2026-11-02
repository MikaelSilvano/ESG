"""Mendeteksi satuan & mata uang laporan keuangan, dan konversi ke satuan lain."""
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Unit:
    currency: str      # "USD" atau "IDR"
    scale: int         # 1, 1_000, 1_000_000

    @property
    def label(self) -> str:
        """Teks satuan untuk kolom 'Satuan Nominal' (seperti contoh DEWA)."""
        prefix = {1: "", 1_000: "ribuan ", 1_000_000: "jutaan "}[self.scale]
        cur = "dolar AS" if self.currency == "USD" else "Rupiah"
        return (prefix + cur) if prefix else cur


PATTERNS = [
    (re.compile(r"(ribuan|thousands?\s+of)\s+(dolar|dollar|us\s*dollar|us\$|united\s+states)", re.I), Unit("USD", 1000)),
    (re.compile(r"(jutaan|millions?\s+of)\s+(dolar|dollar|us\$|united\s+states)", re.I), Unit("USD", 1_000_000)),
    (re.compile(r"(jutaan|millions?\s+of)\s+(rupiah|rp)", re.I), Unit("IDR", 1_000_000)),
    (re.compile(r"(ribuan|thousands?\s+of)\s+(rupiah|rp)", re.I), Unit("IDR", 1000)),
    (re.compile(r"(disajikan|dinyatakan|expressed|presented|\(dalam|\(in)[^.)]{0,25}(dolar\s+amerika|united\s+states\s+dollar|us\s*dollar|dolar\s+as|us\$)", re.I), Unit("USD", 1)),
    (re.compile(r"\bUS\$\s+US\$", re.I), Unit("USD", 1)),
    (re.compile(r"(disajikan|dinyatakan|expressed|presented|\(dalam|\(in)[^.)]{0,25}(rupiah)", re.I), Unit("IDR", 1)),
]


def detect_unit(text: str) -> Unit | None:
    t = re.sub(r"\s+", " ", text)
    for pat, unit in PATTERNS:
        if pat.search(t):
            return unit
    return None


def convert(value: float, src: Unit, dst: Unit, kurs: float | None) -> float:
    """Konversi nilai dari satuan src ke dst. kurs = Rp per 1 USD (akhir tahun nilai tsb)."""
    v = value * src.scale
    if src.currency != dst.currency:
        if kurs is None:
            raise ValueError("Kurs dibutuhkan untuk konversi mata uang")
        v = v * kurs if src.currency == "USD" else v / kurs
    return v / dst.scale
