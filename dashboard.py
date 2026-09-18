import os
from aiohttp import web


class Dashboard:
    def __init__(self, bot):
        self.bot = bot
        self.runner = None

    async def start(self):
        app = web.Application()
        app.add_routes([
            web.get("/", self.home),
            web.get("/health", self.health),
            web.get("/api/overview", self.api_overview),
            web.get("/api/member", self.api_member),
        ])

        self.runner = web.AppRunner(app)
        await self.runner.setup()

        requested_port = int(os.getenv("PORT", os.getenv("DASHBOARD_PORT", "8765")))
        last_error = None
        for port in range(requested_port, requested_port + 11):
            try:
                site = web.TCPSite(self.runner, "0.0.0.0", port)
                await site.start()
                self.port = port
                if port != requested_port:
                    print(f"Dashboard port {requested_port} was busy; using {port} instead.")
                return
            except OSError as exc:
                last_error = exc
        # Dashboard is optional. Do not prevent the Discord bot from starting.
        self.port = None
        print(f"Dashboard disabled: could not bind ports {requested_port}-{requested_port + 10}: {last_error}")


    def _authorized(self, request):
        expected = os.getenv("HORIZON_API_TOKEN", "").strip()
        if not expected:
            return False
        supplied = request.headers.get("X-Horizon-API-Key", "")
        return supplied == expected

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
        total_xp = sum(row[1] for row in rows)
        total_coins = sum(row[2] for row in rows)
        return web.json_response({
            "guild_id": guild.id,
            "guild_name": guild.name,
            "member_count": guild.member_count,
            "tracked_players": len(rows),
            "total_xp": total_xp,
            "total_coins": total_coins,
            "event_count": len(events),
            "latency_ms": round(self.bot.latency * 1000),
            "ai_online": bool(self.bot.ai.enabled),
            "ai_model": self.bot.ai.model,
        })

    async def api_member(self, request):
        if not self._authorized(request):
            return web.json_response({"error": "Unauthorized"}, status=401)
        guild_id = request.query.get("guild_id", "")
        user_id = request.query.get("user_id", "")
        if not guild_id.isdigit() or not user_id.isdigit():
            return web.json_response({"error": "guild_id and user_id are required"}, status=400)
        guild = self.bot.get_guild(int(guild_id))
        if not guild:
            return web.json_response({"error": "Guild not found"}, status=404)
        member = guild.get_member(int(user_id))
        if not member:
            return web.json_response({"error": "Member not found"}, status=404)
        profile = await self.bot.db.profile(int(guild_id), int(user_id))
        return web.json_response({
            "user_id": member.id,
            "username": member.display_name,
            "avatar": str(member.display_avatar.url),
            "roles": [r.name for r in member.roles if r.name != "@everyone"],
            "level": profile["xp"] // 100 + 1,
            "xp": profile["xp"],
            "coins": profile["coins"],
            "warnings": profile["warnings"],
        })

    async def home(self, request):
        return web.Response(
            text=(
                "<html><body>"
                "<h1>🌌 Horizon Dashboard</h1>"
                f"<p>Servers: {len(self.bot.guilds)}</p>"
                f"<p>AI: {'configured' if self.bot.ai.enabled else 'offline'}</p>"
                f"<p>Provider: {self.bot.ai.provider_name}</p>"
                f"<p>Model: {self.bot.ai.model}</p>"
                "<p>Use Discord slash commands to configure Horizon.</p>"
                "</body></html>"
            ),
            content_type="text/html",
        )

    async def health(self, request):
        return web.json_response({
            "online": True,
            "guilds": len(self.bot.guilds),
            "provider": self.bot.ai.provider_name,
            "model": self.bot.ai.model,
            "ai_configured": self.bot.ai.enabled,
        })
