from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any

import aiohttp
from dotenv import load_dotenv

load_dotenv()

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
TIMEOUT = float(os.getenv("GEMINI_HTTP_TIMEOUT", os.getenv("GEMINI_TIMEOUT", "12")))
RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "0"))
REFRESH_SECONDS = int(os.getenv("GEMINI_MODEL_REFRESH_SECONDS", "300"))


class GeminiProvider:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.preferred_model = self.normalize(DEFAULT_MODEL)
        self.active_model = self.preferred_model
        self.available_models: list[str] = []
        self.last_refresh = 0.0
        self.last_error = ""

    @staticmethod
    def normalize(model: str) -> str:
        model = (model or "").strip()
        if model.startswith("models/"):
            model = model[7:]
        return model

    def headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json", "x-goog-api-key": self.api_key}

    async def refresh_models(self, force: bool = False) -> list[str]:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is missing from .env")
        if (not force and self.available_models
                and time.monotonic() - self.last_refresh < REFRESH_SECONDS):
            return self.available_models

        timeout = aiohttp.ClientTimeout(total=TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{API_BASE}/models", headers=self.headers()) as response:
                body = await response.text()
                if response.status != 200:
                    raise RuntimeError(
                        f"Gemini model discovery failed ({response.status}): {body[:600]}"
                    )
                data = json.loads(body)

        models: list[str] = []
        for item in data.get("models", []):
            name = self.normalize(item.get("name", ""))
            methods = item.get("supportedGenerationMethods", [])
            if name and "generateContent" in methods:
                models.append(name)

        # Prefer the configured model, then sensible known aliases, then anything
        # the API key exposes. This gives /ask real automatic model failover.
        priority = [
            self.active_model,
            self.preferred_model,
            "gemini-flash-latest",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-3.6-flash",
            "gemini-3.7-flash",
        ]
        self.available_models = []
        for name in priority + models:
            name = self.normalize(name)
            if name in models and name not in self.available_models:
                self.available_models.append(name)

        self.last_refresh = time.monotonic()
        if self.available_models and self.active_model not in self.available_models:
            self.active_model = self.available_models[0]
        return self.available_models

    async def _request(self, model: str, prompt: str) -> str:
        model = self.normalize(model)
        url = f"{API_BASE}/models/{model}:generateContent"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "1200"))
            },
        }
        timeout = aiohttp.ClientTimeout(total=TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=self.headers(), json=payload) as response:
                body = await response.text()
                if response.status != 200:
                    raise RuntimeError(f"Gemini HTTP {response.status}: {body[:800]}")
                data: dict[str, Any] = json.loads(body)

        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts if p.get("text")).strip()
        if not text:
            raise RuntimeError(f"Gemini returned no text: {json.dumps(data)[:800]}")
        return text

    async def ask(self, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is missing from .env")

        # Cached model list keeps normal requests fast. If a model fails, force a
        # fresh list once and append any newly available models before giving up.
        try:
            models = await self.refresh_models()
        except Exception as exc:
            self.last_error = str(exc)
            models = []

        candidates: list[str] = []
        for model in [self.active_model, self.preferred_model, *models]:
            model = self.normalize(model)
            if model and model not in candidates:
                candidates.append(model)
        if not candidates:
            candidates = [self.preferred_model]

        last_error: Exception | None = None
        refreshed = False

        for model in candidates:
            for retry in range(RETRIES + 1):
                try:
                    result = await self._request(model, prompt)
                    self.active_model = model
                    self.last_error = ""
                    return result
                except Exception as exc:
                    last_error = exc
                    self.last_error = str(exc)
                    if not refreshed:
                        refreshed = True
                        try:
                            fresh = await self.refresh_models(force=True)
                            for fresh_model in fresh:
                                if fresh_model not in candidates:
                                    candidates.append(fresh_model)
                        except Exception:
                            pass
                    if retry < RETRIES:
                        await asyncio.sleep(0.25)

        raise RuntimeError(
            f"All available Gemini models failed. Last error: {last_error or 'unknown error'}"
        )

    async def model_names(self) -> list[str]:
        return await self.refresh_models(force=True)

    async def status_data(self) -> dict[str, Any]:
        try:
            await self.refresh_models()
        except Exception as exc:
            self.last_error = str(exc)
        return {
            "provider": "Gemini",
            "configured_model": self.preferred_model,
            "active_model": self.active_model,
            "available_models": self.available_models,
            "last_error": self.last_error,
        }


class AIProvider:
    """Bot-facing wrapper kept compatible with Horizon's bot.py interface."""

    def __init__(self):
        self.gemini = GeminiProvider()

    @property
    def enabled(self) -> bool:
        return bool(self.gemini.api_key)

    @property
    def model(self) -> str:
        return self.gemini.active_model

    @property
    def provider_name(self) -> str:
        return "Gemini"

    async def generate(self, system: str, prompt: str) -> str:
        combined = f"{system}\n\nUser message:\n{prompt}"
        return await self.gemini.ask(combined)

    async def status(self):
        data = await self.gemini.status_data()
        ok = bool(self.gemini.api_key) and bool(data["available_models"])
        detail = (
            f"Model: `{data['active_model']}`\n"
            f"Available models: {len(data['available_models'])}"
        )
        if data["last_error"]:
            detail += f"\nLast error: `{data['last_error'][:300]}`"
        return ok, detail


# Backwards-compatible helpers for any older Horizon modules.
_provider = GeminiProvider()

async def ask_gemini(prompt: str):
    return await _provider.ask(prompt)

async def get_ai_response(prompt: str):
    return await _provider.ask(prompt)

async def ai_status():
    return await _provider.status_data()

async def list_gemini_models():
    return await _provider.model_names()
