import { promises as fs } from 'fs';
import path from 'path';
import { prisma } from '../db';
import { getEmbeddings } from '../llm';
import { createGitParser } from '../git/parser';

export interface FileInfo {
  path: string;
  language: string | null;
  linesOfCode: number;
  lastAuthor: string | null;
  lastModified: Date | null;
  content: string;
}

export interface IndexingProgress {
  totalFiles: number;
  processedFiles: number;
  currentFile: string;
  progress: number;
}

export type ProgressCallback = (progress: IndexingProgress) => void;

/**
 * Detect programming language from file extension
 */
function detectLanguage(filePath: string): string | null {
  const base = path.basename(filePath);
  // Filename-based detection (no extension)
  const filenameMap: Record<string, string> = {
    Dockerfile: 'dockerfile',
    'Containerfile': 'dockerfile',
    Makefile: 'make',
    GNUmakefile: 'make',
    Rakefile: 'ruby',
    Gemfile: 'ruby',
    'CMakeLists.txt': 'cmake',
    Procfile: 'procfile',
    Brewfile: 'ruby',
  };
  if (filenameMap[base]) return filenameMap[base];

  const ext = path.extname(filePath).toLowerCase();
  const languageMap: Record<string, string> = {
    '.js': 'javascript',
    '.cjs': 'javascript',
    '.mjs': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.py': 'python',
    '.pyi': 'python',
    '.java': 'java',
    '.cpp': 'cpp',
    '.cxx': 'cpp',
    '.cc': 'cpp',
    '.c': 'c',
    '.h': 'c',
    '.hh': 'cpp',
    '.hpp': 'cpp',
    '.hxx': 'cpp',
    '.cs': 'csharp',
    '.go': 'go',
    '.rs': 'rust',
    '.rb': 'ruby',
    '.php': 'php',
    '.swift': 'swift',
    '.kt': 'kotlin',
    '.kts': 'kotlin',
    '.scala': 'scala',
    '.r': 'r',
    '.m': 'objective-c',
    '.mm': 'objective-c++',
    '.sql': 'sql',
    '.sh': 'shell',
    '.bash': 'shell',
    '.zsh': 'shell',
    '.fish': 'shell',
    '.ps1': 'powershell',
    '.html': 'html',
    '.htm': 'html',
    '.css': 'css',
    '.scss': 'scss',
    '.sass': 'sass',
    '.less': 'less',
    '.json': 'json',
    '.jsonc': 'json',
    '.json5': 'json',
    '.xml': 'xml',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.toml': 'toml',
    '.md': 'markdown',
    '.mdx': 'markdown',
    '.txt': 'text',
    '.dart': 'dart',
    '.vue': 'vue',
    '.svelte': 'svelte',
    '.astro': 'astro',
    '.gradle': 'gradle',
    '.lua': 'lua',
    '.proto': 'protobuf',
    '.tf': 'terraform',
    '.tfvars': 'terraform',
    '.hcl': 'hcl',
    '.ex': 'elixir',
    '.exs': 'elixir',
    '.erl': 'erlang',
    '.clj': 'clojure',
    '.cljs': 'clojure',
    '.cljc': 'clojure',
    '.hs': 'haskell',
    '.elm': 'elm',
    '.zig': 'zig',
    '.nim': 'nim',
    '.cr': 'crystal',
    '.dockerfile': 'dockerfile',
    '.gitignore': 'ignore',
    '.gitattributes': 'ignore',
    '.env': 'env',
    '.ini': 'ini',
    '.cfg': 'ini',
    '.conf': 'ini',
    '.properties': 'properties',
  };

  return languageMap[ext] || null;
}

/**
 * Check if file should be indexed
 */
