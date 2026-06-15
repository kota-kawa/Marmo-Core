#!/usr/bin/env node
/**
 * paper-to-course HTML → Markdown Converter
 *
 * Converts the generated HTML course into a clean Markdown document.
 * Preserves: headings, lists, tables, code blocks, callouts, formula blocks.
 * Strips: interactive elements, animations, nav, scripts.
 *
 * Usage:
 *   node html-to-md.js ./my-course/index.html
 *   node html-to-md.js ./my-course/index.html -o ./my-course/README.md
 */

const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom") || (() => { throw new Error("jsdom required: npm install jsdom"); })();

const STYLES_TO_REMOVE = [
  'animate-in', 'visible', 'nav', 'progress-bar', 'nav-dot', 'chat-messages',
  'typing-indicator', 'flow-animation', 'flow-packet', 'flow-controls',
  'quiz-option', 'quiz-feedback', 'quiz-check-btn', 'quiz-reset-btn',
  'arch-diagram', 'arch-description', 'ablation-container', 'ablation-chart',
  'timeline-container', 'comparison-table-container', 'comparison-tooltip',
  'dnd-container', 'dnd-chip', 'dnd-zone', 'term-tooltip',
  'formula-block', 'formula-original', 'formula-explanation',
  'formula-math', 'formula-english', 'formula-symbol',
  'formula-line', 'formula-label',
  'group-chat', 'chat-window',
  'module', 'module-header', 'module-content', 'module-number', 'module-title', 'module-subtitle',
  'screen', 'screen-heading',
  'stagger-children', 'pattern-cards', 'pattern-card',
  'step-cards', 'step-card', 'step-num', 'step-body',
  'icon-rows', 'icon-row', 'icon-circle',
  'callout', 'callout-accent', 'callout-info', 'callout-warning',
  'callout-icon', 'callout-title', 'callout-content',
  'arch-zone', 'arch-zone-label', 'arch-component',
  'flow-steps', 'flow-step', 'flow-step-num', 'flow-arrow',
  'badge-list', 'badge-item', 'badge-code', 'badge-desc',
  'file-tree', 'ft-folder', 'ft-file', 'ft-name', 'ft-desc', 'ft-children',
  'layer-demo', 'layer-tabs', 'layer-tab', 'layer-viewport', 'layer-description',
  'bug-challenge', 'bug-code', 'bug-line', 'line-num', 'bug-feedback',
  'scenario-block', 'scenario-context', 'scenario-label',
  'translation-block', 'translation-code', 'translation-english',
  'translation-label', 'translation-lines', 'tl',
];

// ─── Helpers ─────────────────────────────────────────────────────

function stripHtml(html) {
  return html
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<hr\s*\/?>/gi, '\n\n---\n\n')
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<[^>]+data-[^>]*>/g, '')
    .replace(/<[^>]+onclick[^>]*>/g, '')
    .replace(/class="[^"]*"/g, '')
    .replace(/\s+class\s*=\s*"[^"]*"/g, '')
    .replace(/data-[\w-]+="[^"]*"/g, '')
    .replace(/id="[^"]*"/g, '')
    .replace(/role="[^"]*"/g, '')
    .replace(/aria-[\w-]+="[^"]*"/g, '')
    .replace(/hidden/g, '')
    .replace(/style="[^"]*"/g, '')
    .trim();
}

