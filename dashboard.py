import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from urllib.parse import urlencode

import aiohttp
from aiohttp import web

DISCORD_API = "https://discord.com/api/v10"


class Dashboard:
    """Unified Railway website/API server.

    The same Railway process serves the built Log Horizon website, Discord OAuth,
    Horizon AI, health, and the existing dashboard APIs. Secrets never enter the
    browser.
    """
    def __init__(self, bot):
        self.bot = bot
        self.runner = None
        self.site = None
        self.port = None
        self.web_root = Path(__file__).resolve().parent / "website_dist"
        self.sessions_secret = os.getenv("SESSION_SECRET", "").strip()

    def _base_url(self, request):
        configured = os.getenv("SITE_URL", "").strip().rstrip("/")
        if configured:
            return configured
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("x-forwarded-host", request.host)
        return f"{proto}://{host}"

    def _cookie(self, name, value, max_age=None):
        parts = [f"{name}={value}", "Path=/", "HttpOnly", "SameSite=Lax"]
        if max_age is not None:
            parts.append(f"Max-Age={max_age}")
        # Railway should be HTTPS in production. Local HTTP remains usable when debugging.
        if os.getenv("COOKIE_SECURE", "1") != "0":
            parts.append("Secure")
        return "; ".join(parts)

    def _sign(self, body):
        if not self.sessions_secret:
            raise RuntimeError("SESSION_SECRET is missing")
        return hmac.new(self.sessions_secret.encode(), body.encode(), hashlib.sha256).hexdigest()

    def _make_session(self, payload):
        body = __import__("base64").urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
        return f"{body}.{self._sign(body)}"

    def _parse_cookies(self, request):
        return {part.split("=", 1)[0]: part.split("=", 1)[1] for part in request.headers.get("Cookie", "").split("; ") if "=" in part}

    def _verify_session(self, request):
        token = self._parse_cookies(request).get("lh_session")
        if not token or not self.sessions_secret:
            return None
        try:
            body, sig = token.split(".", 1)
            expected = self._sign(body)
            if not hmac.compare_digest(sig, expected):
                return None
            padded = body + "=" * (-len(body) % 4)
            data = json.loads(__import__("base64").urlsafe_b64decode(padded).decode())
            if time.time() - float(data.get("loggedInAt", 0)) > 7 * 86400:
                return None
            return data
        except Exception:
            return None

    async def _discord(self, path, **kwargs):
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{DISCORD_API}{path}", **kwargs) as response:
                text = await response.text()
                data = json.loads(text) if text else {}
                if response.status >= 400:
                    raise RuntimeError(f"Discord API {response.status}")
                return data

    async def start(self):
        app = web.Application()
        app.add_routes([
            web.get("/", self.home),
            web.get("/anime", self.home),
            web.get("/health", self.health),
            web.get("/api/overview", self.api_overview),
            web.get("/api/member", self.api_member),
            web.get("/api/ai", self.api_ai),
            web.post("/api/ai", self.api_ai),
            web.get("/api/auth/login", self.auth_login),
            web.get("/api/auth/callback", self.auth_callback),
            web.get("/api/auth/me", self.auth_me),
            web.get("/api/auth/logout", self.auth_logout),
        ])
        if self.web_root.exists():
            app.router.add_static("/assets/", self.web_root / "assets", show_index=False)
        app.router.add_get("/{tail:.*}", self.spa)

        self.runner = web.AppRunner(app)
        await self.runner.setup()
        requested_port = int(os.getenv("PORT", os.getenv("DASHBOARD_PORT", "8765")))
        for port in range(requested_port, requested_port + 11):
            try:
                self.site = web.TCPSite(self.runner, "0.0.0.0", port)
                await self.site.start()
                self.port = port
                if port != requested_port:
                    print(f"Website port {requested_port} was busy; using {port} instead.")
                return
            except OSError:
                continue
        self.port = None
        print(f"Website disabled: could not bind ports {requested_port}-{requested_port + 10}.")

    def _authorized(self, request):
        expected = os.getenv("HORIZON_API_TOKEN", "").strip()
        supplied = request.headers.get("X-Horizon-API-Key", "")
        return bool(expected and hmac.compare_digest(supplied, expected))

    async def auth_login(self, request):
        try:
            state = secrets.token_urlsafe(32)
            redirect = os.getenv("DISCORD_REDIRECT_URI", "").strip() or f"{self._base_url(request)}/api/auth/callback"
            params = {"client_id": os.getenv("DISCORD_CLIENT_ID", ""), "response_type": "code", "redirect_uri": redirect, "scope": "identify guilds", "state": state}
            if not params["client_id"] or not os.getenv("DISCORD_CLIENT_SECRET", "") or not self.sessions_secret:
                return web.Response(text="Discord login is not configured on Railway.", status=503)
            response = web.HTTPFound(f"https://discord.com/oauth2/authorize?{urlencode(params)}")
            response.headers.add("Set-Cookie", self._cookie("lh_oauth_state", state, 600))
            return response
        except Exception:
            return web.Response(text="Discord login configuration error.", status=500)

    async def auth_callback(self, request):
        try:
            code = request.query.get("code", "")
            state = request.query.get("state", "")
            cookies = self._parse_cookies(request)
            if not code or not state or not hmac.compare_digest(state, cookies.get("lh_oauth_state", "")):
                return web.Response(text="Invalid OAuth state or code.", status=400)
            redirect = os.getenv("DISCORD_REDIRECT_URI", "").strip() or f"{self._base_url(request)}/api/auth/callback"
            body = {"client_id": os.getenv("DISCORD_CLIENT_ID", ""), "client_secret": os.getenv("DISCORD_CLIENT_SECRET", ""), "grant_type": "authorization_code", "code": code, "redirect_uri": redirect}
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f"{DISCORD_API}/oauth2/token", data=body) as r:
                    token = await r.json()
                    if r.status >= 400:
                        raise RuntimeError("Discord token exchange failed")
                headers = {"Authorization": f"Bearer {token['access_token']}"}
                async with session.get(f"{DISCORD_API}/users/@me", headers=headers) as r:
                    user = await r.json()
                    if r.status >= 400:
                        raise RuntimeError("Discord user lookup failed")
                async with session.get(f"{DISCORD_API}/users/@me/guilds", headers=headers) as r:
                    guilds = await r.json()
                    if r.status >= 400:
                        raise RuntimeError("Discord guild lookup failed")
            guild_id = os.getenv("DISCORD_GUILD_ID", "").strip()
            member = any(str(g.get("id")) == guild_id for g in guilds)
            response = web.HTTPFound(f"{self._base_url(request)}/?discord={'success' if member else 'not-member'}")
            response.headers.add("Set-Cookie", self._cookie("lh_oauth_state", "", 0))
            if member:
                payload = {"id": user["id"], "username": user.get("username", ""), "global_name": user.get("global_name") or user.get("username", ""), "avatar": user.get("avatar"), "loggedInAt": time.time()}
                response.headers.add("Set-Cookie", self._cookie("lh_session", self._make_session(payload), 7 * 86400))
            return response
        except Exception:
            response = web.HTTPFound(f"{self._base_url(request)}/?discord=error")
            response.headers.add("Set-Cookie", self._cookie("lh_oauth_state", "", 0))
            return response

    async def auth_me(self, request):
        session = self._verify_session(request)
        return web.json_response({"user": session} if session else {"user": None}, status=200 if session else 401)

    async def auth_logout(self, request):
        response = web.HTTPFound("/")
        response.headers.add("Set-Cookie", self._cookie("lh_session", "", 0))
        return response

    async def api_ai(self, request):
        if request.method == "GET":
            return web.json_response({"online": True, "ai_configured": bool(self.bot.ai.enabled), "model": self.bot.ai.model, "provider": self.bot.ai.provider_name})
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON body"}, status=400)
        message = body.get("message", "") if isinstance(body, dict) else ""
        history = body.get("history", []) if isinstance(body, dict) else []
        if not isinstance(message, str) or not message.strip():
            return web.json_response({"error": "Please enter a message."}, status=400)
        if len(message) > 4000:
            return web.json_response({"error": "Message is too long."}, status=400)
        guild_id = os.getenv("DISCORD_GUILD_ID", "").strip()
        if not guild_id.isdigit() or not self.bot.get_guild(int(guild_id)):
            return web.json_response({"error": "Horizon is not connected to the configured guild."}, status=503)
        session = self._verify_session(request)
        try:
            answer = await self.bot.generate_ai_reply(int(guild_id), int(session["id"]) if session else None, session.get("global_name", "Website visitor") if session else "Website visitor", message.strip(), history)
            return web.json_response({"reply": answer, "model": self.bot.ai.model})
        except Exception:
            return web.json_response({"error": "Horizon AI is temporarily unavailable."}, status=502)

    async def api_overview(self, request):
        if not self._authorized(request):
            return web.json_response({"error": "Unauthorized"}, status=401)
        guild_id = request.query.get("guild_id", "")
        if not guild_id.isdigit(): return web.json_response({"error": "guild_id is required"}, status=400)
        guild = self.bot.get_guild(int(guild_id))
        if not guild: return web.json_response({"error": "Guild not found"}, status=404)
        rows = await self.bot.db.leaderboard(int(guild_id), 10000)
        events = await self.bot.db.events(int(guild_id))
        return web.json_response({"guild_id": guild.id, "guild_name": guild.name, "member_count": guild.member_count, "tracked_players": len(rows), "total_xp": sum(r[1] for r in rows), "total_coins": sum(r[2] for r in rows), "event_count": len(events), "latency_ms": round(self.bot.latency * 1000), "ai_online": bool(self.bot.ai.enabled), "ai_model": self.bot.ai.model})

    async def api_member(self, request):
        if not self._authorized(request): return web.json_response({"error": "Unauthorized"}, status=401)
        guild_id, user_id = request.query.get("guild_id", ""), request.query.get("user_id", "")
        if not guild_id.isdigit() or not user_id.isdigit(): return web.json_response({"error": "guild_id and user_id are required"}, status=400)
        guild = self.bot.get_guild(int(guild_id)); member = guild.get_member(int(user_id)) if guild else None
        if not member: return web.json_response({"error": "Member not found"}, status=404)
        profile = await self.bot.db.profile(int(guild_id), int(user_id))
        return web.json_response({"user_id": member.id, "username": member.display_name, "avatar": str(member.display_avatar.url), "roles": [r.name for r in member.roles if r.name != "@everyone"], "level": profile["xp"] // 100 + 1, "xp": profile["xp"], "coins": profile["coins"], "warnings": profile["warnings"]})

    async def health(self, request):
        return web.json_response({"online": True, "guilds": len(self.bot.guilds), "provider": self.bot.ai.provider_name, "model": self.bot.ai.model, "ai_configured": self.bot.ai.enabled})

    async def home(self, request):
        if not self.web_root.exists():
            return web.Response(text="Log Horizon website build is missing.", status=503)
        return web.FileResponse(self.web_root / "index.html")

    async def spa(self, request):
        if request.path.startswith("/api/") or request.path == "/health":
            return web.json_response({"error": "Not found"}, status=404)
        if self.web_root.exists():
            return web.FileResponse(self.web_root / "index.html")
        return web.Response(text="Log Horizon website build is missing.", status=503)
