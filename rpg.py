from __future__ import annotations

import asyncio
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

# Matchups are intentionally mild (+/- 10%) so counters matter without making
# a build unwinnable. These are shown before selection and applied only in PvP.
RACE_MATCHUPS = {
    "human": {"vampire": 1.08, "golem": 0.96},
    "elf": {"orc": 1.08, "golem": 0.94},
    "dwarf": {"golem": 1.08, "dragonkin": 0.96},
    "orc": {"dwarf": 1.06, "elf": 0.96},
    "kitsune": {"golem": 0.94, "vampire": 1.05},
    "fae": {"golem": 0.94, "orc": 1.07},
    "vampire": {"fae": 1.06, "human": 0.92},
    "golem": {"orc": 1.06, "elf": 1.06},
    "dragonkin": {"golem": 1.04, "dwarf": 1.04},
}
RACE_ABILITIES = {
    "human": ("Adaptability", "Gain a small balanced bonus to all core combat stats."),
    "elf": ("Keen Sight", "Higher critical chance and precision."),
    "dwarf": ("Stonebody", "Defense percentage is increased."),
    "orc": ("Bloodrage", "Attack rises when below half HP."),
    "kitsune": ("Trickster Step", "Improved evasion and speed."),
    "halfling": ("Lucky", "Higher critical chance and lucky outcomes."),
    "tiefling": ("Infernal Blood", "Attack is stronger against holy builds, but holy counters it slightly."),
    "dragonkin": ("Dragonhide", "Extra defense and HP resilience."),
    "beastfolk": ("Predator Instinct", "Speed and critical chance are improved."),
    "fae": ("Feystep", "Improved evasion and magic mobility."),
    "vampire": ("Blood Hunger", "A small life-steal effect in combat; holy matchups counter it."),
    "golem": ("Stoneform", "Large HP/defense resilience at the cost of speed."),
}

CLASS_MATCHUPS = {
    "paladin": {"necromancer": 1.10, "warlock": 1.08},
    "cleric": {"necromancer": 1.10, "vampire": 1.06},
    "necromancer": {"druid": 1.08, "paladin": 0.92},
    "warlock": {"cleric": 1.08, "paladin": 0.94},
    "mage": {"knight": 1.06, "berserker": 0.96},
    "assassin": {"mage": 1.08, "knight": 0.94},
    "ranger": {"summoner": 1.06, "berserker": 0.96},
    "monk": {"mage": 1.05, "ranger": 0.97},
    "duelist": {"mage": 1.05, "knight": 0.97},
    "spellblade": {"warlock": 1.05, "berserker": 0.97},
}

def matchup_multiplier(attacker_race, attacker_class, defender_race, defender_class):
    value=float(RACE_MATCHUPS.get(attacker_race,{}).get(defender_race,1.0))
    value*=float(CLASS_MATCHUPS.get(attacker_class,{}).get(defender_class,1.0))
    return max(.90,min(1.10,value))

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


# ---------------------------------------------------------------------------
# Combat skills. Each class has a small, readable kit so battles are about
# choosing the right action instead of pressing one "Skill" button forever.
# Keys are stable so old characters automatically receive their class kit.
# ---------------------------------------------------------------------------
CLASS_SKILL_NAMES = {
    "warrior": ("Power Strike", "Guard Break", "Whirlwind", "Iron Will"),
    "berserker": ("Raging Slash", "Blood Rush", "Rampage", "Berserker Fury"),
    "knight": ("Shield Bash", "Crushing Blow", "Guardian Wall", "Royal Verdict"),
    "mage": ("Arcane Bolt", "Flame Burst", "Frost Nova", "Meteor"),
    "rogue": ("Twin Strike", "Poison Edge", "Shadow Step", "Assassinate"),
    "assassin": ("Killing Edge", "Venom Cut", "Phantom Step", "Death Mark"),
    "ranger": ("Aimed Shot", "Piercing Arrow", "Rain of Arrows", "Hunter's Mark"),
    "paladin": ("Holy Strike", "Radiant Shield", "Divine Light", "Judgment"),
    "summoner": ("Spirit Bolt", "Beast Assault", "Soul Link", "Primal Storm"),
    "cleric": ("Holy Bolt", "Smite", "Renew", "Divine Grace"),
    "druid": ("Thorn Lash", "Moonfire", "Nature's Gift", "Wild Tempest"),
    "monk": ("Chi Strike", "Flurry", "Inner Focus", "Dragon Fist"),
    "bard": ("Sonic Note", "Battle Anthem", "Healing Melody", "Finale"),
    "necromancer": ("Soul Bolt", "Bone Spear", "Dark Pact", "Soul Requiem"),
    "warlock": ("Shadow Bolt", "Chaos Brand", "Life Drain", "Doom"),
    "alchemist": ("Acid Flask", "Bomb Toss", "Rejuvenation", "Grand Transmutation"),
    "engineer": ("Arc Shot", "Turret Burst", "Repair Drone", "Overclock"),
    "duelist": ("Riposte", "Lunge", "Blade Dance", "Perfect Duel"),
    "lancer": ("Spear Thrust", "Vault", "Dragon Dive", "Heaven Pierce"),
    "spellblade": ("Arcane Slash", "Elemental Edge", "Mana Guard", "Ether Break"),
}

# Six additional skills per class. They unlock progressively instead of all
# being available at level 1, so high-level builds have meaningful choices.
ADVANCED_SKILLS = {
    "warrior": ("Cleave", "Battle Cry", "Sword Storm", "Lionheart", "King's Edge", "Warlord's Ascension"),
    "berserker": ("Savage Break", "Frenzy", "Blood Cyclone", "Rage Unbound", "Executioner", "Worldbreaker"),
    "knight": ("Shield Counter", "Fortress", "Knight's Oath", "Aegis Crash", "Royal Bulwark", "Divine Bastion"),
    "mage": ("Arcane Lance", "Inferno", "Glacial Prison", "Arcane Barrage", "Starfall", "Cataclysm"),
    "rogue": ("Bleeding Flurry", "Smoke Veil", "Crimson Dance", "Phantom Barrage", "Death Spiral", "Eclipse"),
    "assassin": ("Hemorrhage", "Veiled Step", "Nightmare Cut", "Phantom Barrage", "Silent Execution", "Void Reaper"),
    "ranger": ("Volley", "Trap Mastery", "Storm Shot", "Predator's Mark", "Star Arrow", "Heaven's Volley"),
    "paladin": ("Consecrated Blade", "Holy Ward", "Radiant Burst", "Guardian's Grace", "Sacred Verdict", "Heaven's Judgment"),
    "summoner": ("Spirit Swarm", "Beast Guard", "Soul Chain", "Primal Roar", "Astral Summon", "World Caller"),
    "cleric": ("Radiant Lance", "Blessed Ward", "Mass Renewal", "Holy Nova", "Seraphic Grace", "Divine Ascension"),
    "druid": ("Vine Prison", "Lunar Bloom", "Nature's Ward", "Wildfire", "Ancient Grove", "Worldroot"),
    "monk": ("Palm Burst", "Iron Body", "Sevenfold Strike", "Chi Storm", "Heavenly Fist", "Dragon Ascension"),
    "bard": ("Resonant Blast", "War Chorus", "Soothing Verse", "Grand Crescendo", "Heroic Symphony", "Mythic Finale"),
    "necromancer": ("Grave Lance", "Bone Prison", "Soul Feast", "Army of Bones", "Deathstorm", "Eternal Night"),
    "warlock": ("Abyssal Lance", "Hex Prison", "Soul Siphon", "Chaos Rain", "Demon's Wrath", "Void Apocalypse"),
    "alchemist": ("Corrosive Flask", "Chain Reaction", "Vital Elixir", "Grand Bombardment", "Philosopher's Fire", "Perfect Transmutation"),
    "engineer": ("Piercing Bolt", "Auto-Turret", "Repair Matrix", "Overdrive", "Siege Cannon", "Omega Protocol"),
    "duelist": ("Countercut", "Flash Lunge", "Blade Tempest", "Perfect Tempo", "Sword Eclipse", "Absolute Duel"),
    "lancer": ("Impale", "Sky Vault", "Dragon Rush", "Spear Tempest", "Heavenfall", "Dragon Emperor"),
    "spellblade": ("Runic Slash", "Elemental Storm", "Arcane Guard", "Ether Surge", "Astral Edge", "Reality Break"),
}

MAGIC_CLASSES = {"mage", "summoner", "cleric", "druid", "bard", "necromancer", "warlock", "alchemist"}
HEAL_CLASSES = {"paladin", "cleric", "druid", "bard", "alchemist", "engineer", "warlock", "summoner"}

