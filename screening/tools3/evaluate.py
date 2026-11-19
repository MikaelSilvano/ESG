import json, glob, re, os
from urllib.parse import unquote
cand = json.load(open('cand.json')); comps = json.load(open('companies.json'))
man = json.load(open('manual_urls.json'))
EXC = json.load(open('exclude.json')) if os.path.exists('exclude.json') else {}
LBL = json.load(open('labels.json')) if os.path.exists('labels.json') else {}
ALIAS = {**(json.load(open('../screen/alias.json')) if os.path.exists('../screen/alias.json') else {}), **(json.load(open('alias.json')) if os.path.exists('alias.json') else {})}
V = {}
for f in glob.glob('../screen/pdftxt/*.json'):
    r = json.load(open(f)); V[r['url']] = r
TY = re.compile(r"(annual\s+report|laporan\s+tahunan|sustainability\s+report|laporan\s+keberlanjutan|integrated\s+report|ESG\s+report|tahun\s+buku)\s*(?:tahun\s*)?(20[12]\d)", re.I)
TY2 = re.compile(r"(?<!\d)(20[12]\d)\s+(annual\s+report|laporan\s+tahunan|sustainability\s+report|laporan\s+keberlanjutan|integrated\s+report)", re.I)
def getv(u):
    r = V.get(u)
    if r is None and u.startswith('http://'):
        u = 'https://' + u[7:]; r = V.get(u)
    if r and r.get('note') == 'bukan PDF' and u in ALIAS: return V.get(ALIAS[u]), ALIAS[u]
    return r, u
KWY = re.compile(r"(?:(?<![a-z])sr|(?<![a-z])ar|report|tahunan|keberlanjutan|berkelanjutan|sustainability|annual|lst)[-_ %20]*(?:[a-z]{2,6}[-_ %20]+){0,2}(20[12]\d)(?!\d)", re.I)
def kwyear(u):
    m = KWY.findall(unquote(u).split('/')[-1])
    return int(m[0]) if m else None
def fyear(u):
    ys = re.findall(r"(?<!\d)(20[12]\d)(?!\d)", unquote(u).split('/')[-1])
    return int(ys[-1]) if ys else None
def gri_ok(r): return (r.get('gri_index') or 0) >= 1 or ((r.get('gri_stmt') or 0) >= 1 and (r.get('gri_codes') or 0) >= 15)
def kind(r, hint, u):
    fn = unquote(u).split('/')[-1]
    if re.search(r"(^|[-_ .])(ar[-_ ]?sr|arsr)([-_ .]|\d)|\bar\W+(dan|and|&)\W+sr\b|annual.{0,20}sustainab|tahunan.{0,20}keberlanjutan|integrated", fn, re.I): return 'ARSR'
    if re.search(r"sustainab|sustanib|keberlanjutan|berkelanjutan|(^|[-_ ])SR[-_ .0-9]|ESG[-_ ]?report|\bLST\b", fn, re.I): return 'SR'
    if re.search(r"annual|tahunan|(^|[-_ ])AR[-_ .0-9]|^AR", fn, re.I): return 'AR'
    c = r.get('cover') or ''
    if re.search(r"annual\s+report|laporan\s+tahunan", c, re.I) and re.search(r"sustainability\s+report|laporan\s+keberlanjutan", c, re.I) and hint not in ('SR', 'AR'): return 'ARSR'
    if hint in ('SR', 'AR'): return hint
    if re.search(r"sustainability\s+report|laporan\s+keberlanjutan|ESG\s+report", c, re.I): return 'SR'
    return 'AR'
