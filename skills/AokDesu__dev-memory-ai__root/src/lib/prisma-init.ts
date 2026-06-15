import { PrismaClient } from '@prisma/client';
import { PrismaLibSql } from '@prisma/adapter-libsql';
import { createClient } from '@libsql/client';

/**
 * Initialize database with schema
 * This is a one-time setup script
 */
export async function initializeDatabase() {
  // Create Prisma adapter with config
  const adapter = new PrismaLibSql({
    url: process.env.DATABASE_URL || 'file:./prisma/dev.db',
  });
  
  const prisma = new PrismaClient({ adapter });

  try {
    // Test connection
    await prisma.$connect();
    console.log('✅ Database connected successfully');
    
    // Check if tables exist
    const tables = await prisma.$queryRaw`
      SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';
    `;
    
    if (Array.isArray(tables) && tables.length === 0) {
      console.log('📦 Database is empty, creating tables...');
      
      // Create tables
      await prisma.$executeRaw`
        CREATE TABLE IF NOT EXISTS "Repository" (
          "id" TEXT NOT NULL PRIMARY KEY,
          "path" TEXT NOT NULL UNIQUE,
          "name" TEXT NOT NULL,
          "lastIndexed" DATETIME,
          "status" TEXT NOT NULL DEFAULT 'pending',
          "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          "updatedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
      `;

      await prisma.$executeRaw`
        CREATE TABLE IF NOT EXISTS "File" (
          "id" TEXT NOT NULL PRIMARY KEY,
          "repositoryId" TEXT NOT NULL,
          "path" TEXT NOT NULL,
          "language" TEXT,
          "linesOfCode" INTEGER,
          "lastAuthor" TEXT,
          "lastModified" DATETIME,
          "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          "updatedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY ("repositoryId") REFERENCES "Repository"("id") ON DELETE CASCADE
        )
      `;

      await prisma.$executeRaw`
        CREATE TABLE IF NOT EXISTS "CodeChunk" (
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
        CREATE TABLE IF NOT EXISTS "Commit" (
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
        CREATE TABLE IF NOT EXISTS "IndexingJob" (
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
      await prisma.$executeRaw`CREATE UNIQUE INDEX IF NOT EXISTS "File_repositoryId_path_key" ON "File"("repositoryId", "path")`;
      await prisma.$executeRaw`CREATE INDEX IF NOT EXISTS "File_repositoryId_idx" ON "File"("repositoryId")`;
      await prisma.$executeRaw`CREATE INDEX IF NOT EXISTS "CodeChunk_repositoryId_chunkType_idx" ON "CodeChunk"("repositoryId", "chunkType")`;
      await prisma.$executeRaw`CREATE INDEX IF NOT EXISTS "CodeChunk_fileId_idx" ON "CodeChunk"("fileId")`;
      await prisma.$executeRaw`CREATE INDEX IF NOT EXISTS "Commit_repositoryId_timestamp_idx" ON "Commit"("repositoryId", "timestamp")`;
      await prisma.$executeRaw`CREATE INDEX IF NOT EXISTS "IndexingJob_repositoryId_status_idx" ON "IndexingJob"("repositoryId", "status")`;

      console.log('✅ Database tables created successfully');
    } else {
      console.log('✅ Database tables already exist');
    }

    return true;
  } catch (error) {
    console.error('❌ Database initialization failed:', error);
    return false;
  } finally {
    await prisma.$disconnect();
  }
}

// Run if called directly
if (require.main === module) {
  initializeDatabase()
    .then((success) => {
      process.exit(success ? 0 : 1);
    })
    .catch((error) => {
      console.error(error);
      process.exit(1);
    });
}