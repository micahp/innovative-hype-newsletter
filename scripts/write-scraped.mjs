#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { formatMarkdown } from './scrape-links.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const inputPath = process.argv[2];
const outDir = path.join(__dirname, '..', 'scraped-links');

const raw = fs.readFileSync(inputPath, 'utf8');
const jsonStart = raw.indexOf('[');
let depth = 0;
let jsonEnd = -1;
for (let i = jsonStart; i < raw.length; i++) {
  const c = raw[i];
  if (c === '[') depth++;
  else if (c === ']') {
    depth--;
    if (depth === 0) {
      jsonEnd = i + 1;
      break;
    }
  }
}
const results = JSON.parse(raw.slice(jsonStart, jsonEnd));

fs.mkdirSync(outDir, { recursive: true });

const index = [];
for (const entry of results) {
  const base = entry.slug;
  const jsonFile = path.join(outDir, `${base}.json`);
  const mdFile = path.join(outDir, `${base}.md`);

  if (entry.ok) {
    const { ok, error, ...data } = entry;
    fs.writeFileSync(jsonFile, JSON.stringify(data, null, 2));
    const md = formatMarkdown({ ...data, url: entry.url });
    const screenshotNote = entry.screenshot
      ? `\n**Screenshot:** [${path.basename(entry.screenshot)}](./${path.basename(entry.screenshot)})\n`
      : '';
    fs.writeFileSync(mdFile, md.replace('**Scraped at:**', `${screenshotNote}**Scraped at:**`));
    index.push({ slug: base, url: entry.url, md: `${base}.md`, png: `${base}.png`, ok: true });
  } else {
    index.push({ slug: base, url: entry.url, ok: false, error: entry.error });
  }
}

const indexMd = [
  '# Scraped links index',
  '',
  `Generated: ${new Date().toISOString()}`,
  '',
  '| # | Source | Text | Screenshot |',
  '|---|--------|------|------------|',
  ...index.map((r, i) => {
    const text = r.ok ? `[${r.slug}.md](./${r.md})` : `_failed: ${r.error}_`;
    const shot = r.ok ? `[png](./${r.png})` : '—';
    return `| ${i + 1} | ${r.url} | ${text} | ${shot} |`;
  }),
  '',
].join('\n');

fs.writeFileSync(path.join(outDir, 'INDEX.md'), indexMd);
console.log(`Wrote ${index.filter((r) => r.ok).length}/${results.length} entries to ${outDir}`);