# ---------------------------------------------------------------------------
# Deep skill system
# Every class now has 50 genuinely different skills.  The first ten preserve
# the original stable skill names/keys so existing characters and saved combat
# state remain compatible.  The remaining skills are generated from distinct
# mechanics rather than being simple renamed damage buttons.
# ---------------------------------------------------------------------------
SKILL_UNLOCK_LEVELS = (
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
    12, 14, 16, 18, 20, 22, 24, 26, 28, 30,
    32, 34, 36, 38, 40, 42, 44, 46, 48, 50,
    52, 54, 56, 58, 60, 62, 64, 66, 68, 70,
    72, 74, 76, 78, 80, 84, 88, 92, 96, 100,
)
SKILL_COSTS = tuple(min(150, 8 + int(i * 3.0 + (i ** 1.18) * 0.8)) for i in range(50))
SKILL_COOLDOWNS = tuple(0 if i < 4 else (1 + i // 12) for i in range(50))

SKILL_MECHANICS = [
    ("damage", "Direct strike", "Deals reliable weapon or spell damage."),
    ("heavy", "Heavy strike", "Deals slower, heavier damage with stronger scaling."),
    ("bleed", "Bleeding wound", "Deals damage and applies a bleed for the next two turns."),
    ("multi", "Multi-hit", "Strikes twice with reduced damage per hit."),
    ("heal", "Restoration", "Restores a meaningful amount of HP."),
    ("defend", "Guard stance", "Cuts the next incoming hit and grants a short guard state."),
    ("attack_buff", "Attack stance", "Raises attack for the next few turns."),
    ("def_buff", "Defense stance", "Raises defense for the next few turns."),
    ("lifesteal", "Life drain", "Deals damage and converts part of it into HP."),
    ("armor_break", "Armor break", "Deals damage and temporarily reduces enemy defense."),
    ("mark", "Mark target", "Marks the enemy, increasing the next few hits against it."),
    ("poison", "Poison", "Applies a stacking damage-over-time poison."),
    ("burn", "Burn", "Applies a burning damage-over-time effect."),
    ("freeze", "Freeze", "Deals damage and has a chance to slow the enemy's next turn."),
    ("crit", "Precision burst", "Temporarily raises critical chance before striking."),
    ("dodge", "Evasion", "Grants a short window of improved evasion."),
    ("mana_drain", "Mana siphon", "Damages the enemy while restoring some MP."),
    ("stamina", "Adrenaline", "Restores stamina and deals a quick attack."),
    ("counter", "Counter stance", "Reduces the next hit and retaliates when struck."),
    ("reflect", "Reflect barrier", "Reduces the next incoming hit and reflects part of it."),
    ("cleanse", "Cleanse", "Removes negative combat effects and restores a little HP."),
    ("barrier", "Arcane barrier", "Creates a temporary damage shield."),
    ("haste", "Haste", "Improves speed and evasion for several turns."),
    ("focus", "Focus", "Improves critical chance and skill efficiency briefly."),
    ("vulnerability", "Expose weakness", "Makes the enemy take increased damage briefly."),
    ("silence", "Disruption", "Suppresses the enemy's special behavior briefly."),
    ("execute", "Execution", "Deals bonus damage when the enemy is already weakened."),
    ("true_damage", "True damage", "Ignores most defense, but has a controlled multiplier."),
    ("percent_damage", "Vital strike", "Deals a small percentage of enemy maximum HP."),
    ("aoe", "Area burst", "Wide attack designed for packs and dungeon waves."),
    ("chain", "Chain reaction", "A hit that grows stronger after successful attacks."),
    ("summon", "Summoning", "Calls a temporary combat spirit for a bonus strike."),
    ("pet_boost", "Companion bond", "Empowers the equipped pet and triggers its ability."),
    ("resource", "Resource surge", "Restores MP and stamina while dealing light damage."),
    ("team_heal", "Battlefield recovery", "Strong self-heal designed for group/PvP support."),
    ("team_buff", "Rally", "Grants a broad temporary combat-stat boost."),
    ("dispel", "Dispel", "Removes enemy buffs and then strikes."),
    ("terrain", "Terrain control", "Creates a short-lived field effect that alters combat."),
    ("delayed", "Delayed strike", "Plants a powerful hit that lands after one turn."),
    ("random", "Wild technique", "Chooses one of several controlled effects at random."),
    ("sacrifice", "Sacrificial power", "Consumes a small amount of HP for a powerful attack."),
    ("emergency", "Last stand", "Becomes stronger when the hero is below half HP."),
    ("stance", "Adaptive stance", "Switches between offense and defense based on current HP."),
    ("combo", "Combo finisher", "Gets stronger after consecutive successful actions."),
    ("recovery", "Second wind", "Restores HP and MP with a long cooldown."),
    ("mana_burst", "Mana burst", "Converts stored magical power into a controlled burst."),
    ("curse", "Curse", "Marks the enemy with a stacking weakening curse."),
    ("ultimate", "Ultimate", "High-impact signature attack with a strict cooldown."),
    ("mythic", "Mythic technique", "Late-game class-defining ability with multiple effects."),
    ("signature", "Signature", "A unique capstone that combines the class identity."),
]

_SKILL_NAME_SUFFIXES = [
    "Edge", "Surge", "Break", "Pulse", "Ward", "Rush", "Nova", "Veil", "Crescent", "Drive",
    "Fang", "Brand", "Tempest", "Prism", "Aegis", "Howl", "Burst", "Requiem", "Spear", "Crown",
    "Cascade", "Rift", "Oath", "Mirage", "Torrent", "Vortex", "Halo", "Ruin", "Bloom", "Roar",
    "Chain", "Ascension", "Overture", "Dominion", "Fury", "Sanctum", "Execution", "Apocalypse", "Genesis", "Eclipse",
]

# Class identities change how the same mechanical family is presented.  The
# actual effect is still distinct per skill so players can choose builds.
_CLASS_FLAVOUR = {
    "warrior":"martial", "berserker":"rage", "knight":"guardian", "mage":"arcane",
    "rogue":"shadow", "assassin":"lethal", "ranger":"precision", "paladin":"holy",
    "summoner":"spirit", "cleric":"sacred", "druid":"nature", "monk":"chi",
    "bard":"resonance", "necromancer":"death", "warlock":"abyssal", "alchemist":"alchemy",
    "engineer":"magitech", "duelist":"dueling", "lancer":"dragon", "spellblade":"rune",
}


def _build_class_skills():
    result = {}
    for class_name, base_names in CLASS_SKILL_NAMES.items():
        names = list(base_names) + list(ADVANCED_SKILLS.get(class_name, ()))
        # Preserve the original ten names first.
        generated_names = list(names)
        flavour = _CLASS_FLAVOUR.get(class_name, class_name)
        for suffix in _SKILL_NAME_SUFFIXES:
            generated_names.append(f"{flavour.title()} {suffix}")
        skills = []
        for i in range(50):
            name = generated_names[i] if i < len(generated_names) else f"{flavour.title()} Technique {i+1}"
            effect, mechanic_name, mechanic_desc = SKILL_MECHANICS[i]
            # Keep class identity visible in the first core skills as well as in
            # the later specialized techniques.
            if class_name in HEAL_CLASSES and i in {2,4,8}:
                effect, mechanic_name, mechanic_desc = ("heal", "Restoration", "Restores HP and is especially effective for support-oriented classes.")
            elif class_name in {"knight","warrior","paladin"} and i in {5,6}:
                effect, mechanic_name, mechanic_desc = ("def_buff", "Guarding stance", "Raises defense and reduces incoming damage for several turns.")
            elif class_name in {"assassin","rogue","duelist"} and i in {2,8}:
                effect, mechanic_name, mechanic_desc = ("crit", "Precision burst", "Temporarily raises critical chance before striking.")
            elif class_name in {"necromancer","warlock"} and i in {4,8}:
                effect, mechanic_name, mechanic_desc = ("lifesteal", "Soul drain", "Deals damage and converts part of it into HP.")
            # Scale carefully: damage growth is bounded by combat caps below.
            mult = round(0.82 + min(1.58, i * 0.035), 3)
            if effect in {"heal", "recovery", "team_heal"}:
                mult = round(0.20 + min(0.35, i * 0.006), 3)
            desc = mechanic_desc
            skills.append({
                "key": f"skill_{i+1}",
                "name": name,
                "cost": SKILL_COSTS[i],
                "mult": mult,
                "effect": effect,
                "cooldown": SKILL_COOLDOWNS[i],
                "unlock": SKILL_UNLOCK_LEVELS[i],
                "mechanic": mechanic_name,
                "desc": desc,
            })
        result[class_name] = skills
    return result


SKILLS = _build_class_skills()


# Combat constants: damage is deliberately slower than character growth so
# enemies cannot be deleted by a single basic hit or low-level skill.
CRIT_DAMAGE_MULT = 1.50
CRIT_CAP = 35
PLAYER_DAMAGE_VARIANCE = 0.08
ENEMY_DAMAGE_VARIANCE = 0.08
DEFENSE_SCALE = 1.8
MAX_NORMAL_DAMAGE_FRACTION = 0.28
MP_REGEN_FRACTION = 0.025
MIN_MP_REGEN = 2


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

# A much larger world map.  Areas are deliberately tiered so travel, enemy
# scaling and loot progression have clear identities rather than being cosmetic.
AREAS.update({
    "sunmeadow": {"name":"Sunmeadow", "level":3, "type":"plains", "desc":"Warm grasslands where young adventurers learn to hunt."},
    "mossy_grotto": {"name":"Mossy Grotto", "level":4, "type":"cave", "desc":"A damp cave rich in ore, fungi and lurking beasts."},
    "redleaf_forest": {"name":"Redleaf Forest", "level":6, "type":"forest", "desc":"A crimson woodland with territorial spirits."},
    "pirate_isles": {"name":"Pirate Isles", "level":8, "type":"islands", "desc":"Lawless islands packed with treasure and sea raiders."},
    "starlit_grove": {"name":"Starlit Grove", "level":9, "type":"forest", "desc":"A magical grove where night never fully fades."},
    "blackfen": {"name":"Blackfen", "level":11, "type":"swamp", "desc":"Toxic wetlands haunted by alchemical creatures."},
    "frostwood": {"name":"Frostwood", "level":12, "type":"forest", "desc":"A frozen forest where ancient wolves roam."},
    "thunder_cliffs": {"name":"Thunder Cliffs", "level":14, "type":"cliffs", "desc":"Storm-lashed cliffs charged with elemental energy."},
    "crimson_canyon": {"name":"Crimson Canyon", "level":15, "type":"canyon", "desc":"A deep red canyon filled with ambush predators."},
    "coral_depths": {"name":"Coral Depths", "level":17, "type":"undersea", "desc":"An underwater realm of ruins and giant sea life."},
    "forgotten_catacombs": {"name":"Forgotten Catacombs", "level":18, "type":"underground", "desc":"Burial halls where restless spirits gather."},
    "mist_valley": {"name":"Mist Valley", "level":19, "type":"valley", "desc":"A fog-covered valley that distorts distance and sound."},
    "floating_gardens": {"name":"Floating Gardens", "level":21, "type":"sky", "desc":"Aerial gardens protected by celestial beasts."},
    "storm_islands": {"name":"Storm Islands", "level":22, "type":"sky", "desc":"Islands trapped inside an endless magical storm."},
    "obsidian_fortress": {"name":"Obsidian Fortress", "level":23, "type":"fortress", "desc":"A black citadel occupied by elite warbands."},
    "ash_valley": {"name":"Ash Valley", "level":24, "type":"volcanic", "desc":"A volcanic valley where heat itself becomes a weapon."},
    "inferno_gate": {"name":"Inferno Gate", "level":27, "type":"hell", "desc":"The first stable gate into the lower infernal realms."},
    "blood_moon_fields": {"name":"Blood Moon Fields", "level":28, "type":"cursed", "desc":"A battlefield permanently illuminated by a red moon."},
    "glass_dunes": {"name":"Glass Dunes", "level":32, "type":"desert", "desc":"Sand fused into razor-sharp crystal by ancient magic."},
    "mirage_city": {"name":"Mirage City", "level":34, "type":"city", "desc":"A shifting desert city that appears in different places."},
    "ancient_colosseum": {"name":"Ancient Colosseum", "level":36, "type":"arena", "desc":"An abandoned arena where magical echoes still fight."},
    "thunder_sanctum": {"name":"Thunder Sanctum", "level":38, "type":"temple", "desc":"A storm temple guarded by lightning spirits."},
    "void_border": {"name":"Void Border", "level":42, "type":"void", "desc":"Reality begins to fracture at the edge of the world."},
    "dreaming_sea": {"name":"Dreaming Sea", "level":44, "type":"astral", "desc":"A surreal ocean that reacts to thought and emotion."},
    "starfall_ruins": {"name":"Starfall Ruins", "level":46, "type":"ruins", "desc":"Ancient ruins built around fallen celestial stones."},
    "celestial_spire": {"name":"Celestial Spire", "level":48, "type":"sky", "desc":"A tower reaching beyond the clouds and into the stars."},
    "worldroot_caves": {"name":"Worldroot Caves", "level":52, "type":"mythic", "desc":"Caverns beneath the roots of the World Tree."},
    "eternal_library": {"name":"Eternal Library", "level":55, "type":"arcane", "desc":"A forbidden library containing living spells."},
    "dragon_graveyard": {"name":"Dragon Graveyard", "level":58, "type":"graveyard", "desc":"The bones of ancient dragons form a deadly landscape."},
    "chaos_realm": {"name":"Chaos Realm", "level":62, "type":"chaos", "desc":"A realm where physical laws change between battles."},
    "time_ruins": {"name":"Time Ruins", "level":66, "type":"temporal", "desc":"A shattered civilization trapped across multiple moments."},
    "godfall": {"name":"Godfall", "level":70, "type":"divine", "desc":"A fallen divine domain filled with remnants of old powers."},
    "endless_night": {"name":"Endless Night", "level":75, "type":"void", "desc":"A lightless region where shadow creatures hunt by sound."},
    "reality_edge": {"name":"Reality's Edge", "level":82, "type":"endgame", "desc":"The boundary where worlds overlap and collapse."},
    "origin_sanctum": {"name":"Origin Sanctum", "level":90, "type":"endgame", "desc":"A legendary sanctum said to predate the world itself."},
    "horizon_core": {"name":"Horizon Core", "level":100, "type":"mythic", "desc":"The ultimate endgame region at the heart of Horizon."},
})

KINGDOM_ROLES = {"king": "Sovereign of the kingdom", "duke": "High noble and regional governor", "count": "Noble governing a county", "knight": "Sworn military noble", "citizen": "Recognized resident", "outlaw": "Outside the kingdom's law"}

PET_EGGS = {
    "common_egg": ("Common Egg", "Common", 150), "forest_egg": ("Forest Egg", "Uncommon", 300),
    "moon_egg": ("Moon Egg", "Rare", 600), "dragon_egg": ("Dragon Egg", "Epic", 1200),
    "phoenix_egg": ("Phoenix Egg", "Legendary", 3000), "celestial_egg": ("Celestial Egg", "Mythic", 7500),
    "void_egg": ("Void Egg", "Mythic", 9000), "royal_egg": ("Royal Egg", "Epic", 2000),
}


# Gacha uses transparent published rates and a pity counter.  It is a game
# reward system using earned in-game Gems, not real-money purchases.
GACHA_RATES = [
    ("common", 0.56), ("uncommon", 0.28), ("rare", 0.105),
    ("epic", 0.04), ("legendary", 0.014), ("mythic", 0.001),
]
GACHA_COST_SINGLE = 100
GACHA_COST_TEN = 900
GACHA_EPIC_PITY = 50
GACHA_MYTHIC_PITY = 100
GACHA_CHEST_ITEMS = {
    "chest_common": ("Common Horizon Chest", "common", 50),
    "chest_uncommon": ("Uncommon Horizon Chest", "uncommon", 100),
    "chest_rare": ("Rare Horizon Chest", "rare", 250),
    "chest_epic": ("Epic Horizon Chest", "epic", 600),
    "chest_legendary": ("Legendary Horizon Chest", "legendary", 1500),
    "chest_mythic": ("Mythic Horizon Chest", "mythic", 5000),
}

ENCHANTMENTS = {
    "sharpness": {"name":"Sharpness","desc":"Increases attack by 3% per level.","stat":"atk","pct":3,"max_level":3},
    "fortitude": {"name":"Fortitude","desc":"Increases maximum HP by 3% per level.","stat":"hp","pct":3,"max_level":3},
    "bulwark": {"name":"Bulwark","desc":"Increases defense by 3% per level.","stat":"def","pct":3,"max_level":3},
    "swiftness": {"name":"Swiftness","desc":"Increases speed by 3% per level.","stat":"speed","pct":3,"max_level":3},
    "precision": {"name":"Precision","desc":"Increases critical chance by 2% per level.","stat":"crit","pct":2,"max_level":4},
    "manaweave": {"name":"Manaweave","desc":"Increases maximum MP by 3% per level.","stat":"mp","pct":3,"max_level":3},
    "vampiric": {"name":"Vampiric","desc":"Adds a small life-steal effect to attacks.","stat":"lifesteal","pct":2,"max_level":3},
    "flamebrand": {"name":"Flamebrand","desc":"Adds a burn effect to damaging attacks.","stat":"burn","pct":2,"max_level":3},
    "frostbind": {"name":"Frostbind","desc":"Adds a chance to slow enemies.","stat":"freeze","pct":2,"max_level":3},
    "warding": {"name":"Warding","desc":"Improves resistance to incoming skill damage.","stat":"def","pct":2,"max_level":4},
    "soulbound": {"name":"Soulbound","desc":"Improves resource recovery during long fights.","stat":"mp","pct":2,"max_level":4},
    "hunter": {"name":"Hunter's Mark","desc":"Improves damage against marked targets.","stat":"atk","pct":2,"max_level":4},
}

PET_SPECIES = {
    "Wolf Pup": {"rarity": "common", "atk": 2, "def": 2, "hp": 5, "spd": 2, "crit": 1, "ability": "Howl", "role": "damage"},
    "Rabbit": {"rarity": "common", "atk": 1, "def": 1, "hp": 3, "spd": 4, "crit": 2, "ability": "Lucky Hop", "role": "crit"},
    "Fox": {"rarity": "common", "atk": 2, "def": 1, "hp": 3, "spd": 3, "crit": 3, "ability": "Foxfire", "role": "damage"},
    "Fox Spirit": {"rarity": "uncommon", "atk": 4, "def": 2, "hp": 6, "spd": 4, "crit": 4, "ability": "Spirit Flame", "role": "damage"},
    "Cat": {"rarity": "common", "atk": 1, "def": 2, "hp": 4, "spd": 3, "crit": 2, "ability": "Pounce", "role": "damage"},
    "Forest Wolf": {"rarity": "uncommon", "atk": 4, "def": 3, "hp": 8, "spd": 3, "crit": 2, "ability": "Pack Howl", "role": "damage"},
    "Moon Fox": {"rarity": "uncommon", "atk": 4, "def": 2, "hp": 6, "spd": 4, "crit": 4, "ability": "Moonfire", "role": "damage"},
    "Hawk": {"rarity": "uncommon", "atk": 3, "def": 1, "hp": 4, "spd": 7, "crit": 5, "ability": "Dive", "role": "damage"},
    "Dire Hound": {"rarity": "uncommon", "atk": 5, "def": 3, "hp": 9, "spd": 2, "crit": 1, "ability": "Savage Bite", "role": "damage"},
    "Moon Cat": {"rarity": "rare", "atk": 4, "def": 4, "hp": 10, "spd": 5, "crit": 5, "ability": "Moon Veil", "role": "heal"},
    "Spirit Fox": {"rarity": "rare", "atk": 5, "def": 3, "hp": 8, "spd": 5, "crit": 6, "ability": "Spirit Flame", "role": "damage"},
    "Griffin Chick": {"rarity": "rare", "atk": 6, "def": 4, "hp": 12, "spd": 4, "crit": 4, "ability": "Gust", "role": "damage"},
    "Frost Wolf": {"rarity": "rare", "atk": 6, "def": 5, "hp": 13, "spd": 3, "crit": 3, "ability": "Frost Bite", "role": "damage"},
    "Dragon Whelp": {"rarity": "epic", "atk": 9, "def": 6, "hp": 18, "spd": 3, "crit": 4, "ability": "Dragon Breath", "role": "damage"},
    "Phoenix Chick": {"rarity": "epic", "atk": 7, "def": 5, "hp": 15, "spd": 5, "crit": 6, "ability": "Rebirth", "role": "heal"},
    "Royal Griffin": {"rarity": "epic", "atk": 8, "def": 7, "hp": 20, "spd": 5, "crit": 5, "ability": "Royal Dive", "role": "damage"},
    "Shadow Drake": {"rarity": "epic", "atk": 10, "def": 5, "hp": 17, "spd": 6, "crit": 7, "ability": "Shadow Flame", "role": "damage"},
    "Phoenix": {"rarity": "legendary", "atk": 13, "def": 9, "hp": 28, "spd": 7, "crit": 8, "ability": "Phoenix Rebirth", "role": "heal"},
    "Elder Dragon": {"rarity": "legendary", "atk": 16, "def": 11, "hp": 35, "spd": 5, "crit": 6, "ability": "Elder Breath", "role": "damage"},
    "Celestial Lion": {"rarity": "legendary", "atk": 14, "def": 12, "hp": 38, "spd": 5, "crit": 7, "ability": "Celestial Roar", "role": "damage"},
    "Void Dragon": {"rarity": "mythic", "atk": 20, "def": 14, "hp": 50, "spd": 7, "crit": 10, "ability": "Void Breath", "role": "damage"},
    "Star Serpent": {"rarity": "mythic", "atk": 18, "def": 13, "hp": 45, "spd": 10, "crit": 12, "ability": "Starfall", "role": "damage"},
    "World Tree Sprite": {"rarity": "mythic", "atk": 12, "def": 18, "hp": 65, "spd": 4, "crit": 8, "ability": "World's Blessing", "role": "heal"},
}

PET_ABILITY_DESCRIPTIONS = {
    "Howl":"Deals a small follow-up strike and improves offensive momentum.",
    "Lucky Hop":"Raises the chance of a critical hit when the companion assists.",
    "Foxfire":"Deals magic damage and can ignite the enemy.",
    "Spirit Flame":"Deals magic damage with increased effectiveness against cursed targets.",
    "Pounce":"Deals a quick physical hit with improved crit scaling.",
    "Pack Howl":"Deals damage and briefly improves allied attack.",
    "Moonfire":"Deals lunar magic damage and restores a small amount of HP.",
    "Dive":"A fast strike with extra critical-hit scaling.",
    "Savage Bite":"Heavy physical damage that is stronger against weakened enemies.",
    "Moon Veil":"Restores HP and grants a short defensive veil.",
    "Gust":"Deals ranged damage and improves evasion for one turn.",
    "Frost Bite":"Deals cold damage and can slow the next enemy action.",
    "Dragon Breath":"Heavy elemental damage with a burn chance.",
    "Rebirth":"Restores HP and can prevent one lethal hit per battle.",
    "Royal Dive":"High-damage aerial strike with bonus crit scaling.",
    "Shadow Flame":"Dark elemental damage that ignores part of defense.",
    "Phoenix Rebirth":"Large heal with a long internal cooldown.",
    "Elder Breath":"Heavy elemental damage against a single target.",
    "Celestial Roar":"Damages the enemy and grants a temporary defensive buff.",
    "Void Breath":"Very high damage with a small life-steal effect.",
    "Starfall":"Astral damage with a chance to mark the enemy.",
    "World's Blessing":"Strong recovery plus a temporary defensive blessing.",
}
for _pet in PET_SPECIES.values():
    _pet["ability_desc"] = PET_ABILITY_DESCRIPTIONS.get(_pet.get("ability",""), "A passive companion ability that helps during battle.")


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
    # Elemental / celestial variants push the catalogue beyond 1,000 real
    # entries while keeping every generated item mechanically distinct.
    elements=[
        ("flame","Flame","burn","atk_pct"),("frost","Frost","freeze","def_pct"),
        ("storm","Storm","haste","spd_pct"),("holy","Holy","radiance","crit_pct"),
        ("void","Void","lifesteal","hp_pct"),
    ]
    rarity_level={"common":1,"uncommon":10,"rare":20,"epic":35,"legendary":55,"mythic":75}
    for mat_key, mat_name, rarity, mult in metals:
        for element_key, element_name, ability, pct_field in elements:
            for key,label,base in weapon_bases:
                k=f"{mat_key}_{element_key}_{key}"
                pct=min(10, 2 + (list(rarity_level).index(rarity) * 2) + (base % 2))
                generated[k]={"name":f"{element_name} {mat_name} {label}","slot":"weapon","rarity":rarity,
                              "atk":int(base*mult)+4,"crit":2 if key in {"rapier","dagger","katana","bow"} else 0,
                              "price":int(140*base*mult),"level_req":rarity_level[rarity],"ability":ability,
                              "pct_atk":pct if pct_field=="atk_pct" else 0,"pct_def":pct if pct_field=="def_pct" else 0,
                              "pct_hp":pct if pct_field=="hp_pct" else 0,"pct_speed":pct if pct_field=="spd_pct" else 0,
                              "pct_crit":pct if pct_field=="crit_pct" else 0,"enchant_slots":1+min(4,list(rarity_level).index(rarity))}
            for key,label,base in armor_sets:
                k=f"{mat_key}_{element_key}_{key}_armor"
                pct=min(10, 2 + list(rarity_level).index(rarity)*2)
                generated[k]={"name":f"{element_name} {mat_name} {label}","slot":"armor","rarity":rarity,
                              "def":int(base*mult)+2,"hp":int(base*mult*1.5)+5,"price":int(170*base*mult),
                              "level_req":rarity_level[rarity],"ability":ability,"pct_hp":pct if pct_field=="hp_pct" else 0,
                              "pct_def":pct if pct_field=="def_pct" else 0,"pct_speed":pct if pct_field=="spd_pct" else 0,
                              "pct_crit":pct if pct_field=="crit_pct" else 0,"enchant_slots":1+min(4,list(rarity_level).index(rarity))}
    accessory_bases=[
        ("ring","Ring",4),("amulet","Amulet",5),("belt","War Belt",6),("cloak","Mystic Cloak",5),
        ("boots","Traveler Boots",4),("gloves","Combat Gloves",5),("crown","Battle Crown",7),("earring","Arcane Earring",3),
        ("charm","Spirit Charm",4),("brooch","Royal Brooch",3),
    ]
    for mat_key, mat_name, rarity, mult in metals:
        for element_key, element_name, ability, pct_field in elements[:3]:
            for key,label,base in accessory_bases:
                k=f"{mat_key}_{element_key}_{key}"
                pct=min(10,2+list(rarity_level).index(rarity)*2+(base%2))
                generated[k]={"name":f"{element_name} {mat_name} {label}","slot":"accessory" if key not in {"ring","amulet","earring"} else key,
                              "rarity":rarity,"atk":int(base*mult/2),"def":int(base*mult/2),"hp":int(base*mult),
                              "spd":int(base*mult/3),"crit":int(base/3),"price":int(250*base*mult),
                              "level_req":rarity_level[rarity],"ability":ability,"pct_atk":pct if pct_field=="atk_pct" else 0,
                              "pct_def":pct if pct_field=="def_pct" else 0,"pct_hp":pct if pct_field=="hp_pct" else 0,
                              "pct_speed":pct if pct_field=="spd_pct" else 0,"enchant_slots":1+min(4,list(rarity_level).index(rarity))}
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
for _key, (_name, _rarity, _price) in GACHA_CHEST_ITEMS.items():
    ITEMS[_key]={"name":_name,"slot":"chest","rarity":_rarity,"price":_price,"gacha_chest":True,"level_req":rarity_level.get(_rarity,1) if "rarity_level" in globals() else 1}
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

# Distinct enemy families for every world region. Their base values scale from
# the region tier, while combat caps keep any one enemy from one-shotting a hero.
_AREA_ENEMY_FLAVOURS = {
    "town":"Bandit", "plains":"Marauder", "cave":"Cave Stalker", "forest":"Wild Spirit",
    "coast":"Sea Raider", "islands":"Pirate Beast", "swamp":"Bog Horror", "mountain":"Frost Giant",
    "cliffs":"Storm Harpy", "canyon":"Ravine Hunter", "undersea":"Abyssal Eel", "underground":"Grave Warden",
    "valley":"Mist Phantom", "sky":"Sky Seraph", "fortress":"Obsidian Knight", "volcanic":"Magma Beast",
    "hell":"Infernal Hound", "cursed":"Blood Wraith", "desert":"Crystal Scorpion", "city":"Mirage Assassin",
    "arena":"Colosseum Champion", "temple":"Thunder Priest", "void":"Void Stalker", "astral":"Astral Leviathan",
    "ruins":"Starbound Guardian", "mythic":"Worldroot Colossus", "arcane":"Living Grimoire", "graveyard":"Dragon Revenant",
    "chaos":"Chaos Spawn", "temporal":"Time Eater", "divine":"Fallen Seraph", "endgame":"Reality Hunter",
}
for _area_key,_area in AREAS.items():
    _lvl=int(_area["level"]); _flavour=_AREA_ENEMY_FLAVOURS.get(_area["type"],"Horizon Monster")
    for _variant,_suffix in enumerate(("Scout","Champion"),1):
        _hp=int(48 + _lvl*18 + _variant*20); _atk=int(7 + _lvl*2.1 + _variant*3); _def=int(2 + _lvl*1.15 + _variant*2)
        _drops=["herb","iron_ore","arcane_shard"]
        if _lvl>=10:
            _drops += [k for k,v in ITEMS.items() if v.get("slot") in {"material","egg"} and v.get("rarity") in {"rare","epic"}][:2]
        ENEMIES.append({"name":f"{_flavour} {_suffix}","level":_lvl,"hp":_hp,"atk":_atk,"def":_def,"xp":int(35+_lvl*24+_variant*18),"gold":int(20+_lvl*15+_variant*10),"drops":list(dict.fromkeys([d for d in _drops if d in ITEMS]))})

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
    active_duels: dict[tuple[int, int, int], dict[str, Any]] = field(default_factory=dict, init=False, repr=False)
    combat_locks: dict[tuple[int, int], asyncio.Lock] = field(default_factory=dict, init=False, repr=False)
    duel_locks: dict[tuple[int, int, int], asyncio.Lock] = field(default_factory=dict, init=False, repr=False)

    async def setup(self):
        async with aiosqlite.connect(self.path) as db:
            await db.executescript("""
            CREATE TABLE IF NOT EXISTS rpg_players (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                name TEXT NOT NULL DEFAULT '', race TEXT NOT NULL DEFAULT 'human', class_name TEXT NOT NULL DEFAULT 'warrior',
                level INTEGER NOT NULL DEFAULT 1, xp INTEGER NOT NULL DEFAULT 0, gold INTEGER NOT NULL DEFAULT 250, gems INTEGER NOT NULL DEFAULT 500,
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
            CREATE TABLE IF NOT EXISTS rpg_skill_loadout (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, slot INTEGER NOT NULL, skill_key TEXT NOT NULL,
                PRIMARY KEY (guild_id, user_id, slot)
            );
            CREATE TABLE IF NOT EXISTS rpg_pet_inventory (
                pet_id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                name TEXT NOT NULL, species TEXT NOT NULL, level INTEGER NOT NULL DEFAULT 1, xp INTEGER NOT NULL DEFAULT 0,
                bonus_atk INTEGER NOT NULL DEFAULT 0, bonus_def INTEGER NOT NULL DEFAULT 0, bonus_hp INTEGER NOT NULL DEFAULT 0,
                bonus_mp INTEGER NOT NULL DEFAULT 0, bonus_speed INTEGER NOT NULL DEFAULT 0, bonus_crit INTEGER NOT NULL DEFAULT 0,
                ability TEXT NOT NULL DEFAULT 'Pounce', equipped INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL DEFAULT (strftime('%s','now'))
            );
            CREATE INDEX IF NOT EXISTS idx_rpg_pet_inventory_owner ON rpg_pet_inventory(guild_id,user_id,equipped,pet_id);
            CREATE TABLE IF NOT EXISTS rpg_gacha_state (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, banner TEXT NOT NULL DEFAULT 'horizon',
                pulls INTEGER NOT NULL DEFAULT 0, pity INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id,user_id,banner)
            );
            CREATE TABLE IF NOT EXISTS rpg_equipment_enchants (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, slot TEXT NOT NULL, enchant_key TEXT NOT NULL,
                level INTEGER NOT NULL DEFAULT 1, PRIMARY KEY (guild_id,user_id,slot,enchant_key)
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
                bonus_hp INTEGER NOT NULL DEFAULT 0, bonus_mp INTEGER NOT NULL DEFAULT 0,
                bonus_speed INTEGER NOT NULL DEFAULT 0, bonus_crit INTEGER NOT NULL DEFAULT 0,
                ability TEXT NOT NULL DEFAULT 'Pounce',
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
                "gems": "INTEGER NOT NULL DEFAULT 500",
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
            # Pet migrations keep existing companions valid while adding their
            # passive stats and battle ability.
            cur = await db.execute("PRAGMA table_info(rpg_pets)")
            pet_existing = {row[1] for row in await cur.fetchall()}
            pet_migrations = {
                "bonus_hp": "INTEGER NOT NULL DEFAULT 0",
                "bonus_mp": "INTEGER NOT NULL DEFAULT 0",
                "bonus_speed": "INTEGER NOT NULL DEFAULT 0",
                "bonus_crit": "INTEGER NOT NULL DEFAULT 0",
                "ability": "TEXT NOT NULL DEFAULT 'Pounce'",
            }
            for column, definition in pet_migrations.items():
                if column not in pet_existing:
                    await db.execute(f"ALTER TABLE rpg_pets ADD COLUMN {column} {definition}")
            # Preserve an existing single-pet character while upgrading to a true
            # pet inventory. The old rpg_pets table remains as a compatibility cache.
            cur = await db.execute("SELECT guild_id,user_id,name,species,level,xp,bonus_atk,bonus_def,bonus_hp,bonus_mp,bonus_speed,bonus_crit,ability FROM rpg_pets")
            old_pets = await cur.fetchall()
            for row in old_pets:
                exists = await db.execute("SELECT 1 FROM rpg_pet_inventory WHERE guild_id=? AND user_id=? AND name=? AND species=? LIMIT 1", (row[0],row[1],row[2],row[3]))
                if not await exists.fetchone():
                    await db.execute("INSERT INTO rpg_pet_inventory(guild_id,user_id,name,species,level,xp,bonus_atk,bonus_def,bonus_hp,bonus_mp,bonus_speed,bonus_crit,ability,equipped) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1)", row)
            cur = await db.execute("SELECT guild_id,user_id,class_name FROM rpg_players")
            players = await cur.fetchall()
            for guild_id,user_id,class_name in players:
                count_cur = await db.execute("SELECT COUNT(*) FROM rpg_skill_loadout WHERE guild_id=? AND user_id=?", (guild_id,user_id))
                count = (await count_cur.fetchone())[0]
                if count == 0:
                    for slot, skill_key in enumerate(("skill_1","skill_2","skill_3","skill_4"),1):
                        await db.execute("INSERT OR IGNORE INTO rpg_skill_loadout(guild_id,user_id,slot,skill_key) VALUES(?,?,?,?)", (guild_id,user_id,slot,skill_key))
            await db.commit()

    def _level_xp(self, level: int) -> int:
        # Cumulative XP curve becomes increasingly demanding so high-level
        # progression is earned rather than rushed. Existing XP is preserved.
        level=max(1,int(level))
        return 150 * level * level + 100 * level

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
            for slot,skill_key in enumerate(("skill_1","skill_2","skill_3","skill_4"),1):
                await db.execute("INSERT OR IGNORE INTO rpg_skill_loadout(guild_id,user_id,slot,skill_key) VALUES(?,?,?,?)",(guild_id,user_id,slot,skill_key))
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

    async def pet_record(self, guild_id, user_id):
        # The new pet inventory keeps multiple companions. rpg_pets is retained
        # as a compatibility cache for older code/databases.
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM rpg_pet_inventory WHERE guild_id=? AND user_id=? AND equipped=1 ORDER BY pet_id LIMIT 1", (guild_id, user_id))
            row = await cur.fetchone()
            if row:
                return dict(row)
            cur = await db.execute("SELECT * FROM rpg_pets WHERE guild_id=? AND user_id=?", (guild_id, user_id))
            row = await cur.fetchone()
            return dict(row) if row else None

    async def pet_inventory(self, guild_id, user_id):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur=await db.execute("SELECT * FROM rpg_pet_inventory WHERE guild_id=? AND user_id=? ORDER BY equipped DESC, level DESC, pet_id", (guild_id,user_id))
            return [dict(r) for r in await cur.fetchall()]

    async def _sync_legacy_pet_cache(self, db, guild_id, user_id):
        await db.execute("DELETE FROM rpg_pets WHERE guild_id=? AND user_id=?", (guild_id,user_id))
        cur=await db.execute("SELECT name,species,level,xp,bonus_atk,bonus_def,bonus_hp,bonus_mp,bonus_speed,bonus_crit,ability FROM rpg_pet_inventory WHERE guild_id=? AND user_id=? AND equipped=1 ORDER BY pet_id LIMIT 1", (guild_id,user_id))
        row=await cur.fetchone()
        if row:
            await db.execute("INSERT INTO rpg_pets(guild_id,user_id,name,species,level,xp,bonus_atk,bonus_def,bonus_hp,bonus_mp,bonus_speed,bonus_crit,ability) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (guild_id,user_id,*row))

    async def equip_pet(self, guild_id, user_id, pet_id):
        pets=await self.pet_inventory(guild_id,user_id)
        chosen=next((p for p in pets if int(p["pet_id"])==int(pet_id)),None)
        if not chosen:return False,"That pet is not in your pet inventory."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_pet_inventory SET equipped=0 WHERE guild_id=? AND user_id=?", (guild_id,user_id))
            await db.execute("UPDATE rpg_pet_inventory SET equipped=1 WHERE guild_id=? AND user_id=? AND pet_id=?", (guild_id,user_id,int(pet_id)))
            await self._sync_legacy_pet_cache(db,guild_id,user_id)
            await db.commit()
        return True,f"Equipped **{chosen['name']}** ({chosen['species']})."

    async def unequip_pet(self, guild_id, user_id):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_pet_inventory SET equipped=0 WHERE guild_id=? AND user_id=?", (guild_id,user_id))
            await self._sync_legacy_pet_cache(db,guild_id,user_id)
            await db.commit()
        return True,"Your active pet was placed back into the pet inventory."

    async def unlocked_skills(self, guild_id, user_id):
        p=await self.player(guild_id,user_id)
        if not p:return []
        return [s for s in SKILLS.get(p["class_name"],[]) if int(s["unlock"])<=int(p["level"])]

    async def equipped_skills(self, guild_id, user_id):
        p=await self.player(guild_id,user_id)
        if not p:return []
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT slot,skill_key FROM rpg_skill_loadout WHERE guild_id=? AND user_id=? ORDER BY slot", (guild_id,user_id))
            rows=await cur.fetchall()
        available={s["key"]:s for s in SKILLS.get(p["class_name"],[]) if int(s["unlock"])<=int(p["level"])}
        return [available[key] for _,key in rows if key in available][:4]

    async def equip_skill(self, guild_id, user_id, skill_key, slot=1):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        slot=max(1,min(4,int(slot)))
        skill=self._skill(p["class_name"],skill_key.lower())
        if not skill:return False,"That skill does not belong to your current class."
        if not self._skill_available(p,skill):return False,f"**{skill['name']}** unlocks at level **{skill['unlock']}**."
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT slot FROM rpg_skill_loadout WHERE guild_id=? AND user_id=? AND skill_key=?", (guild_id,user_id,skill["key"]))
            existing=await cur.fetchone()
            if existing and int(existing[0])!=slot:
                await db.execute("DELETE FROM rpg_skill_loadout WHERE guild_id=? AND user_id=? AND slot=?", (guild_id,user_id,int(existing[0])))
            await db.execute("INSERT INTO rpg_skill_loadout(guild_id,user_id,slot,skill_key) VALUES(?,?,?,?) ON CONFLICT(guild_id,user_id,slot) DO UPDATE SET skill_key=excluded.skill_key", (guild_id,user_id,slot,skill["key"]))
            await db.commit()
        return True,f"Equipped **{skill['name']}** in skill slot **{slot}**."

    async def skill_loadout(self,guild_id,user_id):
        p=await self.player(guild_id,user_id)
        if not p:return []
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT slot,skill_key FROM rpg_skill_loadout WHERE guild_id=? AND user_id=? ORDER BY slot", (guild_id,user_id))
            rows=await cur.fetchall()
        all_skills={s["key"]:s for s in SKILLS.get(p["class_name"],[])}
        return [(slot,all_skills.get(key)) for slot,key in rows if all_skills.get(key)]

    async def _pet_bonus(self, guild_id, user_id):
        pet = await self.pet_record(guild_id, user_id)
        if not pet:
            return {"hp": 0, "mp": 0, "atk": 0, "defense": 0, "speed": 0, "crit": 0, "ability": "", "name": "", "species": ""}
        data = PET_SPECIES.get(pet["species"], {})
        return {
            "hp": int(pet.get("bonus_hp", data.get("hp", 0))),
            "mp": int(pet.get("bonus_mp", 0)),
            "atk": int(pet.get("bonus_atk", data.get("atk", 0))),
            "defense": int(pet.get("bonus_def", data.get("def", 0))),
            "speed": int(pet.get("bonus_speed", data.get("spd", 0))),
            "crit": int(pet.get("bonus_crit", data.get("crit", 0))),
            "ability": pet.get("ability") or data.get("ability", "Pounce"),
            "name": pet.get("name", "Pet"),
            "species": pet.get("species", "Companion"),
        }

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
        streak_bonus=random.randint(0,100); xp=150; gold=300+streak_bonus; gems=random.randint(80,140)
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET last_daily=?,gold=gold+?,gems=gems+? WHERE guild_id=? AND user_id=?",(time.time(),gold,gems,guild_id,user_id)); await db.commit()
        old,new=await self.add_rewards(guild_id,user_id,xp,0)
        await self.add_item(guild_id,user_id,"life_potion",1)
        return (xp,gold,gems,new),None

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
        item_key=item_key.lower().strip(); item=ITEMS.get(item_key)
        allowed={"weapon","armor","offhand","accessory","ring","amulet","relic"}
        if not item or item.get("slot") not in allowed: return False,"That item cannot be equipped. Check `!rpg items <category>`."
        inv=dict(await self.inventory(guild_id,user_id))
        if inv.get(item_key,0)<1: return False,"You don't own that item."
        req=int(item.get("level_req",1))
        if int(p["level"])<req:return False,f"**{item['name']}** requires level **{req}**. You are level **{p['level']}**."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO rpg_equipment(guild_id,user_id,slot,item_key) VALUES(?,?,?,?) ON CONFLICT(guild_id,user_id,slot) DO UPDATE SET item_key=excluded.item_key",(guild_id,user_id,item["slot"],item_key))
            await db.commit()
        return True,f"Equipped **{item['name']}** in **{item['slot']}**."

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
        enchants=[]
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT slot,item_key FROM rpg_equipment WHERE guild_id=? AND user_id=?",(guild_id,user_id)); gear=dict(await cur.fetchall())
            cur=await db.execute("SELECT slot,enchant_key,level FROM rpg_equipment_enchants WHERE guild_id=? AND user_id=?",(guild_id,user_id)); enchants=await cur.fetchall()
        bonus=self._progression_bonus(p)
        pct={"atk":0,"defense":0,"hp":0,"mp":0,"speed":0,"crit":0}
        for key in gear.values():
            item=ITEMS.get(key,{})
            bonus["atk"]+=item.get("atk",0); bonus["defense"]+=item.get("def",0); bonus["hp"]+=item.get("hp",0); bonus["mp"]+=item.get("mp",0); bonus["speed"]+=item.get("spd",0); bonus["crit"]+=item.get("crit",0)
            pct["atk"]+=min(10,int(item.get("pct_atk",0))); pct["defense"]+=min(10,int(item.get("pct_def",0))); pct["hp"]+=min(10,int(item.get("pct_hp",0))); pct["mp"]+=min(10,int(item.get("pct_mp",0))); pct["speed"]+=min(10,int(item.get("pct_speed",0))); pct["crit"]+=min(10,int(item.get("pct_crit",0)))
        for slot,enchant_key,level in enchants:
            e=ENCHANTMENTS.get(enchant_key,{})
            stat=e.get("stat"); value=int(e.get("pct",0))*int(level)
            if stat=="atk":pct["atk"]+=value
            elif stat=="def":pct["defense"]+=value
            elif stat=="hp":pct["hp"]+=value
            elif stat=="mp":pct["mp"]+=value
            elif stat=="speed":pct["speed"]+=value
            elif stat=="crit":pct["crit"]+=value
        # Percentage bonuses are capped per source at 10%, while the aggregate
        # cap remains controlled enough to avoid gear invalidating class choice.
        pct={k:min(10,v) for k,v in pct.items()}
        bonus["pct"] = pct
        pet_bonus=await self._pet_bonus(guild_id,user_id)
        bonus["atk"]+=pet_bonus["atk"]; bonus["defense"]+=pet_bonus["defense"]; bonus["hp"]+=pet_bonus["hp"]; bonus["mp"]+=pet_bonus["mp"]; bonus["speed"]+=pet_bonus["speed"]; bonus["crit"]+=pet_bonus["crit"]
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
            cur=await db.execute("SELECT COUNT(*) FROM rpg_quests WHERE guild_id=? AND expires_at>?",(guild_id,time.time())); count=(await cur.fetchone())[0]
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
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT id,level_req FROM rpg_quests WHERE guild_id=? AND id=?",(guild_id,qid)); q=await cur.fetchone()
            if not q:return False,"Quest not found."
            if p["level"]<q[1]:return False,f"You need level {q[1]}."
            cur=await db.execute("SELECT status FROM rpg_player_quests WHERE guild_id=? AND user_id=? AND quest_id=?",(guild_id,user_id,qid)); existing=await cur.fetchone()
            if existing:
                if existing[0]=="claimed":return False,"You already claimed this quest."
                if existing[0]=="active":return False,"Quest is already active."
                if existing[0]=="complete":return False,"Quest is complete. Claim your reward."
            await db.execute("INSERT INTO rpg_player_quests(guild_id,user_id,quest_id,progress,status) VALUES(?,?,?,?,?)",(guild_id,user_id,qid,0,"active")); await db.commit()
        return True,"Quest accepted."

    async def progress_quests(self,guild_id,user_id,ptype,amount=1):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """UPDATE rpg_player_quests
                   SET progress=MIN(progress+?, (SELECT target FROM rpg_quests WHERE id=quest_id)),
                       status=CASE WHEN progress+? >= (SELECT target FROM rpg_quests WHERE id=quest_id) THEN 'complete' ELSE 'active' END
                   WHERE guild_id=? AND user_id=? AND status='active'
                     AND quest_id IN (SELECT id FROM rpg_quests WHERE progress_type=?)""",
                (amount,amount,guild_id,user_id,ptype),
            )
            await db.commit()

    async def claim_quest(self,guild_id,user_id,qid):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT q.target,q.reward_xp,q.reward_gold,q.reward_item,q.reward_qty,p.progress,p.status FROM rpg_quests q JOIN rpg_player_quests p ON q.id=p.quest_id WHERE q.guild_id=? AND q.id=? AND p.user_id=?",(guild_id,qid,user_id)); row=await cur.fetchone()
            if not row:return False,"Quest not active."
            target,xp,gold,item,qty,progress,status=row
            if status not in {"active","complete"}:return False,"Quest has already been claimed."
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

    async def _add_pet_to_inventory(self, guild_id, user_id, name, species, equipped=False):
        data=PET_SPECIES.get(species,{"atk":2,"def":2,"hp":5,"spd":2,"crit":1,"ability":"Pounce"})
        async with aiosqlite.connect(self.path) as db:
            if equipped:
                await db.execute("UPDATE rpg_pet_inventory SET equipped=0 WHERE guild_id=? AND user_id=?",(guild_id,user_id))
            cur=await db.execute("INSERT INTO rpg_pet_inventory(guild_id,user_id,name,species,level,xp,bonus_atk,bonus_def,bonus_hp,bonus_mp,bonus_speed,bonus_crit,ability,equipped) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (guild_id,user_id,name[:24],species,1,0,data.get("atk",2),data.get("def",2),data.get("hp",5),0,data.get("spd",2),data.get("crit",1),data.get("ability","Pounce"),1 if equipped else 0))
            pet_id=cur.lastrowid
            if equipped:
                await self._sync_legacy_pet_cache(db,guild_id,user_id)
            await db.commit()
        return pet_id

    async def pet(self, guild_id, user_id, action="info", name="Spirit"):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        action=(action or "info").lower().strip()
        if action=="adopt":
            species=random.choice(["Wolf Pup","Fox Spirit","Moon Cat","Rabbit"])
            pet_id=await self._add_pet_to_inventory(guild_id,user_id,name or "Spirit",species,equipped=not bool(await self.pet_inventory(guild_id,user_id)))
            data=PET_SPECIES[species]
            return True,f"You adopted **{name or 'Spirit'}**, a **{species}** companion (Pet #{pet_id}).\n🐾 **Ability:** {data['ability']} — {data.get('ability_desc','A passive combat companion effect.')}\n⚔️ +{data['atk']} ATK • 🛡️ +{data['def']} DEF • ❤️ +{data['hp']} HP • 💨 +{data['spd']} SPD • 🎯 +{data['crit']}% Crit\nUse `!rpg pets` to manage your collection."
        pets=await self.pet_inventory(guild_id,user_id)
        current=next((x for x in pets if x.get("equipped")),None)
        if action=="equip":
            try: return await self.equip_pet(guild_id,user_id,int(name))
            except ValueError:return False,"Use `!rpg pet equip <pet_id>`."
        if action=="unequip": return await self.unequip_pet(guild_id,user_id)
        if action=="rename":
            if not current:return False,"You have no equipped pet. Use `!rpg pets` and equip one first."
            new_name=(name or "Spirit").strip()[:24]
            async with aiosqlite.connect(self.path) as db:
                await db.execute("UPDATE rpg_pet_inventory SET name=? WHERE guild_id=? AND user_id=? AND pet_id=?",(new_name,guild_id,user_id,current["pet_id"]))
                await self._sync_legacy_pet_cache(db,guild_id,user_id); await db.commit()
            return True,f"Your equipped pet is now called **{new_name}**."
        if action=="release":
            if not current:return False,"You have no equipped pet."
            async with aiosqlite.connect(self.path) as db:
                await db.execute("DELETE FROM rpg_pet_inventory WHERE guild_id=? AND user_id=? AND pet_id=?",(guild_id,user_id,current["pet_id"]))
                await self._sync_legacy_pet_cache(db,guild_id,user_id); await db.commit()
            return True,f"You released **{current['name']}** from your pet inventory."
        if not current:
            return False,"You have no equipped pet. Use `!rpg pets` to choose one from your collection or `!rpg adopt <name>`."
        data=PET_SPECIES.get(current["species"],{})
        return True,f"**{current['name']}** · **{current['species']}** · Pet #{current['pet_id']} · Lv {current['level']}\n⚔️ +{current['bonus_atk']} ATK • 🛡️ +{current['bonus_def']} DEF • ❤️ +{current.get('bonus_hp',0)} HP • 💨 +{current.get('bonus_speed',0)} SPD • 🎯 +{current.get('bonus_crit',0)}% Crit\n🐾 **{current.get('ability') or data.get('ability','Pounce')}** — {data.get('ability_desc','A passive combat companion effect.')}\n\nYour other pets remain safely stored in `!rpg pets`."

    async def _gacha_state(self,guild_id,user_id,banner="horizon"):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT pulls,pity FROM rpg_gacha_state WHERE guild_id=? AND user_id=? AND banner=?",(guild_id,user_id,banner))
            row=await cur.fetchone()
            if not row:
                await db.execute("INSERT INTO rpg_gacha_state(guild_id,user_id,banner,pulls,pity) VALUES(?,?,?,0,0)",(guild_id,user_id,banner)); await db.commit()
                return {"pulls":0,"pity":0}
            return {"pulls":row[0],"pity":row[1]}

    def _roll_gacha_rarity(self,pity,guarantee_rare=False):
        if pity + 1 >= GACHA_MYTHIC_PITY:
            return "mythic"
        if pity + 1 >= GACHA_EPIC_PITY:
            return random.choice(["epic","legendary","mythic"])
        if guarantee_rare:
            return random.choice(["rare","epic","legendary"])
        roll=random.random(); total=0.0
        for rarity,rate in GACHA_RATES:
            total+=rate
            if roll<=total:return rarity
        return "common"

    async def _gacha_one(self,guild_id,user_id,rarity):
        # Rare+ pulls can award companions; equipment dominates the common pool.
        pet_species=[name for name,data in PET_SPECIES.items() if data.get("rarity")==rarity]
        if rarity in {"rare","epic","legendary","mythic"} and pet_species and random.random()<0.22:
            species=random.choice(pet_species); data=PET_SPECIES[species]
            existing=await self.pet_inventory(guild_id,user_id)
            duplicate=any(p["species"]==species for p in existing)
            pet_name=f"{species} #{random.randint(100,999)}"
            await self._add_pet_to_inventory(guild_id,user_id,pet_name,species,equipped=not existing)
            if duplicate:
                refund={"rare":35,"epic":75,"legendary":150,"mythic":300}.get(rarity,25)
                async with aiosqlite.connect(self.path) as db:
                    await db.execute("UPDATE rpg_players SET gems=gems+? WHERE guild_id=? AND user_id=?",(refund,guild_id,user_id)); await db.commit()
                return {"type":"pet_duplicate","name":pet_name,"species":species,"rarity":rarity,"refund":refund}
            return {"type":"pet","name":pet_name,"species":species,"rarity":rarity,"ability":data.get("ability"),"ability_desc":data.get("ability_desc")}
        candidates=[(k,v) for k,v in ITEMS.items() if v.get("rarity")==rarity and v.get("slot") in {"weapon","armor","offhand","accessory","ring","amulet","relic","chest","consumable"}]
        if not candidates:
            candidates=[(k,v) for k,v in ITEMS.items() if v.get("slot") in {"weapon","armor","offhand","accessory","ring","amulet","relic"}]
        key,item=random.choice(candidates)
        qty=1
        await self.add_item(guild_id,user_id,key,qty)
        return {"type":"item","key":key,"name":item.get("name",key),"rarity":item.get("rarity",rarity),"slot":item.get("slot","item"),"ability":item.get("ability",""),"level_req":item.get("level_req",1)}

    async def gacha_pull(self,guild_id,user_id,count=1,banner="horizon"):
        p=await self.player(guild_id,user_id)
        if not p:return False,{"error":"Create a hero first."}
        count=max(1,min(int(count),10))
        cost=GACHA_COST_TEN if count==10 else GACHA_COST_SINGLE*count
        if int(p.get("gems",0))<cost:return False,{"error":f"You need **{cost} Gems**. You have **{p.get('gems',0)}**."}
        state=await self._gacha_state(guild_id,user_id,banner)
        rewards=[]; pity=state["pity"]; pulls=state["pulls"]
        for i in range(count):
            rarity=self._roll_gacha_rarity(pity,guarantee_rare=(count==10 and i==9))
            reward=await self._gacha_one(guild_id,user_id,rarity)
            rewards.append(reward); pulls+=1
            pity=0 if rarity in {"epic","legendary","mythic"} else pity+1
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET gems=gems-? WHERE guild_id=? AND user_id=?",(cost,guild_id,user_id))
            await db.execute("INSERT INTO rpg_gacha_state(guild_id,user_id,banner,pulls,pity) VALUES(?,?,?,?,?) ON CONFLICT(guild_id,user_id,banner) DO UPDATE SET pulls=excluded.pulls,pity=excluded.pity",(guild_id,user_id,banner,pulls,pity))
            await db.commit()
        return True,{"cost":cost,"gems_left":int(p.get("gems",0))-cost,"rewards":rewards,"pity":pity,"pulls":pulls}

    async def gacha_info(self,guild_id,user_id,banner="horizon"):
        state=await self._gacha_state(guild_id,user_id,banner)
        p=await self.player(guild_id,user_id)
        return {"gems":int(p.get("gems",0)) if p else 0,"pity":state["pity"],"pulls":state["pulls"],"rates":GACHA_RATES}

    async def open_chest(self,guild_id,user_id,item_key):
        data=ITEMS.get(item_key.lower())
        if not data or data.get("slot")!="chest":return False,"That item is not a Horizon chest."
        inv=dict(await self.inventory(guild_id,user_id))
        if inv.get(item_key.lower(),0)<1:return False,"You don't own that chest."
        await self.remove_item(guild_id,user_id,item_key,1)
        rarity=data.get("rarity","common")
        reward=await self._gacha_one(guild_id,user_id,rarity)
        return True,f"Opened **{data['name']}** → **{reward.get('name',reward.get('species','Reward'))}** ({rarity.title()})."

    async def enchantments(self):
        return list(ENCHANTMENTS.items())

    async def enchant_item(self,guild_id,user_id,slot,item_key,enchant_key):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        item=ITEMS.get(item_key.lower()); ench=ENCHANTMENTS.get(enchant_key.lower())
        if not item or not ench:return False,"Unknown item or enchantment. Use `!rpg enchantments`."
        if item.get("slot") not in {"weapon","armor","offhand","accessory","ring","amulet","relic"}:return False,"Only equipment can be enchanted."
        if int(item.get("level_req",1))>int(p["level"]):return False,f"That gear requires level **{item['level_req']}**."
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT item_key FROM rpg_equipment WHERE guild_id=? AND user_id=? AND slot=?",(guild_id,user_id,slot))
            row=await cur.fetchone()
            if not row or row[0]!=item_key.lower():return False,f"Equip **{item['name']}** in the `{slot}` slot first."
            cur=await db.execute("SELECT level FROM rpg_equipment_enchants WHERE guild_id=? AND user_id=? AND slot=? AND enchant_key=?",(guild_id,user_id,slot,enchant_key.lower()))
            row=await cur.fetchone(); level=int(row[0]) if row else 0
            if not row:
                cur=await db.execute("SELECT COUNT(*) FROM rpg_equipment_enchants WHERE guild_id=? AND user_id=? AND slot=?",(guild_id,user_id,slot))
                used=(await cur.fetchone())[0]
                if used>=int(item.get("enchant_slots",0)):
                    return False,f"**{item['name']}** has no free enchantment slots."
            max_level=int(ench.get("max_level",3))
            if level>=max_level:return False,f"**{ench['name']}** is already maxed on this gear."
            cost=750*max(1,level+1)*int(item.get("rarity","common") in {"rare","epic","legendary","mythic"} and 2 or 1)
            if p["gold"]<cost:return False,f"Enchanting costs **{cost} gold**. You have {p['gold']}."
            if row:
                await db.execute("UPDATE rpg_equipment_enchants SET level=level+1 WHERE guild_id=? AND user_id=? AND slot=? AND enchant_key=?",(guild_id,user_id,slot,enchant_key.lower()))
            else:
                await db.execute("INSERT INTO rpg_equipment_enchants(guild_id,user_id,slot,enchant_key,level) VALUES(?,?,?,?,1)",(guild_id,user_id,slot,enchant_key.lower()))
            await db.execute("UPDATE rpg_players SET gold=gold-? WHERE guild_id=? AND user_id=?",(cost,guild_id,user_id)); await db.commit()
        return True,f"Applied **{ench['name']}** Lv **{level+1}** to **{item['name']}** for **{cost} gold**."

    async def equipped_enchants(self,guild_id,user_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT slot,enchant_key,level FROM rpg_equipment_enchants WHERE guild_id=? AND user_id=? ORDER BY slot,enchant_key",(guild_id,user_id)); return await cur.fetchall()

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

    def _combat_stats(self, p, pet_bonus=None):
        data=self._progression_bonus(p)
        pet_bonus=pet_bonus or {"hp":0,"mp":0,"atk":0,"defense":0,"speed":0,"crit":0}
        return {
            "hp": p["hp"] + data["hp"] + pet_bonus.get("hp",0),
            "max_hp": p["max_hp"] + data["hp"] + pet_bonus.get("hp",0),
            "mp": p["mp"] + data["mp"] + pet_bonus.get("mp",0),
            "max_mp": p["max_mp"] + data["mp"] + pet_bonus.get("mp",0),
            "atk": p["atk"] + data["atk"] + pet_bonus.get("atk",0),
            "defense": p["defense"] + data["defense"] + pet_bonus.get("defense",0),
            "speed": p["speed"] + data["speed"] + pet_bonus.get("speed",0),
            "crit": p["crit"] + data["crit"] + pet_bonus.get("crit",0),
            "level": int(p.get("level",1)),
        }

    async def _combat_full_stats(self, guild_id, user_id, p, pet_bonus=None):
        stats=self._combat_stats(p,pet_bonus)
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT slot,item_key FROM rpg_equipment WHERE guild_id=? AND user_id=?",(guild_id,user_id)); gear=await cur.fetchall()
            cur=await db.execute("SELECT slot,enchant_key,level FROM rpg_equipment_enchants WHERE guild_id=? AND user_id=?",(guild_id,user_id)); enchants=await cur.fetchall()
        pct={"atk":0,"defense":0,"hp":0,"mp":0,"speed":0,"crit":0}
        for _slot,key in gear:
            item=ITEMS.get(key,{})
            stats["max_hp"]+=item.get("hp",0); stats["hp"]+=item.get("hp",0)
            stats["max_mp"]+=item.get("mp",0); stats["mp"]+=item.get("mp",0)
            stats["atk"]+=item.get("atk",0); stats["defense"]+=item.get("def",0); stats["speed"]+=item.get("spd",0); stats["crit"]+=item.get("crit",0)
            pct["atk"]+=min(10,int(item.get("pct_atk",0))); pct["defense"]+=min(10,int(item.get("pct_def",0))); pct["hp"]+=min(10,int(item.get("pct_hp",0))); pct["mp"]+=min(10,int(item.get("pct_mp",0))); pct["speed"]+=min(10,int(item.get("pct_speed",0))); pct["crit"]+=min(10,int(item.get("pct_crit",0)))
        for _slot,enchant_key,level in enchants:
            e=ENCHANTMENTS.get(enchant_key,{})
            stat=e.get("stat"); val=int(e.get("pct",0))*int(level)
            if stat=="atk":pct["atk"]+=val
            elif stat=="def":pct["defense"]+=val
            elif stat=="hp":pct["hp"]+=val
            elif stat=="mp":pct["mp"]+=val
            elif stat=="speed":pct["speed"]+=val
            elif stat=="crit":pct["crit"]+=val
        for stat,percent in pct.items():
            percent=min(10,percent)
            if stat=="atk":stats["atk"]+=round(stats["atk"]*percent/100)
            elif stat=="defense":stats["defense"]+=round(stats["defense"]*percent/100)
            elif stat=="hp":
                bonus=round(stats["max_hp"]*percent/100); stats["max_hp"]+=bonus; stats["hp"]+=bonus
            elif stat=="mp":
                bonus=round(stats["max_mp"]*percent/100); stats["max_mp"]+=bonus; stats["mp"]+=bonus
            elif stat=="speed":stats["speed"]+=round(stats["speed"]*percent/100)
            elif stat=="crit":stats["crit"]+=percent
        race=p.get("race","human")
        ability=RACE_ABILITIES.get(race,("Unknown",""))[0]
        stats["race_ability"]=ability
        if race=="human":
            for key in ("atk","defense","speed"): stats[key]+=max(0,round(stats[key]*.02))
        elif race=="elf": stats["crit"]+=3
        elif race=="dwarf": stats["defense"]+=max(0,round(stats["defense"]*.05))
        elif race=="orc" and p.get("hp",0)<=p.get("max_hp",1)*.5: stats["atk"]+=max(1,round(stats["atk"]*.08))
        elif race in {"kitsune","fae"}: stats["speed"]+=2
        elif race=="halfling": stats["crit"]+=2
        elif race=="dragonkin": stats["max_hp"]+=max(1,round(stats["max_hp"]*.04)); stats["hp"]+=max(1,round(stats["hp"]*.04)); stats["defense"]+=2
        elif race=="beastfolk": stats["speed"]+=3; stats["crit"]+=2
        elif race=="vampire": stats["atk"]+=3; stats["lifesteal_pct"]=.08
        elif race=="golem": stats["max_hp"]+=max(1,round(stats["max_hp"]*.06)); stats["hp"]+=max(1,round(stats["hp"]*.06)); stats["defense"]+=3; stats["speed"]=max(1,stats["speed"]-2)
        stats["crit"]=min(35,stats["crit"])
        return stats

    def _enemy_for_level(self, level, area_key="horizon_village"):
        area=AREAS.get(area_key, AREAS["horizon_village"])
        # Adventure difficulty follows the hero. A high-level hero will not
        # randomly roll a level-1 slime as a free kill; the nearest world tier
        # is selected and then scaled to the target level.
        target=max(1, int(level))
        target=max(target, min(int(area["level"]), target + 3))
        eligible=[e for e in ENEMIES if e["level"] <= target + 2]
        if not eligible: eligible=list(ENEMIES)
        nearest=min(abs(e["level"]-target) for e in eligible)
        pool=[e for e in eligible if abs(e["level"]-target) <= nearest + 3]
        enemy=random.choice(pool or eligible).copy()
        scale=max(0, target-enemy["level"])
        enemy["level"] = target
        enemy["hp"] = int(enemy["hp"] * (1.0 + 0.075 * scale) + scale * 18)
        enemy["atk"] = int(enemy["atk"] * (1.0 + 0.035 * scale) + scale * 1.4)
        enemy["def"] = int(enemy["def"] * (1.0 + 0.045 * scale) + scale * 0.8)
        enemy["xp"] = int(enemy["xp"] * (1.0 + 0.045 * scale) + scale * 10)
        enemy["gold"] = int(enemy["gold"] * (1.0 + 0.035 * scale) + scale * 7)
        # Regional enemies can drop both classic materials and themed loot.
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
        enemy["drops"]=[d for d in drops if d in ITEMS] or ["herb"]
        return enemy

    async def start_combat(self,guild_id,user_id,mode="adventure",dungeon_name=None):
        p=await self.player(guild_id,user_id)
        if not p:return {"error":"Create a hero first."}
        key=(guild_id,user_id)
        if key in self.active_combats:return {"error":"You are already in a battle. Finish it first."}
        if p["hp"]<=0:return {"error":"You are down. Use `!rpg rest` first."}
        pet_bonus=await self._pet_bonus(guild_id,user_id)
        stats=await self._combat_full_stats(guild_id,user_id,p,pet_bonus)
        pet=await self.pet_record(guild_id,user_id)
        loadout=await self.skill_loadout(guild_id,user_id)
        base={"player_hp":stats["hp"],"player_max_hp":stats["max_hp"],"player_mp":stats["mp"],"player_max_mp":stats["max_mp"],"player_stamina":p["stamina"],"class_name":p["class_name"],"turn":1,"skill_cooldowns":{},"pet_cooldown":0,"pet":pet_bonus,"combat_stats":stats,"player_level":p["level"],"equipped_skill_keys":[skill["key"] for _slot,skill in loadout if skill],"buffs":{},"enemy_debuffs":{},"enemy_dot":0,"enemy_dot_turns":0,"combo":0,"delayed_damage":0}
        if mode=="adventure":
            remaining=await self._cooldown(p,"last_adventure",20)
            if remaining>0:return {"error":f"Your next adventure is ready in **{int(remaining)+1}s**."}
            stamina_cost=8
            if p["stamina"]<stamina_cost:return {"error":f"You need **{stamina_cost} stamina** to adventure. Use `!rpg rest`."}
            enemy=self._enemy_for_level(p["level"],p.get("area_key","horizon_village"))
            async with aiosqlite.connect(self.path) as db:
                await db.execute("UPDATE rpg_players SET last_adventure=?,stamina=stamina-? WHERE guild_id=? AND user_id=?",(time.time(),stamina_cost,guild_id,user_id)); await db.commit()
            base["player_stamina"]=max(0,p["stamina"]-stamina_cost)
            state={"mode":"adventure","enemy":enemy,"enemy_hp":enemy["hp"],"floor":1,"floors":1,"name":"Adventure","log":[f"You encountered **{enemy['name']}** in {AREAS.get(p.get('area_key','horizon_village'),AREAS['horizon_village'])['name']}."],"started":time.time(),**base}
        else:
            available=[d for d in DUNGEONS if p["level"]>=d[1]]
            d=next((x for x in available if dungeon_name and x[0].lower()==dungeon_name.lower()),None) if dungeon_name else (available[-1] if available else None)
            if not d:return {"error":"No dungeon unlocked yet."}
            n,req,floors,xp,gold,desc=d
            stamina_cost=15 + max(0, floors-3)*3
            if p["stamina"]<stamina_cost:return {"error":f"You need **{stamina_cost} stamina** to enter this dungeon. Use `!rpg rest`."}
            enemy=self._enemy_for_level(p["level"]+max(0, req-p["level"])+1,"horizon_village")
            async with aiosqlite.connect(self.path) as db:
                await db.execute("UPDATE rpg_players SET stamina=stamina-? WHERE guild_id=? AND user_id=?",(stamina_cost,guild_id,user_id)); await db.commit()
            base["player_stamina"]=max(0,p["stamina"]-stamina_cost)
            state={"mode":"dungeon","enemy":enemy,"enemy_hp":enemy["hp"],"floor":1,"floors":floors,"name":n,"reward_xp":xp,"reward_gold":gold,"log":[f"**Floor 1/{floors}** — {enemy['name']} blocks your path."],"started":time.time(),**base}
        self.active_combats[key]=state
        return {"state":state,"stats":stats,"pet":pet}

    def _skill(self, class_name, skill_key):
        return next((s for s in SKILLS.get(class_name, []) if s["key"] == skill_key), None)

    def _skill_available(self, p, skill):
        return skill and int(p.get("level", 1)) >= int(skill.get("unlock", 1))

    def _damage(self, attack, defense, multiplier=1.0, variance=PLAYER_DAMAGE_VARIANCE):
        raw = max(1.0, float(attack) * float(multiplier))
        raw *= random.uniform(1.0 - variance, 1.0 + variance)
        mitigation = 100.0 / (100.0 + max(0.0, float(defense)) * DEFENSE_SCALE)
        return max(2, int(round(raw * mitigation)))

    def _crit_damage(self, damage, crit):
        if random.random() < min(CRIT_CAP, max(0, int(crit))) / 100.0:
            return max(2, int(round(damage * CRIT_DAMAGE_MULT))), True
        return damage, False

    def _equipped_skill_keys(self, p, loadout_rows):
        return {key for _slot,key in loadout_rows if key in {s["key"] for s in SKILLS.get(p["class_name"],[])}}

    def _skill_damage(self, stats, enemy, skill, state, multiplier=None, ignore_def=False):
        enemy_def=float(enemy.get("def",0))
        debuff=state.get("enemy_debuffs",{})
        enemy_def=max(0,enemy_def*(1-float(debuff.get("def_down",0))))
        mult=float(multiplier if multiplier is not None else skill.get("mult",1.0))
        if state.get("buffs",{}).get("atk_up"):
            mult*=1+float(state["buffs"]["atk_up"])
        if debuff.get("vulnerable"):
            mult*=1+float(debuff["vulnerable"])
        if debuff.get("marked"):
            mult*=1+float(debuff["marked"])
        if ignore_def:
            raw=max(2,int(stats["atk"]*mult*random.uniform(0.92,1.08)))
            return raw
        return self._damage(stats["atk"],enemy_def,mult)

    def _apply_skill_effect(self, skill, stats, state):
        """Apply one of the 50 skill mechanics. Values are intentionally bounded."""
        effect=skill.get("effect","damage"); enemy=state["enemy"]; log=[]; defending=False; start_enemy_hp=state["enemy_hp"]
        state.setdefault("buffs",{}); state.setdefault("enemy_debuffs",{})
        dmg=self._skill_damage(stats,enemy,skill,state)
        if effect=="damage":
            state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*0.28))); log.append(f"✨ **{skill['name']}** dealt **{dmg}** damage.")
        elif effect=="heavy":
            dmg=self._skill_damage(stats,enemy,skill,state,skill["mult"]*1.18); state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*0.32))); log.append(f"💥 **{skill['name']}** crushed the target for **{dmg}** damage.")
        elif effect=="bleed":
            state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*0.22))); state["enemy_dot"]+=max(3,int(stats["atk"]*0.08)); state["enemy_dot_turns"]=2; log.append(f"🩸 **{skill['name']}** dealt **{dmg}** and applied Bleed.")
        elif effect=="multi":
            hits=[]
            for _ in range(2):
                hit=self._skill_damage(stats,enemy,skill,state,skill["mult"]*0.58); hit=min(hit,max(2,int(enemy["hp"]*0.16))); state["enemy_hp"]-=hit; hits.append(hit)
            log.append(f"⚔️ **{skill['name']}** struck twice for **{sum(hits)}** total.")
        elif effect in {"heal","team_heal","recovery"}:
            ratio={"heal":0.22,"team_heal":0.30,"recovery":0.34}[effect]
            heal=max(12,int(stats["max_hp"]*ratio)); state["player_hp"]=min(stats["max_hp"],state["player_hp"]+heal)
            if effect=="recovery": state["player_mp"]=min(stats["max_mp"],state["player_mp"]+max(8,int(stats["max_mp"]*.22)))
            log.append(f"💚 **{skill['name']}** restored **{heal} HP**.")
        elif effect=="defend":
            defending=True; state["shield_turns"]=1; state["shield_pct"]=0.55; log.append(f"🛡️ **{skill['name']}** braces against the next hit.")
        elif effect=="attack_buff":
            state["buffs"]["atk_up"]=0.18; state["buffs"]["atk_turns"]=3; state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.16))); log.append(f"⚔️ **{skill['name']}** struck for **{dmg}** and raised attack for 3 turns.")
        elif effect=="def_buff":
            state["buffs"]["def_up"]=0.22; state["buffs"]["def_turns"]=3; state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.14))); log.append(f"🛡️ **{skill['name']}** raised defense for 3 turns.")
        elif effect=="lifesteal":
            state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.24))); heal=max(5,int(dmg*.28)); state["player_hp"]=min(stats["max_hp"],state["player_hp"]+heal); log.append(f"🩸 **{skill['name']}** dealt **{dmg}** and stole **{heal} HP**.")
        elif effect=="armor_break":
            state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.22))); state["enemy_debuffs"]["def_down"]=.18; state["enemy_debuffs"]["def_turns"]=3; log.append(f"🗡️ **{skill['name']}** dealt **{dmg}** and reduced defense.")
        elif effect=="mark":
            state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.18))); state["enemy_debuffs"]["marked"]=.16; state["enemy_debuffs"]["mark_turns"]=3; log.append(f"🎯 **{skill['name']}** marked the enemy; follow-up damage is increased.")
        elif effect in {"poison","burn"}:
            state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.18))); state["enemy_dot"]+=max(4,int(stats["atk"]*.07)); state["enemy_dot_turns"]=3; log.append(f"☠️ **{skill['name']}** dealt **{dmg}** and applied {effect.title()}.")
        elif effect=="freeze":
            state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.20))); state["enemy_debuffs"]["slow_turns"]=2; log.append(f"❄️ **{skill['name']}** dealt **{dmg}** and slowed the enemy.")
        elif effect=="crit":
            state["buffs"]["crit_up"]=12; state["buffs"]["crit_turns"]=2; state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.18))); log.append(f"🎯 **{skill['name']}** sharpened your critical chance.")
        elif effect in {"dodge","haste"}:
            state["buffs"]["evasion"]=0.18 if effect=="dodge" else .24; state["buffs"]["evasion_turns"]=3; state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.14))); log.append(f"💨 **{skill['name']}** increased your evasion.")
        elif effect=="mana_drain":
            state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.20))); gain=max(5,int(stats["max_mp"]*.12)); state["player_mp"]=min(stats["max_mp"],state["player_mp"]+gain); log.append(f"💧 **{skill['name']}** dealt **{dmg}** and restored **{gain} MP**.")
        elif effect=="stamina":
            state["player_stamina"]=min(100,state.get("player_stamina",0)+25); state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.15))); log.append(f"⚡ **{skill['name']}** restored stamina and struck for **{dmg}**.")
        elif effect in {"counter","reflect","barrier"}:
            state["shield_turns"]=2 if effect=="barrier" else 1; state["shield_pct"]=0.55 if effect=="counter" else .65; state["buffs"]["reflect"]=.25 if effect=="reflect" else 0; log.append(f"🛡️ **{skill['name']}** created a protective combat state.")
        elif effect=="cleanse":
            state["buffs"].pop("negative",None); state["player_hp"]=min(stats["max_hp"],state["player_hp"]+max(8,int(stats["max_hp"]*.12))); log.append(f"✨ **{skill['name']}** cleansed negative effects and restored HP.")
        elif effect=="vulnerability":
            state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.15))); state["enemy_debuffs"]["vulnerable"]=.20; state["enemy_debuffs"]["vuln_turns"]=2; log.append(f"🔻 **{skill['name']}** exposed a weakness.")
        elif effect=="silence":
            state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.16))); state["enemy_debuffs"]["silence_turns"]=2; log.append(f"🔇 **{skill['name']}** disrupted the enemy.")
        elif effect=="execute":
            ratio=1.45 if state["enemy_hp"]<=enemy["hp"]*.30 else .92; hit=self._skill_damage(stats,enemy,skill,state,skill["mult"]*ratio); state["enemy_hp"]-=min(hit,max(2,int(enemy["hp"]*.34))); log.append(f"☠️ **{skill['name']}** executed for **{hit}** damage.")
        elif effect=="true_damage":
            hit=self._skill_damage(stats,enemy,skill,state,skill["mult"],ignore_def=True); state["enemy_hp"]-=min(hit,max(2,int(enemy["hp"]*.24))); log.append(f"🌟 **{skill['name']}** pierced defenses for **{hit}** true damage.")
        elif effect=="percent_damage":
            hit=max(8,int(enemy["hp"]*.06)); state["enemy_hp"]-=hit; log.append(f"💠 **{skill['name']}** removed **{hit} HP** based on enemy vitality.")
        elif effect in {"aoe","chain","summon"}:
            mult=1.05 if effect=="aoe" else (1.0+min(.35,state.get("combo",0)*.08) if effect=="chain" else .90)
            hit=self._skill_damage(stats,enemy,skill,state,skill["mult"]*mult); state["enemy_hp"]-=min(hit,max(2,int(enemy["hp"]*.30))); state["combo"]=min(5,state.get("combo",0)+1); log.append(f"🌪️ **{skill['name']}** dealt **{hit}** damage.")
        elif effect=="pet_boost":
            state["buffs"]["pet_up"]=.25; state["pet_cooldown"]=0; hit=self._skill_damage(stats,enemy,skill,state,skill["mult"]*.8); state["enemy_hp"]-=min(hit,max(2,int(enemy["hp"]*.18))); log.append(f"🐾 **{skill['name']}** empowered your companion for the next assist.")
        elif effect=="resource":
            state["player_mp"]=min(stats["max_mp"],state["player_mp"]+max(8,int(stats["max_mp"]*.16))); state["player_stamina"]=min(100,state.get("player_stamina",0)+15); state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.12))); log.append(f"🔋 **{skill['name']}** restored resources and dealt **{dmg}**.")
        elif effect=="team_buff":
            state["buffs"]["atk_up"]=.12; state["buffs"]["def_up"]=.12; state["buffs"]["atk_turns"]=3; state["buffs"]["def_turns"]=3; state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.12))); log.append(f"📣 **{skill['name']}** rallied your combat stats.")
        elif effect=="dispel":
            state["enemy_debuffs"].pop("vulnerable",None); state["enemy_debuffs"].pop("marked",None); state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.22))); log.append(f"🧿 **{skill['name']}** disrupted the target for **{dmg}**.")
        elif effect=="terrain":
            state["enemy_debuffs"]["vulnerable"]=.12; state["enemy_debuffs"]["vuln_turns"]=3; state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.18))); log.append(f"🌍 **{skill['name']}** reshaped the battlefield.")
        elif effect=="delayed":
            state["delayed_damage"]=max(state.get("delayed_damage",0),int(dmg*1.35)); log.append(f"⏳ **{skill['name']}** planted a delayed strike of **{state['delayed_damage']}**.")
        elif effect=="random":
            choice=random.choice(["damage","heal","defend"]); clone=dict(skill); clone["effect"]=choice; clone["name"]=f"{skill['name']} ({choice.title()})"; return self._apply_skill_effect(clone,stats,state)
        elif effect=="sacrifice":
            hp_cost=max(5,int(stats["max_hp"]*.08)); state["player_hp"]=max(1,state["player_hp"]-hp_cost); hit=self._skill_damage(stats,enemy,skill,state,skill["mult"]*1.28); state["enemy_hp"]-=min(hit,max(2,int(enemy["hp"]*.34))); log.append(f"🩸 **{skill['name']}** sacrificed {hp_cost} HP for **{hit}** damage.")
        elif effect=="emergency":
            mult=1.32 if state["player_hp"]<stats["max_hp"]*.5 else .95; hit=self._skill_damage(stats,enemy,skill,state,skill["mult"]*mult); state["enemy_hp"]-=min(hit,max(2,int(enemy["hp"]*.30))); log.append(f"🔥 **{skill['name']}** dealt **{hit}** damage.")
        elif effect=="stance":
            if state["player_hp"]<stats["max_hp"]*.5:
                state["buffs"]["def_up"]=.24; state["buffs"]["def_turns"]=3; log.append(f"🛡️ **{skill['name']}** entered a defensive stance.")
            else:
                state["buffs"]["atk_up"]=.20; state["buffs"]["atk_turns"]=3; log.append(f"⚔️ **{skill['name']}** entered an offensive stance.")
        elif effect=="combo":
            state["combo"]=min(6,state.get("combo",0)+1); hit=self._skill_damage(stats,enemy,skill,state,skill["mult"]*(1+.06*state["combo"])); state["enemy_hp"]-=min(hit,max(2,int(enemy["hp"]*.30))); log.append(f"🔗 **{skill['name']}** chained for **{hit}** damage (combo {state['combo']}).")
        elif effect=="mana_burst":
            dmg=hit(skill["mult"]*1.08,.30); gain=max(3,int(stats["max_mp"]*.06)); state["player_mp"]=min(stats["max_mp"],state["player_mp"]+gain); log.append(f"💧 **{skill['name']}** released **{dmg}** damage and restored {gain} MP.")
        elif effect=="curse":
            dmg=hit(None,.18); state["enemy_debuffs"].update(vulnerable=.14,vuln_turns=3); state["enemy_dot"]+=max(3,int(stats["atk"]*.06)); state["enemy_dot_turns"]=3; log.append(f"🕯️ **{skill['name']}** cursed the target after dealing **{dmg}** damage.")
        elif effect=="focus":
            state["buffs"].update(crit_up=10,crit_turns=3); log.append(f"🎯 **{skill['name']}** focused your next attacks.")
        elif effect=="ultimate":
            hit=self._skill_damage(stats,enemy,skill,state,skill["mult"]*1.18); state["enemy_hp"]-=min(hit,max(2,int(enemy["hp"]*.38))); heal=max(4,int(stats["max_hp"]*.08)); state["player_hp"]=min(stats["max_hp"],state["player_hp"]+heal); log.append(f"🌠 **{skill['name']}** unleashed **{hit}** damage and restored **{heal} HP**.")
        elif effect=="mythic":
            hit=self._skill_damage(stats,enemy,skill,state,skill["mult"]*1.15); state["enemy_hp"]-=min(hit,max(2,int(enemy["hp"]*.38))); state["enemy_debuffs"]["vulnerable"]=.12; state["enemy_debuffs"]["vuln_turns"]=2; log.append(f"👑 **{skill['name']}** combined damage and exposure for **{hit}**.")
        elif effect=="signature":
            hit=self._skill_damage(stats,enemy,skill,state,skill["mult"]*1.2); state["enemy_hp"]-=min(hit,max(2,int(enemy["hp"]*.40))); state["buffs"]["atk_up"]=.18; state["buffs"]["atk_turns"]=2; log.append(f"✨ **{skill['name']}** unleashed your class signature for **{hit}** damage.")
        dealt=max(0,start_enemy_hp-state["enemy_hp"])
        if stats.get("lifesteal_pct") and dealt:
            heal=max(1,int(dealt*float(stats["lifesteal_pct"]))); state["player_hp"]=min(stats["max_hp"],state["player_hp"]+heal); log.append(f"🩸 Blood Hunger restored **{heal} HP**.")
        return log,defending

    async def combat_action(self,guild_id,user_id,action):
        key=(guild_id,user_id)
        lock=self.combat_locks.setdefault(key, asyncio.Lock())
        if lock.locked():
            return {"error":"Your previous combat action is still processing. Please wait a moment."}
        async with lock:
            return await self._combat_action_locked(guild_id,user_id,action)

    async def _combat_action_locked(self,guild_id,user_id,action):
        key=(guild_id,user_id); state=self.active_combats.get(key)
        if not state:return {"error":"No active battle."}
        p=await self.player(guild_id,user_id)
        if not p:return {"error":"Character not found."}
        pet_bonus=await self._pet_bonus(guild_id,user_id)
        stats=await self._combat_full_stats(guild_id,user_id,p,pet_bonus); state["combat_stats"]=stats; state["player_max_hp"]=stats["max_hp"]; state["player_max_mp"]=stats["max_mp"]
        state["player_hp"]=max(0,min(state["player_hp"],stats["max_hp"]))
        state["player_mp"]=max(0,min(state.get("player_mp",stats["mp"]),stats["max_mp"]))
        stats["crit"]=min(35,stats.get("crit",0)+int(state.get("buffs",{}).get("crit_up",0)))
        action=action.lower().strip(); log=[]; defending=False
        if action=="attack":
            dmg, crit = self._crit_damage(self._damage(stats["atk"], state["enemy"].get("def",0), 0.85), stats["crit"])
            dmg=min(dmg, max(2,int(state["enemy"].get("hp",1)*0.28)))
            state["enemy_hp"]-=dmg; log.append(f"⚔️ You hit **{state['enemy']['name']}** for **{dmg}**{' CRITICAL' if crit else ''}.")
            if stats.get("lifesteal_pct"):
                heal=max(1,int(dmg*float(stats["lifesteal_pct"]))); state["player_hp"]=min(stats["max_hp"],state["player_hp"]+heal); log.append(f"🩸 Blood Hunger restored **{heal} HP**.")
        elif action.startswith("skill:") or action=="skill":
            loadout=await self.skill_loadout(guild_id,user_id)
            equipped={skill["key"] for _slot,skill in loadout if skill}
            if action=="skill":
                skills=[skill for _slot,skill in loadout if skill and self._skill_available(p,skill)]
                return {"choose_skill":True,"skills":skills,"state":state}
            skill_key=action.split(":",1)[1].strip(); skill=self._skill(p["class_name"],skill_key)
            if not skill:return {"error":"That skill is not available to your class."}
            if skill_key not in equipped:return {"error":"That skill is not equipped. You can equip up to **4 skills** with `!rpg equip-skill <skill> <slot>`."}
            if not self._skill_available(p,skill):
                return {"error":f"**{skill['name']}** unlocks at level **{skill.get('unlock',1)}**. You are level **{p['level']}**."}
            cooldown=int(state.get("skill_cooldowns",{}).get(skill_key,0))
            if cooldown>0:return {"error":f"**{skill['name']}** is on cooldown for **{cooldown}** more turn(s)."}
            cost=skill["cost"]
            if state["player_mp"]<cost:return {"error":f"You need **{cost} MP** for **{skill['name']}**. Current MP: {state['player_mp']}."}
            state["player_mp"]-=cost
            async with aiosqlite.connect(self.path) as db:
                await db.execute("UPDATE rpg_players SET mp=max(0,mp-?) WHERE guild_id=? AND user_id=?",(cost,guild_id,user_id)); await db.commit()
            log,defending=self._apply_skill_effect(skill,stats,state)
            if skill.get("cooldown"):state.setdefault("skill_cooldowns",{})[skill_key]=skill["cooldown"]
        elif action=="pet":
            if not pet_bonus.get("name"):return {"error":"You don't have a pet. Adopt or hatch one first."}
            cd=int(state.get("pet_cooldown",0))
            if cd>0:return {"error":f"Your pet's ability is ready in **{cd}** more turn(s)."}
            if pet_bonus.get("ability") and PET_SPECIES.get(pet_bonus.get("species"),{}).get("role")=="heal":
                heal=max(8,int(stats["max_hp"]*0.18)+pet_bonus.get("hp",0)//2); state["player_hp"]=min(stats["max_hp"],state["player_hp"]+heal); log.append(f"🐾 **{pet_bonus['name']}** used **{pet_bonus['ability']}** and restored **{heal} HP**.")
            else:
                dmg=self._damage(max(2,pet_bonus.get("atk",0)*2), state["enemy"].get("def",0), 0.65); dmg=min(dmg,max(2,int(state["enemy"].get("hp",1)*0.15))); state["enemy_hp"]-=dmg; log.append(f"🐾 **{pet_bonus['name']}** used **{pet_bonus['ability']}** for **{dmg}** damage.")
            state["pet_cooldown"]=3
        elif action == "potion" or action.startswith("potion:") or action.startswith("food:"):
            inv=dict(await self.inventory(guild_id,user_id)); choices=[(k,q) for k,q in inv.items() if q>0 and ITEMS.get(k,{}).get("slot") in {"consumable","food"}]
            if not choices:return {"error":"You have no usable potion or food."}
            requested=action.split(":",1)[1].strip() if ":" in action else ""
            if requested:
                if requested not in dict(choices): return {"error":"You no longer own that item."}
                item=requested
            else:return {"choose_item":True,"items":choices,"state":state}
            data=ITEMS[item]
            if not await self.remove_item(guild_id,user_id,item,1):return {"error":"That item is no longer available."}
            heal=data.get("heal",0); mana=data.get("mana",0); await self._apply_recovery(guild_id,user_id,heal,mana)
            state["player_hp"]=min(stats["max_hp"],state["player_hp"]+heal); state["player_mp"]=min(stats["max_mp"],state["player_mp"]+mana)
            log.append(f"🧪 You used **{data['name']}** and recovered **{heal} HP**{' and '+str(mana)+' MP' if mana else ''}.")
        elif action=="defend":
            defending=True; state["shield_turns"]=1; log.append("🛡️ You brace for the next hit, reducing incoming damage.")
        elif action=="flee":
            if state["mode"]=="dungeon" and state["floor"]>1:return {"error":"You cannot flee after the first dungeon floor."}
            if random.random()<0.65:
                self.active_combats.pop(key,None); await self._save_combat_hp(guild_id,user_id,state)
                return {"finished":True,"win":False,"fled":True,"log":[*state["log"],"🏃 You escaped the battle."]}
            log.append("You failed to escape!")
        else:return {"error":"Choose Attack, Skill, Potion, Pet, Defend or Flee."}
        state["log"].extend(log)
        if state["enemy_hp"]<=0:
            if state["mode"]=="dungeon" and state["floor"]<state["floors"]:
                state["floor"]+=1; state["enemy"]=self._enemy_for_level(p["level"]+state["floor"]+1,p.get("area_key","horizon_village")); state["enemy_hp"]=state["enemy"]["hp"]
                state["player_hp"]=min(stats["max_hp"],state["player_hp"]+max(5,stats["max_hp"]//8)); state["player_mp"]=min(stats["max_mp"],state["player_mp"]+max(3,stats["max_mp"]//10))
                state["log"].append(f"🏰 **Floor {state['floor']}/{state['floors']}** — **{state['enemy']['name']}** appears. You recover HP and MP between floors.")
                await self.progress_quests(guild_id,user_id,"dungeon",1); await self._save_combat_hp(guild_id,user_id,state)
                async with aiosqlite.connect(self.path) as db: await db.execute("UPDATE rpg_players SET mp=? WHERE guild_id=? AND user_id=?",(state["player_mp"],guild_id,user_id)); await db.commit()
                return {"finished":False,"state":state,"stats":stats}
            xp=(state.get("enemy",{}).get("xp",40)+random.randint(0,25)) if state["mode"]=="adventure" else state["reward_xp"]+state["floors"]*55
            gold=(state.get("enemy",{}).get("gold",30)+random.randint(0,35)) if state["mode"]=="adventure" else state["reward_gold"]+random.randint(0,120)
            drop=random.choice(state["enemy"].get("drops",["herb"]))
            if random.random()<0.08:
                egg_pool=[k for k,v in ITEMS.items() if v.get("slot")=="egg" and (v.get("rarity") in {"common","uncommon","rare"} or p["level"]>=20)]
                if egg_pool: drop=random.choice(egg_pool)
            await self._save_combat_hp(guild_id,user_id,state); old_level,new_level=await self.add_rewards(guild_id,user_id,xp,gold); await self.add_item(guild_id,user_id,drop,1)
            await self.progress_quests(guild_id,user_id,"hunt",1)
            if state["mode"]=="dungeon":
                await self.progress_quests(guild_id,user_id,"dungeon",1)
                if state["floors"]>=5:await self.add_item(guild_id,user_id,"dragon_trophy",1)
            await self.check_achievements(guild_id,user_id); self.active_combats.pop(key,None)
            return {"finished":True,"win":True,"xp":xp,"gold":gold,"drop":drop,"state":state,"level_before":old_level,"level_after":new_level}
        # Enemy turn. Defensive/slow/evasion effects are bounded so no skill can
        # create a permanent lock or make damage disappear.
        dot=int(state.get("enemy_dot",0))
        if dot and state.get("enemy_dot_turns",0)>0:
            state["enemy_hp"]=max(1,state["enemy_hp"]-dot); state["enemy_dot_turns"]-=1; state["log"].append(f"☠️ Damage-over-time effects dealt **{dot}**.")
        if state.get("delayed_damage",0)>0:
            delayed=state["delayed_damage"]; state["enemy_hp"]=max(1,state["enemy_hp"]-min(delayed,max(2,int(state["enemy"]["hp"]*.35)))); state["delayed_damage"]=0; state["log"].append(f"⏳ The delayed strike detonated for **{delayed}** damage.")
        if not defending and random.random()<min(.30,stats["speed"]/220 + float(state.get("buffs",{}).get("evasion",0))):
            state["log"].append(f"💨 You dodged **{state['enemy']['name']}**.")
        else:
            def_up=float(state.get("buffs",{}).get("def_up",0)); effective_def=stats["defense"]*(1+def_up)
            dmg=self._damage(state["enemy"]["atk"], effective_def, 0.90, ENEMY_DAMAGE_VARIANCE)
            dmg=min(dmg, max(2, int(stats["max_hp"]*MAX_NORMAL_DAMAGE_FRACTION)))
            shield=state.get("shield_pct",.5) if (defending or state.get("shield_turns",0)>0) else 0
            if shield:dmg=max(1,int(dmg*(1-shield)))
            state["player_hp"]-=dmg; state["log"].append(f"🩸 **{state['enemy']['name']}** hit you for **{dmg}**.")
            if state.get("buffs",{}).get("reflect"):
                reflected=max(1,int(dmg*state["buffs"]["reflect"])); state["enemy_hp"]=max(1,state["enemy_hp"]-reflected); state["log"].append(f"↩️ Your barrier reflected **{reflected}** damage.")
        for buff_key in ("atk_turns","def_turns","crit_turns","evasion_turns"):
            if buff_key in state.get("buffs",{}):
                state["buffs"][buff_key]-=1
                if state["buffs"][buff_key]<=0:
                    base=buff_key.replace("_turns",""); state["buffs"].pop(base,None); state["buffs"].pop(buff_key,None)
        for debuff_key in ("def_turns","mark_turns","vuln_turns","slow_turns","silence_turns"):
            if debuff_key in state.get("enemy_debuffs",{}):
                state["enemy_debuffs"][debuff_key]-=1
                if state["enemy_debuffs"][debuff_key]<=0:
                    base=debuff_key.replace("_turns",""); state["enemy_debuffs"].pop(base,None); state["enemy_debuffs"].pop(debuff_key,None)
        for key2 in list(state.get("skill_cooldowns",{})):
            state["skill_cooldowns"][key2]=max(0,state["skill_cooldowns"][key2]-1)
        state["pet_cooldown"]=max(0,state.get("pet_cooldown",0)-1)
        mp_regen=max(MIN_MP_REGEN, int(stats["max_mp"]*MP_REGEN_FRACTION))
        old_mp=state["player_mp"]
        state["player_mp"]=min(stats["max_mp"], state["player_mp"]+mp_regen)
        if state["player_mp"]>old_mp:
            state["log"].append(f"💧 You recovered **{state['player_mp']-old_mp} MP**.")
        state["shield_turns"]=max(0,int(state.get("shield_turns",0))-1)
        state["turn"]+=1
        if state["player_hp"]<=0:
            state["player_hp"]=1; await self._set_hp(guild_id,user_id,1); self.active_combats.pop(key,None)
            return {"finished":True,"win":False,"state":state,"defeated":True}
        await self._save_combat_hp(guild_id,user_id,state)
        async with aiosqlite.connect(self.path) as db: await db.execute("UPDATE rpg_players SET mp=? WHERE guild_id=? AND user_id=?",(state["player_mp"],guild_id,user_id)); await db.commit()
        return {"finished":False,"state":state,"stats":stats}

    async def _save_combat_hp(self,guild_id,user_id,state):
        p=await self.player(guild_id,user_id)
        if not p:return
        bonus_hp=int(state.get("player_max_hp",p["max_hp"]))-int(p["max_hp"])
        stored=max(1,min(int(p["max_hp"]),int(state.get("player_hp",1))-bonus_hp))
        await self._set_hp(guild_id,user_id,stored)

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
        egg_key=egg_key.lower().strip(); data=ITEMS.get(egg_key)
        if not data or data.get("slot")!="egg":return False,"That isn't a pet egg. Use `!rpg eggs` to see your eggs."
        species_by={"common":["Wolf Pup","Rabbit","Fox","Cat"],"uncommon":["Forest Wolf","Moon Fox","Hawk","Dire Hound"],"rare":["Moon Cat","Spirit Fox","Griffin Chick","Frost Wolf"],"epic":["Dragon Whelp","Phoenix Chick","Royal Griffin","Shadow Drake"],"legendary":["Phoenix","Elder Dragon","Celestial Lion"],"mythic":["Void Dragon","Star Serpent","World Tree Sprite"]}
        rarity=data.get("rarity","common").lower(); species=random.choice(species_by.get(rarity,species_by["common"]))
        pet_data=PET_SPECIES.get(species,{"atk":2,"def":2,"hp":5,"spd":2,"crit":1,"ability":"Pounce"})
        pet_name=(name or "Spirit").strip()[:24] or "Spirit"
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT quantity FROM rpg_inventory WHERE guild_id=? AND user_id=? AND item_key=?",(guild_id,user_id,egg_key)); owned=await cur.fetchone()
            if not owned or owned[0]<1:return False,f"You don't own **{data['name']}**. Use `!rpg eggs` to see the eggs you own."
            await db.execute("UPDATE rpg_inventory SET quantity=quantity-1 WHERE guild_id=? AND user_id=? AND item_key=?",(guild_id,user_id,egg_key))
            cur=await db.execute("SELECT COUNT(*) FROM rpg_pet_inventory WHERE guild_id=? AND user_id=?",(guild_id,user_id)); has_pets=(await cur.fetchone())[0]>0
            if not has_pets:
                await db.execute("INSERT INTO rpg_pet_inventory(guild_id,user_id,name,species,level,xp,bonus_atk,bonus_def,bonus_hp,bonus_mp,bonus_speed,bonus_crit,ability,equipped) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
                    (guild_id,user_id,pet_name,species,1,0,pet_data["atk"],pet_data["def"],pet_data["hp"],0,pet_data["spd"],pet_data["crit"],pet_data["ability"]))
            else:
                await db.execute("INSERT INTO rpg_pet_inventory(guild_id,user_id,name,species,level,xp,bonus_atk,bonus_def,bonus_hp,bonus_mp,bonus_speed,bonus_crit,ability,equipped) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,0)",
                    (guild_id,user_id,pet_name,species,1,0,pet_data["atk"],pet_data["def"],pet_data["hp"],0,pet_data["spd"],pet_data["crit"],pet_data["ability"]))
            await self._sync_legacy_pet_cache(db,guild_id,user_id); await db.commit()
        return True,f"🥚 **{data['name']}** hatched! You got **{pet_name}**, a **{species}**.\n🐾 **Ability:** {pet_data['ability']} — {pet_data.get('ability_desc','A passive combat companion effect.')}\n⚔️ +{pet_data['atk']} ATK • 🛡️ +{pet_data['def']} DEF • ❤️ +{pet_data['hp']} HP • 💨 +{pet_data['spd']} SPD • 🎯 +{pet_data['crit']}% Crit\nUse `!rpg pets` to equip it whenever you want."

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

    async def start_duel(self,guild_id,user_id,target_id):
        a=await self.player(guild_id,user_id); b=await self.player(guild_id,target_id)
        if not a or not b:return {"error":"Both players need RPG characters."}
        if user_id==target_id:return {"error":"You can't duel yourself."}
        key=(guild_id,min(user_id,target_id),max(user_id,target_id))
        if key in self.active_duels:return {"error":"A duel between these players is already active."}
        if a["hp"]<=0 or b["hp"]<=0:return {"error":"Both heroes must be standing to duel. Use `!rpg rest` first."}
        players={}
        for uid,p in ((user_id,a),(target_id,b)):
            pet=await self._pet_bonus(guild_id,uid); stats=await self._combat_full_stats(guild_id,uid,p,pet); loadout=await self.skill_loadout(guild_id,uid)
            players[uid]={"name":p["name"],"level":p["level"],"race":p["race"],"subrace":p.get("subrace") or "", "class":p["class_name"],"subclass":p.get("subclass") or "", "evolution":p.get("evolution") or "", "hp":stats["hp"],"max_hp":stats["max_hp"],"mp":stats["mp"],"max_mp":stats["max_mp"],"stats":stats,"pet":pet,"skill_cooldowns":{},"pet_cooldown":0,"defending":False,"equipped_skill_keys":[skill["key"] for _slot,skill in loadout if skill]}
        first=user_id if players[user_id]["stats"]["speed"]>=players[target_id]["stats"]["speed"] else target_id
        state={"guild_id":guild_id,"players":players,"turn":first,"round":1,"log":[f"⚔️ <@{first}> has the initiative."],"started":time.time()}
        self.active_duels[key]=state
        return {"state":state,"key":key}

    async def duel_action(self,guild_id,user_id,target_id,action):
        key=(guild_id,min(user_id,target_id),max(user_id,target_id))
        lock=self.duel_locks.setdefault(key, asyncio.Lock())
        if lock.locked():
            return {"error":"That duel action is still processing. Please wait a moment."}
        async with lock:
            return await self._duel_action_locked(guild_id,user_id,target_id,action)

    async def _duel_action_locked(self,guild_id,user_id,target_id,action):
        key=(guild_id,min(user_id,target_id),max(user_id,target_id)); state=self.active_duels.get(key)
        if not state:return {"error":"This duel is no longer active."}
        if state["turn"]!=user_id:return {"error":"It is not your turn."}
        me=state["players"][user_id]; foe_id=target_id; foe=state["players"][foe_id]
        action=action.lower().strip(); log=[]
        if action=="attack":
            matchup=matchup_multiplier(me["race"],me["class"],foe["race"],foe["class"])
            dmg, crit = self._crit_damage(self._damage(me["stats"]["atk"], foe["stats"]["defense"], 0.85*matchup), me["stats"]["crit"])
            dmg=min(dmg,max(2,int(foe["max_hp"]*0.25)))
            if foe.get("defending"): dmg=max(1,dmg//2); foe["defending"]=False; log.append(f"🛡️ **{foe['name']}** blocked part of the hit.")
            foe["hp"]-=dmg; log.append(f"⚔️ **{me['name']}** hit **{foe['name']}** for **{dmg}**{' CRITICAL' if crit else ''}.")
        elif action.startswith("skill:"):
            skill_key=action.split(":",1)[1].strip(); skill=self._skill(me["class"],skill_key)
            if skill_key not in set(me.get("equipped_skill_keys",[])):
                return {"error":"That skill is not in your active 4-skill loadout."}
            if not skill:return {"error":"That skill is not available."}
            if not self._skill_available({"level":me["level"]},skill):return {"error":f"**{skill['name']}** unlocks at level **{skill.get('unlock',1)}**."}
            cd=int(me["skill_cooldowns"].get(skill["key"],0))
            if cd:return {"error":f"**{skill['name']}** is on cooldown for {cd} turn(s)."}
            if me["mp"]<skill["cost"]:return {"error":f"You need {skill['cost']} MP."}
            me["mp"]-=skill["cost"]
            matchup=matchup_multiplier(me["race"],me["class"],foe["race"],foe["class"])
            effect=skill.get("effect","damage")
            if effect in {"heal","team_heal","recovery"}:
                heal=max(10,int(me["max_hp"]*(.22 if effect=="heal" else .30))); me["hp"]=min(me["max_hp"],me["hp"]+heal); log.append(f"💚 **{me['name']}** used **{skill['name']}** and restored {heal} HP.")
            elif effect in {"defend","counter","barrier","reflect","def_buff"}:
                me["defending"]=True; me["shield_pct"]=.55 if effect!="barrier" else .65; log.append(f"🛡️ **{me['name']}** entered **{skill['name']}** defensive state.")
            else:
                if effect=="percent_damage": dmg=max(8,int(foe["max_hp"]*.06))
                elif effect=="true_damage": dmg=max(2,int(me["stats"]["atk"]*skill["mult"]*matchup))
                else:
                    mult=skill["mult"]
                    if effect in {"heavy","ultimate","execute","mythic","signature"}: mult*=1.15
                    if effect=="lifesteal": mult*=1.05
                    dmg=self._damage(me["stats"]["atk"],foe["stats"]["defense"],mult*matchup)
                    dmg=min(dmg,max(2,int(foe["max_hp"]*(.34 if effect in {"ultimate","mythic","signature"} else .25))))
                if foe.get("defending"): dmg=max(1,int(dmg*(1-foe.get("shield_pct",.5)))); foe["defending"]=False; log.append(f"🛡️ **{foe['name']}** blocked part of the skill.")
                foe["hp"]-=dmg; log.append(f"✨ **{me['name']}** used **{skill['name']}** for **{dmg}** damage.")
                if effect=="lifesteal": me["hp"]=min(me["max_hp"],me["hp"]+max(4,int(dmg*.25)))
                if effect in {"attack_buff","team_buff"}: me["stats"]["atk"]+=max(1,int(me["stats"]["atk"]*.12))
            if skill.get("cooldown"):me["skill_cooldowns"][skill["key"]]=skill["cooldown"]
        elif action=="pet":
            if not me["pet"].get("name"):return {"error":"You don't have a pet."}
            if me["pet_cooldown"]>0:return {"error":f"Pet ability ready in {me['pet_cooldown']} turn(s)."}
            role=PET_SPECIES.get(me["pet"].get("species"),{}).get("role","damage")
            if role=="heal":
                heal=max(8,int(me["max_hp"]*.18)); me["hp"]=min(me["max_hp"],me["hp"]+heal); log.append(f"🐾 **{me['pet']['name']}** healed **{me['name']}** for {heal} HP.")
            else:
                dmg=self._damage(max(2,me["pet"].get("atk",0)*2), foe["stats"]["defense"], 0.65)
                dmg=min(dmg,max(2,int(foe["max_hp"]*0.12)))
                if foe.get("defending"): dmg=max(1,dmg//2); foe["defending"]=False; log.append(f"🛡️ **{foe['name']}** blocked part of the pet attack.")
                foe["hp"]-=dmg; log.append(f"🐾 **{me['pet']['name']}** dealt {dmg} damage with **{me['pet'].get('ability','Pet Assist')}**.")
            me["pet_cooldown"]=3
        elif action=="defend":
            me["defending"]=True; log.append(f"🛡️ **{me['name']}** is defending.")
        elif action=="surrender":
            foe["hp"]=max(1,foe["hp"]); return await self._finish_duel(guild_id,key,foe_id,user_id,log+[f"🏳️ **{me['name']}** surrendered."])
        else:return {"error":"Choose Attack, Skills, Pet, Defend or Surrender."}
        state["log"].extend(log)
        if foe["hp"]<=0:return await self._finish_duel(guild_id,key,user_id,foe_id,[])
        for sk in list(me["skill_cooldowns"]):me["skill_cooldowns"][sk]=max(0,me["skill_cooldowns"][sk]-1)
        me["pet_cooldown"]=max(0,me["pet_cooldown"]-1)
        me["mp"]=min(me["max_mp"], me["mp"]+max(MIN_MP_REGEN,int(me["max_mp"]*MP_REGEN_FRACTION)))
        me["defending"]=False
        state["turn"]=foe_id; state["round"]+=1
        return {"finished":False,"state":state}

    async def _finish_duel(self,guild_id,key,winner_id,loser_id,extra_log):
        state=self.active_duels.pop(key,None)
        if not state:return {"error":"Duel already finished."}
        state["log"].extend(extra_log)
        winner=state["players"][winner_id]; loser=state["players"][loser_id]
        await self.add_rewards(guild_id,winner_id,80,120)
        # PvP doesn't delete a character's progress; it simply leaves the loser at 1 HP.
        persisted={}
        for uid,data in state["players"].items():
            p=await self.player(guild_id,uid)
            if p:
                effective_bonus=data["max_hp"]-p["max_hp"]
                persisted[uid]=(max(1,min(p["max_hp"],int(data["hp"]-effective_bonus))),max(0,min(p["max_mp"],int(data["mp"]))))
        async with aiosqlite.connect(self.path) as db:
            for uid,(stored_hp,stored_mp) in persisted.items():
                await db.execute("UPDATE rpg_players SET hp=?,mp=? WHERE guild_id=? AND user_id=?",(stored_hp,stored_mp,guild_id,uid))
            await db.commit()
        state["turn"]=None; state["winner"]=winner_id; state["loser"]=loser_id
        return {"finished":True,"state":state,"winner":winner_id,"loser":loser_id}