function htmlToMd(html) {
  let md = html
    // Remove DOM comments
    .replace(/<!--[\s\S]*?-->/g, '')
    // Headings
    .replace(/<h1[^>]*>([\s\S]*?)<\/h1>/gi, (_, t) => '\n# ' + strip(t) + '\n')
    .replace(/<h2[^>]*>([\s\S]*?)<\/h2>/gi, (_, t) => '\n## ' + strip(t) + '\n')
    .replace(/<h3[^>]*>([\s\S]*?)<\/h3>/gi, (_, t) => '\n### ' + strip(t) + '\n')
    .replace(/<h4[^>]*>([\s\S]*?)<\/h4>/gi, (_, t) => '\n#### ' + strip(t) + '\n')
    // Paragraphs
    .replace(/<p[^>]*>([\s\S]*?)<\/p>/gi, (_, t) => {
      const s = strip(t).trim();
      if (!s || s === '&nbsp;') return '';
      // If it starts with >, it's already a blockquote
      if (s.startsWith('>')) return '\n' + s + '\n';
      return '\n' + s + '\n';
    })
    // Divs (treat as paragraphs)
    .replace(/<div[^>]*>([\s\S]*?)<\/div>/gi, (_, t) => {
      const s = t.trim();
      if (!s) return '';
      // Don't recursively process full divs
      return '\n' + s + '\n';
    })
    // Spans — strip but keep content
    .replace(/<span[^>]*>([\s\S]*?)<\/span>/gi, (_, t) => t)
    // Bold & italic
    .replace(/<strong[^>]*>([\s\S]*?)<\/strong>/gi, '**$1**')
    .replace(/<b[^>]*>([\s\S]*?)<\/b>/gi, '**$1**')
    .replace(/<em[^>]*>([\s\S]*?)<\/em>/gi, '_$1_')
    .replace(/<i[^>]*>([\s\S]*?)<\/i>/gi, '_$1_')
    // Code
    .replace(/<code[^>]*>([\s\S]*?)<\/code>/gi, '`$1`')
    .replace(/<pre[^>]*><code[^>]*>([\s\S]*?)<\/code><\/pre>/gi, '```\n$1\n```')
    // Inline code
    .replace(/`([^`]+)`/g, '`$1`')
    // Lists
    .replace(/<ul[^>]*>([\s\S]*?)<\/ul>/gi, (_, t) => t.replace(/<li[^>]*>([\s\S]*?)<\/li>/gi, (_, it) => '- ' + strip(it).trim() + '\n'))
    .replace(/<ol[^>]*>([\s\S]*?)<\/ol>/gi, (_, t) => {
      let i = 0;
      return t.replace(/<li[^>]*>([\s\S]*?)<\/li>/gi, (_, it) => (++i) + '. ' + strip(it).trim() + '\n');
    })
    // Tables
    .replace(/<table[^>]*>([\s\S]*?)<\/table>/gi, (_, t) => {
      let md = '';
      const rows = [];
      const headerReplaced = t.replace(/<thead[^>]*>([\s\S]*?)<\/thead>/gi, '');
      const tbodyMatch = headerReplaced.match(/<tbody[^>]*>([\s\S]*?)<\/tbody>/gi) || [];
      const theadMatch = t.match(/<thead[^>]*>([\s\S]*?)<\/thead>/gi) || [];
      const tbodyReplaced = t.replace(/<tbody[^>]*>([\s\S]*?)<\/tbody>/gi, '');

      function processRows(html) {
        const r = [];
        html.replace(/<tr[^>]*>([\s\S]*?)<\/tr>/gi, (_, tr) => {
          const cells = [];
          tr.replace(/<(th|td)[^>]*>([\s\S]*?)<\/(th|td)>/gi, (_, tag, content) => {
            cells.push(strip(content).trim());
          });
          if (cells.length) r.push(cells);
        });
        return r;
      }

      const theadRows = processRows(theadMatch.join(''));
      const tbodyRows = processRows(tbodyMatch.join(''));
      const allRows = [...theadRows, ...tbodyRows];

      if (allRows.length === 0) return '';

      const colCount = allRows[0]?.length || 0;
      if (colCount === 0) return '';

      md += '\n';
      allRows.forEach((row, ri) => {
        const cells = row.map(c => {
          const cellMd = c.replace(/<[^>]+>/g, '').trim();
          return ri === 0 ? `**${cellMd}**` : cellMd;
        });
        md += '| ' + cells.join(' | ') + ' |\n';
        if (ri === 0) {
          md += '| ' + cells.map(() => '---').join(' | ') + ' |\n';
        }
      });
      md += '\n';
      return md;
    })
    // Blockquotes (for callout boxes that degrade gracefully)
    .replace(/<blockquote[^>]*>([\s\S]*?)<\/blockquote>/gi, '\n> $1\n')
    // Links
    .replace(/<a[^>]*href="([^"]*)"[^>]*>([\s\S]*?)<\/a>/gi, '[$2]($1)')
    // Remove remaining tags
    .replace(/<[^>]+>/g, '')
    // Decode HTML entities
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&mdash;/g, '—')
    .replace(/&ndash;/g, '–')
    .replace(/&hellip;/g, '...')
    // Clean up multiple blank lines
    .replace(/\n{4,}/g, '\n\n\n')
    .trim();
  return md;
}

function strip(html) {
  return html
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&mdash;/g, '—')
    .replace(/&ndash;/g, '–')
    .replace(/&hellip;/g, '...')
    .trim();
}

function extractModules(html) {
  const { window } = new JSDOM(html);
  const doc = window.document;
  const modules = doc.querySelectorAll('.module');

  const results = [];
  modules.forEach((mod, i) => {
    const numEl = mod.querySelector('.module-number');
    const titleEl = mod.querySelector('.module-title');
    const subtitleEl = mod.querySelector('.module-subtitle');

    const num = numEl ? numEl.textContent.trim() : String(i + 1).padStart(2, '0');
    const title = titleEl ? strip(titleEl.textContent) : `Module ${num}`;
    const subtitle = subtitleEl ? strip(subtitleEl.textContent) : '';

    // Get raw HTML for each screen within module
    const screens = mod.querySelectorAll('.screen');
    const screenContents = [];
    screens.forEach(screen => {
      const headingEl = screen.querySelector('.screen-heading');
      const heading = headingEl ? strip(headingEl.textContent) : '';
      const bodyHtml = screen.innerHTML;
      screenContents.push({ heading, bodyHtml });
    });

    // Fallback: if no screens, use the whole module
    if (screenContents.length === 0) {
      screenContents.push({ heading: '', bodyHtml: mod.innerHTML });
    }

    results.push({ num, title, subtitle, screens: screenContents });
  });

  return results;
}

function modulesToMd(modules, paperTitle, paperSubtitle) {
  let md = '';

  // Front matter
  md += `# ${paperTitle}\n\n`;
  if (paperSubtitle) md += `_${paperSubtitle}_\n\n`;
  md += `---\n\n`;
  md += `> 📚 This is an auto-generated Markdown version of the interactive HTML course.\n`;
  md += `> Generated by **paper-to-course** skill.\n\n`;
  md += `---\n\n`;

  modules.forEach(mod => {
    md += `\n${'#'.repeat(2)} Module ${mod.num}: ${mod.title}\n\n`;
    if (mod.subtitle) md += `_${mod.subtitle}_\n\n`;

    mod.screens.forEach(screen => {
      if (screen.heading) {
        md += `\n### ${screen.heading}\n\n`;
      }

      const screenMd = htmlToMd(screen.bodyHtml);
      if (screenMd) {
        md += screenMd + '\n';
      }
    });
  });

  return md;
}

