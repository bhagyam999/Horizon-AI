import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from pathlib import Path
from urllib.parse import urlencode

import aiohttp
from aiohttp import web

log = logging.getLogger("horizon.dashboard")


class Dashboard:
    """Railway web service: health/API + the complete Log Horizon website."""
    def __init__(self, bot):
        self.bot = bot
        self.runner = None
        self.port = None
        self.base_dir = Path(__file__).resolve().parent
        self.site_dir = self.base_dir / "website"
        self.dist_dir = self.site_dir / "dist"

    async def start(self):
        app = web.Application(client_max_size=5 * 1024 * 1024)
        app.add_routes([
            web.get("/", self.website),
            web.get("/anime", self.website),
            web.get("/health", self.health),
            web.get("/api/overview", self.api_overview),
            web.get("/api/member", self.api_member),
            web.post("/api/ai", self.api_ai),
            web.get("/api/site/auth-login", self.site_auth_login),
            web.get("/api/site/auth-callback", self.site_auth_callback),
            web.get("/api/site/auth-callback/", self.site_auth_callback),
            web.get("/api/site/auth/callback", self.site_auth_callback),
            # Compatibility with the old Netlify callback path, so a stale Discord
            # OAuth redirect does not dead-end in a 404 after moving to Railway.
            web.get("/.netlify/functions/auth-callback", self.site_auth_callback),
            web.get("/.netlify/functions/auth-callback/", self.site_auth_callback),
            web.get("/auth/callback", self.site_auth_callback),
            web.get("/api/site/auth-me", self.site_auth_me),
            web.get("/api/site/auth-logout", self.site_auth_logout),
            web.route("*", "/api/site/horizon-ai", self.site_horizon_ai),
            web.get("/api/site/horizon-server", self.site_horizon_server),
            web.get("/assets/{path:.*}", self.asset),
        ])

        self.runner = web.AppRunner(app)
        await self.runner.setup()
        # Railway routes public traffic to the exact value of $PORT. Never
        # silently move to another port: doing so makes the service appear
        # healthy internally while Railway returns 502 externally.
        port_raw = os.getenv("PORT", "").strip()
        if not port_raw:
            port_raw = os.getenv("DASHBOARD_PORT", "8765").strip()
            print("WARNING: PORT is not set; using DASHBOARD_PORT/fallback. Public Railway networking requires PORT.")
        requested_port = int(port_raw)
        try:
            site = web.TCPSite(self.runner, "0.0.0.0", requested_port)
            await site.start()
            self.port = requested_port
            print(f"Dashboard listening on 0.0.0.0:{requested_port}; website={self.dist_dir}")
        except OSError as exc:
            self.port = None
            print(f"Dashboard failed to bind required port {requested_port}: {exc}")
            raise

    def _authorized(self, request):
        expected = os.getenv("HORIZON_API_TOKEN", "").strip()
        if not expected:
            return False
        return hmac.compare_digest(request.headers.get("X-Horizon-API-Key", ""), expected)

    def _base_url(self, request):
        configured = os.getenv("SITE_URL", "").strip().rstrip("/")
        if configured:
            return configured
        proto = request.headers.get("X-Forwarded-Proto", request.url.scheme)
        host = request.headers.get("X-Forwarded-Host", request.host)
        return f"{proto}://{host}"

    def _redirect_uri(self, request):
        configured = os.getenv("DISCORD_REDIRECT_URI", "").strip()
        return configured or f"{self._base_url(request)}/api/site/auth-callback"

    def _secret(self):
        return os.getenv("SESSION_SECRET", "").strip()

    def _sign(self, value):
        return hmac.new(self._secret().encode(), value.encode(), hashlib.sha256).digest()

    def _make_token(self, payload):
        body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
        sig = base64.urlsafe_b64encode(self._sign(body)).decode().rstrip("=")
        return f"{body}.{sig}"

    def _verify_token(self, token):
        if not token or not self._secret():
            return None
        try:
            body, signature = token.split(".", 1)
            expected = base64.urlsafe_b64encode(self._sign(body)).decode().rstrip("=")
            if not hmac.compare_digest(signature, expected):
                return None
            padded = body + "=" * (-len(body) % 4)
            return json.loads(base64.urlsafe_b64decode(padded).decode())
        except Exception:
            return None

    def _cookies(self, request):
        return {part.split("=", 1)[0].strip(): part.split("=", 1)[1].strip() for part in request.headers.get("Cookie", "").split("; ") if "=" in part}

    def _set_cookie(self, response, name, value, max_age, http_only=True):
        response.set_cookie(name, value, max_age=max_age, path="/", secure=True, httponly=http_only, samesite="Lax")

    def _session(self, request):
        return self._verify_token(self._cookies(request).get("lh_session", ""))

    async def _discord(self, path, **kwargs):
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request("GET", f"https://discord.com/api/v10{path}", **kwargs) as response:
                data = await response.json(content_type=None)
                if response.status >= 400:
                    raise RuntimeError(f"Discord API {response.status}")
                return data

    async def website(self, request):
        index = self.dist_dir / "index.html"
        if index.exists():
            return web.FileResponse(index)
        # The source is kept in the ZIP; Railway's build phase creates dist.
        return web.Response(status=503, text="Log Horizon website is still building. Please refresh shortly.", content_type="text/plain")

    async def asset(self, request):
        path = (self.dist_dir / "assets" / request.match_info["path"]).resolve()
        assets_root = (self.dist_dir / "assets").resolve()
        if not str(path).startswith(str(assets_root)) or not path.is_file():
            raise web.HTTPNotFound()
        return web.FileResponse(path)

    async def health(self, request):
        return web.json_response({
            "online": True,
            "guilds": len(self.bot.guilds),
            "provider": self.bot.ai.provider_name,
            "model": self.bot.ai.model,
            "ai_configured": self.bot.ai.enabled,
            "website": self.dist_dir.exists(),
            "discord_oauth_configured": bool(os.getenv("DISCORD_CLIENT_ID", "").strip() and os.getenv("DISCORD_CLIENT_SECRET", "").strip()),
            "session_configured": bool(self._secret()),
            "redirect_uri_configured": bool(os.getenv("DISCORD_REDIRECT_URI", "").strip()),
            "site_url_configured": bool(os.getenv("SITE_URL", "").strip()),
        })

    async def api_overview(self, request):
        if not self._authorized(request):
            return web.json_response({"error": "Unauthorized"}, status=401)
        guild_id = request.query.get("guild_id", "")
        if not guild_id.isdigit():
            return web.json_response({"error": "guild_id is required"}, status=400)
        guild = self.bot.get_guild(int(guild_id))
        if not guild:
            return web.json_response({"error": "Guild not found"}, status=404)
        rows = await self.bot.db.leaderboard(int(guild_id), 10000)
        events = await self.bot.db.events(int(guild_id))
        return web.json_response({
            "guild_id": guild.id, "guild_name": guild.name, "member_count": guild.member_count,
            "tracked_players": len(rows), "total_xp": sum(r[1] for r in rows),
            "total_coins": sum(r[2] for r in rows), "event_count": len(events),
            "latency_ms": round(self.bot.latency * 1000), "ai_online": bool(self.bot.ai.enabled),
            "ai_model": self.bot.ai.model,
        })

    async def api_member(self, request):
        if not self._authorized(request):
            return web.json_response({"error": "Unauthorized"}, status=401)
        guild_id, user_id = request.query.get("guild_id", ""), request.query.get("user_id", "")
        if not guild_id.isdigit() or not user_id.isdigit():
            return web.json_response({"error": "guild_id and user_id are required"}, status=400)
        guild = self.bot.get_guild(int(guild_id))
        member = guild.get_member(int(user_id)) if guild else None
        if not member:
            return web.json_response({"error": "Member not found"}, status=404)
        profile = await self.bot.db.profile(int(guild_id), int(user_id))
        return web.json_response({"user_id": member.id, "username": member.display_name, "avatar": str(member.display_avatar.url), "roles": [r.name for r in member.roles if r.name != "@everyone"], "level": profile["xp"] // 100 + 1, "xp": profile["xp"], "coins": profile["coins"], "warnings": profile["warnings"]})

    async def api_ai(self, request):
        if not self._authorized(request):
            return web.json_response({"error": "Unauthorized"}, status=401)
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON body"}, status=400)
        message = body.get("message", "") if isinstance(body, dict) else ""
        if not isinstance(message, str) or not message.strip():
            return web.json_response({"error": "Please enter a message."}, status=400)
        guild_id = os.getenv("DISCORD_GUILD_ID", "").strip()
        if not guild_id.isdigit():
            return web.json_response({"error": "Horizon guild is not configured."}, status=503)
        return await self._ai_response(request, int(guild_id), message.strip())

    async def _ai_response(self, request, guild_id, message):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return web.json_response({"error": "Horizon is not connected to the configured guild."}, status=503)
        session = self._session(request)
        if session and str(session.get("id", "")).isdigit():
            scope_id = f"discord:{session['id']}"
            name = session.get("global_name") or session.get("username") or "Discord member"
            profile = await self.bot.db.profile(guild_id, int(session["id"]))
            profile_text = f"nickname={profile['nickname'] or 'none'}; preferences={profile['preferences'] or 'none'}"
        else:
            cookies = self._cookies(request)
            visitor = self._verify_token(cookies.get("lh_visitor", ""))
            response_cookie = None
            if visitor and visitor.get("id"):
                visitor_id = visitor["id"]
            else:
                visitor_id = secrets.token_urlsafe(18)
                response_cookie = visitor_id
            scope_id = f"web:{visitor_id}"
            name = "Website visitor"
            profile_text = "(none)"

        settings = await self.bot.db.settings(guild_id)
        memories = await self.bot.db.memories(guild_id, 30)
        rows = await self.bot.db.ai_conversation(guild_id, scope_id, 120)
        context = self.bot.ai_context_from_rows(rows, message)
        memory_text = "\n".join(f"- {row[1]}" for row in memories)
        system = self.bot.build_ai_system(guild.name, name, memory_text, settings["personality"], profile_text, context)
        system += "\n\nMemory rule: use private conversation memory only when it clearly helps the current request. Never bring up unrelated old topics and never reveal another member's conversation."
        await self.bot.db.add_ai_message(guild_id, scope_id, "user", message)
        try:
            answer = await self.bot.ai.generate(system, message)
        except Exception as exc:
            await self.bot.db.remove_last_ai_message(guild_id, scope_id, "user")
            log.exception("Website Horizon AI request failed")
            return web.json_response({"error": "Horizon AI is temporarily unavailable."}, status=502)
        await self.bot.db.add_ai_message(guild_id, scope_id, "model", answer)
        response = web.json_response({"reply": answer, "model": self.bot.ai.model})
        if not session and response_cookie:
            token=self._make_token({"id":response_cookie,"createdAt":int(time.time())})
            self._set_cookie(response,"lh_visitor",token,60*60*24*365,http_only=True)
        return response

    async def site_horizon_ai(self, request):
        if request.method == "GET":
            try:
                online, detail = await self.bot.ai.status()
                return web.json_response({
                    "online": bool(online),
                    "serviceOnline": True,
                    "aiConfigured": bool(self.bot.ai.enabled),
                    "model": self.bot.ai.model,
                    "provider": self.bot.ai.provider_name,
                    "detail": detail,
                })
            except Exception as exc:
                log.exception("Website Horizon AI status check failed")
                return web.json_response({
                    "online": False,
                    "serviceOnline": True,
                    "aiConfigured": bool(self.bot.ai.enabled),
                    "model": self.bot.ai.model,
                    "provider": self.bot.ai.provider_name,
                    "error": "Horizon AI status check failed.",
                }, status=503)
        if request.method != "POST":
            return web.json_response({"error":"Method not allowed."}, status=405)
        try:
            body=await request.json()
        except Exception:
            return web.json_response({"error":"Invalid JSON body"}, status=400)
        message=body.get("message","") if isinstance(body,dict) else ""
        if not isinstance(message,str) or not message.strip():
            return web.json_response({"error":"Please enter a message."},status=400)
        if len(message)>4000:
            return web.json_response({"error":"Message is too long."},status=400)
        guild_id=os.getenv("DISCORD_GUILD_ID","").strip()
        if not guild_id.isdigit(): return web.json_response({"error":"Horizon guild is not configured."},status=503)
        return await self._ai_response(request,int(guild_id),message.strip())

    async def site_horizon_server(self, request):
        guild_id=os.getenv("DISCORD_GUILD_ID","").strip()
        if not guild_id.isdigit(): return web.json_response({"error":"Horizon guild is not configured."},status=503)
        guild=self.bot.get_guild(int(guild_id))
        if not guild: return web.json_response({"error":"Horizon community data is temporarily unavailable."},status=503)
        rows=await self.bot.db.leaderboard(int(guild_id),10000)
        events=await self.bot.db.events(int(guild_id))
        return web.json_response({"online":True,"guild_name":guild.name,"member_count":guild.member_count,"tracked_players":len(rows),"event_count":len(events),"latency_ms":round(self.bot.latency*1000),"ai_online":bool(self.bot.ai.enabled),"ai_model":self.bot.ai.model})

    async def site_auth_login(self, request):
        if not self._secret(): return web.Response(status=503,text="SESSION_SECRET is not configured.")
        client_id=os.getenv("DISCORD_CLIENT_ID","").strip()
        if not client_id: return web.Response(status=503,text="DISCORD_CLIENT_ID is not configured.")
        state=secrets.token_urlsafe(32)
        params=urlencode({"client_id":client_id,"response_type":"code","redirect_uri":self._redirect_uri(request),"scope":"identify guilds","state":state})
        response=web.HTTPFound(f"https://discord.com/oauth2/authorize?{params}")
        self._set_cookie(response,"lh_oauth_state",state,600,http_only=True)
        return response

    async def site_auth_callback(self, request):
        site=self._base_url(request)
        try:
            q=request.rel_url.query
            code,state=q.get("code"),q.get("state")
            if not code or not state or state!=self._cookies(request).get("lh_oauth_state"):
                return web.HTTPFound(f"{site}/?discord=error")
            data={"client_id":os.getenv("DISCORD_CLIENT_ID",""),"client_secret":os.getenv("DISCORD_CLIENT_SECRET",""),"grant_type":"authorization_code","code":code,"redirect_uri":self._redirect_uri(request)}
            timeout=aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post("https://discord.com/api/v10/oauth2/token",data=data) as token_response:
                    token=await token_response.json(content_type=None)
                    if token_response.status>=400: raise RuntimeError("Discord OAuth token exchange failed")
                headers={"Authorization":f"Bearer {token['access_token']}"}
                async with session.get("https://discord.com/api/v10/users/@me",headers=headers) as user_response:
                    user=await user_response.json(content_type=None)
                    if user_response.status>=400: raise RuntimeError("Discord user lookup failed")
                async with session.get("https://discord.com/api/v10/users/@me/guilds",headers=headers) as guild_response:
                    guilds=await guild_response.json(content_type=None)
                    if guild_response.status>=400: raise RuntimeError("Discord guild lookup failed")
            guild_id=os.getenv("DISCORD_GUILD_ID","").strip()
            if not any(str(g.get("id"))==guild_id for g in guilds if isinstance(g,dict)):
                response=web.HTTPFound(f"{site}/?discord=not-member")
            else:
                payload={"id":str(user["id"]),"username":user.get("username"),"global_name":user.get("global_name") or user.get("username"),"avatar":user.get("avatar"),"loggedInAt":int(time.time()*1000)}
                response=web.HTTPFound(f"{site}/?discord=success")
                self._set_cookie(response,"lh_session",self._make_token(payload),60*60*24*7,http_only=True)
            self._set_cookie(response,"lh_oauth_state","",0,http_only=True)
            return response
        except Exception as exc:
            log.exception("Discord OAuth callback failed")
            # Never expose Discord tokens or client secrets in the browser. The user
            # gets a stable redirect back to the SPA while the detailed exception
            # remains in Railway logs for diagnosis.
            return web.HTTPFound(f"{site}/?discord=error")

    async def site_auth_me(self, request):
        return web.json_response({"user":self._session(request)},headers={"Cache-Control":"no-store"})

    async def site_auth_logout(self, request):
        response=web.json_response({"ok":True})
        self._set_cookie(response,"lh_session","",0,http_only=True)
        return response
