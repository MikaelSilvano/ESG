"""Pelatihan & pemuatan model Machine Learning (Logistic Regression).

Model belajar dari perusahaan yang SUDAH dinilai manual di Excel (contoh: DEWA).
Fitur per item: ada di indeks dengan halaman, ada di indeks tanpa halaman, jumlah
halaman bertanda kode, kemiripan TF-IDF, cakupan kata kunci.
"""
from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

from .scorer import FEATURE_NAMES

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "model" / "model_esg.joblib"


def train(X: list[list[float]], y: list[int]):
    X_arr, y_arr = np.asarray(X, dtype=float), np.asarray(y, dtype=int)
    if len(set(y_arr.tolist())) < 2:
        raise ValueError("Data latih harus memuat poin 0 dan 1")
    clf = LogisticRegression(C=1.0, max_iter=2000)
    clf.fit(X_arr, y_arr)
    return clf


def save(model, path: Path = DEFAULT_MODEL_PATH, meta: dict | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURE_NAMES, "meta": meta or {}}, path)
    return path


def load(path: Path = DEFAULT_MODEL_PATH):
    if not Path(path).exists():
        return None, {}
    obj = joblib.load(path)
    if obj.get("features") != FEATURE_NAMES:
        return None, {}
    return obj["model"], obj.get("meta", {})
