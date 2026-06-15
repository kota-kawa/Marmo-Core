---
name: delphi-terminal
description: Query unified prediction market data (Kalshi, Polymarket, Limitless, Predict.fun, Gemini, Manifold, Opinion, ForecastEx, PredictIt) and parlay RFQs/trades via the Delphi Terminal API.
triggers:
  - prediction market
  - Kalshi / KLSI
  - Polymarket / POLY
  - Limitless, Predict.fun, Gemini, Manifold, Opinion, ForecastEx, PredictIt
  - market odds, prices, orderbook, trade history, OHLCV candles
  - RFQ, MVE trades, parlays
---

# Delphi Terminal API — Agent Skill

You are about to query the Delphi Terminal API, a single interface for prediction market data across nine exchanges and a parlays/RFQ feed. This file is the authoritative guide. Follow it literally.

## When to use this skill

Use this skill whenever the user asks about:

- Prediction market odds, prices, volume, liquidity, spreads
- Orderbooks, top-of-book, raw orderbook deltas
- Trade history or OHLCV candles
- Market search, semantic search, categories, events, clusters
- Parlay RFQs, MVE trades
- Bulk historical data exports (parquet)
- Real-time streaming via WebSockets

If the user names any of these exchanges or asks for "live odds," default to this skill:
**Kalshi, Polymarket, Limitless, Predict.fun, Gemini, Manifold, Opinion, ForecastEx, PredictIt.**

## Base URLs

| Purpose | URL |
| ------- | --- |
| REST API | `https://api.delphiterminal.co` |
| WebSockets | `wss://api.delphiterminal.co` |
| Docs (this skill lives here) | `https://docs.delphimarkets.com` |

## Authentication — do this first

Every REST request needs `X-API-Key: <key>` in the headers. WebSockets require the key as an `api_key` query param.

### Bootstrap flow (when the user has no key)

1. Generate a free test key (10-minute TTL, 60 req/min, no auth required):

   ```bash
   curl -X POST https://api.delphiterminal.co/api/v1/test-key
   ```

   Response:

   ```json
   { "api_key": "dphi_live_a1b2c3d4...", "expires_at": "...", "expires_in": "10 minutes" }
   ```

2. Save `api_key` and pass it on every subsequent call.
3. For production usage, direct the user to `https://delphimarkets.com` to request a permanent key (300 req/min).

### Rate limits and errors

| Key type | Limit |
| -------- | ----- |
| Test | 60 req/min |
| Production | 300 req/min |

| Code | Meaning |
| ---- | ------- |
| 400 | Bad Request — invalid parameters |
| 401 | Unauthorized — missing or invalid API key |
| 404 | Not Found — resource doesn't exist |
| 429 | Too Many Requests — back off and retry |
| 500 | Server error — retry with jitter |

Errors return `{"error": "..."}`.

## Exchanges and identifiers

| Exchange | Prefix in path | ID field | ID format example |
| -------- | -------------- | -------- | ----------------- |
| Kalshi | `/klsi/` | `klsi_id` | `KXBTCD-25FEB14-B55000` |
| Polymarket | `/poly/` | `poly_id` / `condition_id` | `0xb09a659b55f0eab385d75ef14d180e9a6b...` |
| Limitless | `/limitless/` | `market_id` | opaque string |
| Predict.fun | `/pfun/` | `market_id` | opaque string |
| Gemini | `/gemini/` | `market_id` | `GEMI-BTC15M-HI70000` |
| Manifold | `/manifold/` | `market_id` | slug like `Iz0lRpO85N` |
| Opinion | `/opinion/` | `market_id` | numeric string like `10702` |
| ForecastEx | `/fex/` | `market_id` | `EMCAC_1226_24` (no orderbook) |
| PredictIt | `/predictit/` | `market_id` | numeric string like `34256` (prices only) |

Delphi also has a unified `delphi_id` that clusters equivalent markets across exchanges — useful for cross-venue comparisons.

## REST endpoint cheat-sheet

All paths are relative to `https://api.delphiterminal.co`. Send `X-API-Key` on every call except where noted.

### Auth and keys

| Method | Path | Purpose |
| ------ | ---- | ------- |
| POST | `/api/v1/test-key` | Free 10-min test key (no auth) |
| POST | `/api/v1/auth/signup` | Create user account |
| POST | `/api/v1/auth/login` | Get session token |
| GET | `/api/v1/auth/me` | Current user info |
| POST | `/api/v1/auth/logout` | Invalidate session |

