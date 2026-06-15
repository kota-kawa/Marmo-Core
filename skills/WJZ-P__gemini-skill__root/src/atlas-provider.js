import config from './config.js';

function resolveApiKey(explicitApiKey) {
  const apiKey = explicitApiKey || config.atlasApiKey;
  if (!apiKey) {
    throw new Error('缺少 ATLAS_API_KEY，请在环境变量、.env 或 .env.development 中配置');
  }
  return apiKey;
}

function joinUrl(baseUrl, path) {
  return `${baseUrl.replace(/\/+$/, '')}${path}`;
}

async function parseJsonSafely(response) {
  const raw = await response.text();
  try {
    return { raw, data: JSON.parse(raw) };
  } catch {
    return { raw, data: null };
  }
}

async function atlasRequest(path, { apiKey, method = 'GET', body, timeoutMs } = {}) {
  const finalApiKey = resolveApiKey(apiKey);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs ?? config.atlasRequestTimeoutMs);

  try {
    const response = await fetch(joinUrl(config.atlasBaseUrl, path), {
      method,
      headers: {
        Authorization: `Bearer ${finalApiKey}`,
        'Content-Type': 'application/json',
      },
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });

    const { raw, data } = await parseJsonSafely(response);
    if (!response.ok) {
      const message = data?.error?.message || data?.msg || raw || `HTTP ${response.status}`;
      throw new Error(`Atlas API 请求失败: ${response.status} ${message}`);
    }
    if (!data) {
      throw new Error(`Atlas API 返回了非 JSON 响应: ${raw}`);
    }
    return data;
  } finally {
    clearTimeout(timer);
  }
}

async function* parseSseStream(stream) {
  const decoder = new TextDecoder();
  let buffer = '';

  for await (const chunk of stream) {
    buffer += decoder.decode(chunk, { stream: true });

    while (buffer.includes('\n\n')) {
      const separatorIndex = buffer.indexOf('\n\n');
      const eventBlock = buffer.slice(0, separatorIndex);
      buffer = buffer.slice(separatorIndex + 2);

      const dataLines = eventBlock
        .split('\n')
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice(5).trim());

      if (dataLines.length === 0) continue;
      const payload = dataLines.join('\n');
      if (payload === '[DONE]') return;

      try {
        yield JSON.parse(payload);
      } catch {
        // 忽略非 JSON 的 data 帧，保持流式消费健壮性
      }
    }
  }

  const tail = buffer.trim();
  if (tail.startsWith('data:')) {
    const payload = tail.slice(5).trim();
    if (payload && payload !== '[DONE]') {
      yield JSON.parse(payload);
    }
  }
}

export function createAtlasProvider(options = {}) {
  const defaultApiKey = options.apiKey;

  return {
    async listModels({ apiKey, timeoutMs } = {}) {
      return atlasRequest('/models', {
        apiKey: apiKey || defaultApiKey,
        timeoutMs,
      });
    },

    async createChatCompletion(payload, { apiKey, timeoutMs } = {}) {
      return atlasRequest('/chat/completions', {
        apiKey: apiKey || defaultApiKey,
        method: 'POST',
        body: payload,
        timeoutMs,
      });
    },

    async createChatCompletionStream(payload, { apiKey, timeoutMs, onDelta } = {}) {
      const finalApiKey = resolveApiKey(apiKey || defaultApiKey);
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs ?? config.atlasRequestTimeoutMs);

      try {
        const response = await fetch(joinUrl(config.atlasBaseUrl, '/chat/completions'), {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${finalApiKey}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ ...payload, stream: true }),
          signal: controller.signal,
        });

        if (!response.ok || !response.body) {
          const { raw, data } = await parseJsonSafely(response);
          const message = data?.error?.message || data?.msg || raw || `HTTP ${response.status}`;
          throw new Error(`Atlas API 流式请求失败: ${response.status} ${message}`);
        }

        const chunks = [];
        let text = '';
        let finalChunk = null;

        for await (const chunk of parseSseStream(response.body)) {
          finalChunk = chunk;
          chunks.push(chunk);
          const delta = chunk?.choices?.[0]?.delta?.content ?? '';
          if (delta) {
            text += delta;
            onDelta?.(delta, chunk);
          }
        }

        return {
          text,
          chunks,
          finalChunk,
        };
      } finally {
        clearTimeout(timer);
      }
    },
  };
}

