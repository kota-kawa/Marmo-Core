import fs from 'fs-extra';
import path from 'path';

/**
 * Pustaka Lokal Internal Linker (Porting Mandiri Zero-Cost)
 * Berfungsi menyuntikkan tautan internal Tokcer AI secara cerdas ke artikel blog Markdown.
 * Melindungi headers, code blocks, inline code, dan link yang sudah ada agar tidak rusak.
 */

export function injectInternalLinks(markdownText, keywordMap) {
  let text = markdownText;

  // Tempat penyimpanan placeholders
  const codeBlocks = [];
  const inlineCodes = [];
  const existingLinks = [];
  const images = [];

  // 1. Masking Blocks Code (```...```)
  text = text.replace(/```[\s\S]*?```/g, (match) => {
    codeBlocks.push(match);
    return `__CODE_BLOCK_${codeBlocks.length - 1}__`;
  });

  // 2. Masking Inline Code (`...`)
  text = text.replace(/`[^`\n]+`/g, (match) => {
    inlineCodes.push(match);
    return `__INLINE_CODE_${inlineCodes.length - 1}__`;
  });

  // 3. Masking Images (![alt](url))
  text = text.replace(/!\[.*?\]\(.*?\)/g, (match) => {
    images.push(match);
    return `__IMAGE_${images.length - 1}__`;
  });

  // 4. Masking Existing Links ([text](url))
  text = text.replace(/\[.*?\]\(.*?\)/g, (match) => {
    existingLinks.push(match);
    return `__EXISTING_LINK_${existingLinks.length - 1}__`;
  });

  // 5. Lakukan Penggantian Kata Kunci (Urutkan dari terpanjang untuk mencegah overlap)
  const sortedKeywords = Object.keys(keywordMap).sort((a, b) => b.length - a.length);

  for (const keyword of sortedKeywords) {
    const url = keywordMap[keyword];
    // Regex mencari kata kunci sebagai kata utuh (case-insensitive)
    // Menghindari pencocokan di tengah kata
    const regex = new RegExp(`\\b(${escapeRegExp(keyword)})\\b`, 'gi');
    
    // Lakukan penggantian hanya untuk kemunculan PERTAMA (mencegah link-stuffing yang dinilai buruk oleh Google/AI)
    let replaced = false;
    text = text.replace(regex, (match) => {
      if (!replaced) {
        replaced = true;
        return `[${match}](${url})`;
      }
      return match;
    });
  }

  // 6. Unmasking (Kembalikan kode/link ke format aslinya secara terbalik)
  text = text.replace(/__EXISTING_LINK_(\d+)__/g, (_, idx) => existingLinks[parseInt(idx)]);
  text = text.replace(/__IMAGE_(\d+)__/g, (_, idx) => images[parseInt(idx)]);
  text = text.replace(/__INLINE_CODE_(\d+)__/g, (_, idx) => inlineCodes[parseInt(idx)]);
  text = text.replace(/__CODE_BLOCK_(\d+)__/g, (_, idx) => codeBlocks[parseInt(idx)]);

  return text;
}

function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
