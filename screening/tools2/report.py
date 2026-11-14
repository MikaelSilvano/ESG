import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
def cl(x): return ILLEGAL_CHARACTERS_RE.sub('', x) if isinstance(x, str) else x
E = json.load(open('eval.json'))
notes = json.load(open('notes2.json'))
SRY = [str(y) for y in range(2020, 2025)]; ARY = [str(y) for y in range(2020, 2026)]
G = PatternFill('solid', fgColor='C6EFCE'); R = PatternFill('solid', fgColor='FFC7CE'); Y = PatternFill('solid', fgColor='FFEB9C'); Gr = PatternFill('solid', fgColor='EDEDED'); H = PatternFill('solid', fgColor='D9E1F2')
thin = Side(style='thin', color='BFBFBF'); B = Border(left=thin, right=thin, top=thin, bottom=thin)
SRLBL = {'SR': 'SR+GRI', 'SR + indeks GRI terpisah': 'SR + indeks GRI terpisah', 'Terintegrasi di AR (indeks GRI)': 'AR+GRI', 'SR tanpa GRI': 'SR, GRI tdk ada', 'AR+SR tanpa indeks GRI': 'AR/SR, GRI tdk ada', 'SR (teks tak terbaca, perlu cek manual)': 'Cek manual'}
def status(k, v):
    srok = [v['sr'][y][0] in ('SR', 'SR + indeks GRI terpisah', 'Terintegrasi di AR (indeks GRI)') for y in SRY]
    arok = [bool(v['ar'][y]) for y in ARY]
    nogri = [v['sr'][y][0] in ('SR tanpa GRI', 'AR+SR tanpa indeks GRI') for y in SRY]
    ov = notes.get(k, {})
    if 'status' in ov: return ov['status']
    if all(srok) and all(arok): return 'LAYAK'
    if any(nogri): return 'GUGUR (SR tanpa GRI)'
    # AR tahun itu ada & terbaca tetapi tidak menyebut GRI sama sekali, dan SR terpisah tidak ditemukan
    weak = []
    for y in SRY:
        if v['sr'][y][0] is None and v['ar'][y]:
            ars = [d for d in v['docs'] if str(d['year']) == y and d['kind'] in ('AR', 'ARSR')]
            if ars and all(d['readable'] and (d['gri_stmt'] or 0) == 0 and (d['gri_codes'] or 0) < 15 for d in ars): weak.append(y)
    found = sum(srok) + sum(arok)
    if weak and found + len(weak) >= 6: return 'KEMUNGKINAN GUGUR'
    if found == 0: return 'BELUM TERVERIFIKASI'
    if (11 - found) <= 2: return 'HAMPIR (perlu 1-2 dokumen)'
    return 'BELUM LENGKAP'
wb = Workbook(); ws = wb.active; ws.title = 'Ringkasan'
hdr = ['No', 'Kode', 'Nama', 'Sektor', 'Status'] + [f'SR {y}' for y in SRY] + [f'AR {y}' for y in ARY] + ['Catatan']
ws.append(hdr)
order = {'LAYAK': 0, 'HAMPIR (perlu 1-2 dokumen)': 1, 'BELUM LENGKAP': 2, 'KEMUNGKINAN GUGUR': 3, 'GUGUR': 4, 'BELUM TERVERIFIKASI': 5}
rows = []
for i, (k, v) in enumerate(E.items(), 1):
    st = status(k, v); rows.append((order.get('GUGUR' if st.startswith('GUGUR') else st, 6), i, k, v, st))
rows.sort()
for _, i, k, v, st in rows:
    cells = [i, k, v['nama'], v['sektor'], st]
    for y in SRY:
        t, d = v['sr'][y]; cells.append(SRLBL.get(t, '-') if t else '-')
    for y in ARY:
        cells.append('Ada' if v['ar'][y] else '-')
    cells.append(notes.get(k, {}).get('catatan', ''))
    ws.append(cells)
    r = ws.max_row
    for j, y in enumerate(SRY):
        t, d = v['sr'][y]; c = ws.cell(r, 6 + j)
        if d: c.hyperlink = d['url']
        c.fill = G if t in ('SR', 'SR + indeks GRI terpisah', 'Terintegrasi di AR (indeks GRI)') else R if t in ('SR tanpa GRI', 'AR+SR tanpa indeks GRI') else Y if t else Gr
    for j, y in enumerate(ARY):
        d = v['ar'][y]; c = ws.cell(r, 11 + j)
        if d: c.hyperlink = d['url']
        c.fill = G if d else Gr
    sc = ws.cell(r, 5); sc.fill = G if st == 'LAYAK' else Y if st.startswith('HAMPIR') else R if 'GUGUR' in st else Gr
for c in ws[1]: c.font = Font(bold=True); c.fill = H; c.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
for row in ws.iter_rows(min_row=1):
    for c in row: c.border = B
widths = [5, 7, 32, 14, 24] + [11] * 11 + [70]
for j, w in enumerate(widths, 1): ws.column_dimensions[get_column_letter(j)].width = w
for r in range(2, ws.max_row + 1): ws.cell(r, 17).alignment = Alignment(wrap_text=True, vertical='top')
ws.freeze_panes = 'C2'; ws.auto_filter.ref = ws.dimensions
# Bukti
wb2 = wb.create_sheet('Bukti per dokumen')
wb2.append(['Kode', 'Jenis', 'Tahun buku', 'Sumber tahun', 'Halaman', 'Indeks GRI ditemukan', 'Jml kode GRI', 'Memenuhi syarat GRI', 'Cuplikan GRI / indeks', 'Sampul (awal teks)', 'URL'])
for _, i, k, v, st in rows:
    for d in sorted(v['docs'], key=lambda d: (d['kind'], d['year'])):
        if not (2020 <= d['year'] <= 2025): continue
        wb2.append([cl(x) for x in [k, d['kind'], d['year'], d['year_src'], d['pages'], d['gri_index'], d['gri_codes'], 'Ya' if d['gri'] else 'Tidak', d['snip'], d['cover'], d['url']]])
        c = wb2.cell(wb2.max_row, 11); c.hyperlink = d['url']; c.font = Font(color='0563C1', underline='single')
for c in wb2[1]: c.font = Font(bold=True); c.fill = H
for j, w in enumerate([7, 7, 10, 12, 9, 10, 10, 10, 60, 50, 60], 1): wb2.column_dimensions[get_column_letter(j)].width = w
wb2.freeze_panes = 'A2'; wb2.auto_filter.ref = wb2.dimensions
# Bukti pencarian (situs terblokir)
wb3 = wb.create_sheet('Bukti dari pencarian web')
wb3.append(['Kode', 'Temuan', 'Sumber'])
for k, v in notes.items():
    for t, src in v.get('web', []):
        wb3.append([k, t, src])
        if src.startswith('http'): wb3.cell(wb3.max_row, 3).hyperlink = src
for c in wb3[1]: c.font = Font(bold=True); c.fill = H
for j, w in enumerate([7, 90, 80], 1): wb3.column_dimensions[get_column_letter(j)].width = w
# Metode
m = wb.create_sheet('Metode & batasan')
for line in json.load(open('method2.json')): m.append([line])
m.column_dimensions['A'].width = 140
for r in m.iter_rows():
    for c in r: c.alignment = Alignment(wrap_text=True, vertical='top')
import sys
wb.save(sys.argv[1] if len(sys.argv) > 1 else 'Screening_Dataset_ESG_2.xlsx'); print('ok')
from collections import Counter
print(Counter(r[4] for r in rows))
