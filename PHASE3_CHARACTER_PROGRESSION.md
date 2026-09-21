# Phase 3 — Character Progression

Phase 3 builds on the Phase 2 economy foundation.

## Implemented / carried forward
- Pet collection with multiple stored companions and equipped pet switching.
- Pet combat bonuses and pet abilities.
- Advanced character progression: levels, stat points, skill points, talent points, subclasses, subraces and class evolutions.
- Achievements and automatic achievement checks.
- Item Codex / item browser through `!rpg items`.
- Title collection storage and `!rpg titles`.
- Player housing record with a foundation for future upgrades.
- Phase 2 equipment upgrades, intrinsics, sets and Gear Vault remain intact.

## Owner-only OP console

The RPG OP system is deliberately separate from Discord Administrator permissions. A server moderator or Administrator cannot use it.

Set this environment variable to the owner's numeric Discord user ID:

`HORIZON_OWNER_ID=YOUR_DISCORD_USER_ID`

If it is missing or `0`, all OP commands are denied (fail closed).

Commands:
- `!rpg op` — show owner console
- `!rpg op-maxlevel [@user]` — set a hero to level 100
- `!rpg op-maxstats [@user]` — max combat/progression stats
- `!rpg op-item <item_key> [quantity] [@user]` — grant any registered item
- `!rpg op-allitems [@user]` — grant one of every registered item
- `!rpg op-gold <amount> [@user]` — grant gold
- `!rpg op-gems <amount> [@user]` — grant gems
- `!rpg op-title <title_key> [@user]` — unlock a title
- `!rpg op-housing [@user]` — initialize/view housing
- `!rpg op-killboss` — instantly defeat the active world boss

These grants are recorded where the existing economy system supports audit logging.
