import os
from dotenv import load_dotenv

# Load environment variables
# If .env is not found in current dir, load_dotenv searches parent dirs by default.
load_dotenv()

# API Keys
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Base Network Configuration
BASE_RPC_URL = "https://mainnet.base.org"
BASE_CHAIN_ID = 8453

# Trading Parameters
TRADING_PAIRS = ['BTCUSDT']  # Bitcoin/USDT pair
MIN_ORDER_VALUE = 5.0  # Minimum USDT value required by Binance for orders
STOP_LOSS_PERCENTAGE = 1  # Tighter stop loss for safer testing
TAKE_PROFIT_PERCENTAGE = 2  # Tighter take profit for faster testing
POLLING_INTERVAL = 1800  # Time in seconds between trading checks (30 minutes) - Set for Gemini 1.5 Pro free tier limit (50 RPD)
TRADING_FEE_PERCENTAGE = 0.1  # Binance trading fee percentage (0.1% = 0.001 in decimal)
