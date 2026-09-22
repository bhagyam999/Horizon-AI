# Horizon RPG v15 — Core Cleanup

**Current build:** v15 Core Cleanup. This is a deliberate cleanup release before the next deepening build. Removed player-facing NPC/story/living-world/housing/construction/life-path/advanced-diplomacy/mystery/anomaly/world-memory systems and the artificial world-event contribution layer. No new RPG systems were added in this release.

See `VERSION_V15_CLEANUP.md` for the exact scope.

---

# Horizon AI — Log Horizon Legendary RPG

## v11 — Phases 1–4 Completion Pass
See `PHASE1_4_PROGRESS.md` for the current completion work. This update preserves existing RPG data and does not perform another fresh start.

A persistent multiplayer RPG system for the Log Horizon Discord server.

## What this version adds

### Interactive combat
- `!rpg adventure` starts a live battle instead of instantly resolving the fight.
- `!rpg dungeon [name]` starts a floor-by-floor dungeon battle.
- The original Discord message is edited after every action.
- Buttons: **Attack**, **Skill**, **Potion/Food**, **Defend**, **Flee**.
- Dungeon floors advance only after the current enemy is defeated.
- Victory awards XP, gold and loot; level-ups visibly increase the character.

### Character progression
- 13+ races, 20+ classes, 20+ subraces/subclass choices and class evolution paths.
- Level growth: HP, MP, attack, defense and speed increase automatically.
- Skill points, stat points and talent points provide additional build choices.
- Paid identity changes:
  - `!rpg change race <race>`
  - `!rpg change subrace <subrace>`
  - `!rpg change class <class>`
  - `!rpg change subclass <subclass>`
  - `!rpg change path <path>`
  - `!rpg change evolution <evolution>`
- `!rpg evolve` shows currently unlocked evolutions.

### Life paths
Players can shape a social identity beyond combat:
- Adventurer
- Noble
- Royal
- Merchant
- Outlaw
- Thug
- Hunter
- Scholar
- Artisan
- Pirate

### World
- 12 areas ranging from Horizon Village to World Tree.
- `!rpg areas` shows the world atlas.
- `!rpg travel <area_key>` changes the character's current region.
- Regional exploration changes enemy/loot pools.

### Kingdoms
- Players can eventually found kingdoms.
- Kingdoms have rulers, members, treasury, renown and offices.
- Roles include **King, Duke, Count, Knight, Citizen and Outlaw**.
- Commands:
  - `!rpg kingdom list`
  - `!rpg kingdom create <name>`
  - `!rpg kingdom join <name>`
  - `!rpg kingdom info [name]`
  - `!rpg kingdom appoint @user <role>`
  - `!rpg kingdom leave`

### Items
The item catalog now contains several hundred generated and hand-defined items across:
- Weapons
- Armor
- Offhands
- Potions and elixirs
- Food
- Materials
- Relics
- Pet eggs

Use:
- `!rpg items all 1`
- `!rpg items weapon 1`
- `!rpg items armor 1`
- `!rpg items food 1`
- `!rpg items egg 1`
- `!rpg eggs`

### Pets and eggs
- Eggs can drop during adventures.
- Different egg rarities hatch different pet pools.
- `!rpg pet hatch <egg_key> <name>`
- `!rpg pet adopt <name>` remains available.
- `!rpg pet rename <name>` and `!rpg pet release` are supported.

### Existing systems preserved
- RPG guilds
- Parties
- Party dungeons
- Quests
- Crafting
- Gathering / fishing / mining
- Daily rewards
- Player market
- Equipment
- Achievements
- PvP duels
- Leaderboards
- Existing Horizon AI, moderation, games and dashboard modules

## Core RPG commands

