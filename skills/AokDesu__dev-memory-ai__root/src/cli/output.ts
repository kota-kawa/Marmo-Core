import chalk from 'chalk';
import ora, { type Ora } from 'ora';

export const c = {
  success: (s: string) => chalk.green(s),
  error: (s: string) => chalk.red(s),
  warn: (s: string) => chalk.yellow(s),
  info: (s: string) => chalk.cyan(s),
  dim: (s: string) => chalk.dim(s),
  bold: (s: string) => chalk.bold(s),
  accent: (s: string) => chalk.magenta(s),
};

export function spinner(text: string): Ora {
  return ora({ text, color: 'cyan' }).start();
}

export function printSources(
  sources: { file: string; lines: [number, number]; content: string; score?: number }[]
) {
  if (sources.length === 0) return;
  console.log('\n' + c.dim('─'.repeat(60)));
  console.log(c.bold('Sources:'));
  for (const s of sources) {
    const pct = s.score != null ? c.dim(` (${(s.score * 100).toFixed(0)}%)`) : '';
    console.log(`  ${c.accent(s.file)}${c.dim(':' + s.lines[0] + '-' + s.lines[1])}${pct}`);
  }
}

export function printError(msg: string) {
  console.error(c.error('✖ ') + msg);
}

export function printSuccess(msg: string) {
  console.log(c.success('✓ ') + msg);
}
