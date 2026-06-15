#!/usr/bin/env node

import { createHash } from "node:crypto";
import { mkdir, writeFile, readFile, access, stat } from "node:fs/promises";
import { constants as fsConstants } from "node:fs";
import { join } from "node:path";
import { spawn } from "node:child_process";

const BASE_URL = "https://www.isf.org.il";
const OUTPUT_DIR = join(process.cwd(), ".context", "isf-grants-docs");
const FILES_DIR = join(OUTPUT_DIR, "files");
const TEXT_DIR = join(OUTPUT_DIR, "text");

const LANGS = ["en-US", "he-IL"];

async function fetchJson(path) {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: {
      "accept": "application/json",
      "user-agent": "isf-agent-docs-harvester/1.0",
    },
  });

  if (!res.ok) {
    throw new Error(`Request failed (${res.status}) for ${url}`);
  }

  return res.json();
}

function uniqSorted(nums) {
  return Array.from(new Set(nums)).sort((a, b) => a - b);
}

function cleanFilename(name) {
  return name.replace(/[\\/]/g, "_");
}

async function fileExists(path) {
  try {
    await access(path, fsConstants.F_OK);
    return true;
  } catch {
    return false;
  }
}

async function sha256(path) {
  const buf = await readFile(path);
  return createHash("sha256").update(buf).digest("hex");
}

async function runPdftotext(pdfPath, txtPath) {
  return new Promise((resolve) => {
    const child = spawn("pdftotext", ["-layout", pdfPath, txtPath], {
      stdio: "ignore",
    });
    child.on("error", () => resolve(false));
    child.on("close", (code) => resolve(code === 0));
  });
}

