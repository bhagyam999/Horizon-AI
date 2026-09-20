# Log Horizon — Horizon AI architecture

The website and Discord bot use one Horizon AI service hosted on Railway.

```text
Log Horizon website
        ↓
Netlify Function /horizon-ai
        ↓ HTTPS + server-side token
Railway Horizon API
        ↓
Existing Horizon AIProvider
        ↓
Gemini
```

The browser never receives `GEMINI_API_KEY`, `HORIZON_API_TOKEN`, or the Discord bot token.

## Netlify

- `HORIZON_BOT_API_URL`
- `HORIZON_BOT_API_TOKEN`
- `HORIZON_BOT_HTTP_TIMEOUT` (optional)

## Railway

- `DISCORD_TOKEN`
- `DISCORD_GUILD_ID`
- `GEMINI_API_KEY`
- `GEMINI_MODEL` (optional)
- `GEMINI_HTTP_TIMEOUT` (optional)
- `HORIZON_API_TOKEN`
- `PORT` (Railway supplied)

The website keeps its existing AI UI but routes its requests through Railway. This keeps the Discord bot and website on the same Horizon service instead of maintaining two separate Gemini clients.
