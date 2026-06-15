from mcp.server.fastmcp import FastMCP
from binance_client import BinanceTrader
from base_client import BaseClient
import logging
import os
import pandas as pd
import numpy as np

# Initialize the MCP Server
mcp = FastMCP("CryptoTradingBot")

# Initialize Binance Client
try:
    trader = BinanceTrader()
except Exception as e:
    logging.error(f"Failed to initialize BinanceTrader: {e}")
    trader = None

# Initialize Base Client
try:
    base_client = BaseClient()
except Exception as e:
    logging.error(f"Failed to initialize BaseClient: {e}")
    base_client = None

@mcp.tool()
def get_account_balance(asset: str = "USDT") -> str:
    """
    Get the current balance of a specific asset (e.g., USDT, BTC).
    Returns a formatted string with free, locked, and total balance.
    """
    if not trader:
        return "Error: BinanceTrader not initialized."
    
    balance = trader.get_account_balance(asset)
    if balance:
        return f"{asset} Balance: Free={balance['free']}, Locked={balance['locked']}, Total={balance['total']}"
    else:
        return f"Could not retrieve balance for {asset}"

@mcp.tool()
def get_market_price(symbol: str) -> str:
    """
    Get the current price for a trading pair (e.g., BTCUSDT).
    """
    if not trader:
        return "Error: BinanceTrader not initialized."
    
    try:
        ticker = trader.client.get_symbol_ticker(symbol=symbol)
        if ticker:
            return f"Price of {symbol}: {ticker['price']}"
        else:
            return f"Could not retrieve price for {symbol}"
    except Exception as e:
        return f"Error fetching price: {str(e)}"

@mcp.tool()
def fetch_chart_data(symbol: str, interval: str = "1h", limit: int = 100) -> str:
    """
    Fetch historical OHLCV (Open, High, Low, Close, Volume) data for a symbol.
    Useful for technical analysis and backtesting.
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
        interval: Candle interval (e.g., '1m', '5m', '1h', '4h', '1d')
        limit: Number of data points to retrieve (max 500 suggested for context limits)
        
    Returns:
        A formatted string of list of dictionaries containing:
        timestamp, open, high, low, close, volume
    """
    if not trader:
        return "Error: BinanceTrader not initialized."
        
    try:
        klines = trader.get_market_data(symbol, interval, limit)
        if not klines:
            return f"No market data found for {symbol}"
            
        # Format klines into a readable list of dicts
        # Binance kline format: 
        # [0: Open time, 1: Open, 2: High, 3: Low, 4: Close, 5: Volume, ...]
        formatted_data = []
        for k in klines:
            formatted_data.append({
                "time": k[0], # Timestamp (ms)
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5])
            })
            
        # Return as string representation of the list
        return str(formatted_data)
        
    except Exception as e:
        return f"Error fetching chart data: {str(e)}"

