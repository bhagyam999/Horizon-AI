# Horizon RPG — v12 Phases 5–9 Batch

This batch continues from the v11 Phases 1–4 completion pass. It is additive and does **not** wipe RPG data.

## Phase 5 — Crafting & Gathering
- Added persistent profession progression: Gathering, Mining, Fishing, Crafting.
- Gathering/mining/fishing now grant profession XP.
- Gathering profession level 10+ can increase material yield.
- Crafting grants Crafting XP and uses the existing atomic inventory/economy-log flow.
- Added `!rpg professions`.
- Existing recipes, materials, shop and gathering commands remain compatible.

## Phase 6 — Economy
- Added personal economy summary through `!rpg economy`.
- Existing economy logs now feed earned/spent/event statistics.
- Market purchases remain atomic and now apply a 5% market fee to the seller payout.
- Buyer pays the listed total; seller receives the net amount; the fee is logged.
- Existing escrow/cancel behavior remains in place.

## Phase 7 — Pets & Collection
- Pet inventory gains persistent bond, mood and total XP fields.
- Added pet feeding with XP/bond progression: `!rpg petfeed [pet_id]`.
- Pets can level up from earned pet XP, increasing their passive stats.
- Added a persistent species collection/codex: `!rpg petcollection`.
- Existing pet inventory, eggs, adoption, equipping and gacha remain compatible.

## Phase 8 — Player Life
- Housing now has an actual upgrade path: `!rpg house-upgrade`.
- House upgrades increase storage capacity bonus and comfort.
- Added life-path selection: `!rpg life-path <adventurer|merchant|craftsman|scholar|ruler>`.
- Existing life_path, housing, titles and achievements remain compatible.

## Phase 9 — Social Systems
- Added persistent social reputation statistics.
- Successful party dungeon clears count toward party activity.
- Guild treasury contributions count toward guild contribution activity.
- Completed player trades count toward social trade activity.
- Added `!rpg social`.
- Existing parties, guilds, direct trades, kingdoms and bounties remain intact.

## Data safety
- No RPG reset is performed by this batch.
- New tables/columns are created through lightweight migrations.
- Existing Phase 1–5 systems remain in the project.
- OP/admin RPG commands are not reintroduced.

## Verification
- Python syntax validation completed for `rpg.py` and `bot.py`.
- Full live SQLite startup test was not possible in the build environment because `aiosqlite` is not installed there. Test the bot against the project's normal `requirements.txt` environment before deployment.
