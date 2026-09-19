from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any

import aiosqlite
import discord


RACES = {
    "human": {"hp": 0, "atk": 0, "def": 0, "spd": 0, "crit": 2, "desc": "Balanced. Humans adapt to almost any build."},
    "elf": {"hp": -5, "atk": 2, "def": 0, "spd": 3, "crit": 5, "desc": "Fast and precise. Higher critical chance."},
    "dwarf": {"hp": 20, "atk": 1, "def": 5, "spd": -2, "crit": 0, "desc": "Tough and sturdy. Excellent defense and health."},
    "orc": {"hp": 10, "atk": 5, "def": -1, "spd": -1, "crit": 0, "desc": "Brutal strength. More attack, less finesse."},
    "kitsune": {"hp": -5, "atk": 3, "def": 0, "spd": 2, "crit": 3, "desc": "Trickster spirit. Fast with strong crit potential."},
}

CLASSES = {
    "warrior": {"hp": 30, "mp": 5, "atk": 7, "def": 7, "spd": 0, "crit": 2, "resource": "Rage", "desc": "Front-line fighter with strong defense."},
    "mage": {"hp": 0, "mp": 35, "atk": 9, "def": 1, "spd": 1, "crit": 3, "resource": "Mana", "desc": "High magical damage and powerful skills."},
    "rogue": {"hp": 5, "mp": 10, "atk": 7, "def": 2, "spd": 7, "crit": 8, "resource": "Energy", "desc": "Fast striker built around crits and evasion."},
    "ranger": {"hp": 10, "mp": 15, "atk": 8, "def": 3, "spd": 5, "crit": 5, "resource": "Focus", "desc": "Reliable ranged damage and speed."},
    "paladin": {"hp": 35, "mp": 20, "atk": 5, "def": 8, "spd": -1, "crit": 1, "resource": "Faith", "desc": "Tanky hybrid with healing utility."},
    "summoner": {"hp": 5, "mp": 30, "atk": 6, "def": 3, "spd": 2, "crit": 3, "resource": "Mana", "desc": "Controls summoned companions and sustained damage."},
}

RARITIES = {
    "common": (1.00, "Common"),
    "uncommon": (1.20, "Uncommon"),
    "rare": (1.50, "Rare"),
    "epic": (2.00, "Epic"),
    "legendary": (3.00, "Legendary"),
    "mythic": (4.50, "Mythic"),
}

ITEMS = {
    "iron_sword": {"name": "Iron Sword", "slot": "weapon", "rarity": "common", "atk": 8, "price": 120},
    "oak_staff": {"name": "Oak Staff", "slot": "weapon", "rarity": "common", "atk": 7, "mp": 10, "price": 130},
    "hunter_bow": {"name": "Hunter Bow", "slot": "weapon", "rarity": "common", "atk": 7, "crit": 3, "price": 130},
    "steel_blade": {"name": "Steel Blade", "slot": "weapon", "rarity": "rare", "atk": 18, "price": 420},
    "apprentice_robe": {"name": "Apprentice Robe", "slot": "armor", "rarity": "common", "def": 4, "mp": 15, "price": 150},
    "iron_armor": {"name": "Iron Armor", "slot": "armor", "rarity": "common", "def": 9, "hp": 15, "price": 180},
    "shadow_cloak": {"name": "Shadow Cloak", "slot": "armor", "rarity": "rare", "def": 6, "spd": 7, "crit": 4, "price": 420},
    "guardian_shield": {"name": "Guardian Shield", "slot": "offhand", "rarity": "rare", "def": 14, "hp": 20, "price": 450},
    "life_potion": {"name": "Life Potion", "slot": "consumable", "rarity": "common", "heal": 35, "price": 50},
    "mana_potion": {"name": "Mana Potion", "slot": "consumable", "rarity": "common", "mana": 30, "price": 55},
    "wolf_pelt": {"name": "Wolf Pelt", "slot": "material", "rarity": "common", "price": 18},
    "iron_ore": {"name": "Iron Ore", "slot": "material", "rarity": "common", "price": 20},
    "herb": {"name": "Moon Herb", "slot": "material", "rarity": "common", "price": 15},
    "arcane_shard": {"name": "Arcane Shard", "slot": "material", "rarity": "rare", "price": 120},
}


# ---------------------------------------------------------------------------
# Expanded world data.  The catalog is generated from themed templates so the
# game has hundreds of usable, searchable items without a giant hand-written
# wall of repetitive dictionaries.
# ---------------------------------------------------------------------------
RACES.update({
    "halfling": {"hp": -8, "atk": 1, "def": 0, "spd": 5, "crit": 5, "desc": "Small, lucky and exceptionally nimble."},
    "tiefling": {"hp": 0, "atk": 4, "def": -1, "spd": 2, "crit": 4, "desc": "Infernal-blooded spellblade with natural power."},
    "dragonkin": {"hp": 20, "atk": 5, "def": 3, "spd": -1, "crit": 2, "desc": "Draconic blood grants power and resilience."},
    "beastfolk": {"hp": 5, "atk": 2, "def": 1, "spd": 4, "crit": 4, "desc": "Animal traits sharpen senses and movement."},
    "fae": {"hp": -10, "atk": 3, "def": 0, "spd": 6, "crit": 6, "desc": "Fey-born and elusive, with strong magical affinity."},
    "vampire": {"hp": 15, "atk": 5, "def": 2, "spd": 3, "crit": 5, "desc": "A cursed immortal race that thrives at night."},
    "golem": {"hp": 45, "atk": 4, "def": 9, "spd": -5, "crit": 0, "desc": "Living stone built to endure devastating punishment."},
})

SUBRACES = {
    "high_elf": ("elf", {"hp": 0, "atk": 2, "def": 0, "spd": 1, "crit": 2}),
    "wood_elf": ("elf", {"hp": 5, "atk": 1, "def": 0, "spd": 3, "crit": 1}),
    "dark_elf": ("elf", {"hp": -2, "atk": 4, "def": -1, "spd": 2, "crit": 3}),
    "mountain_dwarf": ("dwarf", {"hp": 12, "atk": 1, "def": 3, "spd": -1, "crit": 0}),
    "hill_dwarf": ("dwarf", {"hp": 18, "atk": 0, "def": 2, "spd": -2, "crit": 0}),
    "forest_dwarf": ("dwarf", {"hp": 6, "atk": 2, "def": 1, "spd": 0, "crit": 1}),
    "high_orc": ("orc", {"hp": 8, "atk": 3, "def": 1, "spd": -1, "crit": 0}),
    "half_orc": ("orc", {"hp": 4, "atk": 2, "def": 2, "spd": 1, "crit": 1}),
    "red_kitsune": ("kitsune", {"hp": 0, "atk": 4, "def": -1, "spd": 2, "crit": 4}),
    "white_kitsune": ("kitsune", {"hp": 3, "atk": 1, "def": 1, "spd": 3, "crit": 3}),
    "dragonborn": ("dragonkin", {"hp": 10, "atk": 3, "def": 2, "spd": 0, "crit": 1}),
    "drakeborn": ("dragonkin", {"hp": 15, "atk": 4, "def": 1, "spd": -1, "crit": 2}),
    "catfolk": ("beastfolk", {"hp": 0, "atk": 2, "def": 0, "spd": 5, "crit": 3}),
    "wolfkin": ("beastfolk", {"hp": 6, "atk": 3, "def": 1, "spd": 3, "crit": 2}),
    "foxkin": ("beastfolk", {"hp": -2, "atk": 3, "def": 0, "spd": 4, "crit": 5}),
    "spring_fae": ("fae", {"hp": 0, "atk": 2, "def": 1, "spd": 3, "crit": 3}),
    "night_fae": ("fae", {"hp": -2, "atk": 5, "def": -1, "spd": 4, "crit": 5}),
    "blood_vampire": ("vampire", {"hp": 10, "atk": 3, "def": 2, "spd": 2, "crit": 3}),
    "noble_vampire": ("vampire", {"hp": 5, "atk": 5, "def": 1, "spd": 3, "crit": 4}),
    "iron_golem": ("golem", {"hp": 25, "atk": 2, "def": 5, "spd": -2, "crit": 0}),
    "crystal_golem": ("golem", {"hp": 10, "atk": 5, "def": 3, "spd": -1, "crit": 1}),
    "storm_human": ("human", {"hp": 0, "atk": 2, "def": 0, "spd": 3, "crit": 3}),
    "desert_human": ("human", {"hp": 5, "atk": 1, "def": 2, "spd": 1, "crit": 1}),
}

CLASSES.update({
    "berserker": {"hp": 45, "mp": 5, "atk": 11, "def": 3, "spd": 1, "crit": 5, "resource": "Rage", "desc": "High-risk melee fighter that trades defense for explosive damage."},
    "knight": {"hp": 40, "mp": 10, "atk": 7, "def": 10, "spd": -1, "crit": 1, "resource": "Valor", "desc": "Armored protector built to survive and guard allies."},
    "assassin": {"hp": 0, "mp": 15, "atk": 10, "def": 1, "spd": 10, "crit": 12, "resource": "Energy", "desc": "Extreme speed and critical-hit specialist."},
    "cleric": {"hp": 20, "mp": 35, "atk": 5, "def": 5, "spd": 0, "crit": 2, "resource": "Faith", "desc": "Support caster with healing and holy damage."},
    "druid": {"hp": 15, "mp": 30, "atk": 7, "def": 4, "spd": 2, "crit": 3, "resource": "Nature", "desc": "Nature caster who shifts between offense and support."},
    "monk": {"hp": 20, "mp": 15, "atk": 8, "def": 5, "spd": 8, "crit": 6, "resource": "Chi", "desc": "Martial artist focused on speed, combos and counterattacks."},
    "bard": {"hp": 10, "mp": 30, "atk": 6, "def": 3, "spd": 5, "crit": 5, "resource": "Inspiration", "desc": "Battle musician who buffs allies and disrupts foes."},
    "necromancer": {"hp": 0, "mp": 45, "atk": 10, "def": 0, "spd": 1, "crit": 4, "resource": "Soul", "desc": "Dark caster who commands the dead."},
    "warlock": {"hp": 10, "mp": 40, "atk": 11, "def": 1, "spd": 2, "crit": 5, "resource": "Pact", "desc": "Forbidden magic specialist powered by risky bargains."},
    "alchemist": {"hp": 10, "mp": 25, "atk": 6, "def": 3, "spd": 4, "crit": 4, "resource": "Catalyst", "desc": "Potion, bomb and transmutation expert."},
    "engineer": {"hp": 20, "mp": 20, "atk": 7, "def": 6, "spd": 2, "crit": 3, "resource": "Charge", "desc": "Uses gadgets, turrets and mechanical weapons."},
    "duelist": {"hp": 15, "mp": 10, "atk": 9, "def": 4, "spd": 7, "crit": 8, "resource": "Tempo", "desc": "One-on-one specialist who grows stronger through perfect timing."},
    "lancer": {"hp": 25, "mp": 10, "atk": 9, "def": 6, "spd": 5, "crit": 3, "resource": "Resolve", "desc": "Mobile spear fighter with powerful gap-closing attacks."},
    "spellblade": {"hp": 20, "mp": 30, "atk": 9, "def": 4, "spd": 4, "crit": 5, "resource": "Arcana", "desc": "Hybrid fighter weaving weapon and magic together."},
})

