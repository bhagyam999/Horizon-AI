# Horizon RPG v14.1 — Phases 16–19

Built on v13 (Phases 10–15). Adds World Mysteries, World-Scale Events, World Memory, and the RPG integration/completion audit. No owner/OP commands and no fresh-start reset are introduced.


## v14.1 — Command Stability & Complete Help

- Added a 30-second timeout for prefix RPG commands so slow operations cannot appear permanently stuck.
- Added per-player RPG command locking to prevent overlapping state-changing commands from racing each other.
- Added a clear timeout message and Railway-friendly logging when an RPG command exceeds the limit.
- Rebuilt `!rpg help` as a complete paginated command browser. It discovers every registered RPG command, including nested group commands and aliases.
- Each help entry includes compact usage syntax and a short explanation. New commands automatically appear in help even if their description is not manually added.
- Removed the duplicate Endgame section from the `!rpg` home panel.
- No RPG data reset and no OP commands added.
