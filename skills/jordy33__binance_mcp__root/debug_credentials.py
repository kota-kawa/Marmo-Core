import os
from binance.client import Client
from binance.exceptions import BinanceAPIException
import config

def test_credentials():
    print(f"Testing with API KEY: {config.BINANCE_API_KEY[:5]}...{config.BINANCE_API_KEY[-5:]}")
    print(f"Testing with SECRET KEY: {config.BINANCE_SECRET_KEY[:5]}...{config.BINANCE_SECRET_KEY[-5:]}")
    
    # Try with tld=None (default, binance.com)
    print("\n--- Testing connection to binance.com ---")
    client_com = Client(config.BINANCE_API_KEY, config.BINANCE_SECRET_KEY)
    try:
        account = client_com.get_account()
        print("Success! Your credentials are valid for binance.com.")
    except BinanceAPIException as e:
        print(f"BinanceAPIException: {e}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_credentials()