function shouldIndexFile(filePath: string): boolean {
  const ignoredDirs = new Set([
    'node_modules',
    '.git',
    'dist',
    'build',
    'out',
    '.next',
    'coverage',
    '.vscode',
    '.idea',
    '__pycache__',
    'venv',
    'env',
    '.dart_tool',
    '.gradle',
    '.flutter-plugins',
    'Pods',
    'target',
    'vendor',
    '.claude',
    '.turbo',
    '.cache',
    'tmp',
    'uploads',
  ]);

  const ignoredExtensions = [
    '.lock',
    '.log',
    '.tmp',
    '.cache',
    '.map',
    '.woff',
    '.woff2',
    '.ttf',
    '.eot',
    '.png',
    '.jpg',
    '.jpeg',
    '.gif',
    '.svg',
    '.ico',
    '.pdf',
    '.zip',
    '.tar',
    '.gz',
    '.db',
    '.sqlite',
    '.sqlite3',
    '.so',
    '.dll',
    '.exe',
    '.bin',
    '.class',
    '.jar',
    '.war',
    '.dylib',
    '.o',
    '.a',
    '.pyc',
    '.pyo',
    '.dill',
    '.traineddata',
    '.weights',
    '.h5',
    '.onnx',
    '.pt',
    '.model',
    '.mp3',
    '.mp4',
    '.mov',
    '.avi',
    '.mkv',
    '.wav',
    '.flac',
    '.bmp',
    '.tiff',
    '.webp',
    '.heic',
    '.psd',
  ];

  // Any path segment (including the first) matching an ignored dir -> skip
  const segments = filePath.split(/[\\/]/);
  for (const seg of segments) {
    if (ignoredDirs.has(seg)) {
      return false;
    }
  }

  // Compound suffixes path.extname can't catch
  const lower = filePath.toLowerCase();
  if (lower.endsWith('.min.js') || lower.endsWith('.min.css')) {
    return false;
  }
  // SQLite sidecars (WAL/shared-memory/journal) created next to *.db files
  if (
    lower.endsWith('.db-wal') ||
    lower.endsWith('.db-shm') ||
    lower.endsWith('.db-journal') ||
    lower.endsWith('.sqlite-wal') ||
    lower.endsWith('.sqlite-shm')
  ) {
    return false;
  }

  const ext = path.extname(filePath).toLowerCase();
  if (ignoredExtensions.includes(ext)) {
    return false;
  }

  return true;
}

/**
 * Recursively get all files in a directory
 */
async function getAllFiles(dirPath: string, baseDir: string): Promise<string[]> {
  const files: string[] = [];

  try {
    const entries = await fs.readdir(dirPath, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(dirPath, entry.name);
      const relativePath = path.relative(baseDir, fullPath);

      if (entry.isDirectory()) {
        if (shouldIndexFile(relativePath)) {
          const subFiles = await getAllFiles(fullPath, baseDir);
          files.push(...subFiles);
        }
      } else if (entry.isFile() && shouldIndexFile(relativePath)) {
        files.push(fullPath);
      }
    }
  } catch (error) {
    console.error(`Error reading directory ${dirPath}:`, error);
  }

  return files;
}

/**
 * Read and analyze a file
 */
async function analyzeFile(filePath: string, repoPath: string): Promise<FileInfo | null> {
  try {
    const content = await fs.readFile(filePath, 'utf-8');
    const relativePath = path.relative(repoPath, filePath);
    const stats = await fs.stat(filePath);

    // Count lines of code
    const lines = content.split('\n');
    const linesOfCode = lines.filter((line: string) => line.trim().length > 0).length;

    // Get git info
    const gitParser = createGitParser(repoPath);
    const lastCommit = await gitParser.getLastCommitForFile(relativePath);

    return {
      path: relativePath,
      language: detectLanguage(filePath),
      linesOfCode,
      lastAuthor: lastCommit?.author || null,
      lastModified: lastCommit?.timestamp || stats.mtime,
      content,
    };
  } catch (error) {
    console.error(`Error analyzing file ${filePath}:`, error);
    return null;
  }
}

/**
 * Chunk file content for embedding
 */
function chunkContent(content: string, maxChunkSize: number = 1000): string[] {
  const lines = content.split('\n');
  const chunks: string[] = [];
  let currentChunk: string[] = [];
  let currentSize = 0;

  for (const line of lines) {
    const lineSize = line.length;

    if (currentSize + lineSize > maxChunkSize && currentChunk.length > 0) {
      chunks.push(currentChunk.join('\n'));
      currentChunk = [line];
      currentSize = lineSize;
    } else {
      currentChunk.push(line);
      currentSize += lineSize;
    }
  }

  if (currentChunk.length > 0) {
    chunks.push(currentChunk.join('\n'));
  }

  return chunks;
}

/**
 * Index a single file
 */
