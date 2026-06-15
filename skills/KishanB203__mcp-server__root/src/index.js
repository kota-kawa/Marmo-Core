/**
 * @module src/index
 *
 * MCP Server bootstrap — entry point for the MCP Automation pipeline.
 *
 * Responsibilities:
 *   1. Load environment (via config/env.js, which calls dotenv.config() once)
 *   2. Register all tool schemas with the MCP SDK
 *   3. Route incoming `CallToolRequest` messages to the correct handler
 *   4. Return formatted text responses to the MCP client
 *
 * Tool categories:
 *   ado_*        — Azure DevOps work-item CRUD
 *   figma_*      — Figma design file operations
 *   branch_*     — Git branch naming utilities
 *   conflict_*   — Pre-flight conflict detection
 *   agent_*      — Autonomous agent orchestration
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import fs from "fs";
import http from "node:http";
import { randomUUID } from "node:crypto";

// Config — must be imported before any infrastructure module so that dotenv
// is loaded and process.env is populated before clients are instantiated.
import {
  DEFAULT_AREA_PATH,
  DEFAULT_SPRINT_PATH,
  DEFAULT_BACKLOG_TAGS,
  MCP_TRANSPORT,
  MCP_PORT,
  MCP_HOST,
  MCP_PUBLIC_URL,
  MCP_SERVER_NAME,
} from "./config/env.js";
import { TOOLS } from "./config/tool-definitions.js";

// Infrastructure clients
import { validateFigmaConfig } from "./infrastructure/figma-client.js";

// ADO tools
import { getWorkItem } from "./tools/ado/get-work-item.js";
import { listWorkItems } from "./tools/ado/list-work-items.js";
import {
  updateWorkItemState,
  addWorkItemComment,
  addWorkItemDependency,
} from "./tools/ado/update-work-item.js";
import { createWorkItem } from "./tools/ado/create-work-item.js";

// Figma tools
import {
  getFigmaFile,
  runFigmaDesignWorkflow,
  addFigmaLinkToAdo,
} from "./tools/figma/figma-tools.js";

// Branch tools
import { generateBranchName, validateBranchName } from "./tools/branch/branch-naming.js";
import { preflightCheck } from "./tools/branch/conflict-prevention.js";

// Agents
import developerAgent from "./agents/developer-agent.js";
import devopsAgent from "./agents/devops-agent.js";
import { ticketAgent } from "./agents/ticketAgent.js";
import { codeAgent } from "./agents/codeAgent.js";
import { prAgent } from "./agents/prAgent.js";
import { reviewAgent } from "./agents/reviewAgent.js";

// Services
import { runWorkflow } from "./services/workflow.js";
import {
  listMcpDocFiles,
  loadMcpDocsMarkdown,
} from "./services/mcp-docs.js";
import {
  loadProjectRulesMarkdown,
  listProjectRuleMarkdownFiles,
} from "./services/project-rules.js";

// ─────────────────────────────────────────────────────────────────────────────
// MCP Server
// ─────────────────────────────────────────────────────────────────────────────

const MCP_SERVER_VERSION = "2.0.0";

const createServerInstance = () =>
  new Server(
    { name: MCP_SERVER_NAME, version: MCP_SERVER_VERSION },
    { capabilities: { tools: {} } }
  );

const writeRuntimeLog = (message, meta = undefined) => {
  const ts = new Date().toISOString();
  const payload = { serverName: MCP_SERVER_NAME, ...(meta || {}) };
  const extra = ` ${JSON.stringify(payload)}`;
  process.stderr.write(`[${ts}] ${message}${extra}\n`);
};

const registerHandlers = (server) => {

// ── List tools ────────────────────────────────────────────────────────────────

  server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: TOOLS }));

const formatProjectRulesDevAppendix = (projectRules) => {
  if (!projectRules) return "";
  const files = projectRules.files ?? [];
  const fileLine = files.length
    ? files.map((f) => `\`${f}\``).join(", ")
    : "_(add `*.md` under `rules/`)_";
  const md = String(projectRules.markdown || "").trim();
  if (!md) {
    return (
      `\n\n---\n\n## Project rules (\`rules/\`)\n` +
      `**Files:** ${fileLine}\n` +
      `_No markdown content yet — add standards as \`.md\` files._`
    );
  }
  return (
    `\n\n---\n\n## Project rules (\`rules/\`) — follow while implementing\n` +
    `**Files:** ${fileLine}\n\n` +
    `\`\`\`markdown\n${md}\n\`\`\``
  );
};

const formatMcpDocsAppendix = (projectDir) => {
  const files = listMcpDocFiles({ projectDir });
  const md = loadMcpDocsMarkdown({ projectDir }).trim();

  if (!files.length && !md) {
    return "";
  }

  if (!md) {
    return (
      `\n\n---\n\n## MCP docs (\`mcp_docs/\`)` +
      `\n**Files:** ${files.map((f) => `\`${f}\``).join(", ")}`
    );
  }

  return (
    `\n\n---\n\n## MCP docs (\`mcp_docs/\`) — auto-loaded` +
    `\n**Files:** ${files.length ? files.map((f) => `\`${f}\``).join(", ") : "_(none)_"}\n\n` +
    `\`\`\`markdown\n${md}\n\`\`\``
  );
};

const formatPrePrSuccessAppendix = (validation) => {
  if (!validation) return "";
  const ar = validation.automatedReviewPreview;
  if (!ar) return "";
  const status = ar.issues.length === 0 ? "APPROVED (no blocking review issues)" : "CHANGES REQUESTED";
  const lines = [
    `\n\n---\n\n## Pre-PR automated review (same checks as ReviewerAgent)`,
    `**Status:** ${status}`,
  ];
  if (ar.issues.length) lines.push(`**Issues:** ${ar.issues.join("; ")}`);
  if (ar.warnings.length) lines.push(`**Warnings:** ${ar.warnings.join("; ")}`);
  if (validation.ruleFiles?.length) {
    lines.push(`**Rules considered:** ${validation.ruleFiles.map((f) => `\`${f}\``).join(", ")}`);
  }
  if (validation.mcpDocFiles?.length) {
    lines.push(`**MCP docs considered:** ${validation.mcpDocFiles.map((f) => `\`${f}\``).join(", ")}`);
  }
  return lines.join("\n");
};

// ── Call tool ─────────────────────────────────────────────────────────────────

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  const startedAt = Date.now();
  writeRuntimeLog("tool.call.started", { tool: name });

  try {
    switch (name) {

      // ── Azure DevOps ───────────────────────────────────────────────────────

      case "ado_get_work_item":
        return text(formatWorkItem(await getWorkItem(args.id)));

      case "ado_list_work_items":
        return text(formatWorkItemList(await listWorkItems(args)));

      case "ado_create_work_item": {
        // Always generate requirements first (handled in ticketAgent.createTicket)
        const item = await ticketAgent.createTicket(args);
        return text(
          `Work item created:\n` +
          `**#${item.id}** — ${item.title}\n` +
          `**Type:** ${item.type} | **State:** ${item.state ?? "N/A"}\n` +
          (typeof item.subtaskCount === "number"
            ? `**Subtasks created:** ${item.subtaskCount}\n`
            : "") +
          `**URL:** ${item.url}`
        );
      }

      case "ado_update_work_item_state": {
        const r = await updateWorkItemState(args.id, args.state);
        return text(
          `#${r.id} "${r.title}" -> **${r.newState}**\n${r.url}`
        );
      }

      case "ado_add_comment": {
        const r = await addWorkItemComment(args.id, args.comment);
        return text(`Comment added to #${args.id} by ${r.createdBy}`);
      }

      // ── Figma ──────────────────────────────────────────────────────────────

      case "figma_get_file": {
        const f = await getFigmaFile(args.fileKey);
        return text(
          `# Figma: ${f.name}\n` +
          `**URL:** ${f.url}\n` +
          `**Modified:** ${f.lastModified}\n` +
          `**Pages:** ${f.pages?.map((p) => p.name).join(", ")}`
        );
      }

      case "figma_generate_wireframe": {
        const task = await getWorkItem(args.taskId);
        const r = await runFigmaDesignWorkflow(task);
        return text(
          `# Figma Wireframe — Task #${task.id}\n\n` +
          `**Figma URL:** ${r.figmaFile?.url}\n` +
          `**Status:** ${r.wireframe?.message ?? r.wireframe?.error}\n` +
          `**ADO:** ${r.adoUpdate?.message ?? r.adoUpdate?.error}\n\n` +
          `\`\`\`\n${r.wireframe?.wireframeSpec ?? ""}\n\`\`\``
        );
      }

      case "figma_add_ado_link": {
        const r = await addFigmaLinkToAdo(args.adoTaskId, args.figmaUrl, args.figmaFileName);
        return text(`${r.message}`);
      }

      // ── Branch / Conflict ──────────────────────────────────────────────────

      case "branch_generate_name": {
        const branchName = generateBranchName(args.taskId, args.taskTitle);
        const check = validateBranchName(branchName);
        return text(
          `**Branch:** \`${branchName}\`\n` +
          `**Valid:** ${check.valid ? "Yes" : "No - " + check.reason}`
        );
      }

      case "conflict_preflight_check": {
        const r = preflightCheck(args.taskId, args.branchName, {
          projectDir: args.projectDir,
        });
        const lines = [
          `# Preflight Check`,
          `**Proceed:** ${r.canProceed ? "Yes" : "Conflicts detected"}`,
          ...r.warnings,
        ];
        if (r.existingBranch) lines.push(`**Existing branch:** \`${r.existingBranch}\``);
        if (r.existingPR) lines.push(`**Existing PR:** #${r.existingPR.number}`);
        return text(lines.join("\n"));
      }

      case "project_get_rules": {
        const projectDir = args.projectDir;
        const files = listProjectRuleMarkdownFiles({ projectDir });
        const md = loadProjectRulesMarkdown({ projectDir });
        const mcpFiles = listMcpDocFiles({ projectDir });
        const mcpMd = loadMcpDocsMarkdown({ projectDir });
        return text(
          `# Project rules — \`rules/\`\n\n` +
            `**Files (${files.length}):** ${files.length ? files.map((f) => `\`${f}\``).join(", ") : "_(none)_"}\n\n` +
            `---\n\n` +
            (md.trim() || "_No markdown content in `rules/`._") +
            `\n\n---\n\n# MCP docs — \`mcp_docs/\`\n\n` +
            `**Files (${mcpFiles.length}):** ${mcpFiles.length ? mcpFiles.map((f) => `\`${f}\``).join(", ") : "_(none)_"}\n\n` +
            (mcpMd.trim() || "_No markdown content in `mcp_docs/`._")
        );
      }

      // ── Agents ────────────────────────────────────────────────────────────

      case "agent_analyze_task": {
        const r = await ticketAgent.analyzeTicket(args.taskId);
        return text(
          `# ProductOwnerAgent — Task #${args.taskId}\n\n` +
          r.analysis.summary + "\n\n" +
          `**UI Design needed:** ${r.analysis.requires.uiDesign ? "Yes" : "No"}\n` +
          `**API changes needed:** ${r.analysis.requires.apiChanges ? "Yes" : "No"}\n` +
          `**Ready for dev:** ${
            r.analysis.validation.readyForDevelopment
              ? "Yes"
              : "Issues: " + r.analysis.validation.issues.join(", ")
          }`
        );
      }

      case "agent_generate_architecture": {
        const r = codeAgent.generateArchitecture(args.featureName, args.rootDir);
        const projectDir = args.rootDir;
        return text(
          `# ArchitectAgent — Scaffold: ${r.featureName}\n\n` +
          `**Files created (${r.structure.files.length}):**\n` +
          r.structure.files.map((f) => `- \`${f.path}\``).join("\n") +
            formatProjectRulesDevAppendix(r.projectRules) +
            formatMcpDocsAppendix(projectDir)
        );
      }

      case "agent_start_development": {
        const task = await getWorkItem(args.taskId);
        const projectDir = args.projectDir;
        const r = await developerAgent.workOnTask(task, {
          force: args.force,
          projectDir,
        });
        return text(
          `# DeveloperAgent — ${r.success ? "Ready" : "Blocked"}\n\n` +
          r.log.join("\n") +
          (r.warning ? `\n\n${r.warning}` : "") +
            formatProjectRulesDevAppendix(r.projectRules) +
            formatMcpDocsAppendix(projectDir)
        );
      }

      case "agent_create_pr": {
        const task = await getWorkItem(args.taskId);
        const projectDir = args.projectDir;
        const r = await prAgent.createPullRequest(task, args.branchName, {
          figmaUrl: args.figmaUrl,
          summary: args.summary,
          projectDir,
        });
        if (!r.success) {
          const v = r.validation;
          const extra =
            v?.automatedReviewPreview && v.automatedReviewPreview.issues.length === 0
              ? `\n\n_(Automated review preview would not block on the same diff — fix gate issues above first.)_`
              : "";
          return text(
            `${r.error}\n\n**Gate issues:** ${v?.issues?.join("; ") ?? "n/a"}\n` +
              `**Rule files:** ${v?.ruleFiles?.length ? v.ruleFiles.map((f) => `\`${f}\``).join(", ") : "none"}` +
              `\n**MCP docs files:** ${v?.mcpDocFiles?.length ? v.mcpDocFiles.map((f) => `\`${f}\``).join(", ") : "none"}` +
              extra
          );
        }
        return text(
          `PR: ${r.prUrl}\n**Title:** ${r.title}` +
            formatPrePrSuccessAppendix(r.validation) +
            formatMcpDocsAppendix(projectDir)
        );
      }

      case "agent_review_pr": {
        const projectDir = args.projectDir;
        const r = await reviewAgent.reviewPullRequest(args.prNumber, args.branchName, {
          projectDir,
        });
        return text(
          r.reviewBody +
          `\n\n**Posted:** ${r.posted ? "Yes" : "No (gh CLI required)"}` +
          formatMcpDocsAppendix(projectDir)
        );
      }

      case "agent_merge_pr": {
        const r = await devopsAgent.mergePR(args.prNumber, {
          strategy: args.strategy,
          taskId: args.taskId,
        });
        return text(
          `# DevOpsAgent — ${r.success ? "Merged" : "Failed"}\n\n` +
          r.log.join("\n") +
          (r.error ? `\n\n${r.error}` : "")
        );
      }

      case "agent_generate_solution_requirements": {
        const r = await codeAgent.generateRequirements({
          featureName: args.featureName,
          figmaInput: args.figmaInput,
          businessRequirements: args.businessRequirements,
          outputDir: args.outputDir,
          requirementDocPath: args.requirementDocPath,
          figmaImagesDir: args.figmaImagesDir,
        });
        const figmaMeta = [
          r.figmaAnalysis?.fileKey ? `**Figma file key:** ${r.figmaAnalysis.fileKey}` : null,
          r.figmaAnalysis?.warning ? `**Figma API:** ${r.figmaAnalysis.warning}` : null,
        ]
          .filter(Boolean)
          .join("\n");
        const src = r.sources;
        const sourceLines = [
          `**Requirements file:** \`${src.requirementFile}\``,
          `**Figma screenshots folder:** \`${src.figmaImagesDir}\` (${src.imageFileCount} image(s))`,
        ].join("\n");
        return text(
          `# SolutionRequirementsAgent — Work item content\n\n` +
          `**Feature:** ${r.featureName}\n` +
          `${sourceLines}\n` +
          (figmaMeta ? `\n${figmaMeta}\n` : "") +
          `\n${r.workItemFlowNote}\n\n---\n\n${r.workItemDescription}`
        );
      } 

      case "agent_full_workflow": {
        const result = await runWorkflow(args.taskId, {
          projectDir: args.projectDir,
          skipFigma: args.skipFigma,
          skipArch: args.skipArch,
          force: args.force,
          autoCreateBugOnReviewFail: args.autoCreateBugOnReviewFail,
        });

        if (!result.success) {
          return text(
            `# Workflow blocked — Task #${args.taskId}\n\n` +
            `**Reason:** ${result.reason ?? "Unknown"}\n` +
            (result.preflight?.warnings?.join("\n") ?? "")
          );
        }

        return text([
          `# Full Workflow Complete — Task #${args.taskId}`,
          `**Task:** ${result.task?.title}`,
          `**Branch:** \`${result.branchName}\``,
          `**PR:** ${result.pr?.url ?? "Not created"}`,
          `**Figma:** ${result.figma?.figmaFile?.url ?? "Skipped"}`,
          `**Architecture:** ${result.architecture ? "Scaffolded" : "Skipped"}`,
          `**Merged:** ${result.merge?.merged ? "Yes" : "Not merged"}`,
        ].join("\n"));
      }

      default:
        throw new Error(`Unknown tool: "${name}"`);
    }
  } catch (error) {
    writeRuntimeLog("tool.call.failed", {
      tool: name,
      durationMs: Date.now() - startedAt,
      error: error?.message || String(error),
    });
    return {
      content: [{ type: "text", text: `Error in "${name}": ${error.message}` }],
      isError: true,
    };
  } finally {
    writeRuntimeLog("tool.call.finished", {
      tool: name,
      durationMs: Date.now() - startedAt,
    });
  }
});
};

// ─────────────────────────────────────────────────────────────────────────────
// Response formatters
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Wraps a plain string in the MCP text-content envelope.
 *
 * @param {string} str
 * @returns {{ content: Array<{type:'text',text:string}> }}
 */
