#!/usr/bin/env node
/**
 * paper-to-course — Generic PPTX Slides Builder
 *
 * Takes a slides config (JSON) and produces a clean PPTX presentation.
 * Supports all slide types needed for academic paper presentations.
 *
 * Usage:
 *   const builder = require('./slides-builder');
 *   builder.build(config, outputPath);
 */

const pptxgen = require("pptxgenjs");

// ─── Color Palette ──────────────────────────────────────────────
const C = {
  white:     "FFFFFF",
  offWhite:  "FAFAFA",
  lightGray: "F0F0F0",
  midGray:   "D1D5DB",
  darkGray:  "6B7280",
  charcoal:  "36454F",
  black:     "1F2937",
  coral:     "D94F30",
  coralDark: "B33E24",
  blue:      "3B82F6",
  green:     "10B981",
  purple:    "7C3AED",
  amber:     "D4A843",
};

// ─── Color Helpers ──────────────────────────────────────────────
function colorForName(name) {
  const map = {
    coral:   [C.coral,   "FDEEE9"],
    blue:    [C.blue,    "DBEAFE"],
    green:   [C.green,   "D1FAE5"],
    purple:  [C.purple,  "EDE9FE"],
    amber:   [C.amber,   "FEF3C7"],
    red:     [C.coralDark,"FEE2E2"],
  };
  return map[name] || [C.coral, "FDEEE9"];
}

// ─── Low-level Slide Helpers ────────────────────────────────────
function addSlideNumber(slide, num, total) {
  slide.addText(`${num}/${total}`, {
    x: 9.3, y: 5.3, w: 0.4, h: 0.25,
    fontSize: 9, color: C.darkGray, align: "right", margin: 0
  });
}

function baseSlide(pres, title, slideNum, total) {
  const slide = pres.addSlide();
  slide.background = { color: C.white };

  // Header bar
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.7, fill: { color: C.charcoal }
  });
  slide.addText(title || '', {
    x: 0.5, y: 0.12, w: 8.5, h: 0.46,
    fontSize: 18, fontFace: "Arial Black", bold: true,
    color: C.white, align: "left", valign: "middle", margin: 0
  });
  slide.addText(`${slideNum}`, {
    x: 9.3, y: 0.15, w: 0.4, h: 0.35,
    fontSize: 12, fontFace: "Calibri", bold: true,
    color: C.coral, align: "right", valign: "middle", margin: 0
  });
  // Bottom divider
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 5.55, w: 10, h: 0.075, fill: { color: C.midGray }
  });
  return slide;
}

// ─── Slide Type Builders ─────────────────────────────────────────

function buildTitleSlide(pres, slideNum, total, { title, subtitle, note }) {
  const slide = pres.addSlide();
  slide.background = { color: C.white };

  // Top accent bar
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.08, fill: { color: C.coral }
  });
  slide.addText(title, {
    x: 0.6, y: 1.6, w: 8.8, h: 1.6,
    fontSize: 36, fontFace: "Arial Black", bold: true,
    color: C.charcoal, align: "left", valign: "middle", margin: 0
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.6, y: 3.3, w: 8.8, h: 1.0,
      fontSize: 16, fontFace: "Calibri",
      color: C.darkGray, align: "left", valign: "top", margin: 0
    });
  }
  if (note) {
    slide.addText(note, {
      x: 0.6, y: 4.5, w: 8.8, h: 0.5,
      fontSize: 13, fontFace: "Calibri", italic: true,
      color: C.darkGray, align: "left", margin: 0
    });
  }
  // Bottom bar
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 5.55, w: 10, h: 0.075, fill: { color: C.coral }
  });
  addSlideNumber(slide, slideNum, total);
  return slide;
}

function buildOutlineSlide(pres, slideNum, total, { title, items }) {
  const slide = baseSlide(pres, title || '汇报提纲', slideNum, total);
  const bullets = (items || []).map((item, i) => ({
    text: item,
    options: {
      bullet: true,
      breakLine: i < items.length - 1,
      color: C.charcoal,
      fontSize: 17,
      fontFace: "Calibri",
    }
  }));
  slide.addText(bullets, {
    x: 0.5, y: 0.95, w: 9, h: 4.3,
    valign: "top", paraSpaceAfter: 14
  });
  return slide;
}

