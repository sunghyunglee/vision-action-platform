// node render.js <svg> <png> <scale>
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [svgPath, pngPath, scale] = process.argv.slice(2);
  const svg = fs.readFileSync(svgPath, 'utf8');
  const browser = await chromium.launch();
  const page = await browser.newPage({ deviceScaleFactor: Number(scale || 2) });
  await page.setContent(`<html><body style="margin:0;background:#fff">${svg}</body></html>`);
  await page.locator('svg').first().screenshot({ path: pngPath });
  await browser.close();
})();
