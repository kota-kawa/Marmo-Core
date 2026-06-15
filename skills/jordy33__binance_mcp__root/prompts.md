# Prompts Sugeridos para OpenClaw - MCP Trading Tools

Ahora que el MCP está activo, aquí tienes los prompts sugeridos para usar con OpenClaw, basados en las mejores prácticas del autor.

## 1. Instrucción de Conexión y "Prueba de Humo"
En lugar de solo dar las llaves, le daremos una orden de validación técnica usando tu herramienta de apalancamiento.
"Conéctate a mi cuenta de Binance usando las herramientas de este MCP. Una vez conectado, usa la herramienta adjust_leverage para establecer el apalancamiento de BTCUSDT a 7x. No abras ninguna operación; solo haz este cambio para demostrarme que tienes acceso real a la cuenta y que puedes interactuar con el exchange correctamente."

## 2. Instrucción de Desarrollo de Estrategia y Backtesting
Aquí aprovechamos que tienes fetch_chart_data y calculate_indicators. El autor es tajante: "No permitas que la IA te diga que es una gran estrategia sin números".
"Crea una estrategia de trading para BTCUSDT en velas de 4 horas. El enfoque debe ser Trend Following (seguimiento de tendencia), permitiendo posiciones Long y Short.
Antes de programar nada definitivo:
1. Usa fetch_chart_data para obtener los últimos 30 días de datos.
2. Usa calculate_indicators para probar la lógica (ej. EMAs, RSI).
3. Ejecuta un backtest detallado y muéstrame los KPIs (Profit/Loss, Drawdown, Win Rate).
Regla de oro: Nunca despliegues la estrategia en vivo sin que yo apruebe primero los resultados del backtest."

## 3. Instrucción de Adaptación al Mercado (Cerebro Dual)
El video destaca que OpenClaw puede manejar archivos separados para diferentes condiciones.
"Quiero que diseñes un sistema con lógica de detección de mercado.
• Si el mercado es lateral (ranging), usa una estrategia de reversión a la media.
• Si el mercado tiene tendencia (trending), usa la estrategia de seguimiento.
Escribe el código en un archivo .js que use mi herramienta get_market_price para decidir qué lógica aplicar. Busca en tu base de conocimientos las mejores prácticas de análisis técnico y compárame ambas opciones con datos históricos antes de guardar el archivo."

## 4. Instrucción de Automatización y Persistencia (Cron Jobs)
Como tienes acceso a la terminal, la IA debe encargarse de la "fontanería" del sistema.
"Ahora que la estrategia está aprobada, guarda el código en un archivo llamado binance_trading_bot.js en mi carpeta de trabajo.
Configura un cron job en mi terminal para que este script se ejecute automáticamente cada 4 horas. El script debe:
1. Despertarse y consultar el balance con get_account_balance.
2. Analizar el mercado y decidir si operar.
3. Si decide operar, usar get_symbol_rules para asegurar que la orden cumple con los límites de Binance y luego ejecutarla con place_order.
4. Reportar cualquier error o éxito en read_bot_logs y luego cerrarse hasta la próxima ejecución."

## 5. Instrucción de Reflexión (La Clave del Éxito)
Trata a la IA como un desarrollador experto para mejorar el sistema continuamente.
"Actúa como mi desarrollador de trading senior. Revisa periódicamente los logs con read_bot_logs y dime: ¿Qué errores estás viendo? ¿La estrategia está rindiendo según el backtest original? Si detectas que las condiciones del mercado han cambiado drásticamente, sugéreme una actualización del código de la estrategia inmediatamente."

## Puntos clave que estamos aprovechando del autor:
• Validación sin riesgo: Usar el apalancamiento como prueba inicial.
• Colaboración humana-IA: No dejar que la IA decida sola; tú apruebas los backtests.
• Uso de archivos .js y Cron Jobs: Para que el bot "se despierte" solo y no sea solo una conversación pasiva.
• Acceso a la terminal: Para que la IA instale sus propias dependencias si algo falta.