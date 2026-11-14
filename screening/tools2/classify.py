import json, re, sys
from urllib.parse import unquote
d = json.load(open(sys.argv[1]))
SR = re.compile(r"^sr[-_ ]?20|^sr[-_]|sustainab|sustanib|keberlanjutan|berkelanjutan|\bSR\b|[-_/ ]SR[-_ .0-9]|esg[-_ ]?report|laporan[-_ ]?lst|\bLST\b", re.I)
AR = re.compile(r"^ar[-_ ]?20|annual[-_ %20]*report|laporan[-_ %20]*tahunan|\bAR\b|(^|[-_/ ])AR[-_ .]?20|AR20|integrated[-_ ]?report", re.I)
FS = re.compile(r"assurance|policy|kebijakan|charter|piagam|code[-_ ]?of[-_ ]?conduct|general[-_ ]?meeting|invitation|undangan|pengumuman|announcement|power[-_ ]?of[-_ ]?attorney|kuasa|ringkasan|risalah|summary|minutes|financial[-_ ]?statement|laporan[-_ ]?keuangan|\bLK\b|[-_/ ]LK[-_ ]|\bFS\b|quarter|kuartal|interim|\bQ[1-4]\b|TW[ -]?[1-4]|semester|juni|june|maret|march|september|bulanan|monthly|public[-_ ]?expose|rups|agm|egm|presentation|paparan", re.I)
YRS = range(2018, 2027)
res = {}
for code, v in d.items():
    years = {"SR": {}, "AR": {}}
    for url, texts in v["docs"].items():
        s = unquote(url) + " " + " ".join(texts)
        ys = sorted({int(y) for y in re.findall(r"(?<!\d)(20[12]\d)(?!\d)", s) if int(y) in YRS})
        if not ys: continue
        fn = unquote(url).split('/')[-1]
        if re.search(r"GRI[-_ ]?(20\d\d|index|content)|20\d\d[-_ ]?\w*GRI|content[-_ ]?index|indeks[-_ ]?gri", fn, re.I):
            fy0 = re.findall(r"(?<!\d)(20[12]\d)(?!\d)", fn)
            years.setdefault("GRI", {}).setdefault(int(fy0[-1]) if fy0 else ys[-1], []).append(url); continue
        if SR.search(fn): is_sr, is_ar = True, False
        elif AR.search(fn) or re.search(r"annual|tahunan", fn, re.I): is_sr, is_ar = False, True
        else: is_sr, is_ar = bool(SR.search(s)), bool(AR.search(s))
        if FS.search(s) and not (is_sr or is_ar): continue
        if FS.search(unquote(url).split('/')[-1]) and not is_sr and not re.search(r"annual|tahunan", s, re.I): continue
        # pakai tahun paling akhir yang disebut di nama file bila ada, else teks
        fy = re.findall(r"(?<!\d)(20[12]\d)(?!\d)", unquote(url).split('/')[-1])
        y = int(fy[-1]) if fy and int(fy[-1]) in YRS else ys[-1]
        fname = unquote(url).split('/')[-1] + " " + " ".join(texts)
        if FS.search(fname) and not re.search(r"annual[-_ ]?report|laporan[-_ ]?tahunan|sustainab|keberlanjutan", fname, re.I): continue
        if is_sr: years["SR"].setdefault(y, []).append(url)
        elif is_ar: years["AR"].setdefault(y, []).append(url)
    res[code] = years
json.dump(res, open(sys.argv[2], "w"), indent=1, default=str)
for code, y in res.items():
    sr = sorted(y["SR"]); ar = sorted(y["AR"])
    print(f"{code:5} SR {sr}  AR {ar}")
