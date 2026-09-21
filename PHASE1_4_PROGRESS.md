# Horizon RPG v11 — Phases 1–4 Completion Pass

This release starts the focused completion pass for the first four RPG phases on top of the working v10.14.2 Phase 5 build. No RPG wipe is introduced.

## Phase 1 — Character & RPG Foundation
- Existing race/class/subrace/subclass/evolution/talent/skill systems retained.
- Secret classes remain locked behind their existing Phase 5 awakening system.
- Character progression, stat points, skill mastery and talent points remain persistent.

## Phase 2 — World & Exploration
- Travel is now connected-route aware: undiscovered distant regions cannot be teleported to directly.
- Adjacent routes can be reached and previously discovered routes can be revisited.
- Travel now consumes a small stamina amount based on level-distance, while exploration remains the discovery mechanism.
- Existing regional enemy pools, discoveries, dungeons and world bosses are preserved.

## Phase 3 — Complete Combat
- Interactive combat remains the single engine for adventure and dungeons.
- Combat sessions are now persisted in SQLite.
- If the bot restarts during a battle, the player's battle can be restored for up to 45 minutes instead of silently disappearing.
- Finished, fled and defeated battles remove their persisted session.

## Phase 4 — Items & Equipment
- Existing level requirements, rarity, intrinsic properties, equipment sets, upgrades, enchantments and Gear Vault remain intact.
- No existing equipped gear is wiped by this release.
- Equipment continues to feed directly into the combat-stat calculation.

## Compatibility
- Existing `horizon.db` data is retained.
- A new `rpg_combat_sessions` table is created automatically.
- No owner/OP system is reintroduced.
- No Phase 4 fresh-start migration is repeated.

## Verification
- Python syntax was checked for the modified Python modules.
- Full live SQLite startup testing could not be executed in the build environment because `aiosqlite` is not installed there and the environment has no package-network access. Railway/local deployment should install dependencies from `requirements.txt` before startup.
