"""
Genesis Twitter Bot - Browser-based approach using twikit
No paid Twitter API needed - uses browser cookies
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Optional
import requests

# Try to import twikit, if not available we'll create a stub
try:
    from twikit import Client

    TWIKIT_AVAILABLE = True
except ImportError:
    TWIKIT_AVAILABLE = False
    print("Warning: twikit not installed. Install with: pip install twikit")


class GenesisTwitterBot:
    """
    Twitter bot that monitors @Genesis mentions using browser cookies
    No paid API required - authenticates as a regular user
    """

    def __init__(self, platform_api: str = "http://localhost:8000"):
        self.platform_api = platform_api
        self.client: Optional[Client] = None
        self.username = os.getenv("TWITTER_USERNAME", "")
        self.password = os.getenv("TWITTER_PASSWORD", "")
        self.cookies_file = "twitter_cookies.json"
        self.last_mention_id: Optional[str] = None

    async def initialize(self):
        """Initialize Twitter client with cookies or login"""
        if not TWIKIT_AVAILABLE:
            raise ImportError("twikit library not installed. Run: pip install twikit")

        self.client = Client()

        # Try to load existing cookies
        if os.path.exists(self.cookies_file):
            print(f"Loading cookies from {self.cookies_file}")
            try:
                # Try standard twikit format first
                self.client.load_cookies(self.cookies_file)
            except Exception as e:
                print(f"Standard cookie load failed, trying Firefox format...")
                # Try to load Firefox exported format
                await self._load_firefox_cookies()
        else:
            # Login with credentials
            if not self.username or not self.password:
                raise ValueError(
                    "TWITTER_USERNAME and TWITTER_PASSWORD env vars required for first login"
                )

            print(f"Logging in as {self.username}...")
            await self.client.login(auth_info_1=self.username, password=self.password)
            # Save cookies for future runs
            self.client.save_cookies(self.cookies_file)
            print(f"Cookies saved to {self.cookies_file}")

    async def _load_firefox_cookies(self):
        """Load cookies from Firefox export format"""
        import json

        with open(self.cookies_file, "r") as f:
            cookies_data = json.load(f)

        # Convert Firefox format to twikit format
        cookie_dict = {}
        for cookie in cookies_data:
            name = cookie.get("name")
            value = cookie.get("value")
            if name and value:
                cookie_dict[name] = value

        # Set cookies on the client
        for name, value in cookie_dict.items():
            self.client.set_cookie(name, value)

        print(f"Loaded {len(cookie_dict)} cookies from Firefox format")

    async def start_monitoring(self, check_interval: int = 60):
        """Start monitoring @Genesis mentions"""
        print("Starting Genesis Twitter Bot...")
        print(f"Monitoring for @Genesis mentions every {check_interval} seconds")

        while True:
            try:
                await self._check_mentions()
            except Exception as e:
                print(f"Error checking mentions: {e}")

            await asyncio.sleep(check_interval)

    async def _check_mentions(self):
        """Check for new @Genesis mentions"""
        # Search for mentions
        query = "@Genesis"

        try:
            tweets = await self.client.search_tweet(query, "Latest")

            for tweet in tweets:
                # Skip if we've already processed this tweet
                if self.last_mention_id and tweet.id <= self.last_mention_id:
                    continue

                # Skip our own tweets
                if tweet.user.name == self.username:
                    continue

                print(f"\nNew mention from @{tweet.user.name}: {tweet.text[:100]}...")

                # Process the mention
                await self._process_mention(tweet)

                # Update last processed ID
                self.last_mention_id = tweet.id

        except Exception as e:
            print(f"Error fetching mentions: {e}")

    async def _process_mention(self, tweet):
        """Process a single mention"""
        from .genesis_fundraising import GenesisFundraisingCapability

        # Initialize the fundraising capability
        genesis = GenesisFundraisingCapability(None, self.platform_api)

        # Prepare tweet data
        tweet_data = {
            "id": tweet.id,
            "text": tweet.text,
            "author": tweet.user.name,
            "author_name": tweet.user.name,
            "url": f"https://twitter.com/{tweet.user.name}/status/{tweet.id}",
            "created_at": tweet.created_at
            if hasattr(tweet, "created_at")
            else datetime.utcnow().isoformat(),
        }

        # Handle the mention
        try:
            reply_text = await genesis.handle_twitter_mention(tweet_data)

            if reply_text:
                # Reply to the tweet
                await self._reply_to_tweet(tweet.id, reply_text)
                print(f"Replied: {reply_text[:100]}...")
        except Exception as e:
            print(f"Error processing mention: {e}")
            # Send error reply
            error_reply = (
                f"@{tweet.user.name} Sorry, I encountered an error. Please try again."
            )
            await self._reply_to_tweet(tweet.id, error_reply)

    async def _reply_to_tweet(self, tweet_id: str, text: str):
        """Reply to a specific tweet"""
        try:
            await self.client.create_tweet(text, reply_to=tweet_id)
        except Exception as e:
            print(f"Error replying to tweet: {e}")

    async def post_campaign_update(self, campaign_id: str, message: str):
        """Post an update about a campaign"""
        try:
            tweet_text = f"🚀 Campaign Update!\n\n{message}\n\nView: http://localhost:3000/campaign/{campaign_id}"
            await self.client.create_tweet(tweet_text)
            print(f"Posted campaign update for {campaign_id}")
        except Exception as e:
            print(f"Error posting update: {e}")


# Main entry point
async def main():
    """Run the Genesis Twitter Bot"""
    bot = GenesisTwitterBot(
        platform_api=os.getenv("PLATFORM_API", "http://localhost:8000")
    )

    # Initialize (login or load cookies)
    await bot.initialize()

    # Start monitoring
    await bot.start_monitoring(check_interval=60)


if __name__ == "__main__":
    asyncio.run(main())
