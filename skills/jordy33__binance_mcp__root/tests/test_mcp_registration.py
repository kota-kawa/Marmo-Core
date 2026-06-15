import sys
import os
import asyncio

# Agregamos el directorio padre al path para poder importar mcp_server y sus dependencias
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

async def inspect_and_test_server_tools():
    print("Loading MCP server from mcp_server module...")
    try:
        # Note: The server is configured to run on SSE (localhost:8080) when executed directly.
        # Here we import the object to test tool registration without starting the HTTP server.
        from mcp_server import mcp
    except ImportError as e:
        print(f"Error crítico al importar mcp_server: {e}")
        return

    print("Querying MCP server for registered tools...")
    try:
        tools = await mcp.list_tools()
        
        if not tools:
            print("\n[WARNING] El servidor no devolvió ninguna herramienta.")
            return
            
        print(f"\n[SUCCESS] El servidor tiene {len(tools)} herramientas registradas.")
        
        # Definimos argumentos de prueba para las herramientas que lo requieren
        test_inputs = {
            "get_market_price": {"symbol": "BTCUSDT"},
            "get_account_balance": {"asset": "USDT"},
            "read_bot_logs": {"lines": 5, "log_type": "general"},
            "fetch_chart_data": {"symbol": "BTCUSDT", "interval": "1h", "limit": 5},
            "calculate_indicators": {"symbol": "BTCUSDT", "interval": "1h", "limit": 100},
            "get_symbol_rules": {"symbol": "BTCUSDT"},
            "adjust_leverage": {"symbol": "BTCUSDT", "leverage": 7},
            "get_base_network_status": {}, # No requiere argumentos
        }

        print("\n--- Testing Tool Execution (Skipping 'place_order') ---")

        for tool in tools:
            if tool.name == "place_order":
                print(f"\n[SKIP] Skipping execution of '{tool.name}' (Safety precaution).")
                continue

            print(f"\n[EXEC] Testing '{tool.name}'...")
            
            # Preparamos los argumentos
            kwargs = test_inputs.get(tool.name, {})
            
            try:
                # Ejecutamos la herramienta a través del servidor MCP
                # Nota: call_tool devuelve una lista de contenidos (TextContent, ImageContent, etc.)
                results = await mcp.call_tool(tool.name, arguments=kwargs)
                
                # Imprimimos el resultado de forma legible
                for content in results:
                    if hasattr(content, 'text'):
                        print(f"Result: {content.text.strip()}")
                    else:
                        print(f"Result (Non-text): {content}")
                        
            except Exception as e:
                print(f"[ERROR] Failed to execute '{tool.name}': {e}")

    except Exception as e:
        print(f"\n[ERROR] Error general durante la prueba: {e}")

if __name__ == "__main__":
    asyncio.run(inspect_and_test_server_tools())