### Cross-exchange search and discovery

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/api/v1/events/search?q=<text>` | Free-text event search |
| GET | `/api/v1/search/suggest?q=<text>` | Typeahead suggestions |
| GET | `/api/v1/search/markets?q=<text>` | Keyword market search |
| GET | `/api/v1/search/semantic?q=<text>` | Vector/semantic market search |
| GET | `/api/v1/events/{event_id}` | Event details |
| GET | `/api/v1/events/category/{category}` | Events in a category |
| GET | `/api/v1/events/category/{category}/klsi` | Kalshi events in a category |
| GET | `/api/v1/events/category/{category}/poly` | Polymarket events in a category |
| GET | `/api/v1/markets/{market_id}/orderbook_analytics` | Unified orderbook analytics |
| GET | `/api/v1/markets/{market_id}/orderbook_analytics/best_quotes` | Unified best quotes |

### Delphi clustering (cross-exchange equivalence)

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/api/v1/delphi/{delphi_id}/cluster` | Get a cluster by delphi ID |
| GET | `/api/v1/delphi/{delphi_id}/markets` | All markets in a delphi cluster |
| GET | `/api/v1/clusters/{cluster_id}` | Cluster detail |
| GET | `/api/v1/klsi/{klsi_id}/cluster` | Cluster for a Kalshi market |
| GET | `/api/v1/poly/{poly_id}/cluster` | Cluster for a Polymarket market |
| GET | `/api/v1/limitless/{market_id}/cluster` | Cluster for a Limitless market |
| GET | `/api/v1/pfun/{market_id}/cluster` | Cluster for a Predict.fun market |

### Kalshi (KLSI)

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/api/v1/klsi/markets` | List markets (paginated) |
| GET | `/api/v1/klsi/markets/categories` | All categories |
| GET | `/api/v1/klsi/markets/category/{category}` | Markets by category |
| GET | `/api/v1/klsi/{klsi_id}/market` | Market detail |
| GET | `/api/v1/klsi/{klsi_id}/rules` | Market rules |
| GET | `/api/v1/klsi/{klsi_id}/prices` | Price history |
| GET | `/api/v1/klsi/{klsi_id}/candles` | OHLCV candles |
| GET | `/api/v1/klsi/{klsi_id}/top_of_book` | Best bid/ask |
| GET | `/api/v1/klsi/{klsi_id}/orderbook` | Full orderbook (up to 101 levels) |
| GET | `/api/v1/klsi/{klsi_id}/raw_deltas` | Raw orderbook deltas |
| GET | `/api/v1/klsi/{klsi_id}/tradehistory` | Trade history |
| GET | `/api/v1/klsi/{klsi_id}/orderbook_analytics` | Orderbook analytics |
| GET | `/api/v1/klsi/{klsi_id}/orderbook_analytics/best_quotes` | Best quotes analytics |
| GET | `/api/v1/klsi/event/{event_id}` | Kalshi event detail |
| GET | `/api/v1/klsi/event/{event_id}/markets` | Markets under a Kalshi event |

### Polymarket (POLY)

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/api/v1/poly/markets` | List markets |
| GET | `/api/v1/poly/markets/categories` | All categories |
| GET | `/api/v1/poly/markets/category/{category}` | Markets by category |
| GET | `/api/v1/poly/{poly_id}/market` | Market detail |
| GET | `/api/v1/poly/{poly_id}/rules` | Market rules |
| GET | `/api/v1/poly/{poly_id}/prices` | Price history |
| GET | `/api/v1/poly/{poly_id}/top_of_book` | Best bid/ask |
| GET | `/api/v1/poly/{poly_id}/orderbook` | Full orderbook |
| GET | `/api/v1/poly/{poly_id}/raw_deltas` | Raw orderbook deltas |
| GET | `/api/v1/poly/{poly_id}/tradehistory` | Trade history |
| GET | `/api/v1/poly/{poly_id}/event` | Event for a Polymarket market |
| GET | `/api/v1/poly/event/{event_id}/markets` | Markets under a Polymarket event |

