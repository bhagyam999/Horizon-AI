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
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
AGENT_ONLY_MODELS = {
    "deep-research-pro-preview-12-2025",
    "deep-research-preview-04-2026",
    "deep-research-max-preview-04-2026",
    "antigravity-preview-05-2026",
}
TIMEOUT = float(os.getenv("GEMINI_HTTP_TIMEOUT", os.getenv("GEMINI_TIMEOUT", "25")))
RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "1"))
REFRESH_SECONDS = int(os.getenv("GEMINI_MODEL_REFRESH_SECONDS", "300"))


class GeminiProvider:
    def __init__(self):
        # One Gemini key only. Provider-level failover is handled by AIProvider:
        # Gemini -> Groq -> OpenRouter.
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.preferred_model = self.normalize(DEFAULT_MODEL)
        if self.is_agent_model(self.preferred_model):
            self.preferred_model = "gemini-2.5-flash"
        self.active_model = self.preferred_model
        self.available_models: list[str] = []
        self.last_refresh = 0.0
        self.last_error = ""
        self.model_health: dict[str, dict[str, Any]] = {}


    @staticmethod
    def is_agent_model(model: str) -> bool:
        model = (model or "").strip()
        if model.startswith("models/"):
            model = model[7:]
        return model in AGENT_ONLY_MODELS or model.startswith("deep-research-") or model.startswith("antigravity-")

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
            if name and "generateContent" in methods and not self.is_agent_model(name):
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
        for name in self.available_models:
            previous=self.model_health.get(name)
            if not previous or previous.get("status") in {"unavailable","unknown"}:
                self.model_health[name]={"status":"available","detail":"Listed by Gemini and supports generation."}
        if self.available_models and self.active_model not in self.available_models:
            self.active_model = self.available_models[0]
        return self.available_models

    def _mark_model(self, model: str, status: str, detail: str):
        self.model_health[self.normalize(model)]={"status":status,"detail":detail,"checked_at":time.time()}

    async def _request(self, model: str, prompt: str) -> str:
        model = self.normalize(model)
        if self.is_agent_model(model):
            raise RuntimeError(
                f"Gemini agent-only model {model!r} cannot be used as a normal chat model; falling back to a standard Gemini model."
            )
        timeout = aiohttp.ClientTimeout(total=TIMEOUT)

        # Gemini's newer models can be Interaction-only. Try the legacy
        # generateContent endpoint first for older models, then transparently
        # switch to the Interactions API when Google tells us that the model
        # requires it.
        url = f"{API_BASE}/models/{model}:generateContent"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "1200")),
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=self.headers(), json=payload) as response:
                body = await response.text()
                if response.status == 200:
                    self._mark_model(model, "available", "Responded successfully.")
                    data: dict[str, Any] = json.loads(body)
                    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    answer_parts = [
                        p.get("text", "")
                        for p in parts
                        if p.get("text") and not p.get("thought", False)
                    ]
                    text = "".join(answer_parts).strip()
                    if not text:
                        raise RuntimeError(f"Gemini returned no visible answer text: {json.dumps(data)[:800]}")
                    return text

                # Newer Gemini models may reject generateContent with:
                # "This model only supports Interactions API."
                if response.status == 400 and "Interactions API" in body:
                    interaction_url = f"{API_BASE}/interactions"
                    interaction_payload = {
                        "model": model,
                        "input": prompt,
                        "generation_config": {
                            "max_output_tokens": int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "1200")),
                        },
                        "store": False,
                    }
                    async with session.post(
                        interaction_url,
                        headers=self.headers(),
                        json=interaction_payload,
                    ) as interaction_response:
                        interaction_body = await interaction_response.text()
                        if interaction_response.status != 200:
                            raise RuntimeError(
                                f"Gemini Interactions HTTP {interaction_response.status}: "
                                f"{interaction_body[:800]}"
                            )
                        interaction_data: dict[str, Any] = json.loads(interaction_body)
                        # Interactions responses use structured output steps.
                        answer_parts: list[str] = []
                        for step in interaction_data.get("steps", []):
                            if step.get("type") != "model_output":
                                continue
                            for part in step.get("content", []):
                                if part.get("type") == "text" and part.get("text"):
                                    answer_parts.append(part["text"])
                        text = "".join(answer_parts).strip()
                        if not text:
                            # Also support the simplified output shape if returned.
                            text = str(interaction_data.get("output_text", "")).strip()
                        if not text:
                            raise RuntimeError(
                                f"Gemini Interactions returned no visible answer: "
                                f"{json.dumps(interaction_data)[:800]}"
                            )
                        return text

                if response.status == 429:
                    self._mark_model(model, "rate_limited", "HTTP 429: quota or rate limit reached.")
                    raise RuntimeError(f"Model {model} is rate limited (HTTP 429).")

                if response.status in {400, 404}:
                    self._mark_model(model, "unavailable", f"HTTP {response.status}: model cannot be used with this request.")
                elif response.status in {401, 403}:
                    self._mark_model(model, "auth_error", f"HTTP {response.status}: API key/access issue.")
                elif response.status >= 500:
                    self._mark_model(model, "temporarily_unavailable", f"HTTP {response.status}: Gemini server error.")
                raise RuntimeError(f"Gemini HTTP {response.status}: {body[:800]}")

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
        statuses=[]
        for name in self.available_models:
            health=self.model_health.get(name, {})
            statuses.append({"model":name,"status":health.get("status","available"),"detail":health.get("detail","Listed by Gemini and supports generation.")})
        return {
            "provider": "Gemini",
            "configured_keys": len([REMOVED_MULTI_GEMINI_KEYS]),
            "active_key": self.key_index + 1 if self.api_keys else None,
            "configured_model": self.preferred_model,
            "active_model": self.active_model,
            "available_models": self.available_models,
            "model_statuses": statuses,
            "last_error": self.last_error,
        }


