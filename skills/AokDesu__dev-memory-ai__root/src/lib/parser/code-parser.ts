/**
 * Code Parser using Tree-sitter
 * Extracts code structure (functions, classes, methods) from source files
 */

import * as fs from 'fs';
import * as path from 'path';

// Tree-sitter types (will be available after npm install)
type Parser = any;
type Language = any;
type SyntaxNode = any;

export interface CodeSymbol {
  name: string;
  type: 'function' | 'class' | 'method' | 'variable' | 'interface' | 'type';
  startLine: number;
  endLine: number;
  startColumn: number;
  endColumn: number;
  docstring?: string;
  parameters?: string[];
  returnType?: string;
  parent?: string;
}

export interface ParsedFile {
  filePath: string;
  language: string;
  symbols: CodeSymbol[];
  imports: string[];
  exports: string[];
}

/**
 * Code Parser class for extracting code structure
 */
export class CodeParser {
  private parsers: Map<string, Parser> = new Map();
  private initialized = false;

  /**
   * Initialize tree-sitter parsers for supported languages
   */
  async initialize(): Promise<void> {
    if (this.initialized) return;

    try {
      // Dynamic import to avoid errors when tree-sitter is not installed
      const Parser = (await import('web-tree-sitter')).default;
      await Parser.init();

      // Initialize parsers for common languages
      const languages = [
        { name: 'javascript', file: 'tree-sitter-javascript.wasm' },
        { name: 'typescript', file: 'tree-sitter-typescript.wasm' },
        { name: 'python', file: 'tree-sitter-python.wasm' },
        { name: 'java', file: 'tree-sitter-java.wasm' },
        { name: 'go', file: 'tree-sitter-go.wasm' },
        { name: 'rust', file: 'tree-sitter-rust.wasm' },
        { name: 'cpp', file: 'tree-sitter-cpp.wasm' },
        { name: 'c', file: 'tree-sitter-c.wasm' },
      ];

      for (const lang of languages) {
        try {
          const parser = new Parser();
          const langModule = await Parser.Language.load(
            path.join(process.cwd(), 'node_modules', 'tree-sitter-wasms', 'out', lang.file)
          );
          parser.setLanguage(langModule);
          this.parsers.set(lang.name, parser);
        } catch (error) {
          console.warn(`Failed to load parser for ${lang.name}:`, error);
        }
      }

      this.initialized = true;
    } catch (error) {
      console.warn('Tree-sitter not available, falling back to regex parsing:', error);
      this.initialized = false;
    }
  }

  /**
   * Parse a file and extract code symbols
   */
  async parseFile(filePath: string): Promise<ParsedFile | null> {
    try {
      const content = fs.readFileSync(filePath, 'utf-8');
      const language = this.detectLanguage(filePath);

      if (!language) {
        return null;
      }

      // Try tree-sitter parsing first
      if (this.initialized && this.parsers.has(language)) {
        return await this.parseWithTreeSitter(filePath, content, language);
      }

      // Fallback to regex-based parsing
      return this.parseWithRegex(filePath, content, language);
    } catch (error) {
      console.error(`Error parsing file ${filePath}:`, error);
      return null;
    }
  }

  /**
   * Parse using tree-sitter
   */
  private async parseWithTreeSitter(
    filePath: string,
    content: string,
    language: string
  ): Promise<ParsedFile> {
    const parser = this.parsers.get(language)!;
    const tree = parser.parse(content);
    const symbols: CodeSymbol[] = [];
    const imports: string[] = [];
    const exports: string[] = [];

    // Extract symbols based on language
    this.traverseTree(tree.rootNode, symbols, imports, exports, language);

    return {
      filePath,
      language,
      symbols,
      imports,
      exports,
    };
  }

