import { readFileSync, writeFileSync, existsSync } from 'fs';
import path from 'path';

export interface ProjectConfig {
  projectId: string;
  name: string;
  path: string;
  gitRemote?: string | null;
}

const CONFIG_FILE = '.memory-dev.json';

export function findConfigFile(startDir = process.cwd()): string | null {
  let dir = startDir;
  while (true) {
    const candidate = path.join(dir, CONFIG_FILE);
    if (existsSync(candidate)) return candidate;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

export function readConfig(configPath?: string): ProjectConfig | null {
  const p = configPath ?? findConfigFile();
  if (!p) return null;
  try {
    return JSON.parse(readFileSync(p, 'utf-8')) as ProjectConfig;
  } catch {
    return null;
  }
}

export function writeConfig(dir: string, config: ProjectConfig): string {
  const p = path.join(dir, CONFIG_FILE);
  writeFileSync(p, JSON.stringify(config, null, 2) + '\n', 'utf-8');
  return p;
}
