/* ============================================================
   カード画像の書き出し。cards.html の .card を1枚ずつPNGにする。
   サイトの動作には不要な補助ツール。Node と Playwright が要る。

     node tools/cards.js                     必修から24枚
     node tools/cards.js "must=1&limit=50"   条件はcards.htmlと同じ
     node tools/cards.js "cats=bunker" out/  出力先を変える
   ============================================================ */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const query = process.argv[2] || 'must=1&limit=24';
const outDir = path.resolve(process.argv[3] || 'cards-out');
const src = 'file://' + path.join(__dirname, '..', 'cards.html') + '?' + query;

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const exe = process.env.PLAYWRIGHT_CHROMIUM || '/opt/pw-browsers/chromium';
  const b = await chromium.launch(fs.existsSync(exe) ? { executablePath: exe } : {});
  const p = await (await b.newContext({
    colorScheme: 'light',
    viewport: { width: 1180, height: 1200 },
    deviceScaleFactor: 2                       // 2倍で撮るので印刷にも耐える
  })).newPage();

  await p.goto(src, { waitUntil: 'load' });

  // 画面では一覧、撮影のときは1枚ずつ幅1080pxに固定する
  await p.addStyleTag({ content:
    '.masthead,.cd__lede{display:none}' +
    '.cd{max-width:none;padding:0}' +
    '.cd__grid{grid-template-columns:1080px;justify-content:start;gap:24px}' +
    '.card{width:1080px;max-width:none}' });

  await p.waitForTimeout(1200);                // Webフォントの読み込みを待つ

  const cards = await p.$$('.card');
  for (const c of cards) {
    const id = await c.getAttribute('data-id');
    await c.screenshot({ path: path.join(outDir, id + '.png') });
  }
  console.log(cards.length + '枚を書き出しました → ' + outDir);
  await b.close();
})();
