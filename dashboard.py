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
            web.get("/api/rpg/art", self.rpg_art),
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

    async def rpg_art(self, request):
        """Render deterministic full-body RPG art as a PNG that Discord can display."""
        import hashlib
        import io
        from PIL import Image, ImageDraw, ImageFont, ImageFilter

        kind=request.query.get("kind","character").lower()
        seed=request.query.get("seed","unknown")
        bits=[x.strip().lower().replace("_"," ") for x in seed.split("|") if x.strip()]
        digest=hashlib.sha256(seed.encode()).digest()
        def pick(values,offset=0): return values[digest[offset % len(digest)] % len(values)]
        bg=pick([(12,20,39),(24,16,45),(10,31,42),(37,24,15),(18,28,25)],0)
        accent=pick([(99,213,255),(192,132,252),(245,158,11),(244,63,94),(52,211,153),(229,231,235)],2)
        skin=pick([(243,201,173),(220,174,139),(185,120,85),(240,208,189),(143,93,69)],4)
        hair=pick([(17,24,39),(63,36,23),(124,45,18),(245,208,97),(229,231,235),(107,33,168)],6)
        cloth=pick([(23,32,51),(59,29,43),(23,53,47),(41,32,68),(58,43,27)],8)

        W,H=900,620
        im=Image.new("RGB",(W,H),bg)
        glow=Image.new("RGBA",(W,H),(0,0,0,0)); gd=ImageDraw.Draw(glow)
        for r,a in [(240,20),(190,28),(135,38)]:
            gd.ellipse((450-r,310-r,450+r,310+r),fill=(*accent,a))
        glow=glow.filter(ImageFilter.GaussianBlur(20)); im=Image.alpha_composite(im.convert("RGBA"),glow)
        d=ImageDraw.Draw(im)
        try: font=ImageFont.truetype("DejaVuSans.ttf",24); small=ImageFont.truetype("DejaVuSans.ttf",16); tiny=ImageFont.truetype("DejaVuSans.ttf",13)
        except Exception: font=small=tiny=None
        def txt(xy,text,f,fill): d.text(xy,text,font=f,fill=fill)
        txt((36,30),bits[0].title() + (" " + bits[2].title() if kind=="character" and len(bits)>2 else ""),font,(245,247,250))
        if kind=="character":
            race=bits[0] if bits else "human"; cls=bits[2] if len(bits)>2 else "warrior"; sub=bits[3] if len(bits)>3 else ""
            txt((36,62),f"{sub.title() or 'Adventurer'}  •  identity-based battle art",small,(184,196,216))
            # cape/aura
            d.ellipse((150,115,600,565),outline=(*accent,90),width=5)
            # race traits behind body
            if race in {"fae"}:
                d.polygon([(245,270),(70,190),(110,390),(275,320)],fill=(*accent,80))
                d.polygon([(555,270),(830,190),(790,390),(525,320)],fill=(*accent,80))
            if race in {"beastfolk","kitsune","dragonkin"}:
                d.line((575,390,760,470,720,530),fill=accent,width=24,joint="curve")
            # legs and boots
            d.line((340,445,310,560),fill=(31,41,55),width=55)
            d.line((455,445,490,560),fill=(31,41,55),width=55)
            d.line((280,565,350,565),fill=(5,10,18),width=24)
            d.line((455,565,525,565),fill=(5,10,18),width=24)
            # torso + armor
            d.polygon([(300,265),(500,265),(545,450),(450,485),(350,485),(255,450)],fill=cloth,outline=accent)
            d.line((350,300,450,300),fill=accent,width=6)
            # head
            d.ellipse((305,120,495,300),fill=skin,outline=accent,width=4)
            d.pieslice((305,105,495,300),180,355,fill=hair)
            if race not in {"human","dwarf","golem"}:
                d.polygon([(325,165),(250,120),(300,205)],fill=hair)
                d.polygon([(475,165),(550,120),(500,205)],fill=hair)
            if race in {"tiefling","vampire","dragonkin"}:
                d.polygon([(345,145),(330,75),(385,125)],fill=(215,208,199))
                d.polygon([(455,145),(470,75),(415,125)],fill=(215,208,199))
            # eyes + face
            eye=(15,23,42) if race not in {"vampire","fae"} else accent
            d.ellipse((350,185,370,205),fill=eye); d.ellipse((430,185,450,205),fill=eye)
            d.arc((380,205,420,235),0,180,fill=(127,29,29),width=4)
            # weapon determined by class
            if "lancer" in cls:
                d.line((590,480,700,105),fill=(204,181,138),width=12); d.polygon([(700,85),(682,135),(718,135)],fill=accent)
            elif "ranger" in cls:
                d.arc((565,150,735,480),70,290,fill=(204,181,138),width=13); d.line((650,155,650,470),fill=(229,231,235),width=4)
            elif "engineer" in cls:
                d.rounded_rectangle((565,245,760,300),18,fill=(156,163,175),outline=accent,width=4); d.rectangle((625,295,675,390),fill=(75,85,99)); d.ellipse((700,255,730,285),fill=accent)
            elif "rogue" in cls or "assassin" in cls:
                d.polygon([(585,285),(750,215),(735,255),(590,315)],fill=(219,234,254)); d.rectangle((560,285,625,305),fill=(154,103,63))
            elif any(x in cls for x in ("mage","cleric","druid","summoner","warlock","necromancer","bard")):
                d.line((610,480,650,120),fill=(200,177,138),width=12); d.ellipse((625,90,685,150),fill=accent,outline=(245,247,250),width=3)
            else:
                d.polygon([(630,90),(690,300),(630,485),(570,300)],fill=(219,234,254),outline=(245,247,250)); d.rectangle((585,295,675,320),fill=(183,121,63))
            # identity card
            d.rounded_rectangle((625,405,855,555),20,fill=(255,255,255,18),outline=accent,width=2)
            txt((650,425),"IDENTITY",small,(245,247,250)); txt((650,452),race.title(),tiny,(184,196,216)); txt((650,476),cls.title(),tiny,(184,196,216)); txt((650,500),sub.title() or "Base",tiny,(184,196,216))
        elif kind=="pet":
            species=bits[0] if bits else "companion"; archetype=pick(["wolf","fox","cat","dragon","hawk","spirit","bear"],10)
            txt((36,62),f"{archetype.title()} companion archetype  •  stable identity art",small,(184,196,216))
            d.ellipse((230,145,670,565),fill=(*accent,28),outline=accent,width=5)
            # ears/head/body
            d.polygon([(300,255),(250,145),(350,205),(550,205),(650,145),(600,255)],fill=cloth,outline=accent)
            d.ellipse((290,190,610,430),fill=cloth,outline=accent,width=6)
            d.ellipse((360,285,405,330),fill=accent); d.ellipse((495,285,540,330),fill=accent)
            d.polygon([(425,350),(450,370),(475,350)],fill=skin)
            d.arc((400,355,500,425),0,180,fill=(10,15,25),width=12)
            d.line((355,410,270,520),fill=cloth,width=55); d.line((545,410,630,520),fill=cloth,width=55)
            d.ellipse((390,125,510,245),fill=(*accent,55),outline=accent,width=4)
            txt((36,535),species.title(),font,(245,247,250))
        else:
            name=bits[0] if bits else "monster"; role=bits[4] if len(bits)>4 else "beast"; archetype=pick(["beast","undead","construct","elemental","demon","insect","humanoid"],14); eye=pick([(239,68,68),(245,158,11),(168,85,247),(34,211,238),(132,204,22)],16)
            txt((36,62),f"{archetype.title()}  •  {role.title()}  •  persistent mob identity",small,(184,196,216))
            d.ellipse((185,125,715,570),fill=(*eye,18),outline=accent,width=6)
            d.polygon([(260,445),(210,275),(275,155),(450,100),(625,155),(690,275),(640,445),(450,510)],fill=cloth,outline=accent,width=7)
            d.polygon([(310,185),(225,90),(345,145)],fill=cloth,outline=accent); d.polygon([(590,185),(675,90),(555,145)],fill=cloth,outline=accent)
            d.ellipse((320,235,380,310),fill=eye); d.ellipse((520,235,580,310),fill=eye)
            d.arc((350,315,550,425),0,180,fill=(5,10,18),width=24)
            d.line((320,420,215,535),fill=cloth,width=65); d.line((580,420,685,535),fill=cloth,width=65)
            d.ellipse((395,105,505,215),fill=(*accent,45),outline=accent,width=4)
            txt((36,535),name.title(),font,(245,247,250))

        out=io.BytesIO(); im.convert("RGB").save(out,format="PNG",optimize=True)
        return web.Response(body=out.getvalue(),content_type="image/png",headers={"Cache-Control":"public, max-age=86400"})

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
