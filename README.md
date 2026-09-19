# Horizon AI — Log Horizon Legendary RPG

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
