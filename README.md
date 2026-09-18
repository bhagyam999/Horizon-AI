# Horizon AI — Log Horizon Discord Core

Horizon is the Discord-side community core for Log Horizon.

## Railway environment

Set these variables in Railway:

- `DISCORD_TOKEN`
- `DISCORD_GUILD_ID`
- `GEMINI_API_KEY`
- `GEMINI_MODEL` (default: `gemini-2.5-flash-lite`)
- `GEMINI_HTTP_TIMEOUT` (default: `12000`)
- `HORIZON_API_TOKEN` — long random secret shared only with the Netlify website function
- `PORT` — normally supplied automatically by Railway

Never commit `.env` or real secrets.

## What this build does

Horizon operates across the server rather than being limited to one channel:

- XP and community progression from server messages
- Contextual moderation and escalation handling
- Welcome messages
- Configurable Horizon AI channel
- `/ask` Gemini chat
- Direct `@Horizon ...` AI mentions in any server channel
- Profiles, XP leaderboard, inventory and daily rewards
- Discord-native games and RPG systems
- Community events and event signups
- Server announcements and configurable channels
- Server statistics and Horizon settings
- Authenticated website bridge for live server overview and logged-in member data

Direct mentions are intentionally used instead of replying to every message, so Horizon can be present throughout the server without flooding conversations.

## Website bridge

The dashboard exposes:

- `GET /health` — public health check
- `GET /api/overview?guild_id=...` — authenticated live server overview
- `GET /api/member?guild_id=...&user_id=...` — authenticated member profile data

API requests require:

`X-Horizon-API-Key: <HORIZON_API_TOKEN>`

The website stores that token only in a Netlify serverless function. The Discord bot token never reaches the browser.


## Website AI bridge

The Railway service also exposes an authenticated `POST /api/ai` endpoint for the Log Horizon website. It reuses the same `AIProvider` and server context as Horizon's Discord AI. Requests require `X-Horizon-API-Key` matching `HORIZON_API_TOKEN`.

The website should use the Railway public service URL as `HORIZON_BOT_API_URL`; the Gemini key remains Railway-only.
