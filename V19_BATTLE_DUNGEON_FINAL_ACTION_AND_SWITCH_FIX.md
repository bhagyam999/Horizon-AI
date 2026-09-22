# v19 Battle / Dungeon Final-Action & Selection Fix

## Fixes
- Selecting a different unlocked dungeon now abandons the old temporary run and starts the requested dungeon instead of trapping the player in the previous dungeon.
- The authoritative persistent combat state is recovered if the in-memory cache is missing.
- Expired Discord combat views no longer remove the live in-memory combat state; their controls are disabled while the battle remains recoverable.
- A completed enemy state is guarded so a stale component cannot trigger another enemy turn after the battle is already over.
- Existing all-floor Flee behavior remains intact.
- Existing no-command-deletion, race/class/equipment balancing, and prior battle/dungeon fixes are preserved.

## Validation
- `py_compile` passed for `rpg.py` and `bot.py`.
- `compileall` passed.
