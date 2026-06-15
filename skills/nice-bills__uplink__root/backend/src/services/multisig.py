# Multi-Sig Treasury Service
# Backend service for managing multi-sig operations on Genesis platform

import asyncio
import json
import os
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

import aiohttp
from web3 import Web3
from eth_account import Account
from eth_abi import encode


logger = logging.getLogger(__name__)


class ProposalState(Enum):
    """Proposal states matching smart contract"""

    PENDING = "pending"
    APPROVED = "approved"
    EXECUTED = "executed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ProposalType(Enum):
    """Proposal types"""

    SPEND = "spend"
    REMOVE_SIGNER = "remove_signer"


@dataclass
class SpendProposal:
    """Spend proposal data structure"""

    id: int
    campaign_id: int
    recipient: str
    amount: Decimal
    token: str  # "ETH" or token address
    required_confirmations: int
    confirmations: int
    expiration_time: datetime
    state: ProposalState
    description: str
    created_at: datetime


@dataclass
class TreasuryConfig:
    """Treasury configuration"""

    campaign_id: int
    signers: List[str]
    signer_count: int
    total_funds: Decimal
    is_active: bool
    agent_owner: str


class MultiSigService:
    """
    Service for managing multi-sig treasury operations

    Features:
    - Create and manage campaign treasuries
    - Propose and approve spends
    - Remove Genesis signer (with 1-2% fee)
    - Monitor and log all actions
    """

    # Configuration
    MIN_MULTISIG_SPEND_USD = 300  # $300 minimum for multi-sig
    MIN_REMOVAL_FEE_BPS = 100  # 1%
    MAX_REMOVAL_FEE_BPS = 200  # 2%
    BPS_DENOMINATOR = 10000
    REQUIRED_CONFIRMATIONS = 2

    # Contract ABIs (simplified - full ABIs would be loaded from JSON)
    MULTISIG_TREASURY_ABI = [
        {
            "inputs": [
                {"internalType": "uint256", "name": "_campaignId", "type": "uint256"},
                {"internalType": "address", "name": "_agentOwner", "type": "address"},
                {"internalType": "address", "name": "_agentSigner", "type": "address"},
            ],
            "name": "createTreasury",
            "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "uint256", "name": "_campaignId", "type": "uint256"},
                {"internalType": "address", "name": "_recipient", "type": "address"},
                {"internalType": "uint256", "name": "_amount", "type": "uint256"},
                {"internalType": "address", "name": "_token", "type": "address"},
                {"internalType": "string", "name": "_description", "type": "string"},
            ],
            "name": "proposeSpend",
            "outputs": [{"internalType": "uint256", "name": "proposalId", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "uint256", "name": "_campaignId", "type": "uint256"},
                {"internalType": "uint256", "name": "_proposalId", "type": "uint256"},
            ],
            "name": "confirmProposal",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "uint256", "name": "_campaignId", "type": "uint256"},
                {"internalType": "uint256", "name": "_removalFeeBps", "type": "uint256"},
            ],
            "name": "removeGenesisSigner",
            "outputs": [],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "uint256", "name": "", "type": "uint256"},
                {"internalType": "uint256", "name": "", "type": "uint256"},
            ],
            "name": "spendProposals",
            "outputs": [
                {"internalType": "uint256", "name": "id", "type": "uint256"},
                {"internalType": "address", "name": "recipient", "type": "address"},
                {"internalType": "uint256", "name": "amount", "type": "uint256"},
                {"internalType": "address", "name": "token", "type": "address"},
                {"internalType": "uint256", "name": "requiredConfirmations", "type": "uint256"},
                {"internalType": "uint256", "name": "confirmations", "type": "uint256"},
                {"internalType": "uint256", "name": "expirationTime", "type": "uint256"},
                {
                    "internalType": "enum MultiSigTreasury.ProposalState",
                    "name": "state",
                    "type": "uint8",
                },
                {"internalType": "string", "name": "description", "type": "string"},
                {"internalType": "uint256", "name": "campaignId", "type": "uint256"},
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "uint256", "name": "_campaignId", "type": "uint256"}],
            "name": "getBalance",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "uint256", "name": "_campaignId", "type": "uint256"}],
            "name": "getSigners",
            "outputs": [{"internalType": "address[]", "name": "", "type": "address[]"}],
            "stateMutability": "view",
            "type": "function",
        },
    ]

    def __init__(
        self,
        web3_provider: str,
        multisig_contract_address: str,
        genesis_bot_private_key: str,
        platform_api_url: str = "http://localhost:8000",
        price_oracle_url: Optional[str] = None,
    ):
        """
        Initialize multi-sig service

        Args:
            web3_provider: Web3 provider URL (e.g., Infura, Alchemy)
            multisig_contract_address: MultiSigTreasury contract address
            genesis_bot_private_key: Private key for Genesis bot signer
            platform_api_url: URL for Genesis platform API
            price_oracle_url: Optional price oracle URL for USD conversion
        """
        self.w3 = Web3(Web3.HTTPProvider(web3_provider))
        self.contract_address = multisig_contract_address
        self.genesis_account = Account.from_key(genesis_bot_private_key)
        self.platform_api = platform_api_url
        self.price_oracle_url = price_oracle_url

        # Initialize contract
        self.contract = self.w3.eth.contract(
            address=multisig_contract_address, abi=self.MULTISIG_TREASURY_ABI
        )

        # Action logging
        self.action_logs: List[Dict] = []

    def _log_action(self, action: str, data: Dict):
        """Log an action with timestamp"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "data": data,
            "tx_hash": data.get("tx_hash"),
            "signer": data.get("signer", self.genesis_account.address),
        }
        self.action_logs.append(log_entry)
        logger.info(f"Multi-sig action: {action}", extra=log_entry)

    async def create_treasury(
        self, campaign_id: int, agent_owner_address: str, agent_signer_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new multi-sig treasury for a campaign

        Args:
            campaign_id: Campaign ID
            agent_owner_address: Agent owner wallet address
            agent_signer_address: Optional additional signer

        Returns:
            Dict with transaction receipt and treasury info
        """
        # Validate addresses
        if not self.w3.is_address(agent_owner_address):
            raise ValueError(f"Invalid agent owner address: {agent_owner_address}")

        if agent_signer_address and not self.w3.is_address(agent_signer_address):
            raise ValueError(f"Invalid agent signer address: {agent_signer_address}")

        # Build transaction
        tx = self.contract.functions.createTreasury(
            campaign_id,
            agent_owner_address,
            agent_signer_address or "0x0000000000000000000000000000000000000000",
        ).build_transaction(
            {
                "from": self.genesis_account.address,
                "nonce": self.w3.eth.get_transaction_count(self.genesis_account.address),
                "gas": 500000,
                "gasPrice": self.w3.eth.gas_price,
            }
        )

        # Sign and send
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.genesis_account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        self._log_action(
            "treasury_created",
            {
                "campaign_id": campaign_id,
                "agent_owner": agent_owner_address,
                "agent_signer": agent_signer_address,
                "tx_hash": tx_hash.hex(),
            },
        )

        return {
            "success": receipt.status == 1,
            "tx_hash": tx_hash.hex(),
            "campaign_id": campaign_id,
            "treasury_address": self.contract_address,
            "signers": await self.get_treasury_signers(campaign_id),
        }

    async def propose_spend(
        self,
        campaign_id: int,
        recipient: str,
        amount_eth: Decimal,
        description: str,
        token_address: str = "ETH",
        proposer_private_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Propose a spend from the treasury

        Args:
            campaign_id: Campaign ID
            recipient: Recipient address
            amount_eth: Amount in ETH
            description: Spend description
            token_address: Token address ("ETH" for native)
            proposer_private_key: Optional private key (uses Genesis if not provided)

        Returns:
            Dict with proposal details
        """
        if not self.w3.is_address(recipient):
            raise ValueError(f"Invalid recipient address: {recipient}")

        # Convert amount to wei
        amount_wei = self.w3.to_wei(amount_eth, "ether")

        # Determine token address (0x0 for ETH)
        token = (
            "0x0000000000000000000000000000000000000000"
            if token_address == "ETH"
            else token_address
        )

        # Use agent owner or Genesis for proposal
        signer = (
            Account.from_key(proposer_private_key) if proposer_private_key else self.genesis_account
        )

        tx = self.contract.functions.proposeSpend(
            campaign_id, recipient, amount_wei, token, description
        ).build_transaction(
            {
                "from": signer.address,
                "nonce": self.w3.eth.get_transaction_count(signer.address),
                "gas": 300000,
                "gasPrice": self.w3.eth.gas_price,
            }
        )

        signed_tx = self.w3.eth.account.sign_transaction(tx, signer.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        # Get proposal ID from event
        proposal_id = await self._get_latest_proposal_id(campaign_id)

        self._log_action(
            "spend_proposed",
            {
                "campaign_id": campaign_id,
                "proposal_id": proposal_id,
                "recipient": recipient,
                "amount_eth": str(amount_eth),
                "description": description,
                "tx_hash": tx_hash.hex(),
                "proposer": signer.address,
            },
        )

        return {
            "success": receipt.status == 1,
            "proposal_id": proposal_id,
            "campaign_id": campaign_id,
            "recipient": recipient,
            "amount_eth": str(amount_eth),
            "tx_hash": tx_hash.hex(),
        }

    async def confirm_proposal(
        self, campaign_id: int, proposal_id: int, signer_private_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Confirm a spend proposal

        Args:
            campaign_id: Campaign ID
            proposal_id: Proposal ID
            signer_private_key: Optional private key (uses Genesis if not provided)

        Returns:
            Dict with confirmation details
        """
        signer = (
            Account.from_key(signer_private_key) if signer_private_key else self.genesis_account
        )

        tx = self.contract.functions.confirmProposal(campaign_id, proposal_id).build_transaction(
            {
                "from": signer.address,
                "nonce": self.w3.eth.get_transaction_count(signer.address),
                "gas": 200000,
                "gasPrice": self.w3.eth.gas_price,
            }
        )

        signed_tx = self.w3.eth.account.sign_transaction(tx, signer.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        # Get updated proposal state
        proposal = await self.get_proposal(campaign_id, proposal_id)

        self._log_action(
            "proposal_confirmed",
            {
                "campaign_id": campaign_id,
                "proposal_id": proposal_id,
                "signer": signer.address,
                "confirmations": proposal["confirmations"],
                "state": proposal["state"],
                "tx_hash": tx_hash.hex(),
            },
        )

        return {
            "success": receipt.status == 1,
            "proposal_id": proposal_id,
            "confirmations": proposal["confirmations"],
            "state": proposal["state"],
            "tx_hash": tx_hash.hex(),
        }

    async def remove_genesis_signer(
        self,
        campaign_id: int,
        removal_fee_bps: int = 150,  # Default 1.5%
        agent_owner_private_key: str = None,
    ) -> Dict[str, Any]:
        """
        Remove Genesis bot as signer by paying removal fee

        Args:
            campaign_id: Campaign ID
            removal_fee_bps: Removal fee in basis points (100-200 = 1-2%)
            agent_owner_private_key: Agent owner private key (required)

        Returns:
            Dict with transaction details
        """
        if not agent_owner_private_key:
            raise ValueError("Agent owner private key required for removing Genesis signer")

        if removal_fee_bps < self.MIN_REMOVAL_FEE_BPS or removal_fee_bps > self.MAX_REMOVAL_FEE_BPS:
            raise ValueError(
                f"Removal fee must be between {self.MIN_REMOVAL_FEE_BPS} and {self.MAX_REMOVAL_FEE_BPS} bps"
            )

        agent_account = Account.from_key(agent_owner_private_key)

        # Calculate fee amount
        treasury_balance = await self.get_treasury_balance(campaign_id)
        fee_amount = (treasury_balance * removal_fee_bps) // self.BPS_DENOMINATOR

        tx = self.contract.functions.removeGenesisSigner(
            campaign_id, removal_fee_bps
        ).build_transaction(
            {
                "from": agent_account.address,
                "value": fee_amount,
                "nonce": self.w3.eth.get_transaction_count(agent_account.address),
                "gas": 300000,
                "gasPrice": self.w3.eth.gas_price,
            }
        )

        signed_tx = self.w3.eth.account.sign_transaction(tx, agent_account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        self._log_action(
            "genesis_signer_removed",
            {
                "campaign_id": campaign_id,
                "removal_fee_bps": removal_fee_bps,
                "fee_amount_wei": fee_amount,
                "tx_hash": tx_hash.hex(),
                "agent_owner": agent_account.address,
            },
        )

        return {
            "success": receipt.status == 1,
            "fee_paid_wei": fee_amount,
            "fee_paid_eth": self.w3.from_wei(fee_amount, "ether"),
            "tx_hash": tx_hash.hex(),
        }

    async def get_treasury_signers(self, campaign_id: int) -> List[str]:
        """Get list of signers for a treasury"""
        signers = self.contract.functions.getSigners(campaign_id).call()
        return signers

    async def get_treasury_balance(self, campaign_id: int) -> int:
        """Get treasury balance in wei"""
        balance = self.contract.functions.getBalance(campaign_id).call()
        return balance

    async def get_proposal(self, campaign_id: int, proposal_id: int) -> Dict[str, Any]:
        """Get proposal details"""
        proposal = self.contract.functions.spendProposals(campaign_id, proposal_id).call()

        return {
            "id": proposal[0],
            "recipient": proposal[1],
            "amount_wei": proposal[2],
            "amount_eth": self.w3.from_wei(proposal[2], "ether"),
            "token": proposal[3],
            "required_confirmations": proposal[4],
            "confirmations": proposal[5],
            "expiration_time": datetime.fromtimestamp(proposal[6]),
            "state": ProposalState(list(ProposalState)[proposal[7]].value),
            "description": proposal[8],
            "campaign_id": proposal[9],
        }

    async def _get_latest_proposal_id(self, campaign_id: int) -> int:
        """Get the latest proposal ID for a campaign"""
        # This would typically query events or state
        # For now, return 0 (would be implemented with event logs)
        return 0

    async def calculate_removal_fee(self, campaign_id: int, fee_bps: int) -> Decimal:
        """
        Calculate removal fee in ETH

        Args:
            campaign_id: Campaign ID
            fee_bps: Fee in basis points

        Returns:
            Fee amount in ETH
        """
        balance_wei = await self.get_treasury_balance(campaign_id)
        fee_wei = (balance_wei * fee_bps) // self.BPS_DENOMINATOR
        return self.w3.from_wei(fee_wei, "ether")

    def requires_multisig(self, amount_usd: Decimal) -> bool:
        """
        Check if spend requires multi-sig approval

        Args:
            amount_usd: Amount in USD

        Returns:
            True if multi-sig required (>= $300)
        """
        return amount_usd >= self.MIN_MULTISIG_SPEND_USD

    async def get_action_logs(
        self,
        campaign_id: Optional[int] = None,
        action_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Get action logs with optional filters

        Args:
            campaign_id: Filter by campaign
            action_type: Filter by action type
            start_time: Filter from time
            end_time: Filter to time

        Returns:
            List of log entries
        """
        filtered_logs = self.action_logs

        if campaign_id:
            filtered_logs = [
                log for log in filtered_logs if log["data"].get("campaign_id") == campaign_id
            ]

        if action_type:
            filtered_logs = [log for log in filtered_logs if log["action"] == action_type]

        if start_time:
            filtered_logs = [
                log
                for log in filtered_logs
                if datetime.fromisoformat(log["timestamp"]) >= start_time
            ]

        if end_time:
            filtered_logs = [
                log for log in filtered_logs if datetime.fromisoformat(log["timestamp"]) <= end_time
            ]

        return filtered_logs

    async def auto_approve_as_genesis(self, campaign_id: int, proposal_id: int) -> Dict[str, Any]:
        """
        Automatically approve a proposal as Genesis bot
        Called when proposal meets criteria

        Args:
            campaign_id: Campaign ID
            proposal_id: Proposal ID

        Returns:
            Confirmation result
        """
        logger.info(f"Genesis auto-approving proposal {proposal_id} for campaign {campaign_id}")

        result = await self.confirm_proposal(campaign_id, proposal_id)

        self._log_action(
            "genesis_auto_approved",
            {
                "campaign_id": campaign_id,
                "proposal_id": proposal_id,
                "tx_hash": result.get("tx_hash"),
            },
        )

        return result


class MultiSigEventMonitor:
    """
    Monitor for multi-sig events and auto-actions
    """

    def __init__(self, multisig_service: MultiSigService):
        self.service = multisig_service
        self.running = False

    async def start_monitoring(self):
        """Start monitoring for new proposals"""
        self.running = True
        logger.info("Multi-sig event monitor started")

        while self.running:
            try:
                # Poll for new pending proposals
                await self._check_pending_proposals()
                await asyncio.sleep(10)  # Poll every 10 seconds
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)

    async def _check_pending_proposals(self):
        """Check for proposals needing Genesis approval"""
        # Implementation would query contract for pending proposals
        # and auto-approve based on criteria
        pass

    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.running = False
        logger.info("Multi-sig event monitor stopped")


# Example usage and testing
if __name__ == "__main__":
    # Setup
    service = MultiSigService(
        web3_provider=os.getenv("WEB3_PROVIDER", "http://localhost:8545"),
        multisig_contract_address=os.getenv("MULTISIG_CONTRACT", "0x..."),
        genesis_bot_private_key=os.getenv("GENESIS_PRIVATE_KEY", "0x..."),
        platform_api_url=os.getenv("PLATFORM_API", "http://localhost:8000"),
    )

    async def test():
        # Create treasury
        result = await service.create_treasury(
            campaign_id=1, agent_owner_address="0x...", agent_signer_address="0x..."
        )
        print(f"Treasury created: {result}")

        # Propose spend
        proposal = await service.propose_spend(
            campaign_id=1, recipient="0x...", amount_eth=Decimal("0.5"), description="Test spend"
        )
        print(f"Spend proposed: {proposal}")

    # Run test
    asyncio.run(test())
