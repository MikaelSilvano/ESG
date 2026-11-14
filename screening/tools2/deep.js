// deep.js jobs.json out.json : per emiten, buka start, cari halaman laporan (same-domain), klik paginasi/tab, kumpulkan PDF + label
const { chromium } = require('playwright'); const fs = require('fs');
const jobs = JSON.parse(fs.readFileSync(process.argv[2])); const out = {};
const KW = /laporan|report|sustain|keberlanjutan|berkelanjutan|investor|hubungan|publikasi|publication|annual|tahunan|download|unduh|esg|csr|tjsl/i;
(async () => {
  const b = await chromium.launch({proxy: process.env.HTTPS_PROXY ? {server: process.env.HTTPS_PROXY} : undefined});
  const ctx = await b.newContext({acceptDownloads:false});
  async function visit(p, u, pdfs) {
    try { await p.goto(u, {waitUntil:'domcontentloaded', timeout:45000}); } catch(e) { return []; }
    await p.waitForTimeout(3500);
    const grab = async () => { const ls = await p.$$eval('a', as => as.map(a => { let el=a,c=''; for(let i=0;i<4&&el;i++){c=(el.innerText||'').trim(); if(c.length>12)break; el=el.parentElement;} return [a.href, c.replace(/\s+/g,' ').slice(0,160)]; })).catch(()=>[]);
      for (const [h,c] of ls) if (/\.pdf|download|wpdmdl|\/documents\//i.test(h) && !pdfs[h]) pdfs[h]=c; return ls; };
    let ls = await grab();
    for (const t of ['Sustainability Report','Laporan Keberlanjutan','Annual Report','Laporan Tahunan','Sustainability','Keberlanjutan']) {
      const el = await p.$(`button:has-text("${t}"), [role=tab]:has-text("${t}"), li:has-text("${t}") >> nth=0`).catch(()=>null);
      if (el) { try { await el.click({timeout:2000}); await p.waitForTimeout(1500); ls = ls.concat(await grab()); } catch(e){} }
    }
    for (let n=2;n<=8;n++) { const el = await p.$(`a:text-is("${n}"), button:text-is("${n}")`).catch(()=>null); if (!el) break; try { await el.click({timeout:2000}); await p.waitForTimeout(1500); await grab(); } catch(e) { break; } }
    return ls;
  }
  async function job(code, start) {
    const p = await ctx.newPage(); const pdfs = {}; const host = new URL(start).hostname.replace(/^www\./,'');
    const ls = await visit(p, start, pdfs);
    const cand = [...new Set(ls.filter(([h,c]) => { try { return new URL(h).hostname.replace(/^www\./,'')===host && KW.test(h+' '+c) && !/\.pdf/i.test(h); } catch(e){return false;} }).map(x=>x[0].split('#')[0]))].slice(0,14);
    const seen = new Set([start]); let n2 = [];
    for (const u of cand) { if (seen.has(u)) continue; seen.add(u); const l2 = await visit(p, u, pdfs); n2 = n2.concat(l2); }
    const cand2 = [...new Set(n2.filter(([h,c]) => { try { return new URL(h).hostname.replace(/^www\./,'')===host && /laporan|report|sustain|keberlanjutan|annual|tahunan/i.test(h+' '+c) && !/\.pdf/i.test(h); } catch(e){return false;} }).map(x=>x[0].split('#')[0]))].filter(u=>!seen.has(u)).slice(0,10);
    for (const u of cand2) { seen.add(u); await visit(p, u, pdfs); }
    out[code] = {start, visited:[...seen], docs: Object.fromEntries(Object.entries(pdfs).map(([h,c])=>[h,[c]]))};
    await p.close(); fs.writeFileSync(process.argv[3], JSON.stringify(out,null,1));
    console.error(code, Object.keys(pdfs).length, seen.size);
  }
  const C = +(process.env.CONC||6); let i = 0;
  await Promise.all(Array.from({length:C}, async () => { while (i < jobs.length) { const [c,s] = jobs[i++]; await Promise.race([job(c,s), new Promise(r=>setTimeout(r, 240000))]); } }));
  fs.writeFileSync(process.argv[3], JSON.stringify(out,null,1)); await b.close(); process.exit(0);
})();
