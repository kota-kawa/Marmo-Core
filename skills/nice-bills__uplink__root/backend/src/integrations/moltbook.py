"""
Moltbook Integration for Genesis Platform
Monitors Moltbook posts for @Genesis mentions
"""

import re
import requests
from datetime import datetime
from typing import Optional, Dict, Any


class MoltbookIntegration:
    """Monitor Moltbook for fundraising requests via @Genesis mentions"""

    def __init__(self, platform_api: str = "http://localhost:8000", moltbook_api_key: str = None):
        self.platform_api = platform_api
        self.moltbook_api_key = moltbook_api_key
        self.base_url = "https://api.moltbook.com/v1"  # Example URL

    async def monitor_mentions(self):
        """
        Poll Moltbook API for @Genesis mentions
        Run this as a background task
        """
        import asyncio

        while True:
            try:
                mentions = await self._fetch_mentions()
                for mention in mentions:
                    await self._handle_mention(mention)
            except Exception as e:
                print(f"Error monitoring Moltbook: {e}")

            # Poll every 30 seconds
            await asyncio.sleep(30)

    async def _fetch_mentions(self) -> list:
        """Fetch recent @Genesis mentions from Moltbook"""
        # This would use actual Moltbook API
        # For now, return empty list as placeholder

        headers = {
            "Authorization": f"Bearer {self.moltbook_api_key}",
            "Content-Type": "application/json",
        }

        # Example API call (replace with actual Moltbook endpoint)
        # response = requests.get(
        #     f"{self.base_url}/mentions",
        #     headers=headers,
        #     params={"handle": "Genesis", "limit": 50}
        # )

        return []

    async def _handle_mention(self, post_data: Dict):
        """Handle a Moltbook mention"""

        # Parse similar to Twitter
        text = post_data.get("content", "")

        if not self._is_fundraising_request(text):
            return

        parsed = self._parse_request(text, post_data)

        # Create campaign
        try:
            campaign = await self._create_campaign(post_data, parsed)

            # Reply on Moltbook with campaign link
            await self._reply_on_moltbook(post_data, campaign)

        except Exception as e:
            print(f"Error creating campaign from Moltbook: {e}")

    def _is_fundraising_request(self, text: str) -> bool:
        """Check if post is a fundraising request"""
        text_lower = text.lower()
        trigger_words = ["fund", "raise", "need", "campaign", "help", "donation"]
        has_trigger = any(word in text_lower for word in trigger_words)
        has_amount = bool(re.search(r"\$?\d+", text))
        return has_trigger or has_amount

    def _parse_request(self, text: str, post_data: Dict) -> Dict:
        """Parse fundraising request from Moltbook post"""

        # Extract amount
        amount_match = re.search(r"\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+)", text.replace(",", ""))
        amount = float(amount_match.group(1)) if amount_match else None

        # Extract wallet
        wallet_match = re.search(r"0x[a-fA-F0-9]{40}", text)
        wallet = wallet_match.group(0) if wallet_match else None

        # Extract purpose
        purpose = self._extract_purpose(text)

        return {
            "amount": amount,
            "purpose": purpose,
            "wallet": wallet,
            "author": post_data.get("author", ""),
            "author_name": post_data.get("author_name", ""),
            "post_url": post_data.get("url", ""),
            "post_text": text,
            "post_id": post_data.get("id", ""),
        }

    def _extract_purpose(self, text: str) -> Optional[str]:
        """Extract purpose from post"""
        text = re.sub(r"@\w+", "", text)
        text = re.sub(r"\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?", "", text)
        text = re.sub(r"0x[a-fA-F0-9]{40}", "", text)
        text = " ".join(text.split())
        return text.strip() if len(text.strip()) > 5 else None

    async def _create_campaign(self, post_data: Dict, parsed: Dict) -> Dict:
        """Create campaign via API"""

        # Generate wallet if needed
        wallet_address = parsed["wallet"]
        if not wallet_address:
            wallet_address = await self._generate_wallet(parsed["author"])

        # Get or create agent
        agent_data = await self._get_or_create_agent(
            moltbook_handle=parsed["author"],
            moltbook_name=parsed["author_name"],
            wallet_address=wallet_address,
        )

        # Create campaign
        campaign_data = {
            "agent_id": agent_data["id"],
            "title": self._generate_title(parsed["purpose"]),
            "description": parsed["purpose"],
            "goal": parsed["amount"],
            "deadline": None,
            "source_message": {
                "platform": "moltbook",
                "author_handle": parsed["author"],
                "author_name": parsed["author_name"],
                "content": parsed["post_text"],
                "url": parsed["post_url"],
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

        response = requests.post(f"{self.platform_api}/campaigns", json=campaign_data, timeout=10)

        if response.status_code != 201:
            raise Exception(f"API Error: {response.text}")

        return response.json()

    def _generate_title(self, purpose: str) -> str:
        """Generate campaign title"""
        if not purpose:
            return "Fundraising Campaign"
        title = re.sub(r"[^\w\s]", "", purpose[:50]).strip()
        return title if title else "Fundraising Campaign"

    async def _generate_wallet(self, handle: str) -> str:
        """Generate wallet for user"""
        import secrets
        from eth_account import Account

        private_key = "0x" + secrets.token_hex(32)
        account = Account.from_key(private_key)
        return account.address

    async def _get_or_create_agent(
        self, moltbook_handle: str, moltbook_name: str, wallet_address: str
    ) -> Dict:
        """Get or create agent"""

        # Check existing
        response = requests.get(
            f"{self.platform_api}/agents", params={"moltbook_handle": moltbook_handle}, timeout=10
        )

        if response.status_code == 200:
            agents = response.json()
            if agents:
                return agents[0]

        # Create new
        agent_data = {
            "address": wallet_address,
            "name": moltbook_name,
            "description": f"Agent registered via Moltbook: @{moltbook_handle}",
            "moltbook_handle": moltbook_handle,
        }

        response = requests.post(f"{self.platform_api}/agents", json=agent_data, timeout=10)

        return response.json()

    async def _reply_on_moltbook(self, post_data: Dict, campaign: Dict):
        """Reply on Moltbook with campaign link"""
        # This would use Moltbook API to post a reply
        # Placeholder for now
        print(f"Would reply to Moltbook post {post_data['id']} with campaign {campaign['id']}")


# Usage example:
"""
from integrations.moltbook import MoltbookIntegration

moltbook = MoltbookIntegration(
    platform_api="http://localhost:8000",
    moltbook_api_key="your_api_key"
)

# Start monitoring (run in background)
import asyncio
asyncio.create_task(moltbook.monitor_mentions())
"""
