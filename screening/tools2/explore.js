// explore.js url... : cetak tautan menu (kata kunci) + PDF beserta labelnya
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({proxy: process.env.HTTPS_PROXY ? {server: process.env.HTTPS_PROXY} : undefined});
  const ctx = await b.newContext({acceptDownloads:false});
  const out = {};
  await Promise.all(process.argv.slice(2).map(async u => {
    const p = await ctx.newPage();
    try {
      const r = await p.goto(u, {waitUntil:'domcontentloaded', timeout:60000});
      await p.waitForTimeout(5000);
      const links = await p.$$eval('a', as => as.map(a => {
        let el=a, ctx=''; for (let i=0;i<4 && el;i++){ ctx=(el.innerText||'').trim(); if (ctx.length>12) break; el=el.parentElement; }
        return [a.href, ctx.replace(/\s+/g,' ').slice(0,120)]; }));
      const kw = process.env.ALL ? /./ : /investor|hubungan|report|laporan|sustain|keberlanjutan|annual|tahunan|publikasi|publication|download|unduh|\.pdf/i;
      const seen=new Set();
      out[u] = {status: r && r.status(), title: await p.title(), links: links.filter(l => kw.test(l[0]+' '+l[1]) && !seen.has(l[0]) && seen.add(l[0])).slice(0,+(process.env.LIMIT||60))};
    } catch(e) { out[u] = 'ERR '+e.message.slice(0,120); }
    await p.close();
  }));
  console.log(JSON.stringify(out, null, 1));
  await b.close();
})();
