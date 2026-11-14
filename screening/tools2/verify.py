"""Unduh PDF -> teks (pdftotext) -> cek tahun & GRI. Simpan hanya ringkasan; PDF dihapus."""
import sys, json, re, os, subprocess, hashlib, tempfile, concurrent.futures as cf
import requests
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
OUT = sys.argv[3] if len(sys.argv) > 3 else "pdftxt"
GRI_IDX = re.compile(r"(GRI\s+Content\s+Index|Indeks\s+(Isi\s+)?GRI|GRI\s+Index|Indeks\s+Standar\s+GRI|Daftar\s+(Isi|Indeks)\s+GRI|Referensi\s+(Silang\s+)?GRI|GRI\s+Standards?\s+(Content\s+)?Index|Indeks\s+Konten\s+GRI|Tabel\s+(Indeks\s+)?GRI)", re.I)
GRI_STMT = re.compile(r"(in\s+accordance\s+with\s+the\s+GRI|with\s+reference\s+to\s+the\s+GRI|sesuai\s+(dengan\s+)?(Standar\s+GRI|GRI\s+Standar)|mengacu\s+(pada|kepada)\s+(Standar\s+)?GRI|merujuk\s+(pada|kepada)\s+(Standar\s+)?GRI|GRI\s+Standards?|Standar\s+GRI|GRI\s+Standar)", re.I)
GRI_CODE = re.compile(r"\bGRI\s?(10[0-3]|[23]0[0-9]|40[0-9]|41[0-9]|1|2|3)\b|\b(102|103|201|302|305|401|403|405)-\d{1,2}\b")
def check(url):
    h = hashlib.md5(url.encode()).hexdigest()[:12]
    jf = f"{OUT}/{h}.json"
    if os.path.exists(jf): return json.load(open(jf))
    res = {"url": url, "status": None}
    try:
        r = requests.get(url, headers=UA, timeout=240, stream=True, allow_redirects=True)
        res["status"] = r.status_code; res["final"] = r.url; res["ctype"] = r.headers.get("content-type")
        if r.status_code != 200: raise Exception("http")
        fd, tmp = tempfile.mkstemp(suffix=".pdf", dir=OUT); n = 0
        with os.fdopen(fd, "wb") as f:
            for ch in r.iter_content(1 << 16):
                f.write(ch); n += len(ch)
                if n > 450e6: break
        res["bytes"] = n
        with open(tmp, "rb") as f: head = f.read(1024)
        if b"%PDF-" not in head:
            res["note"] = "bukan PDF"; os.remove(tmp); raise Exception("notpdf")
        info = subprocess.run(["pdfinfo", tmp], capture_output=True, text=True, timeout=60).stdout
        m = re.search(r"Pages:\s+(\d+)", info); res["pages"] = int(m.group(1)) if m else None
        cover = subprocess.run(["pdftotext", "-l", "4", "-layout", tmp, "-"], capture_output=True, text=True, timeout=120).stdout
        full = subprocess.run(["pdftotext", tmp, "-"], capture_output=True, text=True, timeout=600).stdout
        os.remove(tmp)
        res["chars"] = len(full)
        c = " ".join(cover.split())
        res["cover"] = c[:400]
        res["cover_years"] = sorted(set(re.findall(r"(?<!\d)(20[12]\d)(?!\d)", c)))
        res["title_sr"] = bool(re.search(r"sustainab|keberlanjutan", c, re.I))
        res["title_ar"] = bool(re.search(r"annual\s+report|laporan\s+tahunan|integrated", c, re.I))
        res["gri_index"] = len(GRI_IDX.findall(full))
        res["gri_stmt"] = len(GRI_STMT.findall(full))
        res["gri_codes"] = len(GRI_CODE.findall(full))
        m = GRI_IDX.search(full)
        if m: res["gri_index_snip"] = " ".join(full[max(0, m.start()-80): m.end()+120].split())
        m = re.search(r"(in\s+accordance\s+with\s+the\s+GRI[^.]{0,120}|with\s+reference\s+to\s+the\s+GRI[^.]{0,120}|(sesuai|mengacu|merujuk)[^.]{0,40}GRI[^.]{0,120})", full, re.I)
        if m: res["gri_stmt_snip"] = " ".join(m.group(0).split())[:220]
        res["ojk_idx"] = bool(re.search(r"POJK\s*(Nomor\s*)?51|51/POJK\.03/2017|SEOJK\s*(Nomor\s*)?16", full, re.I))
    except Exception as e:
        res.setdefault("note", str(e)[:120])
    json.dump(res, open(jf, "w"))
    return res
if __name__ == "__main__":
    urls = json.load(open(sys.argv[1]))
    os.makedirs(OUT, exist_ok=True)
    out = {}
    with cf.ThreadPoolExecutor(int(os.environ.get("W","8"))) as ex:
        for r in ex.map(check, urls):
            out[r["url"]] = r
            print(r.get("status"), r.get("pages"), r.get("cover_years"), "GRIidx", r.get("gri_index"), r["url"][-70:], flush=True)
    json.dump(out, open(sys.argv[2], "w"), indent=1)
