# Phase 4 — Living World

Phase 4 adds a persistent living-world layer to Horizon:

- 🌎 Server-wide community events
- 🧙 NPCs with relationship affinity and stages
- 🕵️ Hidden quests unlocked through NPC relationships
- 📖 Discoverable lore/codex entries
- 🧠 NPC conversation hooks (deterministic dialogue now; Gemini-ready through the bot AI layer)
- 🏰 Guilds remain available and were reset for a fresh season

## New commands

- `!rpg npcs` — list living-world NPCs
- `!rpg talk <npc_key> [message]` — talk to an NPC and build affinity
- `!rpg lore` — show discovered/undiscovered lore
- `!rpg lore <key>` — read a discovered lore entry
- `!rpg hidden` — inspect hidden-quest states
- `!rpg events` — show server-wide events
- `!rpg contribute <event_id> [amount]` — contribute to a live event

## Fresh start

The first Phase 4 startup performs a one-time RPG reset. It clears RPG characters, inventories, equipment, economy, pets, achievements, titles, housing, quests, guilds, parties, kingdoms, bounties, world events, and Phase 4 player discoveries. It does **not** clear the Discord server configuration, moderation records, or the AI/server chat history stored outside the RPG tables.

The reset is protected by `horizon_rpg_migrations` and runs only once. Subsequent Railway restarts do not wipe progress.

## OP command removal

The Phase 3 owner-only RPG OP console has been completely removed. `HORIZON_OWNER_ID` is no longer read by the bot.
