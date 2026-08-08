import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const outputDir = path.resolve('paper_revision/assets/screenshots');
fs.mkdirSync(outputDir, { recursive: true });

const pages = [
  ['01_监测驾驶舱.png', '/monitoring', '监测驾驶舱'],
  ['02_企业识别.png', '/recognition', '企业识别'],
  ['03_产业分析.png', '/industry-analysis', '产业分析'],
  ['04_模型评估.png', '/model-evaluation', '模型评估'],
  ['05_风险中心.png', '/risks', '风险中心'],
];

const browser = await chromium.launch({
  headless: true,
  executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
});
const context = await browser.newContext({
  viewport: { width: 1600, height: 1000 },
  deviceScaleFactor: 1,
  colorScheme: 'light',
});

const manifest = [];
for (const [filename, route, label] of pages) {
  const page = await context.newPage();
  const url = `http://127.0.0.1:5173${route}`;
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60_000 });
  await page.waitForTimeout(1_200);
  const bodyText = await page.locator('body').innerText();
  const mode = /演示|模拟|demo/i.test(bodyText)
    ? '界面含演示或模拟标识'
    : /历史快照|离线快照/.test(bodyText)
      ? '历史或离线快照'
      : '当前系统界面（数据模式未在页面显式标注）';
  const output = path.join(outputDir, filename);
  await page.screenshot({ path: output, fullPage: false });
  manifest.push({ label, route, url, filename, mode, captured_at: new Date().toISOString() });
  await page.close();
}

await browser.close();
fs.writeFileSync(
  path.resolve('paper_revision/artifacts/system_screenshot_manifest.json'),
  JSON.stringify(manifest, null, 2),
  'utf8',
);
console.log(JSON.stringify({ screenshots: manifest.length, manifest }, null, 2));
