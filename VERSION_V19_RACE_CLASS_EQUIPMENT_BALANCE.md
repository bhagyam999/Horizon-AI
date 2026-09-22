# Horizon RPG v19 — Race, Class & Equipment Balance

## Goals
- Make race identity mechanically meaningful, not cosmetic.
- Make class skills mechanically distinct instead of renamed copies.
- Keep at least 10 meaningful skills per class.
- Make strengths and weaknesses obvious before character selection.
- Fix equipment unequip so gear is returned instead of disappearing.

## Race changes
- Added explicit race strength/weakness profiles.
- PvP race matchup modifiers are more noticeable but capped so counters do not hard-lock builds.
- Vampire Blood Hunger increased from 8% lifesteal to 28% damage dealt, with a minimum 4 HP and a cap of 8% max HP per hit.
- Race descriptions and the race preview now show core strengths, weaknesses and matchup advantages/disadvantages.

## Class changes
- Added explicit class strength/weakness profiles for all 20 normal classes and 4 secret classes.
- Every class retains 20 stable skill slots for save compatibility.
- The first 12 skills are class-defining and use different mechanics by class.
- Secondary skills 13–20 also use a deterministic class-specific rotation rather than one shared generic list.
- Existing active skill slots remain compatible because skill keys stay `skill_1` through `skill_20`.
- Skills continue to be limited to four active skills at a time.

## Equipment fix
- Added persistent `rpg_equipment_instances` records.
- Unequipping now returns the item to inventory and preserves its exact intrinsic rolls, upgrade level, set information and enchantment.
- Equipping the returned item restores the same instance instead of rerolling its properties.
- Replacing equipped gear also returns the previous gear to inventory while preserving its instance data.
- Gear Vault remains available for intentionally stored equipment.

## Compatibility
- A v19 startup migration removes only skill-loadout keys that no longer exist.
- No systems removed during v15 were reintroduced.
- No NPC, story, living-world, housing, anomaly, advanced-life-path, advanced-diplomacy, manual-memory or world-event-contribution systems were added.
