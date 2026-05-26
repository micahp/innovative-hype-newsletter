#!/usr/bin/env node
/** Formats scraped page JSON into markdown files. */

export function slugFromUrl(url) {
  try {
    const u = new URL(url);
    const host = u.hostname.replace(/\./g, '-');
    const path = u.pathname.replace(/\//g, '-').replace(/^-|-$/g, '');
    return `${host}-${path}`.slice(0, 120);
  } catch {
    return url.replace(/[^a-zA-Z0-9.-]/g, '_').slice(0, 120);
  }
}

export function formatMarkdown(data) {
  const lines = [
    `# Scraped content`,
    ``,
    `**Source:** ${data.url}`,
    `**Title:** ${data.title || 'N/A'}`,
    `**Scraped at:** ${data.scrapedAt || new Date().toISOString()}`,
    ``,
  ];

  if (data.og?.description) {
    lines.push(`## Open Graph`, ``, data.og.description, ``);
  }
  if (data.og?.image && !data.og.image.includes('default/v2/og')) {
    lines.push(`**OG image:** ${data.og.image}`, ``);
  }
  if (data.og?.video) {
    lines.push(`**OG video:** ${data.og.video}`, ``);
  }

  const allMedia = new Set();
  const collectMedia = (t) => {
    for (const img of t.images || []) allMedia.add(img);
    for (const vid of t.videos || []) if (vid && !vid.startsWith('blob:')) allMedia.add(vid);
    for (const l of t.links || []) if (/\.(jpg|jpeg|png|gif|webp|mp4|webm)/i.test(l)) allMedia.add(l);
  };

  if (data.post) {
    lines.push(`## Post`, ``);
    if (data.post.author) lines.push(`**Author:** ${data.post.author}`, ``);
    if (data.post.datetime) lines.push(`**Date:** ${data.post.datetime}`, ``);
    lines.push(data.post.text || '', ``);
    collectMedia(data.post);
    if (data.post.links?.length) {
      lines.push(`### Links in post`, ``);
      for (const l of data.post.links) lines.push(`- ${l}`);
      lines.push(``);
    }
  }

  if (data.tweets?.length) {
    for (const t of data.tweets) {
      lines.push(`---`, ``, `## ${t.index === 0 ? 'Main post' : `Reply ${t.index}`}`, ``);
      if (t.author) lines.push(`**Author:** ${t.author}`, ``);
      if (t.datetime) lines.push(`**Date:** ${t.datetime}`, ``);
      lines.push(t.text || '', ``);
      collectMedia(t);
      if (t.links?.length) {
        lines.push(`**Links:**`, ...t.links.map((l) => `- ${l}`), ``);
      }
    }
  }

  if (data.comments?.length) {
    lines.push(`## Comments`, ``);
    for (const c of data.comments) {
      lines.push(`### ${c.author || 'Anonymous'}`, ``);
      if (c.datetime) lines.push(`*${c.datetime}*`, ``);
      lines.push(c.text || '', ``);
      collectMedia(c);
    }
  }

  const mediaList = [...allMedia];
  if (mediaList.length) {
    lines.push(`## Media`, ``);
    for (const m of mediaList) lines.push(`- ${m}`);
    lines.push(``);
  }

  if (data.fallbackText && (!data.tweets?.length && !data.post)) {
    lines.push(`## Full page text (fallback)`, ``, '```', data.fallbackText, '```', ``);
  }

  return lines.join('\n');
}
