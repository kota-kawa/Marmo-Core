import fs from 'fs/promises';
import path from 'path';
import { existsSync, statSync } from 'fs';

/**
 * Secure file system access layer
 * Prevents directory traversal and validates paths
 */

export class FileSystemError extends Error {
  constructor(message: string, public code: string) {
    super(message);
    this.name = 'FileSystemError';
  }
}

/**
 * Validate that a path is safe and within allowed boundaries
 */
export function validatePath(targetPath: string): string {
  // Resolve to absolute path
  const absolutePath = path.resolve(targetPath);
  
  // Check if path exists
  if (!existsSync(absolutePath)) {
    throw new FileSystemError(`Path does not exist: ${targetPath}`, 'PATH_NOT_FOUND');
  }
  
  // Prevent access to system directories
  const forbiddenPaths = [
    '/etc',
    '/sys',
    '/proc',
    '/dev',
    '/root',
    'C:\\Windows',
    'C:\\Program Files',
  ];
  
  for (const forbidden of forbiddenPaths) {
    if (absolutePath.startsWith(forbidden)) {
      throw new FileSystemError(
        `Access to system directory is forbidden: ${forbidden}`,
        'FORBIDDEN_PATH'
      );
    }
  }
  
  return absolutePath;
}

/**
 * Check if path is a directory
 */
export function isDirectory(targetPath: string): boolean {
  try {
    const stats = statSync(targetPath);
    return stats.isDirectory();
  } catch {
    return false;
  }
}

/**
 * Check if path is a file
 */
export function isFile(targetPath: string): boolean {
  try {
    const stats = statSync(targetPath);
    return stats.isFile();
  } catch {
    return false;
  }
}

/**
 * List files in a directory with optional filtering
 */
export async function listFiles(
  dirPath: string,
  options?: {
    recursive?: boolean;
    includeHidden?: boolean;
    extensions?: string[];
    maxDepth?: number;
  }
): Promise<Array<{ path: string; type: 'file' | 'directory'; size?: number }>> {
  const validatedPath = validatePath(dirPath);
  
  if (!isDirectory(validatedPath)) {
    throw new FileSystemError('Path is not a directory', 'NOT_A_DIRECTORY');
  }
  
  const results: Array<{ path: string; type: 'file' | 'directory'; size?: number }> = [];
  
  async function scan(currentPath: string, depth: number = 0) {
    if (options?.maxDepth && depth > options.maxDepth) {
      return;
    }
    
    const entries = await fs.readdir(currentPath, { withFileTypes: true });
    
    for (const entry of entries) {
      // Skip hidden files unless explicitly included
      if (!options?.includeHidden && entry.name.startsWith('.')) {
        continue;
      }
      
      const fullPath = path.join(currentPath, entry.name);
      const relativePath = path.relative(validatedPath, fullPath);
      
      if (entry.isDirectory()) {
        results.push({
          path: relativePath,
          type: 'directory',
        });
        
        if (options?.recursive) {
          await scan(fullPath, depth + 1);
        }
      } else if (entry.isFile()) {
        // Filter by extension if specified
        if (options?.extensions) {
          const ext = path.extname(entry.name).slice(1);
          if (!options.extensions.includes(ext)) {
            continue;
          }
        }
        
        const stats = await fs.stat(fullPath);
        results.push({
          path: relativePath,
          type: 'file',
          size: stats.size,
        });
      }
    }
  }
  
  await scan(validatedPath);
  return results;
}

/**
 * Read file content safely
 */
export async function readFile(filePath: string): Promise<string> {
  const validatedPath = validatePath(filePath);
  
  if (!isFile(validatedPath)) {
    throw new FileSystemError('Path is not a file', 'NOT_A_FILE');
  }
  
  // Check file size (max 10MB by default)
  const stats = await fs.stat(validatedPath);
  const maxSize = parseInt(process.env.NEXT_PUBLIC_MAX_FILE_SIZE || '10485760');
  
  if (stats.size > maxSize) {
    throw new FileSystemError(
      `File too large: ${stats.size} bytes (max: ${maxSize})`,
      'FILE_TOO_LARGE'
    );
  }
  
  return await fs.readFile(validatedPath, 'utf-8');
}

/**
 * Get file metadata
 */