```text
!rpg help
!rpg start <name> <race> <class>
!rpg profile
!rpg races
!rpg subraces [race]
!rpg classes
!rpg subclasses [class]
!rpg paths
!rpg change <race|subrace|class|subclass|path|evolution> <name>
!rpg evolve [evolution]
!rpg spend <stat> [points]

!rpg adventure
!rpg dungeon [name]
!rpg dungeons
!rpg areas
!rpg travel <area>

!rpg quests
!rpg quest <id>
!rpg claim <id>

!rpg party create <name>
!rpg party join <id>
!rpg party info [id]
!rpg party dungeon [name]
!rpg party leave

!rpg guild list
!rpg guild create <name>
!rpg guild join <name>
!rpg guild info [name]
!rpg guild members
!rpg guild deposit <gold>
!rpg guild upgrade
!rpg guild leave

!rpg kingdom list
!rpg kingdom create <name>
!rpg kingdom join <name>
!rpg kingdom info [name]
!rpg kingdom appoint @user <role>
!rpg kingdom leave

!rpg inventory
!rpg use <item_key> [qty]
!rpg items [category] [page]
!rpg eggs
!rpg equip <item_key>
!rpg shop
!rpg buy <item_key> [qty]
!rpg sell <item_key> [qty]
!rpg recipes
!rpg craft <item_key> [qty]
!rpg market
!rpg list <item> <qty> <price>
!rpg marketbuy <id>

!rpg gather
!rpg fish
!rpg mine
!rpg daily
!rpg rest
!rpg pet adopt <name>
!rpg pet hatch <egg_key> <name>
!rpg pet rename <name>
!rpg pet release
!rpg achievements
!rpg leaderboard
!rpg battle @user
!rpg bounty
```

## Running

1. Put the project on the deployment machine.
2. Create `.env` from your existing bot configuration and set `DISCORD_TOKEN` plus the existing Horizon provider/API variables.
3. Install dependencies from `requirements.txt`.
4. Run `python bot.py` (or use `start.bat` on Windows).

The RPG uses the same `horizon.db` database file and automatically creates/migrates its RPG tables on startup. Existing RPG data is retained when the new columns/tables are added.

## RPG Discord UI

RPG list/codex/collection commands use a persistent Discord embed panel rather than plain text. Panels support:
- First / previous / next / last page navigation
- A red 🗑️ delete button that removes the bot panel
- Owner-only interaction protection
- Automatic timeout of navigation controls while leaving the delete control usable
- `Info...` dropdowns on inventory, item codex and pet egg codex pages
- Command messages are removed after execution where Discord permissions allow it, keeping RPG channels clean

The interactive adventure/dungeon combat panel remains a single edited message and uses buttons for Attack, Skill, Potion/Food, Defend and Flee.

## Slash-command registration and Discord rate limits

Horizon deliberately does **not** synchronize slash commands during startup. Discord can rate-limit application-command registration, and waiting for a rate-limited sync inside `setup_hook()` can prevent the bot from ever reaching READY.

Existing slash commands remain available. When slash-command definitions actually need to be registered or updated, the bot owner can run:

- `!sync guild` — sync once to the configured `DISCORD_GUILD_ID` (recommended for Log Horizon)
- `!sync global` — sync once globally (Discord propagation can take longer)

The sync operation performs only one Discord command-registration request. A failed or rate-limited sync does not take the bot offline.


## Railway startup safety

Horizon intentionally does **not** synchronize Discord application/slash commands during startup. This prevents Discord command-registration rate limits from delaying or blocking the bot from reaching READY. Existing registered slash commands remain available.

When slash commands need to be added or changed, the owner can deliberately run:
- `!sync guild` — one guild sync request to the configured `DISCORD_GUILD_ID`.
- `!sync global` — one global sync request.

The bot never clears commands or performs multiple startup sync requests.

## v10 Combined Railway World

This release bundles the complete Log Horizon React/Vite website under `website/` with the Horizon Discord bot and serves the built site from the same Railway service. Railway uses `nixpacks.toml` to install Python/Node dependencies and build the website before starting `python bot.py`.

