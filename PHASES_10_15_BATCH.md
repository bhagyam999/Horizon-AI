# Horizon RPG v13 — Phases 10–15 Batch

This batch continues from v12.1 and is additive. It does not reset RPG player data and does not reintroduce RPG owner/OP commands.

## Phase 10 — Quests & Progression
- Added a persistent Quest Journal summary.
- Existing daily/weekly quests and story chains remain intact.
- Story-chain progress is surfaced by chain and step.
- Quest data remains server-scoped and player-scoped.

Commands:
- `!rpg journal`
- `!rpg quests`
- `!rpg quest <id>`

## Phase 11 — Living World
- Added persistent world state per Discord server.
- World clock with a continuously changing hour/day.
- Four rotating seasons.
- Deterministic changing weather states.
- NPC schedule data and current-hour activity.
- Expiring world rumors.

Commands:
- `!rpg worldstate`
- `!rpg rumors`

## Phase 12 — World Memory & Story
- Added player story memory.
- Story choices are persisted instead of being temporary messages.
- Added Chronicle event storage for important player/world events.
- Story choices currently create a branch record that can be expanded by later story content.

Commands:
- `!rpg story`
- `!rpg storychoose <guard|merchant|arcane|wild>`
- `!rpg chronicle`

## Phase 13 — Player-Built World
- Added player structures tied to the player's current region.
- Added resource-cost construction.
- Added server-wide construction projects.
- Project contributions are tracked per player.
- Completing a server project grants its configured reward.

Commands:
- `!rpg structures`
- `!rpg build <camp|workshop|watchtower|shrine|market_stall>`
- `!rpg projects`
- `!rpg project <id> <gold>`

## Phase 14 — Factions & Politics
- Added four server-scoped factions:
  - Horizon Guard
  - Free Merchants
  - Arcane Circle
  - Wildbound
- Persistent faction membership and reputation.
- Reputation-based faction ranks.
- Persistent faction diplomacy relations.
- Diplomacy requires 1000 faction reputation.

Commands:
- `!rpg factions`
- `!rpg factionjoin <faction_key>`
- `!rpg factionrep <amount>`
- `!rpg factiondiplomacy <faction_key> <allied|neutral|rival>`

## Phase 15 — Endgame Expansion
- Added persistent Endgame Mastery.
- Mastery is derived from existing endgame achievements: legendary clears, secret classes, raid damage and arena rating.
- Added Ascension progression up to the current cap of 5.
- Ascension requires level 80 and 100 Endgame Mastery.
- Ascension grants Renown and Fame and records the event in the Chronicle.

Commands:
- `!rpg endgamemastery`
- `!rpg ascend`

## Safety / compatibility
- No RPG database wipe.
- Existing Phase 1–9 systems are preserved.
- No RPG OP command system added.
- New tables are created with `CREATE TABLE IF NOT EXISTS`.
- New command names/aliases were checked against existing `!rpg` root registrations.
- Python syntax compilation passes for `rpg.py` and `bot.py`.
- The build environment still lacks `aiosqlite`, so a live Discord/SQLite startup could not be executed here. Railway should be used for the final integration test.
