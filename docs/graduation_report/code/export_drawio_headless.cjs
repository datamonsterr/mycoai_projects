#!/usr/bin/env node
const puppeteer = require('puppeteer');
const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const ROOT = path.resolve(__dirname, '..', '..', '..');
const ENCODE_PY = path.join(ROOT, 'tools', 'drawio-ai-kit', 'vendor', 'encode_drawio_url.py');
const FIG_SRC = path.join(ROOT, 'docs', 'graduation_report', 'latex', 'figures', 'src');
const FIG_OUT = path.join(ROOT, 'docs', 'graduation_report', 'latex', 'figures');

const DIAGRAMS = [
  'ch03_architecture.drawio',
  'ch02_research_pipeline.drawio',
  'threshold_pipeline_diagram.drawio',
];

const encodeUrl = (xmlPath) => {
  return execSync(`python3 "${ENCODE_PY}" "${xmlPath}"`, { encoding: 'utf8' }).trim();
};

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/chromium',
    headless: true,
    args: ['--no-sandbox', '--disable-gpu']
  });

  for (const diagram of DIAGRAMS) {
    const srcPath = path.join(FIG_SRC, diagram);
    const outPath = path.join(FIG_OUT, diagram.replace('.drawio', '.png'));

    if (!fs.existsSync(srcPath)) {
      console.error(`Missing: ${srcPath}`);
      continue;
    }

    const url = encodeUrl(srcPath);
    const page = await browser.newPage();
    try {
      await page.setViewport({ width: 4800, height: 3400, deviceScaleFactor: 3 });
      console.log(`${diagram}...`);
      await page.goto(url, { waitUntil: 'networkidle0', timeout: 60000 });
      await new Promise(r => setTimeout(r, 4000));
      await page.screenshot({ path: outPath, fullPage: false });
      const sz = fs.statSync(outPath).size;
      console.log(`  -> ${outPath} (${sz} bytes)`);
    } finally {
      await page.close();
    }
  }

  await browser.close();
  console.log('All exports done.');
})().catch(err => {
  console.error('Export failed:', err.message);
  process.exit(1);
});
