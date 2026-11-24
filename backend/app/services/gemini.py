import httpx
from fastapi import HTTPException
from app.core.config import settings


class GeminiService:
    def __init__(self):
        if not settings.gemini_api_key:
            raise HTTPException(503, "Gemini is not configured. Set GEMINI_API_KEY.")
        self.base = settings.gemini_api_base.rstrip("/")
        self.key = settings.gemini_api_key

    async def _post(self, path: str, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(f"{self.base}/{path}", params={"key": self.key}, json=payload)
        if response.is_error:
            detail = "Gemini request failed"
            try:
                detail = response.json().get("error", {}).get("message", detail)
            except ValueError:
                pass
            raise HTTPException(502, detail)
        return response.json()

    async def embed(self, text: str) -> list[float]:
        data = await self._post(f"models/{settings.gemini_embedding_model}:embedContent", {"model": f"models/{settings.gemini_embedding_model}", "content": {"parts": [{"text": text}]}, "outputDimensionality": 768})
        values = data.get("embedding", {}).get("values", [])
        if len(values) != 768:
            raise HTTPException(502, "Gemini returned an embedding with an unexpected dimension")
        return values

    async def generate(self, prompt: str) -> str:
        data = await self._post(f"models/{settings.gemini_model}:generateContent", {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2}})
        candidates = data.get("candidates", [])
        if candidates:
            candidate = candidates[0]
            parts = candidate.get("content", {}).get("parts", [])
            answer = "".join(part.get("text", "") for part in parts).strip()
            if answer:
                return answer

        raise HTTPException(502, "Gemini returned no text")
