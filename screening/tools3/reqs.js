const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({proxy: process.env.HTTPS_PROXY ? {server: process.env.HTTPS_PROXY} : undefined});
  const p = await b.newPage(); const reqs = [];
  p.on('response', r => { const ct=r.headers()['content-type']||''; if (/json|pdf/.test(ct)) reqs.push(r.status()+' '+ct.slice(0,20)+' '+r.url()); });
  try { await p.goto(process.argv[2], {waitUntil:'networkidle', timeout:60000}); } catch(e) { console.log('ERR', e.message.slice(0,80)); }
  await p.waitForTimeout(4000);
  const links = await p.$$eval('a', as => as.map(a => a.href+' | '+(a.innerText||'').trim().slice(0,50)));
  console.log('TITLE', await p.title()); reqs.forEach(x=>console.log('REQ',x)); links.filter(l=>/pdf|laporan|report|download|unduh/i.test(l)).slice(0,40).forEach(l=>console.log('A',l));
  await b.close();
})();
