// buka halaman, klik semua tombol "load more"/paginasi, kumpulkan semua tautan /documents/ beserta label
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({proxy: process.env.HTTPS_PROXY ? {server: process.env.HTTPS_PROXY} : undefined});
  const p = await b.newPage(); const all = new Map();
  const grab = async () => { const ls = await p.$$eval('a', as => as.map(a => { let el=a, c=''; for (let i=0;i<4&&el;i++){c=(el.innerText||'').trim(); if(c.length>12)break; el=el.parentElement;} return [a.href, c.replace(/\s+/g,' ').slice(0,140)]; })); for (const [h,c] of ls) if (/\.pdf/i.test(h) && !all.has(h)) all.set(h,c); };
  await p.goto(process.argv[2], {waitUntil:'domcontentloaded', timeout:60000}); await p.waitForTimeout(5000); await grab();
  for (let i=0;i<40;i++) {
    const btn = await p.$('text=/^(Load more|Muat lebih|Lihat lebih|Show more|Next|Berikutnya|›|»)$/i');
    if (!btn) break; try { await btn.click({timeout:3000}); await p.waitForTimeout(2500); await grab(); } catch(e) { break; }
  }
  // paginasi bernomor
  for (let n=2;n<=15;n++) { const el = await p.$(`a:text-is("${n}"), button:text-is("${n}")`); if (!el) break; try { await el.click({timeout:3000}); await p.waitForTimeout(2500); await grab(); } catch(e) { break; } }
  console.log(JSON.stringify([...all], null, 0)); await b.close();
})();