function buildContentSlide(pres, slideNum, total, { title, layout, items, cards }) {
  const slide = baseSlide(pres, title, slideNum, total);
  const startY = 0.95;

  if (layout === 'bullets' || layout === 'bullets-large') {
    const fontSize = layout === 'bullets-large' ? 18 : 15;
    const bullets = (items || []).map((item, i) => ({
      text: item,
      options: {
        bullet: true,
        breakLine: i < items.length - 1,
        color: C.charcoal,
        fontSize,
        fontFace: "Calibri",
      }
    }));
    slide.addText(bullets, {
      x: 0.5, y: startY, w: 9, h: 4.3,
      valign: "top", paraSpaceAfter: 12
    });
  } else if (layout === 'cards-2' || layout === 'cards-3' || layout === 'cards-4') {
    const cols = parseInt(layout.split('-')[1]) || 3;
    const cardsArr = cards || items || [];
    const cardW = (9 - (cols + 1) * 0.25) / cols;
    const cardH = 4.0;

    cardsArr.forEach((card, i) => {
      const col = i % cols;
      const x = 0.5 + col * (cardW + 0.25);
      const [colorVal, bgColor] = colorForName(card.color || 'coral');

      // Card bg
      slide.addShape(pres.shapes.RECTANGLE, {
        x, y: startY, w: cardW, h: cardH,
        fill: { color: C.lightGray },
        shadow: { type: "outer", color: "000000", blur: 4, offset: 1, angle: 135, opacity: 0.06 }
      });
      // Accent top
      slide.addShape(pres.shapes.RECTANGLE, {
        x, y: startY, w: cardW, h: 0.06,
        fill: { color: colorVal }
      });
      // Title
      slide.addText(card.title || '', {
        x: x + 0.15, y: startY + 0.2, w: cardW - 0.3, h: 0.55,
        fontSize: 13, fontFace: "Arial", bold: true,
        color: C.charcoal, align: "left", valign: "top", margin: 0
      });
      // Body
      const bodyContent = Array.isArray(card.text) ? card.text : [card.text || ''];
      const bulletItems = bodyContent.map((t, j) => ({
        text: t,
        options: {
          bullet: bodyContent.length > 1,
          breakLine: j < bodyContent.length - 1,
          color: C.charcoal,
          fontSize: 11,
          fontFace: "Calibri"
        }
      }));
      slide.addText(bulletItems, {
        x: x + 0.15, y: startY + 0.8, w: cardW - 0.3, h: cardH - 1.0,
        valign: "top", paraSpaceAfter: 6
      });
    });
  } else if (layout === 'grid-2x2' && cards) {
    const cardW = 4.35;
    const cardH = 1.85;
    const gapX = 0.3;
    const gapY = 0.25;

    cards.forEach((card, i) => {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const x = 0.5 + col * (cardW + gapX);
      const y = startY + row * (cardH + gapY);
      const [colorVal] = colorForName(card.color || 'coral');

      slide.addShape(pres.shapes.RECTANGLE, {
        x, y, w: cardW, h: cardH,
        fill: { color: C.lightGray },
        shadow: { type: "outer", color: "000000", blur: 3, offset: 1, angle: 135, opacity: 0.06 }
      });
      slide.addShape(pres.shapes.RECTANGLE, {
        x, y, w: cardW, h: 0.06,
        fill: { color: colorVal }
      });
      slide.addText(card.title || '', {
        x: x + 0.2, y: y + 0.18, w: cardW - 0.4, h: 0.45,
        fontSize: 13, fontFace: "Arial", bold: true,
        color: C.charcoal, align: "left", valign: "top", margin: 0
      });
      slide.addText(card.text || '', {
        x: x + 0.2, y: y + 0.65, w: cardW - 0.4, h: cardH - 0.85,
        fontSize: 12, fontFace: "Calibri",
        color: C.charcoal, align: "left", valign: "top", margin: 0
      });
    });
  } else if (layout === 'steps' && items) {
    const steps = items;
    const cols = Math.min(steps.length, 4);
    const cardW = (9 - (cols + 1) * 0.25) / cols;
    const cardH = 3.5;

    steps.forEach((step, i) => {
      const x = 0.5 + i * (cardW + 0.25);
      const [colorVal] = colorForName(step.color || 'coral');

      slide.addShape(pres.shapes.RECTANGLE, {
        x, y: startY, w: cardW, h: cardH,
        fill: { color: C.lightGray },
        shadow: { type: "outer", color: "000000", blur: 3, offset: 1, angle: 135, opacity: 0.05 }
      });
      // Number badge
      slide.addShape(pres.shapes.OVAL, {
        x: x + cardW / 2 - 0.25, y: startY + 0.15, w: 0.5, h: 0.5,
        fill: { color: colorVal }
      });
      slide.addText(String(step.num || (i + 1)), {
        x: x + cardW / 2 - 0.25, y: startY + 0.15, w: 0.5, h: 0.5,
        fontSize: 14, fontFace: "Arial", bold: true,
        color: C.white, align: "center", valign: "middle", margin: 0
      });
      slide.addText(step.title || '', {
        x: x + 0.1, y: startY + 0.75, w: cardW - 0.2, h: 0.5,
        fontSize: 12, fontFace: "Arial", bold: true,
        color: C.charcoal, align: "center", valign: "middle", margin: 0
      });
      slide.addText(step.desc || '', {
        x: x + 0.1, y: startY + 1.3, w: cardW - 0.2, h: cardH - 1.5,
        fontSize: 10, fontFace: "Calibri",
        color: C.darkGray, align: "center", valign: "top", margin: 0
      });
    });
  } else {
    // Default: bullet list
    const bullets = (items || []).map((item, i) => ({
      text: item,
      options: {
        bullet: true,
        breakLine: i < items.length - 1,
        color: C.charcoal,
        fontSize: 15,
        fontFace: "Calibri",
      }
    }));
    slide.addText(bullets, {
      x: 0.5, y: startY, w: 9, h: 4.3,
      valign: "top", paraSpaceAfter: 12
    });
  }

  return slide;
}