async function main() {
  await mkdir(OUTPUT_DIR, { recursive: true });
  await mkdir(FILES_DIR, { recursive: true });
  await mkdir(TEXT_DIR, { recursive: true });

  const grantTypesByLang = {};
  for (const lang of LANGS) {
    grantTypesByLang[lang] = await fetchJson(
      `/api/grant/getGrantTypeData?grantType=0&lang=${encodeURIComponent(lang)}`
    );
  }

  const grantTypeIds = uniqSorted(
    LANGS.flatMap((lang) => grantTypesByLang[lang].map((g) => g.grantTypeId))
  );

  const filesByGrantType = {};
  const grantPagesByLang = {
    "en-US": {},
    "he-IL": {},
  };

  for (const grantTypeId of grantTypeIds) {
    filesByGrantType[grantTypeId] = {};
    for (const lang of LANGS) {
      const [files, pages] = await Promise.all([
        fetchJson(
          `/api/grant/GetFilesToGrants?grantTypeId=${grantTypeId}&lang=${encodeURIComponent(lang)}`
        ),
        fetchJson(
          `/api/grant/GetAllGrantsPageContent?grantTypeId=${grantTypeId}&lang=${encodeURIComponent(lang)}`
        ),
      ]);

      filesByGrantType[grantTypeId][lang] = files;
      grantPagesByLang[lang][grantTypeId] = pages;
    }
  }

  const deadlinesByLang = {};
  for (const lang of LANGS) {
    deadlinesByLang[lang] = await fetchJson(
      `/api/innerPages/GetGrantsDeadlines?lang=${encodeURIComponent(lang)}`
    );
  }

  const filesMap = new Map();

  for (const grantTypeId of grantTypeIds) {
    for (const lang of LANGS) {
      for (const entry of filesByGrantType[grantTypeId][lang] || []) {
        if (!entry?.name) continue;

        const key = entry.name;
        const prev = filesMap.get(key) ?? {
          name: entry.name,
          fileId: entry.id ?? null,
          byLang: {},
          grantTypeIds: [],
          url: `${BASE_URL}/Files/${encodeURIComponent(entry.name)}`,
        };

        prev.byLang[lang] = {
          fileType: entry.fileType ?? "",
          description: entry.description ?? "",
          fileTypeId: entry.fileTypeId ?? null,
        };

        if (!prev.grantTypeIds.includes(grantTypeId)) {
          prev.grantTypeIds.push(grantTypeId);
          prev.grantTypeIds.sort((a, b) => a - b);
        }

        filesMap.set(key, prev);
      }
    }
  }

  const fileEntries = Array.from(filesMap.values()).sort((a, b) =>
    a.name.localeCompare(b.name)
  );

  let downloaded = 0;
  let reused = 0;

  for (const fileEntry of fileEntries) {
    const safeName = cleanFilename(fileEntry.name);
    const pdfPath = join(FILES_DIR, safeName);
    const txtPath = join(TEXT_DIR, `${safeName}.txt`);

    const exists = await fileExists(pdfPath);
    if (!exists) {
      const res = await fetch(fileEntry.url, {
        headers: { "user-agent": "isf-agent-docs-harvester/1.0" },
      });

      if (!res.ok) {
        fileEntry.downloadError = `HTTP ${res.status}`;
        continue;
      }

      const bytes = Buffer.from(await res.arrayBuffer());
      await writeFile(pdfPath, bytes);
      downloaded += 1;
    } else {
      reused += 1;
    }

    const fileStat = await stat(pdfPath);
    fileEntry.localPath = `files/${safeName}`;
    fileEntry.bytes = fileStat.size;
    fileEntry.sha256 = await sha256(pdfPath);

    const textOk = await runPdftotext(pdfPath, txtPath);
    if (textOk) {
      fileEntry.textPath = `text/${safeName}.txt`;
    }
  }

  const generatedAt = new Date().toISOString();
  const activeGrantCount = grantTypesByLang["en-US"].filter(
    (g) => g.isActive === "Yes" || g.grantTypeStatus === "Active"
  ).length;

  const manifest = {
    generatedAt,
    source: BASE_URL,
    languages: LANGS,
    grantTypeCount: grantTypeIds.length,
    activeGrantCount,
    fileCount: fileEntries.length,
    downloads: {
      downloaded,
      reused,
    },
    files: fileEntries,
  };

  await Promise.all([
    writeFile(
      join(OUTPUT_DIR, "manifest.json"),
      JSON.stringify(manifest, null, 2),
      "utf8"
    ),
    writeFile(
      join(OUTPUT_DIR, "grant-types.en-US.json"),
      JSON.stringify(grantTypesByLang["en-US"], null, 2),
      "utf8"
    ),
    writeFile(
      join(OUTPUT_DIR, "grant-types.he-IL.json"),
      JSON.stringify(grantTypesByLang["he-IL"], null, 2),
      "utf8"
    ),
    writeFile(
      join(OUTPUT_DIR, "grant-pages.en-US.json"),
      JSON.stringify(grantPagesByLang["en-US"], null, 2),
      "utf8"
    ),
    writeFile(
      join(OUTPUT_DIR, "grant-pages.he-IL.json"),
      JSON.stringify(grantPagesByLang["he-IL"], null, 2),
      "utf8"
    ),
    writeFile(
      join(OUTPUT_DIR, "deadlines.en-US.json"),
      JSON.stringify(deadlinesByLang["en-US"], null, 2),
      "utf8"
    ),
    writeFile(
      join(OUTPUT_DIR, "deadlines.he-IL.json"),
      JSON.stringify(deadlinesByLang["he-IL"], null, 2),
      "utf8"
    ),
  ]);

  const readme = [
    "# ISF Grants Documentation Snapshot",
    "",
    `Generated: ${generatedAt}`,
    `Source: ${BASE_URL}`,
    "",
    "## Coverage",
    `- Grant programs indexed: ${grantTypeIds.length}`,
    `- Active grant programs: ${activeGrantCount}`,
    `- Unique grant-linked documents: ${fileEntries.length}`,
    `- Files downloaded this run: ${downloaded}`,
    `- Files reused from cache: ${reused}`,
    "",
    "## Files",
    "- `manifest.json`: master index of grant docs and local file locations",
    "- `grant-types.en-US.json` and `grant-types.he-IL.json`: grant program metadata",
    "- `grant-pages.*.json`: per-program description text pulled from ISF",
    "- `deadlines.*.json`: deadline tables from ISF",
    "- `files/`: downloaded PDFs from `/Files/<name>`",
    "- `text/`: extracted text from PDFs via `pdftotext`",
    "",
    "## Refresh",
    "```bash",
    "node scripts/fetch-isf-grants-docs.mjs",
    "```",
    "",
  ].join("\n");

  await writeFile(join(OUTPUT_DIR, "README.md"), readme, "utf8");

  console.log(`Done. Indexed ${grantTypeIds.length} programs and ${fileEntries.length} documents.`);
  console.log(`Output: ${OUTPUT_DIR}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
