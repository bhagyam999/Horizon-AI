# v19 Battle & Dungeon Stability Fix

- Battle recovery now checks the persisted combat session before rejecting a player for an in-memory active battle flag.
- Timed-out Discord combat views no longer permanently trap a player: the saved battle can be resumed by running the adventure/dungeon command again.
- Invalid or already-completed persisted battle states are cleared instead of leaving a permanent "already in a battle" lock.
- Dungeon flee is now allowed from every floor, not only floor 1. Fleeing abandons the dungeon run and gives no dungeon-clear reward.
- Existing v19 race/class/equipment balance and no-command-deletion changes are preserved.
