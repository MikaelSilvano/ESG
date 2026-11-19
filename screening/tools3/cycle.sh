#!/bin/bash
# gabung -> klasifikasi -> verifikasi URL baru -> evaluasi
cd "$(dirname "$0")"
export REQUESTS_CA_BUNDLE=$PWD/../certs/bundle.pem
python3 tools/merge.py $EXTRA > /dev/null
python3 tools/classify.py allcrawl.json cand_raw.json > cls.txt
python3 - <<'PY'
import json,glob,os
c=json.load(open('cand_raw.json'))
c={k:{t:{str(y):us for y,us in d.items()} for t,d in v.items()} for k,v in c.items()}
json.dump(c,open('cand.json','w'),indent=1)
done={json.load(open(f))['url'] for f in glob.glob('../screen/pdftxt/*.json')}
urls=[]
for k,v in c.items():
    for t in ('SR','AR','GRI'):
        for y,us in v.get(t,{}).items():
            if 2020<=int(y)<=2025: urls+=us[:6]
if os.path.exists('manual_urls.json'):
    for v in json.load(open('manual_urls.json')).values(): urls+=v
new=sorted(set(u.replace('http://','https://',1) for u in urls if u not in done and u.replace('http://','https://',1) not in done))
json.dump(new,open('urls_new.json','w')); print('URL baru:',len(new))
PY
W=${W:-10} python3 tools/verify.py urls_new.json ver_new.json ../screen/pdftxt > ver_new.log 2>&1
python3 tools/evaluate.py
