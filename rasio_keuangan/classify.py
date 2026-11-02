"""Klasifikasi baris liabilitas: utang berbunga atau bukan.

Urutan keputusan:
1. Aturan dari penjelasan skripsi (kata kunci yang pasti termasuk / pasti tidak termasuk).
2. Bila tidak ada aturan yang cocok: model Machine Learning (TF-IDF + Logistic Regression)
   yang dilatih dari contoh label + baris neraca DEWA yang dipakai di contoh perhitungan CoD.
"""
from __future__ import annotations

import csv
from pathlib import Path
import re

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from .parser import Row

DATA = Path(__file__).parent / "data" / "contoh_label.csv"
MODEL_PATH = Path(__file__).resolve().parent.parent / "model" / "model_utang_berbunga.joblib"

EXCLUDE = re.compile(
    r"(berelasi|related|usaha\b|trade|pajak|\btax|akrual|accrued|masih\s+harus\s+dibayar|imbalan|employee|"
    r"pasca\s*kerja|pensiun|pension|bonus|pendapatan\s+(diterima|ditangguhkan)|unearned|deferred\s+(income|revenue)|"
    r"uang\s+muka|advance|derivatif|derivative|provisi|penyisihan|provision|dividen|dividend|kontrak|contract|"
    r"dimiliki\s+untuk\s+dijual|held\s+for\s+sale|lainnya\b|other\s+(current|non-?current|long-term|short-term)\s+liabilit|"
    r"kontinjensi|contingent|tunjangan|hari\s+raya|\bthr\b|jumlah|total|sub\s*jumlah)", re.I)
INCLUDE = re.compile(
    r"(pinjaman|\bloans?\b|borrowing|utang\s+bank|bank\s+loan|kredit|\bsewa\b|lease|obligasi|\bbonds?\b|\bnotes\b|"
    r"sukuk|wesel|\bmtn\b|medium\s+term|utang\s+jangka\s+panjang|long-term\s+debt|lembaga\s+keuangan|"
    r"pembiayaan\s+konsumen|hak\s+guna|right[-\s]of[-\s]use)", re.I)
OTHER_PAYABLE_3P = re.compile(r"(utang\s+lain-lain|other\s+(accounts\s+)?payables?)", re.I)


def rule(row: Row) -> tuple[bool | None, str]:
    text = f"{row.full_label} | {row.label_en}"
    if OTHER_PAYABLE_3P.search(text) and not re.search(r"berelasi|related", text, re.I):
        if row.section == "LJPJ" or row.sub == "jatuh tempo satu tahun":
            return True, "utang lain-lain pihak ketiga (jangka panjang / jatuh tempo satu tahun)"
        return False, "utang lain-lain pihak ketiga operasional (liabilitas jangka pendek biasa)"
    if EXCLUDE.search(text):
        return False, "aturan: termasuk daftar bukan utang berbunga"
    if INCLUDE.search(text):
        return True, "aturan: pinjaman/utang bank/sewa/obligasi/notes"
    return None, ""


def load_training_examples() -> tuple[list[str], list[int]]:
    X, y = [], []
    with open(DATA, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            X.append(r["label"])
            y.append(1 if r["kategori"] == "utang_berbunga" else 0)
    return X, y


def train(extra_X: list[str] | None = None, extra_y: list[int] | None = None):
    X, y = load_training_examples()
    X += extra_X or []
    y += extra_y or []
    feats = FeatureUnion([
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), lowercase=True)),
        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), lowercase=True)),
    ])
    model = Pipeline([("fitur", feats), ("lr", LogisticRegression(C=5.0, max_iter=3000))])
    model.fit(X, y)
    return model, len(y)


def save(model, n: int, meta: dict, path: Path = MODEL_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "n": n, "meta": meta}, path)
    return path


def load(path: Path = MODEL_PATH):
    if not Path(path).exists():
        return None
    return joblib.load(path)["model"]


def classify(row: Row, model) -> tuple[bool, str, bool]:
    """(utang berbunga?, alasan, perlu_dicek)"""
    dec, why = rule(row)
    if dec is not None:
        return dec, why, "operasional" in why or "jangka panjang / jatuh tempo" in why
    if model is None:
        return False, "tidak dikenali (tanpa model ML) - mohon dicek", True
    p = float(model.predict_proba([f"{row.full_label} {row.label_en}"])[0][1])
    return p >= 0.5, f"ML p={p:.2f} - mohon dicek", True