// ─── Main ───────────────────────────────────────────────────────
const args = process.argv.slice(2);

if (args.length === 0) {
  console.log('Usage: node html-to-md.js <index.html> [-o <output.md>]');
  console.log('  If no output specified, writes to stdout');
  process.exit(1);
}

const inputPath = path.resolve(args[0]);
const outputArg = args.indexOf('-o');
const outputPath = outputArg >= 0 && args[outputArg + 1]
  ? path.resolve(args[outputArg + 1])
  : null;

if (!fs.existsSync(inputPath)) {
  console.error(`❌ File not found: ${inputPath}`);
  process.exit(1);
}

const html = fs.readFileSync(inputPath, 'utf-8');

// Extract title
const titleMatch = html.match(/<title>([\s\S]*?)<\/title>/i);
const paperTitle = titleMatch ? strip(titleMatch[1]) : path.basename(inputPath, '.html');

// Extract subtitle from module subtitle
const subtitleMatch = html.match(/class="module-subtitle"[^>]*>([\s\S]*?)<\/p>/i);
const paperSubtitle = subtitleMatch ? strip(subtitleMatch[1]) : '';

const modules = extractModules(html);
const md = modulesToMd(modules, paperTitle, paperSubtitle);

if (outputPath) {
  fs.writeFileSync(outputPath, md, 'utf-8');
  console.log(`✅ Markdown saved: ${outputPath}`);
} else {
  console.log(md);
}
