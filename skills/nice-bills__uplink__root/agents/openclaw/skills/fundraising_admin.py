import os
import requests
from web3 import Web3
from eth_account import Account
from datetime import datetime, timedelta, timezone

class FundraisingAdmin:
    """Genesis - High-Intelligence Platform Operator"""
    
    def __init__(self):
        # Configuration
        self.rpc_url = "https://testnet-rpc.monad.xyz"
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.api_url = os.getenv(
            "PLATFORM_API",
            "https://genesis-backend.onrender.com",
        ).rstrip("/")
        
        # SECURE: Load API Keys from Environment
        self.api_key = os.getenv("AGENT_API_KEY")
        self.private_key = os.getenv("GENESIS_PRIVATE_KEY")
        
        if not self.api_key or not self.private_key:
             raise ValueError("CRITICAL: Missing AGENT_API_KEY or GENESIS_PRIVATE_KEY in environment.")
        
        self.account = Account.from_key(self.private_key)
        self.address = self.account.address
        self._agent_uuid = None

    def _get_my_uuid(self):
        """Fetch the internal UUID for this agent based on wallet address"""
        if self._agent_uuid:
            return self._agent_uuid
            
        headers = {"X-Agent-Key": self.api_key}
        # Try to find existing agent record
        response = requests.get(f"{self.api_url}/agents/address/{self.address}", headers=headers)
        
        if response.status_code == 200:
            self._agent_uuid = response.json()["id"]
            return self._agent_uuid
        else:
            # If not registered yet, create the agent record
            payload = {
                "address": self.address,
                "name": "Genesis Operator",
                "description": "Primary Autonomous Platform Operator"
            }
            create_res = requests.post(f"{self.api_url}/agents", json=payload, headers=headers)
            self._agent_uuid = create_res.json()["id"]
            return self._agent_uuid

    def launch_campaign(self, handle, amount, purpose, tweet_url, days=30):
        """Deploy a new campaign using the correct UUID and Public Address"""
        uuid = self._get_my_uuid()
        deadline = (datetime.now(timezone.utc) + timedelta(days=int(days))).isoformat()
        
        payload = {
            "agent_id": uuid,
            "title": f"Mission: {purpose[:30]}...",
            "description": purpose,
            "goal": float(amount),
            "deadline": deadline,
            "wallet_address": self.address,
            "source_message": {
                "platform": "twitter",
                "author_handle": handle,
                "content": purpose,
                "url": tweet_url
            }
        }
        headers = {"X-Agent-Key": self.api_key}
        response = requests.post(f"{self.api_url}/campaigns", json=payload, headers=headers)
        
        if response.status_code == 400:
            return {"error": "RATE_LIMIT", "message": response.json().get("detail")}
        
        return response.json()

    def create_privy_wallet(self, user_id, handle):
        """Create a new embedded vault for a user"""
        payload = {"user_id": user_id, "twitter_handle": handle}
        headers = {"X-Agent-Key": self.api_key}
        response = requests.post(f"{self.api_url}/wallets/privy/create", params=payload, headers=headers)
        return response.json()

    def get_leaderboard(self, type="donors"):
        """Fetch platform rankings"""
        endpoint = "donors" if type == "donors" else "campaigns/top"
        response = requests.get(f"{self.api_url}/leaderboard/{endpoint}")
        return response.json()

    def sign_proposal(self, campaign_id, proposal_id):
        """Sign a multisig proposal using the private key"""
        # Logic using self.private_key and web3 will be finalized here
        return "0x_signed_tx_hash"
