import os
import json
from typing import List, Dict, Any

import httpx
from pydantic import BaseSettings, Field

class AISettings(BaseSettings):
    inference_key: str = Field(..., env="DIGITALOCEAN_INFERENCE_KEY")
    model_name: str = Field(default="gpt-5-mini", env="DO_INFERENCE_MODEL")
    base_endpoint: str = Field(default="https://api.digitalocean.com/v1/engines", env="DO_INFERENCE_ENDPOINT")

    class Config:
        env_file = ".env"

settings = AISettings()

class AIService:
    """Thin wrapper around DigitalOcean Serverless Inference API.
    The service is deliberately small – each method builds the payload,
    sends an async request via httpx and returns the parsed JSON.
    """

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {settings.inference_key}",
            "Content-Type": "application/json",
        }
        # Example endpoint: https://api.digitalocean.com/v1/engines/<model>/completions
        self.completions_url = f"{settings.base_endpoint}/{settings.model_name}/completions"
        self.chat_url = f"{settings.base_endpoint}/{settings.model_name}/chat/completions"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def _post(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = await self.client.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    async def categorize(self, description: str) -> Dict[str, Any]:
        """Send a single transaction description to the model for categorization.
        The model is expected to return a JSON object with at least:
            - category (str)
            - confidence (float)
            - rationale (optional dict)
        """
        prompt = f"Classify the following bank transaction description into one of the standard expense categories (e.g., Grocery, Transport, Entertainment, Utilities, Subscription, Salary, Other). Return a JSON object with keys 'category', 'confidence' and optionally 'reason'.\n\nDescription: \"{description}\""
        payload = {
            "model": settings.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 150,
            "temperature": 0.0,
        }
        result = await self._post(self.chat_url, payload)
        # DigitalOcean returns a structure similar to OpenAI's chat API
        choice = result.get("choices", [{}])[0]
        message = choice.get("message", {})
        # The model should output a JSON string in the content
        try:
            content = message.get("content", "")
            return json.loads(content)
        except json.JSONDecodeError:
            # Fallback – return raw content as category with low confidence
            return {"category": content.strip(), "confidence": 0.0, "reason": {"error": "invalid json"}}

    async def generate_savings_plan(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Provide a savings‑plan recommendation based on a list of categorized transactions.
        The payload mirrors an OpenAI‑style chat request where the system prompt defines the task.
        """
        # Build a concise summary of spending to feed the model
        summary = json.dumps(transactions)
        system_prompt = (
            "You are a personal finance assistant. Given a JSON array of transaction objects with fields "
            "'date', 'amount', 'category' (already AI‑predicted), generate 3‑5 actionable savings recommendations. "
            "Each recommendation should include a short description, a confidence score (0‑1) and an estimated monthly savings amount. "
            "Return a JSON object with a top‑level key 'recommendations' containing a list of recommendation objects."
        )
        payload = {
            "model": settings.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": summary},
            ],
            "max_tokens": 500,
            "temperature": 0.2,
        }
        result = await self._post(self.chat_url, payload)
        choice = result.get("choices", [{}])[0]
        try:
            return json.loads(choice.get("message", {}).get("content", "{}"))
        except json.JSONDecodeError:
            return {"recommendations": []}

    async def close(self) -> None:
        await self.client.aclose()

# Provide a module‑level singleton for simplicity in route handlers
ai_service = AIService()
