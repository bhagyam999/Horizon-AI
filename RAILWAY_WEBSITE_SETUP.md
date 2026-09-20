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


## Troubleshooting AI + Discord login

Open `https://YOUR-RAILWAY-DOMAIN/health` in a browser. This endpoint intentionally reports only configuration booleans, never secret values.

For Horizon AI, `ai_configured` must be `true`. The website's Horizon panel also checks the real Gemini model connection before showing Horizon as online. The Railway service must have a valid `GEMINI_API_KEY`; the browser must never receive it.

For Discord login, `discord_oauth_configured` and `session_configured` must both be `true`. `DISCORD_REDIRECT_URI` is recommended and must exactly match the redirect URL registered in the Discord Developer Portal, including `https://`, domain, path, and no extra trailing slash.

The required callback format is:
`https://YOUR-RAILWAY-DOMAIN/api/site/auth-callback`

If the Railway domain changes, update both Railway `SITE_URL`/`DISCORD_REDIRECT_URI` and the Discord OAuth redirect URL, then redeploy. Do not paste API keys, client secrets, bot tokens, or session secrets into chat.

## v10.3 AI context and OAuth notes

Optional AI history settings:
- `AI_HISTORY_BACKFILL_CHANNELS` — maximum public text channels to read on first startup (default `30`).
- `AI_HISTORY_BACKFILL_MESSAGES` — messages read per public channel during the one-time backfill (default `120`).

Horizon keeps the active AI dialogue to the latest 13 messages. Older dialogue remains stored but is not automatically fed back into the model. A separate bounded public-server history index supplies relevant older context without merging different speakers into one identity.

For Railway Discord OAuth, use exactly:
`https://YOUR-RAILWAY-DOMAIN/api/site/auth-callback`

The service also accepts compatible callback aliases to prevent stale redirects from becoming a 404, but the Discord Developer Portal and `DISCORD_REDIRECT_URI` should be updated to the canonical Railway callback above.
