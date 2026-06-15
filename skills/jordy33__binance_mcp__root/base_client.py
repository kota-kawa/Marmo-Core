from web3 import Web3
import config
import logging

class BaseClient:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(config.BASE_RPC_URL))
        
    def check_connection(self):
        return self.w3.is_connected()
    
    def get_latest_block(self):
        try:
            return self.w3.eth.block_number
        except Exception as e:
            logging.error(f"Error getting latest block: {e}")
            return None
    
    def get_gas_price(self):
        try:
            return self.w3.eth.gas_price
        except Exception as e:
            logging.error(f"Error getting gas price: {e}")
            return None
    
    def send_transaction(self, transaction):
        """
        Placeholder for sending transactions on Base network
        transaction should include:
        - from_address
        - to_address
        - value
        - gas
        - gasPrice
        - nonce
        """
        try:
            # Sign and send the transaction
            # This is a placeholder - implement actual transaction logic
            signed_txn = self.w3.eth.account.sign_transaction(transaction)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            return tx_hash
        except Exception as e:
            logging.error(f"Error sending transaction: {e}")
            return None