SUBCLASSES = {
    "vanguard": ("warrior", "Durable frontline specialist", {"hp": 20, "def": 3}),
    "blade_master": ("warrior", "Weapon mastery specialist", {"atk": 4, "spd": 2}),
    "berserk_lord": ("berserker", "Uncontrolled damage dealer", {"atk": 6, "crit": 3}),
    "iron_guardian": ("knight", "Defensive protector", {"hp": 30, "def": 5}),
    "arcane_knight": ("knight", "Magic-infused tank", {"mp": 15, "atk": 3}),
    "fire_mage": ("mage", "Destructive elemental caster", {"atk": 6, "crit": 3}),
    "frost_mage": ("mage", "Control-focused caster", {"def": 2, "mp": 20}),
    "battle_mage": ("mage", "Close-range spell fighter", {"hp": 15, "atk": 4}),
    "shadow_assassin": ("assassin", "Stealth and critical specialist", {"spd": 4, "crit": 5}),
    "nightblade": ("rogue", "Dark dual-wielder", {"atk": 4, "crit": 4}),
    "sniper": ("ranger", "Long-range precision", {"atk": 5, "crit": 5}),
    "beast_master": ("ranger", "Pet-focused ranger", {"hp": 15, "atk": 3}),
    "holy_priest": ("cleric", "Healing and protection", {"mp": 25, "def": 3}),
    "battle_cleric": ("cleric", "Holy frontline fighter", {"hp": 20, "atk": 4}),
    "storm_druid": ("druid", "Lightning and storm magic", {"atk": 5, "spd": 2}),
    "wild_druid": ("druid", "Transformation specialist", {"hp": 25, "def": 2}),
    "dragon_monk": ("monk", "Explosive martial arts", {"atk": 5, "crit": 3}),
    "shadow_monk": ("monk", "Evasive martial artist", {"spd": 5, "crit": 3}),
    "minstrel": ("bard", "Party support", {"mp": 20, "def": 2}),
    "war_chanter": ("bard", "Offensive support", {"atk": 4, "crit": 3}),
    "bone_lord": ("necromancer", "Army-of-undead specialist", {"mp": 30, "def": 1}),
    "soul_reaper": ("necromancer", "Single-target dark magic", {"atk": 7, "crit": 4}),
    "demon_pact": ("warlock", "High-damage pact magic", {"atk": 6, "mp": 15}),
    "void_caller": ("warlock", "Reality-warping caster", {"crit": 5, "mp": 20}),
    "bombardier": ("alchemist", "Explosive alchemist", {"atk": 6, "crit": 3}),
    "transmuter": ("alchemist", "Resource-efficient crafter", {"def": 3, "mp": 20}),
    "artificer": ("engineer", "Construct specialist", {"atk": 4, "def": 4}),
    "machinist": ("engineer", "Ranged gadget fighter", {"atk": 5, "spd": 3}),
    "fencer": ("duelist", "Precision swordplay", {"spd": 3, "crit": 4}),
    "champion": ("duelist", "Arena specialist", {"hp": 20, "atk": 3}),
    "dragoon": ("lancer", "Aerial spear fighter", {"atk": 5, "spd": 3}),
    "templar": ("lancer", "Holy spear knight", {"def": 4, "hp": 15}),
    "spellbreaker": ("spellblade", "Anti-magic duelist", {"atk": 4, "def": 3}),
    "arcane_fencer": ("spellblade", "Magic sword specialist", {"mp": 20, "crit": 3}),
}

CLASS_EVOLUTIONS = {
    "warrior": [(20, "warlord"), (35, "hero")], "mage": [(20, "archmage"), (35, "grand_archmage")],
    "rogue": [(20, "shadow_lord"), (35, "phantom" )], "ranger": [(20, "forest_lord"), (35, "star_hunter")],
    "paladin": [(20, "holy_crusader"), (35, "divine_guardian")], "summoner": [(20, "spirit_master"), (35, "celestial_conjurer")],
    "berserker": [(20, "berserker_lord"), (35, "apocalypse" )], "knight": [(20, "royal_knight"), (35, "immortal_guardian")],
    "assassin": [(20, "deathstalker"), (35, "void_assassin")], "cleric": [(20, "high_priest"), (35, "saint")],
    "druid": [(20, "ancient_druid"), (35, "world_shaper")], "monk": [(20, "grandmaster"), (35, "dragon_sage")],
    "bard": [(20, "legendary_bard"), (35, "mythic_orator")], "necromancer": [(20, "lich"), (35, "death_sovereign")],
    "warlock": [(20, "demon_lord"), (35, "void_sovereign")], "alchemist": [(20, "master_alchemist"), (35, "philosophers_adept")],
    "engineer": [(20, "master_artificer"), (35, "magitech_overlord")], "duelist": [(20, "sword_saint"), (35, "arena_legend")],
    "lancer": [(20, "dragon_lord"), (35, "heaven_lancer")], "spellblade": [(20, "arcane_knight"), (35, "ether_blade")],
}

LIFE_PATHS = {
    "adventurer": "Questing explorer; gains extra rewards from discovery.",
    "noble": "A courtly life focused on influence and estates.",
    "royal": "A ruler or royal court member who can hold kingdom offices.",
    "merchant": "Trade-focused character with better market opportunities.",
    "outlaw": "Wanted wanderer who thrives outside the law.",
    "thug": "Street enforcer who earns renown through intimidation and jobs.",
    "hunter": "Monster tracker with improved hunting rewards.",
    "scholar": "Lore seeker with bonuses to quests and exploration.",
    "artisan": "Crafter and blacksmith with production bonuses.",
    "pirate": "Freebooter who seeks treasure on the high seas.",
}

AREAS = {
    "horizon_village": {"name": "Horizon Village", "level": 1, "type": "town", "desc": "The safe starting settlement."},
    "whispering_woods": {"name": "Whispering Woods", "level": 2, "type": "wild", "desc": "Ancient forest paths filled with beasts and herbs."},
    "ember_plains": {"name": "Ember Plains", "level": 5, "type": "wild", "desc": "Scorched fields where fire monsters roam."},
    "silver_coast": {"name": "Silver Coast", "level": 7, "type": "coast", "desc": "Port towns, pirates and sea monsters."},
    "moonfall_marsh": {"name": "Moonfall Marsh", "level": 10, "type": "wild", "desc": "A cursed wetland beneath an endless moon."},
    "frostpeak": {"name": "Frostpeak", "level": 13, "type": "mountain", "desc": "Frozen mountains guarding ancient ruins."},
    "sunken_ruins": {"name": "Sunken Ruins", "level": 16, "type": "ruins", "desc": "Lost civilization beneath the tides."},
    "skyreach": {"name": "Skyreach", "level": 20, "type": "sky", "desc": "Floating islands connected by ancient portals."},
    "demon_wastes": {"name": "Demon Wastes", "level": 25, "type": "hell", "desc": "A brutal land where corrupted monsters rule."},
    "crystal_desert": {"name": "Crystal Desert", "level": 30, "type": "desert", "desc": "A shimmering desert hiding buried kingdoms."},
    "astral_frontier": {"name": "Astral Frontier", "level": 40, "type": "astral", "desc": "Endgame territory beyond ordinary reality."},
    "world_tree": {"name": "World Tree", "level": 50, "type": "mythic", "desc": "The legendary final region of the known world."},
}

KINGDOM_ROLES = {"king": "Sovereign of the kingdom", "duke": "High noble and regional governor", "count": "Noble governing a county", "knight": "Sworn military noble", "citizen": "Recognized resident", "outlaw": "Outside the kingdom's law"}

PET_EGGS = {
    "common_egg": ("Common Egg", "Common", 150), "forest_egg": ("Forest Egg", "Uncommon", 300),
    "moon_egg": ("Moon Egg", "Rare", 600), "dragon_egg": ("Dragon Egg", "Epic", 1200),
    "phoenix_egg": ("Phoenix Egg", "Legendary", 3000), "celestial_egg": ("Celestial Egg", "Mythic", 7500),
    "void_egg": ("Void Egg", "Mythic", 9000), "royal_egg": ("Royal Egg", "Epic", 2000),
}