### Limitless

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/api/v1/limitless/markets` | List markets |
| GET | `/api/v1/limitless/{market_id}/market` | Market detail |
| GET | `/api/v1/limitless/{market_id}/top_of_book` | Best bid/ask |
| GET | `/api/v1/limitless/{market_id}/orderbook` | Full orderbook |
| GET | `/api/v1/limitless/{market_id}/tradehistory` | Trade history |
| GET | `/api/v1/limitless/{market_id}/exchange_prices` | Raw exchange prices |

### Predict.fun (PFUN)

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/api/v1/pfun/markets` | List markets |
| GET | `/api/v1/pfun/{market_id}/market` | Market detail |
| GET | `/api/v1/pfun/{market_id}/top_of_book` | Best bid/ask |
| GET | `/api/v1/pfun/{market_id}/orderbook` | Full orderbook |
| GET | `/api/v1/pfun/{market_id}/tradehistory` | Trade history |
| GET | `/api/v1/pfun/{market_id}/exchange_prices` | Raw exchange prices |

### Gemini, Manifold, Opinion, ForecastEx, PredictIt

Same shape as above. Substitute the prefix:

| Exchange | List | Detail | Orderbook | Prices | Trades |
| -------- | ---- | ------ | --------- | ------ | ------ |
| Gemini | `/api/v1/gemini/markets` | `/api/v1/gemini/{market_id}/market` | `/api/v1/gemini/{market_id}/orderbook` | `/api/v1/gemini/{market_id}/prices` | `/api/v1/gemini/{market_id}/tradehistory` |
| Manifold | `/api/v1/manifold/markets` | `/api/v1/manifold/{market_id}/market` | `/api/v1/manifold/{market_id}/orderbook` | `/api/v1/manifold/{market_id}/prices` | `/api/v1/manifold/{market_id}/tradehistory` |
| Opinion | `/api/v1/opinion/markets` | `/api/v1/opinion/{market_id}/market` | `/api/v1/opinion/{market_id}/orderbook` | `/api/v1/opinion/{market_id}/prices` | `/api/v1/opinion/{market_id}/tradehistory` |
| ForecastEx | `/api/v1/fex/markets` | `/api/v1/fex/{market_id}/market` | — (no orderbook) | — | `/api/v1/fex/{market_id}/tradehistory` |
| PredictIt | `/api/v1/predictit/markets` | `/api/v1/predictit/{market_id}/market` | — (no orderbook) | `/api/v1/predictit/{market_id}/prices` | — |

### Parlays and RFQs (Pro+ plan)

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/api/v1/klsi/{klsi_id}/rfq` | RFQs for a Kalshi market |
| GET | `/api/v1/klsi/{klsi_id}/mve_trades` | MVE trades for a Kalshi market |
| GET | `/api/v1/klsi/rfq/{rfq_id}` | Single RFQ by ID |
| GET | `/api/v1/klsi/rfq/date/{date}` | RFQs for a date (`YYYY-MM-DD`) |

### Bulk data export (parquet)

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/api/v1/data/{dataset}?date=YYYY-MM-DD` | Presigned parquet download URLs for a date |
| GET | `/api/v1/data/{dataset}/latest` | Today's parquet export |

Supported datasets: `rfqs`, `mve_trades`.

## WebSockets — unified pattern

Every exchange uses the same subscribe/unsubscribe contract; only the endpoint, ID field, and available message types change.

### Connect

```javascript
const ws = new WebSocket(
  "wss://api.delphiterminal.co/ws/<exchange>?api_key=YOUR_API_KEY"
);
```

Connection properties: ping every 54s, 60s pong timeout, 512KB max message.

### Subscribe

```json
{
  "action": "subscribe",
  "<ID_FIELD>": ["<market_id>", "..."],
  "message_types": ["prices", "orderbook", "trades"]
}
```

`message_types` defaults to `["prices", "orderbook"]` if omitted. `action: "unsubscribe"` removes subscriptions.

### Per-exchange reference

| Exchange | Endpoint | ID field | Available message_types |
| -------- | -------- | -------- | ----------------------- |
| Kalshi | `/ws/kalshi` | `klsi_ids` | prices, orderbook, trades |
| Polymarket | `/ws/poly` | `condition_ids` | prices, orderbook, trades |
| Predict.fun | `/ws/pfun` | `market_ids` | prices, orderbook, trades |
| Limitless | `/ws/limitless` | `market_ids` | prices, orderbook, trades |
| Gemini | `/ws/gemi` | `market_ids` | prices, orderbook, trades |
| Manifold | `/ws/mani` | `market_ids` | prices, orderbook, trades |
| Opinion | `/ws/opnm` | `market_ids` | prices, orderbook, trades |
| ForecastEx | `/ws/fex` | `market_ids` | prices, trades (no orderbook) |
| PredictIt | `/ws/prdi` | `market_ids` | prices only |
| Parlays | `/ws/parlays` | `market_ids` | rfq, mve_trades (Pro+ plan) |

