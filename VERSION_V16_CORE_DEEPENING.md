# Horizon RPG v16 — Core Deepening & Balance

This release deepens the systems deliberately kept after the v15 cleanup. It does **not** restore the retired NPC, story, living-world, housing, construction, advanced life-path, advanced diplomacy, mystery, anomaly, manual world-memory, or world-event-contribution systems.

## Core loop strengthened
Create Hero → Explore → Encounter → Fight → Loot → Equip → Upgrade/Craft → Grow → Harder Content → Dungeons/Raids → Endgame.

## Changes

### Character & progression
- Preserves class/race/subclass/evolution/talent/stat progression.
- Exploration now awards Renown/Fame as well as XP/Gold.
- Combat victories award small Renown/Fame and contribute Pet XP.
- Stamina now regenerates passively at 1 point per 90 seconds, with Rest still restoring the full pool.

### Exploration & world
- Exploring costs 6 stamina.
- New discoveries provide XP, Gold, Renown, Fame, and a regional resource.
- Re-exploring discovered routes can still find regional resources.
- Regional resource pools make location matter without adding a new world simulation layer.

### Combat & loot
- Existing live combat remains the main combat engine.
- Victories can now produce a small chance of level-appropriate equipment in addition to material/egg drops.
- Bonus gear is strongly weighted toward common/uncommon/rare so normal combat does not flood players with endgame gear.
- Dungeon/adventure stamina costs remain meaningful.

### Equipment & crafting
- Expanded crafting from the old four meaningful recipes into a progression-oriented recipe set.
- Crafting recipes now support crafting level requirements, gold fees, stamina costs, and profession XP.
- Added Stamina Tonic, Hearty Stew, Arcane Tonic, and Reinforcement Core.
- Epic equipment upgrades now consume Reinforcement Cores, connecting gathering → crafting → upgrades.
- Existing deterministic +0→+15 upgrade system remains intact.

### Economy
- Shop inventory is level-aware so players are less likely to buy unusable gear.
- Merchant faction membership provides a small shop discount and better sale value.
- Shop purchases/sales are recorded in the economy log.
- Player-market listings have a small listing fee; completed sales keep the existing market tax.
- Daily reward income was slightly normalized to reduce passive economy inflation.

### Factions
- Basic faction membership remains.
- Direct reputation editing and diplomacy remain removed.
- Each faction now has a small passive identity:
  - Horizon Guard — defense/potion utility
  - Free Merchants — shop/sale economy utility
  - Arcane Circle — skill/crafting utility
  - Wildbound — gathering utility

### Pets
- Pet feeding now grants real Pet XP without relying on the retired-style bond/mood mechanics.
- Equipped pets gain Pet XP from successful combat.
- Pet levels continue to increase their combat contribution.

### Gacha
- Equipment rewards are now level-aware, reducing unusable early-game gear drops while preserving rarity/pity behavior.

## Validation
- Python AST parsing: passed for `rpg.py`, `bot.py`, and `database.py`.
- Python bytecode compilation: passed.
- RPG root command-name audit: no duplicate RPG root names found in the post-cleanup command inventory.
- Removed-system command references: no references found in `bot.py` to the retired v15 command functions.
- Full runtime import was not performed because the build environment does not have `aiosqlite` installed and network access is unavailable for installing it.
