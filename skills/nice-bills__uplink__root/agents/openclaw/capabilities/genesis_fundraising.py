"""
Genesis Fundraising Capability for OpenClaw Agent
Monitors Twitter for @Genesis mentions and auto-creates campaigns
"""

import re
import requests
from datetime import datetime
from typing import Optional, Dict, Any


class GenesisFundraisingCapability:
    """Monitor Twitter for @Genesis mentions and create campaigns"""

    def __init__(self, agent, platform_api: str = "http://localhost:8000"):
        self.agent = agent
        self.platform_api = platform_api
        self.trigger_words = [
            "fund",
            "raise",
            "need",
            "campaign",
            "help",
            "donation",
            "support",
        ]

    async def handle_twitter_mention(self, tweet_data: Dict[str, Any]) -> Optional[str]:
        """
        Handle when someone mentions @Genesis on Twitter

        Args:
            tweet_data: Dict with 'id', 'text', 'author', 'author_name', 'url'

        Returns:
            Reply text or None if not a fundraising request
        """
        text = tweet_data.get("text", "")

        # Check if it's a fundraising request
        if not self._is_fundraising_request(text):
            return None

        # Parse the request
        parsed = self._parse_fundraising_request(text, tweet_data)

        # Check what information is missing
        missing = self._check_missing_info(parsed)

        if missing:
            # Ask for missing details
            return self._generate_question_reply(tweet_data, missing)

        # We have all info, create campaign
        try:
            campaign = await self._create_campaign(tweet_data, parsed)
            return self._generate_success_reply(tweet_data, campaign)
        except Exception as e:
            return f"@{tweet_data['author']} Sorry, couldn't create campaign. Error: {str(e)}"

    def _is_fundraising_request(self, text: str) -> bool:
        """Check if tweet is a fundraising request"""
        text_lower = text.lower()
        has_trigger = any(word in text_lower for word in self.trigger_words)
        has_amount = bool(re.search(r"\$?\d+", text))
        return has_trigger or has_amount

    def _parse_fundraising_request(self, text: str, tweet_data: Dict) -> Dict[str, Any]:
        """Parse amount, purpose, and wallet from tweet"""

        # Extract amount (handles $500, 500, $1,000, etc.)
        amount_match = re.search(
            r"\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+)", text.replace(",", "")
        )
        amount = float(amount_match.group(1)) if amount_match else None

        # Extract wallet address (0x...)
        wallet_match = re.search(r"0x[a-fA-F0-9]{40}", text)
        wallet = wallet_match.group(0) if wallet_match else None

        # Extract purpose
        purpose = self._extract_purpose(text)

        return {
            "amount": amount,
            "purpose": purpose,
            "wallet": wallet,
            "author": tweet_data["author"],
            "author_name": tweet_data.get("author_name", tweet_data["author"]),
            "tweet_url": tweet_data.get("url", ""),
            "tweet_text": text,
            "tweet_id": tweet_data["id"],
        }

    def _extract_purpose(self, text: str) -> Optional[str]:
        """Extract the purpose/fundraiser description from tweet"""
        # Remove @Genesis and other mentions
        text = re.sub(r"@\w+", "", text)

        # Remove amount patterns
        text = re.sub(r"\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?", "", text)

        # Remove wallet address
        text = re.sub(r"0x[a-fA-F0-9]{40}", "", text)

        # Clean up whitespace
        text = " ".join(text.split())

        return text.strip() if len(text.strip()) > 5 else None

    def _check_missing_info(self, parsed: Dict) -> Optional[str]:
        """Check what information is missing from the request"""
        if not parsed["amount"]:
            return "amount"
        if not parsed["purpose"]:
            return "purpose"
        if not parsed["wallet"]:
            return "wallet"
        return None

    def _generate_question_reply(self, tweet_data: Dict, missing: str) -> str:
        """Generate reply asking for missing information"""
        author = tweet_data["author"]

        if missing == "amount":
            return (
                f"@{author} How much do you need to raise? (e.g., $500, $1000, $5000)"
            )
        elif missing == "purpose":
            return f"@{author} What will the funds be used for?"
        elif missing == "wallet":
            return f"""@{author} What wallet address should receive the funds?

Reply with:
• Your wallet: 0x...
• Or type 'create' and I'll generate one for you"""

        return f"@{author} I need more information to create your campaign."

    def _generate_success_reply(self, tweet_data: Dict, campaign: Dict) -> str:
        """Generate success reply with campaign link"""
        author = tweet_data["author"]
        campaign_id = campaign["id"]
        goal = campaign["goal"]

        # Use localhost for testing, update to production URL later
        campaign_url = f"http://localhost:3000/campaigns/{campaign_id}"

        reply = f"""@{author} Campaign created! 🚀

🎯 Goal: ${goal:,.2f}
🔗 Campaign: {campaign_url}

Support this fundraising by sharing or donating!

Your wallet: {campaign.get("wallet_address", "Will be generated")}

#GenesisFund"""

        return reply

    async def _create_campaign(self, tweet_data: Dict, parsed: Dict) -> Dict:
        """Create campaign via Genesis API"""

        # Handle wallet creation if needed
        wallet_address = parsed["wallet"]
        if not wallet_address:
            wallet_address = await self._generate_wallet(parsed["author"])

        # Get or create agent
        agent_data = await self._get_or_create_agent(
            twitter_handle=parsed["author"],
            twitter_name=parsed["author_name"],
            wallet_address=wallet_address,
        )

        # Prepare campaign data
        campaign_data = {
            "agent_id": agent_data["id"],
            "title": self._generate_campaign_title(parsed["purpose"]),
            "description": parsed["purpose"],
            "goal": parsed["amount"],
            "deadline": None,  # Open-ended by default
            "source_message": {
                "platform": "twitter",
                "author_handle": parsed["author"],
                "author_name": parsed["author_name"],
                "content": parsed["tweet_text"],
                "url": parsed["tweet_url"],
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

        # Create campaign via API
        response = requests.post(
            f"{self.platform_api}/campaigns", json=campaign_data, timeout=10
        )

        if response.status_code != 201:
            raise Exception(f"API Error: {response.text}")

        campaign = response.json()
        campaign["wallet_address"] = wallet_address

        return campaign

    def _generate_campaign_title(self, purpose: str) -> str:
        """Generate a campaign title from purpose"""
        if not purpose:
            return "Fundraising Campaign"

        # Take first 50 chars, remove special chars
        title = re.sub(r"[^\w\s]", "", purpose[:50]).strip()
        return title if title else "Fundraising Campaign"

    async def _generate_wallet(self, twitter_handle: str) -> str:
        """Generate embedded wallet for user via Privy"""
        # Call backend API to create Privy wallet
        response = requests.post(
            f"{self.platform_api}/wallets/privy/create",
            params={"user_id": twitter_handle, "twitter_handle": twitter_handle},
            timeout=10,
        )

        if response.status_code != 201:
            raise Exception(f"Failed to create Privy wallet: {response.text}")

        wallet_data = response.json()
        return wallet_data["address"]

    async def _get_or_create_agent(
        self, twitter_handle: str, twitter_name: str, wallet_address: str
    ) -> Dict:
        """Get existing agent or create new one"""

        # Try to find existing agent by Twitter handle
        response = requests.get(
            f"{self.platform_api}/agents",
            params={"twitter_handle": twitter_handle},
            timeout=10,
        )

        if response.status_code == 200:
            agents = response.json()
            if agents and len(agents) > 0:
                return agents[0]

        # Create new agent
        agent_data = {
            "address": wallet_address,
            "name": twitter_name,
            "description": f"Agent registered via Twitter: @{twitter_handle}",
            "twitter_handle": twitter_handle,
        }

        response = requests.post(
            f"{self.platform_api}/agents", json=agent_data, timeout=10
        )

        if response.status_code != 201:
            raise Exception(f"Failed to create agent: {response.text}")

        return response.json()


# Example usage in OpenClaw agent:
"""
from capabilities.genesis_fundraising import GenesisFundraisingCapability

# Initialize
genesis = GenesisFundraisingCapability(agent, platform_api="http://localhost:8000")

# In your Twitter mention handler:
async def on_mention(tweet):
    reply = await genesis.handle_twitter_mention({
        'id': tweet.id,
        'text': tweet.text,
        'author': tweet.author,
        'author_name': tweet.author_name,
        'url': tweet.url
    })
    
    if reply:
        await agent.tweet_reply(tweet.id, reply)
"""
