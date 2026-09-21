# Phase 5 — Endgame

Phase 5 adds the final endgame layer to Horizon without removing the Phase 4 living-world systems.

## Included

### PvP Arenas
- Ranked player-vs-player arena using the existing turn-based combat engine.
- 30-day PvP seasons with separate ratings, wins, losses, streaks and best rating.
- ELO-style rating changes after each ranked match.
- `!rpg arena [@player]`
- `!rpg season`

### PvP seasons
- A new season is created automatically when the current 30-day period changes.
- Old seasons remain in the database for historical records.

### Server Raid Bosses
- A weekly shared Raid Boss for the whole Discord server.
- Every player attacks the same HP pool.
- Personal damage, attack count and contribution leaderboard are recorded.
- Contributors receive rewards when the raid is defeated; high contributors can receive Dragon Trophies.
- `!rpg raid`
- `!rpg raid attack`

### Secret classes
Four hidden classes are available:
- Void Knight — Level 50 + 800 Renown
- Chronomancer — Level 45 + 10 Arena wins
- Dragon Lord — Level 60 + 100,000 total Raid damage
- Soul Reaper — Level 55 + 2 completed hidden quests

They are hidden from normal character creation and can only be awakened with `!rpg awaken <class_key>` after the requirements are met.

### Legendary endgame
Four repeatable legendary trials were added:
- Abyssal Throne
- End of the Chronicle
- Dragon Throne
- The Last Soul

Each has a level requirement, a combat-power trial, a 24-hour personal cooldown, XP/gold rewards, and a unique legendary/mythic reward item.

Commands:
- `!rpg legendary`
- `!rpg challenge <challenge_key>`

## Fresh-start behavior

Phase 5 does **not** perform another RPG wipe. The Phase 4 fresh-start marker remains authoritative, so existing Phase 4 progress is preserved when the bot restarts or deploys.

The old owner-only OP console remains removed. No `HORIZON_OWNER_ID` variable is read by the Phase 5 RPG code.
