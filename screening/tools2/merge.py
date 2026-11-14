"""Gabungkan hasil semua crawler (lama & baru) -> allcrawl.json {kode: {docs: {url: [teks]}}}"""
import json, sys, os
codes = [d['kode'] for d in json.load(open('companies.json'))]
srcs = ['../screen/crawl1.json', '../screen/crawl3.json', '../screen/wp.json', 'wp.json', 'sitemap.json', 'js/render_out.json'] + sys.argv[1:]
out = {k: {'start': '', 'pages': 0, 'docs': {}} for k in codes}
for f in srcs:
    if not os.path.exists(f):
        continue
    for k, v in json.load(open(f)).items():
        k = k.split('#')[0]
        if k not in out:
            continue
        for u, t in v.get('docs', {}).items():
            out[k]['docs'].setdefault(u, [])
            for x in t:
                if x not in out[k]['docs'][u]:
                    out[k]['docs'][u].append(x)
json.dump(out, open('allcrawl.json', 'w'), indent=0)
print({k: len(v['docs']) for k, v in out.items()})