export async function getFileMetadata(filePath: string) {
  const validatedPath = validatePath(filePath);
  const stats = await fs.stat(validatedPath);
  
  return {
    path: filePath,
    size: stats.size,
    created: stats.birthtime,
    modified: stats.mtime,
    isDirectory: stats.isDirectory(),
    isFile: stats.isFile(),
  };
}

/**
 * Check if path is a Git repository
 */
export async function isGitRepository(dirPath: string): Promise<boolean> {
  try {
    const validatedPath = validatePath(dirPath);
    const gitPath = path.join(validatedPath, '.git');
    return existsSync(gitPath) && isDirectory(gitPath);
  } catch {
    return false;
  }
}

/**
 * Get repository name from path
 */
export function getRepositoryName(dirPath: string): string {
  return path.basename(dirPath);
}

/**
 * Parse git remote "origin" URL from .git/config (no child_process)
 */
export async function getGitRemote(repoPath: string): Promise<string | null> {
  try {
    const configPath = path.join(repoPath, '.git', 'config');
    const content = await fs.readFile(configPath, 'utf-8');
    const match = content.match(/\[remote "origin"\][\s\S]*?\n\s*url\s*=\s*(.+)/);
    return match ? match[1].trim() : null;
  } catch {
    return null;
  }
}

/**
 * Common file extensions to ignore during indexing
 */
export const IGNORE_PATTERNS = [
  // Dependencies
  'node_modules',
  'vendor',
  '.pnp',
  
  // Build outputs
  'dist',
  'build',
  'out',
  '.next',
  '.nuxt',
  '.output',
  
  // Cache
  '.cache',
  '.temp',
  '.tmp',
  
  // IDE
  '.vscode',
  '.idea',
  '.vs',
  
  // OS
  '.DS_Store',
  'Thumbs.db',
  
  // Version control
  '.git',
  '.svn',
  '.hg',
  
  // Logs
  '*.log',
  'logs',
  
  // Environment
  '.env',
  '.env.local',
  
  // Lock files
  'package-lock.json',
  'yarn.lock',
  'pnpm-lock.yaml',
];

/**
 * Check if file should be ignored
 */
export function shouldIgnore(filePath: string): boolean {
  const normalized = filePath.replace(/\\/g, '/');
  
  return IGNORE_PATTERNS.some(pattern => {
    if (pattern.includes('*')) {
      // Glob pattern
      const regex = new RegExp(pattern.replace('*', '.*'));
      return regex.test(normalized);
    }
    // Exact match or directory match
    return normalized.includes(pattern);
  });
}

/**
 * Get file language from extension
 */
export function getLanguageFromExtension(filePath: string): string | null {
  const ext = path.extname(filePath).slice(1).toLowerCase();
  
  const languageMap: Record<string, string> = {
    // JavaScript/TypeScript
    js: 'javascript',
    jsx: 'javascript',
    ts: 'typescript',
    tsx: 'typescript',
    mjs: 'javascript',
    cjs: 'javascript',
    
    // Python
    py: 'python',
    pyw: 'python',
    
    // Java
    java: 'java',
    
    // C/C++
    c: 'c',
    cpp: 'cpp',
    cc: 'cpp',
    cxx: 'cpp',
    h: 'c',
    hpp: 'cpp',
    
    // C#
    cs: 'csharp',
    
    // Go
    go: 'go',
    
    // Rust
    rs: 'rust',
    
    // Ruby
    rb: 'ruby',
    
    // PHP
    php: 'php',
    
    // Swift
    swift: 'swift',
    
    // Kotlin
    kt: 'kotlin',
    kts: 'kotlin',
    
    // Scala
    scala: 'scala',
    
    // Shell
    sh: 'shell',
    bash: 'shell',
    zsh: 'shell',
    
    // Web
    html: 'html',
    htm: 'html',
    css: 'css',
    scss: 'scss',
    sass: 'sass',
    less: 'less',
    
    // Data
    json: 'json',
    yaml: 'yaml',
    yml: 'yaml',
    xml: 'xml',
    toml: 'toml',
    
    // Markdown
    md: 'markdown',
    mdx: 'markdown',
    
    // SQL
    sql: 'sql',
    
    // Other
    dockerfile: 'dockerfile',
    makefile: 'makefile',
  };
  
  return languageMap[ext] || null;
}
