import httpx

from src.config import get_settings

settings = get_settings()


async def process_payment(
    amount: float,
    token_type: str,
    recipient_address: str,
    donor_address: str,
) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.X402_API_URL}/payments",
            headers={"Authorization": f"Bearer {settings.X402_API_KEY}"},
            json={
                "amount": amount,
                "token_type": token_type,
                "recipient": recipient_address,
                "donor": donor_address,
            },
        )
        response.raise_for_status()
        data: dict[str, str] = response.json()
        return str(data["tx_hash"])


async def confirm_payment(tx_hash: str) -> bool:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.X402_API_URL}/payments/{tx_hash}",
            headers={"Authorization": f"Bearer {settings.X402_API_KEY}"},
        )
        response.raise_for_status()
        data: dict[str, str] = response.json()
        return str(data["status"]) == "confirmed"
