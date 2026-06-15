// Project Types
export type ProjectStatus = 'pending' | 'indexing' | 'ready' | 'error';

export interface Project {
  id: string;
  name: string;
  path: string;
  status: ProjectStatus;
  lastIndexed: string | null;
  filesCount?: number;
  createdAt: string;
  branch?: string;
  indexing?: boolean;
}

export interface ProjectSelectRequest {
  path: string;
}

export interface ProjectSelectResponse {
  projectId: string;
  name: string;
  status: ProjectStatus;
  progress: number;
  message?: string;
}

export interface ProjectListResponse {
  projects: Project[];
}

export interface ProjectStatusResponse {
  projectId: string;
  status: ProjectStatus;
  progress: number;
  processedFiles: number;
  totalFiles: number;
  currentFile?: string;
  error?: string;
  startedAt?: string;
  completedAt?: string;
}

export interface ProjectIndexRequest {
  projectId: string;
  incremental?: boolean;
}

export interface ProjectIndexResponse {
  jobId: string;
  status: 'started' | 'already_running';
  message: string;
}

// Search Types
export type ChunkType = 'function' | 'class' | 'file' | 'comment';

export interface SearchFilters {
  fileType?: string[];
  chunkType?: ChunkType[];
  author?: string;
  dateRange?: {
    from: string;
    to: string;
  };
}

export interface SearchRequest {
  projectId: string;
  query: string;
  limit?: number;
  filters?: SearchFilters;
}

export interface SearchResult {
  id: string;
  file: string;
  content: string;
  score: number;
  lineStart: number;
  lineEnd: number;
  language: string;
  chunkType: ChunkType;
  name?: string;
  context?: {
    commit?: {
      hash: string;
      author: string;
      message: string;
      date: string;
    };
  };
}

export interface SearchResponse {
  results: SearchResult[];
  totalResults: number;
  query: string;
  executionTime: number;
}

// Chat Types
export type ChatEventType = 'thinking' | 'context' | 'token' | 'done' | 'error';

export interface ChatRequest {
  projectId: string;
  message: string;
  conversationId?: string;
  context?: string;
}

export interface ChatSource {
  file: string;
  lines: [number, number];
  content: string;
}

export interface ChatThinkingEvent {
  type: 'thinking';
  content: string;
}

export interface ChatContextEvent {
  type: 'context';
  sources: ChatSource[];
}

export interface ChatTokenEvent {
  type: 'token';
  content: string;
}

export interface ChatDoneEvent {
  type: 'done';
  conversationId: string;
}

export interface ChatErrorEvent {
  type: 'error';
  error: string;
}

export type ChatEvent =
  | ChatThinkingEvent
  | ChatContextEvent
  | ChatTokenEvent
  | ChatDoneEvent
  | ChatErrorEvent;

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: Array<{
    file: string;
    lines: [number, number];
  }>;
}
export interface ChatConversation {
  id: string;
  title: string;
  group: string;
  messages: ChatMessage[];
  createdAt: string;
}


export interface ChatHistoryResponse {
  conversationId: string;
  messages: ChatMessage[];
}

// Summary Types
export interface RepositorySummary {
  projectId: string;
  name: string;
  path: string;
  statistics: {
    totalFiles: number;
    totalLines: number;
    languages: Record<string, number>;
    authors: Array<{
      name: string;
      commits: number;
      linesChanged: number;
    }>;
  };
  techStack: string[];
  keyFiles: Array<{
    path: string;
    importance: number;
    reason: string;
  }>;
  recentActivity: Array<{
    date: string;
    commits: number;
    filesChanged: number;
  }>;
  structure: {
    directories: number;
    maxDepth: number;
    mainDirectories: string[];
  };
}

// File Types
export interface FileItem {
  path: string;
  type: 'file' | 'directory';
  language?: string;
  size?: number;
  lastModified?: string;
}

export interface FileTreeNode extends FileItem {
  children?: FileTreeNode[];
  expanded?: boolean;
}

export interface FileListResponse {
  files: FileItem[];
  totalFiles: number;
}

export interface FileContentResponse {
  path: string;
  content: string;
  language: string;
  lines: number;
  metadata: {
    lastAuthor?: string;
    lastModified?: string;
    commits?: number;
  };
}

// Commit Types
export interface Commit {
  hash: string;
  author: string;
  email: string;
  timestamp: string;
  message: string;
  filesChanged: string[];
  additions: number;
  deletions: number;
}

export interface CommitListResponse {
  commits: Commit[];
  totalCommits: number;
}

export interface CommitDetail {
  hash: string;
  author: string;
  email: string;
  timestamp: string;
  message: string;
  filesChanged: Array<{
    path: string;
    status: 'added' | 'modified' | 'deleted';
    additions: number;
    deletions: number;
  }>;
  additions: number;
  deletions: number;
  diff?: string;
}

// Analysis Types
export type AnalysisType = 'impact' | 'dependencies' | 'usage';

export interface AnalysisRequest {
  projectId: string;
  type: AnalysisType;
  target: string;
}

export interface AnalysisResponse {
  type: string;
  target: string;
  analysis: {
    dependencies?: string[];
    dependents?: string[];
    impactScore?: number;
    affectedFiles?: number;
    recommendations?: string[];
    usageCount?: number;
    usageLocations?: Array<{
      file: string;
      line: number;
    }>;
  };
}

// External API Types
export interface ExternalQueryRequest {
  projectId: string;
  query: string;
  context?: string;
  maxResults?: number;
}

export interface ExternalQueryResponse {
  answer: string;
  sources: Array<{
    file: string;
    lines: [number, number];
    content: string;
    relevance: number;
  }>;
  confidence: number;
  executionTime: number;
}

export interface EmbedRequest {
  text: string;
}

export interface EmbedResponse {
  embedding: number[];
  model: string;
}

// WebSocket Event Types
export interface IndexingProgressEvent {
  type: 'indexing_progress';
  projectId: string;
  progress: number;
  currentFile: string;
  processedFiles: number;
  totalFiles: number;
}

export interface IndexingCompleteEvent {
  type: 'indexing_complete';
  projectId: string;
  filesIndexed: number;
  duration: number;
}

export interface FileChangedEvent {
  type: 'file_changed';
  projectId: string;
  file: string;
  changeType: 'added' | 'modified' | 'deleted';
}

export type WebSocketEvent =
  | IndexingProgressEvent
  | IndexingCompleteEvent
  | FileChangedEvent;

// Error Response
export interface ErrorResponse {
  error: string;
  code: string;
  details?: any;
}

// UI-specific types
export interface NavigationItem {
  key: string;
  label: string;
  icon: React.ReactNode;
  kbd?: string;
}

export interface CodeToken {
  t: string; // token type: 'kw', 'fn', 'str', 'num', 'com', 'type', 'prop', 'p' (plain)
  v: string; // value
}

export interface CodeLine {
  tokens: CodeToken[];
  lineNumber: number;
}

// Made with Bob
