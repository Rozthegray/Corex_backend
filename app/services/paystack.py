import os
import httpx
from fastapi import HTTPException
from app.core.config import settings

PAYSTACK_BASE_URL = "https://api.paystack.co"

async def initialize_split_payment(email: str, amount_kobo: int, reference: str, subaccount_code: str) -> str:
    """
    Initializes a Paystack transaction with a strict 80/20 split.
    The transaction_charge is the flat amount kept in the main platform reserve.
    The rest is disbursed to the subaccount (the Department President).
    """
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    # 500 NGN = 50000 kobo. 400 NGN = 40000 kobo (80% Reserve for Corex AI hosting/LLM costs)
    transaction_charge = settings.PLATFORM_TRANSACTION_CHARGE_KOBO 
    
    payload = {
        "email": email,
        "amount": amount_kobo,
        "reference": reference,
        "subaccount": subaccount_code,
        "transaction_charge": transaction_charge,
        "callback_url": "https://yourdomain.com/dashboard/settings/billing"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PAYSTACK_BASE_URL}/transaction/initialize",
            json=payload,
            headers=headers,
            timeout=10.0
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to initialize Paystack gateway")
            
        data = response.json()
        return data["data"]["authorization_url"]

async def create_president_subaccount(bank_code: str, account_number: str, business_name: str) -> str:
    """
    Creates a new Paystack subaccount for the incoming Department President.
    Returns the subaccount_code used for split routing.
    """
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "business_name": business_name,
        "settlement_bank": bank_code,
        "account_number": account_number,
        "percentage_charge": 0 # We use flat transaction_charge on initialize instead
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PAYSTACK_BASE_URL}/subaccount",
            json=payload,
            headers=headers
        )
        data = response.json()
        
        if not data.get("status"):
            raise HTTPException(status_code=400, detail="Invalid bank details provided to Paystack")
            
        return data["data"]["subaccount_code"]