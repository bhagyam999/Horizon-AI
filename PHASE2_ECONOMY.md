# Phase 2 — Economy

This build starts Phase 2 from the existing Horizon RPG foundation.

## Implemented

### Player marketplace
- Listings escrow stackable items immediately.
- Buying and cancelling are atomic SQLite transactions.
- A seller cannot buy their own listing.
- Sold/cancelled listings cannot be replayed.
- Listing IDs have unique tokens for auditability.
- Unique upgraded equipment is intentionally kept out of the stack marketplace until full item-instance trading is enabled; direct `!rpg trade` remains available for unique gear.

Commands:
- `!rpg market`
- `!rpg list <item_key> <quantity> <price>`
- `!rpg marketbuy <listing_id>`
- `!rpg marketcancel <listing_id>`

### Crafting
- Crafting now runs inside one transaction.
- Materials are checked and consumed atomically.
- Output is created in the same transaction.
- Material consumption and output are written to the economy audit log.

Commands:
- `!rpg recipes`
- `!rpg craft <item_key> <quantity>`

### Equipment upgrades
- Equipped gear can be upgraded from +0 to +15.
- Upgrade cost scales with current upgrade level and rarity.
- Upgrade materials depend on rarity.
- Upgrades are deterministic and never destroy the item.

Command:
- `!rpg upgrade <weapon|armor|offhand|accessory|ring|amulet|relic>`

### Intrinsic properties
- Equipping gear creates a unique gear state.
- Properties are rolled once based on rarity and persisted in the database.
- Properties are not rerolled on restart.
- Existing legacy equipment receives a one-time intrinsic migration.

### Equipment sets
- Gear with the same generated equipment family forms a set.
- 2-piece, 4-piece and 6-piece thresholds provide modest bonuses.
- Set focus is deterministic, so a set remains consistent across restarts.

Command:
- `!rpg sets`

### Economy audit / anti-duplication
- Economy mutations are recorded in `rpg_economy_log`.
- Marketplace escrow, purchase and cancellation are atomic.
- Crafting is atomic.
- Equipment upgrades consume gold/materials and update the gear in one transaction.
- Unique gear that is replaced or unequipped is preserved in the Gear Vault instead of being flattened into a normal item stack.

Commands:
- `!rpg economy [limit]`
- `!rpg vault`
- `!rpg vaultequip <vault_id>`

## Important Phase 2 boundary

The stack marketplace intentionally does not accept unique equipment yet. This avoids the classic MMO duplication/loss problem where an upgraded sword is represented only by its base item key. The next economy milestone should introduce first-class item instances for inventory, marketplace listings and direct trades so every unique weapon/armor piece has a permanent identity.
