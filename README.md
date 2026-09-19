# Horizon AI — Log Horizon Discord Core

Horizon is the Discord-side community core for **Log Horizon**.

## Current build

Horizon is built as a low-noise, prefix-first Discord bot. Slash commands remain available for compatibility, but everyday server interaction uses `!` commands similar to established multipurpose Discord bots.

### AI

- `!ai <message>` — talk to Horizon anywhere in the server
- `!h <message>` and `!horizon <message>` — aliases
- `!ask <question>` — ask Horizon directly
- `!aistatus` — provider status
- `!aimodels` — available Gemini models
- No dedicated AI channel is used. Normal mentions stay normal Discord mentions.

### Games

- `!games` — game hub
- `!game <name>` — launch a game with one reusable game message
- `!stop` — stop the active game
- `!join` / `!begin` — Werewolf/Mafia lobby
- `!guess <letter>` — Hangman; Horizon edits the original game message
- `!rps <rock|paper|scissors>` — immediate RPS
- `!vote @player`, `!dayend`, `!nightend` — hidden-role controls
- Trivia, Would You Rather and Truth or Dare use buttons where buttons are useful.
- Mafia/Werewolf roles and night actions are sent through DMs; public game state is kept in one channel message.

### Server / moderation

- `!help [category]` — categorized command guide
- `!config show` — server configuration summary
- `!config welcome #channel` — welcome destination
- `!config logs #channel` — moderation-log destination
- `!mod on|off` and `!modaction log|warn|timeout`
- `!warn`, `!warnings`, `!clear`, `!timeout`, `!kick`, `!ban`
- `!serverinfo`, `!userinfo`, `!avatar`, `!channelinfo`, `!permissions`

### Typed announcements

There is no fixed announcement channel command. Each announcement chooses its **type, ping and destination** when it is sent.

Prefix format:

`!announce <type> <ping> [#channel] | <title> | <message>`

Available types include:

`general` · `event` · `tournament` · `game` · `community` · `update` · `important` · `warning` · `maintenance` · `giveaway` · `news`

Examples:

- `!announce tournament @Tournament #events | Anigame Tournament | Sign-ups open Saturday at 8 PM IST.`
- `!announce event none #events | Game Night | Join us tonight for community games.`
- `!announce important @everyone | Server Update | The rules have been updated.`

The same typed announcement system is available through `/announce`, with Discord's native channel picker. `@everyone`/`@here` and role pings are permission-checked.

### RPG / community

- `!profile`, `!character`, `!rpgroll`, `!inventory`, `!daily`, `!leaderboard`
- `!questcreate`, `!questlist`
- `!eventcreate`, `!eventlist`, `!eventjoin`
- Server facts/personality: `!remember`, `!forget`, `!memories`, `!personality`

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
