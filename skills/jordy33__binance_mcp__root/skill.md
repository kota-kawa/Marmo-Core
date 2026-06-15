# Crypto Trading Agent Skills

## 🤖 System Integration
This agent is the authorized operator of a **Model Context Protocol (MCP) Server**. 

### Connection Details:
- **Transport:** SSE (Server-Sent Events)
- **Endpoint:** `http://localhost:8080/sse`
- **Host:** `127.0.0.1` (Local access only for security)

All tools described below are provided by this server and are directly accessible within the agent's context. The agent should invoke these tools autonomously to fulfill trading objectives, analyze markets, and manage the portfolio.

---

## 🛠 Available Tools

### 1. `get_account_balance`
**Purpose:** Check the available funds in the portfolio.
- **Parameters:**
  - `asset` (str, default="USDT"): The ticker symbol of the asset (e.g., "BTC", "ETH", "USDT").
- **Usage Example:** `get_account_balance(asset="BTC")`
- **Returns:** A string detailing "Free" (available for trade), "Locked" (in open orders), and "Total" balance.

### 2. `get_market_price`
**Purpose:** specific market price lookup.
- **Parameters:**
  - `symbol` (str): The trading pair symbol (e.g., "BTCUSDT").
- **Usage Example:** `get_market_price(symbol="BTCUSDT")`
- **Returns:** The current price as a string.

### 3. `fetch_chart_data`
**Purpose:** Fetch historical OHLCV data for technical analysis or backtesting strategies before execution.
- **Parameters:**
  - `symbol` (str): The trading pair (e.g., "BTCUSDT").
  - `interval` (str, default="1h"): Candle time frame (e.g., "15m", "1h", "4h", "1d").
  - `limit` (int, default=100): Number of candles to retrieve (max 500 recommended).
- **Usage Example:** `fetch_chart_data(symbol="BTCUSDT", interval="4h", limit=50)`
- **Returns:** A list of dictionaries containing timestamp, open, high, low, close, and volume.

### 4. `calculate_indicators`
**Purpose:** Fetch market data and compute key technical indicators (RSI, MACD, Bollinger Bands, SMA/EMA) to identify market conditions (Trending vs Ranging).
- **Parameters:**
  - `symbol` (str): The trading pair (e.g., "BTCUSDT").
  - `interval` (str, default="1h"): Candle time frame.
  - `limit` (int, default=100): Data points for calculation.
- **Returns:** JSON string with:
  - `indicators`: Latest values for RSI, MACD, BB, etc.
  - `market_state_heuristic`: "Likely Ranging", "Likely Trending", etc.
- **Strategic Use:** Use this to select the appropriate strategy (e.g., Mean Reversion for Ranging, Trend Following for Trending).

### 5. `get_symbol_rules`
**Purpose:** Retrieve trading rules for a symbol (Exchange Info).
- **Parameters:**
  - `symbol` (str): The trading pair (e.g., "BTCUSDT").
- **Usage Example:** `get_symbol_rules(symbol="BTCUSDT")`
- **Returns:** A JSON-like string with:
  - `lot_size` (minQty, maxQty, stepSize) -> Essential for quantity precision.
  - `min_notional` -> Minimum order value in quote asset (USDT).
  - `price_filter` -> Tick size for price precision.

### 5. `adjust_leverage`
**Purpose:** Change the leverage for a specific trading pair. **Requires Futures Account**.
- **Primary Use Case:** Acts as a "litmus test" to verify API connectivity and permissions without placing a real order (as suggested by trading bot best practices).
- **Parameters:**
  - `symbol` (str): The trading pair (e.g., "BTCUSDT").
  - `leverage` (int): The target leverage multiplier (e.g., 5, 10, 20).
- **Usage Example:** `adjust_leverage(symbol="BTCUSDT", leverage=7)`
- **Returns:** Success message or error details.

### 5. `place_order`
**Purpose:** Execute a trade (buy or sell) at market price.
- **Parameters:**
  - `symbol` (str): The trading pair (e.g., "BTCUSDT").
  - `side` (str): The direction of the trade ("BUY" or "SELL").
  - `quantity` (float): The amount of the **base asset** to buy or sell.
- **Usage Example:** `place_order(symbol="BTCUSDT", side="BUY", quantity=0.001)`
- **Precision Handling:** The system automatically validates and formats the quantity to match the exchange's `LOT_SIZE` (step size) requirements. You do not need to calculate the exact precision manually, but try to be reasonably accurate.
- **Critical Validation:** 
  - Ensure sufficient `USDT` balance before buying.
  - Ensure sufficient `BTC` balance before selling.
  - The order value (Price * Quantity) must meet Binance's minimum order value (typically ~5-10 USDT).

### 5. `get_base_network_status`
**Purpose:** Monitor the health of the Base L2 blockchain.
- **Parameters:** None
- **Usage Example:** `get_base_network_status()`
- **Returns:** Latest block number and current gas price (in wei).

### 6. `read_bot_logs`
**Purpose:** Debugging and auditing past performance or errors.
- **Parameters:**
  - `lines` (int, default=20): Number of recent log lines to retrieve.
  - `log_type` (str, default="general"): Which log file to read.
    - `"general"` -> Operational logs (`trading_bot.log`).
    - `"profit"` -> Trade result logs (`profit_tracker.log`).
- **Usage Example:** `read_bot_logs(lines=50, log_type="general")`

## 🧠 Strategic Workflows

### Standard Trading Loop
1. **Analyze Market:** 
   - Call `get_market_price("BTCUSDT")` for current price.
   - Call `fetch_chart_data("BTCUSDT", interval="1h", limit=100)` to perform technical analysis (RSI, MACD, etc.) or backtest the strategy on recent data.
2. **Check Funds:** Call `get_account_balance("USDT")` and `get_account_balance("BTC")`.
3. **Decide:** Based on technical analysis and available funds.
4. **Execute:** If a trade signal is generated, call `place_order(...)`.
5. **Verify:** Call `read_bot_logs()` to confirm the order was filled correctly.

### Error Handling
- If `place_order` returns an error, immediately call `read_bot_logs()` to identify the cause (e.g., "Insufficient balance", "Min notional not met").
- If `get_base_network_status` fails, alert that the blockchain connection might be down.
