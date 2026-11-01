"""Pola regex untuk mengenali kode GRI (mis. 102-1, 305-7, 2-1, 103-2-c-vi)."""
import re

# Kode GRI 2016/2018/2020 (3 digit) atau GRI 2021 (2-x / 3-x).
TOPIC_CODE = r"(?:1\d{2}|2\d{2}|3\d{2}|4\d{2})-\d{1,2}"
GEN2021_CODE = r"[23]-\d{1,2}"

# Satu token kode utuh (untuk tabel indeks): "102-1", "GRI 2-1", "2-1.", "(102-1)".
CODE_TOKEN_RE = re.compile(
    rf"^[\[(]?(?:GRI\s*)?(?P<code>{TOPIC_CODE}|{GEN2021_CODE})[a-z]?[\]).,:;]*$", re.I
)
# Kode yang muncul di mana saja dalam baris teks.
ANY_CODE_RE = re.compile(rf"(?<![\d\-./])(?P<code>{TOPIC_CODE}|{GEN2021_CODE})(?![\d])")
# Kode di dalam kurung, mis. "(102-5)(102-45)", "[305-1] [305-2]", "[102-48. 403-2]".
BRACKET_RE = re.compile(r"[\[(\{]([^\[\]()\{\}]{1,120})[\])\}]")
TOPIC_IN_TEXT_RE = re.compile(rf"(?<![\d\-./])({TOPIC_CODE})(?![\d])")
GEN2021_IN_TEXT_RE = re.compile(rf"(?<![\d\-./])({GEN2021_CODE})(?![\d])")
GRI_PREFIXED_RE = re.compile(rf"GRI\s*({TOPIC_CODE}|{GEN2021_CODE})(?![\d])", re.I)

# Kode di template Excel: "102-7-a-i", "103-2-c-vi", "2-1 Rincian organisasi".
TEMPLATE_CODE_RE = re.compile(r"^\s*(\d{1,3}-\d{1,2}(?:-[a-z]{1,2}(?:-[ivx]+)?)?)\b", re.I)


def parent_code(code: str) -> str:
    """'102-7-a-i' -> '102-7'; '103-2-c-vi' -> '103-2'; '102-1' -> '102-1'."""
    parts = code.split("-")
    return "-".join(parts[:2])


def is_gen2021(code: str) -> bool:
    return code.split("-")[0] in {"2", "3"}