class OpenAICompatibleProvider:
    """Small OpenAI-compatible client for Groq and OpenRouter."""

    def __init__(self, name: str, api_key_env: str, base_url: str, model_env: str, default_model: str):
        self.name=name
        self.api_key=os.getenv(api_key_env,"").strip()
        self.base_url=base_url.rstrip("/")
        self.model=os.getenv(model_env,default_model).strip()
        self.last_error=""

    @property
    def enabled(self):
        return bool(self.api_key)

    async def generate(self, system: str, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError(f"{self.name} API key is not configured")
        timeout=aiohttp.ClientTimeout(total=TIMEOUT)
        payload={"model":self.model,"messages":[{"role":"system","content":system},{"role":"user","content":prompt}],"max_tokens":int(os.getenv("AI_MAX_OUTPUT_TOKENS","1200"))}
        headers={"Content-Type":"application/json","Authorization":f"Bearer {self.api_key}"}
        if self.name=="OpenRouter":
            headers["HTTP-Referer"]=os.getenv("OPENROUTER_HTTP_REFERER","https://discord.com")
            headers["X-Title"]=os.getenv("OPENROUTER_X_TITLE","Horizon")
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{self.base_url}/chat/completions",headers=headers,json=payload) as response:
                body=await response.text()
                if response.status!=200:
                    raise RuntimeError(f"{self.name} HTTP {response.status}: {body[:800]}")
                data=json.loads(body)
                choices=data.get("choices") or []
                text=(choices[0].get("message",{}).get("content","") if choices else "").strip()
                if not text:
                    raise RuntimeError(f"{self.name} returned no visible answer: {body[:800]}")
                self.last_error=""
                return text


class AIProvider:
    """Horizon AI failover chain: Gemini -> Groq -> OpenRouter."""

    def __init__(self):
        self.gemini=GeminiProvider()
        self.groq=OpenAICompatibleProvider("Groq","GROQ_API_KEY","https://api.groq.com/openai/v1","GROQ_MODEL","openai/gpt-oss-120b")
        self.openrouter=OpenAICompatibleProvider("OpenRouter","OPENROUTER_API_KEY","https://openrouter.ai/api/v1","OPENROUTER_MODEL","openrouter/free")
        self.providers=[self.gemini,self.groq,self.openrouter]
        self.last_provider="Gemini"
        self.last_error=""

    @property
    def enabled(self):
        return any(getattr(p,"enabled",False) for p in self.providers)

    @property
    def model(self):
        if self.last_provider=="Gemini": return self.gemini.active_model
        if self.last_provider=="Groq": return self.groq.model
        return self.openrouter.model

    @property
    def provider_name(self):
        return self.last_provider

    async def generate(self, system: str, prompt: str) -> str:
        errors=[]
        for provider in self.providers:
            if not getattr(provider,"enabled",False): continue
            try:
                if provider is self.gemini: result=await provider.ask(f"{system}\n\nUser message:\n{prompt}")
                else: result=await provider.generate(system,prompt)
                self.last_provider=provider.name if provider is not self.gemini else "Gemini"
                self.last_error=""
                return result
            except Exception as exc:
                provider.last_error=str(exc)
                errors.append(f"{provider.name if provider is not self.gemini else 'Gemini'}: {exc}")
        self.last_error=" | ".join(errors) or "No AI provider API keys are configured."
        raise RuntimeError(f"All AI providers failed. {self.last_error}")

    async def status(self):
        lines=[]
        for provider in self.providers:
            name=provider.name if provider is not self.gemini else "Gemini"
            model=provider.active_model if provider is self.gemini else provider.model
            lines.append(f"• {name} — {'configured' if provider.enabled else 'not configured'} — {model}")
            if provider.last_error: lines.append(f"  Last error: {provider.last_error[:250]}")
        return self.enabled, "Failover order: Gemini → Groq → OpenRouter\n" + "\n".join(lines)

_provider=AIProvider()

async def ask_gemini(prompt: str):
    return await _provider.generate("You are Horizon, a helpful Discord AI assistant.",prompt)

async def get_ai_response(prompt: str):
    return await _provider.generate("You are Horizon, a helpful Discord AI assistant.",prompt)

async def ai_status():
    return {"provider":_provider.last_provider,"model":_provider.model,"last_error":_provider.last_error}

async def list_gemini_models():
    return await _provider.gemini.model_names()