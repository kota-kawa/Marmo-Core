#!/usr/bin/env node
/**
 * paper-to-course PPTX Generator — CLI Entry Point
 *
 * Generates a PPTX from a slides-config.json file or inline config.
 * Uses slides-builder.js for all slide rendering.
 *
 * Usage:
 *   node generate-pptx.js output.pptx --config slides-config.json
 *   node generate-pptx.js output.pptx --inline '{"title":"...","slides":[...]}'
 *   node generate-pptx.js output.pptx --slides slides-config.json
 */

const path = require("path");
const fs = require("fs");
const { build } = require("./slides-builder");

// ─── CLI Parsing ────────────────────────────────────────────────
const args = process.argv.slice(2);

if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
  console.log(`paper-to-course PPTX Generator

Usage:
  node generate-pptx.js output.pptx --config slides-config.json
  node generate-pptx.js output.pptx --inline '{"title":"...","slides":[...]}'
  node generate-pptx.js output.pptx --slides slides-config.json

Options:
  --config   Path to slides-config.json file
  --inline   Inline JSON config string
  --slides   Alias for --config
  --help     Show this message
`);
  process.exit(0);
}

let outputPath = null;
let configPath = null;
let inlineConfig = null;

for (let i = 0; i < args.length; i++) {
  if (!args[i].startsWith('--')) {
    outputPath = path.resolve(args[i]);
    continue;
  }
  const flag = args[i].replace(/^--/, '');
  if (flag === 'config' || flag === 'slides') {
    configPath = path.resolve(args[++i]);
  } else if (flag === 'inline') {
    try {
      inlineConfig = JSON.parse(args[++i]);
    } catch (e) {
      console.error(`❌ Failed to parse inline JSON: ${e.message}`);
      process.exit(1);
    }
  }
}

if (!outputPath) {
  console.error("❌ Output path required. Usage: node generate-pptx.js output.pptx --config slides-config.json");
  process.exit(1);
}

// ─── Load Config ────────────────────────────────────────────────
let config;
if (inlineConfig) {
  config = inlineConfig;
} else if (configPath) {
  if (!fs.existsSync(configPath)) {
    console.error(`❌ Config file not found: ${configPath}`);
    process.exit(1);
  }
  try {
    const raw = fs.readFileSync(configPath, "utf-8");
    config = JSON.parse(raw);
  } catch (e) {
    console.error(`❌ Failed to parse config: ${e.message}`);
    process.exit(1);
  }
} else {
  // Try to find slides-config.json next to this script or in current dir
  const autoPath = path.resolve("slides-config.json");
  if (fs.existsSync(autoPath)) {
    try {
      config = JSON.parse(fs.readFileSync(autoPath, "utf-8"));
    } catch (e) {
      console.error(`❌ Failed to parse auto-detected config: ${autoPath}`);
      process.exit(1);
    }
  } else {
    console.error("❌ No config provided and no slides-config.json found in current directory.");
    console.error("   Use: node generate-pptx.js output.pptx --config slides-config.json");
    process.exit(1);
  }
}

// ─── Build PPTX ─────────────────────────────────────────────────
build(config, outputPath)
  .then(({ fileName, slideCount }) => {
    console.log(`✅ PPTX saved: ${fileName} (${slideCount} slides)`);
  })
  .catch(err => {
    console.error(`❌ Error: ${err.message}`);
    process.exit(1);
  });
