import sys, json, re, requests, concurrent.futures as cf
from urllib.parse import urlparse
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
def get(u):
    try:
        r=requests.get(u,headers=UA,timeout=25)
        return r.text if r.status_code==200 else ""
    except Exception: return ""
def probe(job):
    code,start=job
    p=urlparse(start); base=f"{p.scheme}://{p.netloc}"
    maps=set(re.findall(r"(?im)^sitemap:\s*(\S+)",get(base+"/robots.txt")))
    maps|={base+"/sitemap.xml",base+"/sitemap_index.xml",base+"/wp-sitemap.xml"}
    seen=set(); docs={}; pages=[]
    todo=list(maps)
    while todo and len(seen)<60:
        m=todo.pop(); 
        if m in seen: continue
        seen.add(m); x=get(m)
        if not x or "<" not in x: continue
        for loc in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>",x):
            loc=loc.replace("&amp;","&")
            if loc.endswith(".xml") or "sitemap" in loc.lower(): 
                if len(seen)+len(todo)<120: todo.append(loc)
            elif re.search(r"\.pdf(\?|$)",loc,re.I): docs[loc]=["sitemap"]
            elif re.search(r"sustainab|keberlanjutan|annual|tahunan|laporan|report",loc,re.I): pages.append(loc)
    return code,base,docs,pages
jobs=[l.split() for l in open(sys.argv[1]) if l.strip()]
out={}
with cf.ThreadPoolExecutor(12) as ex:
    for code,base,docs,pages in ex.map(probe,jobs):
        k=code.split('#')[0]
        o=out.setdefault(k,{"start":base,"pages":0,"docs":{},"report_pages":[]})
        o["docs"].update(docs); o["report_pages"]+=pages
        if docs or pages: print(code,len(docs),len(pages),flush=True)
json.dump(out,open(sys.argv[2],"w"),indent=1)
