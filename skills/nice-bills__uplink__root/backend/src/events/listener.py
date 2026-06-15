"""
Blockchain Event Listener Service
Listens for on-chain events and syncs with database
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Callable, Dict, List
import websockets
import requests

from web3 import Web3


class BlockchainEventListener:
    """
    Listens for Genesis smart contract events on Monad testnet
    Updates database when donations, campaign creations, etc. occur
    """

    def __init__(self, platform_api: str = "http://localhost:8000"):
        self.platform_api = platform_api
        self.rpc_url = os.getenv("MONAD_RPC_URL", "https://testnet-rpc.monad.xyz")
        self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))

        # Contract addresses
        self.campaign_factory = "0xbEC03ac2Fda75cbb5c7f0c510d75F5d48C68AfE0"
        self.agent_registry = "0x3f4D1B21251409075a0FB8E1b0C0A30B23f05653"

        # Event signatures
        self.event_signatures = {
            "DonationReceived": "0x"
            + Web3.keccak(text="DonationReceived(uint256,address,uint256)").hex(),
            "CampaignCreated": "0x"
            + Web3.keccak(text="CampaignCreated(uint256,uint256,uint256,uint256)").hex(),
        }

        self.last_block = 0
        self.is_running = False

    def start_listening(self, poll_interval: int = 10):
        """Start listening for events"""
        print("Starting Blockchain Event Listener...")
        print(f"Connected to: {self.rpc_url}")
        print(f"CampaignFactory: {self.campaign_factory}")

        self.is_running = True
        self.last_block = self.web3.eth.block_number

        while self.is_running:
            try:
                self._check_new_events()
            except Exception as e:
                print(f"Error checking events: {e}")

            time.sleep(poll_interval)

    def _check_new_events(self):
        """Check for new events since last block"""
        current_block = self.web3.eth.block_number

        if current_block <= self.last_block:
            return

        print(f"Checking blocks {self.last_block + 1} to {current_block}")

        # Get logs for CampaignFactory
        logs = self.web3.eth.get_logs(
            {
                "address": self.campaign_factory,
                "fromBlock": self.last_block + 1,
                "toBlock": current_block,
            }
        )

        for log in logs:
            self._process_log(log)

        self.last_block = current_block

    def _process_log(self, log: Dict):
        """Process a single log entry"""
        topics = log.get("topics", [])

        if not topics:
            return

        event_signature = topics[0].hex()

        if event_signature == self.event_signatures["DonationReceived"]:
            self._handle_donation_received(log)
        elif event_signature == self.event_signatures["CampaignCreated"]:
            self._handle_campaign_created(log)

    def _handle_donation_received(self, log: Dict):
        """Handle DonationReceived event"""
        # Decode event data
        # Event: DonationReceived(uint256 indexed campaignId, address indexed donor, uint256 amount)
        topics = log.get("topics", [])
        data = log.get("data", "0x")

        if len(topics) < 3:
            return

        campaign_id = int(topics[1].hex(), 16)
        donor = "0x" + topics[2].hex()[-40:]

        # Amount is in data field
        if data and data != "0x":
            amount_wei = int(data, 16)
            amount_eth = self.web3.from_wei(amount_wei, "ether")
        else:
            # Amount might be in value field for payable functions
            amount_eth = 0

        tx_hash = log.get("transactionHash", "").hex()

        print(f"\n🎉 Donation Received!")
        print(f"  Campaign ID: {campaign_id}")
        print(f"  Donor: {donor}")
        print(f"  Amount: {amount_eth} MON")
        print(f"  Tx: {tx_hash}")

        # Update backend database
        self._sync_donation_to_backend(campaign_id, donor, float(amount_eth), tx_hash)

    def _handle_campaign_created(self, log: Dict):
        """Handle CampaignCreated event"""
        topics = log.get("topics", [])

        if len(topics) < 2:
            return

        campaign_id = int(topics[1].hex(), 16)

        print(f"\n📢 Campaign Created!")
        print(f"  Campaign ID: {campaign_id}")

        # Could sync campaign to backend here if needed

    def _sync_donation_to_backend(self, campaign_id: int, donor: str, amount: float, tx_hash: str):
        """Sync donation to backend API"""
        try:
            # First, find the campaign UUID from campaign_id
            # For now, we'll use a simple mapping or query

            # Create donation record
            donation_data = {
                "campaign_onchain_id": campaign_id,
                "donor_address": donor,
                "amount": amount,
                "token_type": "MON",
                "tx_hash": tx_hash,
                "created_at": datetime.utcnow().isoformat(),
            }

            response = requests.post(
                f"{self.platform_api}/donations/sync", json=donation_data, timeout=10
            )

            if response.status_code == 201:
                print(f"  ✓ Synced to backend")
            else:
                print(f"  ✗ Failed to sync: {response.text}")

        except Exception as e:
            print(f"  ✗ Error syncing: {e}")

    def stop(self):
        """Stop the listener"""
        self.is_running = False
        print("Event listener stopped")


# Simple HTTP endpoint for manual sync
def create_sync_endpoint():
    """Create a simple endpoint to manually trigger sync"""
    from flask import Flask, request, jsonify

    app = Flask(__name__)
    listener = BlockchainEventListener()

    @app.route("/sync", methods=["POST"])
    def sync_events():
        """Manually trigger event sync"""
        try:
            listener._check_new_events()
            return jsonify({"status": "success", "message": "Events synced"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    return app


# Main entry point
if __name__ == "__main__":
    import time

    listener = BlockchainEventListener(
        platform_api=os.getenv("PLATFORM_API", "http://localhost:8000")
    )

    try:
        listener.start_listening(poll_interval=10)
    except KeyboardInterrupt:
        listener.stop()
