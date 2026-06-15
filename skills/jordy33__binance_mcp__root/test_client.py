import asyncio
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

async def main():
    try:
        async with sse_client("http://127.0.0.1:8000/sse") as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                
                print("--- Testing Binance MCP Tools ---")
                
                # Test 1: get_market_price
                print("\n1. Testing 'get_market_price' for BTCUSDT...")
                try:
                    result = await session.call_tool("get_market_price", {"symbol": "BTCUSDT"})
                    # result.content is usually a list of TextContent objects
                    for content in result.content:
                        print(f"Result: {content.text}")
                except Exception as e:
                    print(f"Failed: {e}")

                # Test 2: get_symbol_rules
                print("\n2. Testing 'get_symbol_rules' for BTCUSDT...")
                try:
                    result = await session.call_tool("get_symbol_rules", {"symbol": "BTCUSDT"})
                    for content in result.content:
                        print(f"Result: {content.text}")
                except Exception as e:
                    print(f"Failed: {e}")
                    
                # Test 3: get_account_balance
                print("\n3. Testing 'get_account_balance' for USDT (Requires valid API keys)...")
                try:
                    result = await session.call_tool("get_account_balance", {"asset": "USDT"})
                    for content in result.content:
                        print(f"Result: {content.text}")
                except Exception as e:
                    print(f"Failed: {e}")

    except Exception as e:
        print(f"Error connecting to server: {e}")

if __name__ == "__main__":
    asyncio.run(main())
