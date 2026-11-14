// Render halaman (JS) dan kumpulkan tautan PDF + halaman lanjutan yang relevan.
const { chromium } = require('playwright');
const fs = require('fs');
const [,, jobsFile, outFile, maxPagesArg] = process.argv;
const MAXP = parseInt(maxPagesArg || '25');
const KW = /sustainab|keberlanjutan|annual|tahunan|laporan|report|investor|hubungan|publikasi|publication|download|unduh|esg|csr|financial|keuangan|informasi|governance|\bir\b|\/ir\//i;
(async () => {
  const jobs = JSON.parse(fs.readFileSync(jobsFile));
  const browser = await chromium.launch({ proxy: { server: process.env.HTTPS_PROXY } });
  const out = {};
  const conc = parseInt(process.env.CONC || "4");
  let idx = 0;
  async function worker() {
    while (idx < jobs.length) {
      const [code, start] = jobs[idx++];
      const ctx = await browser.newContext({ ignoreHTTPSErrors: false, userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36' });
      const page = await ctx.newPage();
      const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return ''; } };
      const base = host(start);
      const seen = new Set(), queue = [[start, 0]], docs = {};
      let pages = 0, errors = [];
      while (queue.length && pages < MAXP) {
        const [url, d] = queue.shift();
        if (seen.has(url)) continue; seen.add(url);
        try {
          const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
          await page.waitForTimeout(parseInt(process.env.WAIT || "2500"));
          pages++;
          const st = resp ? resp.status() : 0;
          if (st >= 400) { errors.push(`${st} ${url}`); continue; }
          const links = await page.$$eval('a[href]', as => as.map(a => [a.href, (a.innerText || a.title || '').trim().slice(0, 150)]));
          for (const [h, t] of links) {
            if (!h || h.startsWith('mailto') || h.startsWith('javascript')) continue;
            if (/\.pdf(\?|$)|download|\/files?\/|\/uploads?\/|wpdmdl|getfile|attachment|storage\//i.test(h) && /20(19|2\d)/.test(h + ' ' + t)) {
              (docs[h] = docs[h] || new Set()).add(t); continue;
            }
            if (/\.pdf(\?|$)/i.test(h)) { (docs[h] = docs[h] || new Set()).add(t); continue; }
            const hb = host(h);
            if (hb !== base && !hb.endsWith(base)) continue;
            if (d < 2 && KW.test(h + ' ' + t) && !seen.has(h.split('#')[0])) queue.push([h.split('#')[0], d + 1]);
          }
        } catch (e) { errors.push(String(e).slice(0, 120) + ' ' + url); }
      }
      out[code] = { start, pages, errors: errors.slice(0, 5), docs: Object.fromEntries(Object.entries(docs).map(([k, v]) => [k, [...v]])) };
      console.log(code, pages, Object.keys(docs).length, errors.length);
      await ctx.close();
      fs.writeFileSync(outFile, JSON.stringify(out, null, 1));
    }
  }
  await Promise.all(Array.from({ length: conc }, worker));
  await browser.close();
})();
