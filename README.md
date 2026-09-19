# Horizon AI — Log Horizon Discord Core

Horizon is the Discord-side community core for **Log Horizon**.

## Current build

This build keeps the existing AI, moderation, RPG, events, profiles, economy, dashboard bridge and server tools while expanding the Discord game layer and prefix-based AI.

### AI

- `/ask` — ask Horizon directly
- `/ai_status` — check Gemini connectivity
- `/ai_models` — inspect models available to the configured Gemini key
- `!ai <message>` — talk to Horizon anywhere in the server
- `!h <message>` and `!horizon <message>` are aliases
- Prefix mode replaces mention-to-chat so normal mentions stay normal Discord mentions
- `/set_ai_channel` and `/disable_ai_channel` remain available for dedicated AI chat

### Games

- `!games` — compact game hub
- `!game <name>` — launch a game with one reusable game message
- `!stop` — stop the active game
- `!join` / `!begin` — Werewolf/Mafia lobby flow
- `!guess <letter>` — Hangman; Horizon edits the original game message instead of posting a new board every turn
- `!rps <rock|paper|scissors>` — immediate RPS
- `!vote @player`, `!dayend`, `!nightend` — hidden-role game controls

Games are now designed around low channel noise: prefix commands can be deleted after processing, while the bot updates one game message in place. Button-based games such as Trivia, Would You Rather and Truth or Dare keep their interactive buttons. Werewolf and Mafia use private DMs for roles and night actions, so players do not publicly see another player's role/action.

Every game launch explains what the game is and what to do next, so players do not get a dead “game started” message with no instructions.

### Server and moderation

- Contextual moderation and escalation handling
- Welcome messages
- Profiles, XP, leaderboard, inventory and daily rewards
- Community events and event signups
- Server announcements and configurable channels
- `/horizon_permissions` — inspect Horizon's effective Discord permissions
- `/horizon_settings` and `/server_stats`

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

## Discord permissions

If you choose to give Horizon the **Administrator** permission in the Discord server, `/horizon_permissions` will confirm that Discord is exposing Administrator to the bot. The bot does not attempt to grant itself permissions; permissions are controlled by the server owner/admin through Discord.

For prefix-based AI, Discord's **Message Content Intent** must remain enabled in the Developer Portal. Horizon already requests `message_content` and `members` intents in code.

## Website bridge

The dashboard exposes:

- `GET /health` — public health check
- `GET /api/overview?guild_id=...` — authenticated live server overview
- `GET /api/member?guild_id=...&user_id=...` — authenticated member profile data
- `POST /api/ai` — authenticated website-to-Horizon AI bridge

API requests require:

`X-Horizon-API-Key: <HORIZON_API_TOKEN>`

The website stores that token only in a Netlify serverless function. The Discord bot token and Gemini key never reach the browser.