function buildFlowSlide(pres, slideNum, total, { title, steps }) {
  const slide = baseSlide(pres, title, slideNum, total);
  const startY = 1.1;
  const cardW = 2.0;
  const gap = 0.33;

  (steps || []).forEach((step, i) => {
    const x = 0.5 + i * (cardW + gap);
    const [colorVal] = colorForName(step.color || 'coral');

    slide.addShape(pres.shapes.RECTANGLE, {
      x, y: startY, w: cardW, h: 3.6,
      fill: { color: C.lightGray },
      shadow: { type: "outer", color: "000000", blur: 3, offset: 1, angle: 135, opacity: 0.05 }
    });
    slide.addShape(pres.shapes.OVAL, {
      x: x + cardW / 2 - 0.25, y: startY + 0.15, w: 0.5, h: 0.5,
      fill: { color: colorVal }
    });
    slide.addText(String(step.num || (i + 1)), {
      x: x + cardW / 2 - 0.25, y: startY + 0.15, w: 0.5, h: 0.5,
      fontSize: 14, fontFace: "Arial", bold: true,
      color: C.white, align: "center", valign: "middle", margin: 0
    });
    slide.addText(step.title || '', {
      x: x + 0.1, y: startY + 0.75, w: cardW - 0.2, h: 0.5,
      fontSize: 12, fontFace: "Arial", bold: true,
      color: C.charcoal, align: "center", valign: "middle", margin: 0
    });
    slide.addText(step.subtitle || '', {
      x: x + 0.1, y: startY + 1.25, w: cardW - 0.2, h: 0.35,
      fontSize: 9, fontFace: "Calibri",
      color: C.darkGray, align: "center", valign: "middle", margin: 0
    });
    slide.addText(step.desc || '', {
      x: x + 0.1, y: startY + 1.65, w: cardW - 0.2, h: 1.9,
      fontSize: 10, fontFace: "Calibri",
      color: C.darkGray, align: "center", valign: "top", margin: 0
    });
    if (i < (steps || []).length - 1) {
      slide.addText("→", {
        x: x + cardW + 0.02, y: startY + 1.5, w: gap - 0.04, h: 0.4,
        fontSize: 18, color: C.midGray, align: "center", valign: "middle", margin: 0
      });
    }
  });
  return slide;
}

