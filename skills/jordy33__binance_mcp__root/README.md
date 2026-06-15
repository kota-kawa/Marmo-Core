# Binance MCP Server

A Model Context Protocol (MCP) server for cryptocurrency trading on Binance and Base network interactions. This server provides tools for automated trading, market analysis, and blockchain operations.

## Features

- **Binance Trading Tools**: Place orders, check balances, fetch market data, and calculate technical indicators.
- **Base Network Integration**: Monitor blockchain status and prepare for DeFi operations.
- **Technical Analysis**: Built-in RSI, MACD, Bollinger Bands, and moving averages.
- **Secure API Handling**: Environment variables for API keys.

## Installation

1. Clone or navigate to the project directory.

2. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   ```

3. Activate the virtual environment:
   ```bash
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

4. Upgrade pip and install dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

## Environment Variables

Create a `.env` file in the root directory with your API credentials:

```env
# Binance API Configuration
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET_KEY=your_binance_secret_key_here
```

**Security Note**: Never commit the `.env` file to version control. It is already included in `.gitignore`.

## Running the MCP Server

Start the server with Server-Sent Events (SSE) transport:

```bash
python mcp_server.py
```

The server will run on `http://127.0.0.1:8080/sse` by default.

## Available Tools

The MCP server exposes the following tools for integration with AI agents:

### Trading Tools
- `get_account_balance(asset="USDT")`: Get balance for a specific asset.
- `get_market_price(symbol="BTCUSDT")`: Get current market price.
- `fetch_chart_data(symbol="BTCUSDT", interval="1h", limit=100)`: Fetch historical OHLCV data.
- `calculate_indicators(symbol="BTCUSDT", interval="1h", limit=100)`: Calculate technical indicators (RSI, MACD, Bollinger Bands, etc.).
- `get_symbol_rules(symbol="BTCUSDT")`: Get trading rules and precision requirements.
- `adjust_leverage(symbol="BTCUSDT", leverage=5)`: Adjust leverage for futures trading.
- `place_order(symbol="BTCUSDT", side="BUY", quantity=0.001)`: Place a market order.

### Blockchain Tools
- `get_base_network_status()`: Check Base network health (block number, gas price).

### Utility Tools
- `read_bot_logs(lines=20, log_type="general")`: Read bot logs for debugging.

## Testing

Run the tests to verify functionality:

```bash
python -m pytest tests/
```

Or run a specific test:

```bash
python tests/test_mcp_registration.py
```

## Configuration

Trading parameters can be adjusted in `config.py`:

- `TRADING_PAIRS`: List of symbols to trade.
- `MIN_ORDER_VALUE`: Minimum order value in USDT.
- `STOP_LOSS_PERCENTAGE`: Stop loss percentage.
- `TAKE_PROFIT_PERCENTAGE`: Take profit percentage.
- `POLLING_INTERVAL`: Time between checks (in seconds).

## Security Considerations

- Use testnet for initial testing.
- Implement proper risk management.
- Monitor API rate limits.
- Keep API keys secure and rotate regularly.

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Make your changes.
4. Add tests for new functionality.
5. Submit a pull request.

## License

This project is licensed under the MIT License.

