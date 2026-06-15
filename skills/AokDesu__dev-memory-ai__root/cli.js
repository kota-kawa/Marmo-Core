#!/usr/bin/env node
// Registers tsx TypeScript loader then imports cli.ts
import { register } from 'tsx/esm/api';
import { fileURLToPath, pathToFileURL } from 'url';
import { dirname, resolve } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const unregister = register();

try {
  await import(pathToFileURL(resolve(__dirname, 'cli.ts')).href);
} finally {
  unregister();
}