function buildTableSlide(pres, slideNum, total, { title, headers, rows, highlightRows }) {
  const slide = baseSlide(pres, title, slideNum, total);

  const tableData = [
    headers.map(h => ({
      text: h,
      options: {
        fill: { color: C.charcoal },
        color: C.white,
        bold: true,
        fontSize: 11,
        fontFace: "Calibri",
        align: "center",
        valign: "middle"
      }
    })),
    ...rows.map((row, ri) =>
      row.map((cell, ci) => ({
        text: String(cell),
        options: {
          fill: { color: (highlightRows || []).includes(ri) ? "FEF2F2" : C.white },
          color: C.charcoal,
          fontSize: 11,
          fontFace: "Calibri",
          align: ci === 0 ? "left" : "center",
          valign: "middle",
          bold: (highlightRows || []).includes(ri) && ci === 0,
        }
      }))
    )
  ];

  const colCount = headers.length;
  const colWs = {
    2: [3, 6],
    3: [3, 3, 3],
    4: [2.5, 1.2, 1.2, 4.1],
    5: [2.2, 1.5, 1.1, 1.1, 3.1],
    6: [2.2, 1.5, 1.1, 1.1, 1.1, 2.0],
    7: [2.0, 1.2, 1.0, 1.0, 1.0, 1.0, 1.8],
  };

  slide.addTable(tableData, {
    x: 0.5, y: 0.95, w: 9,
    colW: colWs[colCount] || Array(colCount).fill(9 / colCount),
    border: { pt: 0.5, color: C.midGray },
    fontFace: "Calibri",
  });
  return slide;
}

function buildBarsSlide(pres, slideNum, total, { title, subtitle, items }) {
  const slide = baseSlide(pres, title, slideNum, total);

  const barStartX = 0.5;
  const barStartY = 0.95;
  const barMaxW = 6.5;
  const barH = 0.75;
  const gap = 0.2;
  const labelW = 1.5;
  const barBaseX = barStartX + labelW;

  (items || []).forEach((item, i) => {
    const y = barStartY + i * (barH + gap);
    const pct = Math.max(0, Math.min(100, item.value));
    const barW = (pct / 100) * (9 - barBaseX - 0.5);

    // Label
    slide.addText(item.label || '', {
      x: barStartX, y, w: labelW, h: barH,
      fontSize: 11, fontFace: "Calibri", bold: true,
      color: C.charcoal, align: "left", valign: "middle", margin: 0
    });
    // Bar
    slide.addShape(pres.shapes.RECTANGLE, {
      x: barBaseX, y: y + 0.08, w: barW, h: barH - 0.16,
      fill: { color: item.isBaseline ? C.coral : "94A3B8" }
    });
    // Value
    const valueText = item.valueText || `${item.value}%`;
    slide.addText(valueText, {
      x: barBaseX + barW + 0.08, y, w: 0.6, h: barH,
      fontSize: 12, fontFace: "Arial", bold: true,
      color: item.isBaseline ? C.coral : C.charcoal, align: "left", valign: "middle", margin: 0
    });
    // Drop annotation
    if (item.drop !== undefined) {
      slide.addText(`${item.drop > 0 ? '+' : ''}${item.drop}%`, {
        x: barBaseX + barW + 0.7, y, w: 0.6, h: barH,
        fontSize: 11, fontFace: "Calibri",
        color: item.drop < 0 ? C.coral : C.green, align: "left", valign: "middle", margin: 0
      });
    }
  });

  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.5, y: 4.7, w: 9, h: 0.7,
      fontSize: 12, fontFace: "Calibri", italic: true,
      color: C.darkGray, align: "left", valign: "top", margin: 0
    });
  }
  return slide;
}

function buildStatsSlide(pres, slideNum, total, { title, stats }) {
  const slide = baseSlide(pres, title, slideNum, total);
  const startY = 1.1;
  const cardH = 2.2;
  const gap = 0.4;
  const cols = (stats || []).length;
  const cardW = cols > 0 ? (9 - gap * (cols - 1)) / cols : 9;

  (stats || []).forEach((stat, i) => {
    const x = 0.5 + i * (cardW + gap);
    const [colorVal, bgColor] = colorForName(stat.color || 'coral');

    slide.addShape(pres.shapes.RECTANGLE, {
      x, y: startY, w: cardW, h: cardH,
      fill: { color: bgColor || C.lightGray }
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x, y: startY, w: cardW, h: 0.06,
      fill: { color: colorVal }
    });
    slide.addText(stat.value || '', {
      x, y: startY + 0.2, w: cardW, h: stat.big ? 1.2 : 1.0,
      fontSize: stat.big ? 44 : 36, fontFace: "Arial Black", bold: true,
      color: colorVal, align: "center", valign: "middle", margin: 0
    });
    slide.addText(stat.label || '', {
      x: x + 0.1, y: startY + 1.25, w: cardW - 0.2, h: 0.85,
      fontSize: 11, fontFace: "Calibri",
      color: C.charcoal, align: "center", valign: "top", margin: 0
    });
  });
  return slide;
}

