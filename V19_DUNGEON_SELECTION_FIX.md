# v19 Dungeon Selection Fix

## Fix
Players can now return to any dungeon they have unlocked after completing or fleeing their current dungeon run.

Previously, `start_combat()` always resumed the persisted combat session before considering the dungeon name supplied to `!rpg dungeon <name>`. That meant requesting a different dungeon while a saved run existed simply reopened the old run.

## New behavior
- `!rpg dungeons` lists dungeon options.
- `!rpg dungeon <name>` starts the requested unlocked dungeon when no run is active.
- If a run is active, requesting a different dungeon tells the player to finish or flee first.
- Requesting the same dungeon resumes the existing run after a UI timeout/restart.
- Fleeing from any floor clears the dungeon run, after which another unlocked dungeon can be selected.
