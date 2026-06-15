#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  McpError,
  ErrorCode
} from '@modelcontextprotocol/sdk/types.js';

// Builder: construye workflows n8n en memoria
class N8NWorkflowBuilder {
  private nodes: any[] = [];
  private connections: any[] = [];
  private nextPosition = { x: 100, y: 100 };

  addNode(nodeType: string, name: string, parameters: any) {
    this.nodes.push({
      type: nodeType,
      name: name,
      parameters: parameters,
      position: { ...this.nextPosition }
    });
    this.nextPosition.x += 200;
    return name;
  }

  connectNodes(source: string, target: string, sourceOutput = 0, targetInput = 0) {
    this.connections.push({
      source_node: source,
      target_node: target,
      source_output: sourceOutput,
      target_input: targetInput
    });
  }

  exportWorkflow() {
    const workflow = {
      nodes: this.nodes,
      connections: {
        main: this.connections.map(conn => ({
          node: conn.target_node,
          type: 'main',
          index: conn.target_input,
          sourceNode: conn.source_node,
          sourceIndex: conn.source_output
        }))
      }
    };
    return workflow;
  }
}

// Servidor MCP
class N8NWorkflowServer {
  private server: Server;

  constructor() {
    this.server = new Server(
      { name: 'n8n-workflow-builder', version: '0.1.0' },
      { capabilities: { tools: {} } }
    );
    this.setupToolHandlers();
    this.server.onerror = (error) => console.error('[MCP Error]', error);
  }

  private setupToolHandlers() {
    // Listar herramientas disponibles
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [{
        name: 'create_workflow',
        description: 'Create an n8n workflow from a specification of nodes and connections',
        inputSchema: {
          type: 'object',
          properties: {
            nodes: {
              type: 'array',
              items: {
                type: 'object',
                properties: {
                  type: { type: 'string', description: 'n8n node type (e.g., n8n-nodes-base.httpRequest)' },
                  name: { type: 'string', description: 'Display name for the node' },
                  parameters: { type: 'object', description: 'Node-specific parameters' }
                },
                required: ['type', 'name']
              },
              description: 'Array of nodes in the workflow'
            },
            connections: {
              type: 'array',
              items: {
                type: 'object',
                properties: {
                  source: { type: 'string', description: 'Source node name' },
                  target: { type: 'string', description: 'Target node name' }
                },
                required: ['source', 'target']
              },
              description: 'Array of connections between nodes'
            }
          },
          required: ['nodes', 'connections']
        }
      }]
    }));

    // Ejecutar herramientas
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      if (request.params.name !== 'create_workflow') {
        throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${request.params.name}`);
      }

      const args = request.params.arguments as any;
      if (!args?.nodes || !Array.isArray(args.nodes)) {
        throw new McpError(ErrorCode.InvalidParams, 'nodes array is required');
      }

      const builder = new N8NWorkflowBuilder();

      for (const node of args.nodes) {
        builder.addNode(node.type, node.name, node.parameters || {});
      }

      if (args.connections) {
        for (const conn of args.connections) {
          builder.connectNodes(conn.source, conn.target);
        }
      }

      const workflow = builder.exportWorkflow();
      return {
        content: [{ type: 'text', text: JSON.stringify(workflow, null, 2) }]
      };
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
  }
}

const server = new N8NWorkflowServer();
server.run().catch(console.error);
