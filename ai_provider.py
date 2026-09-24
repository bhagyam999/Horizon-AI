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
        self.last_usage_tokens = 0
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

    @property
    def enabled(self) -> bool:
        """Whether Gemini has a usable API key configured."""
        return bool(self.api_key)

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
                    usage=data.get("usageMetadata") or {}
                    self.last_usage_tokens=int(usage.get("totalTokenCount") or 0)
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
            "configured_keys": 1 if self.api_key else 0,
            "active_key": 1 if self.api_key else None,
            "configured_model": self.preferred_model,
            "active_model": self.active_model,
            "available_models": self.available_models,
            "model_statuses": statuses,
            "last_error": self.last_error,
        }


class OpenAICompatibleProvider:
    """Small OpenAI-compatible client for Grok and OpenRouter."""

    def __init__(self, name: str, api_key_env: str, base_url: str, model_env: str, default_model: str, aliases: tuple[str, ...] = ()):
        self.name=name
        self.api_key=os.getenv(api_key_env,"").strip()
        if not self.api_key:
            for alias in aliases:
                self.api_key=os.getenv(alias,"").strip()
                if self.api_key:
                    break
        self.base_url=base_url.rstrip("/")
        self.model=os.getenv(model_env,default_model).strip()
        self.last_error=""
        self.last_usage_tokens=0

    @property
    def enabled(self):
        return bool(self.api_key)

    async def generate(self, system: str, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError(f"{self.name} API key is not configured")
        timeout=aiohttp.ClientTimeout(total=TIMEOUT)
        payload={
            "model":self.model,
            "messages":[{"role":"system","content":system},{"role":"user","content":prompt}],
            "max_tokens":int(os.getenv("AI_MAX_OUTPUT_TOKENS","800")),
        }
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
                usage=data.get("usage") or {}
                self.last_usage_tokens=int(usage.get("total_tokens") or 0)
                choices=data.get("choices") or []
                text=(choices[0].get("message",{}).get("content","") if choices else "").strip()
                if not text:
                    raise RuntimeError(f"{self.name} returned no visible answer: {body[:800]}")
                self.last_error=""
                return text


class DailyTokenBudget:
    """Persistent per-provider daily token guard. Reset is 17:30 IST."""
    def __init__(self):
        self.path=os.getenv("AI_USAGE_FILE", os.path.join(os.path.dirname(__file__), "ai_usage.json"))
        self.limit=int(os.getenv("AI_DAILY_TOKEN_LIMIT","100000"))
        self._lock=asyncio.Lock()
        self.data={}

    @staticmethod
    def period_key():
        from datetime import datetime, timedelta, timezone
        ist=timezone(timedelta(hours=5,minutes=30))
        now=datetime.now(ist)
        if (now.hour,now.minute) < (17,30):
            now-=timedelta(days=1)
        return now.strftime("%Y-%m-%d")

    async def _load(self):
        if self.data:
            return
        try:
            with open(self.path,"r",encoding="utf-8") as f:
                self.data=json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            self.data={}

    async def remaining(self, provider):
        async with self._lock:
            await self._load()
            used=int(self.data.get(self.period_key(),{}).get(provider,0))
            return max(0,self.limit-used)

    async def can_spend(self, provider, estimated_tokens):
        return (await self.remaining(provider)) >= max(1,int(estimated_tokens))

    async def add(self, provider, tokens):
        async with self._lock:
            await self._load()
            key=self.period_key()
            row=self.data.setdefault(key,{})
            row[provider]=int(row.get(provider,0))+max(0,int(tokens))
            for old in sorted(list(self.data))[:-7]:
                self.data.pop(old,None)
            tmp=self.path+".tmp"
            os.makedirs(os.path.dirname(self.path) or ".",exist_ok=True)
            with open(tmp,"w",encoding="utf-8") as f:
                json.dump(self.data,f)
            os.replace(tmp,self.path)

    async def status(self):
        key=self.period_key()
        used=self.data.get(key,{})
        return {"date":key,"limit":self.limit,"used":dict(used)}


class AIProvider:
    """Failover: Gemini -> Grok -> Gemini recovery -> OpenRouter emergency."""
    def __init__(self):
        self.gemini=GeminiProvider()
        self.grok=OpenAICompatibleProvider("Grok","XAI_API_KEY","https://api.x.ai/v1","GROK_MODEL","grok-4.7",aliases=("GROK_API_KEY","XAI_API_KEY"))
        self.openrouter=OpenAICompatibleProvider("OpenRouter","OPENROUTER_API_KEY","https://openrouter.ai/api/v1","OPENROUTER_MODEL","openrouter/free")
        self.budget=DailyTokenBudget()
        self.last_provider="Gemini"
        self.last_error=""

    @property
    def enabled(self):
        return any(getattr(p,"enabled",False) for p in (self.gemini,self.grok,self.openrouter))

    @property
    def model(self):
        if self.last_provider=="Gemini": return self.gemini.active_model
        if self.last_provider=="Grok": return self.grok.model
        return self.openrouter.model

    @staticmethod
    def estimate_tokens(system, prompt):
        chars=len(system)+len(prompt)
        return max(1,(chars+3)//4)+int(os.getenv("AI_MAX_OUTPUT_TOKENS","800"))

    async def _try(self, provider, system, prompt):
        estimate=self.estimate_tokens(system,prompt)
        name="Gemini" if provider is self.gemini else provider.name
        if not await self.budget.can_spend(name,estimate):
            raise RuntimeError(f"{name} daily token budget exhausted.")
        if provider is self.gemini:
            result=await provider.ask(f"{system}\n\nUser message:\n{prompt}")
            used=provider.last_usage_tokens or estimate
        else:
            result=await provider.generate(system,prompt)
            used=provider.last_usage_tokens or estimate
        await self.budget.add(name,used)
        return result

    async def generate(self, system: str, prompt: str) -> str:
        errors=[]
        if self.gemini.enabled:
            try:
                result=await self._try(self.gemini,system,prompt)
                self.last_provider="Gemini"; self.last_error=""
                return result
            except Exception as exc:
                errors.append(f"Gemini: {exc}")
                self.gemini.last_error=str(exc)
        if self.grok.enabled:
            try:
                result=await self._try(self.grok,system,prompt)
                self.last_provider="Grok"; self.last_error=""
                return result
            except Exception as exc:
                errors.append(f"Grok: {exc}")
                self.grok.last_error=str(exc)
        if self.gemini.enabled:
            try:
                result=await self._try(self.gemini,system,prompt)
                self.last_provider="Gemini"; self.last_error=""
                return result
            except Exception as exc:
                errors.append(f"Gemini recovery: {exc}")
                self.gemini.last_error=str(exc)
        if self.openrouter.enabled:
            try:
                result=await self._try(self.openrouter,system,prompt)
                self.last_provider="OpenRouter"; self.last_error=""
                return result
            except Exception as exc:
                errors.append(f"OpenRouter: {exc}")
                self.openrouter.last_error=str(exc)
        self.last_error=" | ".join(errors) or "No AI provider API keys are configured."
        raise RuntimeError(f"All AI providers failed. {self.last_error}")

    async def status(self):
        lines=[]
        for provider in (self.gemini,self.grok,self.openrouter):
            name="Gemini" if provider is self.gemini else provider.name
            model=provider.active_model if provider is self.gemini else provider.model
            remaining=await self.budget.remaining(name)
            lines.append(f"• {name} — {'configured' if provider.enabled else 'not configured'} — {model} — {remaining:,} tokens remaining today")
            if provider.last_error: lines.append(f"  Last error: {provider.last_error[:250]}")
        return self.enabled, "Failover order: Gemini → Grok → Gemini recovery → OpenRouter emergency\nDaily token limit per provider: " + f"{self.budget.limit:,}\n" + "\n".join(lines)

    async def usage_status(self):
        return await self.budget.status()

_provider=AIProvider()

_provider=AIProvider()

async def ask_gemini(prompt: str):
    return await _provider.generate("You are Horizon, a helpful Discord AI assistant.",prompt)

async def get_ai_response(prompt: str):
    return await _provider.generate("You are Horizon, a helpful Discord AI assistant.",prompt)

async def ai_status():
    return {"provider":_provider.last_provider,"model":_provider.model,"last_error":_provider.last_error}

async def list_gemini_models():
    return await _provider.gemini.model_names()