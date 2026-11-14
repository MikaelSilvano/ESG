"""verify_local.py URL LOCALPDF  -> isi cache pdftxt untuk URL dari file lokal (unduhan manual)."""
import sys, os, json, hashlib, importlib.util
spec = importlib.util.spec_from_file_location("v", os.path.join(os.path.dirname(__file__), "verify.py"))
sys.argv = [sys.argv[0], "x", "x", "../screen/pdftxt"] + sys.argv[1:]
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
url, path = sys.argv[4], sys.argv[5]
class R:
    status_code = 200; url = url; headers = {"content-type": "application/pdf"}
    def iter_content(self, n):
        with open(path, "rb") as f:
            while True:
                b = f.read(n)
                if not b: break
                yield b
v.requests.get = lambda *a, **k: R()
jf = f"../screen/pdftxt/{hashlib.md5(url.encode()).hexdigest()[:12]}.json"
if os.path.exists(jf): os.remove(jf)
r = v.check(url); r["note"] = (r.get("note") or "") + " (unduh manual)"
json.dump(r, open(jf, "w"))
print({k: r.get(k) for k in ("status","pages","cover_years","gri_index","gri_codes","note")})
