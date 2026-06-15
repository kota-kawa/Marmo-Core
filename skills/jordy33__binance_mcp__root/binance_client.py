from binance.client import Client
from binance.exceptions import BinanceAPIException
import config
import logging
import time
import math

class BinanceTrader:
    def __init__(self):
        self.client = Client(
            config.BINANCE_API_KEY, 
            config.BINANCE_SECRET_KEY,
            {"verify": True, "timeout": 20}
        )
        self.recv_window = 5000  # 5 seconds
        # Force initial time sync
        self._force_time_sync()
        
    def _force_time_sync(self):
        """Force the client to sync its time with the server"""
        try:
            # Get server time
            server_time = self.client.get_server_time()
            # Set the timestamp offset in the client
            self.client.timestamp_offset = server_time['serverTime'] - int(time.time() * 1000)
            logging.info(f"Set timestamp offset to {self.client.timestamp_offset}ms")
        except Exception as e:
            logging.error(f"Error syncing time: {e}")
            
    def _format_quantity(self, symbol, quantity):
        """Format the quantity according to the symbol's precision rules"""
        try:
            info = self.get_symbol_info(symbol)
            if not info:
                return None

            # Get step size from LOT_SIZE filter
            step_size = None
            min_qty = None
            max_qty = None
            for filter in info['filters']:
                if filter['filterType'] == 'LOT_SIZE':
                    step_size = float(filter['stepSize'])
                    min_qty = float(filter['minQty'])
                    max_qty = float(filter['maxQty'])
                    break

            if not step_size:
                logging.error(f"Could not find step size for {symbol}")
                return None

            # Calculate precision from step size
            precision = int(round(-math.log(step_size, 10), 0))
            
            # Round down to ensure we don't exceed available balance
            formatted_qty = math.floor(quantity * 10**precision) / 10**precision
            
            # Check min/max constraints
            if formatted_qty < min_qty:
                logging.error(f"Quantity {formatted_qty} is below minimum {min_qty}")
                return None
            if formatted_qty > max_qty:
                logging.error(f"Quantity {formatted_qty} is above maximum {max_qty}")
                return None

            logging.info(f"Formatted quantity for {symbol}: {formatted_qty} (precision: {precision}, min: {min_qty}, max: {max_qty})")
            return str(formatted_qty)

        except Exception as e:
            logging.error(f"Error formatting quantity: {e}")
            return None
            
    def get_account_balance(self, asset='USDT'):
        max_retries = 3
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                if retry_count > 0:
                    # Force time sync before retry
                    self._force_time_sync()
                    
                account = self.client.get_account(recvWindow=self.recv_window)
                for balance in account['balances']:
                    if balance['asset'] == asset:
                        # Return both free and locked balance for more accurate calculations
                        return {
                            'free': float(balance['free']),
                            'locked': float(balance['locked']),
                            'total': float(balance['free']) + float(balance['locked'])
                        }
            except BinanceAPIException as e:
                last_error = e
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(1)
                    continue
            except Exception as e:
                logging.error(f"Unexpected error getting balance: {e}")
                return None
                
        if last_error:
            logging.error(f"Error getting balance after {max_retries} retries: {last_error}")
        return None

    def get_market_data(self, symbol, interval='1h', limit=100):
        max_retries = 2
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                if retry_count > 0:
                    # Force time sync before retry
                    self._force_time_sync()
                    
                klines = self.client.get_klines(
                    symbol=symbol,
                    interval=interval,
                    limit=limit
                )
                
                # Validate the response
                if not klines or not isinstance(klines, list) or len(klines) == 0:
                    logging.error(f"Received invalid market data for {symbol}: {klines}")
                    retry_count += 1
                    if retry_count < max_retries:
                        time.sleep(1)
                        continue
                    return None
                    
                # Validate data structure
                for kline in klines:
                    if not isinstance(kline, list) or len(kline) < 12:
                        logging.error(f"Invalid kline data structure for {symbol}")
                        retry_count += 1
                        if retry_count < max_retries:
                            time.sleep(1)
                            continue
                        return None
                        
                return klines
                
            except BinanceAPIException as e:
                last_error = e
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(1)
                    continue
            except Exception as e:
                logging.error(f"Unexpected error getting market data: {e}")
                return None
                
        if last_error:
            logging.error(f"Error getting market data after {max_retries} retries: {last_error}")
        return None

    def _calculate_max_sell_quantity(self, balance, fee_percentage):
        """Calculate maximum quantity that can be sold accounting for fees"""
        # If we want to sell X BTC, we need X * (1 + fee) available
        # So if we have B BTC available, we can sell X where: X * (1 + fee) = B
        # Therefore X = B / (1 + fee)
        return balance / (1 + fee_percentage)

    def place_order(self, symbol, side, quantity):
        """Place a market order"""
        max_retries = 3
        retry_count = 0
        last_error = None
        
        # For SELL orders, adjust quantity to account for fees
        if side == 'SELL':
            balance = self.get_account_balance('BTC')
            if not balance:
                logging.error(f"Could not get BTC balance")
                return None
                
            # Skip if balance is too small
            if balance['free'] < 1e-5:  # Minimum tradeable amount
                logging.info(f"BTC balance {balance['free']:.8f} is too small to trade (min: 0.00001)")
                return None
                
            fee_percentage = config.TRADING_FEE_PERCENTAGE / 100
            max_sell_qty = self._calculate_max_sell_quantity(balance['free'], fee_percentage)
            
            if quantity > max_sell_qty:
                logging.info(f"Adjusting sell quantity from {quantity:.8f} to {max_sell_qty:.8f} BTC to account for {fee_percentage*100}% fee")
                quantity = max_sell_qty
        
        # Format the quantity
        formatted_qty = self._format_quantity(symbol, quantity)
        if not formatted_qty:
            return None
            
        # Get current price to verify order value
        ticker = self.client.get_symbol_ticker(symbol=symbol)
        if not ticker:
            logging.error("Could not get current price")
            return None
            
        current_price = float(ticker['price'])
        order_value = float(formatted_qty) * current_price
            
        # Get minimum notional value from symbol info
        symbol_info = self.get_symbol_info(symbol)
        min_notional = config.MIN_ORDER_VALUE  # Use config value as default
        for filter in symbol_info['filters']:
            if filter['filterType'] == 'NOTIONAL':
                min_notional = float(filter['minNotional'])
                break
                
        # Log the order details
        logging.info(f"Attempting to {side} {formatted_qty} {symbol} at ~{current_price} USDT")
        logging.info(f"Order value: {order_value:.2f} USDT (min required: {min_notional} USDT)")
        
        # Check minimum notional
        if order_value < min_notional:
            logging.error(f"Order value {order_value:.2f} USDT is below minimum required {min_notional} USDT")
            return None
            
        while retry_count < max_retries:
            try:
                if retry_count > 0:
                    self._force_time_sync()
                    
                # For BUY orders, verify USDT balance and include fee reserve
                if side == 'BUY':
                    fee_percentage = config.TRADING_FEE_PERCENTAGE / 100
                    required_usdt = order_value * (1 + fee_percentage)  # Include fee
                    balance = self.get_account_balance('USDT')
                    if not balance:
                        logging.error(f"Could not get USDT balance")
                        return None
                        
                    if balance['free'] < required_usdt:
                        logging.error(f"Insufficient USDT balance. Required (incl. {fee_percentage*100}% fee): {required_usdt:.2f}, Available: {balance['free']:.2f}")
                        return None
                
                # Get initial balances before order
                initial_base_balance = self.get_account_balance('BTC')
                initial_quote_balance = self.get_account_balance('USDT')
                
                if not initial_base_balance or not initial_quote_balance:
                    logging.error("Could not get initial balances")
                    return None
                    
                logging.info(f"Initial balances - BTC: {initial_base_balance['total']:.12f}, USDT: {initial_quote_balance['total']:.12f}")
                
                # Place the market order
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    type='MARKET',
                    quantity=formatted_qty,
                    recvWindow=self.recv_window
                )
                
                if order and order['status'] == 'FILLED':
                    logging.info(f"Order placed and filled: {order}")
                    
                    # Calculate expected balances from fills
                    executed_qty = float(order['executedQty'])
                    quote_qty = float(order['cummulativeQuoteQty'])
                    
                    # Calculate total commission
                    total_commission = 0
                    commission_asset = order['fills'][0]['commissionAsset']
                    for fill in order['fills']:
                        total_commission += float(fill['commission'])
                    
                    logging.info(f"Order details - Executed: {executed_qty} BTC, Quote: {quote_qty} USDT, Commission: {total_commission} {commission_asset}")
                    
                    if side == 'BUY':
                        if commission_asset == 'BTC':
                            expected_btc = initial_base_balance['total'] + executed_qty - total_commission
                            expected_usdt = initial_quote_balance['total'] - quote_qty
                        else:  # USDT commission
                            expected_btc = initial_base_balance['total'] + executed_qty
                            expected_usdt = initial_quote_balance['total'] - quote_qty - total_commission
                    else:  # SELL
                        if commission_asset == 'USDT':
                            expected_btc = initial_base_balance['total'] - executed_qty
                            expected_usdt = initial_quote_balance['total'] + quote_qty - total_commission
                        else:  # BTC commission
                            expected_btc = initial_base_balance['total'] - executed_qty - total_commission
                            expected_usdt = initial_quote_balance['total'] + quote_qty
                        
                    logging.info(f"Expected balances - BTC: {expected_btc:.12f}, USDT: {expected_usdt:.12f}")
                    
                    # Add small tolerance for floating point comparison
                    balance_tolerance = 1e-8
                    
                    # Wait for balance updates with expected values
                    if side == 'SELL':
                        self.wait_for_balance_update('BTC', 'decrease', expected_value=expected_btc, balance_tolerance=balance_tolerance)
                        self.wait_for_balance_update('USDT', 'increase', expected_value=expected_usdt, balance_tolerance=balance_tolerance)
                    else:  # BUY
                        self.wait_for_balance_update('USDT', 'decrease', expected_value=expected_usdt, balance_tolerance=balance_tolerance)
                        self.wait_for_balance_update('BTC', 'increase', expected_value=expected_btc, balance_tolerance=balance_tolerance)
                        
                return order
                
            except BinanceAPIException as e:
                last_error = e
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(1)
                    continue
                logging.error(f"Error placing order after {retry_count} retries: {e}")
            except Exception as e:
                logging.error(f"Unexpected error placing order: {e}")
                return None
                
        return None

    def get_symbol_info(self, symbol):
        max_retries = 2
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                if retry_count > 0:
                    # Force time sync before retry
                    self._force_time_sync()
                    
                info = self.client.get_symbol_info(symbol)
                if info:
                    logging.info(f"Symbol info for {symbol}: {info}")
                else:
                    logging.error(f"No symbol info returned for {symbol}")
                return info
            except BinanceAPIException as e:
                last_error = e
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(1)
                    continue
            except Exception as e:
                logging.error(f"Unexpected error getting symbol info: {e}")
                return None
                
        if last_error:
            logging.error(f"Error getting symbol info after {max_retries} retries: {last_error}")
        return None

    def wait_for_balance_update(self, asset, expected_operation, timeout=30, max_retries=3, expected_value=None, balance_tolerance=1e-8):
        """Wait for balance to update after an order with retries
        expected_operation: 'increase' or 'decrease'
        expected_value: if provided, wait for balance to match this value within tolerance
        balance_tolerance: tolerance for balance comparison (default 1e-8)
        """
        retry_count = 0
        while retry_count < max_retries:
            # Add initial delay before first check to allow balance to update
            time.sleep(5)  # Increased from 3s to 5s
            
            start_time = time.time()
            initial_balance = self.get_account_balance(asset)
            if not initial_balance:
                logging.error(f"Could not get initial {asset} balance")
                return False
                
            initial_free = initial_balance['free']
            initial_total = initial_balance['total']
            
            if expected_value is not None:
                logging.info(f"[Attempt {retry_count + 1}] Waiting for {asset} balance to reach {expected_value:.12f} ±{balance_tolerance:.12f} "
                           f"(current: Free: {initial_free:.12f}, Total: {initial_total:.12f})")
            else:
                logging.info(f"[Attempt {retry_count + 1}] Waiting for {asset} balance to {expected_operation} from Free: {initial_free:.12f}, Total: {initial_total:.12f}")
            
            # For very small amounts, use a relative comparison
            min_absolute_change = 1e-12  # Even smaller minimum absolute change
            min_relative_change = 0.0000001  # 0.00001% change threshold - even more sensitive
            last_check_time = 0
            
            while time.time() - start_time < timeout:
                # Add a small delay between checks
                time.sleep(1)  # Increased from 0.5s to 1s
                
                current_balance = self.get_account_balance(asset)
                if not current_balance:
                    time.sleep(1)
                    continue
                    
                current_free = current_balance['free']
                current_total = current_balance['total']
                
                # Calculate absolute and relative changes
                abs_change_free = abs(current_free - initial_free)
                abs_change_total = abs(current_total - initial_total)
                rel_change_free = abs_change_free / max(initial_free, min_absolute_change)
                rel_change_total = abs_change_total / max(initial_total, min_absolute_change)
                
                current_time = time.time()
                # Log every 3 seconds or on significant changes
                if current_time - last_check_time >= 3 or rel_change_free > min_relative_change or rel_change_total > min_relative_change:
                    if expected_value is not None:
                        balance_diff = abs(current_total - expected_value)
                        logging.info(f"{asset} balance check - Free: {current_free:.12f}, Total: {current_total:.12f} "
                                   f"(diff from expected: {balance_diff:.12f})")
                    else:
                        logging.info(f"{asset} balance check - Free: {current_free:.12f} ({rel_change_free*100:.6f}% change), "
                                   f"Total: {current_total:.12f} ({rel_change_total*100:.6f}% change)")
                    last_check_time = current_time
            
                # If expected value is provided, check if we're within tolerance
                if expected_value is not None:
                    if abs(current_total - expected_value) <= balance_tolerance:
                        logging.info(f"{asset} balance matched expected value - Current: {current_total:.12f}, Expected: {expected_value:.12f} "
                                   f"(diff: {abs(current_total - expected_value):.12f} ≤ {balance_tolerance:.12f})")
                        return True
                # Otherwise check for directional change
                else:
                    if expected_operation == 'decrease':
                        if ((current_free < initial_free and abs_change_free > min_absolute_change) or 
                            (current_total < initial_total and abs_change_total > min_absolute_change) or
                            (float(current['total']) < 0.00001 and float(current['free']) < 0.00001)):
                            logging.info(f"{asset} balance decreased - Free: {initial_free:.12f} -> {current_free:.12f} ({abs_change_free:.12f} change), "
                                       f"Total: {initial_total:.12f} -> {current_total:.12f} ({abs_change_total:.12f} change)")
                            return True
                    else:  # increase
                        if ((current_free > initial_free and abs_change_free > min_absolute_change) or 
                            (current_total > initial_total and abs_change_total > min_absolute_change)):
                            logging.info(f"{asset} balance increased - Free: {initial_free:.12f} -> {current_free:.12f} ({abs_change_free:.12f} change), "
                                       f"Total: {initial_total:.12f} -> {current_total:.12f} ({abs_change_total:.12f} change)")
                            return True
        
            if expected_value is not None:
                logging.warning(f"[Attempt {retry_count + 1}] Timeout waiting for {asset} balance to reach {expected_value:.12f} ±{balance_tolerance:.12f} - "
                              f"Last Free: {current_free:.12f}, Last Total: {current_total:.12f}")
            else:
                logging.warning(f"[Attempt {retry_count + 1}] Timeout waiting for {asset} balance to {expected_operation} - "
                              f"Last Free: {current_free:.12f} ({rel_change_free*100:.6f}% change), "
                              f"Last Total: {current_total:.12f} ({rel_change_total*100:.6f}% change)")
        
            retry_count += 1
            if retry_count < max_retries:
                logging.info(f"Retrying balance check in 5 seconds...")
                time.sleep(5)
    
        logging.error(f"Failed to detect {asset} balance update after {max_retries} attempts")
        return False

    def change_leverage(self, symbol, leverage):
        """Change the leverage for a symbol (Futures only)"""
        try:
            # Note: This will only work if the account is a Futures account
            # and the client is initialized for Futures, or if using Spot, 
            # this call might fail or require a different client method.
            # Assuming we are using the standard client which supports futures calls via extensions.
            
            # Since standard Client is mixed, we can try to access the futures endpoint directly
            # or check if a futures method exists.
            
            # For python-binance, futures methods are usually directly on the client 
            # (e.g., client.futures_change_leverage).
            # If we are in Spot mode (which we seem to be), this call will fail 
            # unless we have a Futures account linked and use the right endpoint.
            
            # Let's try to invoke the futures method.
            response = self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            logging.info(f"Leverage changed for {symbol}: {response}")
            return response
            
        except BinanceAPIException as e:
            logging.error(f"Binance API Error changing leverage: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error changing leverage: {e}")
            return None