### Persistent AI memory
Horizon keeps a short rolling dialogue per Discord channel so members speaking together share the actual conversation context, while each message retains its speaker identity. Older public server history is indexed separately and retrieved only when relevant. Website conversations remain session-scoped. Use `!aiforget` or `/ai_forget` to clear the active AI dialogue for the current scope.

### RPG fixes
- `!rpg items` / `!rpg item` / `!rpg codex` opens a paginated item codex with an item-details menu.
- `!rpg use` opens a menu when no item key is supplied; it never picks a random consumable.
- Combat's Potion/Food button opens a private item picker instead of choosing an item automatically.
- Quest progress now caps at the target and changes to `complete` automatically.
- Dungeon floor victories count toward dungeon quests as each floor is cleared.
- Quest claiming/acceptance now prevents duplicate rewards.

## v10.5 RPG Combat & Collection Upgrade
- Turn-based PvE combat now shows HP, MP, stamina, ATK, DEF, SPD and Crit for the hero, plus enemy HP/ATK/DEF.
- Adventure and dungeon combat now use a four-skill active loadout selected from a much larger class skill library.
- Added `!rpg skills` to inspect the current class skill kit.
- Pets now grant real passive combat bonuses (HP/ATK/DEF/SPD/Crit) and a usable battle ability with a cooldown.
- Pet/egg storage was migrated safely with new passive-stat and ability columns.
- `!rpg pet`, `!rpg eggs`, `!rpg adopt`, `!rpg hatch`, `!rpg rename` and `!rpg release` remain simple.
- PvP is now turn-based: both players can Attack, choose individual Skills, use Pet Assist, Defend, or Surrender. PvP displays both heroes' bars/stats and character artwork.
- Character artwork is deterministic and changes when race, subrace, class, subclass or evolution changes. Equipment/name changes do not change the character artwork.
- Mob and pet artwork is deterministic by enemy/species.
- Existing RPG, AI, website, economy, quests, guilds, kingdoms, parties and other systems are preserved.

## v10.7 Combat Balance Update

- PvE enemies now scale to the hero's level and current world tier instead of becoming trivial at higher levels.
- Adventure and dungeon encounters use a level-aware enemy tier with HP/ATK/DEF/XP/gold scaling.
- Combat damage uses a defense mitigation curve and damage caps to prevent one-hit kills.
- Critical hits are capped at 35% chance and use a 1.5x multiplier instead of doubling damage.
- Skills now have 50 class-specific abilities with level unlocks, MP costs, cooldowns and controlled mechanics; only four can be active at once.
- Higher-level skills unlock at levels 5, 10, 15, 20, 25, 30, 40, 55 and 70.
- MP regenerates slowly each completed combat round; potions and dungeon-floor recovery remain available.
- Adventure/dungeon entries consume stamina so exploration cannot be spammed indefinitely.
- Combat actions are serialized per player and PvP actions per duel to prevent double-click/race-condition exploits.
- PvP uses the same damage philosophy and per-hit damage caps.
- Existing RPG systems, pets, eggs, AI, website, economy, quests, guilds, kingdoms, parties and other functionality are preserved.

## v10.8 Legendary RPG + AI Reliability Upgrade

This release builds on the complete v10.7 project; it is not a reduced rewrite.

### RPG systems
- 48 explorable areas with tiered level requirements and 100+ distinct enemy templates.
- 1,400+ classified RPG items generated from weapon, armor, offhand, accessory, ring, amulet, relic, consumable, food, material, egg and chest families.
- High-tier gear has level requirements, item abilities, enchantment slots and small percentage bonuses. Percentage bonuses are deliberately capped at 10% per stat aggregate.
- 12 equipment enchantments with persistent per-slot levels.
- Every class now has exactly 20 distinct skills. Characters start with 3 active skills, then unlock additional skills at larger level gaps (Lv 6, 11, 16, 22, 28, etc.). Each skill has its own mechanic, MP cost, cooldown, damage/healing information and buff/debuff details; a fourth active slot can be filled later.
- Players can have many unlocked skills but only 4 active skills at once using `!rpg equip-skill <skill_key> <1-4>`.
- Race abilities and class/race matchup modifiers are shown before selection and are intentionally mild so counters do not hard-lock builds.
- Race/class/subrace/subclass/path/evolution changes now require an explicit Confirm/Cancel interaction before gold is spent.
- Level XP now scales much more aggressively at higher levels.
- Gacha system uses earned in-game Gems, published rates, Epic/Mythic pity, single/ten-pulls, equipment, chests and pets.
- Pets are now a true collection: pets can be stored, equipped, unequipped and swapped without releasing the others.
- `!rpg items` and top-level `!items` / `!item` use a robust classified codex with detailed inspection.
- `!rpg help` now explains the systems, commands, loadouts and examples in detail.