  /**
   * Traverse syntax tree and extract symbols
   */
  private traverseTree(
    node: SyntaxNode,
    symbols: CodeSymbol[],
    imports: string[],
    exports: string[],
    language: string,
    parent?: string
  ): void {
    // Extract based on node type
    const nodeType = node.type;

    // Function declarations
    if (
      nodeType === 'function_declaration' ||
      nodeType === 'function_definition' ||
      nodeType === 'method_definition'
    ) {
      const symbol = this.extractFunction(node, language, parent);
      if (symbol) symbols.push(symbol);
    }

    // Class declarations
    if (nodeType === 'class_declaration' || nodeType === 'class_definition') {
      const symbol = this.extractClass(node, language);
      if (symbol) {
        symbols.push(symbol);
        // Parse methods within class
        for (const child of node.children) {
          this.traverseTree(child, symbols, imports, exports, language, symbol.name);
        }
        return;
      }
    }

    // Import statements
    if (nodeType === 'import_statement' || nodeType === 'import_declaration') {
      const importPath = this.extractImport(node);
      if (importPath) imports.push(importPath);
    }

    // Export statements
    if (nodeType === 'export_statement' || nodeType === 'export_declaration') {
      const exportName = this.extractExport(node);
      if (exportName) exports.push(exportName);
    }

    // Recursively traverse children
    for (const child of node.children) {
      this.traverseTree(child, symbols, imports, exports, language, parent);
    }
  }

  /**
   * Extract function information from node
   */
  private extractFunction(node: SyntaxNode, language: string, parent?: string): CodeSymbol | null {
    try {
      const nameNode = node.childForFieldName('name');
      if (!nameNode) return null;

      const name = nameNode.text;
      const parameters = this.extractParameters(node);
      const returnType = this.extractReturnType(node);
      const docstring = this.extractDocstring(node);

      return {
        name,
        type: parent ? 'method' : 'function',
        startLine: node.startPosition.row + 1,
        endLine: node.endPosition.row + 1,
        startColumn: node.startPosition.column,
        endColumn: node.endPosition.column,
        parameters,
        returnType,
        docstring,
        parent,
      };
    } catch (error) {
      return null;
    }
  }

  /**
   * Extract class information from node
   */
  private extractClass(node: SyntaxNode, language: string): CodeSymbol | null {
    try {
      const nameNode = node.childForFieldName('name');
      if (!nameNode) return null;

      const name = nameNode.text;
      const docstring = this.extractDocstring(node);

      return {
        name,
        type: 'class',
        startLine: node.startPosition.row + 1,
        endLine: node.endPosition.row + 1,
        startColumn: node.startPosition.column,
        endColumn: node.endPosition.column,
        docstring,
      };
    } catch (error) {
      return null;
    }
  }

  /**
   * Extract function parameters
   */
  private extractParameters(node: SyntaxNode): string[] {
    const params: string[] = [];
    const paramsNode = node.childForFieldName('parameters');
    if (!paramsNode) return params;

    for (const child of paramsNode.children) {
      if (child.type === 'identifier' || child.type === 'parameter') {
        params.push(child.text);
      }
    }

    return params;
  }

  /**
   * Extract return type
   */
  private extractReturnType(node: SyntaxNode): string | undefined {
    const returnTypeNode = node.childForFieldName('return_type');
    return returnTypeNode?.text;
  }

  /**
   * Extract docstring/comment
   */
  private extractDocstring(node: SyntaxNode): string | undefined {
    // Look for comment node before the declaration
    const prevSibling = node.previousSibling;
    if (prevSibling && prevSibling.type === 'comment') {
      return prevSibling.text;
    }
    return undefined;
  }

