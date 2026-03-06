import os
import json
from typing import List, Dict, Any

import httpx
from dotenv import load_dotenv

load_dotenv()

INFERENCE_KEY = os.getenv("DIGITALOCEAN_INFERENCE_KEY", "")
MODEL_NAME = os.getenv("DO_INFERENCE_MODEL", "openai-gpt-oss-120b")
BASE_ENDPOINT = os.getenv("DO_INFERENCE_ENDPOINT", "https://inference.do-ai.run/v1")

if not INFERENCE_KEY:
    INFERENCE_KEY = "missing"


class AIService:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {INFERENCE_KEY}",
            "Content-Type": "application/json",
        }
        self.chat_url = f"{BASE_ENDPOINT}/chat/completions"
        self.model_name = MODEL_NAME
        self.client = httpx.AsyncClient(timeout=30.0)

    async def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = await self.client.post(
            self.chat_url, headers=self.headers, json=payload
        )
        response.raise_for_status()
        return response.json()

    async def categorize(self, description: str) -> Dict[str, Any]:
        prompt = (
            f"Classify the following bank transaction description into one of the standard "
            f"expense categories (e.g., Grocery, Transport, Entertainment, Utilities, "
            f"Subscription, Salary, Other). Return a JSON object with keys 'category', "
            f"'confidence' and optionally 'reason'.\n\nDescription: \"{description}\""
        )
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": 256,
            "temperature": 0.0,
        }
        result = await self._post(payload)
        choice = result.get("choices", [{}])[0]
        message = choice.get("message", {})
        try:
            content = message.get("content", "")
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "category": content.strip(),
                "confidence": 0.0,
                "reason": {"error": "invalid json"},
            }

    async def generate_savings_plan(
        self, transactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        summary = json.dumps(transactions)
        system_prompt = (
            "You are a personal finance assistant. Given a JSON array of transaction objects with fields "
            "'date', 'amount', 'category' (already AI-predicted), generate 3-5 actionable savings "
            "recommendations. Each recommendation should include a short description, a confidence "
            "score (0-1) and an estimated monthly savings amount. Return a JSON object with a "
            "top-level key 'recommendations' containing a list of recommendation objects."
        )
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": summary},
            ],
            "max_completion_tokens": 512,
            "temperature": 0.2,
        }
        result = await self._post(payload)
        choice = result.get("choices", [{}])[0]
        try:
            return json.loads(choice.get("message", {}).get("content", "{}"))
        except json.JSONDecodeError:
            return {"recommendations": []}

    async def close(self) -> None:
        await self.client.aclose()


ai_service = AIService()