function buildFormulaSlide(pres, slideNum, total, { title, formula, lines }) {
  const slide = baseSlide(pres, title, slideNum, total);
  const startY = 0.95;

  // Formula box
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: startY, w: 9, h: 1.1,
    fill: { color: "1E1E2E" }
  });
  slide.addText(formula || '', {
    x: 0.7, y: startY, w: 8.6, h: 1.1,
    fontSize: 16, fontFace: "JetBrains Mono",
    color: "CDD6F4", align: "left", valign: "middle", margin: 0
  });

  // Explanations
  if (lines && lines.length) {
    const itemH = Math.min(0.55, (4.3 - startY - 1.3) / lines.length);
    lines.forEach((line, i) => {
      const y = startY + 1.25 + i * itemH;

      // Symbol
      slide.addText(line.symbol || '', {
        x: 0.5, y, w: 1.8, h: itemH,
        fontSize: 11, fontFace: "JetBrains Mono",
        color: "CBA6F7", bold: true, align: "left", valign: "top", margin: 0
      });
      // English explanation
      slide.addText(line.english || '', {
        x: 2.3, y, w: 7.2, h: itemH,
        fontSize: 11, fontFace: "Calibri",
        color: C.darkGray, align: "left", valign: "top", margin: 0
      });
    });
  }
  return slide;
}

function buildQuoteSlide(pres, slideNum, total, { title, quote, attribution }) {
  const slide = baseSlide(pres, title || '核心启示', slideNum, total);
  const startY = 1.1;

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: startY, w: 9, h: 3.6,
    fill: { color: C.lightGray },
    shadow: { type: "outer", color: "000000", blur: 4, offset: 1, angle: 135, opacity: 0.06 }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: startY, w: 0.08, h: 3.6,
    fill: { color: C.coral }
  });
  slide.addText(`"${quote || ''}"`, {
    x: 0.8, y: startY + 0.3, w: 8.5, h: 2.6,
    fontSize: 20, fontFace: "Calibri", italic: true,
    color: C.charcoal, align: "left", valign: "middle", margin: 0
  });
  if (attribution) {
    slide.addText(`— ${attribution}`, {
      x: 0.8, y: startY + 3.0, w: 8.5, h: 0.4,
      fontSize: 13, fontFace: "Calibri", bold: true,
      color: C.darkGray, align: "right", margin: 0
    });
  }
  return slide;
}

function buildTimelineSlide(pres, slideNum, total, { title, items }) {
  const slide = baseSlide(pres, title || '发展脉络', slideNum, total);
  const startY = 0.95;
  const itemH = 0.78;

  (items || []).forEach((item, i) => {
    const y = startY + i * itemH;

    // Year badge
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 0.9, h: 0.5,
      fill: { color: i >= (items.length - 2) ? C.coral : C.charcoal }
    });
    slide.addText(item.year || '', {
      x: 0.5, y, w: 0.9, h: 0.5,
      fontSize: 9, fontFace: "Calibri", bold: true,
      color: C.white, align: "center", valign: "middle", margin: 0
    });
    // Arrow
    slide.addText("→", {
      x: 1.5, y, w: 0.3, h: 0.5,
      fontSize: 14, color: C.darkGray, align: "center", valign: "middle", margin: 0
    });
    // Title
    slide.addText(item.title || '', {
      x: 1.85, y, w: 2.3, h: 0.5,
      fontSize: 12, fontFace: "Arial", bold: true,
      color: i >= (items.length - 2) ? C.coral : C.charcoal,
      align: "left", valign: "middle", margin: 0
    });
    // Description
    slide.addText(item.desc || '', {
      x: 4.2, y, w: 5.3, h: 0.5,
      fontSize: 11, fontFace: "Calibri",
      color: C.darkGray, align: "left", valign: "middle", margin: 0
    });
    // Divider
    if (i < items.length - 1) {
      slide.addShape(pres.shapes.LINE, {
        x: 0.5, y: y + 0.6, w: 9, h: 0,
        line: { color: C.lightGray, width: 0.5 }
      });
    }
  });
  return slide;
}