async function indexFile(
  fileInfo: FileInfo,
  repositoryId: string,
  repoPath: string
): Promise<void> {
  try {
    // Create or update file record
    const file = await prisma.file.upsert({
      where: {
        repositoryId_path: {
          repositoryId,
          path: fileInfo.path,
        },
      },
      update: {
        language: fileInfo.language,
        linesOfCode: fileInfo.linesOfCode,
        lastAuthor: fileInfo.lastAuthor,
        lastModified: fileInfo.lastModified,
      },
      create: {
        repositoryId,
        path: fileInfo.path,
        language: fileInfo.language,
        linesOfCode: fileInfo.linesOfCode,
        lastAuthor: fileInfo.lastAuthor,
        lastModified: fileInfo.lastModified,
      },
    });

    // Delete existing chunks for this file
    await prisma.codeChunk.deleteMany({
      where: { fileId: file.id },
    });

    // Chunk the content
    const chunks = chunkContent(fileInfo.content);

    // Create code chunks with embeddings
    for (let i = 0; i < chunks.length; i++) {
      const chunk = chunks[i];
      const startLine = i * 50 + 1; // Approximate line numbers
      const endLine = startLine + chunk.split('\n').length - 1;

      // Generate embedding
      let embedding: string | null = null;
      try {
        const embeddingVector = await getEmbeddings(chunk);
        embedding = JSON.stringify(embeddingVector);
      } catch (error) {
        console.error(`Error generating embedding for chunk:`, error);
      }

      await prisma.codeChunk.create({
        data: {
          repositoryId,
          fileId: file.id,
          chunkType: 'file',
          content: chunk,
          startLine,
          endLine,
          embedding,
          metadata: JSON.stringify({
            language: fileInfo.language,
            chunkIndex: i,
            totalChunks: chunks.length,
          }),
        },
      });
    }
  } catch (error) {
    console.error(`Error indexing file ${fileInfo.path}:`, error);
    throw error;
  }
}

/**
 * Index a single file by relative path — used by the watch command for incremental updates
 */
export async function indexSingleFile(
  repositoryId: string,
  repoPath: string,
  relativePath: string
): Promise<void> {
  const fullPath = path.join(repoPath, relativePath);
  const fileInfo = await analyzeFile(fullPath, repoPath);
  if (!fileInfo) return;
  await indexFile(fileInfo, repositoryId, repoPath);
}

/**
 * Index an entire repository
 */
export async function indexRepository(
  repositoryId: string,
  repoPath: string,
  onProgress?: ProgressCallback
): Promise<void> {
  // Update repository status
  await prisma.repository.update({
    where: { id: repositoryId },
    data: { status: 'indexing' },
  });

  // Create indexing job (declared outside try so the catch can update it)
  const job = await prisma.indexingJob.create({
    data: {
      repositoryId,
      status: 'running',
      startedAt: new Date(),
    },
  });

  try {

    // Get all files
    const files = await getAllFiles(repoPath, repoPath);
    const totalFiles = files.length;

    // Update job with total files
    await prisma.indexingJob.update({
      where: { id: job.id },
      data: { totalFiles },
    });

    // Index Git commits
    const gitParser = createGitParser(repoPath);
    const isGitRepo = await gitParser.isGitRepository();
    if (isGitRepo) {
      await gitParser.indexCommits(repositoryId);
    }

    // Index each file
    for (let i = 0; i < files.length; i++) {
      const filePath = files[i];
      const relativePath = path.relative(repoPath, filePath);

      // Update progress
      const progress = ((i + 1) / totalFiles) * 100;
      await prisma.indexingJob.update({
        where: { id: job.id },
        data: {
          processedFiles: i + 1,
          currentFile: relativePath,
          progress,
        },
      });

      if (onProgress) {
        onProgress({
          totalFiles,
          processedFiles: i + 1,
          currentFile: relativePath,
          progress,
        });
      }

      // Analyze and index file
      const fileInfo = await analyzeFile(filePath, repoPath);
      if (fileInfo) {
        await indexFile(fileInfo, repositoryId, repoPath);
      }
    }

    // Mark as complete
    await prisma.indexingJob.update({
      where: { id: job.id },
      data: {
        status: 'completed',
        completedAt: new Date(),
        progress: 100,
      },
    });

    await prisma.repository.update({
      where: { id: repositoryId },
      data: {
        status: 'ready',
        lastIndexed: new Date(),
      },
    });
  } catch (error) {
    console.error('Error indexing repository:', error);

    // Mark repo + job as failed so the UI doesn't show stale "running"
    await prisma.repository.update({
      where: { id: repositoryId },
      data: { status: 'error' },
    });

    await prisma.indexingJob
      .update({
        where: { id: job.id },
        data: {
          status: 'failed',
          completedAt: new Date(),
          error: error instanceof Error ? error.message : String(error),
        },
      })
      .catch(() => {});

    throw error;
  }
}

/**
 * Get indexing progress for a repository
 */
export async function getIndexingProgress(repositoryId: string): Promise<IndexingProgress | null> {
  const job = await prisma.indexingJob.findFirst({
    where: {
      repositoryId,
      status: 'running',
    },
    orderBy: {
      createdAt: 'desc',
    },
  });

  if (!job) {
    return null;
  }

  return {
    totalFiles: job.totalFiles || 0,
    processedFiles: job.processedFiles || 0,
    currentFile: job.currentFile || '',
    progress: job.progress,
  };
}

// Made with Bob
