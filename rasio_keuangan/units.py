"""Mendeteksi satuan & mata uang laporan keuangan, dan konversi ke satuan lain."""
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Unit:
    currency: str      # "USD" atau "IDR"
    scale: int         # 1, 1_000, 1_000_000, 1_000_000_000

    @property
    def label(self) -> str:
        """Teks satuan untuk kolom 'Satuan Nominal' (seperti contoh DEWA)."""
        prefix = {1: "", 1_000: "ribuan ", 1_000_000: "jutaan ", 1_000_000_000: "miliaran "}[self.scale]
        cur = "dolar AS" if self.currency == "USD" else "Rupiah"
        return (prefix + cur) if prefix else cur


PATTERNS = [
    # format ringkas: US$ '000 / USD'000 / Rp'000 / Rp juta / (Dalam USD, kecuali ...) / (In Rupiah, unless ...)
    (re.compile(r"(us\$|usd)\s*['\u2019`\u2018]?\s*000\s*,\s*000\b|(us\$|usd)\s*juta|(us\$|usd)\s*millions?", re.I), Unit("USD", 1_000_000)),
    (re.compile(r"(us\$|usd)\s*['\u2019`\u2018]\s*000|(us\$|usd)\s+000\b|dalam\s+ribuan\s+(us\$|usd)|in\s+thousands\s+of\s+(us\$|usd)|"
                r"\(\s*(dalam|in)\s+(ribuan|thousands?)\s+(us\$|usd)", re.I), Unit("USD", 1000)),
    (re.compile(r"rp\s*['\u2019`\u2018]\s*000\s*,\s*000|rp\s*juta|in\s+millions?\s+of\s+(rp|rupiah)|dalam\s+jutaan\s+(rp|rupiah)|"
                r"\(\s*(dalam|in)\s+(jutaan|millions?)\s+rup", re.I), Unit("IDR", 1_000_000)),
    (re.compile(r"rp\s*['\u2019`\u2018]\s*000\b|dalam\s+ribuan\s+(rp|rupiah)|in\s+thousands\s+of\s+(rp|rupiah)", re.I), Unit("IDR", 1000)),
    (re.compile(r"\(\s*(dalam|in|expressed\s+in|stated\s+in)\s+(usd|us\$|us\s+dollars?|dolar\s+as|dolar\s+amerika)\b|"
                r"(dalam|in)\s+(usd|us\$)\s*,?\s*(kecuali|unless|except)", re.I), Unit("USD", 1)),
    (re.compile(r"\(\s*(dalam|in|expressed\s+in|stated\s+in)\s+(rupiah|rp)\b|(dalam|in)\s+(rupiah|rp)\s*(penuh|full)?\s*,?\s*(kecuali|unless|except)|"
                r"(rupiah\s+penuh|full\s+rupiah|rupiah\s+full)", re.I), Unit("IDR", 1)),
    (re.compile(r"(ribuan|thousands?\s+of)\s+(dolar|dollar|us\s*dollar|us\$|united\s+states)", re.I), Unit("USD", 1000)),
    (re.compile(r"(jutaan|millions?\s+of)\s+(dolar|dollar|us\$|united\s+states)", re.I), Unit("USD", 1_000_000)),
    (re.compile(r"(miliaran|milyaran|billions?\s+of)\s+(rupiah|rp)|in\s+billions\s+of\s+(rupiah|rp)|rp\s*miliar", re.I), Unit("IDR", 1_000_000_000)),
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