function buildSummarySlide(pres, slideNum, total, { title, items }) {
  const slide = baseSlide(pres, title || '总结', slideNum, total);

  (items || []).forEach((item, i) => {
    const y = 0.95 + i * 1.05;
    const [colorVal] = colorForName(item.color || 'coral');

    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 9, h: 0.9,
      fill: { color: i % 2 === 0 ? C.lightGray : C.white }
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 0.06, h: 0.9,
      fill: { color: colorVal }
    });
    slide.addText(item.text || '', {
      x: 0.7, y, w: 8.6, h: 0.9,
      fontSize: 14, fontFace: "Calibri",
      color: C.charcoal, align: "left", valign: "middle", margin: 0
    });
  });
  return slide;
}

function buildLimitationsSlide(pres, slideNum, total, { title, limitations, futureWork }) {
  const slide = baseSlide(pres, title || '局限与展望', slideNum, total);
  const colW = 4.45;

  // Left: limitations
  slide.addText("当前局限", {
    x: 0.5, y: 0.9, w: colW, h: 0.4,
    fontSize: 13, fontFace: "Arial", bold: true,
    color: C.charcoal, align: "left", margin: 0
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.3, w: colW, h: 3.5,
    fill: { color: "FEF2F2" }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.3, w: 0.06, h: 3.5,
    fill: { color: C.coral }
  });
  const limitBullets = (limitations || []).map((t, i) => ({
    text: t,
    options: {
      bullet: true,
      breakLine: i < limitations.length - 1,
      color: C.charcoal,
      fontSize: 13,
      fontFace: "Calibri"
    }
  }));
  slide.addText(limitBullets, {
    x: 0.65, y: 1.4, w: colW - 0.3, h: 3.3,
    valign: "top", paraSpaceAfter: 10
  });

  // Right: future work
  slide.addText("未来方向", {
    x: 5.05, y: 0.9, w: colW, h: 0.4,
    fontSize: 13, fontFace: "Arial", bold: true,
    color: C.charcoal, align: "left", margin: 0
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.05, y: 1.3, w: colW, h: 3.5,
    fill: { color: "F0FDF4" }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.05, y: 1.3, w: 0.06, h: 3.5,
    fill: { color: C.green }
  });
  const futureBullets = (futureWork || []).map((t, i) => ({
    text: t,
    options: {
      bullet: true,
      breakLine: i < futureWork.length - 1,
      color: C.charcoal,
      fontSize: 13,
      fontFace: "Calibri"
    }
  }));
  slide.addText(futureBullets, {
    x: 5.2, y: 1.4, w: colW - 0.3, h: 3.3,
    valign: "top", paraSpaceAfter: 10
  });

  return slide;
}

// ─── Master Builder ──────────────────────────────────────────────
const BUILDERS = {
  title:       buildTitleSlide,
  outline:     buildOutlineSlide,
  content:     buildContentSlide,
  flow:        buildFlowSlide,
  table:       buildTableSlide,
  bars:        buildBarsSlide,
  stats:       buildStatsSlide,
  formula:     buildFormulaSlide,
  quote:       buildQuoteSlide,
  timeline:    buildTimelineSlide,
  summary:     buildSummarySlide,
  limitations: buildLimitationsSlide,
};

function build(config, outputPath) {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.title = config.title || "Paper Course";
  pres.author = "paper-to-course";

  const slides = config.slides || [];
  const total = slides.length;

  slides.forEach((slideConfig, i) => {
    const slideNum = i + 1;
    const type = slideConfig.type || 'content';
    const builder = BUILDERS[type];
    if (builder) {
      builder(pres, slideNum, total, slideConfig);
    } else {
      // Fallback: content slide with title and bullets
      buildContentSlide(pres, slideNum, total, {
        title: slideConfig.title || `Slide ${slideNum}`,
        items: slideConfig.items || [],
      });
    }
  });

  return pres.writeFile({ fileName: outputPath })
    .then(() => ({ fileName: outputPath, slideCount: slides.length }));
}

module.exports = { build };