### AI reliability and context
- Fixed the public server-history query so Horizon can actually retrieve indexed history instead of failing on a nonexistent database column.
- Discord AI keeps the strict latest 13-message rolling dialogue while using older public-server history separately when it is relevant.
- Speaker names and IDs remain attached to indexed messages so Horizon can distinguish members discussing one another.
- AI history backfill defaults are now 50 public channels × 250 messages per channel, still excluding private/staff channels and bot messages.
- Gemini's default model is now `gemini-2.5-flash`; an explicitly configured `GEMINI_MODEL` remains respected and the provider still performs model discovery/failover.


### v10.9 RPG progression changes
- Added `!rpg bounty claim <id>` and member-targeted bounty posting with `@player`. PvP defeats can automatically complete eligible player-targeted bounties.
- Added separate cooldowns: Gathering 30s, Mining 45s, Fishing 40s.
- Characters now start with exactly 3 skills; the old fourth starter slot is removed during migration.
- Skill catalogue reduced from 50 repetitive generated entries to 20 distinct combat mechanics per class.
- Skill unlocks are spaced across the level curve rather than every 1-2 levels.
- Skill views now show approximate damage/healing, MP cost, cooldown, buff and debuff information.
- Existing progression, gear, pets, gacha, quests, economy, website and AI systems are preserved.

## v10.10 RPG progression and art
- Stat Points are spent with `!rpg stat <stat>`.
- Skill Points are spent with `!rpg skill <skill_key>` to raise unlocked skill mastery to Rank 5.
- Talent Points are spent in separate class and race trees with `!rpg talent class <key>` or `!rpg talent race <key>`; `!rpg talents` shows both trees.
- Skill mastery gives small bounded scaling improvements rather than replacing level-based unlocks.
- RPG battle/profile art now uses a deterministic full-body PNG renderer based on race, subrace, class, subclass/evolution, mob identity and pet identity instead of random face-only avatars.
- The RPG art renderer requires Pillow.

## v10.11 RPG trading and art overhaul
- Added a secure direct player-to-player trading system with atomic transfer for item stacks, weapons, armor, offhands, accessories, relics, eggs/chests, pets, Gold and Diamonds (the existing RPG Gems currency).
- Trade flow: `!rpg trade @player` → add assets with `tradeadd`, `tradepet`, `tradegold`, `tradediamonds` → inspect with `tradeview` → the target accepts with `tradeaccept`. Either participant can cancel; `tradeclear` clears that participant's side.
- Trading validates ownership again at acceptance time and performs the entire exchange in one SQLite transaction, preventing partial transfers. Equipped pets must be unequipped first. If the final copy of equipped gear is traded away, its stale equipment/enchantment reference is removed safely.
- Added persistent trade tables and indexes; existing RPG databases migrate automatically through `CREATE TABLE IF NOT EXISTS` during startup.
- Replaced the previous simple procedural RPG art with a larger 1024×1024 identity renderer featuring layered lighting, gradients, particles, magic circles, armor/weapon silhouettes, race traits, class-specific weapons, pet archetypes, mob roles/elements and dedicated gear/item renders. The renderer remains deterministic so the same identity stays visually consistent.
- RPG art URLs now include a renderer version so Discord can refresh previously cached images after deployment.