const text = (str) => {
  return { content: [{ type: "text", text: str }] };
}

/**
 * Formats a full work item as Markdown.
 *
 * @param {import("./tools/ado/get-work-item.js").WorkItem} item
 * @returns {string}
 */
const formatWorkItem = (item) => {
  return [
    `# Work Item #${item.id}: ${item.title}`,
    `**Type:** ${item.type} | **State:** ${item.state} | **Priority:** ${item.priority}`,
    `**Assigned:** ${item.assignedTo} | **Points:** ${item.storyPoints} | **Sprint:** ${item.iterationPath}`,
    `**URL:** ${item.url}`,
    ``,
    `## Description`,
    item.description,
    ``,
    `## Acceptance Criteria`,
    item.acceptanceCriteria,
    ...(item.reproductionSteps
      ? [``, `## Reproduction Steps`, item.reproductionSteps]
      : []),
    ...(item.comments?.length > 0
      ? [
          ``,
          `## Comments (${item.comments.length})`,
          ...item.comments.map(
            (c) => `**${c.author}:** ${c.text.replace(/<[^>]+>/g, "")}`
          ),
        ]
      : []),
    ...(item.relations?.length > 0
      ? [
          ``,
          `## Linked Items`,
          ...item.relations.map((r) => `- [${r.type}] ${r.title || r.url}`),
        ]
      : []),
  ].join("\n");
}

