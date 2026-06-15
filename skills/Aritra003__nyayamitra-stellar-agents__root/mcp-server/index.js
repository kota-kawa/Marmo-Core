
const { Server } = require('@modelcontextprotocol/sdk/server/index.js');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');
const { CallToolRequestSchema, ListToolsRequestSchema } = require('@modelcontextprotocol/sdk/types.js');
const axios = require('axios');

const PROXY_URL = process.env.X402_PROXY_URL || 'http://localhost:3000';

const TOOLS = [
  {
    name: 'legal_research',
    description: 'Query NyayaMitra Vidhi agent for Indian legal research. 30+ jurisdictions. Costs 0.05 USDC via Stellar x402.',
    inputSchema: {
      type: 'object',
      required: ['query', 'jurisdiction'],
      properties: {
        query: { type: 'string', description: 'Legal research question' },
        jurisdiction: { type: 'string', description: 'Jurisdiction code: IN, IN-DL, IN-MH, IN-KA, SG, AE-DIFC' },
        court_level: { type: 'string', enum: ['supreme', 'high', 'sessions', 'district'] },
        output_format: { type: 'string', enum: ['summary', 'detailed', 'citations_only'] }
      }
    }
  },
  {
    name: 'precedent_lookup',
    description: 'Query NyayaMitra Kosh agent for verified case precedents. Hallucination prevention built in. Costs 0.05 USDC via Stellar x402.',
    inputSchema: {
      type: 'object',
      required: ['legal_question', 'jurisdiction'],
      properties: {
        legal_question: { type: 'string', description: 'Legal question for precedent research' },
        jurisdiction: { type: 'string', description: 'Jurisdiction code: IN, IN-DL, IN-MH, SG, AE-DIFC' },
        section: { type: 'string', description: 'Optional statute section e.g. Section 138 NI Act' },
        date_range: { type: 'object', properties: { from: { type: 'string' }, to: { type: 'string' } } }
      }
    }
  },
  {
    name: 'legal_qa',
    description: 'Query NyayaMitra Sahayak agent for plain-language legal Q&A. Ideal for due diligence chains. Costs 0.01 USDC via Stellar x402.',
    inputSchema: {
      type: 'object',
      required: ['question'],
      properties: {
        question: { type: 'string', description: 'Legal question in plain language' },
        jurisdiction: { type: 'string', description: 'Jurisdiction code. Defaults to IN.' },
        context: { type: 'string', description: 'Optional contract clause for contextual analysis' }
      }
    }
  }
];

async function callWithPayment(endpoint, body) {
  try {
    const response = await axios.post(`${PROXY_URL}${endpoint}`, body, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 60000,
    });
    return response.data;
  } catch (err) {
    if (err.response?.status !== 402) {
      throw new Error(`Proxy error: ${err.response?.data?.error || err.message}`);
    }
    const paymentInstructions = err.response.data;
    const accepts = paymentInstructions.accepts?.[0];
    console.error(`[MCP] 402 received — need ${accepts?.maxAmountRequired} ${accepts?.asset} on ${accepts?.network}`);
    const mockProof = Buffer.from(JSON.stringify({
      transactionHash: `demo_${Date.now()}`,
      network: accepts?.network,
      amount: accepts?.maxAmountRequired,
      asset: accepts?.asset,
      payTo: accepts?.payTo,
    })).toString('base64');
    const retryResponse = await axios.post(`${PROXY_URL}${endpoint}`, body, {
      headers: {
        'Content-Type': 'application/json',
        'X-Payment': mockProof,
      },
      timeout: 60000,
    });
    return retryResponse.data;
  }
}

const server = new Server(
  { name: 'nyayamitra-legal-intelligence', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools: TOOLS };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  console.error(`[MCP] Tool called: ${name}`);

  try {
    let result;
    if (name === 'legal_research') {
      result = await callWithPayment('/x402/v1/agents/vidhi/research', {
        query: args.query,
        jurisdiction: args.jurisdiction,
        court_level: args.court_level,
        output_format: args.output_format || 'summary',
      });
    } else if (name === 'precedent_lookup') {
      result = await callWithPayment('/x402/v1/agents/kosh/precedent', {
        legal_question: args.legal_question,
        jurisdiction: args.jurisdiction,
        section: args.section,
        date_range: args.date_range,
      });
    } else if (name === 'legal_qa') {
      result = await callWithPayment('/x402/v1/agents/sahayak/qa', {
        question: args.question,
        jurisdiction: args.jurisdiction || 'IN',
        context: args.context,
      });
    } else {
      throw new Error(`Unknown tool: ${name}`);
    }

    return {
      content: [{
        type: 'text',
        text: typeof result === 'string' ? result : JSON.stringify(result, null, 2)
      }]
    };
  } catch (err) {
    console.error(`[MCP] Error:`, err.message);
    return {
      content: [{ type: 'text', text: `Error: ${err.message}` }],
      isError: true,
    };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('[MCP] NyayaMitra MCP server running');
  console.error(`[MCP] Proxy: ${PROXY_URL}`);
}

main().catch(err => {
  console.error('[MCP] Fatal:', err);
  process.exit(1);
});