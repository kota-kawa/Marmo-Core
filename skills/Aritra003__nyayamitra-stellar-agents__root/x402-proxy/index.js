require('dotenv').config({ path: require('path').resolve(__dirname, '../.env') });const express = require('express');
const axios = require('axios');
const cors = require('cors');

const app = express();
app.use(express.json());
app.use(cors());

const PORT = process.env.PROXY_PORT || 3000;
const NYAYAMITRA_URL = process.env.NYAYAMITRA_API_URL;
const NYAYAMITRA_KEY = process.env.NYAYAMITRA_API_KEY;
const RECIPIENT = process.env.RECIPIENT_WALLET;

const usedPaymentHashes = new Set();

function buildPaymentRequired(agentName, price, resourcePath) {
  return {
    x402Version: '1',
    accepts: [{
      scheme: 'exact',
      network: 'stellar-testnet',
      maxAmountRequired: String(price),
      resource: `http://localhost:3000${resourcePath}`,
      description: `NyayaMitra: ${agentName} — Indian legal intelligence`,
      mimeType: 'application/json',
      payTo: RECIPIENT,
      maxTimeoutSeconds: 60,
      asset: 'USDC',
      extra: {
        agent: agentName.toLowerCase(),
        provider: 'NyayaMitra AI / ATNIA Solutions',
      }
    }]
  };
}

async function verifyPayment(xPaymentHeader, requiredAmount) {
  try {
    const decoded = Buffer.from(xPaymentHeader, 'base64').toString('utf8');
    const paymentProof = JSON.parse(decoded);
    const txHash = paymentProof.transactionHash || paymentProof.hash;
    if (!txHash) return { valid: false, error: 'No transaction hash' };
    if (usedPaymentHashes.has(txHash)) return { valid: false, error: 'Payment already used' };
    usedPaymentHashes.add(txHash);
    console.log(`✅ Payment accepted: ${txHash}`);
    return { valid: true, payer: paymentProof.payer || 'agent', amount: requiredAmount, txHash };
  } catch (err) {
    return { valid: false, error: err.message };
  }
}

function x402Guard(agentName, price, resourcePath) {
  return async (req, res, next) => {
    const paymentHeader = req.headers['x-payment'];
    if (!paymentHeader) {
      console.log(`🔒 402 fired for ${agentName}`);
      return res.status(402).json(buildPaymentRequired(agentName, price, resourcePath));
    }
    const verification = await verifyPayment(paymentHeader, price);
    if (!verification.valid) {
      return res.status(402).json({
        error: 'Payment verification failed',
        reason: verification.error,
        ...buildPaymentRequired(agentName, price, resourcePath)
      });
    }
    req.paymentInfo = verification;
    next();
  };
}

async function proxyToNyayaMitra(endpoint, body, res, req) {
  try {
    console.log(`🔄 Proxying to NyayaMitra: ${endpoint}`);
    console.log('Calling URL:', `${NYAYAMITRA_URL}${endpoint}`);
    const response = await axios.post(
      `${NYAYAMITRA_URL}${endpoint}`,
      body,
      {
        headers: {
          'Authorization': `Bearer ${NYAYAMITRA_KEY}`,
          'Content-Type': 'application/json',
        },
        timeout: 55000,
      }
    );
    console.log(`✅ NyayaMitra responded for ${endpoint}`);
    return res.json({
      ...response.data,
      _x402: {
        paid: true,
        amount: req.paymentInfo?.amount,
        txHash: req.paymentInfo?.txHash,
        provider: 'NyayaMitra AI / ATNIA Solutions',
      }
    });
  } catch (err) {
    console.error(`Proxy error for ${endpoint}:`, err.message);
    if (err.code === 'ECONNREFUSED') {
      return res.status(503).json({ error: 'NyayaMitra API unreachable' });
    }
    return res.status(500).json({
      error: 'NyayaMitra API error',
      detail: err.response?.data || err.message
    });
  }
}

app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    service: 'NyayaMitra x402 Proxy',
    network: 'stellar-testnet',
    agents: ['vidhi', 'kosh', 'sahayak'],
    recipient: RECIPIENT,
  });
});

app.post(
  '/x402/v1/agents/vidhi/research',
  x402Guard('Vidhi', parseFloat(process.env.PRICE_VIDHI || '0.05'), '/x402/v1/agents/vidhi/research'),
  async (req, res) => {
    const { query, jurisdiction, court_level, output_format } = req.body;
    if (!query || !jurisdiction) {
      return res.status(400).json({ error: 'query and jurisdiction are required' });
    }
    await proxyToNyayaMitra('/api/v1/research/query', {
      query, jurisdiction, court_level, output_format
    }, res, req);
  }
);

app.post(
  '/x402/v1/agents/kosh/precedent',
  x402Guard('Kosh', parseFloat(process.env.PRICE_KOSH || '0.05'), '/x402/v1/agents/kosh/precedent'),
  async (req, res) => {
    const { legal_question, jurisdiction, section, date_range } = req.body;
    if (!legal_question || !jurisdiction) {
      return res.status(400).json({ error: 'legal_question and jurisdiction are required' });
    }
    await proxyToNyayaMitra('/api/v1/citations/verify', {
  legal_question, jurisdiction, section, date_range
}, res, req);
  }
);

app.post(
  '/x402/v1/agents/sahayak/qa',
  x402Guard('Sahayak', parseFloat(process.env.PRICE_SAHAYAK || '0.01'), '/x402/v1/agents/sahayak/qa'),
  async (req, res) => {
    const { question, jurisdiction, context } = req.body;
    if (!question) {
      return res.status(400).json({ error: 'question is required' });
    }
    await proxyToNyayaMitra('/api/v1/research/query', {
  query: question, jurisdiction: jurisdiction || 'IN', context
}, res, req);
  }
);

app.listen(PORT, () => {
  console.log(`\n🚀 NyayaMitra x402 Proxy running on port ${PORT}`);
  console.log(`   NyayaMitra API: ${NYAYAMITRA_URL}`);
  console.log(`   Recipient: ${RECIPIENT}`);
  console.log(`\n📡 Routes:`);
  console.log(`   POST /x402/v1/agents/vidhi/research   → 0.05 USDC`);
  console.log(`   POST /x402/v1/agents/kosh/precedent   → 0.05 USDC`);
  console.log(`   POST /x402/v1/agents/sahayak/qa       → 0.01 USDC`);
  console.log(`   GET  /health`);
});