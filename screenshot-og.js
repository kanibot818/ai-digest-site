
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1200, height: 630 } });
  await page.goto('http://localhost:8199/og-image.html', { waitUntil: 'networkidle' });
  // Wait for fonts to load
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(1000);
  await page.screenshot({ path: '/home/alexabc/ai-digest-site/og-image.png', type: 'png' });
  await browser.close();
  console.log('Screenshot done');
})();
