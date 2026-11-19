// ptpp.js url... : buka halaman, coba select/paginasi, kumpulkan tautan PDF + konteks
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({proxy: process.env.HTTPS_PROXY ? {server: process.env.HTTPS_PROXY} : undefined});
  const p = await b.newPage();
  const all = new Map();
  const grab = async () => {
    const ls = await p.$$eval('a', as => as.map(a => [a.href, ((a.closest('div,li,tr') || a).innerText || '').replace(/\s+/g, ' ').slice(0, 100)])).catch(() => []);
    for (const [h, c] of ls) if (/\.pdf/i.test(h)) all.set(h, c);
  };
  for (const u of process.argv.slice(2)) {
    try { await p.goto(u, {waitUntil: 'networkidle', timeout: 60000}); } catch (e) {}
    await p.waitForTimeout(3000);
    await grab();
    const sels = await p.$$('select');
    for (const s of sels) {
      const opts = await s.$$eval('option', os => os.map(o => o.value)).catch(() => []);
      for (const o of opts) { try { await s.selectOption(o); await p.waitForTimeout(2000); await grab(); } catch (e) {} }
    }
    for (let n = 2; n <= 12; n++) {
      const el = await p.$(`.pagination a:text-is("${n}"), .page-link:text-is("${n}"), a:text-is("${n}")`).catch(() => null);
      if (!el) break;
      try { await el.click({timeout: 3000}); await p.waitForTimeout(2500); await grab(); } catch (e) { break; }
    }
  }
  console.log(JSON.stringify([...all]));
  await b.close();
})();
