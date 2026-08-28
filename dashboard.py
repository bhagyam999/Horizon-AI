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
        ])

        self.runner = web.AppRunner(app)
        await self.runner.setup()

        requested_port = int(os.getenv("DASHBOARD_PORT", "8765"))
        last_error = None
        for port in range(requested_port, requested_port + 11):
            try:
                site = web.TCPSite(self.runner, "127.0.0.1", port)
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