/**
 * Formats a list of work-item summaries as Markdown.
 *
 * @param {import("./tools/ado/list-work-items.js").WorkItemSummary[]} items
 * @returns {string}
 */
const formatWorkItemList = (items) => {
  if (!items.length) return "No work items found.";
  return [
    `# Work Items (${items.length})`,
    ...items.map(
      (i) =>
        `## #${i.id} — ${i.title}\n**${i.type}** | ${i.state} | ${i.assignedTo} | P${i.priority}`
    ),
  ].join("\n\n");
}

// ─────────────────────────────────────────────────────────────────────────────
// Startup
// ─────────────────────────────────────────────────────────────────────────────

async function main() {
  const startupMcpDocFiles = listMcpDocFiles();
  if (startupMcpDocFiles.length > 0) {
    process.stderr.write(
      `Loaded mcp_docs context (${startupMcpDocFiles.length} file(s)): ${startupMcpDocFiles.join(", ")}\n`
    );
  }
  if (MCP_TRANSPORT === "http") {
    /** @type {Map<string, { server: Server, transport: StreamableHTTPServerTransport }>} */
    const sessions = new Map();
    /** @type {Map<string, string>} */
    const clientSessionByIp = new Map();

    const httpServer = http.createServer(async (req, res) => {
      const requestStartedAt = Date.now();
      try {
        // Basic CORS support for remote MCP clients.
        res.setHeader("Access-Control-Allow-Origin", "*");
        res.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
        res.setHeader(
          "Access-Control-Allow-Headers",
          "Content-Type, Authorization, MCP-Session-Id"
        );

        if (req.method === "OPTIONS") {
          res.statusCode = 204;
          res.end();
          return;
        }

        const rawPath = String(req.url || "/").split("?")[0];
        const decodedPath = (() => {
          try {
            return decodeURIComponent(rawPath);
          } catch {
            return rawPath;
          }
        })();
        const normalizedPath =
          decodedPath
            .replace(/"+$/g, "")
            .replace(/\/+$/, "") || "/";
        const clientIp = String(req.socket?.remoteAddress || "");
        writeRuntimeLog("http.request.received", {
          method: req.method,
          path: rawPath,
          clientIp,
          hasSessionHeader: Boolean(req.headers["mcp-session-id"]),
        });

        // Accept both root and /mcp endpoints for compatibility with clients
        // that provide base URL without explicit /mcp suffix.
        const isMcpEndpoint = normalizedPath === "/mcp" || normalizedPath === "/";
        if (!isMcpEndpoint) {
          writeRuntimeLog("mcp.connection.failed", {
            reason: "invalid_endpoint_path",
            method: req.method,
            rawPath,
            normalizedPath,
            clientIp,
          });
          res.statusCode = 404;
          res.setHeader("Content-Type", "application/json");
          res.end(
            JSON.stringify({
              error: "Not Found",
              path: rawPath,
              expected: ["/", "/mcp"],
            })
          );
          return;
        }

        const sessionId = req.headers["mcp-session-id"];
        const normalizedSessionId =
          typeof sessionId === "string"
            ? sessionId
            : Array.isArray(sessionId)
              ? sessionId[0]
              : undefined;

        if (normalizedSessionId) {
          const existingSession = sessions.get(normalizedSessionId);
          if (!existingSession) {
            writeRuntimeLog("http.session.invalid", {
              sessionId: normalizedSessionId,
              clientIp,
            });
            writeRuntimeLog("mcp.connection.failed", {
              reason: "invalid_session_id",
              sessionId: normalizedSessionId,
              clientIp,
              method: req.method,
              path: rawPath,
            });
            res.statusCode = 404;
            res.setHeader("Content-Type", "application/json");
            res.end(
              JSON.stringify({
                jsonrpc: "2.0",
                error: {
                  code: -32000,
                  message: "Invalid session id",
                },
                id: null,
              })
            );
            return;
          }

          writeRuntimeLog("http.session.routed", {
            sessionId: normalizedSessionId,
            clientIp,
          });
          await existingSession.transport.handleRequest(req, res);
          writeRuntimeLog("http.request.completed", {
            method: req.method,
            path: rawPath,
            clientIp,
            durationMs: Date.now() - requestStartedAt,
          });
          return;
        }

        // New session flow: first request must be initialize (no session header yet).
        const parsedBody = await new Promise((resolve, reject) => {
          if (req.method !== "POST") {
            resolve(undefined);
            return;
          }
          let raw = "";
          req.on("data", (chunk) => {
            raw += chunk.toString();
          });
          req.on("end", () => {
            if (!raw.trim()) {
              resolve(undefined);
              return;
            }
            try {
              resolve(JSON.parse(raw));
            } catch (parseError) {
              reject(parseError);
            }
          });
          req.on("error", reject);
        });

        const method = parsedBody?.method;
        // Compatibility fallback: some clients/proxies may not forward mcp-session-id.
        // If we can confidently map by client IP, route request to that active session.
        if (method !== "initialize" && clientIp) {
          const fallbackSessionId = clientSessionByIp.get(clientIp);
          if (fallbackSessionId) {
            const fallbackSession = sessions.get(fallbackSessionId);
            if (fallbackSession) {
              writeRuntimeLog("http.session.fallback_by_ip", {
                clientIp,
                sessionId: fallbackSessionId,
                method,
              });
              await fallbackSession.transport.handleRequest(req, res, parsedBody);
              writeRuntimeLog("http.request.completed", {
                method: req.method,
                path: rawPath,
                clientIp,
                durationMs: Date.now() - requestStartedAt,
              });
              return;
            }
          }
        }

        if (method !== "initialize") {
          writeRuntimeLog("http.request.rejected_missing_session", {
            method,
            clientIp,
          });
          writeRuntimeLog("mcp.connection.failed", {
            reason: "missing_session_id",
            clientIp,
            method: req.method,
            path: rawPath,
          });
          res.statusCode = 400;
          res.setHeader("Content-Type", "application/json");
          res.end(
            JSON.stringify({
              jsonrpc: "2.0",
              error: {
                code: -32000,
                message: "Mcp-Session-Id header is required",
              },
              id: parsedBody?.id ?? null,
            })
          );
          return;
        }

        const server = createServerInstance();
        registerHandlers(server);
        const transport = new StreamableHTTPServerTransport({
          sessionIdGenerator: () => randomUUID(),
          enableJsonResponse: true,
        });
        transport.onerror = (transportError) => {
          writeRuntimeLog("mcp.transport.error", {
            clientIp,
            error: transportError?.message || String(transportError),
          });
        };
        transport.onclose = () => {
          writeRuntimeLog("mcp.transport.closed", {
            clientIp,
            sessionId: transport.sessionId,
          });
        };
        await server.connect(transport);
        await transport.handleRequest(req, res, parsedBody);

        const createdSessionId = transport.sessionId;
        if (createdSessionId) {
          sessions.set(createdSessionId, { server, transport });
          if (clientIp) clientSessionByIp.set(clientIp, createdSessionId);
          writeRuntimeLog("http.session.created", {
            sessionId: createdSessionId,
            clientIp,
          });
        }
        writeRuntimeLog("http.request.completed", {
          method: req.method,
          path: rawPath,
          clientIp,
          durationMs: Date.now() - requestStartedAt,
        });
      } catch (err) {
        process.stderr.write(
          `HTTP transport error: ${err?.message || String(err)}\n`
        );
        writeRuntimeLog("mcp.connection.failed", {
          reason: "http_transport_exception",
          error: err?.message || String(err),
        });
        writeRuntimeLog("http.request.error", {
          error: err?.message || String(err),
          durationMs: Date.now() - requestStartedAt,
        });
        if (!res.headersSent) {
          res.statusCode = 500;
          res.setHeader("Content-Type", "application/json");
          res.end(
            JSON.stringify({
              jsonrpc: "2.0",
              error: {
                code: -32000,
                message: err?.message || "Internal Server Error",
              },
              id: null,
            })
          );
        } else {
          res.end();
        }
      }
    });

    await new Promise((resolve, reject) => {
      httpServer.once("error", reject);
      httpServer.listen(Number(MCP_PORT), MCP_HOST, resolve);
    });

    process.stderr.write(
      `${MCP_SERVER_NAME} v${MCP_SERVER_VERSION} ready (${TOOLS.length} tools) on http://${MCP_HOST}:${MCP_PORT}/mcp\n`
    );
    if (MCP_PUBLIC_URL) {
      process.stderr.write(
        `Public MCP URL configured: ${MCP_PUBLIC_URL}\n` +
        `Connect command: codex mcp add codex_mcp_server --url "${MCP_PUBLIC_URL}"\n`
      );
    }
    return;
  }

  const server = createServerInstance();
  registerHandlers(server);
  const stdioTransport = new StdioServerTransport();
  await server.connect(stdioTransport);
  process.stderr.write(
    `${MCP_SERVER_NAME} v${MCP_SERVER_VERSION} ready (${TOOLS.length} tools) [stdio]\n`
  );
}

main().catch((err) => {
  process.stderr.write(`Fatal: ${err.message}\n`);
  process.exit(1);
});
