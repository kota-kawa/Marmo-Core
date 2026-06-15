import { PrismaClient } from '@prisma/client';
import { PrismaLibSql } from '@prisma/adapter-libsql';

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined;
};

// Create Prisma adapter with config
const adapter = new PrismaLibSql({
  url: process.env.DATABASE_URL || 'file:./prisma/dev.db',
});

export const prisma =
  globalForPrisma.prisma ??
  new PrismaClient({
    adapter,
    log: process.env.NODE_ENV === 'development' ? ['query', 'error', 'warn'] : ['error'],
  });

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma;

// Initialize database tables on first import
async function initDB() {
  try {
    await prisma.$connect();

    // Concurrent readers/writers: WAL + busy_timeout avoids "Operation has timed
    // out" errors when the dashboard polls while the indexer is writing.
    try {
      await prisma.$executeRawUnsafe('PRAGMA journal_mode=WAL');
      await prisma.$executeRawUnsafe('PRAGMA synchronous=NORMAL');
      await prisma.$executeRawUnsafe('PRAGMA busy_timeout=15000');
    } catch (e) {
      console.warn('PRAGMA setup failed (non-fatal):', e);
    }
    
    // Check if tables exist
    const tables = await prisma.$queryRaw<Array<{ name: string }>>`
      SELECT name FROM sqlite_master WHERE type='table' AND name='Repository';
    `;
    
    if (tables.length === 0) {
      console.log('Creating database tables...');
      
      // Create all tables
      await prisma.$executeRaw`
        CREATE TABLE "Repository" (
          "id" TEXT NOT NULL PRIMARY KEY,
          "path" TEXT NOT NULL UNIQUE,
          "name" TEXT NOT NULL,
          "gitRemote" TEXT,
          "lastIndexed" DATETIME,
          "status" TEXT NOT NULL DEFAULT 'pending',
          "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          "updatedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
      `;

      await prisma.$executeRaw`
        CREATE TABLE "File" (
          "id" TEXT NOT NULL PRIMARY KEY,
          "repositoryId" TEXT NOT NULL,
          "path" TEXT NOT NULL,
          "language" TEXT,
          "linesOfCode" INTEGER,
          "size" INTEGER,
          "contentHash" TEXT,
          "lastAuthor" TEXT,
          "lastModified" DATETIME,
          "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          "updatedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY ("repositoryId") REFERENCES "Repository"("id") ON DELETE CASCADE
        )
      `;

      await prisma.$executeRaw`
        CREATE TABLE "CodeChunk" (
          "id" TEXT NOT NULL PRIMARY KEY,
          "repositoryId" TEXT NOT NULL,
          "fileId" TEXT NOT NULL,
          "chunkType" TEXT NOT NULL,
          "name" TEXT,
          "content" TEXT NOT NULL,
          "startLine" INTEGER NOT NULL,
          "endLine" INTEGER NOT NULL,
          "embedding" TEXT,
          "metadata" TEXT,
          "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          "updatedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY ("repositoryId") REFERENCES "Repository"("id") ON DELETE CASCADE,
          FOREIGN KEY ("fileId") REFERENCES "File"("id") ON DELETE CASCADE
        )
      `;

      await prisma.$executeRaw`
        CREATE TABLE "Commit" (
          "id" TEXT NOT NULL PRIMARY KEY,
          "repositoryId" TEXT NOT NULL,
          "hash" TEXT NOT NULL UNIQUE,
          "author" TEXT NOT NULL,
          "email" TEXT,
          "timestamp" DATETIME NOT NULL,
          "message" TEXT NOT NULL,
          "filesChanged" TEXT NOT NULL,
          "embedding" TEXT,
          "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY ("repositoryId") REFERENCES "Repository"("id") ON DELETE CASCADE
        )
      `;

      await prisma.$executeRaw`
        CREATE TABLE "IndexingJob" (
          "id" TEXT NOT NULL PRIMARY KEY,
          "repositoryId" TEXT NOT NULL,
          "status" TEXT NOT NULL,
          "progress" REAL NOT NULL DEFAULT 0,
          "totalFiles" INTEGER,
          "processedFiles" INTEGER,
          "currentFile" TEXT,
          "error" TEXT,
          "startedAt" DATETIME,
          "completedAt" DATETIME,
          "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY ("repositoryId") REFERENCES "Repository"("id") ON DELETE CASCADE
        )
      `;

      // Create indexes
      await prisma.$executeRaw`CREATE UNIQUE INDEX "File_repositoryId_path_key" ON "File"("repositoryId", "path")`;
      await prisma.$executeRaw`CREATE INDEX "File_repositoryId_idx" ON "File"("repositoryId")`;
      await prisma.$executeRaw`CREATE INDEX "File_contentHash_idx" ON "File"("contentHash")`;
      await prisma.$executeRaw`CREATE INDEX "CodeChunk_repositoryId_chunkType_idx" ON "CodeChunk"("repositoryId", "chunkType")`;
      await prisma.$executeRaw`CREATE INDEX "CodeChunk_fileId_idx" ON "CodeChunk"("fileId")`;
      await prisma.$executeRaw`CREATE INDEX "Commit_repositoryId_timestamp_idx" ON "Commit"("repositoryId", "timestamp")`;
      await prisma.$executeRaw`CREATE INDEX "IndexingJob_repositoryId_status_idx" ON "IndexingJob"("repositoryId", "status")`;

      console.log('✅ Database initialized successfully');
    }

    // Idempotent migrations for tables created by older versions of initDB
    const fileCols = await prisma.$queryRaw<Array<{ name: string }>>`
      PRAGMA table_info(File);
    `;
    const fileColNames = fileCols.map((c) => c.name);
    if (!fileColNames.includes('size')) {
      await prisma.$executeRawUnsafe('ALTER TABLE File ADD COLUMN size INTEGER');
    }
    if (!fileColNames.includes('contentHash')) {
      await prisma.$executeRawUnsafe('ALTER TABLE File ADD COLUMN contentHash TEXT');
      await prisma.$executeRawUnsafe(
        'CREATE INDEX IF NOT EXISTS File_contentHash_idx ON File(contentHash)'
      );
    }

    const repoCols = await prisma.$queryRaw<Array<{ name: string }>>`
      PRAGMA table_info(Repository);
    `;
    const repoColNames = repoCols.map((c) => c.name);
    if (!repoColNames.includes('gitRemote')) {
      await prisma.$executeRawUnsafe('ALTER TABLE Repository ADD COLUMN gitRemote TEXT');
    }
  } catch (error) {
    console.error('Database initialization error:', error);
  }
}

// Auto-initialize on import
initDB().catch(console.error);