def readable(r): return (r.get('chars') or 0) >= 300 * (r.get('pages') or 1) * 0.3
SRY = list(range(2020, 2025)); ARY = list(range(2020, 2026))
out = {}
for c in comps:
    k = c['kode']; cd = cand.get(k, {'SR': {}, 'AR': {}})
    items = []
    for t in ('SR', 'AR', 'GRI'):
        for y, us in cd.get(t, {}).items():
            for u in us: items.append((t, int(y), u))
    for u in man.get(k, []): items.append(('?', fyear(u), u))
    docs = []
    seen = set()
    for hint, y, u in items:
        r, ru = getv(u)
        if not r or ru in seen or u in EXC.get(k, {}) or ru in EXC.get(k, {}): continue
        seen.add(ru)
        if r.get('status') != 200 or (r.get('pages') or 0) < (2 if hint == 'GRI' else 20): continue
        lb0 = LBL.get(u) or LBL.get(ru)
        m = TY.findall(r.get('cover') or '')
        ty = int(m[0][1]) if m else None
        if ty is None and kwyear(ru) is None and not lb0:
            m2 = TY2.findall((r.get('cover') or '')[:250])
            ty = int(m2[0][0]) if m2 else None
        lb = LBL.get(u) or LBL.get(ru)
        if lb: ty = lb['year']
        yr = ty or kwyear(ru) or y or (int(r['cover_years'][-1]) if r.get('cover_years') else None)
        if yr is None: continue
        kd = 'GRI' if hint == 'GRI' else (lb['kind'] if lb else kind(r, hint, ru))
        docs.append({'url': ru, 'year': yr, 'year_src': ('label tautan di situs' if lb else 'judul sampul' if ty else 'nama file'), 'label': (lb or {}).get('label'), 'kind': kd, 'pages': r.get('pages'),
                     'gri': gri_ok(r), 'gri_index': r.get('gri_index'), 'gri_codes': r.get('gri_codes'), 'gri_stmt': r.get('gri_stmt'),
                     'snip': (r.get('gri_index_snip') or r.get('gri_stmt_snip') or '')[:200], 'cover': (r.get('cover') or '')[:160], 'chars': r.get('chars'), 'readable': readable(r)})
    sr = {}; ar = {}
    for y in SRY:
        c1 = [d for d in docs if d['year'] == y and d['kind'] == 'SR']
        c2 = [d for d in docs if d['year'] == y and d['kind'] in ('ARSR', 'AR') and (d['gri_index'] or 0) >= 1]
        c3 = [d for d in docs if d['year'] == y and d['kind'] == 'ARSR']
        g1 = [d for d in c1 if d['gri']]
        gx = [d for d in docs if d['year'] == y and d['kind'] == 'GRI' and d['gri']]
        if g1: sr[y] = ('SR', g1[0])
        elif c1 and gx: sr[y] = ('SR + indeks GRI terpisah', c1[0])
        elif c2: sr[y] = ('Terintegrasi di AR (indeks GRI)', c2[0])
        elif c1 and not any(d['readable'] for d in c1): sr[y] = ('SR (teks tak terbaca, perlu cek manual)', c1[0])
        elif c1: sr[y] = ('SR tanpa GRI', c1[0])
        elif c3: sr[y] = ('AR+SR tanpa indeks GRI', c3[0])
        else: sr[y] = (None, None)
    for y in ARY:
        a = [d for d in docs if d['year'] == y and d['kind'] in ('AR', 'ARSR') and (d['pages'] or 0) >= 50]
        def _rank(d):
            c = d['cover'] or ''
            return (bool(re.search(r"laporan\s*tahunan|annual\s*report|l\s*a\s*p\s*o\s*r\s*a\s*n\s+t\s*a\s*h\s*u\s*n\s*a\s*n|integrated|terintegrasi", c, re.I)),
                    not re.search(r"SECURITIES AND EXCHANGE|6-K|EDGAR|20-F|^Company:", c + d['url'], re.I), d['pages'] or 0)
        a.sort(key=_rank, reverse=True)
        ar[y] = a[0] if a else None
    out[k] = {'nama': c['nama'], 'sektor': c['sektor'], 'papan': c['papan'], 'sr': sr, 'ar': ar, 'docs': docs}
json.dump(out, open('eval.json', 'w'), indent=1, default=str)
def sc(v):
    return {'SR': 'S', 'SR + indeks GRI terpisah': 'G', 'Terintegrasi di AR (indeks GRI)': 'I', 'SR tanpa GRI': 'g', 'AR+SR tanpa indeks GRI': 'x', 'SR (teks tak terbaca, perlu cek manual)': '?'}.get(v[0], '.')
for k, v in out.items():
    s = ''.join(sc(v['sr'][y]) for y in SRY); a = ''.join('A' if v['ar'][y] else '.' for y in ARY)
    if s == '.....' and a == '......': continue
    print(f"{k:5} SR {s} AR {a}")