def _build_expanded_items():
    # Keep the original iconic items, then add a large discoverable catalog.
    generated = {}
    weapon_bases = [
        ("sword", "Sword", 9), ("greatsword", "Greatsword", 13), ("katana", "Katana", 11),
        ("rapier", "Rapier", 8), ("axe", "Axe", 12), ("greataxe", "Greataxe", 15),
        ("mace", "Mace", 10), ("hammer", "Warhammer", 13), ("spear", "Spear", 10),
        ("lance", "Lance", 12), ("dagger", "Dagger", 7), ("bow", "Bow", 9),
        ("crossbow", "Crossbow", 11), ("staff", "Staff", 8), ("wand", "Wand", 7),
        ("orb", "Arcane Orb", 8), ("scythe", "Scythe", 14), ("claws", "Claws", 9),
    ]
    metals = [("bronze", "Bronze", "common", 1.0), ("steel", "Steel", "uncommon", 1.2),
              ("silver", "Silver", "rare", 1.5), ("mithril", "Mithril", "epic", 2.0),
              ("dragon", "Dragon", "legendary", 3.0), ("celestial", "Celestial", "mythic", 4.5)]
    for mat_key, mat_name, rarity, mult in metals:
        for key, label, base in weapon_bases:
            k=f"{mat_key}_{key}"; generated[k]={"name":f"{mat_name} {label}","slot":"weapon","rarity":rarity,"atk":int(base*mult)+2,"crit":2 if key in {"rapier","dagger","katana","bow"} else 0,"price":int(90*base*mult)}
    armor_sets=[("chainmail","Chainmail",8),("plate","Plate Armor",13),("leather","Leather Armor",5),("scale","Scale Armor",10),
                ("mage","Mage Robe",4),("cleric","Cleric Vestments",5),("assassin","Assassin Garb",4),("ranger","Ranger Leathers",6),
                ("royal","Royal Armor",12),("dragon","Dragon Armor",16),("celestial","Celestial Armor",20)]
    for mat_key, mat_name, rarity, mult in metals:
        for key,label,base in armor_sets:
            k=f"{mat_key}_{key}"; generated[k]={"name":f"{mat_name} {label}","slot":"armor","rarity":rarity,"def":int(base*mult),"hp":int(base*mult*1.5),"price":int(120*base*mult)}
    for i,(name,rarity,price) in enumerate([
        ("Small Health Potion","common",45),("Health Potion","uncommon",90),("Greater Health Potion","rare",180),("Superior Health Potion","epic",350),
        ("Elixir of Vitality","legendary",700),("Full Restore Elixir","mythic",1500),
        ("Small Mana Potion","common",50),("Mana Potion","uncommon",100),("Greater Mana Potion","rare",200),("Superior Mana Potion","epic",400),
        ("Stamina Tonic","uncommon",80),("Antidote","common",35),("Burn Cure","common",35),("Freeze Cure","common",35),("Focus Elixir","rare",220),
        ("Strength Draught","rare",250),("Iron Skin Potion","rare",250),("Swiftstep Potion","rare",250),("Critical Elixir","epic",500),("Phoenix Elixir","legendary",1200)]):
        key=name.lower().replace(" ","_").replace("-",""); generated[key]={"name":name,"slot":"consumable","rarity":rarity,"heal":35+i*8 if "Health" in name or "Restore" in name or "Vitality" in name else 0,"mana":30+i*6 if "Mana" in name else 0,"price":price}
    foods=["Honey Bread","Berry Pie","Hearty Stew","Grilled Fish","Roasted Meat","Forest Mushroom Soup","Spicy Curry","Royal Feast","Traveler's Ration","Sweet Bun","Apple Tart","Moonberry Jam","Dragon Steak","Phoenix Fruit","Crystal Melon","Seafood Platter","Mountain Cheese","Golden Rice","Herbal Tea","Spiced Tea","Warm Milk","Campfire Skewer","Meat Pie","Fish Sandwich","Adventure Biscuit","Festival Cake","King's Banquet","Duke's Banquet","Elven Salad","Dwarven Ale Bread","Kitsune Dumplings"]
    for i,name in enumerate(foods):
        key="food_"+name.lower().replace(" ","_").replace("'","")
        generated[key]={"name":name,"slot":"food","rarity":"common" if i<10 else ("uncommon" if i<20 else "rare"),"heal":18+i*4,"stamina":8+(i%6)*3,"price":25+i*12}
    materials=["oak log","silver ore","mithril ore","dragon scale","phoenix feather","moon crystal","sun shard","shadow essence","beast fang","wolf claw","goblin ear","orc tusk","slime core","wraith dust","demon horn","angel feather","fae pollen","ancient bone","star fragment","void crystal","sea pearl","coral","amber","ruby","sapphire","emerald","topaz","obsidian","quartz","leather scrap","silk thread","magic fiber","enchanted wood","ashwood","frostwood","red herb","blue herb","golden herb","nightshade","sunflower seed"]
    for i,name in enumerate(materials):
        key="mat_"+name.replace(" ","_"); rarity="common" if i<15 else ("uncommon" if i<28 else ("rare" if i<37 else "epic")); generated[key]={"name":name.title(),"slot":"material","rarity":rarity,"price":20+i*18}
    for egg_key,(egg_name,rarity,price) in PET_EGGS.items():
        generated[egg_key]={"name":egg_name,"slot":"egg","rarity":rarity,"price":price,"pet_egg":True}
    # Additional trinkets / offhands create another equipment layer.
    shields=[("buckler","Buckler",6),("tower_shield","Tower Shield",12),("mirror_shield","Mirror Shield",10),("dragon_shield","Dragon Shield",16),("celestial_shield","Celestial Shield",20),("spellbook","Spellbook",3),("totem","Totem",4),("quiver","Quiver",2)]
    for mat_key,mat_name,rarity,mult in metals:
        for key,label,base in shields:
            k=f"{mat_key}_{key}"; generated[k]={"name":f"{mat_name} {label}","slot":"offhand","rarity":rarity,"def":int(base*mult),"hp":int(base*mult),"mp":int(base*mult*2) if key in {"spellbook","totem","quiver"} else 0,"price":int(100*base*mult)}
    # A few utility relics make exploration loot more interesting.
    relics=["Explorer's Compass","Adventurer's Lantern","Guild Crest","Royal Signet","Thief's Coin","Scholar's Lens","Hunter's Charm","Duke's Seal","King's Crown Fragment","Void Compass","Dragon Heart Shard","World Tree Seed"]
    for i,name in enumerate(relics):
        key="relic_"+name.lower().replace(" ","_").replace("'",""); generated[key]={"name":name,"slot":"relic","rarity":["uncommon","rare","epic","legendary","mythic"][min(4,i//3)],"atk":i//4,"def":i//5,"spd":i//3,"crit":i//2,"price":300+i*250}
    ITEMS.update(generated)
    ITEMS.setdefault("dragon_trophy", {"name":"Dragon Trophy","slot":"material","rarity":"legendary","price":1000})

_build_expanded_items()
for _egg_key, _egg_name, _rarity, _price in [
    ("fire_egg","Fire Egg","rare",700),("water_egg","Water Egg","rare",700),("frost_egg","Frost Egg","epic",1400),
    ("ruin_egg","Ruin Egg","epic",1600),("sky_egg","Sky Egg","legendary",3200),("demon_egg","Demon Egg","legendary",3800),
    ("desert_egg","Desert Egg","epic",1800),("astral_egg","Astral Egg","mythic",8500),("world_egg","World Egg","mythic",12000),
    ("beast_egg","Beast Egg","uncommon",400),("spirit_egg","Spirit Egg","rare",900),("shadow_egg","Shadow Egg","epic",1800),
]:
    ITEMS[_egg_key]={"name":_egg_name,"slot":"egg","rarity":_rarity,"price":_price,"pet_egg":True}
SHOP_ITEMS = [k for k,v in ITEMS.items() if v.get("price") and v.get("slot") in {"weapon","armor","offhand","consumable","food"}]

RECIPES = {
    "life_potion": {"iron_ore": 1, "herb": 2},
    "mana_potion": {"herb": 3, "arcane_shard": 1},
    "steel_blade": {"iron_ore": 5, "arcane_shard": 1},
    "guardian_shield": {"iron_ore": 7, "wolf_pelt": 2},
}

ENEMIES = [
    {"name": "Slime", "level": 1, "hp": 45, "atk": 7, "def": 2, "xp": 35, "gold": 25, "drops": ["herb"]},
    {"name": "Forest Wolf", "level": 2, "hp": 65, "atk": 10, "def": 3, "xp": 55, "gold": 38, "drops": ["wolf_pelt", "herb"]},
    {"name": "Goblin Raider", "level": 4, "hp": 95, "atk": 14, "def": 5, "xp": 90, "gold": 65, "drops": ["iron_ore"]},
    {"name": "Arcane Wraith", "level": 7, "hp": 145, "atk": 21, "def": 8, "xp": 150, "gold": 110, "drops": ["arcane_shard"]},
    {"name": "Ancient Dragonling", "level": 12, "hp": 260, "atk": 32, "def": 14, "xp": 300, "gold": 240, "drops": ["arcane_shard", "iron_ore"]},
]

DUNGEONS = [
    ("Goblin Caves", 1, 3, 140, 90, "A beginner dungeon with three floors."),
    ("Moonlit Ruins", 5, 4, 360, 240, "Ancient ruins filled with arcane enemies."),
    ("Dragonspire", 10, 5, 800, 550, "A dangerous tower ending in a dragon boss."),
]

ACHIEVEMENTS = {
    "first_blood": ("First Blood", "Defeat your first enemy.", 100),
    "level_10": ("Rising Hero", "Reach level 10.", 500),
    "collector": ("Collector", "Own 10 different item types.", 300),
    "guild_founder": ("Guild Founder", "Create a guild.", 250),
    "dungeon_clear": ("Dungeon Delver", "Clear your first dungeon.", 400),
    "legend": ("Legend", "Reach level 25.", 1500),
}


@dataclass
class RPGService:
    path: str
    active_combats: dict[tuple[int, int], dict[str, Any]] = field(default_factory=dict, init=False, repr=False)

    async def setup(self):
        async with aiosqlite.connect(self.path) as db:
            await db.executescript("""
            CREATE TABLE IF NOT EXISTS rpg_players (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                name TEXT NOT NULL DEFAULT '', race TEXT NOT NULL DEFAULT 'human', class_name TEXT NOT NULL DEFAULT 'warrior',
                level INTEGER NOT NULL DEFAULT 1, xp INTEGER NOT NULL DEFAULT 0, gold INTEGER NOT NULL DEFAULT 250,
                hp INTEGER NOT NULL DEFAULT 100, max_hp INTEGER NOT NULL DEFAULT 100,
                mp INTEGER NOT NULL DEFAULT 40, max_mp INTEGER NOT NULL DEFAULT 40,
                atk INTEGER NOT NULL DEFAULT 10, defense INTEGER NOT NULL DEFAULT 5, speed INTEGER NOT NULL DEFAULT 5,
                crit INTEGER NOT NULL DEFAULT 5, skill_points INTEGER NOT NULL DEFAULT 0,
                stamina INTEGER NOT NULL DEFAULT 100, location TEXT NOT NULL DEFAULT 'Horizon Village',
                guild_name TEXT NOT NULL DEFAULT '', title TEXT NOT NULL DEFAULT 'Adventurer', prestige INTEGER NOT NULL DEFAULT 0,
                subclass TEXT NOT NULL DEFAULT '', subrace TEXT NOT NULL DEFAULT '', evolution TEXT NOT NULL DEFAULT '',
                life_path TEXT NOT NULL DEFAULT 'adventurer', renown INTEGER NOT NULL DEFAULT 0, fame INTEGER NOT NULL DEFAULT 0,
                stat_points INTEGER NOT NULL DEFAULT 0, talent_points INTEGER NOT NULL DEFAULT 0, kingdom_name TEXT NOT NULL DEFAULT '',
                kingdom_role TEXT NOT NULL DEFAULT '', area_key TEXT NOT NULL DEFAULT 'horizon_village',
                last_daily REAL NOT NULL DEFAULT 0, last_adventure REAL NOT NULL DEFAULT 0,
                last_hunt REAL NOT NULL DEFAULT 0, last_weekly REAL NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS rpg_inventory (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, item_key TEXT NOT NULL, quantity INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id, item_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_equipment (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, slot TEXT NOT NULL, item_key TEXT NOT NULL,
                PRIMARY KEY (guild_id, user_id, slot)
            );
            CREATE TABLE IF NOT EXISTS rpg_quests (
                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, kind TEXT NOT NULL, title TEXT NOT NULL,
                description TEXT NOT NULL, level_req INTEGER NOT NULL DEFAULT 1, target INTEGER NOT NULL DEFAULT 1,
                progress_type TEXT NOT NULL DEFAULT 'hunt', reward_xp INTEGER NOT NULL DEFAULT 0,
                reward_gold INTEGER NOT NULL DEFAULT 0, reward_item TEXT DEFAULT '', reward_qty INTEGER NOT NULL DEFAULT 0,
                expires_at REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS rpg_player_quests (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, quest_id INTEGER NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'active',
                PRIMARY KEY (guild_id, user_id, quest_id)
            );
            CREATE TABLE IF NOT EXISTS rpg_guilds (
                guild_id INTEGER NOT NULL, name TEXT NOT NULL, leader_id INTEGER NOT NULL,
                level INTEGER NOT NULL DEFAULT 1, xp INTEGER NOT NULL DEFAULT 0, bank INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL, PRIMARY KEY (guild_id, name)
            );
            CREATE TABLE IF NOT EXISTS rpg_guild_members (
                guild_id INTEGER NOT NULL, guild_name TEXT NOT NULL, user_id INTEGER NOT NULL,
                rank TEXT NOT NULL DEFAULT 'member', joined_at REAL NOT NULL,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS rpg_parties (
                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, name TEXT NOT NULL,
                leader_id INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'open', created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rpg_party_members (
                party_id INTEGER NOT NULL, user_id INTEGER NOT NULL, role TEXT NOT NULL DEFAULT 'member',
                PRIMARY KEY (party_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS rpg_pets (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, name TEXT NOT NULL,
                species TEXT NOT NULL, level INTEGER NOT NULL DEFAULT 1, xp INTEGER NOT NULL DEFAULT 0,
                bonus_atk INTEGER NOT NULL DEFAULT 0, bonus_def INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS rpg_achievements (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, achievement_key TEXT NOT NULL,
                unlocked_at REAL NOT NULL, PRIMARY KEY (guild_id, user_id, achievement_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_market (
                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, seller_id INTEGER NOT NULL,
                item_key TEXT NOT NULL, quantity INTEGER NOT NULL, price_each INTEGER NOT NULL, created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rpg_kingdoms (
                guild_id INTEGER NOT NULL, name TEXT NOT NULL, ruler_id INTEGER NOT NULL, level INTEGER NOT NULL DEFAULT 1,
                treasury INTEGER NOT NULL DEFAULT 0, renown INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL,
                PRIMARY KEY (guild_id, name)
            );
            CREATE TABLE IF NOT EXISTS rpg_kingdom_members (
                guild_id INTEGER NOT NULL, kingdom_name TEXT NOT NULL, user_id INTEGER NOT NULL,
                role TEXT NOT NULL DEFAULT 'citizen', joined_at REAL NOT NULL,
                PRIMARY KEY (guild_id, kingdom_name, user_id)
            );
            CREATE TABLE IF NOT EXISTS rpg_bounties (
                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, poster_id INTEGER NOT NULL,
                target_name TEXT NOT NULL, reward INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'open', created_at REAL NOT NULL
            );
            """)
            # Lightweight migrations for existing Horizon RPG databases.
            migrations = {
                "subclass": "TEXT NOT NULL DEFAULT ''", "subrace": "TEXT NOT NULL DEFAULT ''",
                "evolution": "TEXT NOT NULL DEFAULT ''", "life_path": "TEXT NOT NULL DEFAULT 'adventurer'",
                "renown": "INTEGER NOT NULL DEFAULT 0", "fame": "INTEGER NOT NULL DEFAULT 0",
                "stat_points": "INTEGER NOT NULL DEFAULT 0", "talent_points": "INTEGER NOT NULL DEFAULT 0",
                "kingdom_name": "TEXT NOT NULL DEFAULT ''", "kingdom_role": "TEXT NOT NULL DEFAULT ''",
                "area_key": "TEXT NOT NULL DEFAULT 'horizon_village'",
            }
            cur = await db.execute("PRAGMA table_info(rpg_players)")
            existing = {row[1] for row in await cur.fetchall()}
            for column, definition in migrations.items():
                if column not in existing:
                    await db.execute(f"ALTER TABLE rpg_players ADD COLUMN {column} {definition}")
            await db.commit()

    def _level_xp(self, level: int) -> int:
        return 100 * level * level

    def _class_stats(self, race: str, class_name: str):
        race = RACES.get(race, RACES["human"])
        cls = CLASSES.get(class_name, CLASSES["warrior"])
        return {
            "max_hp": 100 + race["hp"] + cls["hp"],
            "max_mp": 40 + cls["mp"],
            "atk": 10 + race["atk"] + cls["atk"],
            "defense": 5 + race["def"] + cls["def"],
            "speed": 5 + race["spd"] + cls["spd"],
            "crit": 5 + race["crit"] + cls["crit"],
        }

    async def player(self, guild_id: int, user_id: int):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM rpg_players WHERE guild_id=? AND user_id=?", (guild_id, user_id))
            row = await cur.fetchone()
            return dict(row) if row else None

    async def create_player(self, guild_id: int, user_id: int, name: str, race: str, class_name: str):
        race = race.lower(); class_name = class_name.lower()
        if race not in RACES or class_name not in CLASSES:
            raise ValueError("Invalid race or class.")
        if await self.player(guild_id, user_id):
            return False, "You already have a hero. Use `!rpg profile` to inspect it."
        s = self._class_stats(race, class_name)
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO rpg_players(guild_id,user_id,name,race,class_name,max_hp,hp,max_mp,mp,atk,defense,speed,crit) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                             (guild_id,user_id,name[:32],race,class_name,s["max_hp"],s["max_hp"],s["max_mp"],s["max_mp"],s["atk"],s["defense"],s["speed"],s["crit"]))
            for item, qty in (("life_potion",3),("mana_potion",2),("iron_sword",1),("iron_armor",1)):
                await db.execute("INSERT INTO rpg_inventory VALUES(?,?,?,?)", (guild_id,user_id,item,qty))
            await db.commit()
        return True, f"Hero **{name}** created as a **{race.title()} {class_name.title()}**."

    async def ensure_player(self, guild_id: int, user_id: int):
        p = await self.player(guild_id, user_id)
        if not p:
            return False, "You don't have an RPG character yet. Start with `!rpg start <name> <race> <class>`."
        return True, p

    async def inventory(self, guild_id, user_id):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT item_key,quantity FROM rpg_inventory WHERE guild_id=? AND user_id=? AND quantity>0 ORDER BY item_key", (guild_id,user_id))
            return await cur.fetchall()

    async def add_item(self, guild_id, user_id, item_key, quantity=1):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO rpg_inventory VALUES(?,?,?,?) ON CONFLICT(guild_id,user_id,item_key) DO UPDATE SET quantity=quantity+excluded.quantity", (guild_id,user_id,item_key,quantity))
            await db.commit()

    async def remove_item(self, guild_id, user_id, item_key, quantity=1):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT quantity FROM rpg_inventory WHERE guild_id=? AND user_id=? AND item_key=?", (guild_id,user_id,item_key))
            row = await cur.fetchone()
            if not row or row[0] < quantity: return False
            await db.execute("UPDATE rpg_inventory SET quantity=quantity-? WHERE guild_id=? AND user_id=? AND item_key=?", (quantity,guild_id,user_id,item_key))
            await db.commit(); return True

    async def add_rewards(self, guild_id, user_id, xp=0, gold=0):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET xp=xp+?, gold=gold+? WHERE guild_id=? AND user_id=?", (xp,gold,guild_id,user_id))
            cur = await db.execute("SELECT level,xp FROM rpg_players WHERE guild_id=? AND user_id=?", (guild_id,user_id)); p = await cur.fetchone()
            old_level = p[0]
            new_level = old_level
            while p[1] >= self._level_xp(new_level) and new_level < 100: new_level += 1
            levels = new_level - old_level
            if levels:
                # Every level gives both an automatic growth package and points
                # the player can deliberately invest.  This makes progression
                # visible instead of merely changing the number on the sheet.
                await db.execute(
                    "UPDATE rpg_players SET level=?, max_hp=max_hp+?, hp=max_hp+?, max_mp=max_mp+?, mp=max_mp+?, atk=atk+?, defense=defense+?, speed=speed+?, skill_points=skill_points+?, stat_points=stat_points+?, talent_points=talent_points+? WHERE guild_id=? AND user_id=?",
                    (new_level, levels*12, levels*12, levels*5, levels*5, levels*2, levels, levels, levels*2, levels*3, levels, guild_id, user_id)
                )
            await db.commit()
            return old_level, new_level

    async def _cooldown(self, p, field, seconds):
        remaining = max(0, seconds - (time.time() - float(p[field])))
        return remaining

    async def adventure(self, guild_id, user_id):
        p = await self.player(guild_id,user_id)
        if not p: return {"error":"Start a character first with `!rpg start`."}
        remaining = await self._cooldown(p,"last_adventure",45)
        if remaining > 0: return {"error":f"Your next adventure is ready in **{int(remaining)+1}s**."}
        enemy = random.choice([e for e in ENEMIES if e["level"] <= p["level"]+3])
        player_hp = p["hp"]; enemy_hp = enemy["hp"] + max(0,p["level"]-enemy["level"])*8
        log=[]; turn=0
        atk = p["atk"]; defense=p["defense"]; speed=p["speed"]
        while player_hp>0 and enemy_hp>0 and turn<30:
            turn += 1
            if random.random() < min(.18, speed/200):
                log.append("You dodged the enemy's attack.")
            else:
                dmg=max(1,enemy["atk"] + random.randint(-2,3) - defense//3); player_hp-=dmg; log.append(f"{enemy['name']} hit you for **{dmg}**.")
            if player_hp<=0: break
            crit = random.random() < min(.60,p["crit"]/100)
            dmg=max(1,atk + random.randint(-2,4) - enemy["def"]//2)
            if crit: dmg*=2
            enemy_hp-=dmg; log.append(f"You dealt **{dmg}**{' critical damage' if crit else ''}.")
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET last_adventure=?,hp=? WHERE guild_id=? AND user_id=?", (time.time(),max(1,player_hp),guild_id,user_id)); await db.commit()
        if player_hp<=0:
            await self.add_item(guild_id,user_id,"life_potion",1)
            return {"win":False,"enemy":enemy,"log":log[-8:],"hp":1}
        xp=enemy["xp"]+random.randint(0,20); gold=enemy["gold"]+random.randint(0,30)
        await self.add_rewards(guild_id,user_id,xp,gold)
        drop=random.choice(enemy["drops"])
        await self.add_item(guild_id,user_id,drop,1)
        await self.progress_quests(guild_id,user_id,"hunt",1)
        await self.check_achievements(guild_id,user_id)
        return {"win":True,"enemy":enemy,"log":log[-8:],"xp":xp,"gold":gold,"drop":drop,"hp":max(1,player_hp)}

    async def daily(self,guild_id,user_id):
        p=await self.player(guild_id,user_id)
        if not p: return None,"Start your hero first with `!rpg start`."
        remaining=await self._cooldown(p,"last_daily",86400)
        if remaining>0: return None,f"Daily reward ready in **{int(remaining//3600)}h {int((remaining%3600)//60)}m**."
        streak_bonus=random.randint(0,100); xp=150; gold=300+streak_bonus
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET last_daily=?,gold=gold+? WHERE guild_id=? AND user_id=?",(time.time(),gold,guild_id,user_id)); await db.commit()
        old,new=await self.add_rewards(guild_id,user_id,xp,0)
        await self.add_item(guild_id,user_id,"life_potion",1)
        return (xp,gold,new),None

    async def use_item(self,guild_id,user_id,item_key,quantity=1):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        item_key=item_key.lower(); item=ITEMS.get(item_key)
        if not item or item.get("slot") not in {"consumable","food"}:return False,"That item cannot be used this way."
        quantity=max(1,min(int(quantity),10))
        if not await self.remove_item(guild_id,user_id,item_key,quantity):return False,"You don't own enough of that item."
        heal=item.get("heal",0)*quantity; mana=item.get("mana",0)*quantity; stamina=item.get("stamina",0)*quantity
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET hp=min(max_hp,hp+?),mp=min(max_mp,mp+?),stamina=min(100,stamina+?) WHERE guild_id=? AND user_id=?",(heal,mana,stamina,guild_id,user_id)); await db.commit()
        return True,f"Used **{item['name']} ×{quantity}** — +{heal} HP, +{mana} MP, +{stamina} stamina."

    async def equip(self,guild_id,user_id,item_key):
        p=await self.player(guild_id,user_id)
        if not p: return False,"Start a hero first."
        item=ITEMS.get(item_key.lower())
        if not item or item["slot"] not in {"weapon","armor","offhand"}: return False,"That item cannot be equipped."
        inv=dict(await self.inventory(guild_id,user_id))
        if inv.get(item_key.lower(),0)<1: return False,"You don't own that item."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO rpg_equipment(guild_id,user_id,slot,item_key) VALUES(?,?,?,?) ON CONFLICT(guild_id,user_id,slot) DO UPDATE SET item_key=excluded.item_key",(guild_id,user_id,item["slot"],item_key.lower()))
            await db.commit()
        return True,f"Equipped **{item['name']}**."

    def _progression_bonus(self, p):
        bonus={"atk":0,"defense":0,"hp":0,"mp":0,"speed":0,"crit":0}
        subrace=p.get("subrace") or ""
        if subrace in SUBRACES:
            _, values=SUBRACES[subrace]
            bonus["hp"]+=values.get("hp",0); bonus["atk"]+=values.get("atk",0); bonus["defense"]+=values.get("def",0)
            bonus["speed"]+=values.get("spd",0); bonus["crit"]+=values.get("crit",0)
        subclass=p.get("subclass") or ""
        if subclass in SUBCLASSES:
            _,_,values=SUBCLASSES[subclass]
            bonus["hp"]+=values.get("hp",0); bonus["atk"]+=values.get("atk",0); bonus["defense"]+=values.get("def",0)
            bonus["speed"]+=values.get("spd",0); bonus["crit"]+=values.get("crit",0); bonus["mp"]+=values.get("mp",0)
        if p.get("evolution"):
            tier=2 if p["level"]>=35 else 1
            bonus["atk"]+=4*tier; bonus["defense"]+=2*tier; bonus["hp"]+=15*tier; bonus["mp"]+=10*tier; bonus["crit"]+=2*tier
        return bonus

    async def stats(self,guild_id,user_id):
        p=await self.player(guild_id,user_id)
        if not p:return None
        gear={}
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT slot,item_key FROM rpg_equipment WHERE guild_id=? AND user_id=?",(guild_id,user_id)); gear=dict(await cur.fetchall())
        bonus=self._progression_bonus(p)
        for key in gear.values():
            item=ITEMS.get(key,{})
            bonus["atk"]+=item.get("atk",0); bonus["defense"]+=item.get("def",0); bonus["hp"]+=item.get("hp",0); bonus["mp"]+=item.get("mp",0); bonus["speed"]+=item.get("spd",0); bonus["crit"]+=item.get("crit",0)
        return p,gear,bonus

    async def change_identity(self,guild_id,user_id,kind,value):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        kind=kind.lower(); value=value.lower().strip()
        costs={"race":1500,"class":1200,"subrace":2200,"subclass":3000,"path":1800,"evolution":5000}
        if kind not in costs:return False,"Change one of: race, subrace, class, subclass, path, evolution."
        if kind=="race":
            if value not in RACES:return False,f"Unknown race. Use `!rpg races`."
            if value==p["race"]:return False,"You already are that race."
            updates={"race":value,"subrace":""}
        elif kind=="class":
            if value not in CLASSES:return False,"Unknown class. Use `!rpg classes`."
            if value==p["class_name"]:return False,"You already have that class."
            updates={"class_name":value,"subclass":"","evolution":""}
        elif kind=="subrace":
            if value not in SUBRACES:return False,"Unknown subrace. Use `!rpg subraces`."
            parent,_=SUBRACES[value]
            if parent!=p["race"]:return False,f"That subrace belongs to **{parent.title()}**, not {p['race'].title()}."
            updates={"subrace":value}
        elif kind=="subclass":
            if value not in SUBCLASSES:return False,"Unknown subclass. Use `!rpg subclasses`."
            parent,_,_=SUBCLASSES[value]
            if parent!=p["class_name"]:return False,f"That subclass requires **{parent.title()}**."
            if p["level"]<10:return False,"Subclasses unlock at level **10**."
            updates={"subclass":value,"evolution":""}
        elif kind=="path":
            if value not in LIFE_PATHS:return False,"Unknown life path. Use `!rpg paths`."
            updates={"life_path":value}
        else:
            evolutions=[name for lvl,name in CLASS_EVOLUTIONS.get(p["class_name"],[]) if p["level"]>=lvl]
            if value not in evolutions:return False,"That evolution is not unlocked for your class and level."
            updates={"evolution":value}
        cost=costs[kind]
        if p["gold"]<cost:return False,f"Changing your {kind} costs **{cost} gold**. You have {p['gold']}."
        new_race=updates.get("race",p["race"]); new_class=updates.get("class_name",p["class_name"])
        old_base=self._class_stats(p["race"],p["class_name"]); new_base=self._class_stats(new_race,new_class)
        growth=p["level"]-1
        old_atk=old_base["atk"]+growth*2; old_def=old_base["defense"]+growth; old_spd=old_base["speed"]+growth; old_hp=old_base["max_hp"]+growth*12; old_mp=old_base["max_mp"]+growth*5
        keep_atk=max(0,p["atk"]-old_atk); keep_def=max(0,p["defense"]-old_def); keep_spd=max(0,p["speed"]-old_spd); keep_hp=max(0,p["max_hp"]-old_hp); keep_mp=max(0,p["max_mp"]-old_mp)
        new_max_hp=new_base["max_hp"]+growth*12+keep_hp; new_max_mp=new_base["max_mp"]+growth*5+keep_mp
        new_atk=new_base["atk"]+growth*2+keep_atk; new_def=new_base["defense"]+growth+keep_def; new_spd=new_base["speed"]+growth+keep_spd
        fields=", ".join(f"{k}=?" for k in updates)
        vals=list(updates.values())+[p["gold"]-cost,new_max_hp,new_max_mp,new_atk,new_def,new_spd,max(1,min(p["hp"],new_max_hp)),max(0,min(p["mp"],new_max_mp)),guild_id,user_id]
        async with aiosqlite.connect(self.path) as db:
            await db.execute(f"UPDATE rpg_players SET {fields}, gold=?, max_hp=?, max_mp=?, atk=?, defense=?, speed=?, hp=?, mp=? WHERE guild_id=? AND user_id=?",vals)
            await db.commit()
        return True,f"Your **{kind}** changed to **{value.replace('_',' ').title()}** for **{cost} gold**."

    async def spend_stat(self,guild_id,user_id,stat,amount=1):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        amount=max(1,min(int(amount),25)); stat=stat.lower()
        mapping={"attack":"atk","atk":"atk","defense":"defense","def":"defense","speed":"speed","spd":"speed","crit":"crit","hp":"max_hp","mana":"max_mp","mp":"max_mp"}
        column=mapping.get(stat)
        if not column:return False,"Choose attack, defense, speed, crit, hp or mana."
        if p["stat_points"]<amount:return False,f"You only have **{p['stat_points']} stat points**."
        gain=amount*5 if column in {"max_hp","max_mp"} else amount
        async with aiosqlite.connect(self.path) as db:
            await db.execute(f"UPDATE rpg_players SET {column}={column}+?, stat_points=stat_points-? WHERE guild_id=? AND user_id=?",(gain,amount,guild_id,user_id)); await db.commit()
        return True,f"Spent **{amount}** stat point(s) on **{stat}** (+{gain})."

    async def create_guild(self,guild_id,user_id,name):
        if await self.player(guild_id,user_id) is None:return False,"Create an RPG character first."
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT 1 FROM rpg_guilds WHERE guild_id=? AND lower(name)=lower(?)",(guild_id,name));
            if await cur.fetchone(): return False,"A guild with that name already exists."
            await db.execute("INSERT INTO rpg_guilds(guild_id,name,leader_id,created_at) VALUES(?,?,?,?)",(guild_id,name[:32],user_id,time.time()))
            await db.execute("INSERT INTO rpg_guild_members VALUES(?,?,?,?,?)",(guild_id,name[:32],user_id,"leader",time.time()))
            await db.execute("UPDATE rpg_players SET guild_name=? WHERE guild_id=? AND user_id=?",(name[:32],guild_id,user_id)); await db.commit()
        await self.check_achievements(guild_id,user_id)
        return True,f"Guild **{name}** created. You are its leader."

    async def guilds(self,guild_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT name,leader_id,level,xp,bank FROM rpg_guilds WHERE guild_id=? ORDER BY level DESC,name",(guild_id,)); return await cur.fetchall()

    async def join_guild(self,guild_id,user_id,name):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT name FROM rpg_guilds WHERE guild_id=? AND lower(name)=lower(?)",(guild_id,name)); g=await cur.fetchone()
            if not g:return False,"Guild not found."
            await db.execute("DELETE FROM rpg_guild_members WHERE guild_id=? AND user_id=?",(guild_id,user_id))
            await db.execute("INSERT INTO rpg_guild_members VALUES(?,?,?,?,?)",(guild_id,g[0],user_id,"member",time.time()))
            await db.execute("UPDATE rpg_players SET guild_name=? WHERE guild_id=? AND user_id=?",(g[0],guild_id,user_id)); await db.commit()
        return True,f"Joined **{g[0]}**."

    async def guild_info(self,guild_id,name=None,user_id=None):
        async with aiosqlite.connect(self.path) as db:
            if name:
                cur=await db.execute("SELECT * FROM rpg_guilds WHERE guild_id=? AND lower(name)=lower(?)",(guild_id,name))
            else:
                if user_id is not None:
                    cur=await db.execute("SELECT g.* FROM rpg_guilds g JOIN rpg_guild_members m ON g.guild_id=m.guild_id AND g.name=m.guild_name WHERE m.guild_id=? AND m.user_id=? LIMIT 1",(guild_id,user_id))
                else:
                    cur=await db.execute("SELECT * FROM rpg_guilds WHERE guild_id=? ORDER BY level DESC LIMIT 1",(guild_id,))
            row=await cur.fetchone();
            if not row:return None
            cur=await db.execute("SELECT user_id,rank FROM rpg_guild_members WHERE guild_id=? AND guild_name=?",(guild_id,row[1])); members=await cur.fetchall()
            return row,members

    async def leave_guild(self,guild_id,user_id):
        info=await self.guild_info(guild_id,user_id=user_id)
        if not info:return False,"You are not in a guild."
        g,members=info
        if g[2]==user_id:
            return False,"The guild leader cannot leave. Transfer leadership or create a new guild."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM rpg_guild_members WHERE guild_id=? AND user_id=?",(guild_id,user_id))
            await db.execute("UPDATE rpg_players SET guild_name='' WHERE guild_id=? AND user_id=?",(guild_id,user_id))
            await db.commit()
        return True,f"You left **{g[1]}**."

    async def create_party(self,guild_id,user_id,name):
        if not await self.player(guild_id,user_id):return False,"Create a hero first."
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT id FROM rpg_parties WHERE guild_id=? AND leader_id=? AND status='open'",(guild_id,user_id));
            if await cur.fetchone():return False,"You already lead an open party."
            cur=await db.execute("INSERT INTO rpg_parties(guild_id,name,leader_id,created_at) VALUES(?,?,?,?)",(guild_id,name[:32],user_id,time.time())); pid=cur.lastrowid
            await db.execute("INSERT INTO rpg_party_members VALUES(?,?,?)",(pid,user_id,"leader")); await db.commit()
        return True,f"Party **{name}** created. Party ID: `{pid}`. Others can `!rpg party join {pid}`."

    async def party_info(self,guild_id,pid=None,user_id=None):
        async with aiosqlite.connect(self.path) as db:
            if pid is not None: cur=await db.execute("SELECT * FROM rpg_parties WHERE guild_id=? AND id=?",(guild_id,pid))
            else: cur=await db.execute("SELECT p.* FROM rpg_parties p JOIN rpg_party_members m ON p.id=m.party_id WHERE p.guild_id=? AND m.user_id=? AND p.status='open' LIMIT 1",(guild_id,user_id))
            party=await cur.fetchone()
            if not party:return None
            cur=await db.execute("SELECT user_id,role FROM rpg_party_members WHERE party_id=?",(party[0],)); members=await cur.fetchall(); return party,members

    async def join_party(self,guild_id,user_id,pid):
        info=await self.party_info(guild_id,pid=pid)
        if not info:return False,"Party not found."
        party,members=info
        if party[4]!="open":return False,"That party is already running."
        if len(members)>=4:return False,"Party is full (4 players)."
        if any(m[0]==user_id for m in members):return False,"You are already in this party."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO rpg_party_members VALUES(?,?,?)",(pid,user_id,"member")); await db.commit()
        return True,f"Joined **{party[1]}**."

    async def leave_party(self,guild_id,user_id):
        info=await self.party_info(guild_id,user_id=user_id)
        if not info:return False,"You are not in an open party."
        party,members=info
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM rpg_party_members WHERE party_id=? AND user_id=?",(party[0],user_id))
            if party[3]==user_id:
                await db.execute("UPDATE rpg_parties SET status='closed' WHERE id=?",(party[0],))
            await db.commit()
        return True,"You left the party."

    async def quest_seed(self,guild_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT COUNT(*) FROM rpg_quests WHERE guild_id=?",(guild_id,)); count=(await cur.fetchone())[0]
            if count>=8:return
            templates=[
                ("daily","Wolf Hunt","Defeat 3 enemies.",1,3,"hunt",180,260,"wolf_pelt",2),
                ("daily","Gatherer","Collect 3 materials from adventures.",1,3,"gather",160,220,"herb",2),
                ("daily","Dungeon Call","Clear a dungeon floor.",1,1,"dungeon",250,350,"life_potion",2),
                ("weekly","Champion's Path","Win 8 battles or adventures.",5,8,"hunt",800,1200,"arcane_shard",2),
            ]
            for kind,title,desc,lvl,target,ptype,xp,gold,item,qty in templates:
                await db.execute("INSERT INTO rpg_quests(guild_id,kind,title,description,level_req,target,progress_type,reward_xp,reward_gold,reward_item,reward_qty,expires_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(guild_id,kind,title,desc,lvl,target,ptype,xp,gold,item,qty,time.time()+86400*(7 if kind=='weekly' else 1)))
            await db.commit()

    async def quests(self,guild_id,user_id):
        await self.quest_seed(guild_id)
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT q.id,q.title,q.description,q.level_req,q.target,q.progress_type,q.reward_xp,q.reward_gold,q.reward_item,q.reward_qty,COALESCE(p.progress,0),COALESCE(p.status,'available') FROM rpg_quests q LEFT JOIN rpg_player_quests p ON q.id=p.quest_id AND p.guild_id=? AND p.user_id=? WHERE q.guild_id=? AND q.expires_at>? ORDER BY q.kind,q.id",(guild_id,user_id,guild_id,time.time())); return await cur.fetchall()

    async def accept_quest(self,guild_id,user_id,qid):
        p=await self.player(guild_id,user_id); 
        if not p:return False,"Create a hero first."
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT id,level_req FROM rpg_quests WHERE guild_id=? AND id=?",(guild_id,qid)); q=await cur.fetchone()
            if not q:return False,"Quest not found."
            if p["level"]<q[1]:return False,f"You need level {q[1]}."
            await db.execute("INSERT OR REPLACE INTO rpg_player_quests(guild_id,user_id,quest_id,progress,status) VALUES(?,?,?,?,?)",(guild_id,user_id,qid,0,"active")); await db.commit()
        return True,"Quest accepted."

    async def progress_quests(self,guild_id,user_id,ptype,amount=1):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_player_quests SET progress=progress+? WHERE guild_id=? AND user_id=? AND status='active' AND quest_id IN (SELECT id FROM rpg_quests WHERE progress_type=? )",(amount,guild_id,user_id,ptype)); await db.commit()

    async def claim_quest(self,guild_id,user_id,qid):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT q.target,q.reward_xp,q.reward_gold,q.reward_item,q.reward_qty,p.progress,p.status FROM rpg_quests q JOIN rpg_player_quests p ON q.id=p.quest_id WHERE q.guild_id=? AND q.id=? AND p.user_id=?",(guild_id,qid,user_id)); row=await cur.fetchone()
            if not row:return False,"Quest not active."
            target,xp,gold,item,qty,progress,status=row
            if status!="active":return False,"Quest is not active."
            if progress<target:return False,f"Progress: {progress}/{target}."
            await db.execute("UPDATE rpg_player_quests SET status='claimed' WHERE guild_id=? AND user_id=? AND quest_id=?",(guild_id,user_id,qid)); await db.execute("UPDATE rpg_players SET gold=gold+? WHERE guild_id=? AND user_id=?",(gold,guild_id,user_id)); await db.commit()
        await self.add_rewards(guild_id,user_id,xp,0)
        if item: await self.add_item(guild_id,user_id,item,qty)
        return True,f"Quest complete: **+{xp} XP**, **+{gold} gold**" + (f", **{ITEMS[item]['name']} ×{qty}**" if item else "")

    async def check_achievements(self,guild_id,user_id):
        p=await self.player(guild_id,user_id)
        if not p:return []
        inv=await self.inventory(guild_id,user_id)
        unlocked=[]
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT achievement_key FROM rpg_achievements WHERE guild_id=? AND user_id=?",(guild_id,user_id)); existing={r[0] for r in await cur.fetchall()}
            checks={"first_blood":p["xp"]>0,"level_10":p["level"]>=10,"collector":len(inv)>=10,"legend":p["level"]>=25}
            cur=await db.execute("SELECT 1 FROM rpg_guild_members WHERE guild_id=? AND user_id=? AND rank='leader'",(guild_id,user_id)); checks["guild_founder"]=bool(await cur.fetchone())
            # Dungeon achievement is awarded by the dungeon command through this helper flag.
            cur=await db.execute("SELECT 1 FROM rpg_inventory WHERE guild_id=? AND user_id=? AND item_key='dragon_trophy'",(guild_id,user_id)); checks["dungeon_clear"]=bool(await cur.fetchone())
            for key,ok in checks.items():
                if ok and key not in existing:
                    await db.execute("INSERT INTO rpg_achievements VALUES(?,?,?,?)",(guild_id,user_id,key,time.time())); unlocked.append(ACHIEVEMENTS[key])
            await db.commit()
        return unlocked

    async def achievement_list(self,guild_id,user_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT achievement_key,unlocked_at FROM rpg_achievements WHERE guild_id=? AND user_id=? ORDER BY unlocked_at",(guild_id,user_id)); return await cur.fetchall()

    async def shop(self):
        # A rotating storefront keeps the command readable even though the
        # world now contains hundreds of discoverable items.
        featured=[k for k in SHOP_ITEMS if ITEMS[k].get("rarity") in {"common","uncommon","rare"}]
        random.shuffle(featured)
        keys=featured[:24]
        return [(k,ITEMS[k]) for k in keys]

    async def buy(self,guild_id,user_id,item_key,quantity=1):
        p=await self.player(guild_id,user_id); item=ITEMS.get(item_key.lower())
        if not p:return False,"Create a hero first."
        if not item or not item.get("price"):return False,"That item isn't sold in the shop."
        quantity=max(1,min(quantity,50)); cost=item["price"]*quantity
        if p["gold"]<cost:return False,f"You need {cost} gold."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET gold=gold-? WHERE guild_id=? AND user_id=?",(cost,guild_id,user_id)); await db.commit()
        await self.add_item(guild_id,user_id,item_key.lower(),quantity); return True,f"Bought **{item['name']} ×{quantity}** for **{cost} gold**."

    async def sell(self,guild_id,user_id,item_key,quantity=1):
        item=ITEMS.get(item_key.lower());
        if not item:return False,"Unknown item."
        quantity=max(1,quantity)
        if not await self.remove_item(guild_id,user_id,item_key.lower(),quantity):return False,"You don't have enough of that item."
        value=max(1,int(item.get("price",10)*0.45))*quantity
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET gold=gold+? WHERE guild_id=? AND user_id=?",(value,guild_id,user_id)); await db.commit()
        return True,f"Sold **{item['name']} ×{quantity}** for **{value} gold**."

    async def craft(self,guild_id,user_id,item_key,quantity=1):
        item_key=item_key.lower(); recipe=RECIPES.get(item_key)
        if not recipe:return False,"Recipe not found. Use `!rpg recipes`."
        quantity=max(1,min(quantity,10))
        for mat,need in recipe.items():
            inv=dict(await self.inventory(guild_id,user_id));
            if inv.get(mat,0)<need*quantity:return False,f"Missing **{ITEMS[mat]['name']}** ×{need*quantity}."
        for mat,need in recipe.items(): await self.remove_item(guild_id,user_id,mat,need*quantity)
        await self.add_item(guild_id,user_id,item_key,quantity)
        return True,f"Crafted **{ITEMS[item_key]['name']} ×{quantity}**."

    async def gather(self,guild_id,user_id,kind="gather"):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        if p["stamina"]<10:return False,"You are exhausted. Use `!rpg rest`."
        item=random.choice(["herb","iron_ore","wolf_pelt","herb"] if kind!="fish" else ["herb","wolf_pelt"])
        qty=random.randint(1,2)
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET stamina=stamina-10 WHERE guild_id=? AND user_id=?",(guild_id,user_id)); await db.commit()
        await self.add_item(guild_id,user_id,item,qty); await self.progress_quests(guild_id,user_id,"gather",1)
        return True,f"You gathered **{ITEMS[item]['name']} ×{qty}**. Stamina remaining: **{max(0,p['stamina']-10)}**."

    async def rest(self,guild_id,user_id):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET hp=max_hp,mp=max_mp,stamina=100 WHERE guild_id=? AND user_id=?",(guild_id,user_id)); await db.commit()
        return True,"You rested at Horizon Village. HP, MP and stamina restored."

    async def create_market(self,guild_id,user_id,item_key,quantity,price):
        if quantity<1 or price<1:return False,"Quantity and price must be positive."
        if not await self.remove_item(guild_id,user_id,item_key.lower(),quantity):return False,"You don't own enough of that item."
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("INSERT INTO rpg_market(guild_id,seller_id,item_key,quantity,price_each,created_at) VALUES(?,?,?,?,?,?)",(guild_id,user_id,item_key.lower(),quantity,price,time.time())); mid=cur.lastrowid; await db.commit()
        return True,f"Market listing `#{mid}` created."

    async def market(self,guild_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT id,seller_id,item_key,quantity,price_each FROM rpg_market WHERE guild_id=? ORDER BY id DESC LIMIT 20",(guild_id,)); return await cur.fetchall()

    async def market_buy(self,guild_id,user_id,listing_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT seller_id,item_key,quantity,price_each FROM rpg_market WHERE guild_id=? AND id=?",(guild_id,listing_id)); row=await cur.fetchone()
            if not row:return False,"Listing not found."
            seller,item,qty,price=row; total=qty*price
            p=await self.player(guild_id,user_id)
            if p["gold"]<total:return False,f"You need {total} gold."
            await db.execute("UPDATE rpg_players SET gold=gold-? WHERE guild_id=? AND user_id=?",(total,guild_id,user_id)); await db.execute("UPDATE rpg_players SET gold=gold+? WHERE guild_id=? AND user_id=?",(total,guild_id,seller)); await db.execute("DELETE FROM rpg_market WHERE id=?",(listing_id,)); await db.commit()
        await self.add_item(guild_id,user_id,item,qty); return True,f"Bought **{ITEMS.get(item,{'name':item})['name']} ×{qty}** for **{total} gold**."

    async def dungeon(self,guild_id,user_id,name=None):
        p=await self.player(guild_id,user_id)
        if not p:return {"error":"Create a hero first."}
        available=[d for d in DUNGEONS if p["level"]>=d[1]]
        d=next((x for x in available if name and x[0].lower()==name.lower()),None) if name else (available[-1] if available else None)
        if not d:return {"error":"No dungeon unlocked yet."}
        _,req,floors,xp,gold,desc=d
        hp=p["hp"]; log=[]
        for floor in range(1,floors+1):
            enemy=random.choice(ENEMIES); enemy_hp=enemy["hp"]+floor*20+p["level"]*4
            while enemy_hp>0 and hp>0:
                dmg=max(1,p["atk"]+random.randint(-2,5)-enemy["def"]//2); enemy_hp-=dmg
                if enemy_hp<=0: break
                hp-=max(1,enemy["atk"]+random.randint(-2,4)-p["defense"]//3)
            if hp<=0: break
            log.append(f"Floor {floor}: defeated **{enemy['name']}**.")
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET hp=? WHERE guild_id=? AND user_id=?",(max(1,hp),guild_id,user_id)); await db.commit()
        if hp<=0:return {"win":False,"name":d[0],"log":log+["You were defeated. Return after resting."],"hp":1}
        reward_xp=xp+floors*50; reward_gold=gold+random.randint(0,100); await self.add_rewards(guild_id,user_id,reward_xp,reward_gold); await self.add_item(guild_id,user_id,"arcane_shard" if floors>=4 else "iron_ore",floors)
        if floors>=5: await self.add_item(guild_id,user_id,"dragon_trophy",1)
        await self.progress_quests(guild_id,user_id,"dungeon",1); await self.check_achievements(guild_id,user_id)
        return {"win":True,"name":d[0],"log":log,"xp":reward_xp,"gold":reward_gold,"hp":hp}

    async def pet(self, guild_id, user_id, action="info", name="Spirit"):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT name,species,level,xp,bonus_atk,bonus_def FROM rpg_pets WHERE guild_id=? AND user_id=?",(guild_id,user_id)); pet=await cur.fetchone()
            if action=="adopt":
                if pet:return False,"You already have a companion."
                species=random.choice(["Wolf Pup","Fox Spirit","Dragon Whelp","Moon Cat"])
                await db.execute("INSERT INTO rpg_pets VALUES(?,?,?,?,?,?,?)",(guild_id,user_id,name[:24],species,1,0,2,2)); await db.commit()
                return True,f"You adopted **{name}**, a **{species}** companion."
            if action=="rename":
                if not pet:return False,"Adopt a companion first with `!rpg pet adopt <name>`."
                await db.execute("UPDATE rpg_pets SET name=? WHERE guild_id=? AND user_id=?",(name[:24],guild_id,user_id)); await db.commit(); return True,f"Your companion is now called **{name[:24]}**."
            if action=="release":
                if not pet:return False,"You have no companion."
                await db.execute("DELETE FROM rpg_pets WHERE guild_id=? AND user_id=?",(guild_id,user_id)); await db.commit(); return True,f"You released **{pet[0]}**, freeing your companion slot."
            if not pet:return False,"You have no companion. Use `!rpg pet adopt <name>`."
            return True,f"**{pet[0]}** — {pet[1]} • Lv {pet[2]} • XP {pet[3]} • +{pet[4]} ATK / +{pet[5]} DEF"

    async def party_dungeon(self,guild_id,user_id,name=None):
        info=await self.party_info(guild_id,user_id=user_id)
        if not info:return {"error":"You are not in an open party."}
        party,members=info
        if party[3] != user_id:return {"error":"Only the party leader can launch the dungeon."}
        if len(members)<2:return {"error":"Bring at least one other hero into the party first."}
        leader=await self.player(guild_id,user_id)
        available=[d for d in DUNGEONS if leader and leader["level"]>=d[1]]
        d=next((x for x in available if name and x[0].lower()==name.lower()),None) if name else (available[-1] if available else None)
        if not d:return {"error":"No dungeon is unlocked for the party leader."}
        n,req,floors,xp,gold,desc=d
        # Party power is the sum of each hero's combat stats. This keeps the
        # group game simple while making team composition matter.
        power=0
        for uid,_role in members:
            stats=await self.stats(guild_id,uid)
            if stats:
                p,gear,b=stats; power += p["atk"]+b["atk"]+p["defense"]+b["defense"]+p["speed"]+b["speed"]
        required_power=floors*55 + req*12
        chance=min(.95,max(.25,power/max(1,required_power)*.55))
        success=random.random() < chance
        if not success:
            return {"win":False,"name":n,"members":len(members),"chance":chance,"log":["The party was overwhelmed before reaching the final floor."]}
        rewards=[]
        for uid,_role in members:
            rxp=xp+floors*60; rgold=gold+random.randint(0,100)
            await self.add_rewards(guild_id,uid,rxp,rgold)
            await self.add_item(guild_id,uid,"arcane_shard" if floors>=4 else "iron_ore",max(1,floors//2))
            await self.progress_quests(guild_id,uid,"dungeon",1)
            rewards.append((uid,rxp,rgold))
        return {"win":True,"name":n,"members":len(members),"chance":chance,"rewards":rewards,"log":[f"The party cleared all **{floors} floors**.",f"Team power check passed with **{power}** combined combat power."]}

    async def guild_deposit(self,guild_id,user_id,amount):
        amount=max(1,amount); info=await self.guild_info(guild_id,user_id=user_id)
        if not info:return False,"You are not in a guild."
        p=await self.player(guild_id,user_id)
        if p["gold"]<amount:return False,"You don't have enough gold."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET gold=gold-? WHERE guild_id=? AND user_id=?",(amount,guild_id,user_id)); await db.execute("UPDATE rpg_guilds SET bank=bank+?,xp=xp+? WHERE guild_id=? AND name=?",(amount,amount//2,guild_id,info[0][1])); await db.commit()
        return True,f"Deposited **{amount} gold** into **{info[0][1]}**."

    async def guild_upgrade(self,guild_id,user_id):
        info=await self.guild_info(guild_id,user_id=user_id)
        if not info:return False,"You are not in a guild."
        g=info[0]
        level, xp = g[3], g[4]
        cost = level * 1000
        if xp < cost:return False,f"Guild needs **{cost} guild XP** for the next level."
        if g[2] != user_id:
            return False,"Only the guild leader can upgrade the guild."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_guilds SET level=level+1,xp=xp-? WHERE guild_id=? AND name=?",(cost,guild_id,g[1])); await db.commit()
        return True,f"**{g[1]}** reached guild level **{level+1}**."

    async def spend_skill(self,guild_id,user_id,stat):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        stat=stat.lower()
        mapping={"attack":"atk","atk":"atk","defense":"defense","def":"defense","speed":"speed","spd":"speed","crit":"crit","hp":"max_hp","mana":"max_mp","mp":"max_mp"}
        column=mapping.get(stat)
        if not column:return False,"Choose `attack`, `defense`, `speed`, `crit`, `hp`, or `mana`."
        if p["skill_points"]<1:return False,"You have no skill points. Level up to earn one."
        async with aiosqlite.connect(self.path) as db:
            await db.execute(f"UPDATE rpg_players SET {column}={column}+?,skill_points=skill_points-1 WHERE guild_id=? AND user_id=?",(5 if column in {"max_hp","max_mp"} else 1,guild_id,user_id)); await db.commit()
        return True,f"Skill point spent on **{stat}**."

    def _combat_stats(self, p):
        data=self._progression_bonus(p)
        return {
            "hp": p["hp"] + data["hp"], "max_hp": p["max_hp"] + data["hp"],
            "mp": p["mp"] + data["mp"], "max_mp": p["max_mp"] + data["mp"],
            "atk": p["atk"] + data["atk"], "defense": p["defense"] + data["defense"],
            "speed": p["speed"] + data["speed"], "crit": p["crit"] + data["crit"],
        }

    def _enemy_for_level(self, level, area_key="horizon_village"):
        area=AREAS.get(area_key, AREAS["horizon_village"])
        candidates=[e for e in ENEMIES if e["level"] <= max(level,area["level"])+4]
        enemy=random.choice(candidates or ENEMIES).copy()
        scale=max(0,level-enemy["level"])
        area_scale=max(0,area["level"]-enemy["level"])
        enemy["level"] += scale//2 + area_scale//3
        enemy["hp"] += scale*9 + area_scale*8
        enemy["atk"] += scale*2 + area_scale*2
        enemy["def"] += scale//2 + area_scale
        enemy["xp"] += scale*12 + area_scale*15
        enemy["gold"] += scale*8 + area_scale*10
        # Regional enemies can drop both classic materials and new themed loot.
        regional={
            "whispering_woods":["herb","mat_wolf_claw","forest_egg"],
            "ember_plains":["mat_red_herb","mat_obsidian","fire_egg"],
            "silver_coast":["mat_sea_pearl","food_grilled_fish","water_egg"],
            "moonfall_marsh":["mat_nightshade","mat_shadow_essence","moon_egg"],
            "frostpeak":["mat_frostwood","mat_sapphire","frost_egg"],
            "sunken_ruins":["mat_ancient_bone","mat_ruby","ruin_egg"],
            "skyreach":["mat_star_fragment","mat_angel_feather","sky_egg"],
            "demon_wastes":["mat_demon_horn","mat_void_crystal","demon_egg"],
            "crystal_desert":["mat_crystal_melon","mat_amber","desert_egg"],
            "astral_frontier":["mat_void_crystal","mat_star_fragment","astral_egg"],
            "world_tree":["mat_world_tree_seed","celestial_egg","phoenix_egg"],
        }
        drops=list(dict.fromkeys(enemy.get("drops",[])+regional.get(area_key,[])))
        enemy["drops"]= [d for d in drops if d in ITEMS] or ["herb"]
        return enemy

    async def start_combat(self,guild_id,user_id,mode="adventure",dungeon_name=None):
        p=await self.player(guild_id,user_id)
        if not p:return {"error":"Create a hero first."}
        key=(guild_id,user_id)
        if key in self.active_combats:return {"error":"You are already in a battle. Finish it first."}
        if p["hp"]<=0:return {"error":"You are down. Use `!rpg rest` first."}
        if mode=="adventure":
            remaining=await self._cooldown(p,"last_adventure",20)
            if remaining>0:return {"error":f"Your next adventure is ready in **{int(remaining)+1}s**."}
            enemy=self._enemy_for_level(p["level"],p.get("area_key","horizon_village"))
            state={"mode":"adventure","enemy":enemy,"enemy_hp":enemy["hp"],"player_hp":p["hp"],"player_max_hp":self._combat_stats(p)["max_hp"],"floor":1,"floors":1,"name":"Adventure","log":[f"You encountered **{enemy['name']}** in {AREAS.get(p.get('area_key','horizon_village'),AREAS['horizon_village'])['name']}."],"started":time.time()}
            async with aiosqlite.connect(self.path) as db:
                await db.execute("UPDATE rpg_players SET last_adventure=? WHERE guild_id=? AND user_id=?",(time.time(),guild_id,user_id)); await db.commit()
        else:
            available=[d for d in DUNGEONS if p["level"]>=d[1]]
            d=next((x for x in available if dungeon_name and x[0].lower()==dungeon_name.lower()),None) if dungeon_name else (available[-1] if available else None)
            if not d:return {"error":"No dungeon unlocked yet."}
            n,req,floors,xp,gold,desc=d
            enemy=self._enemy_for_level(p["level"]+req//2,"horizon_village")
            state={"mode":"dungeon","enemy":enemy,"enemy_hp":enemy["hp"]+20,"player_hp":p["hp"],"player_max_hp":self._combat_stats(p)["max_hp"],"floor":1,"floors":floors,"name":n,"reward_xp":xp,"reward_gold":gold,"log":[f"**Floor 1/{floors}** — {enemy['name']} blocks your path."],"started":time.time()}
        self.active_combats[key]=state
        return {"state":state,"stats":self._combat_stats(p)}

    async def combat_action(self,guild_id,user_id,action):
        key=(guild_id,user_id); state=self.active_combats.get(key)
        if not state:return {"error":"No active battle."}
        p=await self.player(guild_id,user_id)
        if not p:return {"error":"Character not found."}
        stats=self._combat_stats(p); action=action.lower()
        log=[]; defending=False
        if action=="attack":
            crit=random.random()<min(.65,stats["crit"]/100)
            dmg=max(1,stats["atk"]+random.randint(-3,5)-state["enemy"].get("def",0)//2)
            if crit:dmg*=2
            state["enemy_hp"]-=dmg; log.append(f"You hit **{state['enemy']['name']}** for **{dmg}**{' CRITICAL' if crit else ''}.")
        elif action=="skill":
            costs={"mage":15,"warlock":15,"necromancer":15,"cleric":12,"paladin":10,"druid":12,"summoner":12,"spellblade":10}
            cost=costs.get(p["class_name"],8)
            if p["mp"]<cost:return {"error":f"You need **{cost} MP** for your class skill."}
            skill_mult=1.65 if p["class_name"] in {"mage","warlock","necromancer"} else 1.45
            dmg=max(2,int(stats["atk"]*skill_mult)+random.randint(0,8)-state["enemy"].get("def",0)//3)
            state["enemy_hp"]-=dmg
            async with aiosqlite.connect(self.path) as db:
                await db.execute("UPDATE rpg_players SET mp=max(0,mp-?) WHERE guild_id=? AND user_id=?",(cost,guild_id,user_id)); await db.commit()
            log.append(f"✨ **{p['class_name'].title()} skill** dealt **{dmg}** damage.")
        elif action in {"potion","food"}:
            inv=dict(await self.inventory(guild_id,user_id))
            choices=[(k,q) for k,q in inv.items() if q>0 and ITEMS.get(k,{}).get("slot") in {"consumable","food"}]
            if not choices:return {"error":"You have no usable potion or food."}
            # Prefer the strongest recovery item available.
            item=max((k for k,_ in choices), key=lambda k: ITEMS[k].get("heal",0)+ITEMS[k].get("stamina",0)*2+ITEMS[k].get("mana",0))
            data=ITEMS[item]
            if not await self.remove_item(guild_id,user_id,item,1):return {"error":"That item is no longer available."}
            heal=data.get("heal",0); mana=data.get("mana",0)
            await self._apply_recovery(guild_id,user_id,heal,mana)
            state["player_hp"]=min(stats["max_hp"],state["player_hp"]+heal)
            log.append(f"🍖 You used **{data['name']}** and recovered **{heal} HP**{' and '+str(mana)+' MP' if mana else ''}.")
        elif action=="defend":
            defending=True; log.append("🛡️ You brace for the next hit, reducing incoming damage.")
        elif action=="flee":
            if state["mode"]=="dungeon" and state["floor"]>1:return {"error":"You cannot flee after the first dungeon floor."}
            if random.random()<0.65:
                self.active_combats.pop(key,None)
                await self._set_hp(guild_id,user_id,max(1,state["player_hp"]))
                return {"finished":True,"win":False,"fled":True,"log":[*state["log"],"🏃 You escaped the battle."]}
            log.append("You failed to escape!")
        else:
            return {"error":"Choose Attack, Skill, Potion, Defend or Flee."}
        state["log"].extend(log)
        if state["enemy_hp"]<=0:
            if state["mode"]=="dungeon" and state["floor"]<state["floors"]:
                state["floor"]+=1
                state["enemy"]=self._enemy_for_level(p["level"]+state["floor"],p.get("area_key","horizon_village"))
                state["enemy_hp"]=state["enemy"]["hp"]+state["floor"]*18
                state["player_hp"]=min(stats["max_hp"],state["player_hp"]+max(5,stats["max_hp"]//8))
                state["log"].append(f"🏰 **Floor {state['floor']}/{state['floors']}** — **{state['enemy']['name']}** appears. You recover a little HP between floors.")
                await self._set_hp(guild_id,user_id,state["player_hp"])
                return {"finished":False,"state":state,"stats":stats}
            xp=(state.get("enemy",{}).get("xp",40)+random.randint(0,25)) if state["mode"]=="adventure" else state["reward_xp"]+state["floors"]*55
            gold=(state.get("enemy",{}).get("gold",30)+random.randint(0,35)) if state["mode"]=="adventure" else state["reward_gold"]+random.randint(0,120)
            drop=random.choice(state["enemy"].get("drops",["herb"]))
            if random.random()<0.08:
                egg_pool=[k for k,v in ITEMS.items() if v.get("slot")=="egg" and (v.get("rarity") in {"common","uncommon","rare"} or p["level"]>=20)]
                if egg_pool: drop=random.choice(egg_pool)
            await self._set_hp(guild_id,user_id,max(1,state["player_hp"]))
            old_level,new_level=await self.add_rewards(guild_id,user_id,xp,gold); await self.add_item(guild_id,user_id,drop,1)
            await self.progress_quests(guild_id,user_id,"hunt",1)
            if state["mode"]=="dungeon":
                await self.progress_quests(guild_id,user_id,"dungeon",1)
                if state["floors"]>=5:await self.add_item(guild_id,user_id,"dragon_trophy",1)
            await self.check_achievements(guild_id,user_id)
            self.active_combats.pop(key,None)
            return {"finished":True,"win":True,"xp":xp,"gold":gold,"drop":drop,"state":state,"level_before":old_level,"level_after":new_level}
        # Enemy's turn after player action.
        if not defending and random.random()<min(.18,stats["speed"]/220):
            state["log"].append(f"💨 You dodged **{state['enemy']['name']}**.")
        else:
            dmg=max(1,state["enemy"]["atk"]+random.randint(-3,4)-stats["defense"]//3)
            if defending:dmg=max(1,dmg//2)
            state["player_hp"]-=dmg; state["log"].append(f"🩸 **{state['enemy']['name']}** hit you for **{dmg}**.")
        if state["player_hp"]<=0:
            state["player_hp"]=1; await self._set_hp(guild_id,user_id,1); self.active_combats.pop(key,None)
            return {"finished":True,"win":False,"state":state,"defeated":True}
        await self._set_hp(guild_id,user_id,state["player_hp"])
        return {"finished":False,"state":state,"stats":stats}

    async def _set_hp(self,guild_id,user_id,hp):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET hp=? WHERE guild_id=? AND user_id=?",(max(1,int(hp)),guild_id,user_id)); await db.commit()

    async def _apply_recovery(self,guild_id,user_id,heal,mana):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET hp=min(max_hp,hp+?),mp=min(max_mp,mp+?) WHERE guild_id=? AND user_id=?",(heal,mana,guild_id,user_id)); await db.commit()

    async def travel(self,guild_id,user_id,area_key):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        area=AREAS.get(area_key.lower())
        if not area:return False,"Unknown area. Use `!rpg areas`."
        if p["level"]<area["level"]:return False,f"That area requires level **{area['level']}**."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET area_key=?,location=? WHERE guild_id=? AND user_id=?",(area_key.lower(),area["name"],guild_id,user_id)); await db.commit()
        return True,f"You traveled to **{area['name']}**. {area['desc']}"

    async def egg_hatch(self,guild_id,user_id,egg_key,name="Spirit"):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        egg_key=egg_key.lower(); data=ITEMS.get(egg_key)
        if not data or data.get("slot")!="egg":return False,"That is not a pet egg."
        if not await self.remove_item(guild_id,user_id,egg_key,1):return False,"You don't own that egg."
        species_by={"common":["Wolf Pup","Rabbit","Fox","Cat"],"uncommon":["Forest Wolf","Moon Fox","Hawk","Dire Hound"],"rare":["Moon Cat","Spirit Fox","Griffin Chick","Frost Wolf"],"epic":["Dragon Whelp","Phoenix Chick","Royal Griffin","Shadow Drake"],"legendary":["Phoenix","Elder Dragon","Celestial Lion"],"mythic":["Void Dragon","Star Serpent","World Tree Sprite"]}
        rarity=data.get("rarity","common"); species=random.choice(species_by.get(rarity,species_by["common"]))
        bonus=2+{"common":0,"uncommon":2,"rare":4,"epic":7,"legendary":11,"mythic":16}.get(rarity,0)
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT 1 FROM rpg_pets WHERE guild_id=? AND user_id=?",(guild_id,user_id)); exists=await cur.fetchone()
            if exists:return False,"You already have a companion. Release or rename it first."
            await db.execute("INSERT INTO rpg_pets VALUES(?,?,?,?,?,?,?)",(guild_id,user_id,name[:24],species,1,0,bonus,bonus)); await db.commit()
        return True,f"The **{data['name']}** hatched into **{species}**! Your pet starts with **+{bonus} ATK / +{bonus} DEF**."

    async def kingdom_list(self,guild_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT name,ruler_id,level,treasury,renown FROM rpg_kingdoms WHERE guild_id=? ORDER BY level DESC,renown DESC",(guild_id,)); return await cur.fetchall()

    async def kingdom_create(self,guild_id,user_id,name):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        if p["level"]<15:return False,"Founding a kingdom requires **level 15**."
        if p["gold"]<50000:return False,"Founding a kingdom requires **50,000 gold**."
        name=name.strip()[:32]
        if not name:return False,"Give your kingdom a name."
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT 1 FROM rpg_kingdoms WHERE guild_id=? AND lower(name)=lower(?)",(guild_id,name))
            if await cur.fetchone():return False,"That kingdom already exists."
            await db.execute("INSERT INTO rpg_kingdoms(guild_id,name,ruler_id,treasury,created_at) VALUES(?,?,?,?,?)",(guild_id,name,user_id,0,time.time()))
            await db.execute("INSERT INTO rpg_kingdom_members VALUES(?,?,?,?,?)",(guild_id,name,user_id,"king",time.time()))
            await db.execute("UPDATE rpg_players SET gold=gold-50000,kingdom_name=?,kingdom_role=?,title='King',life_path='royal',renown=renown+100 WHERE guild_id=? AND user_id=?",(name,"king",guild_id,user_id)); await db.commit()
        return True,f"**{name}** has been founded. You are its **King**."

    async def kingdom_join(self,guild_id,user_id,name):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT name FROM rpg_kingdoms WHERE guild_id=? AND lower(name)=lower(?)",(guild_id,name)); row=await cur.fetchone()
            if not row:return False,"Kingdom not found."
            await db.execute("DELETE FROM rpg_kingdom_members WHERE guild_id=? AND user_id=?",(guild_id,user_id))
            await db.execute("INSERT INTO rpg_kingdom_members VALUES(?,?,?,?,?)",(guild_id,row[0],user_id,"citizen",time.time()))
            await db.execute("UPDATE rpg_players SET kingdom_name=?,kingdom_role='citizen',life_path='noble' WHERE guild_id=? AND user_id=?",(row[0],guild_id,user_id)); await db.commit()
        return True,f"You joined **{row[0]}** as a citizen."

    async def kingdom_info(self,guild_id,name=None,user_id=None):
        async with aiosqlite.connect(self.path) as db:
            if name:cur=await db.execute("SELECT * FROM rpg_kingdoms WHERE guild_id=? AND lower(name)=lower(?)",(guild_id,name))
            elif user_id:cur=await db.execute("SELECT k.* FROM rpg_kingdoms k JOIN rpg_kingdom_members m ON k.guild_id=m.guild_id AND k.name=m.kingdom_name WHERE k.guild_id=? AND m.user_id=? LIMIT 1",(guild_id,user_id))
            else:cur=await db.execute("SELECT * FROM rpg_kingdoms WHERE guild_id=? ORDER BY level DESC LIMIT 1",(guild_id,))
            kingdom=await cur.fetchone()
            if not kingdom:return None
            cur=await db.execute("SELECT user_id,role FROM rpg_kingdom_members WHERE guild_id=? AND kingdom_name=? ORDER BY role",(guild_id,kingdom[1])); members=await cur.fetchall()
            return kingdom,members

    async def kingdom_promote(self,guild_id,user_id,target_id,role):
        role=role.lower(); info=await self.kingdom_info(guild_id,user_id=user_id)
        if not info:return False,"You are not in a kingdom."
        k,members=info
        if k[2]!=user_id:return False,"Only the King can appoint nobles."
        if role not in KINGDOM_ROLES or role=="king":return False,"Appoint: duke, count, knight, citizen or outlaw."
        if not any(uid==target_id for uid,_ in members):return False,"That player is not in your kingdom."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_kingdom_members SET role=? WHERE guild_id=? AND kingdom_name=? AND user_id=?",(role,guild_id,k[1],target_id))
            await db.execute("UPDATE rpg_players SET kingdom_role=?,title=? WHERE guild_id=? AND user_id=?",(role,role.title(),guild_id,target_id)); await db.commit()
        return True,f"<@{target_id}> is now a **{role.title()}** of **{k[1]}**."

    async def kingdom_leave(self,guild_id,user_id):
        info=await self.kingdom_info(guild_id,user_id=user_id)
        if not info:return False,"You are not in a kingdom."
        k,_=info
        if k[2]==user_id:return False,"The King cannot leave. Abdicate by transferring the crown first."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM rpg_kingdom_members WHERE guild_id=? AND kingdom_name=? AND user_id=?",(guild_id,k[1],user_id))
            await db.execute("UPDATE rpg_players SET kingdom_name='',kingdom_role='',title='Adventurer' WHERE guild_id=? AND user_id=?",(guild_id,user_id)); await db.commit()
        return True,f"You left **{k[1]}**."

    async def bounty_post(self,guild_id,user_id,target_name,reward):
        if reward<100:return False,"Bounties must be at least 100 gold."
        p=await self.player(guild_id,user_id)
        if not p or p["gold"]<reward:return False,"You don't have enough gold."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET gold=gold-? WHERE guild_id=? AND user_id=?",(reward,guild_id,user_id))
            await db.execute("INSERT INTO rpg_bounties(guild_id,poster_id,target_name,reward,created_at) VALUES(?,?,?,?,?)",(guild_id,user_id,target_name[:64],reward,time.time())); await db.commit()
        return True,f"Bounty posted on **{target_name}** for **{reward} gold**."

    async def bounties(self,guild_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT id,target_name,reward,poster_id FROM rpg_bounties WHERE guild_id=? AND status='open' ORDER BY reward DESC LIMIT 20",(guild_id,)); return await cur.fetchall()

    async def duel(self,guild_id,user_id,target_id):
        a=await self.player(guild_id,user_id); b=await self.player(guild_id,target_id)
        if not a or not b:return {"error":"Both players need RPG characters."}
        if user_id==target_id:return {"error":"You can't duel yourself."}
        # Lightweight deterministic turn simulation using the same combat stats as PvE.
        ahp,bhp=a["hp"],b["hp"]; log=[]; turn=0
        order=[("a",a,b), ("b",b,a)] if a["speed"]>=b["speed"] else [("b",b,a),("a",a,b)]
        while ahp>0 and bhp>0 and turn<40:
            turn+=1
            for who,att,defn in order:
                if ahp<=0 or bhp<=0: break
                dmg=max(1,att["atk"]+random.randint(-2,4)-defn["defense"]//2)
                if who=="a": bhp-=dmg
                else: ahp-=dmg
                log.append((who,dmg))
        winner=user_id if bhp<=0 else target_id
        loser=target_id if winner==user_id else user_id
        await self.add_rewards(guild_id,winner,80,120)
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET hp=max(1,hp) WHERE guild_id=? AND user_id=?",(guild_id,loser)); await db.commit()
        return {"winner":winner,"loser":loser,"log":log[-10:]}