## Worked examples

### 1. Semantic search across all exchanges

```bash
curl -s -H "X-API-Key: $API_KEY" \
  "https://api.delphiterminal.co/api/v1/search/semantic?q=will%20bitcoin%20hit%20100k%20this%20year" | jq
```

### 2. Pull Kalshi orderbook

```bash
curl -s -H "X-API-Key: $API_KEY" \
  "https://api.delphiterminal.co/api/v1/klsi/KXBTCD-25FEB14-B55000/orderbook" | jq
```

### 3. Pull Polymarket trade history

```bash
curl -s -H "X-API-Key: $API_KEY" \
  "https://api.delphiterminal.co/api/v1/poly/0xb09a659b55f0eab385d75ef14d180e9a6b2f02290a427504e38bf803e35d25d6/tradehistory?limit=50" | jq
```

### 4. Stream Kalshi prices + orderbook

```javascript
const ws = new WebSocket(
  "wss://api.delphiterminal.co/ws/kalshi?api_key=" + process.env.API_KEY
);

ws.onopen = () => {
  ws.send(JSON.stringify({
    action: "subscribe",
    klsi_ids: ["KXBTCD-25FEB14-B55000"],
    message_types: ["prices", "orderbook", "trades"],
  }));
};

ws.onmessage = (event) => console.log(JSON.parse(event.data));
```

### 5. Download a parquet export

```bash
curl -s -H "X-API-Key: $API_KEY" \
  "https://api.delphiterminal.co/api/v1/data/rfqs?date=2026-02-13" > export.json
URL=$(jq -r '.parts[0].url' export.json)
curl -L "$URL" -o rfqs_2026-02-13.parquet
duckdb -c "SELECT * FROM read_parquet('rfqs_2026-02-13.parquet') LIMIT 20;"
```

Presigned URLs expire in ~5 minutes. Re-request metadata if the download fails.

## Operating guidelines for the agent

- **Prefer search first.** When the user names a topic, call `/api/v1/search/semantic` or `/api/v1/events/search` before guessing market IDs.
- **Use clusters for cross-venue answers.** If the user asks "which exchange has the best price for X," fetch `/api/v1/delphi/{delphi_id}/markets` or the per-exchange `/cluster` endpoints and compare `top_of_book`.
- **Paginate.** All list endpoints accept `limit` and `offset` (or cursor). Default `limit=50`.
- **Stream, don't poll.** If the user wants live updates, use the WebSocket for that exchange.
- **Handle 429s with exponential backoff.** Never hammer on retry.
- **Never hardcode IDs.** Look them up dynamically from search or the `markets` list.
- **Surface the API key source.** If you minted a test key, tell the user it expires in 10 minutes and point them to `https://delphimarkets.com` for a production key.

## When the cheat-sheet isn't enough

Fetch these on demand for full schemas and edge cases:

- Full REST spec: `https://docs.delphimarkets.com/openapi.json`
- Parlays spec: `https://docs.delphimarkets.com/openapi-parlays.json`
- WebSocket spec: `https://docs.delphimarkets.com/openapi-websockets.json`
- Full flat docs dump: `https://docs.delphimarkets.com/llms-full.txt`
- Per-exchange WebSocket pages:
  - `https://docs.delphimarkets.com/ws-kalshi.md`
  - `https://docs.delphimarkets.com/ws-polymarket.md`
  - `https://docs.delphimarkets.com/ws-pfun.md`
  - `https://docs.delphimarkets.com/ws-limitless.md`
  - `https://docs.delphimarkets.com/ws-gemi.md`
  - `https://docs.delphimarkets.com/ws-mani.md`
  - `https://docs.delphimarkets.com/ws-opnm.md`
  - `https://docs.delphimarkets.com/ws-fex.md`
  - `https://docs.delphimarkets.com/ws-prdi.md`
  - `https://docs.delphimarkets.com/ws-parlays.md`
- Topical pages: `/introduction.md`, `/quickstart.md`, `/authentication.md`, `/data-extraction.md`, `/klsi-examples.md`, `/polymarket-examples.md`, `/websocket-examples.md`, `/changelog.md`.