@mcp.tool()
def calculate_indicators(symbol: str, interval: str = "1h", limit: int = 100) -> str:
    """
    Calculate technical indicators (RSI, MACD, Bollinger Bands, EMA, SMA) for a symbol.
    Use this to determine if the market is Trending or Ranging.
    
    Returns:
        A dictionary with the latest indicator values.
    """
    if not trader:
        return "Error: BinanceTrader not initialized."
        
    try:
        klines = trader.get_market_data(symbol, interval, limit)
        if not klines:
            return f"No market data found for {symbol}"

        # Create DataFrame
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 
            'close_time', 'quote_asset_volume', 'number_of_trades', 
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Convert to floats
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
            
        # --- Calculate Indicators ---
        
        # 1. RSI (14)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 2. MACD (12, 26, 9)
        exp12 = df['close'].ewm(span=12, adjust=False).mean()
        exp26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp12 - exp26
        df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['hist'] = df['macd'] - df['signal']
        
        # 3. Bollinger Bands (20, 2)
        df['sma20'] = df['close'].rolling(window=20).mean()
        df['std20'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['sma20'] + (df['std20'] * 2)
        df['bb_lower'] = df['sma20'] - (df['std20'] * 2)
        
        # 4. Moving Averages
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['sma200'] = df['close'].rolling(window=200).mean()
        
        # Get latest values (last closed candle usually, but here we take the very last one available)
        latest = df.iloc[-1]
        
        # Determine Market State (Simple Heuristic)
        # Trending: Price > EMA50 (Uptrend) or Price < EMA50 (Downtrend) AND ADX > 25 (not calc here, but RSI can hint)
        # Ranging: RSI between 40-60, Price near SMA20 (Middle BB)
        
        market_state = "Unknown"
        if 40 < latest['rsi'] < 60:
            market_state = "Likely Ranging"
        elif latest['rsi'] > 70 or latest['rsi'] < 30:
            market_state = "Likely Trending/Overextended"
        else:
            market_state = "Neutral/Trending"
            
        result = {
            "symbol": symbol,
            "current_price": latest['close'],
            "indicators": {
                "RSI_14": round(latest['rsi'], 2),
                "MACD": {
                    "macd": round(latest['macd'], 4),
                    "signal": round(latest['signal'], 4),
                    "hist": round(latest['hist'], 4)
                },
                "Bollinger_Bands": {
                    "upper": round(latest['bb_upper'], 2),
                    "middle_sma20": round(latest['sma20'], 2),
                    "lower": round(latest['bb_lower'], 2)
                },
                "EMA_50": round(latest['ema50'], 2),
                "SMA_200": round(latest['sma200'], 2) if not np.isnan(latest['sma200']) else "Not enough data"
            },
            "market_state_heuristic": market_state
        }
        
        return str(result)
        
    except Exception as e:
        return f"Error calculating indicators: {str(e)}"

@mcp.tool()
def get_symbol_rules(symbol: str) -> str:
    """
    Get specific trading rules (Exchange Info) for a symbol.
    Returns details like LOT_SIZE (step size), MIN_NOTIONAL, etc.
    Useful for the AI to calculate precise quantities dynamically.
    """
    if not trader:
        return "Error: BinanceTrader not initialized."
    
    try:
        info = trader.get_symbol_info(symbol)
        if not info:
            return f"Could not retrieve info for {symbol}"

        # Extract specific filters for cleaner AI consumption
        filters = {f['filterType']: f for f in info.get('filters', [])}
        
        extracted_rules = {
            "symbol": symbol,
            "baseAsset": info.get("baseAsset"),
            "quoteAsset": info.get("quoteAsset"),
        }
        
        # Quantity Rules (LOT_SIZE)
        if 'LOT_SIZE' in filters:
            extracted_rules['lot_size'] = {
                "minQty": filters['LOT_SIZE'].get('minQty'),
                "maxQty": filters['LOT_SIZE'].get('maxQty'),
                "stepSize": filters['LOT_SIZE'].get('stepSize')
            }
            
        # Value Rules (NOTIONAL or MIN_NOTIONAL)
        if 'NOTIONAL' in filters:
            extracted_rules['min_notional'] = filters['NOTIONAL'].get('minNotional')
        elif 'MIN_NOTIONAL' in filters:
             extracted_rules['min_notional'] = filters['MIN_NOTIONAL'].get('minNotional')
             
        # Price Rules (PRICE_FILTER)
        if 'PRICE_FILTER' in filters:
             extracted_rules['price_filter'] = {
                 "minPrice": filters['PRICE_FILTER'].get('minPrice'),
                 "maxPrice": filters['PRICE_FILTER'].get('maxPrice'),
                 "tickSize": filters['PRICE_FILTER'].get('tickSize')
             }

        return str(extracted_rules)

    except Exception as e:
        return f"Error getting symbol rules: {str(e)}"

@mcp.tool()
def adjust_leverage(symbol: str, leverage: int) -> str:
    """
    Adjust the leverage for a specific symbol (Futures only).
    Useful for verifying API connectivity without placing an order.
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
        leverage: Leverage multiplier (e.g., 5, 10, 20)
        
    Returns:
        Success message with response details or error message.
    """
    if not trader:
        return "Error: BinanceTrader not initialized."
        
    try:
        result = trader.change_leverage(symbol, leverage)
        if result:
            return f"Success: Leverage for {symbol} changed to {leverage}x. Response: {result}"
        else:
            return f"Failed to change leverage for {symbol}. Check logs/permissions (Futures enabled?)."
    except Exception as e:
        return f"Error changing leverage: {str(e)}"

@mcp.tool()
def place_order(symbol: str, side: str, quantity: float) -> str:
    """
    Place a MARKET order (BUY or SELL).
    side: 'BUY' or 'SELL'
    quantity: Amount of base asset to buy/sell.
    """
    if not trader:
        return "Error: BinanceTrader not initialized."
    
    # Simple validation
    if side.upper() not in ['BUY', 'SELL']:
        return "Error: Side must be BUY or SELL"
        
    try:
        order = trader.place_order(symbol, side.upper(), quantity)
        if order:
            return f"Order executed successfully: {order}"
        else:
            return "Order failed. Check logs for details."
    except Exception as e:
        return f"Error executing order: {str(e)}"

@mcp.tool()
def get_base_network_status() -> str:
    """Get the current status of the Base network (Block number and Gas price)."""
    if not base_client or not base_client.check_connection():
        return "Error: BaseClient not connected."
    
    try:
        block = base_client.get_latest_block()
        gas = base_client.get_gas_price()
        return f"Base Network Status:\nLatest Block: {block}\nGas Price: {gas} wei"
    except Exception as e:
        return f"Error fetching network status: {str(e)}"

@mcp.tool()
def read_bot_logs(lines: int = 20, log_type: str = "general") -> str:
    """
    Read the last N lines from the bot logs.
    log_type: 'general' (trading_bot.log) or 'profit' (profit_tracker.log)
    """
    log_filename = "profit_tracker.log" if log_type == "profit" else "trading_bot.log"
    
    # Check current directory first, then parent directory
    possible_paths = [log_filename, os.path.join("..", log_filename)]
    
    log_path = None
    for path in possible_paths:
        if os.path.exists(path):
            log_path = path
            break
            
    if not log_path:
        return f"Log file {log_filename} does not exist in current or parent directory."
            
    try:
        with open(log_path, 'r') as f:
            # Efficiently read last N lines
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if lines > 0 else []
            return "".join(last_lines)
    except Exception as e:
        return f"Error reading logs: {str(e)}"

if __name__ == "__main__":
    # Run the server using SSE transport.
    # Note: FastMCP.run() arguments might vary by version. 
    # If host/port args failed, we try just transport='sse' which defaults to localhost:8000 usually.
    # To specify port, some versions use environment variables or specific args like `port=8080` might be passed differently.
    # Let's try without host/port first, as they caused the TypeError.
    # Use PORT environment variable if supported by the underlying implementation.
    os.environ["PORT"] = "8080"
    os.environ["HOST"] = "127.0.0.1"
    mcp.run(transport='sse')
