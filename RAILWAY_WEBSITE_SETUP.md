# Combined Railway deployment

This project now contains the complete Discord bot and the Log Horizon website in one deployable service. Railway builds `website/dist` during deployment and the Python dashboard serves it from the same public Railway domain.

## Required Railway variables
- `DISCORD_TOKEN`
- `DISCORD_GUILD_ID`
- `DISCORD_CLIENT_ID`
- `DISCORD_CLIENT_SECRET`
- `SESSION_SECRET`
- `GEMINI_API_KEY`
- `HORIZON_API_TOKEN` (long random bridge token)
- `HORIZON_DB=/data/horizon.db`
- `SITE_URL=https://YOUR-RAILWAY-DOMAIN`
- `DISCORD_REDIRECT_URI=https://YOUR-RAILWAY-DOMAIN/api/site/auth-callback`

Attach a Railway Volume at `/data`. Do not delete that volume when deploying updates; it contains the persistent RPG/database state.

## Discord Developer Portal
Add exactly this OAuth redirect URI:
`https://YOUR-RAILWAY-DOMAIN/api/site/auth-callback`

## Website
The website is served from the same Railway service at `/` and `/anime`. The browser talks to same-origin `/api/site/*` endpoints, so the separate Netlify bridge is no longer required for this combined deployment.

## AI memory isolation
Horizon stores private conversation history by `(guild_id, user_id)` for Discord members and by a private website visitor/session ID for website visitors. It does not use the old guild-wide transient AI history. Server-wide `/remember` facts remain separate and are visible to Horizon for the whole server.


## v10.1 Railway runtime fix
The repository includes a Dockerfile with a Node build stage for `website/` and a Python runtime that starts `python bot.py`. The dashboard binds to Railway's exact `$PORT` on `0.0.0.0`; it never switches to another port, because Railway's public proxy routes to `$PORT`. On startup it logs `Dashboard listening on 0.0.0.0:<PORT>`.