  /**
   * Extract import path
   */
  private extractImport(node: SyntaxNode): string | null {
    const sourceNode = node.childForFieldName('source');
    return sourceNode?.text.replace(/['"]/g, '') || null;
  }

  /**
   * Extract export name
   */
  private extractExport(node: SyntaxNode): string | null {
    const nameNode = node.childForFieldName('name');
    return nameNode?.text || null;
  }

  /**
   * Fallback regex-based parsing for when tree-sitter is not available
   */
  private parseWithRegex(filePath: string, content: string, language: string): ParsedFile {
    const symbols: CodeSymbol[] = [];
    const imports: string[] = [];
    const exports: string[] = [];
    const lines = content.split('\n');

    // Language-specific regex patterns
    const patterns = this.getRegexPatterns(language);

    lines.forEach((line, index) => {
      // Extract functions
      const funcMatch = line.match(patterns.function);
      if (funcMatch) {
        symbols.push({
          name: funcMatch[1],
          type: 'function',
          startLine: index + 1,
          endLine: index + 1,
          startColumn: 0,
          endColumn: line.length,
        });
      }

      // Extract classes
      const classMatch = line.match(patterns.class);
      if (classMatch) {
        symbols.push({
          name: classMatch[1],
          type: 'class',
          startLine: index + 1,
          endLine: index + 1,
          startColumn: 0,
          endColumn: line.length,
        });
      }

      // Extract imports
      const importMatch = line.match(patterns.import);
      if (importMatch) {
        imports.push(importMatch[1]);
      }

      // Extract exports
      const exportMatch = line.match(patterns.export);
      if (exportMatch) {
        exports.push(exportMatch[1]);
      }
    });

    return {
      filePath,
      language,
      symbols,
      imports,
      exports,
    };
  }

  /**
   * Get regex patterns for language
   */
  private getRegexPatterns(language: string): {
    function: RegExp;
    class: RegExp;
    import: RegExp;
    export: RegExp;
  } {
    const patterns: Record<string, any> = {
      javascript: {
        function: /(?:function|const|let|var)\s+(\w+)\s*(?:=\s*)?(?:\([^)]*\)|async)/,
        class: /class\s+(\w+)/,
        import: /import.*from\s+['"]([^'"]+)['"]/,
        export: /export\s+(?:default\s+)?(?:class|function|const|let|var)\s+(\w+)/,
      },
      typescript: {
        function: /(?:function|const|let|var)\s+(\w+)\s*(?:=\s*)?(?:\([^)]*\)|async)/,
        class: /class\s+(\w+)/,
        import: /import.*from\s+['"]([^'"]+)['"]/,
        export: /export\s+(?:default\s+)?(?:class|function|const|let|var|interface|type)\s+(\w+)/,
      },
      python: {
        function: /def\s+(\w+)\s*\(/,
        class: /class\s+(\w+)/,
        import: /(?:from\s+[\w.]+\s+)?import\s+([\w.]+)/,
        export: /^(\w+)\s*=/,
      },
      java: {
        function: /(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(/,
        class: /(?:public|private)?\s*class\s+(\w+)/,
        import: /import\s+([\w.]+)/,
        export: /public\s+(?:class|interface)\s+(\w+)/,
      },
    };

    return patterns[language] || patterns.javascript;
  }

  /**
   * Detect language from file extension
   */
  private detectLanguage(filePath: string): string | null {
    const ext = path.extname(filePath).toLowerCase();
    const languageMap: Record<string, string> = {
      '.js': 'javascript',
      '.jsx': 'javascript',
      '.ts': 'typescript',
      '.tsx': 'typescript',
      '.py': 'python',
      '.java': 'java',
      '.go': 'go',
      '.rs': 'rust',
      '.cpp': 'cpp',
      '.cc': 'cpp',
      '.c': 'c',
      '.h': 'c',
    };

    return languageMap[ext] || null;
  }
}

// Singleton instance
let parserInstance: CodeParser | null = null;

/**
 * Get or create code parser instance
 */
export async function getCodeParser(): Promise<CodeParser> {
  if (!parserInstance) {
    parserInstance = new CodeParser();
    await parserInstance.initialize();
  }
  return parserInstance;
}

// Made with Bob