## v10.13 RPG Item Catalogue Overhaul
- Replaced the repetitive elemental/enchantment-named gear catalogue with **14,000+ distinct base items**.
- Enchantments are now a separate system: item names never include an applied enchantment.
- Existing legacy elemental item keys remain valid for old inventories/trades, but display as neutral archive/base items with no embedded enchantment.
- `!rpg iteminfo <item_key>` now provides the **Full Preview**, including base stats, empty enchantment slots, and every enchantment compatible with that equipment slot.
- Enchantment application now validates slot compatibility before spending gold.

## v10.14 Phase 1 — Living World RPG

Phase 1 connects the existing RPG systems into a more active MMORPG-style world while preserving the existing economy, trading, pets, gear, talents, skills, guilds, parties, kingdoms and website.

### World map and exploration
- Added a connected 48-area world graph used by the World Map and Exploration systems.
- `!rpg map` / `!rpg worldmap` shows the current region, discovered regions and locked regions.
- `!rpg explore` discovers nearby level-appropriate regions and rewards exploration.
- Travel now records discovered regions and advances exploration quests/objectives.

### Multi-floor dungeons
- Expanded the dungeon atlas from 3 dungeons to 17 dungeons across the full level curve.
- Every dungeon has a final-floor boss with a unique identity.
- Final floors use stronger boss HP/ATK/DEF scaling and display a boss marker.
- Floor transitions restore a controlled amount of HP/MP and reset combat statuses/combos.
- `!rpg dungeons` lists dungeon requirements, floors, rewards and bosses.

### Status effects and combat combos
- Added persistent combat status tracking for Bleed, Poison, Burn, Freeze, Stun, Vulnerable and Weaken-style effects.
- Damage-over-time statuses tick independently and expire cleanly.
- Freeze can occasionally stun an enemy; weakened/silenced enemies deal reduced damage.
- Combat UI now displays active enemy statuses and the current combo counter.
- Added bounded skill-combo chains so compatible skill sequences can create small bonus damage without one-shotting enemies.

### World bosses
- Added persistent server-wide world boss events with 60-minute lifetimes.
- `!rpg worldboss` shows the active boss.
- `!rpg worldboss spawn` starts a world boss when none is active.
- `!rpg worldboss attack` performs a basic attack; `!rpg worldboss attack <skill_key>` uses an equipped skill.
- Boss HP, contribution damage and attack cooldowns are persisted in SQLite.
- Bosses change phases as HP falls and grant contribution rewards when defeated, with additional rewards for top contributors.

### Story quest chains
- Added three persistent multi-step story chains with prerequisites, rewards and world-boss/dungeon/exploration objectives.
- Story steps must be completed in order instead of being claimable all at once.
- Existing daily/weekly quest behavior remains compatible.

### Daily and weekly objectives
- Added persistent daily and weekly objective boards.
- `!rpg objectives` shows current progress and rewards.
- `!rpg objective <key>` claims a completed objective.
- Hunt, exploration, dungeon, gathering and world-boss activity automatically advances the relevant objectives.

## v10.14.1 hotfix
- Fixed duplicate `!rpg dungeons` command registration that caused Discord.py `CommandRegistrationError` at startup.
- Retained the Phase 1 dungeon atlas command with aliases and boss information.

## v10.14.2 — Interactive Equipment Loadout

- Added `!rpg equipment` with aliases `!rpg gear`, `!rpg loadout`, and `!rpg equipui`.
- Each visible equipment slot has its own Discord dropdown populated from the player's owned equipment for that slot.
- Supports Weapon, Armor, Offhand, Accessory, Ring, Amulet, and Relic slots.
- Selecting an item equips it immediately and keeps the loadout panel open.
- Each slot includes an Unequip option.
- Four equipment-slot dropdowns are shown per page with navigation for the remaining slots, respecting Discord's five action-row limit.
- Existing `!rpg equip <item_key>` remains available as a direct fallback.
- Preset loadouts are intentionally left for the next progression/economy phase.
