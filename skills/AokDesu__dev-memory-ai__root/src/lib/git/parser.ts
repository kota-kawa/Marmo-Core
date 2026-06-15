import simpleGit, { SimpleGit, LogResult, DefaultLogFields } from 'simple-git';
import { prisma } from '../db';

export interface GitCommitInfo {
  hash: string;
  author: string;
  email: string;
  timestamp: Date;
  message: string;
  filesChanged: string[];
}

export class GitParser {
  private git: SimpleGit;
  private repoPath: string;

  constructor(repoPath: string) {
    this.repoPath = repoPath;
    this.git = simpleGit(repoPath);
  }

  /**
   * Check if directory is a git repository
   */
  async isGitRepository(): Promise<boolean> {
    try {
      await this.git.status();
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Get all commits from repository
   */
  async getCommitHistory(limit?: number): Promise<GitCommitInfo[]> {
    try {
      const log: LogResult<DefaultLogFields> = await this.git.log({
        maxCount: limit,
        '--all': null,
      });

      const commits: GitCommitInfo[] = [];

      for (const commit of log.all) {
        // Get files changed in this commit
        const diff = await this.git.show([
          '--name-only',
          '--pretty=format:',
          commit.hash,
        ]);

        const filesChanged = diff
          .split('\n')
          .filter((line: string) => line.trim().length > 0);

        commits.push({
          hash: commit.hash,
          author: commit.author_name,
          email: commit.author_email,
          timestamp: new Date(commit.date),
          message: commit.message,
          filesChanged,
        });
      }

      return commits;
    } catch (error) {
      console.error('Error getting commit history:', error);
      return [];
    }
  }

  /**
   * Get commits for a specific file
   */
  async getFileHistory(filePath: string): Promise<GitCommitInfo[]> {
    try {
      const log = await this.git.log({
        file: filePath,
        '--all': null,
      });

      return log.all.map((commit: DefaultLogFields) => ({
        hash: commit.hash,
        author: commit.author_name,
        email: commit.author_email,
        timestamp: new Date(commit.date),
        message: commit.message,
        filesChanged: [filePath],
      }));
    } catch (error) {
      console.error(`Error getting file history for ${filePath}:`, error);
      return [];
    }
  }

  /**
   * Get the last commit that modified a file
   */
  async getLastCommitForFile(filePath: string): Promise<GitCommitInfo | null> {
    try {
      const log = await this.git.log({
        file: filePath,
        maxCount: 1,
      });

      if (log.all.length === 0) {
        return null;
      }

      const commit = log.all[0];
      return {
        hash: commit.hash,
        author: commit.author_name,
        email: commit.author_email,
        timestamp: new Date(commit.date),
        message: commit.message,
        filesChanged: [filePath],
      };
    } catch (error) {
      console.error(`Error getting last commit for ${filePath}:`, error);
      return null;
    }
  }

  /**
   * Index all commits into database
   */
  async indexCommits(repositoryId: string, limit?: number): Promise<number> {
    try {
      const commits = await this.getCommitHistory(limit);
      let indexed = 0;

      for (const commit of commits) {
        try {
          await prisma.commit.upsert({
            where: { hash: commit.hash },
            update: {
              author: commit.author,
              email: commit.email,
              timestamp: commit.timestamp,
              message: commit.message,
              filesChanged: JSON.stringify(commit.filesChanged),
            },
            create: {
              repositoryId,
              hash: commit.hash,
              author: commit.author,
              email: commit.email || '',
              timestamp: commit.timestamp,
              message: commit.message,
              filesChanged: JSON.stringify(commit.filesChanged),
            },
          });
          indexed++;
        } catch (error) {
          console.error(`Error indexing commit ${commit.hash}:`, error);
        }
      }

      return indexed;
    } catch (error) {
      console.error('Error indexing commits:', error);
      return 0;
    }
  }

  /**
   * Get repository statistics
   */
  // async getRepositoryStats() {
  //   try {
  //     const log = await this.git.log({ '--all': null });
  //     const status = await this.git.status();
  //
  //     const authors = new Set(log.all.map((c: DefaultLogFields) => c.author_name));
  //     const branches = await this.git.branch();
  //
  //     return {
  //       totalCommits: log.total,
  //       totalAuthors: authors.size,
  //       currentBranch: branches.current,
  //       allBranches: branches.all,
  //       isClean: status.isClean(),
  //       modified: status.modified.length,
  //       created: status.created.length,
  //       deleted: status.deleted.length,
  //     };
  //   } catch (error) {
  //     console.error('Error getting repository stats:', error);
  //     return null;
  //   }
  // }
}

/**
 * Create a GitParser instance for a repository
 */
export function createGitParser(repoPath: string): GitParser {
  return new GitParser(repoPath);
}

// Made with Bob
