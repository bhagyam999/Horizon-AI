from __future__ import annotations

import asyncio
import json
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import aiosqlite
import discord


# ---------------------------------------------------------------------------
# Horizon RPG unified rotation clock — one shared reset time: 17:30 IST.
# Shop: every 4 hours. Daily: every day. Weekly: every Monday. Monthly: day 1.
# ---------------------------------------------------------------------------
HORIZON_RESET_TZ = ZoneInfo("Asia/Kolkata")
HORIZON_RESET_HOUR = 17
HORIZON_RESET_MINUTE = 30

def _rotation_anchor(dt):
    local = dt.astimezone(HORIZON_RESET_TZ)
    anchor = local.replace(hour=HORIZON_RESET_HOUR, minute=HORIZON_RESET_MINUTE, second=0, microsecond=0)
    if local < anchor:
        anchor -= timedelta(days=1)
    return anchor

def rotation_key(period, now=None):
    now = datetime.now(timezone.utc) if now is None else now
    local = now.astimezone(HORIZON_RESET_TZ)
    base = _rotation_anchor(now)
    period = str(period).lower()
    if period == "shop":
        slot = int((local - base).total_seconds() // 14400)
        return f"{base:%Y-%m-%d}-s{slot}"
    if period == "daily":
        return base.strftime("%Y-%m-%d")
    if period == "weekly":
        iso = base.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    if period == "monthly":
        return base.strftime("%Y-%m")
    return base.strftime("%Y-%m-%d-%H:%M")

def rotation_info(period, now=None):
    now = datetime.now(timezone.utc) if now is None else now
    local = now.astimezone(HORIZON_RESET_TZ)
    base = _rotation_anchor(now)
    period = str(period).lower()
    if period == "shop":
        elapsed = int((local - base).total_seconds() // 14400)
        nxt = base + timedelta(hours=4 * (elapsed + 1))
    elif period == "daily":
        nxt = base + timedelta(days=1)
    elif period == "weekly":
        week_start = base - timedelta(days=base.weekday())
        nxt = week_start + timedelta(days=7)
    elif period == "monthly":
        # The monthly boundary is the first day of the month at 17:30 IST.
        current_month_start = base.replace(day=1)
        if base.day == 1 and local < current_month_start:
            nxt = current_month_start
        else:
            year = base.year + (1 if base.month == 12 else 0)
            month = 1 if base.month == 12 else base.month + 1
            nxt = base.replace(year=year, month=month, day=1)
    else:
        nxt = base + timedelta(days=1)
    return rotation_key(period, now), nxt.astimezone(timezone.utc)

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
    "human": {"vampire": 1.14, "golem": 0.92},
    "elf": {"orc": 1.14, "golem": 0.90},
    "dwarf": {"golem": 1.16, "dragonkin": 0.92},
    "orc": {"dwarf": 1.14, "elf": 0.90},
    "kitsune": {"golem": 0.90, "vampire": 1.12},
    "fae": {"golem": 0.90, "orc": 1.14},
    "vampire": {"fae": 1.14, "human": 0.88},
    "golem": {"orc": 1.14, "elf": 1.14},
    "dragonkin": {"golem": 1.10, "dwarf": 1.08},
}
RACE_ABILITIES = {
    "human": ("Adaptability", "Gain a small balanced bonus to core combat stats; no major weakness, but no extreme specialty."),
    "elf": ("Keen Sight", "Critical-focused attacks gain extra precision; elves trade durability for speed."),
    "dwarf": ("Stonebody", "Defense is reinforced, making damage easier to absorb; speed remains the trade-off."),
    "orc": ("Bloodrage", "Attack rises when below half HP, rewarding dangerous low-health play."),
    "kitsune": ("Trickster Step", "Improves speed and evasion, but the race has low durability."),
    "halfling": ("Lucky", "Higher critical chance and lucky outcomes."),
    "tiefling": ("Infernal Blood", "Attack is stronger against holy builds, but holy counters it slightly."),
    "dragonkin": ("Dragonhide", "Extra defense and HP resilience."),
    "beastfolk": ("Predator Instinct", "Speed and critical chance are improved."),
    "fae": ("Feystep", "Improved evasion and magic mobility."),
    "vampire": ("Blood Hunger", "Restores roughly 28% of damage dealt, with a minimum 4 HP and a cap of 8% max HP per hit; holy opponents counter the sustain."),
    "golem": ("Stoneform", "Massively reinforces HP and defense, but its low speed makes it easy to outmaneuver."),
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
    return max(.82,min(1.18,value))

# Clear identity cards. These are intentionally visible in class/race menus so
# players can understand the trade-offs before choosing a build.
RACE_PROFILES = {
    "human": {"strength":"Adaptable all-rounder","weakness":"No specialized peak; relies on good build choices"},
    "elf": {"strength":"Speed, precision and critical hits","weakness":"Lower durability; struggles in prolonged trades"},
    "dwarf": {"strength":"Defense, HP and sustained frontline play","weakness":"Low speed; poor at chasing evasive targets"},
    "orc": {"strength":"High physical damage, especially while wounded","weakness":"Lower defense and mobility"},
    "kitsune": {"strength":"Speed, evasion and burst magic","weakness":"Fragile against heavy hits"},
    "halfling": {"strength":"Luck, crits and evasive play","weakness":"Low HP makes mistakes costly"},
    "tiefling": {"strength":"Aggressive damage and spell pressure","weakness":"Lower defense; vulnerable to holy pressure"},
    "dragonkin": {"strength":"High HP, defense and reliable damage","weakness":"Slow and less explosive"},
    "beastfolk": {"strength":"Speed, crits and sustained pursuit","weakness":"Moderate defenses; dislikes burst damage"},
    "fae": {"strength":"Extreme mobility and magical pressure","weakness":"Very low HP and poor direct durability"},
    "vampire": {"strength":"Sustain through damage and strong offensive stats","weakness":"Holy opponents counter its sustain; weak if it cannot attack"},
    "golem": {"strength":"Exceptional HP and defense","weakness":"Very slow and poor at evasion/initiative"},
}

CLASS_PROFILES = {
    "warrior":{"strength":"Balanced frontline: damage + defense","weakness":"Lacks extreme ranged pressure or burst"},
    "berserker":{"strength":"Highest sustained physical pressure when wounded","weakness":"Low defense and resource efficiency"},
    "knight":{"strength":"Defense, guarding and safe attrition","weakness":"Slow and lower burst damage"},
    "mage":{"strength":"Elemental control, range and resource-heavy burst","weakness":"Fragile when pressured"},
    "rogue":{"strength":"Speed, poison, evasion and flexible burst","weakness":"Low defense; mistakes are punished"},
    "ranger":{"strength":"Reliable ranged damage, marks and control","weakness":"Less effective when pinned down"},
    "paladin":{"strength":"Defense, healing and holy pressure","weakness":"Slow and resource-dependent"},
    "summoner":{"strength":"Pet synergy, sustained pressure and utility","weakness":"Lower direct burst without setup"},
    "cleric":{"strength":"Healing, cleansing and defensive support","weakness":"Low direct physical damage"},
    "druid":{"strength":"Flexible sustain, terrain and damage-over-time","weakness":"Needs time to build pressure"},
    "monk":{"strength":"Combo chains, counters and mobility","weakness":"Requires timing; weaker when resource-starved"},
    "bard":{"strength":"Team buffs, healing and disruption","weakness":"Lower solo burst"},
    "necromancer":{"strength":"Sustain, curses and summon pressure","weakness":"Fragile and vulnerable to holy pressure"},
    "warlock":{"strength":"High-risk damage, curses and self-sustain","weakness":"Pays HP/resources for power"},
    "alchemist":{"strength":"Flexible consumables, debuffs and recovery","weakness":"Lower raw stats and setup dependency"},
    "engineer":{"strength":"Turrets, repair and controlled ranged pressure","weakness":"Needs setup and positioning"},
    "duelist":{"strength":"Single-target timing, counters and tempo","weakness":"Less effective against multiple threats"},
    "lancer":{"strength":"Mobile reach, gap-closing and finishing power","weakness":"More predictable than rogue-style classes"},
    "spellblade":{"strength":"Hybrid physical/magic pressure and anti-defense tools","weakness":"Jack-of-all-trades; less specialized than pure classes"},
    "void_knight":{"strength":"Defensive anti-magic melee","weakness":"Slow and resource hungry"},
    "chronomancer":{"strength":"Tempo, delayed damage and control","weakness":"Low durability"},
    "dragon_lord":{"strength":"Massive burst and dragon durability","weakness":"Slow and expensive skills"},
    "soul_reaper":{"strength":"Single-target execution and life drain","weakness":"Weak sustained defense and holy counters"},
}

# Class kits use different mechanics, not just different names. Every class
# keeps 20 slots for save compatibility, while the first 12 are deliberately
# class-defining and unlock by level.
CLASS_SKILL_EXTRA_POOL = ["focus","cleanse","reflect","stamina","resource","dispel","terrain","pet_boost","summon","chain","aoe","team_buff","sacrifice","emergency","stance","mana_burst","curse","silence","delayed","mark","vulnerability","true_damage","execute","lifesteal","armor_break","counter","barrier","dodge","freeze","burn","poison","bleed","multi","heavy","heal","def_buff","attack_buff","mana_drain","percent_damage","signature","mythic","ultimate"]

CLASS_SKILL_EFFECTS = {
    "warrior":["damage","heavy","def_buff","armor_break","counter","barrier","attack_buff","multi","vulnerability","execute","true_damage","ultimate"],
    "berserker":["heavy","bleed","sacrifice","attack_buff","emergency","lifesteal","multi","attack_buff","combo","execute","true_damage","ultimate"],
    "knight":["def_buff","heavy","barrier","counter","defend","armor_break","team_buff","heal","vulnerability","true_damage","execute","ultimate"],
    "mage":["burn","freeze","mana_drain","aoe","delayed","silence","vulnerability","true_damage","mana_burst","curse","execute","ultimate"],
    "rogue":["multi","poison","dodge","bleed","mark","combo","armor_break","counter","lifesteal","execute","true_damage","ultimate"],
    "assassin":["lifesteal","poison","dodge","bleed","mark","execute","true_damage","vulnerability","combo","silence","armor_break","ultimate"],
    "ranger":["damage","multi","mark","armor_break","poison","burn","freeze","dodge","delayed","true_damage","execute","ultimate"],
    "paladin":["damage","def_buff","heal","attack_buff","lifesteal","counter","burn","barrier","vulnerability","team_buff","execute","ultimate"],
    "summoner":["summon","pet_boost","chain","team_buff","barrier","heal","mana_drain","vulnerability","aoe","execute","true_damage","ultimate"],
    "cleric":["heal","team_buff","def_buff","dispel","silence","barrier","vulnerability","mana_drain","recovery","true_damage","execute","ultimate"],
    "druid":["poison","heal","terrain","freeze","lifesteal","def_buff","aoe","delayed","vulnerability","execute","true_damage","ultimate"],
    "monk":["combo","multi","counter","dodge","attack_buff","def_buff","lifesteal","armor_break","stamina","execute","true_damage","ultimate"],
    "bard":["team_buff","heal","vulnerability","silence","dodge","attack_buff","def_buff","mana_drain","dispel","combo","true_damage","ultimate"],
    "necromancer":["lifesteal","summon","curse","poison","sacrifice","barrier","mana_drain","delayed","vulnerability","execute","true_damage","ultimate"],
    "warlock":["curse","lifesteal","sacrifice","poison","silence","mana_drain","vulnerability","delayed","emergency","execute","true_damage","ultimate"],
    "alchemist":["poison","burn","heal","armor_break","random","resource","dodge","vulnerability","dispel","execute","true_damage","ultimate"],
    "engineer":["summon","pet_boost","barrier","armor_break","mark","delayed","resource","def_buff","aoe","execute","true_damage","ultimate"],
    "duelist":["counter","multi","dodge","mark","attack_buff","armor_break","combo","def_buff","true_damage","execute","vulnerability","ultimate"],
    "lancer":["heavy","multi","stamina","armor_break","bleed","dodge","attack_buff","counter","execute","true_damage","sacrifice","ultimate"],
    "spellblade":["damage","burn","freeze","mana_burst","armor_break","counter","vulnerability","lifesteal","true_damage","execute","mana_drain","ultimate"],
    "void_knight":["def_buff","barrier","silence","armor_break","counter","true_damage","vulnerability","execute","lifesteal","stance","ultimate","signature"],
    "chronomancer":["delayed","freeze","dodge","mana_drain","dodge","vulnerability","chain","resource","silence","true_damage","execute","ultimate"],
    "dragon_lord":["heavy","burn","multi","def_buff","attack_buff","aoe","armor_break","sacrifice","true_damage","execute","vulnerability","ultimate"],
    "soul_reaper":["lifesteal","bleed","curse","mark","silence","armor_break","delayed","vulnerability","execute","true_damage","sacrifice","ultimate"],
}

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
    "crusader": ("paladin", "Offensive holy warrior", {"atk": 5, "crit": 2}),
    "aegis_knight": ("paladin", "Shield-focused protector", {"hp": 25, "def": 4}),
    "dawnbringer": ("paladin", "Holy healer and support", {"mp": 20, "def": 2}),
    "blood_saint": ("paladin", "Self-healing holy bruiser", {"hp": 15, "atk": 4, "crit": 2}),
    "spellbreaker": ("spellblade", "Anti-magic duelist", {"atk": 4, "def": 3}),
    "arcane_fencer": ("spellblade", "Magic sword specialist", {"mp": 20, "crit": 3}),
    "beastcaller": ("summoner", "Powerful beast companion specialist", {"hp": 15, "atk": 4}),
    "conjurer": ("summoner", "Multiple-summon specialist", {"mp": 25, "spd": 2}),
    "eidolon_master": ("summoner", "Legendary companion specialist", {"mp": 30, "crit": 3}),
}


# ---------------------------------------------------------------------------
# Specialization combat identities.
# Every existing sub-race gets a distinct passive mechanic. Subclasses use
# combat traits so choosing one changes gameplay instead of only adding stats.
# ---------------------------------------------------------------------------
SUBRACE_TRAITS = {
 "high_elf":{"name":"Arcane Precision","desc":"+8% skill damage; finisher skills deal 10% more.","skill_pct":8,"finisher_pct":10},
 "wood_elf":{"name":"Forest Renewal","desc":"Successful skills restore 3% max HP and 4 MP.","skill_heal_pct":3,"resource_gain":4},
 "dark_elf":{"name":"Shadow Veins","desc":"Skills deal +18% damage against targets below 50% HP.","low_target_pct":18},
 "mountain_dwarf":{"name":"Granite Stance","desc":"Take 8% less damage while above 70% HP.","high_hp_reduction":8},
 "hill_dwarf":{"name":"Last Stand","desc":"Take 15% less damage while below 40% HP.","low_hp_reduction":15},
 "forest_dwarf":{"name":"Rooted Guard","desc":"Defensive skills gain 1 extra shield turn.","shield_turn_bonus":1},
 "high_orc":{"name":"War Cry","desc":"Below 60% HP, skill damage increases by 14%.","low_hp_skill_pct":14},
 "half_orc":{"name":"Brutal Momentum","desc":"Every 3 combo stacks add another 8% skill damage.","combo_pct":8},
 "red_kitsune":{"name":"Foxfire","desc":"Burn skills deal 25% more damage.","effect_bonus":{"burn":25}},
 "white_kitsune":{"name":"Moonstep","desc":"Using a skill grants 10% evasion for 2 turns.","skill_evasion":10},
 "dragonborn":{"name":"Draconic Surge","desc":"Finisher skills deal 12% more damage; successful skills restore 5% max MP.","finisher_pct":12,"resource_pct":5},
 "drakeborn":{"name":"Wyrmheart","desc":"Skills gain 10% damage while below 50% HP.","low_hp_skill_pct":10},
 "catfolk":{"name":"Predator Rhythm","desc":"Multi-hit and critical-focused skills deal 15% more damage.","effect_bonus":{"multi":15,"crit":15}},
 "wolfkin":{"name":"Pack Hunter","desc":"Each combo stack adds 3% skill damage, capped at 15%.","combo_pct":3},
 "foxkin":{"name":"Mirage Pounce","desc":"Skills gain 25% damage after a dodge state is active.","next_skill_pct":25},
 "spring_fae":{"name":"Spring Bloom","desc":"Skills restore 4% max HP while below 60% HP.","conditional_skill_heal":4},
 "night_fae":{"name":"Night Veil","desc":"Below 50% HP, gain 10% skill damage and 12% evasion.","low_hp_skill_pct":10,"low_hp_evasion":12},
 "blood_vampire":{"name":"Sanguine Feast","desc":"Restore 6% of skill damage as HP, capped at 5% max HP per action.","trait_lifesteal":6,"trait_lifesteal_cap":5},
 "noble_vampire":{"name":"Royal Hunger","desc":"Finisher skills deal 15% more damage.","finisher_pct":15},
 "iron_golem":{"name":"Iron Shell","desc":"Begin combat with a 25% shield for 2 turns.","start_shield":25,"start_shield_turns":2},
 "crystal_golem":{"name":"Prism Core","desc":"Reflect 20% of damage while your shield is active.","reflect":20},
 "storm_human":{"name":"Stormfoot","desc":"Using a skill grants 8% evasion for 2 turns.","skill_evasion":8},
 "desert_human":{"name":"Sunforged","desc":"Critical hits against you deal 7% less damage.","crit_damage_reduction":7},
}

SUBCLASS_TRAITS = {
 "vanguard":{"name":"Hold the Line","desc":"Defending gives an additional 18% damage reduction.","defend_reduction":18},
 "blade_master":{"name":"Weapon Flow","desc":"Heavy and multi-hit skills deal 15% more damage.","effect_bonus":{"heavy":15,"multi":15}},
 "berserk_lord":{"name":"Blood Frenzy","desc":"Below 50% HP, skills deal 20% more damage.","low_hp_skill_pct":20},
 "iron_guardian":{"name":"Fortress Core","desc":"Begin combat with a 20% shield for 2 turns.","start_shield":20,"start_shield_turns":2},
 "arcane_knight":{"name":"Arcane Guard","desc":"Barrier skills deal 15% more damage.","effect_bonus":{"barrier":15}},
 "fire_mage":{"name":"Inferno Mastery","desc":"Burn skills deal 30% more damage.","effect_bonus":{"burn":30}},
 "frost_mage":{"name":"Winter's Silence","desc":"Freeze skills deal 25% more damage.","effect_bonus":{"freeze":25}},
 "battle_mage":{"name":"Spellfist","desc":"Skills deal 7% more damage and you take 6% less damage.","skill_pct":7,"damage_reduction":6},
 "shadow_assassin":{"name":"Death from Shadows","desc":"Mark and execute skills deal 25% more damage.","effect_bonus":{"mark":25,"execute":25}},
 "nightblade":{"name":"Crimson Dance","desc":"Bleed and multi-hit skills deal 18% more damage.","effect_bonus":{"bleed":18,"multi":18}},
 "sniper":{"name":"Deadeye","desc":"Skills deal 18% more damage while the enemy is above 70% HP.","high_target_pct":18},
 "beast_master":{"name":"Beast Bond","desc":"Pet attacks deal 25% more damage.","pet_damage_pct":25},
 "holy_priest":{"name":"Sacred Grace","desc":"Healing skills restore 25% more HP.","heal_skill_pct":25},
 "battle_cleric":{"name":"Martyr's Oath","desc":"Below 50% HP, take 8% less damage and receive 25% more healing.","low_hp_reduction":8,"low_hp_heal_pct":25},
 "storm_druid":{"name":"Stormcaller","desc":"Terrain, Burn and Freeze skills deal 18% more damage.","effect_bonus":{"terrain":18,"burn":18,"freeze":18}},
 "wild_druid":{"name":"Wildshape","desc":"Below 50% HP, gain 15% skill damage and 10% damage reduction.","low_hp_skill_pct":15,"low_hp_reduction":10},
 "dragon_monk":{"name":"Dragon Combo","desc":"Combo-based skills gain 10% damage per combo stack, capped at 40%.","combo_pct":10},
 "shadow_monk":{"name":"Afterimage","desc":"After a skill, gain 15% evasion for 1 turn.","skill_evasion":15},
 "minstrel":{"name":"Encore","desc":"Healing skills are 20% stronger and skills restore 3 MP.","heal_skill_pct":20,"resource_gain":3},
 "war_chanter":{"name":"War Chorus","desc":"Attack-buff skills deal 20% more damage.","effect_bonus":{"attack_buff":20}},
 "bone_lord":{"name":"Grave Legion","desc":"Summon skills deal 25% more damage.","effect_bonus":{"summon":25}},
 "soul_reaper":{"name":"Soul Harvest","desc":"Execute and lifesteal skills deal 20% more damage.","effect_bonus":{"execute":20,"lifesteal":20}},
 "demon_pact":{"name":"Pact of Ruin","desc":"Sacrifice skills deal 30% more damage.","effect_bonus":{"sacrifice":30}},
 "void_caller":{"name":"Reality Fracture","desc":"Vulnerability and true-damage skills deal 22% more damage.","effect_bonus":{"vulnerability":22,"true_damage":22}},
 "bombardier":{"name":"Chain Reaction","desc":"Burn and Area skills deal 20% more damage.","effect_bonus":{"burn":20,"aoe":20}},
 "transmuter":{"name":"Efficient Catalyst","desc":"Successful skills restore 4% max MP.","resource_pct":4},
 "artificer":{"name":"Construct Command","desc":"Pet and summon skills deal 25% more damage.","effect_bonus":{"pet_boost":25,"summon":25}},
 "machinist":{"name":"Overclock","desc":"After a skill, the next skill gains 20% damage.","next_skill_pct":20},
 "fencer":{"name":"Perfect Riposte","desc":"Counter and multi-hit skills deal 20% more damage.","effect_bonus":{"counter":20,"multi":20}},
 "champion":{"name":"Arena Momentum","desc":"Each combo stack adds 4% skill damage, capped at 16%.","combo_pct":4},
 "dragoon":{"name":"Aerial Assault","desc":"Heavy and multi-hit skills deal 18% more damage.","effect_bonus":{"heavy":18,"multi":18}},
 "templar":{"name":"Holy Spear","desc":"Defending gives an additional 20% damage reduction.","defend_reduction":20},
 "spellbreaker":{"name":"Null Edge","desc":"True-damage and armor-break skills deal 25% more damage.","effect_bonus":{"true_damage":25,"armor_break":25}},
 "arcane_fencer":{"name":"Runic Tempo","desc":"Successful skills restore 4% max MP and the next skill deals 8% more damage.","resource_pct":4,"next_skill_pct":8},
 "crusader":{"name":"Divine Wrath","desc":"Skills deal 10% more damage; attacks against enemies below 40% HP deal another 10%.","skill_pct":10,"low_target_pct":10},
 "aegis_knight":{"name":"Sacred Bulwark","desc":"Begin combat with a 25% shield for 2 turns; defending gives 20% additional damage reduction.","start_shield":25,"start_shield_turns":2,"defend_reduction":20},
 "dawnbringer":{"name":"Light of Dawn","desc":"Healing skills restore 25% more HP; successful healing also restores 4 MP.","heal_skill_pct":25,"resource_gain":4},
 "blood_saint":{"name":"Sanguine Faith","desc":"Offensive skills restore 10% of damage dealt as HP, capped at 8% max HP per skill; below 50% HP, skill damage increases by 15%.","trait_lifesteal":10,"trait_lifesteal_cap":8,"low_hp_skill_pct":15},
 "beastcaller":{"name":"Primal Bond","desc":"Pet attacks deal 30% more damage and successful pet attacks build Feral momentum.","pet_damage_pct":30,"pet_feral_pct":5},
 "conjurer":{"name":"Arcane Multiplicity","desc":"Summon skills deal 15% more damage and gain additional power when multiple summons are active.","effect_bonus":{"summon":15},"multi_summon_bonus":10},
 "eidolon_master":{"name":"Eidolon Bond","desc":"Summon skills deal 20% more damage; successful summon actions build Soul Charges toward an empowered Eidolon attack.","effect_bonus":{"summon":20},"eidolon_charge":1},
}


# ---------------------------------------------------------------------------
# Combat skills. Each class has a small, readable kit so battles are about
# choosing the right action instead of pressing one "Skill" button forever.
# Keys are stable so old characters automatically receive their class kit.
# ---------------------------------------------------------------------------
CLASS_SKILL_NAMES = {
    "warrior": ("Vanguard's Wrath", "Guard Break", "Tempest Requiem", "Iron Will"),
    "berserker": ("Furyfang", "Blood Rush", "Rampage", "Berserker Fury"),
    "knight": ("Dawnshield Crash", "Royal Maul", "Guardian Wall", "Throne of Judgment"),
    "mage": ("Aetherbolt", "Cinderfall", "Glacial Aria", "Meteor"),
    "rogue": ("Duskfang Waltz", "Poison Edge", "Shadow Step", "Assassinate"),
    "assassin": ("Killing Edge", "Venom Cut", "Eclipse Step", "Reaper's Brand"),
    "ranger": ("Hawkeye's Oath", "Starpiercer", "Heaven's Rain", "Predator's Sigil"),
    "paladin": ("Dawn's Smite", "Radiant Shield", "Divine Light", "Judgment"),
    "summoner": ("Eidolon Bolt", "Feral Conclave", "Eidolon Bond", "Primal Storm"),
    "cleric": ("Lumen Bolt", "Judicator's Light", "Dawn's Renewal", "Divine Grace"),
    "druid": ("Briarwhip", "Lunaris Bloom", "Sylvan Benediction", "Wild Tempest"),
    "monk": ("Heavenly Meridian", "Sevenfold Petals", "Inner Focus", "Dragon Fist"),
    "bard": ("Resonance Spark", "Battle Anthem", "Seraphic Lullaby", "Grand Finale"),
    "necromancer": ("Wraithbolt", "Gravefang", "Dark Pact", "Soul Requiem"),
    "warlock": ("Umbral Bolt", "Brand of Ruin", "Merciful Requiem", "Doomsday Sigil"),
    "alchemist": ("Acid Flask", "Bomb Toss", "Rejuvenation", "Grand Transmutation"),
    "engineer": ("Arc Shot", "Turret Burst", "Repair Drone", "Overclock"),
    "duelist": ("Mirrorsteel Reprisal", "Lunge", "Blade Dance", "Perfect Duel"),
    "lancer": ("Spear Thrust", "Vault", "Dragon Dive", "Skybreaker Fist"),
    "spellblade": ("Arcane Slash", "Elemental Edge", "Mana Guard", "Ether Break"),
}

# Six additional skills per class. They unlock progressively instead of all
# being available at level 1, so high-level builds have meaningful choices.
ADVANCED_SKILLS = {
    "warrior": ("Gale Rend", "Warborn Roar", "Sword Storm", "Lionheart", "King's Edge", "Warlord's Ascension"),
    "berserker": ("Ruinous Rend", "Frenzy", "Crimson Tempest", "Rage Unbound", "Executioner", "Apocalypse Unbound"),
    "knight": ("Aegis Reprisal", "Fortress", "Knight's Oath", "Aegis Crash", "Royal Bulwark", "Divine Bastion"),
    "mage": ("Arcane Lance", "Infernal Sonata", "Glacial Prison", "Arcane Barrage", "Starfall", "Cataclysm"),
    "rogue": ("Bleeding Flurry", "Smoke Veil", "Crimson Dance", "Phantom Barrage", "Death Spiral", "Eclipse"),
    "assassin": ("Hemorrhage", "Veiled Step", "Nightmare Cut", "Phantom Barrage", "Silentus", "Void Reaper"),
    "ranger": ("Volley", "Trap Mastery", "Storm Shot", "Predator's Mark", "Astral Arrow", "Celestial Volley"),
    "paladin": ("Consecrated Blade", "Holy Ward", "Radiant Burst", "Guardian's Grace", "Sacred Verdict", "Heaven's Verdict"),
    "summoner": ("Spirit Swarm", "Beast Guard", "Soul Chain", "Primal Roar", "Astral Summon", "Genesis Summons"),
    "cleric": ("Radiant Lance", "Hallowed Veil", "Mass Renewal", "Holy Nova", "Seraphic Grace", "Seraphic Apotheosis"),
    "druid": ("Vine Prison", "Lunar Bloom", "Nature's Ward", "Wildheart Inferno", "Ancient Grove", "Worldroot"),
    "monk": ("Palm Burst", "Adamantine Vessel", "Sevenfold Strike", "Chi Storm", "Heavenly Fist", "Azure Dragon Ascension"),
    "bard": ("Harmonic Rupture", "War Chorus", "Soothing Verse", "Grand Crescendo", "Heroic Symphony", "Mythic Finale"),
    "necromancer": ("Grave Lance", "Bone Prison", "Sanguine Grave", "Army of Bones", "Deathstorm", "Eternal Dusk"),
    "warlock": ("Abyssal Lance", "Hex Prison", "Soul Siphon", "Chaos Rain", "Demon's Wrath", "Abyssal Apocalypse"),
    "alchemist": ("Corrosive Flask", "Chain Reaction", "Vital Elixir", "Grand Bombardment", "Philosopher's Fire", "Perfect Transmutation"),
    "engineer": ("Piercing Bolt", "Auto-Turret", "Repair Matrix", "Overdrive", "Siege Cannon", "Omega Protocol"),
    "duelist": ("Countercut", "Flash Lunge", "Blade Tempest", "Perfect Tempo", "Sword Eclipse", "Absolute Duel"),
    "lancer": ("Impale", "Sky Vault", "Dragon Rush", "Spear Tempest", "Heavenfall", "Dragon Emperor"),
    "spellblade": ("Runic Slash", "Elemental Storm", "Arcane Guard", "Ether Surge", "Astral Edge", "Reality Break"),
}

MAGIC_CLASSES = {"mage", "summoner", "cleric", "druid", "bard", "necromancer", "warlock", "alchemist"}
HEAL_CLASSES = {"paladin", "cleric", "druid", "bard", "alchemist", "engineer", "warlock", "summoner"}

# ---------------------------------------------------------------------------
# Skill system
# Each class has 20 distinct skills.  The first three are available from the
# beginning; later skills unlock in meaningful 5-10 level gaps instead of
# handing the player a new button every couple of levels.
# ---------------------------------------------------------------------------
SKILL_UNLOCK_LEVELS = (1, 1, 1, 6, 11, 16, 22, 28, 34, 40, 46, 52, 58, 64, 70, 76, 82, 88, 94, 100)

# Every entry uses a different combat mechanic inside a single class.
SKILL_ARCHETYPES = [
    ("damage", "Basic Technique", "Reliable single-target damage."),
    ("heavy", "Heavy Technique", "A slower, stronger hit with higher damage."),
    ("multi", "Twin Technique", "Two separate hits; useful against light defenses."),
    ("bleed", "Wound Technique", "Deals damage and inflicts Bleed for 3 turns."),
    ("heal", "Recovery Technique", "Restores a percentage of maximum HP."),
    ("def_buff", "Guard Technique", "Deals light damage and grants +18% DEF for 3 turns."),
    ("attack_buff", "Power Technique", "Deals damage and grants +15% ATK for 3 turns."),
    ("armor_break", "Break Technique", "Deals damage and inflicts -18% DEF for 3 turns."),
    ("poison", "Venom Technique", "Deals damage and applies Poison for 4 turns."),
    ("burn", "Scorch Technique", "Deals damage and applies Burn for 3 turns."),
    ("freeze", "Control Technique", "Deals damage and slows the enemy for 2 turns."),
    ("lifesteal", "Drain Technique", "Deals damage and restores HP from the damage dealt."),
    ("mana_drain", "Siphon Technique", "Deals damage and restores MP."),
    ("dodge", "Evasion Technique", "Deals light damage and grants +20% evasion for 3 turns."),
    ("counter", "Counter Technique", "Prepares a counter stance against the next attack."),
    ("barrier", "Barrier Technique", "Creates a strong shield against the next 2 hits."),
    ("vulnerability", "Expose Technique", "Deals damage and makes the enemy take +20% damage for 2 turns."),
    ("execute", "Execution Technique", "Deals bonus damage when the target is below 30% HP."),
    ("true_damage", "Piercing Technique", "Deals controlled damage that ignores defense."),
    ("ultimate", "Signature Technique", "High-impact class finisher with damage and a small heal."),
]

# Unlock gaps are deliberately long.  Players start with exactly three skills
# and gradually build a toolkit rather than collecting dozens of near-identical
# attacks immediately.
SKILL_COSTS = (8, 12, 15, 18, 14, 16, 18, 20, 21, 22, 24, 25, 26, 28, 30, 32, 34, 36, 38, 42)
SKILL_COOLDOWNS = (0, 1, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 6, 7)

# Skill points are now for mastering unlocked skills, not for raw stats.
# Each skill can be mastered to rank 5; every rank gives a small, bounded
# improvement so a high-level skill feels stronger without replacing gear or
# talent choices.
SKILL_MAX_RANK = 5
SKILL_RANK_DAMAGE = 0.035
SKILL_RANK_HEAL = 0.02

# Permanent talent trees. Every node has five ranks and costs one Talent Point
# per rank. Class trees are deliberately different in name/flavour, while the
# mechanical bonuses stay small and predictable. Race trees add a second layer.
CLASS_TALENT_TEMPLATES = {
    "warrior": [("vanguard_heart","Vanguard Heart","+1.5% maximum HP per rank","hp_pct"),("weapon_mastery","Weapon Mastery","+1% skill damage per rank","skill_pct"),("iron_training","Iron Training","+1% DEF per rank","def_pct"),("battle_instinct","Battle Instinct","+0.5% Crit per rank","crit"),("second_wind","Second Breath","+1% healing received per rank","heal_pct"),("martial_focus","Martial Focus","+1% ATK per rank","atk_pct"),("steady_breath","Steady Breath","+1% maximum MP per rank","mp_pct"),("finisher_training","Finisher Training","+1% execute/ultimate damage per rank","finisher_pct")],
    "berserker": [("blood_furnace","Blood Furnace","+1% ATK per rank","atk_pct"),("pain_to_power","Pain to Power","+1% skill damage per rank","skill_pct"),("scarred_hide","Scarred Hide","+1% DEF per rank","def_pct"),("predator_eye","Predator Eye","+0.5% Crit per rank","crit"),("blood_recovery","Blood Requiem","+1% healing per rank","heal_pct"),("fury_reserve","Fury Reserve","+1% maximum MP per rank","mp_pct"),("rage_body","Rage Body","+1.5% HP per rank","hp_pct"),("executioner_training","Executioner Training","+1% finisher damage per rank","finisher_pct")],
    "knight": [("fortress_heart","Fortress Heart","+1.5% maximum HP per rank","hp_pct"),("shield_mastery","Shield Mastery","+1% skill damage per rank","skill_pct"),("plate_discipline","Plate Discipline","+1% DEF per rank","def_pct"),("battle_awareness","Battle Awareness","+0.5% Crit per rank","crit"),("guardian_grace","Guardian Grace","+1% healing per rank","heal_pct"),("holy_reserve","Holy Reserve","+1% maximum MP per rank","mp_pct"),("royal_strength","Royal Strength","+1% ATK per rank","atk_pct"),("verdict_mastery","Verdict Mastery","+1% finisher damage per rank","finisher_pct")],
    "mage": [("arcane_core","Arcane Core","+1.5% maximum MP per rank","mp_pct"),("spellcraft","Spellcraft","+1% skill damage per rank","skill_pct"),("warding","Warding","+1% DEF per rank","def_pct"),("arcane_precision","Arcane Precision","+0.5% Crit per rank","crit"),("mystic_recovery","Mystic Recovery","+1% healing per rank","heal_pct"),("ether_body","Ether Body","+1% HP per rank","hp_pct"),("arcane_force","Arcane Force","+1% ATK per rank","atk_pct"),("cataclysm_mastery","Cataclysm Mastery","+1% finisher damage per rank","finisher_pct")],
    "rogue": [("shadow_body","Shadow Body","+1% HP per rank","hp_pct"),("dirty_tricks","Dirty Tricks","+1% skill damage per rank","skill_pct"),("evasive_training","Evasive Training","+1% DEF per rank","def_pct"),("killer_eye","Killer Eye","+0.5% Crit per rank","crit"),("field_recovery","Field Recovery","+1% healing per rank","heal_pct"),("shadow_reserve","Shadow Reserve","+1% MP per rank","mp_pct"),("assassin_force","Assassin Force","+1% ATK per rank","atk_pct"),("execution_art","Execution Art","+1% finisher damage per rank","finisher_pct")],
}
# Classes not listed above inherit a class-specific named tree generated from
# their identity, keeping every class playable without repetitive hard-coded data.
CLASS_TALENT_FALLBACK = [
    ("core_training","Core Training","+1% maximum HP per rank","hp_pct"),
    ("combat_mastery","Combat Mastery","+1% skill damage per rank","skill_pct"),
    ("guard_training","Guard Training","+1% DEF per rank","def_pct"),
    ("keen_eye","Keen Eye","+0.5% Crit per rank","crit"),
    ("renewal","Renewal","+1% healing per rank","heal_pct"),
    ("resource_mastery","Resource Mastery","+1% maximum MP per rank","mp_pct"),
    ("power_training","Power Training","+1% ATK per rank","atk_pct"),
    ("finisher_mastery","Finisher Mastery","+1% finisher damage per rank","finisher_pct"),
]

RACE_TALENT_TEMPLATES = {
    "human": [("adaptation","Adaptation","+0.5% ATK, DEF and HP per rank","balanced"),("resourcefulness","Resourcefulness","+1% maximum MP per rank","mp_pct"),("luck","Fortune","+0.5% Crit per rank","crit")],
    "elf": [("keen_senses","Keen Senses","+0.5% Crit per rank","crit"),("forest_vigor","Forest Vigor","+1% HP per rank","hp_pct"),("arcane_affinity","Arcane Affinity","+1% skill damage per rank","skill_pct")],
    "dwarf": [("stone_skin","Stone Skin","+1% DEF per rank","def_pct"),("deep_reserves","Deep Reserves","+1% HP per rank","hp_pct"),("forge_power","Forge Power","+1% ATK per rank","atk_pct")],
    "orc": [("blood_strength","Blood Strength","+1% ATK per rank","atk_pct"),("warrior_hide","Warrior Hide","+1% HP per rank","hp_pct"),("brutal_focus","Brutal Focus","+0.5% Crit per rank","crit")],
    "kitsune": [("foxfire","Foxfire","+1% skill damage per rank","skill_pct"),("trickster_speed","Trickster Speed","+0.5% Crit per rank","crit"),("spirit_reserve","Spirit Reserve","+1% MP per rank","mp_pct")],
    "fae": [("fey_grace","Fey Grace","+1% HP per rank","hp_pct"),("glimmer","Glimmer","+1% skill damage per rank","skill_pct"),("fey_focus","Fey Focus","+0.5% Crit per rank","crit")],
    "vampire": [("bloodline","Bloodline","+1% ATK per rank","atk_pct"),("night_body","Night Body","+1% HP per rank","hp_pct"),("blood_magic","Blood Magic","+1% healing per rank","heal_pct")],
    "golem": [("living_fortress","Living Fortress","+1% DEF per rank","def_pct"),("stone_core","Stone Core","+1.5% HP per rank","hp_pct"),("crystal_power","Crystal Power","+1% skill damage per rank","skill_pct")],
}


_CLASS_SKILL_NAMES = {
    "warrior": ["Vanguard's Wrath", "Gale Rend", "Tempest Requiem", "Ironfall Crescent", "Second Breath", "Aegis of Stone", "Warborn Roar", "Kingsplitter", "Scarlet Brand", "Emberbrand", "Skullbreaker", "Valor Reaver", "Warrior's Clarity", "Windborne March", "Mirrorsteel Reprisal", "Titan's Vigil", "Sundered Fate", "Grim Severance", "Adamantine Fang", "Thronebreaker"],
    "berserker": ["Furyfang", "Ruinous Rend", "Crimson Tempest", "Hemorrhage Arc", "Blood Requiem", "Madman's Bulwark", "Warcry of Ruin", "Mangled Crown", "Venomous Rage", "Hellfire Frenzy", "Winter's Grasp", "Sanguine Feast", "Fury Reaver", "Predator's Rush", "Berserker's Reprisal", "Hide of the Ravager", "Murderous Instinct", "Final Rupture", "Furyspike", "Apocalypse Unbound"],
    "knight": ["Dawnshield Crash", "Royal Maul", "Aegis Tempest", "Scarlet Oath", "Knight's Benediction", "Bastion Vow", "Sovereign's Call", "Kingsplitter", "Venom Oath", "Sunscar Brand", "Winter Aegis", "Valor Reaver", "Arcane Seal", "Bulwark Step", "Aegis Reprisal", "Citadel of Dawn", "Judicator's Gaze", "Royal Severance", "Seraphic Lance", "Throne of Judgment"],
    "mage": ["Aetherbolt", "Cinderfall", "Glacial Aria", "Astral Rupture", "Etherial Grace", "Prism Aegis", "Leyline Ascension", "Runebreak", "Serpent's Veil", "Infernal Sonata", "Winter's Silence", "Sanguine Transmutation", "Aether Siphon", "Astral Step", "Arcanist's Reprisal", "Aetheric Bastion", "Leyline Exposure", "Void Sentence", "Starless Lance", "Celestial Cataclysm"],
    "rogue": ["Duskfang Waltz", "Umbral Crescent", "Phantom Waltz", "Crimson Vein", "Rogue's Reprieve", "Veilguard", "Predator's Pulse", "Gloamrend", "Viper's Kiss", "Cinderfang", "Nightspine Dart", "Sanguine Touch", "Shadow Siphon", "Umbral Step", "Thief's Reprisal", "Veil of Ash", "Hunter's Brand", "Gravekiss", "Nightpiercer", "Ebon Eclipse"],
    "assassin": ["Crimson Fang", "Viper's Shroud", "Eclipse Step", "Sanguine Requiem", "Moonless Harvest", "Reaper's Brand", "Predator's Omen", "Kingscar", "Widow's Ichor", "Ashen Fang", "Winter's Needle", "Blood Requiem", "Aether Theft", "Wraithstep", "Phantom Reprisal", "Veil of Oblivion", "Doomed Sigil", "Silentus", "Starless Fang", "Eclipse Execution"],
    "ranger": ["Hawkeye's Oath", "Starpiercer", "Heaven's Rain", "Thornflight", "Hunter's Grace", "Warden's Hide", "Predator's Sight", "Adamant Arrow", "Viperflight", "Emberflight", "Frostflight", "Sanguine Arrow", "Soulstring", "Galefoot", "Reprisal Arrow", "Warden's Snare", "Predator's Sigil", "Last Hunt", "Astral Arrow", "Celestial Volley"],
    "paladin": ["Dawn's Smite", "Aureate Aegis", "Lumen's Grace", "Seraphic Might", "Sanctified Requiem", "Judicator's Reprisal", "Solaris Brand", "Consecration", "Serpent's Sin", "Halo Bastion", "Heaven's Condemnation", "Heaven's Verdict", "Faith Reaver", "Pilgrim's Step", "Seraphic Reprisal", "Aegis of the Seraphim", "Judgment Sigil", "Apotheosis Verdict", "Seraph's Lance", "Heaven's Verdict"],
    "summoner": ["Eidolon Bolt", "Feral Conclave", "Eidolon Bond", "Wraithscar", "Ethereal Mend", "Warden Eidolon", "Primal Sovereignty", "Eidolon Rupture", "Ichor Familiar", "Cinder Familiar", "Rime Familiar", "Vital Covenant", "Aether Pact", "Astral Passage", "Feral Reprisal", "Eidolon Aegis", "Soul Sigil", "Eidolon Devour", "Astral Fang", "Genesis Summons"],
    "cleric": ["Lumen Bolt", "Judicator's Light", "Seraphic Tide", "Sunscar", "Dawn's Renewal", "Hallowed Veil", "Litany of Valor", "Heretic's Ruin", "Purge of Venom", "Censerfire", "Winter Litany", "Merciful Requiem", "Faith Reaver", "Halo Step", "Seraphic Reprisal", "Sanctum of Dawn", "Heretic's Brand", "Final Benediction", "Judgment Spear", "Seraphic Apotheosis"],
    "druid": ["Briarwhip", "Lunaris Bloom", "Verdant Tempest", "Briar's Curse", "Sylvan Benediction", "Elderbark Mantle", "Primal Flourish", "Worldroot Rend", "Venomblossom", "Wildheart Inferno", "Frostpetal", "Verdant Siphon", "Leyroot", "Galeleaf Step", "Briar Reprisal", "Ancientwood Aegis", "Spiritbloom", "Primal Severance", "Worldroot Spire", "Gaia's Tempest"],
    "monk": ["Heavenly Meridian", "Iron Lotus", "Sevenfold Petals", "Crimson Meridian", "Stillwater Trance", "Adamantine Vessel", "Warrior's Breath", "Meridian Ruin", "Serpent Meridian", "Sunforge Fist", "Winter Lotus", "Sanguine Palm", "Qi Requiem", "Cloudstep", "Mirror Palm", "Heavenly Mantle", "Eightfold Rupture", "Dragon's Last Breath", "Skybreaker Fist", "Azure Dragon Ascension"],
    "bard": ["Resonance Spark", "Harmonic Rupture", "War Canticle", "Dissonant Scar", "Seraphic Lullaby", "Ballad of the Aegis", "March of Kings", "Sundered Symphony", "Venomous Refrain", "Ember Overture", "Winter's Ballad", "Sanguine Aria", "Aetheric Melody", "Tempo of the Gale", "Reprisal Chorus", "Symphony of Wards", "Dirge of Frailty", "Grand Finale", "Astral Crescendo", "Mythic Cantata"],
    "necromancer": ["Wraithbolt", "Gravefang", "Mourning Tide", "Gravescar", "Unhallowed Renewal", "Ossuary Aegis", "Abyssal Ascension", "Soulreaver", "Miasma of Graves", "Netherflame", "Tombfrost", "Sanguine Grave", "Aether Reaping", "Wraithwalk", "Ossuary Reprisal", "Gravebound Ward", "Hex of Ruin", "Reaper's Severance", "Oblivion Spire", "Eternal Dusk"],
    "warlock": ["Umbral Bolt", "Brand of Ruin", "Abyssal Sonata", "Crimson Hex", "Pact of Renewal", "Demonhide Mantle", "Abyssal Ascension", "Curse of Iron", "Plague Sigil", "Netherflame", "Rime Hex", "Sanguine Siphon", "Pact Reaver", "Abyss Step", "Demon's Reprisal", "Abyssal Aegis", "Hex of Exposure", "Doomsday Sigil", "Netherfang", "Abyssal Apocalypse"],
    "alchemist": ["Acid Flask", "Bomb Toss", "Catalyst Burst", "Corrosive Cut", "Rejuvenation", "Reactive Mixture", "Battle Tonic", "Armor Dissolver", "Toxic Compound", "Incendiary Flask", "Cryo Flask", "Life Elixir", "Mana Elixir", "Quickstep Tonic", "Counter Mixture", "Barrier Compound", "Weakness Serum", "Execution Bomb", "Piercing Compound", "Grand Transmutation"],
    "engineer": ["Arc Shot", "Siege Burst", "Drone Volley", "Bleeding Shrapnel", "Repair Drone", "Plated Frame", "Overclock", "Armor Breaker", "Toxic Payload", "Incendiary Round", "Cryo Round", "Leech Drone", "Energy Reclaimer", "Thruster Dash", "Counter Turret", "Energy Barrier", "Target Lock", "Finisher Cannon", "Rail Pierce", "Omega Protocol"],
    "duelist": ["Mirrorsteel Reprisal", "Lunge", "Blade Dance", "Crimson Feint", "Second Breath", "Perfect Guard", "Tempo Surge", "Guard Break", "Poisoned Point", "Flashing Edge", "Frost Feint", "Life-Stealing Lunge", "Tempo Siphon", "Flash Step", "Perfect Counter", "Duelist Barrier", "Opening Cut", "Final Thrust", "True Edge", "Absolute Duel"],
    "lancer": ["Spear Thrust", "Vault", "Dragon Dive", "Bleeding Impale", "Combat Recovery", "Spear Guard", "Resolve Surge", "Armor Skewer", "Venom Spear", "Flame Dive", "Frost Lance", "Blood Lance", "Resolve Siphon", "Skystep", "Counter Thrust", "Dragon Ward", "Weakpoint Impale", "Heavenfall", "Dragon Pierce", "Dragon Emperor"],
    "spellblade": ["Arcane Slash", "Elemental Edge", "Rune Flurry", "Bleeding Rune", "Ether Renewal", "Mana Guard", "Arcane Might", "Rune Break", "Venom Rune", "Inferno Edge", "Frost Edge", "Soul Edge", "Aether Siphon", "Blink Blade", "Runic Counter", "Ether Barrier", "Expose Rune", "Ether Execution", "Astral Edge", "Reality Break"],
}

_CLASS_SKILL_NAMES.update({
    "void_knight":["Null Guard","Void Cleave","Abyssal Wall","Spell Sever","Gravitic Counter","Null Barrier","Void Brand","Eventide Slash","Black Oath","Final Null","Eclipse Pierce","Void Judgment","Abyss Step","Anti-Magic Pulse","Oblivion Guard","Null Field","Void Rend","Execution Zero","Starless Edge","Knight of Nothing"],
    "chronomancer":["Second Hand","Time Fracture","Temporal Anchor","Rewind Pulse","Haste Loop","Stolen Moment","Clockwork Delay","Future Sight","Time Stop","Paradox Cut","Chrono Pierce","End of Seconds","Backstep","Time Siphon","Frozen Moment","Causal Break","Borrowed Future","Age the Wound","Timeline Collapse","Eternal Clock"],
    "dragon_lord":["Drakefang","Inferno Breath","Wingstorm","Scale Guard","Dragon Roar","Molten Brand","Skyfire Dive","Ancient Might","Cataclysm Wing","Worldfire","Dragon Pierce","King of Dragons","Aerial Dominion","Scorching Talon","Imperial Scale","Elder Flame","Draconic Ruin","Heavenbreaker","Starfire Maw","Dragon Apocalypse"],
    "soul_reaper":["Soulreaver","Grave Step","Reaper's Mark","Bleeding Echo","Sanguine Grave","Death Veil","Echo Harvest","Spirit Sever","Funeral Bell","Last Breath","Requiem Pierce","Soul Reaping","Wraith Step","Memory Drain","Death Counter","Grave Barrier","Final Echo","Execution Reaper","Oblivion Scythe","End of Souls"],
})

_CLASS_FLAVOUR = {k:k for k in _CLASS_SKILL_NAMES}


def _skill_buff_text(effect):
    return {"attack_buff":"+18% ATK for 3 turns","def_buff":"+22% DEF for 3 turns","dodge":"+18% evasion for 3 turns","team_buff":"+12% ATK and DEF for 3 turns","focus":"+10 critical chance for 3 turns","stance":"+24% DEF below 50% HP, otherwise +20% ATK for 3 turns","pet_boost":"Companion empowered and cooldown refreshed","resource":"Restores MP and Stamina","stamina":"+25 Stamina","mana_burst":"Restores about 6% maximum MP","ultimate":"Restores about 8% maximum HP","signature":"+18% ATK for 2 turns"}.get(effect,"None")

def _skill_debuff_text(effect):
    return {"armor_break":"-18% enemy DEF for 3 turns","mark":"+16% follow-up damage for 3 turns","vulnerability":"+20% damage taken for 2 turns","poison":"Poison for 4 turns","burn":"Burn for 3 turns","freeze":"Freeze for 2 turns; chance to Stun","silence":"Enemy abilities disabled for 2 turns","curse":"+14% damage taken for 3 turns","terrain":"+12% damage taken for 3 turns","bleed":"Bleed for 3 turns"}.get(effect,"None")

def _skill_effect_text(effect):
    return {
        "damage":"Deals direct physical damage.",
        "heavy":"Deals heavy damage with a higher damage cap.",
        "multi":"Hits twice with reduced damage per hit.",
        "bleed":"Deals damage and applies Bleed for 3 turns.",
        "heal":"Restores about 22% of maximum HP.",
        "team_heal":"Restores about 30% of maximum HP.",
        "recovery":"Restores about 34% HP and restores MP.",
        "def_buff":"Deals a light hit and grants +22% DEF for 3 turns.",
        "attack_buff":"Deals a light hit and grants +18% ATK for 3 turns.",
        "armor_break":"Deals damage and reduces enemy DEF by 18% for 3 turns.",
        "poison":"Deals damage and applies Poison for 4 turns.",
        "burn":"Deals damage and applies Burn for 3 turns.",
        "freeze":"Deals damage, slows the enemy for 2 turns, and has a chance to Stun.",
        "lifesteal":"Deals damage and heals you for part of the damage dealt.",
        "mana_drain":"Deals damage and restores about 12% maximum MP.",
        "dodge":"Deals a light hit and grants +18% evasion for 3 turns.",
        "counter":"Creates a 1-turn defensive counter state.",
        "barrier":"Creates a 2-turn barrier that reduces incoming damage.",
        "vulnerability":"Deals damage and makes the enemy take +20% damage for 2 turns.",
        "execute":"Deals stronger damage, especially when the enemy is below 30% HP.",
        "true_damage":"Deals damage that ignores enemy DEF.",
        "ultimate":"Deals very high damage and restores about 8% maximum HP.",
        "signature":"Deals very high damage and grants +18% ATK for 2 turns.",
        "stance":"Below 50% HP: +24% DEF for 3 turns; otherwise +20% ATK for 3 turns.",
        "focus":"Grants +10 critical chance for 3 turns.",
        "crit":"Grants +12 critical chance for 2 turns.",
        "mark":"Deals damage and marks the enemy for +16% follow-up damage for 3 turns.",
        "silence":"Deals damage and disables enemy abilities for 2 turns.",
        "curse":"Deals damage and makes the enemy take +14% damage for 3 turns.",
        "terrain":"Deals damage and makes the enemy take +12% damage for 3 turns.",
        "resource":"Restores MP and Stamina while dealing damage.",
        "stamina":"Restores 25 Stamina while dealing damage.",
        "mana_burst":"Deals damage and restores about 6% maximum MP.",
        "delayed":"Stores a delayed strike for the next resolution.",
        "sacrifice":"Consumes about 8% maximum HP for a stronger attack.",
        "emergency":"Deals stronger damage while below 50% HP.",
        "combo":"Builds combo and increases the strike's damage.",
        "chain":"Deals damage that scales with your current combo.",
        "team_buff":"Deals a light hit and grants +12% ATK and DEF for 3 turns.",
        "pet_boost":"Empowers the companion and refreshes its cooldown.",
        "summon":"Deals a summoned attack and builds combo.",
        "aoe":"Deals a wider attack with capped damage.",
        "dispel":"Removes selected enemy advantages and deals damage.",
        "random":"Randomly performs a controlled damage, heal, or defend effect.",
        "defend":"Reduces the next incoming hit.",
        "reflect":"Creates protection and reflects part of incoming damage.",
        "cleanse":"Removes negative effects and restores HP.",
        "percent_damage":"Deals damage based on a percentage of enemy maximum HP.",
        "mythic":"Deals massive damage and applies vulnerability.",
    }.get(effect, f"Uses the {effect.replace('_',' ')} combat effect.")

# ---------------------------------------------------------------------------
# Subclass skill kits
# Every specialization gets six additional active skills.  The parent class
# supplies the foundation; the subclass kit changes the way that foundation is
# expressed so choosing a subclass matters in combat as well as on the stat
# sheet.
SUBCLASS_SKILL_EFFECTS = {
    "vanguard":["def_buff","heavy","barrier","counter","armor_break","team_buff"],
    "blade_master":["multi","heavy","bleed","armor_break","crit","execute"],
    "berserk_lord":["heavy","bleed","sacrifice","lifesteal","emergency","execute"],
    "iron_guardian":["barrier","def_buff","counter","heavy","team_buff","true_damage"],
    "arcane_knight":["damage","mana_burst","barrier","burn","armor_break","true_damage"],
    "fire_mage":["burn","aoe","heavy","vulnerability","mana_burst","ultimate"],
    "frost_mage":["freeze","barrier","delayed","vulnerability","mana_drain","ultimate"],
    "battle_mage":["damage","heavy","mana_burst","lifesteal","armor_break","execute"],
    "shadow_assassin":["lifesteal","bleed","dodge","mark","execute","true_damage"],
    "nightblade":["multi","bleed","poison","dodge","lifesteal","execute"],
    "sniper":["mark","true_damage","heavy","delayed","execute","ultimate"],
    "beast_master":["pet_boost","mark","damage","team_buff","execute","ultimate"],
    "holy_priest":["heal","barrier","cleanse","team_buff","dispel","ultimate"],
    "battle_cleric":["damage","heal","barrier","attack_buff","lifesteal","execute"],
    "storm_druid":["burn","freeze","terrain","aoe","delayed","ultimate"],
    "wild_druid":["lifesteal","heal","terrain","def_buff","aoe","execute"],
    "dragon_monk":["combo","multi","counter","attack_buff","lifesteal","execute"],
    "shadow_monk":["dodge","counter","multi","combo","true_damage","execute"],
    "minstrel":["heal","team_buff","dodge","mana_drain","cleanse","ultimate"],
    "war_chanter":["attack_buff","team_buff","heavy","vulnerability","combo","ultimate"],
    "bone_lord":["summon","aoe","curse","barrier","sacrifice","ultimate"],
    "soul_reaper":["lifesteal","bleed","mark","curse","execute","true_damage"],
    "demon_pact":["sacrifice","lifesteal","curse","burn","vulnerability","ultimate"],
    "void_caller":["curse","vulnerability","true_damage","delayed","mana_drain","ultimate"],
    "bombardier":["aoe","burn","armor_break","delayed","execute","ultimate"],
    "transmuter":["resource","heal","dispel","mana_burst","vulnerability","ultimate"],
    "artificer":["summon","barrier","armor_break","mark","aoe","ultimate"],
    "machinist":["damage","delayed","mark","barrier","true_damage","ultimate"],
    "fencer":["counter","multi","dodge","mark","true_damage","execute"],
    "champion":["heavy","combo","attack_buff","def_buff","lifesteal","ultimate"],
    "dragoon":["heavy","multi","dodge","armor_break","execute","ultimate"],
    "templar":["def_buff","barrier","heal","counter","attack_buff","true_damage"],
    "crusader":["heavy","attack_buff","lifesteal","burn","execute","ultimate"],
    "aegis_knight":["barrier","def_buff","counter","team_buff","heal","ultimate"],
    "dawnbringer":["heal","team_buff","cleanse","barrier","lifesteal","ultimate"],
    "blood_saint":["lifesteal","heal","bleed","attack_buff","execute","ultimate"],
    "spellbreaker":["armor_break","true_damage","silence","vulnerability","mana_drain","execute"],
    "arcane_fencer":["damage","burn","mana_burst","counter","true_damage","ultimate"],
    "beastcaller":["pet_boost","summon","mark","team_buff","execute","ultimate"],
    "conjurer":["summon","barrier","chain","aoe","mana_drain","ultimate"],
    "eidolon_master":["summon","pet_boost","barrier","vulnerability","true_damage","ultimate"],
}

_SUBCLASS_SKILL_WORDS = {
    "damage":"Arc","heavy":"Ruin","multi":"Sevenfold Petals","bleed":"Rend","heal":"Mending Light",
    "def_buff":"Aegis","attack_buff":"Ascension","armor_break":"Sunder","poison":"Venom",
    "burn":"Infernal Sonata","freeze":"Frostbind","lifesteal":"Sanguine Feast","mana_drain":"Soul Siphon",
    "dodge":"Veilstep","counter":"Mirrorsteel Reprisal","barrier":"Bulwark","vulnerability":"Expose",
    "execute":"Final Rupture","true_damage":"Piercing Edge","ultimate":"Apotheosis","signature":"Ascension",
    "focus":"Deadeye","mark":"Predator's Sigil","silence":"Silence","curse":"Hex",
    "terrain":"Domain","resource":"Essence Flow","stamina":"Second Breath","mana_burst":"Mana Burst",
    "delayed":"Delayed Ruin","sacrifice":"Blood Price","emergency":"Last Stand","combo":"Momentum",
    "chain":"Chainstrike","team_buff":"War Hymn","pet_boost":"Bondcall","summon":"Summoning",
    "aoe":"Tempest","dispel":"Purification","cleanse":"Cleansing Light","random":"Catalyst",
}

def _build_subclass_skills():
    result={}
    for subclass, data in SUBCLASSES.items():
        parent=data[0]
        effects=SUBCLASS_SKILL_EFFECTS.get(subclass, CLASS_SKILL_EFFECTS.get(parent, ["damage","heavy","def_buff","attack_buff","lifesteal","ultimate"])[:6])
        title=subclass.replace("_"," ").title()
        skills=[]
        for i,effect in enumerate(effects[:6],1):
            word=_SUBCLASS_SKILL_WORDS.get(effect,effect.replace("_"," ").title())
            # Names describe the mechanic while still sounding like abilities
            # from a fantasy RPG rather than generic "Skill 1" entries.
            name=f"{title}'s {word}"
            skills.append({
                "key":f"sub_{subclass}_{i}",
                "name":name,
                "cost":SKILL_COSTS[min(i+1,len(SKILL_COSTS)-1)],
                "mult":round(0.92 + (i-1)*0.045,3),
                "effect":effect,
                "cooldown":SKILL_COOLDOWNS[min(i+1,len(SKILL_COOLDOWNS)-1)],
                "unlock":max(1, 5 + (i-1)*5),
                "mechanic":word,
                "desc":_skill_effect_text(effect),
                "buff_text":_skill_buff_text(effect),
                "debuff_text":_skill_debuff_text(effect),
                "heal_pct":{"heal":.28,"lifesteal":.34,"ultimate":.08}.get(effect,0),
                "damage_cap":.34 if effect in {"heavy","execute","ultimate","sacrifice","true_damage"} else .30,
                "subclass":subclass,
            })
        result[subclass]=skills
    return result

SUBCLASS_SKILLS = _build_subclass_skills()


def _build_class_skills():
    result = {}
    for class_name in list(CLASSES) + ["void_knight","chronomancer","dragon_lord","soul_reaper"]:
        names = _CLASS_SKILL_NAMES.get(class_name, [])
        if not names:
            # Secret classes use distinct names instead of generic Skill N labels.
            prefixes={"void_knight":"Void Knight","chronomancer":"Chronomancer","dragon_lord":"Dragon Lord","soul_reaper":"Soul Reaper"}
            base=prefixes.get(class_name,class_name.replace('_',' ').title())
            names=[f"{base} Technique {i}" for i in range(1,21)]
        effects=CLASS_SKILL_EFFECTS.get(class_name, CLASS_SKILL_EFFECTS.get("warrior"))
        # Keep 20 stable keys. Slots 1-12 are class-defining; 13-20 remain
        # available as secondary tools for existing characters.
        skills=[]
        for i in range(20):
            if i < len(effects):
                effect=effects[i]
            else:
                # Give each class a different secondary toolkit instead of the
                # same generic eight skills. The rotation is deterministic so
                # saves remain stable across restarts.
                class_index=list(CLASSES).index(class_name) if class_name in CLASSES else 20 + ["void_knight","chronomancer","dragon_lord","soul_reaper"].index(class_name)
                used=set(effects)
                candidates=CLASS_SKILL_EXTRA_POOL[class_index % len(CLASS_SKILL_EXTRA_POOL):] + CLASS_SKILL_EXTRA_POOL[:class_index % len(CLASS_SKILL_EXTRA_POOL)]
                extras=[e for e in candidates if e not in used]
                effect=extras[i-len(effects)]
            name={
                "damage":"Cinderfang","heavy":"Titanfall","multi":"Twin Requiem","bleed":"Crimson Rend",
                "heal":"Lumen's Grace","def_buff":"Aegis of the Dawn","attack_buff":"Warborn Ascension",
                "armor_break":"Sunderer's Oath","poison":"Venomveil","burn":"Emberwake","freeze":"Frostwraith",
                "lifesteal":"Sanguine Requiem","mana_drain":"Aether Siphon","dodge":"Phantom Step",
                "counter":"Oathbound Reprisal","barrier":"Seraphic Aegis","vulnerability":"Mark of Ruin",
                "execute":"Eclipse Execution","true_damage":"Worldrend","ultimate":"Cataclysm Aria",
                "signature":"Sovereign's Verdict","stance":"Eclipse Stance","focus":"Keenstar Focus",
                "mark":"Hunter's Sigil","silence":"Gravebind","curse":"Doomweaver's Hex",
                "terrain":"Realmshaper's Decree","resource":"Astral Resurgence","stamina":"Warrior's Vigor",
                "mana_burst":"Aetherflare","delayed":"Doomclock","sacrifice":"Blood Price",
                "emergency":"Desperate Ascension","combo":"Rising Tempest","chain":"Myriad Blades",
                "team_buff":"Banner of Valor","pet_boost":"Beastlord's Bond","summon":"Phantom Conjuration",
                "aoe":"Starfall Cataclysm","dispel":"Nullsong","random":"Fateweaver's Gambit"
            }.get(effect,names[i] if i < len(names) else f"{class_name.replace('_',' ').title()} Technique {i+1}")
            mechanic_name={
                "damage":"Core Strike","heavy":"Power Blow","multi":"Rapid Sequence","bleed":"Bleeding Wound","heal":"Recovery","def_buff":"Defensive Stance","attack_buff":"Offensive Stance","armor_break":"Defense Break","poison":"Poison","burn":"Burn","freeze":"Freeze","lifesteal":"Merciful Requiem","mana_drain":"Aether Siphon","dodge":"Evasive Step","counter":"Counter Stance","barrier":"Barrier","vulnerability":"Expose Weakness","execute":"Final Rupture","true_damage":"Piercing Damage","ultimate":"Signature Finisher","summon":"Summon","pet_boost":"Companion Empowerment","chain":"Chain Attack","team_buff":"Battle Rally","defend":"Guard","sacrifice":"Blood Price","emergency":"Desperation","attack_buff":"Rage Surge","combo":"Combo Technique","mana_burst":"Mana Burst","curse":"Curse","silence":"Silence","delayed":"Delayed Strike","stance":"Adaptive Stance","terrain":"Terrain Control","dispel":"Dispel","resource":"Resource Surge","random":"Volatile Mixture","dodge":"Haste","signature":"Class Signature","aoe":"Area Strike","recovery":"Recovery Pulse","stamina":"Stamina Surge","mark":"Target Mark","focus":"Focus"}.get(effect,effect.replace('_',' ').title())
            mechanic_desc={
                "summon":"Calls a class-specific companion effect for sustained pressure.","pet_boost":"Empowers your companion and refreshes its combat rhythm.","chain":"Builds pressure from consecutive attacks.","team_buff":"Raises offensive and defensive combat performance.","sacrifice":"Spend HP to gain stronger damage.","emergency":"Becomes stronger when you are badly wounded.","attack_buff":"Converts momentum into stronger offense.","combo":"Scales with consecutive successful techniques.","mana_burst":"Deals damage while refunding some mana.","curse":"Applies a lingering vulnerability curse.","silence":"Disrupts enemy abilities for a short duration.","delayed":"Stores damage and detonates it later.","stance":"Chooses an offensive or defensive stance based on HP.","terrain":"Changes the battlefield to create an opening.","dispel":"Removes enemy advantages and punishes them.","resource":"Restores combat resources while attacking.","random":"A volatile effect with a controlled random outcome.","dodge":"Improves combat tempo and evasion.","signature":"A high-impact class-defining finisher.","aoe":"A wider attack pattern with capped damage.","stamina":"Restores stamina while maintaining pressure.","mark":"Marks the target for stronger follow-up attacks.","focus":"Improves critical consistency for a short window.",}.get(effect, f"A {class_name.replace('_',' ')}-specific combat technique.")
            mult=round(.78 + min(i,11)*.035,3)
            if effect in {"heavy","sacrifice","ultimate","signature"}: mult=1.16 if effect=="heavy" else (1.34 if effect=="sacrifice" else (1.48 if effect=="ultimate" else 1.42))
            elif effect=="multi": mult=.48
            elif effect in {"heal","def_buff","attack_buff","dodge","counter","barrier","team_buff","defend","pet_boost","resource","stamina","focus"}: mult=.35
            elif effect in {"true_damage","execute"}: mult=1.05 + min(i,11)*.01
            heal_pct={"heal":.24,"lifesteal":.30,"ultimate":.08,"recovery":.34}.get(effect,0)
            damage_cap=.28 if effect not in {"heavy","execute","ultimate","signature","sacrifice"} else .34
            skills.append({"key":f"skill_{i+1}","name":name,"cost":SKILL_COSTS[i],"mult":mult,"effect":effect,"cooldown":SKILL_COOLDOWNS[i],"unlock":SKILL_UNLOCK_LEVELS[i],"mechanic":mechanic_name,"desc":_skill_effect_text(effect),"buff_text":_skill_buff_text(effect),"debuff_text":_skill_debuff_text(effect),"heal_pct":heal_pct,"damage_cap":damage_cap})
        result[class_name]=skills
    return result


SKILLS = _build_class_skills()

async def _migrate_skill_loadouts(db_path):
    """Remove obsolete skill keys from saved loadouts after the class-kit rebalance."""
    try:
        async with aiosqlite.connect(db_path) as db:
            cur=await db.execute("SELECT DISTINCT class_name FROM rpg_players")
            classes={r[0] for r in await cur.fetchall()}
            for cls in classes:
                valid={x["key"] for x in SKILLS.get(cls,[])} | {x["key"] for skills in SUBCLASS_SKILLS.values() for x in skills}
                if not valid: continue
                cur=await db.execute("SELECT guild_id,user_id,slot,skill_key FROM rpg_skill_loadout")
                rows=await cur.fetchall()
                for guild_id,user_id,slot,key in rows:
                    if key not in valid:
                        await db.execute("DELETE FROM rpg_skill_loadout WHERE guild_id=? AND user_id=? AND slot=?",(guild_id,user_id,slot))
            await db.commit()
    except Exception:
        # Migration is best-effort; normal startup must remain safe for old DBs.
        pass


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
    "common_egg": ("Common Egg", "Common", 150),
    "forest_egg": ("Forest Egg", "Uncommon", 300),
    "moon_egg": ("Moon Egg", "Rare", 600),
    "ocean_egg": ("Ocean Egg", "Rare", 700),
    "dragon_egg": ("Dragon Egg", "Epic", 1200),
    "celestial_egg": ("Celestial Egg", "Legendary", 3000),
}

# Every egg has its own exclusive five-pet pool. Pets never appear in more
# than one egg, so the egg-pets command can clearly show where each species is found.
PET_EGG_POOLS = {
    "common_egg": ["Wolf Pup","Rabbit","Fox","Cat","Hedgehog"],
    "forest_egg": ["Forest Wolf","Hawk","Dire Hound","Moss Turtle","Green Sprite"],
    "moon_egg": ["Moon Cat","Moon Fox","Spirit Fox","Night Owl","Lunar Lynx"],
    "ocean_egg": ["Tide Otter","Coral Crab","Sea Serpent","Pearl Koi","Storm Ray"],
    "dragon_egg": ["Dragon Whelp","Frost Drake","Ember Drake","Thunder Wyvern","Royal Griffin"],
    "celestial_egg": ["Phoenix","Elder Dragon","Celestial Lion","Astral Unicorn","Star Guardian"],
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
    "hunter": {"name":"Predator's Sigil","desc":"Improves damage against marked targets.","stat":"atk","pct":2,"max_level":4},
}


# Which enchantments are legal for each equipment slot.  Enchantments are a
# separate progression layer; none are baked into an item's name or base stats.
ENCHANTMENT_COMPATIBILITY = {
    "weapon": {"sharpness", "precision", "vampiric", "flamebrand", "frostbind", "hunter", "swiftness", "soulbound"},
    "armor": {"fortitude", "bulwark", "swiftness", "manaweave", "frostbind", "warding", "soulbound"},
    "offhand": {"fortitude", "bulwark", "precision", "manaweave", "swiftness", "warding", "soulbound"},
    "accessory": {"sharpness", "fortitude", "precision", "manaweave", "swiftness", "warding", "soulbound", "hunter", "vampiric"},
    "ring": {"precision", "manaweave", "swiftness", "soulbound", "vampiric", "hunter", "flamebrand", "frostbind"},
    "amulet": {"fortitude", "manaweave", "warding", "soulbound", "vampiric", "hunter", "flamebrand", "frostbind"},
    "relic": set(ENCHANTMENTS),
}

def compatible_enchantments(item: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Return the enchantments that can be applied to this base item."""
    allowed = ENCHANTMENT_COMPATIBILITY.get(item.get("slot"), set())
    return [(key, ENCHANTMENTS[key]) for key in ENCHANTMENTS if key in allowed]

PET_SPECIES = {
    "Wolf Pup": {"rarity": "common", "atk": 2, "def": 2, "hp": 5, "spd": 2, "crit": 1, "ability": "Howl", "role": "damage"},
    "Rabbit": {"rarity": "common", "atk": 1, "def": 1, "hp": 3, "spd": 4, "crit": 2, "ability": "Lucky Hop", "role": "crit"},
    "Fox": {"rarity": "common", "atk": 2, "def": 1, "hp": 3, "spd": 3, "crit": 3, "ability": "Foxfire", "role": "damage"},
    "Fox Spirit": {"rarity": "uncommon", "atk": 4, "def": 2, "hp": 6, "spd": 4, "crit": 4, "ability": "Spirit Flame", "role": "damage"},
    "Cat": {"rarity": "common", "atk": 1, "def": 2, "hp": 4, "spd": 3, "crit": 2, "ability": "Pounce", "role": "damage"},
    "Forest Wolf": {"rarity": "uncommon", "atk": 4, "def": 3, "hp": 8, "spd": 3, "crit": 2, "ability": "Pack Howl", "role": "damage"},
    "Moon Fox": {"rarity": "uncommon", "atk": 4, "def": 2, "hp": 6, "spd": 4, "crit": 4, "ability": "Lunaris Bloom", "role": "damage"},
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
    "Lunaris Bloom":"Deals lunar magic damage and restores a small amount of HP.",
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
PET_SPECIES.update({
    "Hedgehog":{"rarity":"common","atk":1,"def":3,"hp":6,"spd":2,"crit":1,"ability":"Spiky Guard","role":"tank"},
    "Moss Turtle":{"rarity":"uncommon","atk":2,"def":5,"hp":12,"spd":1,"crit":0,"ability":"Moss Shell","role":"tank"},
    "Green Sprite":{"rarity":"uncommon","atk":3,"def":2,"hp":7,"spd":5,"crit":3,"ability":"Verdant Spark","role":"heal"},
    "Night Owl":{"rarity":"rare","atk":5,"def":3,"hp":9,"spd":7,"crit":6,"ability":"Night Sight","role":"crit"},
    "Lunar Lynx":{"rarity":"rare","atk":6,"def":4,"hp":11,"spd":6,"crit":7,"ability":"Lunar Pounce","role":"damage"},
    "Tide Otter":{"rarity":"rare","atk":5,"def":5,"hp":13,"spd":5,"crit":3,"ability":"Tidal Guard","role":"tank"},
    "Coral Crab":{"rarity":"rare","atk":4,"def":8,"hp":16,"spd":2,"crit":1,"ability":"Coral Armor","role":"tank"},
    "Sea Serpent":{"rarity":"epic","atk":9,"def":6,"hp":19,"spd":6,"crit":5,"ability":"Aqua Coil","role":"damage"},
    "Pearl Koi":{"rarity":"rare","atk":4,"def":5,"hp":14,"spd":5,"crit":5,"ability":"Pearl Blessing","role":"heal"},
    "Storm Ray":{"rarity":"epic","atk":10,"def":5,"hp":18,"spd":9,"crit":7,"ability":"Thunder Current","role":"damage"},
    "Frost Drake":{"rarity":"epic","atk":10,"def":7,"hp":21,"spd":5,"crit":5,"ability":"Glacial Breath","role":"damage"},
    "Ember Drake":{"rarity":"epic","atk":11,"def":6,"hp":20,"spd":5,"crit":6,"ability":"Inferno Breath","role":"damage"},
    "Thunder Wyvern":{"rarity":"epic","atk":12,"def":5,"hp":19,"spd":8,"crit":8,"ability":"Thunder Dive","role":"damage"},
    "Astral Unicorn":{"rarity":"legendary","atk":12,"def":11,"hp":30,"spd":8,"crit":9,"ability":"Astral Grace","role":"heal"},
    "Star Guardian":{"rarity":"legendary","atk":15,"def":14,"hp":40,"spd":6,"crit":8,"ability":"Starlight Ward","role":"tank"},
})
for _pet in PET_SPECIES.values():
    _pet["ability_desc"] = PET_ABILITY_DESCRIPTIONS.get(_pet.get("ability",""), "A passive companion ability that helps during battle.")


def _build_expanded_items():
    """Build a compact, curated item catalogue.

    Eggs and pets are intentionally kept in PET_EGGS/PET_SPECIES and are NOT
    registered as normal items.  Equipment is generated from a small number of
    meaningful base families instead of thousands of cosmetic duplicates.
    """
    generated = {}

    level_req = {"common":1, "uncommon":8, "rare":18, "epic":32, "legendary":50, "mythic":72}
    rarity_mult = {"common":1.0, "uncommon":1.2, "rare":1.5, "epic":2.0, "legendary":3.0, "mythic":4.5}

    materials = [
        ("bronze","Bronze","common"), ("iron","Iron","common"),
        ("steel","Steel","uncommon"), ("silver","Silver","rare"),
        ("gold","Gold","rare"), ("mithril","Mithril","epic"),
        ("dragonbone","Dragonbone","legendary"), ("aetherium","Aetherium","mythic"),
    ]

    weapons = [
        ("sword","Sword",10,0), ("greatsword","Greatsword",14,0),
        ("katana","Katana",11,2), ("spear","Spear",10,1),
        ("dagger","Dagger",7,3), ("bow","Bow",9,2),
        ("staff","Staff",8,0), ("scythe","Scythe",13,1),
        ("gauntlet","Gauntlets",10,1), ("wand","Wand",7,2),
    ]
    armor = [
        ("leather","Leather Armor",6,8), ("chain","Chainmail",8,12),
        ("plate","Plate Armor",13,18), ("mage","Mage Robe",4,16),
        ("ranger","Ranger Leathers",7,10), ("cleric","Cleric Vestments",5,20),
        ("dragon","Dragon Armor",16,28), ("celestial","Celestial Armor",20,35),
    ]
    offhands = [
        ("buckler","Buckler",6,8), ("kite","Kite Shield",9,14),
        ("greatshield","Greatshield",14,24), ("spellbook","Spellbook",4,18),
        ("totem","Totem",5,15), ("focus","Casting Focus",4,20),
    ]
    accessories = [
        ("ring","Ring",4), ("amulet","Amulet",5), ("belt","War Belt",6),
        ("cloak","Cloak",5), ("boots","Boots",4), ("gloves","Gloves",5),
        ("talisman","Talisman",5), ("medallion","Medallion",6),
    ]

    for m_i,(mk,mname,rarity) in enumerate(materials):
        mult = rarity_mult[rarity]
        for w_i,(wk,wname,base,crit) in enumerate(weapons):
            key=f"{mk}_{wk}"
            generated[key] = {
                "name":f"{mname} {wname}", "slot":"weapon", "rarity":rarity,
                "atk":int(base*mult)+m_i, "crit":crit if wk in {"katana","dagger","bow","wand"} else 0,
                "price":int(100*base*mult)+m_i*35, "level_req":level_req[rarity],
                "enchant_slots":1+min(4,list(RARITIES).index(rarity)),
                "family":wk,
            }
        for a_i,(ak,aname,base,hp) in enumerate(armor):
            key=f"{mk}_{ak}_armor"
            generated[key] = {
                "name":f"{mname} {aname}", "slot":"armor", "rarity":rarity,
                "def":int(base*mult)+m_i//2, "hp":int(hp*mult)+m_i*2,
                "price":int(125*base*mult)+m_i*40, "level_req":level_req[rarity],
                "enchant_slots":1+min(4,list(RARITIES).index(rarity)), "family":ak,
            }
        for o_i,(ok,oname,base,hp) in enumerate(offhands):
            key=f"{mk}_{ok}_offhand"
            generated[key] = {
                "name":f"{mname} {oname}", "slot":"offhand", "rarity":rarity,
                "def":int(base*mult)+1, "hp":int(hp*mult),
                "mp":int(base*mult*1.5) if ok in {"spellbook","totem","focus"} else 0,
                "price":int(110*base*mult), "level_req":level_req[rarity],
                "enchant_slots":1+min(4,list(RARITIES).index(rarity)),
            }
        for a_i,(ak,aname,base) in enumerate(accessories):
            key=f"{mk}_{ak}_accessory"
            slot=ak if ak in {"ring","amulet"} else "accessory"
            generated[key] = {
                "name":f"{mname} {aname}", "slot":slot, "rarity":rarity,
                "atk":int(base*mult/2), "def":int(base*mult/2),
                "hp":int(base*mult), "spd":max(1,int(base*mult/3)),
                "crit":max(0,int(base/3)), "price":int(200*base*mult),
                "level_req":level_req[rarity],
                "enchant_slots":1+min(4,list(RARITIES).index(rarity)),
            }

    relics = [
        ("explorers_compass","Explorer's Compass","uncommon",{"spd":3}),
        ("guild_crest","Guild Crest","rare",{"hp":20,"def":3}),
        ("hunters_charm","Hunter's Charm","rare",{"atk":4,"crit":3}),
        ("royal_signet","Royal Signet","epic",{"hp":25,"atk":5}),
        ("void_compass","Void Compass","legendary",{"mp":25,"spd":6,"crit":4}),
        ("dragon_heart_shard","Dragon Heart Shard","legendary",{"hp":40,"atk":7}),
        ("world_tree_seed","World Tree Seed","mythic",{"hp":60,"def":8,"mp":30}),
        ("horizon_relic","Horizon Relic","mythic",{"atk":10,"def":10,"spd":5,"crit":5}),
    ]
    for key,name,rarity,stats in relics:
        generated["relic_"+key]={"name":name,"slot":"relic","rarity":rarity,
                                 **stats,"price":500*list(RARITIES).index(rarity)+500,
                                 "level_req":level_req[rarity],
                                 "enchant_slots":1+min(4,list(RARITIES).index(rarity))}

    potions = [
        ("small_health_potion","Small Health Potion","common",45,0),
        ("health_potion","Health Potion","uncommon",90,0),
        ("greater_health_potion","Greater Health Potion","rare",180,0),
        ("superior_health_potion","Superior Health Potion","epic",350,0),
        ("small_mana_potion","Small Mana Potion","common",0,30),
        ("mana_potion","Mana Potion","uncommon",0,60),
        ("greater_mana_potion","Greater Mana Potion","rare",0,100),
        ("superior_mana_potion","Superior Mana Potion","epic",0,170),
        ("full_restore_elixir","Full Restore Elixir","legendary",300,250),
        ("stamina_tonic","Stamina Tonic","uncommon",35,0),
        ("arcane_tonic","Arcane Tonic","rare",0,55),
    ]
    for key,name,rarity,heal,mana in potions:
        data={"name":name,"slot":"consumable","rarity":rarity,"price":80*level_req[rarity]//2}
        if key=="stamina_tonic": data["stamina"]=35
        else:
            data["heal"],data["mana"]=heal,mana
        generated[key]=data

    foods = [
        "Honey Bread","Berry Pie","Hearty Stew","Grilled Fish","Roasted Meat","Mushroom Soup",
        "Spicy Curry","Royal Feast","Traveler's Ration","Sweet Bun","Apple Tart","Moonberry Jam",
        "Dragon Steak","Phoenix Fruit","Crystal Melon","Seafood Platter","Mountain Cheese","Golden Rice",
        "Herbal Tea","Spiced Tea","Campfire Skewer","Meat Pie","Fish Sandwich","Festival Cake",
    ]
    for n,name in enumerate(foods):
        key="food_"+name.lower().replace(" ","_").replace("'","")
        generated[key]={"name":name,"slot":"food","rarity":"common" if n<12 else "uncommon",
                        "heal":20+n*3,"stamina":8+(n%5)*3,"price":30+n*10}

    material_names = [
        "Oak Log","Iron Ore","Coal","Silver Ore","Gold Ore","Mithril Ore","Dragon Scale",
        "Phoenix Feather","Moon Crystal","Sun Shard","Shadow Essence","Beast Fang","Wolf Claw",
        "Goblin Ear","Orc Tusk","Slime Core","Wraith Dust","Demon Horn","Angel Feather",
        "Fae Pollen","Ancient Bone","Star Fragment","Void Crystal","Sea Pearl","Coral","Amber",
        "Ruby","Sapphire","Emerald","Topaz","Obsidian","Quartz","Leather Scrap","Silk Thread",
        "Magic Fiber","Ashwood","Frostwood","Red Herb","Blue Herb","Golden Herb","Nightshade",
        "Sunflower Seed","Reinforcement Core","Dragon Trophy",
    ]
    for n,name in enumerate(material_names):
        key="mat_"+name.lower().replace(" ","_")
        rarity="common" if n<16 else ("uncommon" if n<28 else ("rare" if n<38 else "epic"))
        generated[key]={"name":name,"slot":"material","rarity":rarity,"price":20+n*15}
    # Preserve old material keys used by existing recipes/upgrades.
    generated.update({
        "iron_ore":{"name":"Iron Ore","slot":"material","rarity":"common","price":20},
        "herb":{"name":"Moon Herb","slot":"material","rarity":"common","price":15},
        "wolf_pelt":{"name":"Wolf Pelt","slot":"material","rarity":"common","price":18},
        "arcane_shard":{"name":"Arcane Shard","slot":"material","rarity":"rare","price":120},
        "reinforcement_core":{"name":"Reinforcement Core","slot":"material","rarity":"rare","price":180},
        "dragon_trophy":{"name":"Dragon Trophy","slot":"material","rarity":"legendary","price":1000},
    })

    ITEMS.update(generated)
    equipment_slots={"weapon","armor","offhand","accessory","ring","amulet","relic"}
    for data in ITEMS.values():
        if data.get("slot") in equipment_slots:
            rarity=data.get("rarity","common")
            data["enchant_slots"]=max(1,int(data.get("enchant_slots",
                1+min(4,list(RARITIES).index(rarity) if rarity in RARITIES else 0))))


_build_expanded_items()
for _key, (_name, _rarity, _price) in GACHA_CHEST_ITEMS.items():
    ITEMS[_key]={"name":_name,"slot":"chest","rarity":_rarity,"price":_price,"gacha_chest":True,"level_req":rarity_level.get(_rarity,1) if "rarity_level" in globals() else 1}
SHOP_ITEMS = [k for k,v in ITEMS.items() if v.get("price") and not v.get("pet_egg") and not v.get("pet") and v.get("slot") not in {"egg"}]

# Crafted utility items are intentionally modest: they improve uptime without replacing rest, combat, or gear.
ITEMS.update({
    "stamina_tonic":{"name":"Stamina Tonic","slot":"consumable","rarity":"uncommon","stamina":35,"price":90},
    "hearty_stew":{"name":"Hearty Stew","slot":"food","rarity":"common","heal":45,"stamina":20,"price":70},
    "arcane_tonic":{"name":"Arcane Tonic","slot":"consumable","rarity":"uncommon","mana":55,"price":110},
    "reinforcement_core":{"name":"Reinforcement Core","slot":"material","rarity":"rare","price":180},
})

RECIPES = {
    # Consumables
    "life_potion":{"iron_ore":1,"herb":2,"_meta":{"level_req":1,"gold_fee":5,"xp":10}},
    "mana_potion":{"herb":3,"arcane_shard":1,"_meta":{"level_req":2,"gold_fee":8,"xp":12}},
    "small_health_potion":{"herb":2,"_meta":{"level_req":1,"gold_fee":5,"xp":8}},
    "greater_health_potion":{"health_potion":2,"_meta":{"level_req":10,"gold_fee":20,"xp":20}},
    "superior_health_potion":{"greater_health_potion":2,"_meta":{"level_req":25,"gold_fee":45,"xp":35}},
    "small_mana_potion":{"herb":2,"_meta":{"level_req":1,"gold_fee":5,"xp":8}},
    "greater_mana_potion":{"mana_potion":2,"arcane_shard":1,"_meta":{"level_req":12,"gold_fee":25,"xp":24}},
    "superior_mana_potion":{"greater_mana_potion":2,"arcane_shard":2,"_meta":{"level_req":30,"gold_fee":55,"xp":40}},
    "stamina_tonic":{"herb":2,"wolf_pelt":1,"_meta":{"level_req":2,"gold_fee":10,"xp":12}},
    "arcane_tonic":{"herb":3,"arcane_shard":1,"_meta":{"level_req":8,"gold_fee":20,"xp":20}},
    "hearty_stew":{"food_grilled_fish":2,"herb":1,"_meta":{"level_req":3,"gold_fee":10,"xp":15}},
    "food_grilled_fish":{"mat_oak_log":1,"mat_sea_pearl":1,"_meta":{"level_req":1,"gold_fee":5,"xp":8}},
    "food_mushroom_soup":{"mat_oak_log":1,"herb":2,"_meta":{"level_req":2,"gold_fee":6,"xp":9}},
    "food_roasted_meat":{"wolf_pelt":1,"herb":1,"_meta":{"level_req":3,"gold_fee":8,"xp":10}},
    # Core gear
    "steel_blade":{"iron_ore":5,"arcane_shard":1,"_meta":{"level_req":5,"gold_fee":70,"xp":40}},
    "guardian_shield":{"iron_ore":7,"wolf_pelt":2,"_meta":{"level_req":7,"gold_fee":90,"xp":45}},
    "reinforcement_core":{"iron_ore":4,"arcane_shard":2,"_meta":{"level_req":10,"gold_fee":120,"xp":55}},
    "dragon_trophy":{"arcane_shard":5,"iron_ore":8,"_meta":{"level_req":25,"gold_fee":300,"xp":90}},
}
# A broad but finite crafting catalogue: every listed recipe makes a real base
# item, while the remaining catalogue is obtained through drops/shop/world loot.
_recipe_tiers={"bronze":(1,1),"iron":(2,2),"steel":(8,4),"silver":(18,6),
               "gold":(18,8),"mithril":(32,10),"dragonbone":(50,14),"aetherium":(72,20)}
_recipe_mats=["mat_iron_ore","mat_coal","mat_silver_ore","mat_gold_ore","mat_mithril_ore",
              "mat_dragon_scale","mat_moon_crystal","mat_star_fragment","mat_void_crystal"]
# 40+ gear recipes: selected signature weapons, armor and accessories rather
# than every cosmetic combination.
for _idx,(_mk,_req) in enumerate(_recipe_tiers.items()):
    for _wk in ("sword","greatsword","katana","spear","bow"):
        _key=f"{_mk}_{_wk}"
        if _key in ITEMS:
            _mat=_recipe_mats[min(_idx+1,len(_recipe_mats)-1)]
            RECIPES[_key]={_mat:_req[0]+2,"mat_coal":max(1,_req[0]//2),
                           "_meta":{"level_req":_req[0],"gold_fee":_req[1]*8,"xp":18+_idx*8}}
    for _ak in ("leather","chain","plate","mage","ranger"):
        _key=f"{_mk}_{_ak}_armor"
        if _key in ITEMS:
            _mat=_recipe_mats[min(_idx+1,len(_recipe_mats)-1)]
            RECIPES[_key]={_mat:_req[0]+3,"mat_leather_scrap":2+_idx%3,
                           "_meta":{"level_req":_req[0],"gold_fee":_req[1]*10,"xp":20+_idx*8}}
    for _ak in ("ring","amulet","belt"):
        _key=f"{_mk}_{_ak}_accessory"
        if _key in ITEMS:
            _mat=_recipe_mats[min(_idx+1,len(_recipe_mats)-1)]
            RECIPES[_key]={_mat:max(1,_req[0]),"mat_silk_thread":2+_idx%2,
                           "_meta":{"level_req":_req[0],"gold_fee":_req[1]*6,"xp":15+_idx*7}}
# Fix the few recipes whose historical material key is an alias.
RECIPES["steel_blade"]={"iron_ore":5,"arcane_shard":1,"_meta":{"level_req":5,"gold_fee":70,"xp":40}}
RECIPES["guardian_shield"]={"iron_ore":7,"wolf_pelt":2,"_meta":{"level_req":7,"gold_fee":90,"xp":45}}



# ---------------------------------------------------------------------------
# Phase 2 — Economy / gear progression
# ---------------------------------------------------------------------------
# Set bonuses are intentionally modest. A set should reward commitment without
# making mixed builds obsolete.
SET_FOCUS = {
    "atk": "Attack", "defense": "Defense", "hp": "Vitality", "speed": "Speed", "crit": "Critical Chance"
}
UPGRADE_MAX = 15
UPGRADE_COST_BASE = 350
UPGRADE_MATERIALS = {
    "common": ("iron_ore", 1), "uncommon": ("iron_ore", 2), "rare": ("arcane_shard", 2),
    "epic": ("reinforcement_core", 1), "legendary": ("dragon_trophy", 2), "mythic": ("dragon_trophy", 4),
}


def _intrinsic_count(rarity: str) -> int:
    return {"common": 1, "uncommon": 1, "rare": 2, "epic": 2, "legendary": 3, "mythic": 3}.get(rarity, 1)


def _roll_intrinsics(item: dict[str, Any]) -> dict[str, Any]:
    """Roll per-instance properties once; they are never re-rolled by upgrades."""
    rarity = item.get("rarity", "common")
    pool = [
        ("atk_pct", random.randint(1, 3), "% ATK"),
        ("def_pct", random.randint(1, 3), "% DEF"),
        ("hp_pct", random.randint(1, 4), "% HP"),
        ("speed_pct", random.randint(1, 3), "% SPD"),
        ("crit_flat", random.randint(1, 2), "Crit"),
    ]
    random.shuffle(pool)
    chosen = pool[:_intrinsic_count(rarity)]
    return {key: value for key, value, _ in chosen}


def _set_key_for_item(item: dict[str, Any], item_key: str) -> str:
    family = str(item.get("family", "")).strip().lower()
    if family:
        return f"{family}_set"
    return ""


def _set_focus(set_key: str) -> str:
    if not set_key:
        return "atk"
    return ("atk", "defense", "hp", "speed", "crit")[sum(ord(c) for c in set_key) % 5]

# Base enemies remain as fallback encounters, while regional mobs below provide
# distinct identities and combat kits for the world map.
ENEMIES = [
    {"name": "Slime", "level": 1, "hp": 45, "atk": 7, "def": 2, "speed": 3, "crit": 4, "xp": 35, "gold": 25, "drops": ["herb"], "abilities": ["acid_spit"]},
    {"name": "Forest Wolf", "level": 2, "hp": 65, "atk": 10, "def": 3, "speed": 9, "crit": 10, "xp": 55, "gold": 38, "drops": ["wolf_pelt", "herb"], "abilities": ["pounce"]},
    {"name": "Goblin Raider", "level": 4, "hp": 95, "atk": 14, "def": 5, "speed": 7, "crit": 7, "xp": 90, "gold": 65, "drops": ["iron_ore"], "abilities": ["dirty_trick"]},
    {"name": "Arcane Wraith", "level": 7, "hp": 145, "atk": 21, "def": 8, "speed": 8, "crit": 12, "xp": 150, "gold": 110, "drops": ["arcane_shard"], "abilities": ["arcane_burst"]},
    {"name": "Ancient Dragonling", "level": 12, "hp": 260, "atk": 32, "def": 14, "speed": 6, "crit": 14, "xp": 300, "gold": 240, "drops": ["arcane_shard", "iron_ore"], "abilities": ["dragon_breath", "frenzy"]},
]

ENEMY_ABILITIES = {
    "acid_spit": {"name":"Acid Spit","type":"damage","mult":0.92,"cooldown":3,"desc":"A corrosive ranged attack."},
    "pounce": {"name":"Pounce","type":"burst","mult":1.28,"cooldown":3,"desc":"A fast leap with increased critical pressure."},
    "dirty_trick": {"name":"Dirty Trick","type":"debuff","mult":0.82,"cooldown":4,"desc":"A cheap strike that reduces the next few incoming defenses."},
    "arcane_burst": {"name":"Arcane Burst","type":"magic","mult":1.18,"cooldown":3,"desc":"A concentrated magical blast."},
    "dragon_breath": {"name":"Dragon Breath","type":"burn","mult":1.10,"cooldown":4,"desc":"Burning breath that leaves a damage-over-time effect."},
    "frenzy": {"name":"Frenzy","type":"buff","mult":0.65,"cooldown":5,"desc":"A strike that increases the monster's attack."},
    "power_strike": {"name":"Vanguard's Wrath","type":"damage","mult":1.35,"cooldown":3,"desc":"A heavy physical attack."},
    "guard": {"name":"Aegis of Stone","type":"guard","mult":0.55,"cooldown":4,"desc":"Raises the monster's defenses temporarily."},
    "regenerate": {"name":"Regenerate","type":"heal","mult":0.55,"cooldown":5,"desc":"Recovers a portion of maximum HP."},
    "venom": {"name":"Venom Spit","type":"poison","mult":0.88,"cooldown":4,"desc":"A poisonous attack that damages the hero over time."},
    "storm": {"name":"Storm Lance","type":"magic","mult":1.22,"cooldown":4,"desc":"A lightning strike with high critical pressure."},
    "soul_drain": {"name":"Soul Drain","type":"drain","mult":0.95,"cooldown":5,"desc":"Deals damage and heals the monster."},
    "void_rend": {"name":"Void Rend","type":"pierce","mult":1.16,"cooldown":4,"desc":"Partially ignores defense."},
}

DUNGEONS = [
    ("Goblin Caves", 1, 3, 140, 90, "A beginner dungeon with three floors."),
    ("Moonlit Ruins", 5, 4, 360, 240, "Ancient ruins filled with arcane enemies."),
    ("Dragonspire", 10, 5, 800, 550, "A dangerous tower ending in a dragon boss."),
    ("Sunken Catacombs", 15, 5, 1250, 850, "Flooded burial halls where drowned kings still rule."),
    ("Obsidian Bastion", 23, 6, 1900, 1300, "A fortress defended by cursed knights and war machines."),
    ("Ashen Caldera", 28, 6, 2700, 1850, "A volcanic dungeon where every chamber burns."),
    ("Crystal Labyrinth", 34, 7, 3900, 2500, "A shifting maze of living crystal and mirrored beasts."),
    ("Thunder Sanctum", 40, 7, 5200, 3400, "A storm temple whose guardians wield living lightning."),
    ("Void Threshold", 46, 8, 7000, 4600, "A broken reality where monsters phase between worlds."),
    ("Dragon Grave", 52, 8, 9000, 6000, "The bones of dead dragons hide an ancient sovereign."),
    ("Eternal Library", 58, 9, 11500, 7600, "Living spells guard forbidden knowledge."),
    ("Time Ruins", 64, 9, 14500, 9500, "Every floor exists in a different moment."),
    ("Godfall Citadel", 70, 10, 18000, 12000, "A fallen divine fortress inhabited by exiled powers."),
    ("Endless Night", 78, 10, 23000, 15500, "A lightless labyrinth where sound attracts predators."),
    ("Reality's Edge", 86, 11, 29000, 19500, "The world fractures more deeply with every floor."),
    ("Origin Sanctum", 94, 12, 37000, 25000, "A primordial dungeon said to predate Horizon itself."),
    ("Horizon Core", 100, 12, 50000, 35000, "The ultimate dungeon at the heart of the world."),
]

DUNGEON_BOSSES = {
    "Goblin Caves": "Goblin Warchief Grakk", "Moonlit Ruins": "The Moonbound Archivist",
    "Dragonspire": "Veyrath, the Young Dragon", "Sunken Catacombs": "Drowned King Marrow",
    "Obsidian Bastion": "General Blacksteel", "Ashen Caldera": "Cindermaw, Lord of Ash",
    "Crystal Labyrinth": "Prismatic Hydra", "Thunder Sanctum": "Raijin's Last Disciple",
    "Void Threshold": "The Reality Eater", "Dragon Grave": "Elder Wyrm Ossuary",
    "Eternal Library": "The Living Grimoire", "Time Ruins": "Chronarch Zero",
    "Godfall Citadel": "The Fallen God-King", "Endless Night": "Nocturne, Eater of Light",
    "Reality's Edge": "The Boundary Walker", "Origin Sanctum": "The First Guardian",
    "Horizon Core": "HORIZON, Worldheart Sovereign",
}

# A readable world graph. Travel remains backward-compatible (players can still
# travel to any level-eligible region), while the graph powers the map/exploration
# systems and shows the natural route between regions.
AREA_CONNECTIONS = {}
_area_order = sorted(AREAS.items(), key=lambda kv: (int(kv[1].get("level", 1)), kv[0]))
for _i, (_key, _data) in enumerate(_area_order):
    AREA_CONNECTIONS.setdefault(_key, set())
    if _i > 0:
        AREA_CONNECTIONS[_key].add(_area_order[_i-1][0])
        AREA_CONNECTIONS[_area_order[_i-1][0]].add(_key)
# Important regional shortcuts make the graph feel like a world rather than a line.
for _a, _c in [
    ("horizon_village", "whispering_woods"), ("whispering_woods", "mossy_grotto"),
    ("silver_coast", "pirate_isles"), ("frostpeak", "frostwood"),
    ("sunken_ruins", "forgotten_catacombs"), ("skyreach", "floating_gardens"),
    ("demon_wastes", "inferno_gate"), ("crystal_desert", "glass_dunes"),
    ("astral_frontier", "dreaming_sea"), ("world_tree", "worldroot_caves"),
    ("dragon_graveyard", "dragon_grave" if "dragon_grave" in AREAS else "dragon_graveyard"),
    ("horizon_core", "origin_sanctum"),
]:
    if _a in AREAS and _c in AREAS:
        AREA_CONNECTIONS.setdefault(_a, set()).add(_c); AREA_CONNECTIONS.setdefault(_c, set()).add(_a)
AREA_CONNECTIONS = {k: sorted(v) for k, v in AREA_CONNECTIONS.items()}

WORLD_BOSS_TEMPLATES = [
    ("forest_ancient", "Ancient Treant Elder", "whispering_woods", 12, "A primordial guardian awakened beneath the oldest roots."),
    ("ember_colossus", "Ember Colossus", "ash_valley", 30, "A walking volcano that feeds on the fire beneath Horizon."),
    ("abyssal_tyrant", "Abyssal Tyrant", "void_border", 55, "A colossal creature that emerged from a crack in reality."),
    ("elder_dragon", "Elder Dragon Avarax", "dragon_graveyard", 75, "An ancient dragon awakened by the bones of its kin."),
    ("fallen_seraph", "Fallen Seraph Elyra", "godfall", 90, "A divine exile whose wings still burn with corrupted light."),
    ("worldroot_colossus", "Worldroot Colossus", "worldroot_caves", 100, "A living mountain born from the roots of the World Tree."),
]

OBJECTIVE_TEMPLATES = {
    "daily": [
        ("daily_hunt","Monster Hunter","Defeat enemies","hunt",5,220,350,"wolf_pelt",2),
        ("daily_explore","Pathfinder","Explore or travel through the world","explore",2,180,280,"herb",3),
        ("daily_dungeon","Dungeon Runner","Clear dungeon floors","dungeon",2,300,450,"arcane_shard",2),
        ("daily_gather","Field Collector","Gather resources","gather",4,180,300,"mat_blue_herb",2),
        ("daily_battle","Battle Ready","Win battles or adventures","hunt",8,280,420,"life_potion",3),
        ("daily_boss","Boss Watcher","Help damage a world boss","worldboss",1,350,550,"mat_void_crystal",1),
        ("daily_pet","Companion Bond","Use your pet in an adventure","hunt",3,240,380,"mat_beast_fang",2),
        ("daily_crafter","Apprentice Crafter","Craft items","gather",2,240,360,"reinforcement_core",1),
        ("daily_merchant","Market Day","Buy or sell items","gather",3,200,320,"mat_gold_ore",2),
        ("daily_quester","Adventurer's Errand","Complete RPG quests","hunt",2,300,450,"arcane_shard",1),
    ],
    "weekly": [
        ("weekly_hunt","Monster Exterminator","Defeat enemies","hunt",30,1600,2400,"arcane_shard",8),
        ("weekly_dungeon","Dungeon Delver","Clear dungeon floors","dungeon",12,2200,3400,"dragon_trophy",2),
        ("weekly_boss","World Challenger","Deal damage to a world boss","worldboss",1,2500,4000,"mat_void_crystal",5),
        ("weekly_explorer","Master Pathfinder","Explore or travel through the world","explore",15,1800,2800,"mat_star_fragment",3),
        ("weekly_gather","Resource Run","Gather resources","gather",30,1500,2300,"mat_mithril_ore",5),
        ("weekly_pet","Beastmaster's Week","Use your pet in adventures","hunt",20,1900,2900,"forest_egg",1),
        ("weekly_craft","Master Artisan","Craft items","gather",10,1800,2700,"reinforcement_core",4),
        ("weekly_quests","Quest Hunter","Complete RPG quests","hunt",8,2000,3000,"arcane_shard",10),
    ],
    "monthly": [
        ("monthly_hunter","Horizon Exterminator","Defeat enemies","hunt",120,7000,11000,"dragon_trophy",5),
        ("monthly_explorer","World Wanderer","Explore or travel through the world","explore",50,6500,10000,"mat_star_fragment",8),
        ("monthly_dungeon","Dungeon Conqueror","Clear dungeon floors","dungeon",40,8500,13000,"mat_void_crystal",10),
        ("monthly_boss","World Boss Nemesis","Help damage world bosses","worldboss",4,9000,14000,"dragon_trophy",8),
        ("monthly_gather","Grand Collector","Gather resources","gather",100,6000,9000,"mat_mithril_ore",10),
        ("monthly_pet","Ultimate Beastmaster","Use your pet in adventures","hunt",75,7000,10500,"moon_egg",1),
        ("monthly_crafter","Grand Artisan","Craft items","gather",30,6500,10000,"reinforcement_core",12),
        ("monthly_quests","Legendary Adventurer","Complete RPG quests","hunt",25,8000,12000,"dragon_trophy",3),
    ],
}

OBJECTIVE_ROTATION_COUNTS={"daily":6,"weekly":5,"monthly":4}

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
    _regional_abilities={
        "town":["power_strike","dirty_trick"], "plains":["pounce","power_strike"], "cave":["venom","guard"],
        "wild":["pounce","power_strike"], "forest":["pounce","regenerate"], "coast":["power_strike","venom"],
        "islands":["power_strike","storm"], "swamp":["venom","regenerate"], "mountain":["guard","power_strike"],
        "cliffs":["storm","pounce"], "canyon":["pounce","power_strike"], "undersea":["venom","soul_drain"],
        "underground":["soul_drain","guard"], "valley":["arcane_burst","venom"], "sky":["storm","regenerate"],
        "fortress":["guard","power_strike"], "volcanic":["dragon_breath","frenzy"], "hell":["dragon_breath","soul_drain"],
        "cursed":["soul_drain","venom"], "desert":["venom","power_strike"], "city":["dirty_trick","arcane_burst"],
        "arena":["power_strike","frenzy"], "temple":["storm","arcane_burst"], "void":["void_rend","soul_drain"],
        "astral":["void_rend","storm"], "ruins":["arcane_burst","guard"], "mythic":["dragon_breath","regenerate"],
        "arcane":["arcane_burst","void_rend"], "graveyard":["soul_drain","venom"], "chaos":["void_rend","frenzy"],
        "temporal":["arcane_burst","dirty_trick"], "divine":["storm","regenerate"], "endgame":["void_rend","frenzy"],
    }.get(_area["type"],["power_strike"])
    _variants=(("Scout",0.82,0.92,1.15,1.10),("Hunter",0.95,1.02,1.28,1.25),("Champion",1.15,1.12,0.92,1.45),("Alpha",1.32,1.22,0.78,1.75))
    for _variant,(_suffix,_hm,_am,_sm,_reward) in enumerate(_variants,1):
        _hp=int((48 + _lvl*18 + _variant*20)*_hm); _atk=int((7 + _lvl*2.1 + _variant*3)*_am); _def=int((2 + _lvl*1.15 + _variant*2)*_am)
        _drops=["herb","iron_ore","arcane_shard"]
        if _lvl>=10:
            _drops += [k for k,v in ITEMS.items() if v.get("slot") in {"material","egg"} and v.get("rarity") in {"rare","epic"}][:2]
        ENEMIES.append({"name":f"{_flavour} {_suffix}","area_key":_area_key,"level":_lvl,"hp":_hp,"atk":_atk,"def":_def,
            "speed":max(1,int((4+_lvl*.42+_variant)*_sm)),"crit":min(28,int(5+_lvl*.18+_variant*2)),
            "xp":int((35+_lvl*24+_variant*18)*_reward),"gold":int((20+_lvl*15+_variant*10)*_reward),
            "drops":list(dict.fromkeys([d for d in _drops if d in ITEMS])),"abilities":_regional_abilities[:2]})

ACHIEVEMENTS = {
    "first_blood": ("First Blood", "Defeat your first enemy.", 100),
    "level_10": ("Rising Hero", "Reach level 10.", 500),
    "collector": ("Collector", "Own 10 different item types.", 300),
    "guild_founder": ("Guild Founder", "Create a guild.", 250),
    "dungeon_clear": ("Dungeon Delver", "Clear your first dungeon.", 400),
    "legend": ("Legend", "Reach level 25.", 1500),
}

# ---------------------------------------------------------------------------
# Phase 5 — Endgame systems
# ---------------------------------------------------------------------------
SECRET_CLASS_KEYS = {"void_knight", "chronomancer", "dragon_lord", "soul_reaper"}
SECRET_CLASSES = {
    "void_knight": {
        "name": "Void Knight", "req_level": 50, "req_renown": 800,
        "desc": "A knight who weaponizes the space between worlds.",
        "hp": 55, "mp": 15, "atk": 13, "def": 11, "spd": 2, "crit": 4, "resource": "Void",
        "requirement": "Reach level 50 and 800 Renown.",
    },
    "chronomancer": {
        "name": "Chronomancer", "req_level": 45, "req_pvp_wins": 10,
        "desc": "A temporal mage who bends turn order and cooldowns.",
        "hp": 10, "mp": 55, "atk": 13, "def": 2, "spd": 8, "crit": 7, "resource": "Time",
        "requirement": "Reach level 45 and win 10 Arena matches.",
    },
    "dragon_lord": {
        "name": "Dragon Lord", "req_level": 60, "req_raid_damage": 100000,
        "desc": "A legendary commander whose presence echoes through raid battles.",
        "hp": 80, "mp": 25, "atk": 16, "def": 9, "spd": 5, "crit": 6, "resource": "Draconic Fury",
        "requirement": "Reach level 60 and deal 100,000 total Raid Boss damage.",
    },
    "soul_reaper": {
        "name": "Soul Reaper", "req_level": 55, "req_renown": 500,
        "desc": "A forbidden executioner who harvests the echoes left by fallen enemies.",
        "hp": 25, "mp": 45, "atk": 15, "def": 4, "spd": 9, "crit": 10, "resource": "Souls",
        "requirement": "Reach level 55 and 500 Renown.",
    },
}

# Secret classes are real combat classes, but the normal character creator
# refuses them. They can only be awakened through the Phase 5 unlock system.
for _k, _v in SECRET_CLASSES.items():
    CLASSES[_k] = {k: _v[k] for k in ("hp","mp","atk","def","spd","crit","resource","desc")}

# Give secret classes their own names while retaining the existing skill engine.
_SECRET_SKILL_NAMES = {
    "void_knight": ["Void Slash","Rift Guard","Abyss Step","Null Strike","Graviton Edge","Void Chain","Black Aegis","Rift Breaker","Abyssal Roar","Null Field","Event Horizon","Void Reversal","Dimensional Cleave","Abyss Walker","Rift Execution","Singularity","World Rend","Void Dominion","Abyss Ascension","Zero Point"],
    "chronomancer": ["Time Bolt","Second Breath","Temporal Step","Clockwork Lance","Haste Loop","Time Fracture","Rewind","Slow Field","Chrono Burst","Paradox","Time Stop","Future Sight","Age","Timeline Break","Temporal Prison","Epoch Collapse","Infinite Moment","Chronostasis","Eternal Cycle","Absolute Time"],
    "dragon_lord": ["Dragon Fang","Scale Guard","Drake Rush","Flame Breath","Wing Slash","Dragon Roar","Infernal Sonata","Skyfall","Ancient Might","Draconic Ward","Elder Breath","Dragonheart","Meteor Wing","Worldfire","Dragon King's Command","Calamity","Heavenrend","Ancient Dragon Form","Cataclysm","True Dragon Dominion"],
    "soul_reaper": ["Soul Cut","Grave Step","Spirit Guard","Reaper's Mark","Soul Drain","Death Bloom","Spectral Chains","Black Lantern","Soulfire","Gravebind","Eclipse Execution","Soul Harvest","Abyssal Reap","Phantom March","Final Benediction","Soul Storm","Requiem","Kingdom of Death","Final Harvest","End of Souls"],
}
for _k, _names in _SECRET_SKILL_NAMES.items():
    _base = [dict(x) for x in SKILLS["warrior"]]
    for _skill, _name in zip(_base, _names):
        _skill["name"] = _name
    SKILLS[_k] = _base

ITEMS.setdefault("abyssal_core", {"name":"Abyssal Core","slot":"relic","rarity":"legendary","atk":35,"def":20,"hp":120,"spd":8,"crit":8,"price":50000,"level_req":50})
ITEMS.setdefault("chronicle_shard", {"name":"Chronicle Shard","slot":"relic","rarity":"legendary","atk":20,"def":10,"mp":100,"spd":15,"crit":10,"price":50000,"level_req":50})
ITEMS.setdefault("dragon_lord_scale", {"name":"Dragon Lord Scale","slot":"armor","rarity":"mythic","def":45,"hp":250,"atk":20,"spd":8,"crit":6,"price":75000,"level_req":60})
ITEMS.setdefault("soul_reaper_scythe", {"name":"Soul Reaper's Scythe","slot":"weapon","rarity":"mythic","atk":55,"spd":12,"crit":15,"price":80000,"level_req":55})

LEGENDARY_CHALLENGES = {
    "abyssal_throne": {"name":"Abyssal Throne", "level":50, "hp":18000, "atk":260, "def":150, "reward":"abyssal_core", "xp":12000, "gold":25000, "desc":"Survive the throne of the void and claim its core."},
    "chronicle_end": {"name":"End of the Chronicle", "level":60, "hp":24000, "atk":340, "def":190, "reward":"chronicle_shard", "xp":18000, "gold":35000, "desc":"Break the timeline without becoming trapped inside it."},
    "dragon_throne": {"name":"Dragon Throne", "level":70, "hp":32000, "atk":430, "def":230, "reward":"dragon_lord_scale", "xp":26000, "gold":50000, "desc":"Face the ancient sovereign of dragons."},
    "soul_end": {"name":"The Last Soul", "level":75, "hp":38000, "atk":500, "def":260, "reward":"soul_reaper_scythe", "xp":32000, "gold":65000, "desc":"A final trial for heroes who have walked beyond ordinary mortality."},
}


# ---------------------------------------------------------------------------
# v16 — Core Deepening & Balance
# ---------------------------------------------------------------------------
# The goal of this pass is to make every existing loop feed another loop:
# exploration finds resources, resources feed professions/crafting, crafting
# feeds gear/consumables, combat feeds loot/progression, and social systems
# provide small utility advantages. No retired story/NPC/living-world/etc.
# systems are reintroduced here.
STAMINA_REGEN_SECONDS = 90
ADVENTURE_STAMINA_COST = 8
EXPLORE_STAMINA_COST = 6
CRAFT_STAMINA_COST = 2
PARTY_DUNGEON_STAMINA_COST = 12
RAID_STAMINA_COST = 5
MARKET_LISTING_FEE_RATE = 0.01

FACTION_PASSIVES = {
    "horizon_guard": {"name":"Guard Discipline", "desc":"+3% defense and +5% potion effectiveness.", "def_pct":3, "heal_pct":5},
    "free_merchants": {"name":"Merchant Network", "desc":"5% cheaper shop purchases and +5% market sale value.", "shop_pct":5, "sale_pct":5},
    "arcane_circle": {"name":"Arcane Insight", "desc":"+3% skill damage and +5% crafting XP.", "skill_pct":3, "craft_xp_pct":5},
    "wildbound": {"name":"Wilderness Knowledge", "desc":"+1 material on successful gathering when the roll produces 1–2 items.", "gather_extra":1},
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
                upgrade_level INTEGER NOT NULL DEFAULT 0, intrinsic_json TEXT NOT NULL DEFAULT '{}',
                set_key TEXT NOT NULL DEFAULT '', instance_uid TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (guild_id, user_id, slot)
            );
            CREATE TABLE IF NOT EXISTS rpg_equipment_storage (
                instance_uid TEXT PRIMARY KEY, guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                slot TEXT NOT NULL, item_key TEXT NOT NULL, upgrade_level INTEGER NOT NULL DEFAULT 0,
                intrinsic_json TEXT NOT NULL DEFAULT '{}', set_key TEXT NOT NULL DEFAULT '', created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_rpg_equipment_storage_owner ON rpg_equipment_storage(guild_id,user_id,slot);
            CREATE TABLE IF NOT EXISTS rpg_equipment_instances (
                instance_uid TEXT PRIMARY KEY, guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                slot TEXT NOT NULL, item_key TEXT NOT NULL, upgrade_level INTEGER NOT NULL DEFAULT 0,
                intrinsic_json TEXT NOT NULL DEFAULT '{}', set_key TEXT NOT NULL DEFAULT '',
                enchant_key TEXT NOT NULL DEFAULT '', enchant_level INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_rpg_equipment_instances_owner ON rpg_equipment_instances(guild_id,user_id,item_key);
            CREATE TABLE IF NOT EXISTS rpg_economy_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE, guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL, event_type TEXT NOT NULL, item_key TEXT NOT NULL DEFAULT '',
                quantity INTEGER NOT NULL DEFAULT 0, gold_delta INTEGER NOT NULL DEFAULT 0,
                balance_after INTEGER, metadata_json TEXT NOT NULL DEFAULT '{}', created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_rpg_economy_log_owner ON rpg_economy_log(guild_id,user_id,created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_rpg_economy_log_event ON rpg_economy_log(guild_id,event_type,created_at DESC);
            CREATE TABLE IF NOT EXISTS rpg_skill_loadout (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, slot INTEGER NOT NULL, skill_key TEXT NOT NULL,
                PRIMARY KEY (guild_id, user_id, slot)
            );
            CREATE TABLE IF NOT EXISTS rpg_skill_mastery (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, skill_key TEXT NOT NULL, rank INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (guild_id, user_id, skill_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_talents (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, tree TEXT NOT NULL, talent_key TEXT NOT NULL, rank INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id, tree, talent_key)
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
            CREATE TABLE IF NOT EXISTS rpg_combat_sessions (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                state_json TEXT NOT NULL, updated_at REAL NOT NULL,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE INDEX IF NOT EXISTS idx_rpg_combat_sessions_updated ON rpg_combat_sessions(updated_at);
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
            CREATE TABLE IF NOT EXISTS rpg_titles (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, title_key TEXT NOT NULL,
                unlocked_at REAL NOT NULL, PRIMARY KEY (guild_id, user_id, title_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_housing (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, house_key TEXT NOT NULL DEFAULT 'cabin',
                level INTEGER NOT NULL DEFAULT 1, xp INTEGER NOT NULL DEFAULT 0,
                storage_bonus INTEGER NOT NULL DEFAULT 0, comfort INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL, PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS rpg_market (
                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, seller_id INTEGER NOT NULL,
                item_key TEXT NOT NULL, quantity INTEGER NOT NULL, price_each INTEGER NOT NULL, created_at REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'open', buyer_id INTEGER DEFAULT 0, sold_at REAL DEFAULT 0, listing_token TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS rpg_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL,
                proposer_id INTEGER NOT NULL, target_id INTEGER NOT NULL,
                proposer_gold INTEGER NOT NULL DEFAULT 0, target_gold INTEGER NOT NULL DEFAULT 0,
                proposer_gems INTEGER NOT NULL DEFAULT 0, target_gems INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'open', created_at REAL NOT NULL, updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rpg_trade_items (
                trade_id INTEGER NOT NULL, side TEXT NOT NULL, item_key TEXT NOT NULL, quantity INTEGER NOT NULL,
                PRIMARY KEY (trade_id, side, item_key),
                FOREIGN KEY (trade_id) REFERENCES rpg_trades(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS rpg_trade_pets (
                trade_id INTEGER NOT NULL, side TEXT NOT NULL, pet_id INTEGER NOT NULL,
                PRIMARY KEY (trade_id, side, pet_id),
                FOREIGN KEY (trade_id) REFERENCES rpg_trades(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_rpg_trades_parties ON rpg_trades(guild_id, proposer_id, target_id, status);
            CREATE INDEX IF NOT EXISTS idx_rpg_trade_items_trade ON rpg_trade_items(trade_id, side);
            CREATE INDEX IF NOT EXISTS idx_rpg_trade_pets_trade ON rpg_trade_pets(trade_id, side);
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
            CREATE TABLE IF NOT EXISTS rpg_area_discoveries (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, area_key TEXT NOT NULL,
                discovered_at REAL NOT NULL, source TEXT NOT NULL DEFAULT 'exploration',
                PRIMARY KEY (guild_id, user_id, area_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_objectives (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, period TEXT NOT NULL,
                objective_key TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL,
                progress_type TEXT NOT NULL, target INTEGER NOT NULL, progress INTEGER NOT NULL DEFAULT 0,
                reward_xp INTEGER NOT NULL DEFAULT 0, reward_gold INTEGER NOT NULL DEFAULT 0,
                reward_item TEXT, reward_qty INTEGER NOT NULL DEFAULT 0, claimed INTEGER NOT NULL DEFAULT 0,
                period_key TEXT NOT NULL, created_at REAL NOT NULL,
                PRIMARY KEY (guild_id, user_id, period, objective_key, period_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_world_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, event_key TEXT NOT NULL,
                name TEXT NOT NULL, description TEXT NOT NULL, area_key TEXT NOT NULL, level INTEGER NOT NULL,
                max_hp INTEGER NOT NULL, hp INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'active',
                started_at REAL NOT NULL, expires_at REAL NOT NULL, created_by INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rpg_world_event_participants (
                event_id INTEGER NOT NULL, guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                damage INTEGER NOT NULL DEFAULT 0, attacks INTEGER NOT NULL DEFAULT 0, last_attack REAL NOT NULL DEFAULT 0,
                PRIMARY KEY (event_id, user_id), FOREIGN KEY (event_id) REFERENCES rpg_world_events(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_rpg_world_events_active ON rpg_world_events(guild_id,status,expires_at);
            CREATE INDEX IF NOT EXISTS idx_rpg_world_event_participants_damage ON rpg_world_event_participants(event_id,damage DESC);

            -- Phase 4: living-world systems. These are server-scoped and player progress
            -- is deliberately separate from the existing RPG character tables.
            CREATE TABLE IF NOT EXISTS rpg_npcs (
                guild_id INTEGER NOT NULL, npc_key TEXT NOT NULL, name TEXT NOT NULL,
                role TEXT NOT NULL, area_key TEXT NOT NULL DEFAULT 'horizon_village',
                personality TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (guild_id, npc_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_npc_relationships (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, npc_key TEXT NOT NULL,
                affinity INTEGER NOT NULL DEFAULT 0, stage TEXT NOT NULL DEFAULT 'stranger',
                interactions INTEGER NOT NULL DEFAULT 0, last_interaction REAL NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id,user_id,npc_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_lore_entries (
                guild_id INTEGER NOT NULL, lore_key TEXT NOT NULL, title TEXT NOT NULL,
                body TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'world',
                required_npc TEXT NOT NULL DEFAULT '', required_affinity INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id,lore_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_lore_discoveries (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, lore_key TEXT NOT NULL,
                discovered_at REAL NOT NULL, source TEXT NOT NULL DEFAULT 'discovery',
                PRIMARY KEY (guild_id,user_id,lore_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_hidden_quests (
                guild_id INTEGER NOT NULL, hidden_key TEXT NOT NULL, title TEXT NOT NULL,
                description TEXT NOT NULL, npc_key TEXT NOT NULL DEFAULT '',
                required_affinity INTEGER NOT NULL DEFAULT 0, trigger_type TEXT NOT NULL DEFAULT 'relationship',
                trigger_value INTEGER NOT NULL DEFAULT 0, reward_xp INTEGER NOT NULL DEFAULT 0,
                reward_gold INTEGER NOT NULL DEFAULT 0, reward_item TEXT NOT NULL DEFAULT '',
                reward_qty INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (guild_id,hidden_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_hidden_quest_progress (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, hidden_key TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'locked', progress INTEGER NOT NULL DEFAULT 0,
                updated_at REAL NOT NULL DEFAULT 0, PRIMARY KEY (guild_id,user_id,hidden_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_server_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, event_key TEXT NOT NULL,
                name TEXT NOT NULL, description TEXT NOT NULL, event_type TEXT NOT NULL DEFAULT 'community',
                target INTEGER NOT NULL DEFAULT 1, progress INTEGER NOT NULL DEFAULT 0,
                reward_xp INTEGER NOT NULL DEFAULT 0, reward_gold INTEGER NOT NULL DEFAULT 0,
                reward_item TEXT NOT NULL DEFAULT '', reward_qty INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active', started_at REAL NOT NULL, expires_at REAL NOT NULL,
                UNIQUE(guild_id,event_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_server_event_contributions (
                event_id INTEGER NOT NULL, guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                contribution INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(event_id,user_id),
                FOREIGN KEY(event_id) REFERENCES rpg_server_events(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_rpg_npc_relationships_user ON rpg_npc_relationships(guild_id,user_id,affinity DESC);
            CREATE INDEX IF NOT EXISTS idx_rpg_server_events_active ON rpg_server_events(guild_id,status,expires_at);

            -- Phase 5: PvP seasons, raid bosses, secret classes and legendary trials.
            CREATE TABLE IF NOT EXISTS rpg_pvp_seasons (
                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, season_number INTEGER NOT NULL,
                name TEXT NOT NULL, started_at REAL NOT NULL, ends_at REAL NOT NULL, status TEXT NOT NULL DEFAULT 'active',
                UNIQUE(guild_id,season_number)
            );
            CREATE TABLE IF NOT EXISTS rpg_pvp_ratings (
                guild_id INTEGER NOT NULL, season_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                rating INTEGER NOT NULL DEFAULT 1000, wins INTEGER NOT NULL DEFAULT 0, losses INTEGER NOT NULL DEFAULT 0,
                streak INTEGER NOT NULL DEFAULT 0, best_rating INTEGER NOT NULL DEFAULT 1000,
                PRIMARY KEY(guild_id,season_id,user_id)
            );
            CREATE TABLE IF NOT EXISTS rpg_arena_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, season_id INTEGER NOT NULL,
                player_a INTEGER NOT NULL, player_b INTEGER NOT NULL, winner_id INTEGER NOT NULL DEFAULT 0,
                rating_delta_a INTEGER NOT NULL DEFAULT 0, rating_delta_b INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_rpg_pvp_ratings_leaderboard ON rpg_pvp_ratings(guild_id,season_id,rating DESC);
            CREATE TABLE IF NOT EXISTS rpg_raid_bosses (
                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, raid_key TEXT NOT NULL,
                name TEXT NOT NULL, description TEXT NOT NULL, level INTEGER NOT NULL, max_hp INTEGER NOT NULL, hp INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active', started_at REAL NOT NULL, expires_at REAL NOT NULL, weekly_key TEXT NOT NULL,
                UNIQUE(guild_id,weekly_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_raid_damage (
                raid_id INTEGER NOT NULL, guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, damage INTEGER NOT NULL DEFAULT 0,
                attacks INTEGER NOT NULL DEFAULT 0, last_attack REAL NOT NULL DEFAULT 0, claimed INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(raid_id,user_id), FOREIGN KEY(raid_id) REFERENCES rpg_raid_bosses(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_rpg_raid_damage_rank ON rpg_raid_damage(raid_id,damage DESC);
            CREATE TABLE IF NOT EXISTS rpg_secret_class_unlocks (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, class_key TEXT NOT NULL, unlocked_at REAL NOT NULL,
                PRIMARY KEY(guild_id,user_id,class_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_legendary_challenges (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, challenge_key TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0, completions INTEGER NOT NULL DEFAULT 0, last_completed REAL NOT NULL DEFAULT 0,
                PRIMARY KEY(guild_id,user_id,challenge_key)
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
                "last_gather": "REAL NOT NULL DEFAULT 0", "last_mine": "REAL NOT NULL DEFAULT 0", "last_fish": "REAL NOT NULL DEFAULT 0",
            }
            cur = await db.execute("PRAGMA table_info(rpg_players)")
            existing = {row[1] for row in await cur.fetchall()}
            for column, definition in migrations.items():
                if column not in existing:
                    await db.execute(f"ALTER TABLE rpg_players ADD COLUMN {column} {definition}")
            cur = await db.execute("PRAGMA table_info(rpg_equipment)")
            equipment_existing = {row[1] for row in await cur.fetchall()}
            equipment_migrations = {
                "upgrade_level": "INTEGER NOT NULL DEFAULT 0",
                "intrinsic_json": "TEXT NOT NULL DEFAULT '{}'",
                "set_key": "TEXT NOT NULL DEFAULT ''",
                "instance_uid": "TEXT NOT NULL DEFAULT ''",
            }
            for column, definition in equipment_migrations.items():
                if column not in equipment_existing:
                    await db.execute(f"ALTER TABLE rpg_equipment ADD COLUMN {column} {definition}")
            cur = await db.execute("PRAGMA table_info(rpg_market)")
            market_existing = {row[1] for row in await cur.fetchall()}
            market_migrations = {
                "status": "TEXT NOT NULL DEFAULT 'open'", "buyer_id": "INTEGER DEFAULT 0",
                "sold_at": "REAL DEFAULT 0", "listing_token": "TEXT NOT NULL DEFAULT ''",
            }
            for column, definition in market_migrations.items():
                if column not in market_existing:
                    await db.execute(f"ALTER TABLE rpg_market ADD COLUMN {column} {definition}")
            await db.execute("UPDATE rpg_market SET listing_token='legacy-'||id WHERE listing_token='' OR listing_token IS NULL")
            await db.execute("UPDATE rpg_equipment SET instance_uid='legacy-'||guild_id||'-'||user_id||'-'||slot WHERE instance_uid='' OR instance_uid IS NULL")
            await db.execute("UPDATE rpg_equipment SET set_key='' WHERE set_key IS NULL")
            # One-time migration for already-equipped legacy gear. Intrinsics are
            # rolled only when the old row has no intrinsic payload, so restarts
            # never reroll a player's gear.
            cur = await db.execute("SELECT guild_id,user_id,slot,item_key,intrinsic_json,set_key FROM rpg_equipment")
            legacy_gear = await cur.fetchall()
            for gid, uid, slot, item_key, intrinsic_json, set_key in legacy_gear:
                item = ITEMS.get(item_key, {})
                intr = intrinsic_json if intrinsic_json not in (None, "", "{}") else json.dumps(_roll_intrinsics(item), separators=(",", ":"))
                skey = set_key or _set_key_for_item(item, item_key)
                await db.execute("UPDATE rpg_equipment SET intrinsic_json=?,set_key=? WHERE guild_id=? AND user_id=? AND slot=?",(intr,skey,gid,uid,slot))
            await db.execute("CREATE INDEX IF NOT EXISTS idx_rpg_market_open ON rpg_market(guild_id,status,created_at DESC)")
            cur = await db.execute("PRAGMA table_info(rpg_quests)")
            quest_existing = {row[1] for row in await cur.fetchall()}
            quest_migrations = {"chain_key": "TEXT NOT NULL DEFAULT ''", "chain_step": "INTEGER NOT NULL DEFAULT 0"}
            for column, definition in quest_migrations.items():
                if column not in quest_existing:
                    await db.execute(f"ALTER TABLE rpg_quests ADD COLUMN {column} {definition}")
            cur = await db.execute("PRAGMA table_info(rpg_bounties)")
            bounty_existing = {row[1] for row in await cur.fetchall()}
            if "target_id" not in bounty_existing:
                await db.execute("ALTER TABLE rpg_bounties ADD COLUMN target_id INTEGER DEFAULT 0")
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
            # New progression starts with exactly three active skills. Remove the
            # old fourth starter slot from characters created by earlier versions;
            # skill 4 remains unlockable normally at level 6.
            await db.execute("DELETE FROM rpg_skill_loadout WHERE slot=4")

            cur = await db.execute("SELECT guild_id,user_id,area_key FROM rpg_players")
            for _gid,_uid,_area in await cur.fetchall():
                _area = _area or "horizon_village"
                if _area in AREAS:
                    await db.execute("INSERT OR IGNORE INTO rpg_area_discoveries(guild_id,user_id,area_key,discovered_at,source) VALUES(?,?,?,?,?)",(_gid,_uid,_area,time.time(),"migration"))
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
                    for slot, skill_key in enumerate(("skill_1","skill_2","skill_3"),1):
                        await db.execute("INSERT OR IGNORE INTO rpg_skill_loadout(guild_id,user_id,slot,skill_key) VALUES(?,?,?,?)", (guild_id,user_id,slot,skill_key))
            # Ensure every existing character has exactly three starter skills and
            # a mastery record for those skills. Skill points are intentionally not
            # spent automatically; players decide which skills to master.
            cur = await db.execute("SELECT guild_id,user_id,class_name FROM rpg_players")
            for guild_id,user_id,class_name in await cur.fetchall():
                for skill_key in ("skill_1","skill_2","skill_3"):
                    await db.execute("INSERT OR IGNORE INTO rpg_skill_mastery(guild_id,user_id,skill_key,rank) VALUES(?,?,?,1)", (guild_id,user_id,skill_key))
            # Batch v12 — Phases 5-9 progression tables. These are additive and
            # intentionally do not reset existing RPG data.
            await db.executescript("""
            CREATE TABLE IF NOT EXISTS rpg_professions (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, profession TEXT NOT NULL,
                level INTEGER NOT NULL DEFAULT 1, xp INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(guild_id,user_id,profession)
            );
            CREATE TABLE IF NOT EXISTS rpg_recipe_unlocks (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, recipe_key TEXT NOT NULL,
                unlocked_at REAL NOT NULL, PRIMARY KEY(guild_id,user_id,recipe_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_pet_collection (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, species TEXT NOT NULL,
                first_seen REAL NOT NULL, times_seen INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY(guild_id,user_id,species)
            );
            CREATE TABLE IF NOT EXISTS rpg_social_reputation (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                helpful INTEGER NOT NULL DEFAULT 0, party_runs INTEGER NOT NULL DEFAULT 0,
                trades_completed INTEGER NOT NULL DEFAULT 0, guild_contributions INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(guild_id,user_id)
            );
            CREATE INDEX IF NOT EXISTS idx_rpg_market_seller_status ON rpg_market(guild_id,seller_id,status);
            """)
            cur=await db.execute("PRAGMA table_info(rpg_pet_inventory)")
            pet_inv_existing={row[1] for row in await cur.fetchall()}
            for column,definition in {
                "bond":"INTEGER NOT NULL DEFAULT 0",
                "mood":"INTEGER NOT NULL DEFAULT 50",
                "total_xp":"INTEGER NOT NULL DEFAULT 0",
            }.items():
                if column not in pet_inv_existing:
                    await db.execute(f"ALTER TABLE rpg_pet_inventory ADD COLUMN {column} {definition}")
            # v13 — Phases 10-15 additive world/quest/building/faction/endgame systems.
            await db.executescript("""
            CREATE TABLE IF NOT EXISTS rpg_world_state (
                guild_id INTEGER PRIMARY KEY, world_day INTEGER NOT NULL DEFAULT 1,
                weather TEXT NOT NULL DEFAULT 'clear', season TEXT NOT NULL DEFAULT 'spring',
                stability INTEGER NOT NULL DEFAULT 100, last_tick REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS rpg_rumors (
                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, text TEXT NOT NULL,
                area_key TEXT NOT NULL DEFAULT '', source_npc TEXT NOT NULL DEFAULT '',
                created_at REAL NOT NULL, expires_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_rpg_rumors_active ON rpg_rumors(guild_id,expires_at);
            CREATE TABLE IF NOT EXISTS rpg_npc_schedules (
                guild_id INTEGER NOT NULL, npc_key TEXT NOT NULL, hour INTEGER NOT NULL,
                area_key TEXT NOT NULL, activity TEXT NOT NULL, PRIMARY KEY(guild_id,npc_key,hour)
            );
            CREATE TABLE IF NOT EXISTS rpg_story_memory (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, chapter INTEGER NOT NULL DEFAULT 1,
                flags_json TEXT NOT NULL DEFAULT '{}', choices_json TEXT NOT NULL DEFAULT '[]', updated_at REAL NOT NULL,
                PRIMARY KEY(guild_id,user_id)
            );
            CREATE TABLE IF NOT EXISTS rpg_chronicle (
                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL DEFAULT 0,
                event_key TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL, area_key TEXT NOT NULL DEFAULT '',
                created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_rpg_chronicle_world ON rpg_chronicle(guild_id,created_at DESC);
            CREATE TABLE IF NOT EXISTS rpg_world_structures (
                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                structure_key TEXT NOT NULL, name TEXT NOT NULL, area_key TEXT NOT NULL, level INTEGER NOT NULL DEFAULT 1,
                materials_json TEXT NOT NULL DEFAULT '{}', created_at REAL NOT NULL,
                UNIQUE(guild_id,user_id,structure_key,area_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_world_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, project_key TEXT NOT NULL,
                name TEXT NOT NULL, description TEXT NOT NULL, area_key TEXT NOT NULL, target INTEGER NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0, reward_xp INTEGER NOT NULL DEFAULT 0, reward_gold INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active', expires_at REAL NOT NULL,
                UNIQUE(guild_id,project_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_project_contributions (
                project_id INTEGER NOT NULL, guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                contribution INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(project_id,user_id),
                FOREIGN KEY(project_id) REFERENCES rpg_world_projects(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS rpg_factions (
                guild_id INTEGER NOT NULL, faction_key TEXT NOT NULL, name TEXT NOT NULL, description TEXT NOT NULL,
                ideology TEXT NOT NULL, color TEXT NOT NULL DEFAULT '', PRIMARY KEY(guild_id,faction_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_faction_members (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, faction_key TEXT NOT NULL,
                reputation INTEGER NOT NULL DEFAULT 0, rank TEXT NOT NULL DEFAULT 'outsider', joined_at REAL NOT NULL,
                PRIMARY KEY(guild_id,user_id)
            );
            CREATE TABLE IF NOT EXISTS rpg_faction_relations (
                guild_id INTEGER NOT NULL, faction_a TEXT NOT NULL, faction_b TEXT NOT NULL, relation TEXT NOT NULL DEFAULT 'neutral',
                updated_at REAL NOT NULL, PRIMARY KEY(guild_id,faction_a,faction_b)
            );
            CREATE TABLE IF NOT EXISTS rpg_endgame_progress (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, mastery INTEGER NOT NULL DEFAULT 0,
                ascension INTEGER NOT NULL DEFAULT 0, milestones_json TEXT NOT NULL DEFAULT '{}', updated_at REAL NOT NULL,
                PRIMARY KEY(guild_id,user_id)
            );
            CREATE INDEX IF NOT EXISTS idx_rpg_faction_rep ON rpg_faction_members(guild_id,faction_key,reputation DESC);
            """)
            # v14 — Phases 16-19: mysteries, world-scale events, persistent world memory, RPG completion audit.
            await db.executescript("""
            CREATE TABLE IF NOT EXISTS rpg_mysteries (
                guild_id INTEGER NOT NULL, mystery_key TEXT NOT NULL, name TEXT NOT NULL,
                description TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'mystery',
                required_level INTEGER NOT NULL DEFAULT 1, required_flag TEXT NOT NULL DEFAULT '',
                area_key TEXT NOT NULL DEFAULT '', discovery_threshold INTEGER NOT NULL DEFAULT 1,
                reward_xp INTEGER NOT NULL DEFAULT 0, reward_gold INTEGER NOT NULL DEFAULT 0,
                reward_item TEXT NOT NULL DEFAULT '', reward_qty INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'hidden', discovered_at REAL NOT NULL DEFAULT 0,
                PRIMARY KEY(guild_id,mystery_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_mystery_progress (
                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, mystery_key TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0, discovered INTEGER NOT NULL DEFAULT 0,
                flags_json TEXT NOT NULL DEFAULT '{}', updated_at REAL NOT NULL,
                PRIMARY KEY(guild_id,user_id,mystery_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, anomaly_key TEXT NOT NULL,
                area_key TEXT NOT NULL, severity INTEGER NOT NULL DEFAULT 1, state TEXT NOT NULL DEFAULT 'active',
                started_at REAL NOT NULL, resolved_at REAL NOT NULL DEFAULT 0, UNIQUE(guild_id,anomaly_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_world_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL DEFAULT 0,
                memory_key TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'world', summary TEXT NOT NULL,
                consequence_json TEXT NOT NULL DEFAULT '{}', created_at REAL NOT NULL,
                UNIQUE(guild_id,user_id,memory_key)
            );
            CREATE INDEX IF NOT EXISTS idx_rpg_world_memory ON rpg_world_memory(guild_id,user_id,created_at DESC);
            CREATE TABLE IF NOT EXISTS rpg_world_event_state (
                guild_id INTEGER PRIMARY KEY, event_key TEXT NOT NULL DEFAULT '', phase TEXT NOT NULL DEFAULT 'dormant',
                threat INTEGER NOT NULL DEFAULT 0, world_progress INTEGER NOT NULL DEFAULT 0,
                started_at REAL NOT NULL DEFAULT 0, updated_at REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS rpg_rpg_completion (
                guild_id INTEGER PRIMARY KEY, phase16 INTEGER NOT NULL DEFAULT 0, phase17 INTEGER NOT NULL DEFAULT 0,
                phase18 INTEGER NOT NULL DEFAULT 0, phase19 INTEGER NOT NULL DEFAULT 0,
                audit_json TEXT NOT NULL DEFAULT '{}', updated_at REAL NOT NULL
            );
            """)
            await db.execute("""
            CREATE TABLE IF NOT EXISTS rpg_pending_rewards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                reward_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'combat',
                created_at REAL NOT NULL,
                claimed_at REAL NOT NULL DEFAULT 0
            )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_rpg_pending_rewards_user ON rpg_pending_rewards(guild_id,user_id,claimed_at,id)")
            await db.commit()

        # Phase 4 launches on a clean RPG economy/progression state. This is a
        # one-time migration marker, so Railway restarts never wipe players again.
        await self._phase4_fresh_start()
        await self._v15_remove_retired_systems()
        await self._v16_migrate()
        await self._v19_migrate()

    async def _v16_migrate(self):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("PRAGMA table_info(rpg_players)")
            cols={r[1] for r in await cur.fetchall()}
            if "last_stamina_tick" not in cols:
                await db.execute("ALTER TABLE rpg_players ADD COLUMN last_stamina_tick REAL NOT NULL DEFAULT 0")
            now=time.time()
            await db.execute("UPDATE rpg_players SET last_stamina_tick=? WHERE last_stamina_tick<=0",(now,))
            await db.commit()

    async def _v19_migrate(self):
        """Balance migration: clean stale skill loadout rows and keep normal gear visible on unequip."""
        try:
            async with aiosqlite.connect(self.path) as db:
                cur=await db.execute("SELECT DISTINCT class_name FROM rpg_players")
                classes={r[0] for r in await cur.fetchall()}
                cur=await db.execute("SELECT guild_id,user_id,slot,skill_key FROM rpg_skill_loadout")
                rows=await cur.fetchall()
                for guild_id,user_id,slot,key in rows:
                    pcls=next(iter(classes),None) if len(classes)==1 else None
                    # Validate against every known class; invalid keys are removed
                    # only when they cannot exist in any current class kit.
                    if not any(key in {x["key"] for x in SKILLS.get(cls,[])} for cls in SKILLS) and not any(key in {x["key"] for x in skills} for skills in SUBCLASS_SKILLS.values()):
                        await db.execute("DELETE FROM rpg_skill_loadout WHERE guild_id=? AND user_id=? AND slot=?",(guild_id,user_id,slot))
                await db.commit()
        except Exception:
            pass

    async def _refresh_stamina(self, guild_id, user_id):
        now=time.time()
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT stamina,last_stamina_tick FROM rpg_players WHERE guild_id=? AND user_id=?",(guild_id,user_id))
            row=await cur.fetchone()
            if not row:return 0
            stamina=max(0,min(100,int(row[0])))
            tick=float(row[1] or now)
            gained=int(max(0,now-tick)//STAMINA_REGEN_SECONDS)
            if gained:
                new_stamina=min(100,stamina+gained)
                consumed=min(gained,100-stamina)
                new_tick=tick+consumed*STAMINA_REGEN_SECONDS
                if new_stamina>=100:new_tick=now
                await db.execute("UPDATE rpg_players SET stamina=?,last_stamina_tick=? WHERE guild_id=? AND user_id=?",(new_stamina,new_tick,guild_id,user_id)); await db.commit()
                return new_stamina
            return stamina

    async def _spend_stamina(self,guild_id,user_id,cost):
        cost=max(0,int(cost)); await self._refresh_stamina(guild_id,user_id)
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT stamina FROM rpg_players WHERE guild_id=? AND user_id=?",(guild_id,user_id)); row=await cur.fetchone()
            if not row or int(row[0])<cost:return False,int(row[0]) if row else 0
            await db.execute("UPDATE rpg_players SET stamina=stamina-?,last_stamina_tick=? WHERE guild_id=? AND user_id=?",(cost,time.time(),guild_id,user_id)); await db.commit()
            return True,max(0,int(row[0])-cost)

    async def _refund_stamina(self,guild_id,user_id,amount):
        amount=max(0,int(amount))
        if not amount:return
        await self._refresh_stamina(guild_id,user_id)
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET stamina=min(100,stamina+?),last_stamina_tick=? WHERE guild_id=? AND user_id=?",(amount,time.time(),guild_id,user_id)); await db.commit()

    async def _faction_passive(self,guild_id,user_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT faction_key FROM rpg_faction_members WHERE guild_id=? AND user_id=?",(guild_id,user_id)); row=await cur.fetchone()
        return FACTION_PASSIVES.get(row[0],{}) if row else {}

    async def _combat_loot(self,guild_id,user_id,p,enemy):
        """Give varied, level-appropriate loot without flooding inventories."""
        rewards=[]
        # Every victory pays a material; stronger regions have a chance at a
        # second material or a piece of usable gear.
        drops=[k for k in enemy.get("drops",[]) if k in ITEMS]
        if drops:
            first=random.choice(drops); qty=1+int(random.random()<0.18)
            await self.add_item(guild_id,user_id,first,qty,event_type="combat_loot")
            rewards.append((first,qty))
        if random.random()<0.10:
            candidates=[(k,v) for k,v in ITEMS.items() if v.get("slot") in {"weapon","armor","offhand","accessory","ring","amulet","relic"} and int(v.get("level_req",1))<=int(p["level"])+2 and int(v.get("level_req",1))>=max(1,int(p["level"])-8)]
            if candidates:
                # Keep ordinary combat from producing endgame gear too often.
                weights={"common":70,"uncommon":24,"rare":5,"epic":1,"legendary":0,"mythic":0}
                usable=[(k,v) for k,v in candidates if weights.get(v.get("rarity","common"),0)>0]
                if not usable: usable=candidates
                key,item=random.choices(usable,weights=[weights.get(v.get("rarity","common"),1) for _,v in usable],k=1)[0]
                await self.add_item(guild_id,user_id,key,1,event_type="combat_gear_drop")
                rewards.append((key,1))
        return rewards

    async def _v15_remove_retired_systems(self):
        retired = [
            "rpg_housing", "rpg_npc_relationships", "rpg_lore_discoveries",
            "rpg_hidden_quest_progress", "rpg_server_event_contributions",
            "rpg_server_events", "rpg_hidden_quests", "rpg_lore_entries", "rpg_npcs",
            "rpg_world_state", "rpg_rumors", "rpg_npc_schedules", "rpg_story_memory",
            "rpg_chronicle", "rpg_world_structures", "rpg_project_contributions",
            "rpg_world_projects", "rpg_faction_relations", "rpg_mysteries",
            "rpg_anomalies", "rpg_world_memory", "rpg_world_event_state",
            "rpg_rpg_completion",
        ]
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys=OFF")
            for table in retired:
                try:
                    await db.execute(f"DROP TABLE IF EXISTS {table}")
                except Exception:
                    pass
            await db.commit()

    async def _phase4_fresh_start(self):
        tables = [
            "rpg_world_event_participants", "rpg_world_events", "rpg_objectives",
            "rpg_area_discoveries", "rpg_bounties", "rpg_kingdom_members", "rpg_kingdoms",
            "rpg_trade_items", "rpg_trade_pets", "rpg_trades", "rpg_market",
            "rpg_housing", "rpg_titles", "rpg_achievements", "rpg_pets", "rpg_pet_inventory",
            "rpg_talents", "rpg_skill_mastery", "rpg_skill_loadout", "rpg_equipment_enchants",
            "rpg_gacha_state", "rpg_economy_log", "rpg_equipment_storage", "rpg_equipment",
            "rpg_inventory", "rpg_player_quests", "rpg_quests", "rpg_party_members",
            "rpg_parties", "rpg_guild_members", "rpg_guilds", "rpg_players",
            "rpg_npc_relationships", "rpg_lore_discoveries", "rpg_hidden_quest_progress",            "rpg_server_event_contributions", "rpg_server_events", "rpg_hidden_quests",
            "rpg_lore_entries", "rpg_npcs"        ]
        async with aiosqlite.connect(self.path) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS horizon_rpg_migrations (key TEXT PRIMARY KEY, applied_at REAL NOT NULL)")
            cur=await db.execute("SELECT 1 FROM horizon_rpg_migrations WHERE key='phase4_fresh_start_v1'")
            if await cur.fetchone():
                return
            await db.execute("PRAGMA foreign_keys=OFF")
            for table in tables:
                try:
                    await db.execute(f"DELETE FROM {table}")
                except Exception:
                    pass
            await db.execute("DELETE FROM sqlite_sequence WHERE name LIKE 'rpg_%'")
            await db.execute("INSERT INTO horizon_rpg_migrations(key,applied_at) VALUES('phase4_fresh_start_v1',?)",(time.time(),))
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
        if race not in RACES or class_name not in CLASSES or class_name in SECRET_CLASS_KEYS:
            raise ValueError("Invalid race or class.")
        if await self.player(guild_id, user_id):
            return False, "You already have a hero. Use `!rpg profile` to inspect it."
        s = self._class_stats(race, class_name)
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO rpg_players(guild_id,user_id,name,race,class_name,max_hp,hp,max_mp,mp,atk,defense,speed,crit) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                             (guild_id,user_id,name[:32],race,class_name,s["max_hp"],s["max_hp"],s["max_mp"],s["max_mp"],s["atk"],s["defense"],s["speed"],s["crit"]))
            for item, qty in (("life_potion",3),("mana_potion",2),("iron_sword",1),("iron_armor",1)):
                await db.execute("INSERT INTO rpg_inventory VALUES(?,?,?,?)", (guild_id,user_id,item,qty))
            for slot,skill_key in enumerate(("skill_1","skill_2","skill_3"),1):
                await db.execute("INSERT OR IGNORE INTO rpg_skill_loadout(guild_id,user_id,slot,skill_key) VALUES(?,?,?,?)",(guild_id,user_id,slot,skill_key))
            await db.execute("INSERT OR IGNORE INTO rpg_area_discoveries(guild_id,user_id,area_key,discovered_at,source) VALUES(?,?,?,?,?)",(guild_id,user_id,"horizon_village",time.time(),"starting_area"))
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

    def skills_for_player(self, player):
        """Return the class core/advanced skills plus the player's six subclass skills."""
        if not player:
            return []
        class_name=player.get("class_name") or player.get("class") or "warrior"
        subclass=player.get("subclass") or ""
        skills=list(SKILLS.get(class_name, []))
        if subclass in SUBCLASS_SKILLS:
            skills.extend(SUBCLASS_SKILLS[subclass])
        return skills

    def _skill_for_player(self, player, skill_key):
        return next((s for s in self.skills_for_player(player) if s["key"] == skill_key), None)

    async def unlocked_skills(self, guild_id, user_id):
        p=await self.player(guild_id,user_id)
        if not p:return []
        return [s for s in self.skills_for_player(p) if int(s["unlock"])<=int(p["level"])]

    async def equipped_skills(self, guild_id, user_id):
        p=await self.player(guild_id,user_id)
        if not p:return []
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT slot,skill_key FROM rpg_skill_loadout WHERE guild_id=? AND user_id=? ORDER BY slot", (guild_id,user_id))
            rows=await cur.fetchall()
        available={s["key"]:s for s in self.skills_for_player(p) if int(s["unlock"])<=int(p["level"])}
        return [available[key] for _,key in rows if key in available][:4]

    async def equip_skill(self, guild_id, user_id, skill_key, slot=1):
        p=await self.player(guild_id,user_id)
        if not p:
            return False,"Create a hero first."
        try:
            slot=int(slot)
        except (TypeError,ValueError):
            return False,"Skill slot must be **1, 2, 3, or 4**."
        if slot not in {1,2,3,4}:
            return False,"Skill slot must be **1, 2, 3, or 4**."
        skill=self._skill_for_player(p,str(skill_key).lower().strip())
        if not skill:
            return False,"That skill does not belong to your current class/subclass."
        if not self._skill_available(p,skill):
            return False,f"**{skill['name']}** unlocks at level **{skill['unlock']}**."
        async with aiosqlite.connect(self.path) as db:
            # A skill can occupy only one active slot. If it is moved,
            # clear its old slot first, then replace the requested slot.
            await db.execute(
                "DELETE FROM rpg_skill_loadout WHERE guild_id=? AND user_id=? AND skill_key=?",
                (guild_id,user_id,skill["key"]),
            )
            await db.execute(
                "INSERT INTO rpg_skill_loadout(guild_id,user_id,slot,skill_key) VALUES(?,?,?,?) "
                "ON CONFLICT(guild_id,user_id,slot) DO UPDATE SET skill_key=excluded.skill_key",
                (guild_id,user_id,slot,skill["key"]),
            )
            await db.commit()
        return True,f"Equipped **{skill['name']}** in **Skill Slot {slot}**."


    async def skill_loadout(self,guild_id,user_id):
        p=await self.player(guild_id,user_id)
        if not p:return []
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT slot,skill_key FROM rpg_skill_loadout WHERE guild_id=? AND user_id=? ORDER BY slot", (guild_id,user_id))
            rows=await cur.fetchall()
        all_skills={s["key"]:s for s in self.skills_for_player(p)}
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

    async def _economy_log(self, db, guild_id, user_id, event_type, *, item_key="", quantity=0, gold_delta=0, balance_after=None, metadata=None):
        await db.execute(
            "INSERT INTO rpg_economy_log(event_id,guild_id,user_id,event_type,item_key,quantity,gold_delta,balance_after,metadata_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (uuid.uuid4().hex, int(guild_id), int(user_id), str(event_type), str(item_key or ""), int(quantity), int(gold_delta), balance_after,
             json.dumps(metadata or {}, separators=(",", ":"), sort_keys=True), time.time())
        )

    async def add_item(self, guild_id, user_id, item_key, quantity=1, *, event_type="item_gain", metadata=None):
        item_key=str(item_key).lower().strip(); quantity=int(quantity)
        if quantity <= 0 or item_key not in ITEMS:
            return False
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO rpg_inventory VALUES(?,?,?,?) ON CONFLICT(guild_id,user_id,item_key) DO UPDATE SET quantity=quantity+excluded.quantity", (guild_id,user_id,item_key,quantity))
            await self._economy_log(db,guild_id,user_id,event_type,item_key=item_key,quantity=quantity,metadata=metadata)
            await db.commit()
        return True

    async def remove_item(self, guild_id, user_id, item_key, quantity=1, *, event_type="item_spend", metadata=None):
        item_key=str(item_key).lower().strip(); quantity=int(quantity)
        if quantity <= 0:
            return False
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT quantity FROM rpg_inventory WHERE guild_id=? AND user_id=? AND item_key=?", (guild_id,user_id,item_key))
            row = await cur.fetchone()
            if not row or int(row[0]) < quantity:
                return False
            await db.execute("UPDATE rpg_inventory SET quantity=quantity-? WHERE guild_id=? AND user_id=? AND item_key=?", (quantity,guild_id,user_id,item_key))
            await self._economy_log(db,guild_id,user_id,event_type,item_key=item_key,quantity=-quantity,metadata=metadata)
            await db.commit()
            return True

    async def add_rewards(self, guild_id, user_id, xp=0, gold=0):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET xp=xp+?, gold=gold+? WHERE guild_id=? AND user_id=?", (xp,gold,guild_id,user_id))
            cur = await db.execute("SELECT level,xp FROM rpg_players WHERE guild_id=? AND user_id=?", (guild_id,user_id)); p = await cur.fetchone()
            old_level = p[0]
            new_level = old_level
            while p[1] >= self._level_xp(new_level) and new_level < 100: new_level += 1
            levels = new_level - old_level
            if levels:
                # Every level gives automatic growth plus separate Stat, Skill and Talent points.  This makes progression
                # visible instead of merely changing the number on the sheet.
                await db.execute(
                    "UPDATE rpg_players SET level=?, max_hp=max_hp+?, hp=max_hp+?, max_mp=max_mp+?, mp=max_mp+?, atk=atk+?, defense=defense+?, speed=speed+?, skill_points=skill_points+?, stat_points=stat_points+?, talent_points=talent_points+? WHERE guild_id=? AND user_id=?",
                    (new_level, levels*12, levels*12, levels*5, levels*5, levels*2, levels, levels, levels, levels*3, levels, guild_id, user_id)
                )
            await db.commit()
            return old_level, new_level

    async def _queue_pending_reward(self, guild_id, user_id, reward_type, payload, *, source="combat"):
        """Persist a reward that could not be delivered automatically."""
        payload = dict(payload or {})
        try:
            async with aiosqlite.connect(self.path) as db:
                await db.execute(
                    "INSERT INTO rpg_pending_rewards(guild_id,user_id,reward_type,payload_json,source,created_at) VALUES(?,?,?,?,?,?)",
                    (guild_id,user_id,str(reward_type),json.dumps(payload,separators=(",",":"),sort_keys=True),str(source),time.time())
                )
                await db.commit()
            return True
        except Exception:
            # Never let a recovery-ledger failure break the already-resolved
            # victory result. The combat panel remains authoritative.
            log.exception("Could not save pending reward: guild=%s user=%s type=%s",guild_id,user_id,reward_type)
            return False

    async def pending_rewards(self, guild_id, user_id):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory=aiosqlite.Row
            cur=await db.execute(
                "SELECT id,reward_type,payload_json,source,created_at FROM rpg_pending_rewards WHERE guild_id=? AND user_id=? AND claimed_at=0 ORDER BY id",
                (guild_id,user_id)
            )
            rows=[]
            for row in await cur.fetchall():
                data=dict(row)
                try: data["payload"]=json.loads(data.pop("payload_json") or "{}")
                except Exception: data["payload"]={}
                rows.append(data)
            return rows

    async def claim_pending_rewards(self, guild_id, user_id):
        """Deliver all pending tangible rewards, keeping failed rows for retry."""
        pending=await self.pending_rewards(guild_id,user_id)
        if not pending:
            return False, "You have no pending rewards."
        delivered=[]; failed=[]
        for row in pending:
            rid=int(row["id"]); kind=row["reward_type"]; payload=row.get("payload",{}) or {}
            try:
                if kind=="xp_gold":
                    xp=max(0,int(payload.get("xp",0))); gold=max(0,int(payload.get("gold",0)))
                    await self.add_rewards(guild_id,user_id,xp,gold)
                    label=f"{xp:,} XP + {gold:,} Gold"
                elif kind=="item":
                    item=str(payload.get("item_key","")).lower(); qty=max(1,int(payload.get("quantity",1)))
                    if not await self.add_item(guild_id,user_id,item,qty,event_type="pending_reward"):
                        raise RuntimeError(f"Unknown item: {item}")
                    label=f"{ITEMS.get(item,{}).get('name',item)} ×{qty}"
                elif kind=="pet_xp":
                    amount=max(0,int(payload.get("amount",0)))
                    if amount:
                        await self._grant_pet_xp(guild_id,user_id,amount)
                    label=f"{amount} Pet XP"
                elif kind=="renown":
                    renown=int(payload.get("renown",0)); fame=int(payload.get("fame",0))
                    async with aiosqlite.connect(self.path) as db:
                        await db.execute("UPDATE rpg_players SET renown=renown+?,fame=fame+? WHERE guild_id=? AND user_id=?",(renown,fame,guild_id,user_id))
                        await db.commit()
                    label=f"{renown} Renown + {fame} Fame"
                else:
                    raise RuntimeError(f"Unknown pending reward type: {kind}")
                async with aiosqlite.connect(self.path) as db:
                    await db.execute("UPDATE rpg_pending_rewards SET claimed_at=? WHERE id=? AND guild_id=? AND user_id=? AND claimed_at=0",(time.time(),rid,guild_id,user_id))
                    await db.commit()
                delivered.append(label)
            except Exception:
                failed.append(f"#{rid} ({kind})")
                log.exception("Pending reward claim failed: guild=%s user=%s reward_id=%s",guild_id,user_id,rid)
        if not delivered:
            return False, "I couldn't deliver the pending rewards right now. They are still saved; try !rpg claim again later."
        message="Recovered: " + ", ".join(delivered)
        if failed:
            message += "\n\nStill pending: " + ", ".join(failed) + ". Nothing was deleted for those rewards."
        else:
            message += "\n\nAll pending rewards have been claimed."
        return True, message

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
        streak_bonus=random.randint(0,60); xp=180; gold=220+streak_bonus; gems=random.randint(60,110)
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
        faction=await self._faction_passive(guild_id,user_id)
        heal=int(item.get("heal",0)*quantity*(1+faction.get("heal_pct",0)/100)); mana=item.get("mana",0)*quantity; stamina=item.get("stamina",0)*quantity
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET hp=min(max_hp,hp+?),mp=min(max_mp,mp+?),stamina=min(100,stamina+?),last_stamina_tick=? WHERE guild_id=? AND user_id=?",(heal,mana,stamina,time.time(),guild_id,user_id)); await db.commit()
        return True,f"Used **{item['name']} ×{quantity}** — +{heal} HP, +{mana} MP, +{stamina} stamina."

    async def equip(self,guild_id,user_id,item_key):
        p=await self.player(guild_id,user_id)
        if not p: return False,"Start a hero first."
        item_key=item_key.lower().strip(); item=ITEMS.get(item_key)
        allowed={"weapon","armor","offhand","accessory","ring","amulet","relic"}
        if not item or item.get("slot") not in allowed: return False,"That item cannot be equipped. Check `!rpg items <category>`."
        req=int(item.get("level_req",1))
        if int(p["level"])<req:return False,f"**{item['name']}** requires level **{req}**. You are level **{p['level']}**."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("BEGIN IMMEDIATE")
            cur=await db.execute("SELECT quantity FROM rpg_inventory WHERE guild_id=? AND user_id=? AND item_key=?",(guild_id,user_id,item_key)); invrow=await cur.fetchone()
            if not invrow or int(invrow[0])<1:
                await db.rollback(); return False,"You don't own that item."
            slot=item["slot"]
            cur=await db.execute("SELECT instance_uid,upgrade_level,intrinsic_json,set_key,enchant_key,enchant_level FROM rpg_equipment_instances WHERE guild_id=? AND user_id=? AND item_key=? ORDER BY created_at ASC LIMIT 1",(guild_id,user_id,item_key))
            stored=await cur.fetchone()
            if stored:
                uid,upgrade,intrinsic_json,set_key,enchant_key,enchant_level=stored
                intrinsics=json.loads(intrinsic_json or "{}")
                upgrade=int(upgrade); enchant_level=int(enchant_level)
            else:
                uid=uuid.uuid4().hex; upgrade=0; intrinsics=_roll_intrinsics(item); set_key=_set_key_for_item(item,item_key); enchant_key=""; enchant_level=0
            cur=await db.execute("SELECT item_key,upgrade_level,intrinsic_json,set_key,instance_uid FROM rpg_equipment WHERE guild_id=? AND user_id=? AND slot=?",(guild_id,user_id,slot)); old=await cur.fetchone()
            if old:
                cur=await db.execute("SELECT enchant_key,level FROM rpg_equipment_enchants WHERE guild_id=? AND user_id=? AND slot=?",(guild_id,user_id,slot)); oe=await cur.fetchone()
                await db.execute("INSERT OR REPLACE INTO rpg_equipment_instances(instance_uid,guild_id,user_id,slot,item_key,upgrade_level,intrinsic_json,set_key,enchant_key,enchant_level,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(old[4] or uuid.uuid4().hex,guild_id,user_id,slot,old[0],int(old[1]),old[2] or "{}",old[3] or "",oe[0] if oe else "",int(oe[1]) if oe else 0,time.time()))
                await db.execute("DELETE FROM rpg_equipment_enchants WHERE guild_id=? AND user_id=? AND slot=?",(guild_id,user_id,slot))
                await db.execute("INSERT INTO rpg_inventory VALUES(?,?,?,1) ON CONFLICT(guild_id,user_id,item_key) DO UPDATE SET quantity=quantity+1",(guild_id,user_id,old[0]))
            await db.execute("UPDATE rpg_inventory SET quantity=quantity-1 WHERE guild_id=? AND user_id=? AND item_key=?",(guild_id,user_id,item_key))
            await db.execute("INSERT INTO rpg_equipment(guild_id,user_id,slot,item_key,upgrade_level,intrinsic_json,set_key,instance_uid) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(guild_id,user_id,slot) DO UPDATE SET item_key=excluded.item_key,upgrade_level=excluded.upgrade_level,intrinsic_json=excluded.intrinsic_json,set_key=excluded.set_key,instance_uid=excluded.instance_uid",(guild_id,user_id,slot,item_key,upgrade,json.dumps(intrinsics,separators=(",",":")),set_key,uid))
            if stored: await db.execute("DELETE FROM rpg_equipment_instances WHERE instance_uid=?",(uid,))
            if enchant_key and enchant_level>0:
                await db.execute("INSERT OR REPLACE INTO rpg_equipment_enchants(guild_id,user_id,slot,enchant_key,level) VALUES(?,?,?,?,?)",(guild_id,user_id,slot,enchant_key,enchant_level))
            await self._economy_log(db,guild_id,user_id,"equip",item_key=item_key,quantity=-1,metadata={"slot":slot,"instance_uid":uid,"intrinsics":intrinsics,"set_key":set_key})
            await db.commit()
        intrinsic_text=" • ".join(f"+{v}{('%' if k.endswith('_pct') else '')} {k.replace('_pct','').replace('_flat','').upper()}" for k,v in intrinsics.items()) or "None"
        set_text=f" • Set: {set_key.replace('_set','').title()}" if set_key else ""
        return True,f"Equipped **{item['name']}** in **{slot}**.\n✨ Intrinsics: {intrinsic_text}{set_text}"

    async def unequip_slot(self, guild_id, user_id, slot):
        slot=str(slot or "").strip().lower()
        allowed={"weapon","armor","offhand","accessory","ring","amulet","relic"}
        if slot not in allowed:
            return False, "That is not a valid equipment slot."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("BEGIN IMMEDIATE")
            cur=await db.execute("SELECT item_key,upgrade_level,intrinsic_json,set_key,instance_uid FROM rpg_equipment WHERE guild_id=? AND user_id=? AND slot=?", (guild_id,user_id,slot))
            row=await cur.fetchone()
            if not row:
                await db.rollback(); return False, f"Nothing is equipped in **{slot.title()}**."
            cur=await db.execute("SELECT enchant_key,level FROM rpg_equipment_enchants WHERE guild_id=? AND user_id=? AND slot=?",(guild_id,user_id,slot)); ench=await cur.fetchone()
            uid=row[4] or uuid.uuid4().hex
            await db.execute("INSERT OR REPLACE INTO rpg_equipment_instances(instance_uid,guild_id,user_id,slot,item_key,upgrade_level,intrinsic_json,set_key,enchant_key,enchant_level,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(uid,guild_id,user_id,slot,row[0],int(row[1]),row[2] or "{}",row[3] or "",ench[0] if ench else "",int(ench[1]) if ench else 0,time.time()))
            await db.execute("INSERT INTO rpg_inventory VALUES(?,?,?,1) ON CONFLICT(guild_id,user_id,item_key) DO UPDATE SET quantity=quantity+1",(guild_id,user_id,row[0]))
            await db.execute("DELETE FROM rpg_equipment WHERE guild_id=? AND user_id=? AND slot=?", (guild_id,user_id,slot))
            await db.execute("DELETE FROM rpg_equipment_enchants WHERE guild_id=? AND user_id=? AND slot=?", (guild_id,user_id,slot))
            await self._economy_log(db,guild_id,user_id,"unequip",item_key=row[0],quantity=1,metadata={"slot":slot,"instance_uid":uid,"returned_to_inventory":True})
            await db.commit()
        return True, f"Unequipped **{ITEMS.get(row[0], {'name':row[0]}).get('name',row[0])}** from **{slot.title()}** and returned it to your inventory. Its upgrades and properties are preserved."

    async def equipment_details(self,guild_id,user_id):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory=aiosqlite.Row
            cur=await db.execute("SELECT * FROM rpg_equipment WHERE guild_id=? AND user_id=? ORDER BY slot",(guild_id,user_id))
            return [dict(r) for r in await cur.fetchall()]

    async def upgrade_equipment(self,guild_id,user_id,slot):
        slot=str(slot or "").lower().strip()
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("BEGIN IMMEDIATE")
            cur=await db.execute("SELECT * FROM rpg_equipment WHERE guild_id=? AND user_id=? AND slot=?",(guild_id,user_id,slot))
            gear=await cur.fetchone()
            if not gear: await db.rollback(); return False,f"Nothing is equipped in **{slot.title()}**."
            keys=[d[0] for d in cur.description]; gear=dict(zip(keys,gear))
            current=int(gear.get("upgrade_level",0)); item=ITEMS.get(gear["item_key"],{})
            if current>=UPGRADE_MAX: await db.rollback(); return False,f"**{item.get('name',gear['item_key'])}** is already +{UPGRADE_MAX}."
            rarity=item.get("rarity","common"); mat,mat_need=UPGRADE_MATERIALS.get(rarity,UPGRADE_MATERIALS["common"])
            gold_cost=UPGRADE_COST_BASE*(current+1)*max(1, list(RARITIES).index(rarity)+1)
            cur=await db.execute("SELECT quantity FROM rpg_inventory WHERE guild_id=? AND user_id=? AND item_key=?",(guild_id,user_id,mat)); row=await cur.fetchone()
            if not row or int(row[0])<mat_need: await db.rollback(); return False,f"Upgrade +{current+1} needs **{mat_need}× {ITEMS.get(mat,{'name':mat}).get('name',mat)}**."
            if int(p["gold"])<gold_cost: await db.rollback(); return False,f"Upgrade +{current+1} costs **{gold_cost} gold**."
            # Deterministic success: the cost scales instead of using frustrating
            # destruction. Rare+ gear gets a small protection discount at high levels.
            await db.execute("UPDATE rpg_inventory SET quantity=quantity-? WHERE guild_id=? AND user_id=? AND item_key=?",(mat_need,guild_id,user_id,mat))
            await db.execute("UPDATE rpg_players SET gold=gold-? WHERE guild_id=? AND user_id=?",(gold_cost,guild_id,user_id))
            new_level=current+1
            await db.execute("UPDATE rpg_equipment SET upgrade_level=? WHERE guild_id=? AND user_id=? AND slot=?",(new_level,guild_id,user_id,slot))
            await self._economy_log(db,guild_id,user_id,"equipment_upgrade",item_key=gear["item_key"],quantity=1,gold_delta=-gold_cost,metadata={"slot":slot,"from":current,"to":new_level,"material":mat,"material_qty":mat_need})
            await self._economy_log(db,guild_id,user_id,"upgrade_material_spend",item_key=mat,quantity=-mat_need,metadata={"slot":slot,"upgrade":new_level})
            await db.commit()
        return True,f"⬆️ **{item.get('name',gear['item_key'])}** upgraded to **+{new_level}**.\nCost: {gold_cost} gold + {mat_need}× {ITEMS.get(mat,{'name':mat}).get('name',mat)}"

    async def equipment_sets(self,guild_id,user_id):
        details=await self.equipment_details(guild_id,user_id)
        counts={}
        for g in details:
            if g.get("set_key"): counts[g["set_key"]]=counts.get(g["set_key"],0)+1
        return [(k,c,_set_focus(k)) for k,c in sorted(counts.items(),key=lambda x:(-x[1],x[0]))]

    async def gear_vault(self,guild_id,user_id):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory=aiosqlite.Row
            cur=await db.execute("SELECT * FROM rpg_equipment_storage WHERE guild_id=? AND user_id=? ORDER BY created_at DESC",(guild_id,user_id))
            return [dict(r) for r in await cur.fetchall()]

    async def equip_vault(self,guild_id,user_id,instance_uid):
        instance_uid=str(instance_uid).strip()
        if not instance_uid:return False,"Provide a gear vault ID. Use `!rpg vault`."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("BEGIN IMMEDIATE")
            cur=await db.execute("SELECT * FROM rpg_equipment_storage WHERE guild_id=? AND user_id=? AND instance_uid=?",(guild_id,user_id,instance_uid)); row=await cur.fetchone()
            if not row: await db.rollback(); return False,"Gear vault item not found."
            cols=[d[0] for d in cur.description]; data=dict(zip(cols,row)); slot=data["slot"]
            cur=await db.execute("SELECT item_key,upgrade_level,intrinsic_json,set_key,instance_uid FROM rpg_equipment WHERE guild_id=? AND user_id=? AND slot=?",(guild_id,user_id,slot)); old=await cur.fetchone()
            if old:
                await db.execute("INSERT OR REPLACE INTO rpg_equipment_storage(instance_uid,guild_id,user_id,slot,item_key,upgrade_level,intrinsic_json,set_key,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(old[4] or uuid.uuid4().hex,guild_id,user_id,slot,old[0],int(old[1]),old[2] or "{}",old[3] or "",time.time()))
                await db.execute("DELETE FROM rpg_equipment_enchants WHERE guild_id=? AND user_id=? AND slot=?",(guild_id,user_id,slot))
            await db.execute("INSERT INTO rpg_equipment(guild_id,user_id,slot,item_key,upgrade_level,intrinsic_json,set_key,instance_uid) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(guild_id,user_id,slot) DO UPDATE SET item_key=excluded.item_key,upgrade_level=excluded.upgrade_level,intrinsic_json=excluded.intrinsic_json,set_key=excluded.set_key,instance_uid=excluded.instance_uid",(guild_id,user_id,slot,data["item_key"],int(data["upgrade_level"]),data["intrinsic_json"],data["set_key"],data["instance_uid"]))
            await db.execute("DELETE FROM rpg_equipment_storage WHERE guild_id=? AND user_id=? AND instance_uid=?",(guild_id,user_id,instance_uid))
            await self._economy_log(db,guild_id,user_id,"vault_equip",item_key=data["item_key"],quantity=1,metadata={"slot":slot,"instance_uid":instance_uid})
            await db.commit()
        return True,f"Equipped **{ITEMS.get(data['item_key'],{'name':data['item_key']}).get('name',data['item_key'])} +{data['upgrade_level']}** from the gear vault."

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
        await self._refresh_stamina(guild_id,user_id)
        p=await self.player(guild_id,user_id)
        if not p:return None
        gear={}
        enchants=[]
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT slot,item_key FROM rpg_equipment WHERE guild_id=? AND user_id=?",(guild_id,user_id)); gear=dict(await cur.fetchall())
            cur=await db.execute("SELECT slot,item_key,upgrade_level,intrinsic_json,set_key FROM rpg_equipment WHERE guild_id=? AND user_id=?",(guild_id,user_id)); gear_rows=await cur.fetchall()
            gear_details={r[0]:r for r in gear_rows}
            cur=await db.execute("SELECT slot,enchant_key,level FROM rpg_equipment_enchants WHERE guild_id=? AND user_id=?",(guild_id,user_id)); enchants=await cur.fetchall()
        bonus=self._progression_bonus(p)
        pct={"atk":0,"defense":0,"hp":0,"mp":0,"speed":0,"crit":0}
        set_counts={}
        for slot,key in gear.items():
            item=ITEMS.get(key,{})
            row=gear_details.get(slot)
            upgrade=int(row[2]) if row else 0
            bonus["atk"]+=item.get("atk",0)+upgrade*max(1,item.get("atk",0)//8)
            bonus["defense"]+=item.get("def",0)+upgrade*max(1,item.get("def",0)//8)
            bonus["hp"]+=item.get("hp",0)+upgrade*max(2,item.get("hp",0)//10)
            bonus["mp"]+=item.get("mp",0)+upgrade*max(1,item.get("mp",0)//10)
            bonus["speed"]+=item.get("spd",0)+upgrade//3
            bonus["crit"]+=item.get("crit",0)+upgrade//4
            pct["atk"]+=min(10,int(item.get("pct_atk",0))); pct["defense"]+=min(10,int(item.get("pct_def",0))); pct["hp"]+=min(10,int(item.get("pct_hp",0))); pct["mp"]+=min(10,int(item.get("pct_mp",0))); pct["speed"]+=min(10,int(item.get("pct_speed",0))); pct["crit"]+=min(10,int(item.get("pct_crit",0)))
            if row and row[4]:
                try:
                    intr=json.loads(row[3] or "{}")
                except json.JSONDecodeError:
                    intr={}
                pct["atk"]+=int(intr.get("atk_pct",0)); pct["defense"]+=int(intr.get("def_pct",0)); pct["hp"]+=int(intr.get("hp_pct",0)); pct["speed"]+=int(intr.get("speed_pct",0)); bonus["crit"]+=int(intr.get("crit_flat",0))
                set_counts[row[4]]=set_counts.get(row[4],0)+1
        for set_key,count in set_counts.items():
            focus=_set_focus(set_key)
            if count>=2: pct[focus]+=2
            if count>=4: pct[focus]+=5
            if count>=6: pct[focus]+=8
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
        faction=await self._faction_passive(guild_id,user_id)
        bonus["faction_passive"]=faction.get("name","")
        bonus["faction_desc"]=faction.get("desc","")
        if faction.get("def_pct"): bonus["defense"]+=round(bonus["defense"]*faction["def_pct"]/100)
        if faction.get("heal_pct"): bonus["heal_pct"]=faction["heal_pct"]
        if faction.get("skill_pct"): bonus["skill_pct"]=faction["skill_pct"]
        return p,gear,bonus

    async def change_identity(self,guild_id,user_id,kind,value):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        kind=kind.lower(); value=value.lower().strip()
        costs={"race":1500,"class":1200,"subrace":2200,"subclass":3000,"evolution":5000}
        if kind not in costs:return False,"Change one of: race, subrace, class, subclass, evolution."
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
        # Legacy quest rows remain in the database for save compatibility.
        # The visible Quest Board is now driven by Quest 2.0 rotations.
        return

    async def quests(self,guild_id,user_id):
        await self.quest_seed(guild_id)
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT q.id,q.title,q.description,q.level_req,q.target,q.progress_type,q.reward_xp,q.reward_gold,q.reward_item,q.reward_qty,COALESCE(p.progress,0),COALESCE(p.status,'available'),q.kind,q.chain_key,q.chain_step FROM rpg_quests q LEFT JOIN rpg_player_quests p ON q.id=p.quest_id AND p.guild_id=? AND p.user_id=? WHERE q.guild_id=? AND q.expires_at>? ORDER BY CASE q.kind WHEN 'daily' THEN 1 WHEN 'weekly' THEN 2 ELSE 3 END,q.id",(guild_id,user_id,guild_id,time.time())); return await cur.fetchall()

    async def accept_quest(self,guild_id,user_id,qid):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT id,level_req,chain_key,chain_step,title FROM rpg_quests WHERE guild_id=? AND id=?",(guild_id,qid)); q=await cur.fetchone()
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
        await self.progress_objectives(guild_id,user_id,ptype,amount)
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

    def _objective_period_key(self, period):
        return str(rotation_key(period))

    async def quest2_categories(self, guild_id, user_id):
        """Return the complete, readable Quest 2.0 board for one hero."""
        await self.ensure_objectives(guild_id, user_id)
        keys={p:self._objective_period_key(p) for p in ("daily","weekly","monthly")}
        async with aiosqlite.connect(self.path) as db:
            db.row_factory=aiosqlite.Row
            cur=await db.execute(
                "SELECT period,objective_key,title,description,target,progress,reward_xp,reward_gold,reward_item,reward_qty,claimed,period_key FROM rpg_objectives WHERE guild_id=? AND user_id=? AND period_key IN (?,?,?) ORDER BY CASE period WHEN 'daily' THEN 0 WHEN 'weekly' THEN 1 ELSE 2 END, objective_key",
                (guild_id,user_id,keys["daily"],keys["weekly"],keys["monthly"]),
            )
            rows=[dict(x) for x in await cur.fetchall()]
            cur=await db.execute("SELECT class_name,race,subclass,subrace,level FROM rpg_players WHERE guild_id=? AND user_id=?",(guild_id,user_id))
            player=await cur.fetchone()
            cur=await db.execute("SELECT faction_key,reputation,rank FROM rpg_faction_members WHERE guild_id=? AND user_id=?",(guild_id,user_id))
            faction=await cur.fetchone()
            cur=await db.execute("SELECT id,target_name,reward,status FROM rpg_bounties WHERE guild_id=? AND status='open' ORDER BY reward DESC,id DESC LIMIT 6",(guild_id,))
            bounties=[dict(x) for x in await cur.fetchall()]

        story=[
            {"title":"The First Step","description":"Defeat 3 enemies and prove you can survive outside Horizon Village.","target":3,"progress":0,"reward_xp":300,"reward_gold":500,"reward_item":"life_potion","reward_qty":2,"state":"MAIN"},
            {"title":"Into the Wild","description":"Explore or travel through the world 5 times.","target":5,"progress":0,"reward_xp":700,"reward_gold":1000,"reward_item":"arcane_shard","reward_qty":2,"state":"MAIN"},
            {"title":"Echoes of the Ancient","description":"Clear 3 dungeon floors and uncover the old ruins.","target":3,"progress":0,"reward_xp":1200,"reward_gold":1800,"reward_item":"reinforcement_core","reward_qty":2,"state":"MAIN"},
        ]
        if player:
            class_key=str(player["class_name"] or "warrior").lower()
            race_key=str(player["race"] or "human").lower()
            class_name=class_key.replace("_"," ").title()
            race_name=race_key.replace("_"," ").title()
            level=int(player["level"] or 1)
            class_quests=[
                {"title":f"{class_name} Trial: Master Your Path","description":f"Win 5 battles while progressing as a {class_name}.","reward_xp":500,"reward_gold":750,"state":"AVAILABLE"},
                {"title":f"{class_name} Trial: Veteran","description":f"Reach level {max(10,level + 5)} to deepen your {class_name} mastery.","reward_xp":900,"reward_gold":1200,"state":"AVAILABLE"},
                {"title":f"{class_name} Trial: Signature","description":f"Use your class skills in 10 successful battles.","reward_xp":1400,"reward_gold":1800,"state":"AVAILABLE"},
            ]
            race_quests=[
                {"title":f"{race_name} Heritage: Awakening","description":f"Complete 5 adventures while carrying the legacy of the {race_name}.","reward_xp":450,"reward_gold":650,"state":"AVAILABLE"},
                {"title":f"{race_name} Heritage: Prove Yourself","description":f"Reach level {max(8,level + 3)}.","reward_xp":750,"reward_gold":1000,"state":"AVAILABLE"},
                {"title":f"{race_name} Heritage: Mastery","description":f"Complete 15 battles using the strengths of your {race_name} lineage.","reward_xp":1200,"reward_gold":1600,"state":"AVAILABLE"},
            ]
        else:
            class_quests=[{"title":"Class Quests Locked","description":"Create a hero to unlock quests based on your class.","state":"LOCKED"}]
            race_quests=[{"title":"Race Quests Locked","description":"Create a hero to unlock quests based on your race.","state":"LOCKED"}]
        if faction:
            faction_key=str(faction["faction_key"])
            faction_name=faction_key.replace("_"," ").title()
            rep=int(faction["reputation"] or 0)
            faction_quests=[
                {"title":f"{faction_name}: Earn Your Standing","description":f"Raise your reputation with {faction_name} beyond your current {rep} reputation.","reward_xp":650,"reward_gold":900,"state":"AVAILABLE"},
                {"title":f"{faction_name}: Serve the Cause","description":"Complete 5 RPG activities while representing your faction.","reward_xp":1000,"reward_gold":1500,"state":"AVAILABLE"},
                {"title":f"{faction_name}: Trusted Ally","description":"Reach 100 reputation with your faction.","reward_xp":1800,"reward_gold":2500,"state":"AVAILABLE"},
            ]
        else:
            faction_quests=[
                {"title":"Choose Your Allegiance","description":"Join a faction with !rpg factions, then use !rpg factionjoin <faction_key> to unlock faction quests.","reward_xp":0,"reward_gold":0,"state":"LOCKED"},
                {"title":"Horizon Guard","description":"A defensive faction focused on protecting settlements.","state":"INFO"},
                {"title":"Free Merchants","description":"A trade-focused faction built around commerce and markets.","state":"INFO"},
            ]
        bounty=[{"title":f"Bounty #{b['id']}: {b['target_name']}","description":f"Track down {b['target_name']} and claim the posted bounty.","reward_gold":int(b["reward"] or 0),"state":"OPEN"} for b in bounties]
        if not bounty:
            bounty=[{"title":"No Open Bounties","description":"There are no player-posted bounties right now. New bounties will appear here when someone posts one.","state":"INFO"}]
        secret=[
            {"title":"??? — The Whispering Door","description":"A hidden path is watching. Discover unusual places and investigate strange events.","reward_xp":1000,"reward_gold":1500,"state":"HIDDEN"},
            {"title":"??? — The Nameless Echo","description":"Some secrets reveal themselves only after you meet their hidden conditions.","reward_xp":1500,"reward_gold":2200,"state":"HIDDEN"},
            {"title":"??? — Beyond the Horizon","description":"The final clue has not been revealed. Keep exploring.","reward_xp":2500,"reward_gold":4000,"state":"HIDDEN"},
        ]
        legendary=[
            {"title":"Legendary Trial: World Challenger","description":"Defeat a world boss and prove you can stand against a regional threat.","reward_xp":3000,"reward_gold":5000,"state":"LEGENDARY"},
            {"title":"Legendary Trial: Dungeon Conqueror","description":"Clear 10 dungeon floors without abandoning the run.","reward_xp":4500,"reward_gold":7000,"state":"LEGENDARY"},
            {"title":"Legendary Trial: Horizon's Edge","description":"Reach level 50 and enter an endgame region.","reward_xp":6000,"reward_gold":10000,"state":"LEGENDARY"},
        ]
        return {"story":story,"daily":[x for x in rows if x["period"]=="daily"],"weekly":[x for x in rows if x["period"]=="weekly"],"monthly":[x for x in rows if x["period"]=="monthly"],"class":class_quests,"race":race_quests,"faction":faction_quests,"bounty":bounty,"secret":secret,"legendary":legendary}

    async def claim_quest2_objective(self, guild_id, user_id, period, objective_key, period_key=None):
        """Claim a completed Quest 2.0 rotating objective exactly once."""
        period=str(period).lower()
        if period not in {"daily","weekly","monthly"}:
            return False, "This quest is not a claimable rotating objective."
        if period_key is None:
            period_key=self._objective_period_key(period)
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute(
                "SELECT target,progress,reward_xp,reward_gold,reward_item,reward_qty,claimed,title FROM rpg_objectives WHERE guild_id=? AND user_id=? AND period=? AND objective_key=? AND period_key=?",
                (guild_id,user_id,period,objective_key,period_key),
            )
            row=await cur.fetchone()
            if not row:
                return False, "Quest not found or it has rotated out."
            target,progress,xp,gold,item,qty,claimed,title=row
            if int(claimed):
                return False, "You already claimed this quest."
            if int(progress) < int(target):
                return False, f"Quest is not complete yet: {progress}/{target}."
            await db.execute(
                "UPDATE rpg_objectives SET claimed=1 WHERE guild_id=? AND user_id=? AND period=? AND objective_key=? AND period_key=? AND claimed=0",
                (guild_id,user_id,period,objective_key,period_key),
            )
            await db.commit()
        await self.add_rewards(guild_id,user_id,int(xp or 0),0)
        if int(gold or 0):
            async with aiosqlite.connect(self.path) as db:
                await db.execute("UPDATE rpg_players SET gold=gold+? WHERE guild_id=? AND user_id=?",(int(gold),guild_id,user_id))
                await db.commit()
        if item:
            await self.add_item(guild_id,user_id,item,int(qty or 1),event_type="quest_reward")
        reward_parts=[]
        if int(xp or 0): reward_parts.append(f"+{int(xp)} XP")
        if int(gold or 0): reward_parts.append(f"+{int(gold)} gold")
        if item:
            reward_parts.append(f"{ITEMS.get(item,{'name':item}).get('name',item)} ×{int(qty or 1)}")
        return True, f"Claimed **{title}** — " + (" • ".join(reward_parts) if reward_parts else "no reward")

    def rotation_status(self):
        return {p: rotation_info(p) for p in ("shop","daily","weekly","monthly")}

    def _rotated_objective_templates(self, period):
        templates=list(OBJECTIVE_TEMPLATES[period])
        count=min(OBJECTIVE_ROTATION_COUNTS.get(period,len(templates)),len(templates))
        rng=random.Random(f"horizon-objectives:{period}:{rotation_key(period)}")
        return rng.sample(templates,count)

    async def ensure_objectives(self,guild_id,user_id):
        now=time.time()
        async with aiosqlite.connect(self.path) as db:
            for period in ("daily","weekly","monthly"):
                period_key=self._objective_period_key(period)
                for key,title,desc,ptype,target,xp,gold,item,qty in self._rotated_objective_templates(period):
                    await db.execute("INSERT OR IGNORE INTO rpg_objectives(guild_id,user_id,period,objective_key,title,description,progress_type,target,progress,reward_xp,reward_gold,reward_item,reward_qty,claimed,period_key,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(guild_id,user_id,period,key,title,desc,ptype,target,0,xp,gold,item,qty,0,period_key,now))
            await db.commit()

    async def progress_objectives(self,guild_id,user_id,ptype,amount=1):
        await self.ensure_objectives(guild_id,user_id)
        keys=(self._objective_period_key("daily"),self._objective_period_key("weekly"),self._objective_period_key("monthly"))
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_objectives SET progress=MIN(target,progress+?) WHERE guild_id=? AND user_id=? AND progress_type=? AND claimed=0 AND period_key IN (?,?,?)",(max(1,int(amount)),guild_id,user_id,ptype,*keys))
            await db.commit()

    async def objectives(self,guild_id,user_id):
        await self.ensure_objectives(guild_id,user_id)
        keys=(self._objective_period_key("daily"),self._objective_period_key("weekly"),self._objective_period_key("monthly"))
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT period,objective_key,title,description,target,progress,reward_xp,reward_gold,reward_item,reward_qty,claimed,period_key FROM rpg_objectives WHERE guild_id=? AND user_id=? AND period_key IN (?,?,?) ORDER BY CASE period WHEN 'daily' THEN 0 WHEN 'weekly' THEN 1 ELSE 2 END,objective_key",(guild_id,user_id,*keys))
            return await cur.fetchall()

    async def claim_objective(self,guild_id,user_id,objective_key):
        await self.ensure_objectives(guild_id,user_id)
        keys=(self._objective_period_key("daily"),self._objective_period_key("weekly"),self._objective_period_key("monthly"))
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT period,objective_key,target,progress,reward_xp,reward_gold,reward_item,reward_qty,claimed,period_key FROM rpg_objectives WHERE guild_id=? AND user_id=? AND objective_key=? AND period_key IN (?,?,?)",(guild_id,user_id,objective_key,*keys))
            row=await cur.fetchone()
            if not row:return False,"Objective not found in the current Quest 2.0 rotations. Use !rpg objectives."
            period,key,target,progress,xp,gold,item,qty,claimed,row_period=row
            if claimed:return False,"That objective has already been claimed."
            if progress<target:return False,f"Progress: {progress}/{target}."
            await db.execute("UPDATE rpg_objectives SET claimed=1 WHERE guild_id=? AND user_id=? AND objective_key=? AND period_key=?",(guild_id,user_id,key,row_period))
            await db.execute("UPDATE rpg_players SET gold=gold+? WHERE guild_id=? AND user_id=?",(gold,guild_id,user_id))
            await db.commit()
        await self.add_rewards(guild_id,user_id,xp,0)
        if item: await self.add_item(guild_id,user_id,item,qty)
        return True,f"Objective complete: **{key.replace('_',' ').title()}** — +{xp} XP • +{gold} gold" + (f" • {ITEMS.get(item,{'name':item}).get('name',item)} ×{qty}" if item else "")


    async def world_map(self,guild_id,user_id):
        p=await self.player(guild_id,user_id)
        if not p:return None
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT area_key FROM rpg_area_discoveries WHERE guild_id=? AND user_id=?",(guild_id,user_id)); discovered={r[0] for r in await cur.fetchall()}
        return p.get("area_key","horizon_village"),discovered

    async def explore(self,guild_id,user_id):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        await self._refresh_stamina(guild_id,user_id); p=await self.player(guild_id,user_id)
        current=p.get("area_key","horizon_village") or "horizon_village"
        neighbors=AREA_CONNECTIONS.get(current,[])
        eligible=[k for k in neighbors if k in AREAS and int(AREAS[k]["level"])<=int(p["level"])+3]
        if not eligible:return False,"There are no new level-appropriate routes from this region yet. Check `!rpg map` for the world atlas."
        if int(p["stamina"])<EXPLORE_STAMINA_COST:return False,f"You need **{EXPLORE_STAMINA_COST} stamina** to explore. Rest or wait for stamina to recover."
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT area_key FROM rpg_area_discoveries WHERE guild_id=? AND user_id=?",(guild_id,user_id)); known={r[0] for r in await cur.fetchall()}
            unknown=[k for k in eligible if k not in known]
            target=random.choice(unknown or eligible); fresh=target not in known
            await db.execute("UPDATE rpg_players SET stamina=stamina-?,last_stamina_tick=? WHERE guild_id=? AND user_id=?",(EXPLORE_STAMINA_COST,time.time(),guild_id,user_id))
            await db.execute("INSERT OR IGNORE INTO rpg_area_discoveries(guild_id,user_id,area_key,discovered_at,source) VALUES(?,?,?,?,?)",(guild_id,user_id,target,time.time(),"exploration")); await db.commit()
        area=AREAS[target]
        if fresh:
            xp=80+int(area["level"])*8; gold=60+int(area["level"])*6
            await self.add_rewards(guild_id,user_id,xp,gold)
            await self.progress_quests(guild_id,user_id,"explore",1)
            pool=[x for x in self._area_resource_pool(target) if x in ITEMS]
            if pool: await self.add_item(guild_id,user_id,random.choice(pool),1,event_type="exploration_find")
            async with aiosqlite.connect(self.path) as db:
                await db.execute("UPDATE rpg_players SET renown=renown+5,fame=fame+2 WHERE guild_id=? AND user_id=?",(guild_id,user_id)); await db.commit()
            return True,f"🧭 You discovered **{area['name']}**!\n{area['desc']}\n\n+{xp} XP • +{gold} Gold • +5 Renown • +2 Fame\nYou also found a regional resource."
        # Re-exploration is still useful: it can produce a small resource find.
        pool=[x for x in self._area_resource_pool(target) if x in ITEMS]
        found=random.choice(pool) if pool and random.random()<0.55 else None
        if found: await self.add_item(guild_id,user_id,found,1,event_type="exploration_find")
        await self.progress_quests(guild_id,user_id,"explore",1)
        return True,f"🧭 You explored near **{area['name']}**. {('You found **'+ITEMS[found]['name']+'**.' if found else 'The route revealed nothing valuable this time.')}\n−{EXPLORE_STAMINA_COST} stamina."

    def _area_resource_pool(self,area_key):
        area=AREAS.get(area_key,{})
        t=area.get("type","wild")
        pools={
            "town":["herb","food_grilled_fish"],"plains":["herb","wolf_pelt"],"forest":["herb","wolf_pelt","forest_egg"],
            "cave":["iron_ore","arcane_shard"],"mountain":["iron_ore","mat_frostwood"],"coast":["food_grilled_fish","mat_sea_pearl"],
            "islands":["food_grilled_fish","mat_sea_pearl"],"swamp":["herb","mat_nightshade"],"volcanic":["iron_ore","mat_obsidian"],
            "desert":["mat_crystal_melon","mat_amber"],"undersea":["mat_sea_pearl","food_grilled_fish"],"sky":["mat_star_fragment","mat_angel_feather"],
            "hell":["mat_demon_horn","mat_void_crystal"],"void":["mat_void_crystal","mat_star_fragment"],"astral":["mat_star_fragment","mat_void_crystal"],
            "mythic":["mat_world_tree_seed","mat_star_fragment"],"graveyard":["mat_ancient_bone","mat_void_crystal"],"arcane":["arcane_shard","mat_star_fragment"],
        }
        return pools.get(t,["herb","iron_ore"])

    async def world_boss_active(self,guild_id):
        now=time.time()
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_world_events SET status='expired' WHERE guild_id=? AND status='active' AND expires_at<=?",(guild_id,now))
            cur=await db.execute("SELECT * FROM rpg_world_events WHERE guild_id=? AND status='active' ORDER BY id DESC LIMIT 1",(guild_id,)); row=await cur.fetchone(); await db.commit()
        return row

    async def world_boss_spawn(self,guild_id,user_id,template_key=None):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first.",None
        active=await self.world_boss_active(guild_id)
        if active:return False,f"A world boss is already active: **{active[3]}**.",active
        candidates=[x for x in WORLD_BOSS_TEMPLATES if int(x[3])<=max(1,int(p["level"])+20)] or WORLD_BOSS_TEMPLATES[:1]
        if template_key:
            chosen=next((x for x in WORLD_BOSS_TEMPLATES if x[0]==template_key.lower()),None)
            if not chosen:return False,"Unknown world boss template.",None
        else: chosen=random.choice(candidates)
        key,name,area,level,desc=chosen
        max_hp=max(25000,int(level)*420)
        now=time.time()
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("INSERT INTO rpg_world_events(guild_id,event_key,name,description,area_key,level,max_hp,hp,status,started_at,expires_at,created_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(guild_id,key,name,desc,area,level,max_hp,max_hp,"active",now,now+3600,user_id)); eid=cur.lastrowid; await db.commit()
        await self.progress_objectives(guild_id,user_id,"worldboss",1)
        return True,f"🌎 **WORLD BOSS SPAWNED** — **{name}**\nLv {level} • HP {max_hp:,}\n📍 {AREAS.get(area,{'name':area})['name']}\n\n{desc}\nExpires in 60 minutes.",await self.world_boss_active(guild_id)

    async def world_boss_attack(self,guild_id,user_id,skill_key=""):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first.",None
        event=await self.world_boss_active(guild_id)
        if not event:return False,"No world boss is active. Use `!rpg worldboss spawn` to summon one.",None
        eid,gid,event_key,name,desc,area,level,max_hp,hp,status,started,expires,created_by=event
        now=time.time()
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT last_attack FROM rpg_world_event_participants WHERE event_id=? AND user_id=?",(eid,user_id)); prev=await cur.fetchone()
            if prev and now-float(prev[0])<10:return False,f"Your next world-boss attack is ready in **{int(10-(now-float(prev[0])))+1}s**.",event
        pet=await self._pet_bonus(guild_id,user_id); stats=await self._combat_full_stats(guild_id,user_id,p,pet)
        skill=None
        if skill_key:
            skill=self._skill_for_player(p,skill_key.lower().strip())
            if not skill:return False,"That skill doesn't exist for your class.",event
            equipped={x["key"] for _s,x in await self.skill_loadout(guild_id,user_id) if x}
            if skill["key"] not in equipped:return False,"That skill isn't equipped.",event
            if int(p["mp"])<int(skill["cost"]):return False,f"You need {skill['cost']} MP.",event
        # World-boss damage is intentionally capped so a single player cannot delete the event.
        pseudo={"enemy": {"name":name,"level":level,"hp":max_hp,"atk":max(10,int(level*2.2)),"def":max(5,int(level*1.4))},"enemy_hp":hp,"buffs":{},"enemy_debuffs":{}}
        if skill:
            pseudo["enemy"]["def"]=max(1,int(level*1.2)); damage=self._skill_damage(stats,pseudo["enemy"],skill,pseudo); damage=max(1,min(int(max_hp*.045),damage)); cost=int(skill["cost"])
            async with aiosqlite.connect(self.path) as db: await db.execute("UPDATE rpg_players SET mp=max(0,mp-?) WHERE guild_id=? AND user_id=?",(cost,guild_id,user_id)); await db.commit()
            action_name=skill["name"]
        else:
            damage=max(1,min(int(max_hp*.025),self._damage(stats["atk"],int(level*1.2),1.0)))
            action_name="Basic Attack"
        new_hp=max(0,int(hp)-damage)
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO rpg_world_event_participants(event_id,guild_id,user_id,damage,attacks,last_attack) VALUES(?,?,?,?,?,?) ON CONFLICT(event_id,user_id) DO UPDATE SET damage=damage+excluded.damage,attacks=attacks+1,last_attack=excluded.last_attack",(eid,guild_id,user_id,damage,1,now))
            await db.execute("UPDATE rpg_world_events SET hp=?,status=? WHERE id=?",(new_hp,"defeated" if new_hp<=0 else "active",eid)); await db.commit()
        await self.progress_objectives(guild_id,user_id,"worldboss",1)
        await self.progress_quests(guild_id,user_id,"worldboss",1)
        if new_hp<=0:
            async with aiosqlite.connect(self.path) as db:
                cur=await db.execute("SELECT user_id,damage FROM rpg_world_event_participants WHERE event_id=? ORDER BY damage DESC",(eid,)); participants=await cur.fetchall()
                await db.commit()
            # Reward everyone who meaningfully participated, with a top-damage bonus.
            for rank,(uid,damage_done) in enumerate(participants,1):
                base_xp=900+int(level)*30; base_gold=900+int(level)*40
                mult=1.5 if rank==1 else (1.25 if rank<=3 else 1.0)
                await self.add_rewards(guild_id,int(uid),int(base_xp*mult),int(base_gold*mult))
                await self.add_item(guild_id,int(uid),"dragon_trophy" if rank<=3 else "arcane_shard",1 if rank<=3 else 2)
            return True,f"🌎 **{name} has been defeated!**\nYour **{action_name}** dealt **{damage:,}** damage.\n🏆 You were part of the victory and earned a contribution reward.",await self.world_boss_active(guild_id)
        phase="I" if new_hp>max_hp*.75 else ("II" if new_hp>max_hp*.5 else ("III" if new_hp>max_hp*.25 else "ENRAGED"))
        return True,f"🌎 **{name}** — Phase **{phase}**\nYour **{action_name}** dealt **{damage:,}** damage.\n❤️ Boss HP: **{new_hp:,}/{max_hp:,}**",await self.world_boss_active(guild_id)







    async def title_list(self,guild_id,user_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT title_key,unlocked_at FROM rpg_titles WHERE guild_id=? AND user_id=? ORDER BY unlocked_at",(guild_id,user_id)); return await cur.fetchall()

    async def unlock_title(self,guild_id,user_id,title_key):
        title_key=str(title_key).lower().strip()
        titles={"adventurer":"Adventurer","champion":"Champion","legend":"Legend","collector":"Collector","beastmaster":"Beastmaster","master_crafter":"Master Crafter"}
        if title_key not in titles:return False,"Unknown title key."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT OR IGNORE INTO rpg_titles VALUES(?,?,?,?)",(guild_id,user_id,title_key,time.time())); await db.commit()
        return True,f"Title unlocked: **{titles[title_key]}**."

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

    async def shop(self,guild_id=None,user_id=None):
        # The shop is a broad rotating catalogue, not a weapon-only storefront.
        # It deliberately shows many categories while keeping the Discord panel
        # manageable. The Item Codex remains the complete source of truth.
        level=1
        if guild_id is not None and user_id is not None:
            p=await self.player(guild_id,user_id)
            level=int(p["level"]) if p else 1

        rarity_order={r:i for i,r in enumerate(RARITIES)}
        shop_cycle=rotation_key("shop")
        rng=random.Random(f"horizon-shop:{shop_cycle}:{level}")
        category_targets={
            "weapon":16,
            "armor":14,
            "offhand":8,
            "accessory":8,
            "ring":6,
            "amulet":6,
            "relic":5,
            "consumable":10,
            "food":8,
            "material":6,
            "egg":5,
            "chest":4,
        }

        selected=[]
        selected_keys=set()

        # Pick from every category independently so one huge generated
        # equipment category cannot crowd out potions, accessories, eggs, etc.
        for slot,target in category_targets.items():
            eligible=[
                k for k,v in ITEMS.items()
                if v.get("price")
                and v.get("slot")==slot
                and int(v.get("level_req",1))<=level+5            ]
            eligible.sort(key=lambda k:(
                int(ITEMS[k].get("level_req",1)),
                rarity_order.get(ITEMS[k].get("rarity","common"),0),
                ITEMS[k].get("name",k)
            ))
            if len(eligible)>target:
                # Keep the lower-level catalogue useful while still rotating
                # higher-rarity choices through the shop.
                low=[k for k in eligible if int(ITEMS[k].get("level_req",1))<=level+3]
                pool=low if len(low)>=target else eligible
                chosen=rng.sample(pool,target)
            else:
                chosen=list(eligible)
            selected.extend(chosen)
            selected_keys.update(chosen)

        # If a category is short at a low level, fill the remaining slots from
        # the global eligible pool rather than leaving the shop tiny.
        max_listings=96
        if len(selected)<max_listings:
            remaining=[
                k for k,v in ITEMS.items()
                if k not in selected_keys
                and v.get("price")
                and int(v.get("level_req",1))<=level+5
            ]
            rng.shuffle(remaining)
            selected.extend(remaining[:max_listings-len(selected)])

        selected=selected[:max_listings]
        selected.sort(key=lambda k:(
            str(ITEMS[k].get("slot","item")),
            int(ITEMS[k].get("level_req",1)),
            rarity_order.get(ITEMS[k].get("rarity","common"),0),
            ITEMS[k].get("name",k)
        ))
        return [(k,ITEMS[k]) for k in selected]

    async def buy(self,guild_id,user_id,item_key,quantity=1):
        p=await self.player(guild_id,user_id); item=ITEMS.get(item_key.lower())
        if not p:return False,"Create a hero first."
        if not item or not item.get("price"):return False,"That item isn't sold in the shop."
        req=int(item.get("level_req",1))
        if item.get("slot") not in {"consumable","food","material"} and int(p["level"])<req:return False,f"That gear requires level **{req}**."
        quantity=max(1,min(int(quantity),50)); base_cost=int(item["price"])*quantity
        faction=await self._faction_passive(guild_id,user_id); discount=int(base_cost*faction.get("shop_pct",0)/100); cost=max(1,base_cost-discount)
        if p["gold"]<cost:return False,f"You need **{cost} gold**."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET gold=gold-? WHERE guild_id=? AND user_id=?",(cost,guild_id,user_id));            await self._economy_log(db,guild_id,user_id,"shop_buy",item_key=item_key.lower(),quantity=quantity,gold_delta=-cost,metadata={"base":base_cost,"discount":discount}); await db.commit()
        await self.add_item(guild_id,user_id,item_key.lower(),quantity); return True,f"Bought **{item['name']} ×{quantity}** for **{cost} gold**." + (f" (−{discount} faction discount)" if discount else "")

    async def sell(self,guild_id,user_id,item_key,quantity=1):
        item=ITEMS.get(item_key.lower());
        if not item:return False,"Unknown item."
        quantity=max(1,quantity)
        if not await self.remove_item(guild_id,user_id,item_key.lower(),quantity):return False,"You don't have enough of that item."
        value=max(1,int(item.get("price",10)*0.45))*quantity
        faction=await self._faction_passive(guild_id,user_id); bonus=int(value*faction.get("sale_pct",0)/100); value+=bonus
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET gold=gold+? WHERE guild_id=? AND user_id=?",(value,guild_id,user_id));
            await self._economy_log(db,guild_id,user_id,"shop_sell",item_key=item_key.lower(),quantity=quantity,gold_delta=value,metadata={"faction_bonus":bonus}); await db.commit()
        return True,f"Sold **{item['name']} ×{quantity}** for **{value} gold**." + (f" (+{bonus} faction bonus)" if bonus else "")

    async def rest(self,guild_id,user_id):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET hp=max_hp,mp=max_mp,stamina=100,last_stamina_tick=? WHERE guild_id=? AND user_id=?",(time.time(),guild_id,user_id)); await db.commit()
        return True,"You rested at Horizon Village. HP, MP and stamina restored."

    async def _trade_row(self, db, guild_id, trade_id):
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM rpg_trades WHERE guild_id=? AND id=?", (guild_id, int(trade_id)))
        row = await cur.fetchone()
        return dict(row) if row else None

    async def trade_create(self, guild_id, proposer_id, target_id):
        proposer_id, target_id = int(proposer_id), int(target_id)
        if proposer_id == target_id:
            return False, "You cannot trade with yourself."
        if not await self.player(guild_id, proposer_id) or not await self.player(guild_id, target_id):
            return False, "Both players need an RPG character before trading."
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "SELECT id FROM rpg_trades WHERE guild_id=? AND status='open' AND ((proposer_id=? AND target_id=?) OR (proposer_id=? AND target_id=?)) LIMIT 1",
                (guild_id, proposer_id, target_id, target_id, proposer_id),
            )
            if await cur.fetchone():
                return False, "You already have an open trade with that player. Finish or cancel it first."
            now = time.time()
            cur = await db.execute(
                "INSERT INTO rpg_trades(guild_id,proposer_id,target_id,created_at,updated_at) VALUES(?,?,?,?,?)",
                (guild_id, proposer_id, target_id, now, now),
            )
            trade_id = cur.lastrowid
            await db.commit()
        return True, trade_id

    async def trade_add_item(self, guild_id, user_id, trade_id, item_key, quantity=1):
        item_key = str(item_key).lower().strip()
        quantity = int(quantity)
        if quantity < 1:
            return False, "Quantity must be at least 1."
        if item_key not in ITEMS:
            return False, "Unknown item. Use `!rpg items` or `!rpg iteminfo <item_key>`."
        async with aiosqlite.connect(self.path) as db:
            trade = await self._trade_row(db, guild_id, trade_id)
            if not trade or trade["status"] != "open":
                return False, "That trade is no longer open."
            if int(user_id) not in {int(trade["proposer_id"]), int(trade["target_id"])}:
                return False, "You are not a participant in that trade."
            side = "proposer" if int(user_id) == int(trade["proposer_id"]) else "target"
            cur = await db.execute("SELECT quantity FROM rpg_inventory WHERE guild_id=? AND user_id=? AND item_key=?", (guild_id,user_id,item_key))
            inv = await cur.fetchone()
            if not inv or int(inv[0]) < quantity:
                return False, f"You only own **{int(inv[0]) if inv else 0}** of that item."
            cur = await db.execute("SELECT COALESCE(SUM(quantity),0) FROM rpg_trade_items ti JOIN rpg_trades t ON t.id=ti.trade_id WHERE ti.side=? AND ti.item_key=? AND t.guild_id=? AND t.status='open' AND ((t.proposer_id=? ) OR (t.target_id=?)) AND ti.trade_id<>?", (side,item_key,guild_id,int(user_id),int(user_id),int(trade_id)))
            reserved = int((await cur.fetchone())[0] or 0)
            if reserved + quantity > int(inv[0]):
                return False, f"You already have **{reserved}** of that item committed to another open trade."
            await db.execute("INSERT INTO rpg_trade_items(trade_id,side,item_key,quantity) VALUES(?,?,?,?) ON CONFLICT(trade_id,side,item_key) DO UPDATE SET quantity=quantity+excluded.quantity", (int(trade_id),side,item_key,quantity))
            await db.execute("UPDATE rpg_trades SET updated_at=? WHERE id=?", (time.time(),int(trade_id)))
            await db.commit()
        return True, f"Added **{ITEMS[item_key]['name']} ×{quantity}** to your side of trade `#{trade_id}`."

    async def trade_add_pet(self, guild_id, user_id, trade_id, pet_id):
        pet_id=int(pet_id)
        async with aiosqlite.connect(self.path) as db:
            trade=await self._trade_row(db,guild_id,trade_id)
            if not trade or trade["status"]!="open": return False,"That trade is no longer open."
            if int(user_id) not in {int(trade["proposer_id"]),int(trade["target_id"])}: return False,"You are not a participant in that trade."
            side="proposer" if int(user_id)==int(trade["proposer_id"]) else "target"
            cur=await db.execute("SELECT name,species,equipped FROM rpg_pet_inventory WHERE pet_id=? AND guild_id=? AND user_id=?",(pet_id,guild_id,user_id)); pet=await cur.fetchone()
            if not pet:return False,"That pet does not belong to you."
            if int(pet[2]):return False,"Unequip that pet first. Your active companion cannot be traded."
            cur=await db.execute("SELECT 1 FROM rpg_trade_pets tp JOIN rpg_trades t ON t.id=tp.trade_id WHERE tp.pet_id=? AND t.status='open' AND t.id<>? LIMIT 1",(pet_id,int(trade_id)))
            if await cur.fetchone():return False,"That pet is already reserved in another open trade."
            await db.execute("INSERT OR IGNORE INTO rpg_trade_pets(trade_id,side,pet_id) VALUES(?,?,?)",(int(trade_id),side,pet_id))
            await db.execute("UPDATE rpg_trades SET updated_at=? WHERE id=?",(time.time(),int(trade_id)))
            await db.commit()
        return True,f"Added pet **{pet[0]}** (`#{pet_id}`) to your side of trade `#{trade_id}`."

    async def trade_add_currency(self, guild_id, user_id, trade_id, currency, amount):
        currency=str(currency).lower().strip(); amount=int(amount)
        column={"gold":"gold","gems":"gems","gem":"gems","diamond":"gems","diamonds":"gems"}.get(currency)
        label="Gold" if column=="gold" else "Diamonds (Gems)"
        if not column:return False,"Currency must be `gold` or `diamonds`."
        if amount<0:return False,"Amount cannot be negative."
        async with aiosqlite.connect(self.path) as db:
            trade=await self._trade_row(db,guild_id,trade_id)
            if not trade or trade["status"]!="open":return False,"That trade is no longer open."
            if int(user_id) not in {int(trade["proposer_id"]),int(trade["target_id"])}:return False,"You are not a participant in that trade."
            side="proposer" if int(user_id)==int(trade["proposer_id"]) else "target"
            current=int((await (await db.execute(f"SELECT {column} FROM rpg_players WHERE guild_id=? AND user_id=?",(guild_id,user_id))).fetchone())[0] or 0)
            cur=await db.execute(f"SELECT proposer_{column} FROM rpg_trades WHERE id=?",(int(trade_id),)) if side=="proposer" else await db.execute(f"SELECT target_{column} FROM rpg_trades WHERE id=?",(int(trade_id),))
            already=int((await cur.fetchone())[0] or 0)
            # Do not double-count this trade; other open trades are not reserved and are rechecked at acceptance.
            if already+amount>current:return False,f"You have **{current} {label}** but are trying to offer **{already+amount}**."
            field=f"{side}_{column}"
            await db.execute(f"UPDATE rpg_trades SET {field}=?,updated_at=? WHERE id=?",(already+amount,time.time(),int(trade_id)))
            await db.commit()
        return True,f"Your trade offer now includes **{already+amount} {label}**."

    async def trade_remove_all(self, guild_id, user_id, trade_id):
        async with aiosqlite.connect(self.path) as db:
            trade=await self._trade_row(db,guild_id,trade_id)
            if not trade or trade["status"]!="open":return False,"That trade is no longer open."
            if int(user_id) not in {int(trade["proposer_id"]),int(trade["target_id"])}:return False,"You are not a participant in that trade."
            side="proposer" if int(user_id)==int(trade["proposer_id"]) else "target"
            await db.execute("DELETE FROM rpg_trade_items WHERE trade_id=? AND side=?",(int(trade_id),side))
            await db.execute("DELETE FROM rpg_trade_pets WHERE trade_id=? AND side=?",(int(trade_id),side))
            await db.execute(f"UPDATE rpg_trades SET {side}_gold=0,{side}_gems=0,updated_at=? WHERE id=?",(time.time(),int(trade_id)))
            await db.commit()
        return True,f"Cleared your side of trade `#{trade_id}`."

    async def trade_details(self, guild_id, trade_id):
        async with aiosqlite.connect(self.path) as db:
            trade=await self._trade_row(db,guild_id,trade_id)
            if not trade:return None
            cur=await db.execute("SELECT side,item_key,quantity FROM rpg_trade_items WHERE trade_id=? ORDER BY side,item_key",(int(trade_id),)); items=[dict(r) for r in await cur.fetchall()]
            cur=await db.execute("SELECT side,pet_id FROM rpg_trade_pets WHERE trade_id=? ORDER BY side,pet_id",(int(trade_id),)); pets=[dict(r) for r in await cur.fetchall()]
            return {"trade":trade,"items":items,"pets":pets}

    async def trade_cancel(self, guild_id, user_id, trade_id):
        async with aiosqlite.connect(self.path) as db:
            trade=await self._trade_row(db,guild_id,trade_id)
            if not trade:return False,"Trade not found."
            if int(user_id) not in {int(trade["proposer_id"]),int(trade["target_id"])}:return False,"You are not a participant in that trade."
            if trade["status"]!="open":return False,"That trade is already closed."
            await db.execute("UPDATE rpg_trades SET status='cancelled',updated_at=? WHERE id=?",(time.time(),int(trade_id))); await db.commit()
        return True,f"Trade `#{trade_id}` cancelled. Nothing was transferred."

    async def trade_accept(self, guild_id, user_id, trade_id):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys=ON")
            await db.execute("BEGIN IMMEDIATE")
            trade=await self._trade_row(db,guild_id,trade_id)
            if not trade:
                await db.rollback(); return False,"Trade not found."
            if trade["status"]!="open":
                await db.rollback(); return False,"That trade is no longer open."
            if int(user_id)!=int(trade["target_id"]):
                await db.rollback(); return False,"Only the receiving player can accept this trade."
            proposer,target=int(trade["proposer_id"]),int(trade["target_id"])
            # Re-check every asset immediately before transfer.
            for side,owner in (("proposer",proposer),("target",target)):
                cur=await db.execute("SELECT item_key,quantity FROM rpg_trade_items WHERE trade_id=? AND side=?",(int(trade_id),side))
                for item_key,qty in await cur.fetchall():
                    cur2=await db.execute("SELECT quantity FROM rpg_inventory WHERE guild_id=? AND user_id=? AND item_key=?",(guild_id,owner,item_key)); row=await cur2.fetchone()
                    if not row or int(row[0])<int(qty):
                        await db.rollback(); return False,f"Trade cannot complete: <@{owner}> no longer has enough **{ITEMS.get(item_key,{'name':item_key})['name']}**."
                cur=await db.execute("SELECT pet_id FROM rpg_trade_pets WHERE trade_id=? AND side=?",(int(trade_id),side))
                for (pet_id,) in await cur.fetchall():
                    cur2=await db.execute("SELECT equipped FROM rpg_pet_inventory WHERE pet_id=? AND guild_id=? AND user_id=?",(int(pet_id),guild_id,owner)); row=await cur2.fetchone()
                    if not row:
                        await db.rollback(); return False,f"Trade cannot complete: pet `#{pet_id}` is no longer owned by <@{owner}>."
                    if int(row[0]):
                        await db.rollback(); return False,f"Trade cannot complete: pet `#{pet_id}` is equipped. Unequip it first."
            for side,owner,curcol in (("proposer",proposer,"proposer"),("target",target,"target")):
                gold=int(trade[f"{curcol}_gold"]); gems=int(trade[f"{curcol}_gems"])
                cur=await db.execute("SELECT gold,gems FROM rpg_players WHERE guild_id=? AND user_id=?",(guild_id,owner)); row=await cur.fetchone()
                if not row or int(row[0])<gold or int(row[1])<gems:
                    await db.rollback(); return False,f"Trade cannot complete: <@{owner}> no longer has enough currency."
            # Move item stacks.
            for side,owner,receiver in (("proposer",proposer,target),("target",target,proposer)):
                cur=await db.execute("SELECT item_key,quantity FROM rpg_trade_items WHERE trade_id=? AND side=?",(int(trade_id),side))
                for item_key,qty in await cur.fetchall():
                    await db.execute("UPDATE rpg_inventory SET quantity=quantity-? WHERE guild_id=? AND user_id=? AND item_key=?",(int(qty),guild_id,owner,item_key))
                    cur_left=await db.execute("SELECT quantity FROM rpg_inventory WHERE guild_id=? AND user_id=? AND item_key=?",(guild_id,owner,item_key)); left_row=await cur_left.fetchone()
                    if not left_row or int(left_row[0])<=0:
                        # If the last copy of equipped gear is traded away, remove the stale equipment reference and its enchants.
                        cur_slots=await db.execute("SELECT slot FROM rpg_equipment WHERE guild_id=? AND user_id=? AND item_key=?",(guild_id,owner,item_key)); slots=[r[0] for r in await cur_slots.fetchall()]
                        await db.execute("DELETE FROM rpg_equipment WHERE guild_id=? AND user_id=? AND item_key=?",(guild_id,owner,item_key))
                        for slot in slots:
                            await db.execute("DELETE FROM rpg_equipment_enchants WHERE guild_id=? AND user_id=? AND slot=?",(guild_id,owner,slot))
                    await db.execute("INSERT INTO rpg_inventory(guild_id,user_id,item_key,quantity) VALUES(?,?,?,?) ON CONFLICT(guild_id,user_id,item_key) DO UPDATE SET quantity=quantity+excluded.quantity",(guild_id,receiver,item_key,int(qty)))
            # Move unique pets.
            for side,owner,receiver in (("proposer",proposer,target),("target",target,proposer)):
                cur=await db.execute("SELECT pet_id FROM rpg_trade_pets WHERE trade_id=? AND side=?",(int(trade_id),side))
                for (pet_id,) in await cur.fetchall():
                    await db.execute("UPDATE rpg_pet_inventory SET user_id=? WHERE pet_id=? AND guild_id=? AND user_id=?",(receiver,int(pet_id),guild_id,owner))
            # Keep the legacy single-pet compatibility cache synchronized.
            await self._sync_legacy_pet_cache(db,guild_id,proposer)
            await self._sync_legacy_pet_cache(db,guild_id,target)
            # Currency exchange is simultaneous and atomic.
            pg,gg=int(trade["proposer_gold"]),int(trade["target_gold"]); pd,gd=int(trade["proposer_gems"]),int(trade["target_gems"])
            await db.execute("UPDATE rpg_players SET gold=gold-?+?,gems=gems-?+? WHERE guild_id=? AND user_id=?",(pg,gg,pd,gd,guild_id,proposer))
            await db.execute("UPDATE rpg_players SET gold=gold-?+?,gems=gems-?+? WHERE guild_id=? AND user_id=?",(gg,pg,gd,pd,guild_id,target))
            await db.execute("UPDATE rpg_trades SET status='completed',updated_at=? WHERE id=?",(time.time(),int(trade_id)))
            await db.execute("INSERT INTO rpg_social_reputation(guild_id,user_id,trades_completed) VALUES(?,?,1) ON CONFLICT(guild_id,user_id) DO UPDATE SET trades_completed=trades_completed+1",(guild_id,proposer))
            await db.execute("INSERT INTO rpg_social_reputation(guild_id,user_id,trades_completed) VALUES(?,?,1) ON CONFLICT(guild_id,user_id) DO UPDATE SET trades_completed=trades_completed+1",(guild_id,target))
            await db.commit()
        return True,f"Trade `#{trade_id}` completed successfully. Assets were transferred atomically."

    async def trade_list(self, guild_id, user_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT id,proposer_id,target_id,status,created_at,proposer_gold,target_gold,proposer_gems,target_gems FROM rpg_trades WHERE guild_id=? AND status='open' AND (proposer_id=? OR target_id=?) ORDER BY id DESC LIMIT 20",(guild_id,user_id,user_id)); return await cur.fetchall()

    async def create_market(self,guild_id,user_id,item_key,quantity,price):
        item_key=str(item_key).lower().strip(); quantity=int(quantity); price=int(price)
        if item_key not in ITEMS:return False,"Unknown item."
        if quantity<1 or price<1:return False,"Quantity and price must be positive."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("BEGIN IMMEDIATE")
            cur=await db.execute("SELECT quantity FROM rpg_inventory WHERE guild_id=? AND user_id=? AND item_key=?",(guild_id,user_id,item_key)); row=await cur.fetchone()
            if not row or int(row[0])<quantity: await db.rollback(); return False,"You don't own enough of that item."
            # Gear instances cannot yet be represented in the stack market.
            if ITEMS[item_key].get("slot") in {"weapon","armor","offhand","accessory","ring","amulet","relic"}:
                await db.rollback(); return False,"Use direct `!rpg trade` for unique gear. The player market is stack-safe for consumables/materials/items; unique gear marketplace support is coming with persistent item instances."
            await db.execute("UPDATE rpg_inventory SET quantity=quantity-? WHERE guild_id=? AND user_id=? AND item_key=?",(quantity,guild_id,user_id,item_key))
            token=uuid.uuid4().hex
            cur=await db.execute("INSERT INTO rpg_market(guild_id,seller_id,item_key,quantity,price_each,created_at,status,listing_token) VALUES(?,?,?,?,?,?,?,?)",(guild_id,user_id,item_key,quantity,price,time.time(),"open",token)); mid=cur.lastrowid
            await self._economy_log(db,guild_id,user_id,"market_list",item_key=item_key,quantity=-quantity,metadata={"listing_id":mid,"listing_token":token,"price_each":price})
            await db.commit()
        return True,f"Market listing `#{mid}` created and the items are now escrowed."

    async def market(self,guild_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT id,seller_id,item_key,quantity,price_each FROM rpg_market WHERE guild_id=? AND status='open' ORDER BY id DESC LIMIT 50",(guild_id,)); return await cur.fetchall()

    async def market_cancel(self,guild_id,user_id,listing_id):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("BEGIN IMMEDIATE")
            cur=await db.execute("SELECT seller_id,item_key,quantity,status FROM rpg_market WHERE guild_id=? AND id=?",(guild_id,int(listing_id))); row=await cur.fetchone()
            if not row:return False,"Listing not found."
            seller,item,qty,status=row
            if int(seller)!=int(user_id): await db.rollback(); return False,"Only the seller can cancel this listing."
            if status!="open": await db.rollback(); return False,"That listing is already closed."
            await db.execute("UPDATE rpg_market SET status='cancelled' WHERE id=?",(int(listing_id),))
            await db.execute("INSERT INTO rpg_inventory VALUES(?,?,?,?) ON CONFLICT(guild_id,user_id,item_key) DO UPDATE SET quantity=quantity+excluded.quantity",(guild_id,user_id,item,qty))
            await self._economy_log(db,guild_id,user_id,"market_cancel",item_key=item,quantity=qty,metadata={"listing_id":int(listing_id)})
            await db.commit()
        return True,f"Listing `#{listing_id}` cancelled and **{ITEMS.get(item,{'name':item}).get('name',item)} ×{qty}** returned."

    async def market_buy(self,guild_id,user_id,listing_id):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("BEGIN IMMEDIATE")
            cur=await db.execute("SELECT seller_id,item_key,quantity,price_each,status,listing_token FROM rpg_market WHERE guild_id=? AND id=?",(guild_id,int(listing_id))); row=await cur.fetchone()
            if not row: await db.rollback(); return False,"Listing not found."
            seller,item,qty,price,status,token=row
            if status!="open": await db.rollback(); return False,"That listing is no longer available."
            if int(seller)==int(user_id): await db.rollback(); return False,"You cannot buy your own listing."
            total=int(qty)*int(price)
            cur=await db.execute("SELECT gold FROM rpg_players WHERE guild_id=? AND user_id=?",(guild_id,user_id)); p=await cur.fetchone()
            if not p or int(p[0])<total: await db.rollback(); return False,f"You need {total} gold."
            cur=await db.execute("SELECT user_id FROM rpg_players WHERE guild_id=? AND user_id=?",(guild_id,seller));
            if not await cur.fetchone(): await db.rollback(); return False,"Seller no longer has a valid RPG character."
            tax=max(1,total*5//100)
            seller_net=total-tax
            await db.execute("UPDATE rpg_players SET gold=gold-? WHERE guild_id=? AND user_id=?",(total,guild_id,user_id))
            await db.execute("UPDATE rpg_players SET gold=gold+? WHERE guild_id=? AND user_id=?",(seller_net,guild_id,seller))
            await db.execute("INSERT INTO rpg_inventory VALUES(?,?,?,?) ON CONFLICT(guild_id,user_id,item_key) DO UPDATE SET quantity=quantity+excluded.quantity",(guild_id,user_id,item,qty))
            await db.execute("UPDATE rpg_market SET status='sold',buyer_id=?,sold_at=? WHERE id=? AND status='open'",(user_id,time.time(),int(listing_id)))
            await self._economy_log(db,guild_id,user_id,"market_buy",item_key=item,quantity=qty,gold_delta=-total,metadata={"listing_id":int(listing_id),"seller_id":int(seller),"listing_token":token})
            await self._economy_log(db,guild_id,seller,"market_sale",item_key=item,quantity=qty,gold_delta=seller_net,metadata={"listing_id":int(listing_id),"buyer_id":int(user_id),"listing_token":token,"tax":tax})
            await self._economy_log(db,guild_id,seller,"market_tax",gold_delta=-tax,metadata={"listing_id":int(listing_id)})
            await db.commit()
        return True,f"Bought **{ITEMS.get(item,{'name':item}).get('name',item)} ×{qty}** for **{total} gold**. Market fee: **{tax} gold**."

    async def economy_log(self,guild_id,user_id,limit=20):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT created_at,event_type,item_key,quantity,gold_delta,balance_after,metadata_json FROM rpg_economy_log WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT ?",(guild_id,user_id,max(1,min(int(limit),50))))
            return await cur.fetchall()

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
            await db.execute("INSERT INTO rpg_pet_collection(guild_id,user_id,species,first_seen,times_seen) VALUES(?,?,?,?,1) ON CONFLICT(guild_id,user_id,species) DO UPDATE SET times_seen=times_seen+1",(guild_id,user_id,species,time.time()))
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

    async def pet_feed(self,guild_id,user_id,pet_id=None):
        pets=await self.pet_inventory(guild_id,user_id); current=next((x for x in pets if x.get("equipped")),None) if pet_id is None else next((x for x in pets if int(x["pet_id"])==int(pet_id)),None)
        if not current:return False,"Pet not found."
        food="hearty_stew"
        inv=dict(await self.inventory(guild_id,user_id))
        if inv.get(food,0)<1:
            return False,"You need **Hearty Stew** to feed a pet."
        await self.remove_item(guild_id,user_id,food,1,event_type="pet_feed")
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_pet_inventory SET total_xp=total_xp+35,xp=xp+35 WHERE pet_id=? AND guild_id=? AND user_id=?",(current["pet_id"],guild_id,user_id))
            await db.commit()
        await self._level_pet(guild_id,user_id,int(current["pet_id"]))
        return True,f"Fed **{current['name']}**. The meal granted **35 Pet XP** and can help it grow stronger."

    async def _grant_pet_xp(self,guild_id,user_id,amount):
        pet=await self.pet_record(guild_id,user_id)
        if not pet:return 0
        amount=max(0,int(amount))
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_pet_inventory SET total_xp=total_xp+?,xp=xp+? WHERE guild_id=? AND user_id=? AND equipped=1",(amount,amount,guild_id,user_id))
            await db.commit()
        await self._level_pet(guild_id,user_id,int(pet["pet_id"]))
        return amount

    async def _level_pet(self,guild_id,user_id,pet_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT species,level,total_xp FROM rpg_pet_inventory WHERE pet_id=? AND guild_id=? AND user_id=?",(pet_id,guild_id,user_id)); row=await cur.fetchone()
            if not row:return
            species,level,total_xp=row; new_level=min(50,1+int(total_xp)//100)
            if new_level<=int(level):return
            base=PET_SPECIES.get(species,{})
            await db.execute("UPDATE rpg_pet_inventory SET level=?,bonus_atk=?,bonus_def=?,bonus_hp=?,bonus_speed=?,bonus_crit=? WHERE pet_id=?",(new_level,int(base.get("atk",2))+new_level-1,int(base.get("def",2))+new_level-1,int(base.get("hp",5))+5*(new_level-1),int(base.get("spd",2))+new_level//2,int(base.get("crit",1))+new_level//3,pet_id))
            await self._sync_legacy_pet_cache(db,guild_id,user_id); await db.commit()

    async def pet_collection(self,guild_id,user_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT species,times_seen,first_seen FROM rpg_pet_collection WHERE guild_id=? AND user_id=? ORDER BY species",(guild_id,user_id)); return await cur.fetchall()

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
        # Gear is level-aware so a new hero does not get flooded with unusable endgame pieces.
        p=await self.player(guild_id,user_id)
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
        level=int(p.get("level",1)) if p else 1
        candidates=[(k,v) for k,v in ITEMS.items() if v.get("rarity")==rarity and v.get("slot") in {"weapon","armor","offhand","accessory","ring","amulet","relic","chest","consumable"} and int(v.get("level_req",1))<=level+3]
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
        if enchant_key.lower() not in ENCHANTMENT_COMPATIBILITY.get(item.get("slot"), set()):
            allowed = ", ".join(ENCHANTMENTS[k]["name"] for k in ENCHANTMENT_COMPATIBILITY.get(item.get("slot"), set()))
            return False, f"**{ench['name']}** cannot be equipped on **{item['name']}**. Compatible enchantments: {allowed}."
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
        # A party run is a real expedition: every member commits stamina, and
        # the group gets a small coordination bonus instead of a combat-only check.
        for uid,_role in members:
            await self._refresh_stamina(guild_id,uid)
            member=await self.player(guild_id,uid)
            if not member or int(member["stamina"])<PARTY_DUNGEON_STAMINA_COST:
                return {"error":f"<@{uid}> needs **{PARTY_DUNGEON_STAMINA_COST} stamina** for the expedition."}
        power=0
        for uid,_role in members:
            stats=await self.stats(guild_id,uid)
            if stats:
                p,gear,b=stats; power += p["atk"]+b["atk"]+p["defense"]+b["defense"]+p["speed"]+b["speed"]
        required_power=floors*55 + req*12
        # Team size adds reliability but never guarantees success.
        chance=min(.93,max(.30,power/max(1,required_power)*.60 + (len(members)-2)*.04))
        for uid,_role in members:
            await self._spend_stamina(guild_id,uid,PARTY_DUNGEON_STAMINA_COST)
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
        async with aiosqlite.connect(self.path) as db:
            for uid,_role in members:
                await db.execute("INSERT INTO rpg_social_reputation(guild_id,user_id,party_runs) VALUES(?,?,1) ON CONFLICT(guild_id,user_id) DO UPDATE SET party_runs=party_runs+1",(guild_id,uid))
            await db.commit()
        return {"win":True,"name":n,"members":len(members),"chance":chance,"rewards":rewards,"log":[f"The party cleared all **{floors} floors**.",f"Team power check passed with **{power}** combined combat power."]}

    async def profession_data(self,guild_id,user_id,profession=None):
        async with aiosqlite.connect(self.path) as db:
            if profession:
                cur=await db.execute("SELECT profession,level,xp FROM rpg_professions WHERE guild_id=? AND user_id=? AND profession=?",(guild_id,user_id,profession.lower()))
            else:
                cur=await db.execute("SELECT profession,level,xp FROM rpg_professions WHERE guild_id=? AND user_id=? ORDER BY profession",(guild_id,user_id))
            return await cur.fetchall()

    async def _profession_xp(self,guild_id,user_id,profession,amount):
        profession=str(profession).lower(); amount=max(0,int(amount))
        if not amount:return
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT OR IGNORE INTO rpg_professions(guild_id,user_id,profession,level,xp) VALUES(?,?,?,?,0)",(guild_id,user_id,profession,1))
            cur=await db.execute("SELECT level,xp FROM rpg_professions WHERE guild_id=? AND user_id=? AND profession=?",(guild_id,user_id,profession)); row=await cur.fetchone()
            level,xp=int(row[0]),int(row[1])+amount
            while level<50 and xp >= level*level*100:
                xp-=level*level*100; level+=1
            await db.execute("UPDATE rpg_professions SET level=?,xp=? WHERE guild_id=? AND user_id=? AND profession=?",(level,xp,guild_id,user_id,profession)); await db.commit()
        return level,xp

    async def professions(self,guild_id,user_id):
        rows=await self.profession_data(guild_id,user_id)
        known={r[0]:r for r in rows}
        out=[]
        for key in ("gathering","mining","fishing","crafting"):
            r=known.get(key,(key,1,0)); out.append(r)
        return out

    async def craft(self,guild_id,user_id,item_key,quantity=1):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        item_key=item_key.lower().strip(); recipe=RECIPES.get(item_key)
        if not recipe:return False,"Recipe not found. Use `!rpg recipes`."
        meta=recipe.get("_meta",{}) if isinstance(recipe,dict) else {}
        quantity=max(1,min(int(quantity),10)); req=int(meta.get("level_req",1))
        prof=await self.profession_data(guild_id,user_id,"crafting"); level=int(prof[0][1]) if prof else 1
        if level<req:return False,f"**{ITEMS.get(item_key,{'name':item_key}).get('name',item_key)}** requires Crafting Lv **{req}**."
        stamina_cost=CRAFT_STAMINA_COST*quantity
        ok,remaining=await self._spend_stamina(guild_id,user_id,stamina_cost)
        if not ok:return False,f"You need **{stamina_cost} stamina** to craft that quantity."
        fee=int(meta.get("gold_fee",0))*quantity
        faction=await self._faction_passive(guild_id,user_id); xp_gain=int(meta.get("xp",25)*quantity*(1+faction.get("craft_xp_pct",0)/100))
        async with aiosqlite.connect(self.path) as db:
            await db.execute("BEGIN IMMEDIATE")
            cur=await db.execute("SELECT gold FROM rpg_players WHERE guild_id=? AND user_id=?",(guild_id,user_id)); row=await cur.fetchone()
            if not row or int(row[0])<fee:
                await db.rollback(); await self._refund_stamina(guild_id,user_id,stamina_cost)
                return False,f"You need **{fee} gold** for the crafting fee."
            for mat,need in recipe.items():
                if mat=="_meta":continue
                cur=await db.execute("SELECT quantity FROM rpg_inventory WHERE guild_id=? AND user_id=? AND item_key=?",(guild_id,user_id,mat)); have=await cur.fetchone()
                if not have or int(have[0])<int(need)*quantity:
                    await db.rollback(); await self._refund_stamina(guild_id,user_id,stamina_cost)
                    return False,f"Missing **{ITEMS.get(mat,{'name':mat}).get('name',mat)}** ×{int(need)*quantity}."
            for mat,need in recipe.items():
                if mat=="_meta":continue
                amount=int(need)*quantity
                await db.execute("UPDATE rpg_inventory SET quantity=quantity-? WHERE guild_id=? AND user_id=? AND item_key=?",(amount,guild_id,user_id,mat))
                await self._economy_log(db,guild_id,user_id,"craft_material",item_key=mat,quantity=-amount,metadata={"output":item_key})
            await db.execute("UPDATE rpg_players SET gold=gold-? WHERE guild_id=? AND user_id=?",(fee,guild_id,user_id))
            await db.execute("INSERT INTO rpg_inventory VALUES(?,?,?,?) ON CONFLICT(guild_id,user_id,item_key) DO UPDATE SET quantity=quantity+excluded.quantity",(guild_id,user_id,item_key,quantity))
            await self._economy_log(db,guild_id,user_id,"craft_fee",gold_delta=-fee,metadata={"output":item_key})
            await self._economy_log(db,guild_id,user_id,"craft_output",item_key=item_key,quantity=quantity,metadata={"recipe":recipe})
            await db.commit()
        level_xp=await self._profession_xp(guild_id,user_id,"crafting",xp_gain)
        await self.check_achievements(guild_id,user_id)
        return True,f"Crafted **{ITEMS[item_key]['name']} ×{quantity}**. Crafting Lv **{level_xp[0]}** (+{xp_gain} XP) • −{stamina_cost} stamina • −{fee} gold."

    async def gather(self,guild_id,user_id,kind="gather"):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        await self._refresh_stamina(guild_id,user_id); p=await self.player(guild_id,user_id)
        kind=str(kind or "gather").lower()
        settings={
            "gather": ("last_gather",30,[("herb",.45),("wolf_pelt",.30),("iron_ore",.15),("arcane_shard",.10)],"Gathering","gathering"),
            "mine": ("last_mine",45,[("iron_ore",.50),("arcane_shard",.18),("wolf_pelt",.12),("herb",.20)],"Mining","mining"),
            "fish": ("last_fish",40,[("food_grilled_fish",.55),("arcane_shard",.08),("herb",.20),("wolf_pelt",.17)],"Fishing","fishing"),
        }
        field,cooldown,pool,label,profession=settings.get(kind,settings["gather"])
        remaining=await self._cooldown(p,field,cooldown)
        if remaining>0:return False,f"⏳ **{label}** is on cooldown. Try again in **{int(remaining)+1}s**."
        if p["stamina"]<10:return False,"You are exhausted. Use `!rpg rest`."
        roll=random.random(); acc=0.0; item=pool[-1][0]
        for key,chance in pool:
            acc+=chance
            if roll<=acc:item=key; break
        prof_rows=await self.profession_data(guild_id,user_id,profession); prof_level=int(prof_rows[0][1]) if prof_rows else 1
        faction=await self._faction_passive(guild_id,user_id)
        qty=random.randint(1,2) + (1 if prof_level>=10 else 0) + (1 if faction.get("gather_extra") and random.random()<0.5 else 0)
        async with aiosqlite.connect(self.path) as db:
            await db.execute(f"UPDATE rpg_players SET stamina=stamina-10, {field}=?, last_stamina_tick=? WHERE guild_id=? AND user_id=?",(time.time(),time.time(),guild_id,user_id)); await db.commit()
        await self.add_item(guild_id,user_id,item,qty,event_type=f"{profession}_gather")
        level_xp=await self._profession_xp(guild_id,user_id,profession,20)
        await self.progress_quests(guild_id,user_id,"gather",1)
        return True,f"**{label} successful!** You obtained **{ITEMS[item]['name']} ×{qty}**. {label} Lv **{level_xp[0]}**. Next attempt in **{cooldown}s**."

    async def social_stats(self,guild_id,user_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT helpful,party_runs,trades_completed,guild_contributions FROM rpg_social_reputation WHERE guild_id=? AND user_id=?",(guild_id,user_id)); row=await cur.fetchone()
        return {"helpful":row[0],"party_runs":row[1],"trades_completed":row[2],"guild_contributions":row[3]} if row else {"helpful":0,"party_runs":0,"trades_completed":0,"guild_contributions":0}

    async def economy_summary(self,guild_id,user_id):
        p=await self.player(guild_id,user_id)
        if not p:return None
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT COALESCE(SUM(CASE WHEN gold_delta>0 THEN gold_delta ELSE 0 END),0),COALESCE(SUM(CASE WHEN gold_delta<0 THEN -gold_delta ELSE 0 END),0),COUNT(*) FROM rpg_economy_log WHERE guild_id=? AND user_id=?",(guild_id,user_id)); earned,spent,events=await cur.fetchone()
            cur=await db.execute("SELECT COUNT(*) FROM rpg_market WHERE guild_id=? AND seller_id=? AND status='sold'",(guild_id,user_id)); sold=(await cur.fetchone())[0]
        return {"gold":p["gold"],"gems":p["gems"],"earned":earned,"spent":spent,"events":events,"market_sold":sold}

    async def guild_deposit(self,guild_id,user_id,amount):
        amount=max(1,amount); info=await self.guild_info(guild_id,user_id=user_id)
        if not info:return False,"You are not in a guild."
        p=await self.player(guild_id,user_id)
        if p["gold"]<amount:return False,"You don't have enough gold."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET gold=gold-? WHERE guild_id=? AND user_id=?",(amount,guild_id,user_id)); await db.execute("UPDATE rpg_guilds SET bank=bank+?,xp=xp+? WHERE guild_id=? AND name=?",(amount,amount//2,guild_id,info[0][1]))
            await db.execute("INSERT INTO rpg_social_reputation(guild_id,user_id,guild_contributions) VALUES(?,?,1) ON CONFLICT(guild_id,user_id) DO UPDATE SET guild_contributions=guild_contributions+1",(guild_id,user_id)); await db.commit()
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

    async def spend_stat(self,guild_id,user_id,stat,amount=1):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        stat=stat.lower()
        mapping={"attack":"atk","atk":"atk","defense":"defense","def":"defense","speed":"speed","spd":"speed","crit":"crit","hp":"max_hp","mana":"max_mp","mp":"max_mp"}
        column=mapping.get(stat)
        if not column:return False,"Choose `attack`, `defense`, `speed`, `crit`, `hp`, or `mana`."
        try: amount=int(amount)
        except (TypeError,ValueError): return False,"The number of points must be a whole number."
        amount=max(1,min(amount,25))
        if p["stat_points"]<amount:return False,f"You only have **{p['stat_points']} stat points**."
        gain=amount*5 if column in {"max_hp","max_mp"} else amount
        async with aiosqlite.connect(self.path) as db:
            await db.execute(f"UPDATE rpg_players SET {column}={column}+?,stat_points=stat_points-? WHERE guild_id=? AND user_id=?",(gain,amount,guild_id,user_id)); await db.commit()
        return True,f"Spent **{amount}** stat point(s) on **{stat.title()}** (+{gain})."

    async def skill_mastery(self,guild_id,user_id,skill_key,amount=1):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        skill=self._skill_for_player(p,skill_key.lower())
        if not skill:return False,"That skill does not belong to your current class."
        if not self._skill_available(p,skill):return False,f"**{skill['name']}** unlocks at level **{skill['unlock']}**."
        try: amount=int(amount)
        except (TypeError,ValueError): return False,"The number of skill points must be a whole number."
        amount=max(1,min(amount,SKILL_MAX_RANK))
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT rank FROM rpg_skill_mastery WHERE guild_id=? AND user_id=? AND skill_key=?",(guild_id,user_id,skill["key"]))
            row=await cur.fetchone(); rank=int(row[0]) if row else 0
            if rank>=SKILL_MAX_RANK:return False,f"**{skill['name']}** is already at Mastery **{SKILL_MAX_RANK}**."
            amount=min(amount,SKILL_MAX_RANK-rank)
            if p["skill_points"]<amount:return False,f"You only have **{p['skill_points']} skill points**."
            new_rank=rank+amount
            await db.execute("INSERT INTO rpg_skill_mastery(guild_id,user_id,skill_key,rank) VALUES(?,?,?,?) ON CONFLICT(guild_id,user_id,skill_key) DO UPDATE SET rank=excluded.rank",(guild_id,user_id,skill["key"],new_rank))
            await db.execute("UPDATE rpg_players SET skill_points=skill_points-? WHERE guild_id=? AND user_id=?",(amount,guild_id,user_id)); await db.commit()
        return True,f"✨ **{skill['name']}** mastered to **Rank {new_rank}/{SKILL_MAX_RANK}**. Spent **{amount}** Skill Point(s)."

    async def skill_masteries(self,guild_id,user_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT skill_key,rank FROM rpg_skill_mastery WHERE guild_id=? AND user_id=?",(guild_id,user_id)); rows=await cur.fetchall()
        return {key:int(rank) for key,rank in rows}

    def _talent_nodes(self,p,tree):
        if tree=="class":
            class_name=p["class_name"]
            if class_name in CLASS_TALENT_TEMPLATES:
                return CLASS_TALENT_TEMPLATES[class_name]
            label=class_name.replace("_"," ").title()
            return [(f"{class_name}_{key}",f"{label} {name}",desc,effect) for key,name,desc,effect in CLASS_TALENT_FALLBACK]
        race=p.get("race","human")
        return RACE_TALENT_TEMPLATES.get(race,RACE_TALENT_TEMPLATES["human"])

    async def talent_ranks(self,guild_id,user_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT tree,talent_key,rank FROM rpg_talents WHERE guild_id=? AND user_id=?",(guild_id,user_id)); rows=await cur.fetchall()
        return {(tree,key):int(rank) for tree,key,rank in rows}

    async def spend_talent(self,guild_id,user_id,tree,talent_key,amount=1):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        tree=tree.lower(); talent_key=talent_key.lower()
        if tree not in {"class","race"}:return False,"Choose the `class` or `race` talent tree."
        nodes=self._talent_nodes(p,tree); node=next((x for x in nodes if x[0]==talent_key),None)
        if not node:return False,"That talent is not available in your current tree."
        try: amount=int(amount)
        except (TypeError,ValueError): return False,"The number of talent points must be a whole number."
        amount=max(1,min(amount,5))
        ranks=await self.talent_ranks(guild_id,user_id); current=ranks.get((tree,talent_key),0)
        if current>=5:return False,f"**{node[1]}** is already at Rank **5/5**."
        amount=min(amount,5-current)
        if p["talent_points"]<amount:return False,f"You only have **{p['talent_points']} talent points**."
        new_rank=current+amount
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO rpg_talents(guild_id,user_id,tree,talent_key,rank) VALUES(?,?,?,?,?) ON CONFLICT(guild_id,user_id,tree,talent_key) DO UPDATE SET rank=excluded.rank",(guild_id,user_id,tree,talent_key,new_rank))
            await db.execute("UPDATE rpg_players SET talent_points=talent_points-? WHERE guild_id=? AND user_id=?",(amount,guild_id,user_id)); await db.commit()
        return True,f"🌟 **{node[1]}** is now **Rank {new_rank}/5**. Spent **{amount}** Talent Point(s). {node[2]}"

    def _talent_bonuses(self,p,ranks):
        bonus={"atk_pct":0.0,"def_pct":0.0,"hp_pct":0.0,"mp_pct":0.0,"crit":0.0,"skill_pct":0.0,"heal_pct":0.0,"finisher_pct":0.0}
        for tree in ("class","race"):
            for key,_name,_desc,effect in self._talent_nodes(p,tree):
                rank=int(ranks.get((tree,key),0));
                if not rank: continue
                if effect=="balanced":
                    bonus["atk_pct"]+=.5*rank; bonus["def_pct"]+=.5*rank; bonus["hp_pct"]+=.5*rank
                elif effect in bonus:
                    bonus[effect]+=({"hp_pct":1.5,"mp_pct":1.5}.get(effect,1.0))*rank if effect in {"hp_pct","mp_pct"} else (0.5*rank if effect=="crit" else 1.0*rank)
        return bonus

    def _combat_stats(self, p, pet_bonus=None, talent_bonus=None):
        data=self._progression_bonus(p)
        talent_bonus=talent_bonus or {}
        pet_bonus=pet_bonus or {"hp":0,"mp":0,"atk":0,"defense":0,"speed":0,"crit":0}
        base_hp=p["max_hp"] + data["hp"] + pet_bonus.get("hp",0)
        base_mp=p["max_mp"] + data["mp"] + pet_bonus.get("mp",0)
        base_atk=p["atk"] + data["atk"] + pet_bonus.get("atk",0)
        base_def=p["defense"] + data["defense"] + pet_bonus.get("defense",0)
        return {
            "hp": int((p["hp"] + data["hp"] + pet_bonus.get("hp",0)) * (1+talent_bonus.get("hp_pct",0)/100)),
            "max_hp": int(base_hp * (1+talent_bonus.get("hp_pct",0)/100)),
            "mp": int((p["mp"] + data["mp"] + pet_bonus.get("mp",0)) * (1+talent_bonus.get("mp_pct",0)/100)),
            "max_mp": int(base_mp * (1+talent_bonus.get("mp_pct",0)/100)),
            "atk": int(base_atk * (1+talent_bonus.get("atk_pct",0)/100)),
            "defense": int(base_def * (1+talent_bonus.get("def_pct",0)/100)),
            "speed": p["speed"] + data["speed"] + pet_bonus.get("speed",0),
            "crit": p["crit"] + data["crit"] + pet_bonus.get("crit",0) + talent_bonus.get("crit",0),
            "skill_pct": talent_bonus.get("skill_pct",0),
            "heal_pct": talent_bonus.get("heal_pct",0),
            "finisher_pct": talent_bonus.get("finisher_pct",0),
            "level": int(p.get("level",1)),
        }

    async def _combat_full_stats(self, guild_id, user_id, p, pet_bonus=None):
        talent_ranks=await self.talent_ranks(guild_id,user_id)
        talent_bonus=self._talent_bonuses(p,talent_ranks)
        stats=self._combat_stats(p,pet_bonus,talent_bonus)
        faction=await self._faction_passive(guild_id,user_id)
        if faction.get("def_pct"): stats["defense"]+=round(stats["defense"]*faction["def_pct"]/100)
        if faction.get("skill_pct"): stats["skill_pct"]=float(stats.get("skill_pct",0))+float(faction["skill_pct"])
        if faction.get("heal_pct"): stats["heal_pct"]=float(stats.get("heal_pct",0))+float(faction["heal_pct"])
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT slot,item_key,upgrade_level,intrinsic_json,set_key FROM rpg_equipment WHERE guild_id=? AND user_id=?",(guild_id,user_id)); gear=await cur.fetchall()
            cur=await db.execute("SELECT slot,enchant_key,level FROM rpg_equipment_enchants WHERE guild_id=? AND user_id=?",(guild_id,user_id)); enchants=await cur.fetchall()
        pct={"atk":0,"defense":0,"hp":0,"mp":0,"speed":0,"crit":0}
        set_counts={}
        for _slot,key,upgrade,intrinsic_json,set_key in gear:
            item=ITEMS.get(key,{})
            stats["max_hp"]+=item.get("hp",0)+int(upgrade)*max(2,item.get("hp",0)//10); stats["hp"]+=item.get("hp",0)+int(upgrade)*max(2,item.get("hp",0)//10)
            stats["max_mp"]+=item.get("mp",0)+int(upgrade)*max(1,item.get("mp",0)//10); stats["mp"]+=item.get("mp",0)+int(upgrade)*max(1,item.get("mp",0)//10)
            stats["atk"]+=item.get("atk",0)+int(upgrade)*max(1,item.get("atk",0)//8); stats["defense"]+=item.get("def",0)+int(upgrade)*max(1,item.get("def",0)//8); stats["speed"]+=item.get("spd",0)+int(upgrade)//3; stats["crit"]+=item.get("crit",0)+int(upgrade)//4
            pct["atk"]+=min(10,int(item.get("pct_atk",0))); pct["defense"]+=min(10,int(item.get("pct_def",0))); pct["hp"]+=min(10,int(item.get("pct_hp",0))); pct["mp"]+=min(10,int(item.get("pct_mp",0))); pct["speed"]+=min(10,int(item.get("pct_speed",0))); pct["crit"]+=min(10,int(item.get("pct_crit",0)))
            try: intr=json.loads(intrinsic_json or "{}")
            except json.JSONDecodeError: intr={}
            pct["atk"]+=int(intr.get("atk_pct",0)); pct["defense"]+=int(intr.get("def_pct",0)); pct["hp"]+=int(intr.get("hp_pct",0)); pct["speed"]+=int(intr.get("speed_pct",0)); stats["crit"]+=int(intr.get("crit_flat",0))
            if set_key: set_counts[set_key]=set_counts.get(set_key,0)+1
        for set_key,count in set_counts.items():
            focus=_set_focus(set_key)
            if count>=2: pct[focus]+=2
            if count>=4: pct[focus]+=5
            if count>=6: pct[focus]+=8
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
        elif race=="vampire": stats["atk"]+=3; stats["lifesteal_pct"]=.28; stats["lifesteal_min"]=4; stats["lifesteal_cap_pct"]=.08
        elif race=="golem": stats["max_hp"]+=max(1,round(stats["max_hp"]*.06)); stats["hp"]+=max(1,round(stats["hp"]*.06)); stats["defense"]+=3; stats["speed"]=max(1,stats["speed"]-2)
        subrace_trait=SUBRACE_TRAITS.get(p.get("subrace") or "",{})
        subclass_trait=SUBCLASS_TRAITS.get(p.get("subclass") or "",{})
        traits=(subrace_trait,subclass_trait)
        stats["trait_names"]=[t.get("name") for t in traits if t]
        stats["trait_skill_pct"]=sum(float(t.get("skill_pct",0)) for t in traits)
        stats["trait_finisher_pct"]=sum(float(t.get("finisher_pct",0)) for t in traits)
        stats["trait_damage_reduction"]=sum(float(t.get("damage_reduction",0)) for t in traits)
        stats["trait_low_hp_reduction"]=sum(float(t.get("low_hp_reduction",0)) for t in traits)
        stats["trait_high_hp_reduction"]=sum(float(t.get("high_hp_reduction",0)) for t in traits)
        stats["trait_low_hp_skill_pct"]=sum(float(t.get("low_hp_skill_pct",0)) for t in traits)
        stats["trait_low_hp_evasion"]=sum(float(t.get("low_hp_evasion",0)) for t in traits)
        stats["trait_high_target_pct"]=sum(float(t.get("high_target_pct",0)) for t in traits)
        stats["trait_low_target_pct"]=sum(float(t.get("low_target_pct",0)) for t in traits)
        stats["trait_combo_pct"]=sum(float(t.get("combo_pct",0)) for t in traits)
        stats["trait_next_skill_pct"]=sum(float(t.get("next_skill_pct",0)) for t in traits)
        stats["trait_skill_evasion"]=sum(float(t.get("skill_evasion",0)) for t in traits)
        stats["pet_damage_pct"]=sum(float(t.get("pet_damage_pct",0)) for t in traits)
        stats["trait_crit_damage_reduction"]=sum(float(t.get("crit_damage_reduction",0)) for t in traits)
        stats["trait_defend_reduction"]=sum(float(t.get("defend_reduction",0)) for t in traits)
        stats["trait_lifesteal"]=sum(float(t.get("trait_lifesteal",0)) for t in traits)
        stats["trait_lifesteal_cap"]=max([float(t.get("trait_lifesteal_cap",0)) for t in traits] or [0])
        stats["trait_skill_heal_pct"]=sum(float(t.get("skill_heal_pct",0)) for t in traits)
        stats["trait_conditional_skill_heal"]=sum(float(t.get("conditional_skill_heal",0)) for t in traits)
        stats["trait_resource_gain"]=sum(float(t.get("resource_gain",0)) for t in traits)
        stats["trait_resource_pct"]=sum(float(t.get("resource_pct",0)) for t in traits)
        stats["trait_effect_bonus"]={}
        for trait in traits:
            for effect,value in trait.get("effect_bonus",{}).items():
                stats["trait_effect_bonus"][effect]=stats["trait_effect_bonus"].get(effect,0)+float(value)
        starts=[t for t in traits if t.get("start_shield")]
        if starts:
            stats["trait_start_shield"]=max(float(t["start_shield"]) for t in starts)/100
            stats["trait_start_shield_turns"]=max(int(t.get("start_shield_turns",1)) for t in starts)
        stats["trait_reflect"]=sum(float(t.get("reflect",0)) for t in traits)
        stats["crit"]=min(35,stats["crit"])
        return stats

    def _enemy_for_level(self, level, area_key="horizon_village"):
        area=AREAS.get(area_key, AREAS["horizon_village"])
        # Adventure difficulty follows the hero. A high-level hero will not
        # randomly roll a level-1 slime as a free kill; the nearest world tier
        # is selected and then scaled to the target level.
        target=max(1, int(level))
        target=max(target, min(int(area["level"]), target + 3))
        regional=[e for e in ENEMIES if e.get("area_key")==area_key and e["level"] <= target + 3]
        eligible=regional or [e for e in ENEMIES if "area_key" not in e and e["level"] <= target + 2]
        if not eligible: eligible=regional or list(ENEMIES)
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

    async def _load_combat_session(self,guild_id,user_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT state_json,updated_at FROM rpg_combat_sessions WHERE guild_id=? AND user_id=?",(guild_id,user_id)); row=await cur.fetchone()
            if not row:return None
            if time.time()-float(row[1])>60*45:
                await db.execute("DELETE FROM rpg_combat_sessions WHERE guild_id=? AND user_id=?",(guild_id,user_id)); await db.commit(); return None
            try:return json.loads(row[0])
            except (TypeError,json.JSONDecodeError):
                await db.execute("DELETE FROM rpg_combat_sessions WHERE guild_id=? AND user_id=?",(guild_id,user_id)); await db.commit(); return None

    async def _persist_combat_session(self,guild_id,user_id,state):
        payload=json.dumps(state,separators=(",",":"),default=str)
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO rpg_combat_sessions(guild_id,user_id,state_json,updated_at) VALUES(?,?,?,?) ON CONFLICT(guild_id,user_id) DO UPDATE SET state_json=excluded.state_json,updated_at=excluded.updated_at",(guild_id,user_id,payload,time.time())); await db.commit()

    async def _delete_combat_session(self,guild_id,user_id):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM rpg_combat_sessions WHERE guild_id=? AND user_id=?",(guild_id,user_id)); await db.commit()

    async def start_combat(self,guild_id,user_id,mode="adventure",dungeon_name=None):
        p=await self.player(guild_id,user_id)
        if not p:return {"error":"Create a hero first."}
        key=(guild_id,user_id)

        # Recover persisted battles before rejecting an "active" in-memory entry.
        # This makes combat recoverable after a bot restart, a timed-out Discord
        # View, or a stale in-memory flag. A completed/corrupt persisted state is
        # cleared instead of trapping the player in a permanent battle lock.
        persisted=await self._load_combat_session(guild_id,user_id)
        if persisted:
            try:
                enemy_hp=float(persisted.get("enemy_hp",0))
                enemy=persisted.get("enemy") or {}
                valid=bool(persisted.get("mode") in {"adventure","dungeon"} and enemy.get("name") and enemy_hp>0)
            except (TypeError,ValueError):
                valid=False
            if not valid:
                self.active_combats.pop(key,None)
                await self._delete_combat_session(guild_id,user_id)
                return {"error":"Your previous battle state was incomplete, so Horizon cleared it. You can start a new battle now."}

            # A requested dungeon can replace a different saved dungeon run.
            # A dungeon run is temporary progress, not a permanent dungeon
            # selection. If the player explicitly names another unlocked
            # dungeon, abandon the old run and start the requested one below.
            # This also clears stale sessions left behind by an expired battle UI.
            if mode == "dungeon" and dungeon_name:
                requested = str(dungeon_name).strip().casefold()
                current = str(persisted.get("name") or "").strip().casefold()
                if current != requested:
                    self.active_combats.pop(key,None)
                    await self._delete_combat_session(guild_id,user_id)
                    persisted = None
                else:
                    self.active_combats[key]=persisted
                    return {"state":persisted,"stats":await self._combat_full_stats(guild_id,user_id,p,await self._pet_bonus(guild_id,user_id)),"resumed":True}
            else:
                self.active_combats[key]=persisted
                return {"state":persisted,"stats":await self._combat_full_stats(guild_id,user_id,p,await self._pet_bonus(guild_id,user_id)),"resumed":True}

        if key in self.active_combats:
            # The in-memory flag can survive longer than the actual battle.
            # Drop it when it is clearly no longer actionable.
            active=self.active_combats.get(key) or {}
            try:
                if float(active.get("enemy_hp",0))<=0 or not active.get("enemy"):
                    self.active_combats.pop(key,None)
                else:
                    return {"error":"You are already in a battle. Finish it first."}
            except (TypeError,ValueError):
                self.active_combats.pop(key,None)
        if p["hp"]<=0:return {"error":"You are down. Use `!rpg rest` first."}
        pet_bonus=await self._pet_bonus(guild_id,user_id)
        stats=await self._combat_full_stats(guild_id,user_id,p,pet_bonus)
        pet=await self.pet_record(guild_id,user_id)
        loadout=await self.skill_loadout(guild_id,user_id)
        base={"player_hp":stats["hp"],"player_max_hp":stats["max_hp"],"player_mp":stats["mp"],"player_max_mp":stats["max_mp"],"player_stamina":p["stamina"],"class_name":p["class_name"],"subrace":p.get("subrace") or "","subclass":p.get("subclass") or "","turn":1,"skill_cooldowns":{},"pet_cooldown":0,"pet":pet_bonus,"combat_stats":stats,"player_level":p["level"],"equipped_skill_keys":[skill["key"] for _slot,skill in loadout if skill],"buffs":{},"enemy_debuffs":{},"enemy_statuses":{},"enemy_dot":0,"enemy_dot_turns":0,"enemy_ability_cooldowns":{},"enemy_guard_turns":0,"enemy_guard_pct":0,"player_dot":0,"player_dot_turns":0,"combo":0,"combo_chain":[],"combo_unique":[],"combo_last_skill":"","combo_repeat":0,"combo_peak":0,"last_skill_effect":"","delayed_damage":0,"shield_turns":int(stats.get("trait_start_shield_turns",0)),"shield_pct":float(stats.get("trait_start_shield",0))}
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

            # Accept the same dungeon identifiers players see in `!rpg dungeons`:
            # the display name ("Goblin Caves"), the command key/slug
            # ("goblin_caves"), and a simple 1-based index among unlocked dungeons.
            # The old code only accepted the exact display name, so a player who
            # copied the key shown by the atlas could not switch dungeons even
            # though the dungeon was unlocked.
            d=None
            if dungeon_name:
                raw=str(dungeon_name).strip()
                folded=raw.casefold()
                slug="_".join(raw.casefold().replace("'", "").replace("’", "").split())
                if folded.isdigit():
                    idx=int(folded)-1
                    if 0 <= idx < len(available):
                        d=available[idx]
                if d is None:
                    d=next((x for x in available if x[0].casefold()==folded),None)
                if d is None:
                    d=next((x for x in available if x[0].casefold().replace(" ","_").replace("'","").replace("’","")==slug),None)
                if d is None:
                    return {"error":f"Dungeon **{raw}** is not unlocked or was not found. Use `!rpg dungeons` and enter the dungeon name or key shown there."}
            else:
                d=available[-1] if available else None
            if not d:return {"error":"No dungeon unlocked yet."}
            n,req,floors,xp,gold,desc=d
            stamina_cost=15 + max(0, floors-3)*3
            if p["stamina"]<stamina_cost:return {"error":f"You need **{stamina_cost} stamina** to enter this dungeon. Use `!rpg rest`."}
            enemy=self._enemy_for_level(p["level"]+max(0, req-p["level"])+1,p.get("area_key","horizon_village"))
            enemy["dungeon_name"]=n; enemy["is_boss"]=False
            async with aiosqlite.connect(self.path) as db:
                await db.execute("UPDATE rpg_players SET stamina=stamina-? WHERE guild_id=? AND user_id=?",(stamina_cost,guild_id,user_id)); await db.commit()
            base["player_stamina"]=max(0,p["stamina"]-stamina_cost)
            state={"mode":"dungeon","enemy":enemy,"enemy_hp":enemy["hp"],"floor":1,"floors":floors,"name":n,"reward_xp":xp,"reward_gold":gold,"log":[f"**Floor 1/{floors}** — {enemy['name']} blocks your path."],"started":time.time(),**base}
        self.active_combats[key]=state
        await self._persist_combat_session(guild_id,user_id,state)
        return {"state":state,"stats":stats,"pet":pet}

    def _skill(self, class_name, skill_key, subclass=""):
        pool=list(SKILLS.get(class_name, []))+list(SUBCLASS_SKILLS.get(subclass, []))
        return next((s for s in pool if s["key"] == skill_key), None)

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
        return {key for _slot,key in loadout_rows if key in {s["key"] for s in self.skills_for_player(p)}}

    def _skill_damage(self, stats, enemy, skill, state, multiplier=None, ignore_def=False):
        enemy_def=float(enemy.get("def",0))
        enemy_def*=1+float(state.get("enemy_guard_pct",0))
        debuff=state.get("enemy_debuffs",{})
        enemy_def=max(0,enemy_def*(1-float(debuff.get("def_down",0))))
        mult=float(multiplier if multiplier is not None else skill.get("mult",1.0))
        if state.get("buffs",{}).get("atk_up"):
            mult*=1+float(state["buffs"]["atk_up"])
        if stats.get("skill_pct"):
            mult*=1+float(stats.get("skill_pct",0))/100
        if skill.get("finisher") or skill.get("effect") in {"execute","ultimate","signature","mythic"}:
            if stats.get("finisher_pct"):
                mult*=1+float(stats.get("finisher_pct",0))/100
            if stats.get("trait_finisher_pct"):
                mult*=1+float(stats.get("trait_finisher_pct",0))/100
        mult*=1+float(stats.get("trait_skill_pct",0))/100
        effect=skill.get("effect","damage")
        effect_bonus=float(stats.get("trait_effect_bonus",{}).get(effect,0))
        if effect_bonus:
            mult*=1+effect_bonus/100
        if stats.get("trait_low_hp_skill_pct") and state.get("player_hp",stats.get("max_hp",1))<=stats.get("max_hp",1)*.5:
            mult*=1+float(stats["trait_low_hp_skill_pct"])/100
        if stats.get("trait_high_target_pct") and state.get("enemy_hp",0)>=enemy.get("hp",1)*.70:
            mult*=1+float(stats["trait_high_target_pct"])/100
        if stats.get("trait_low_target_pct") and state.get("enemy_hp",0)<=enemy.get("hp",1)*.40:
            mult*=1+float(stats["trait_low_target_pct"])/100
        # Advanced combo scaling:
        # - every successful skill can continue the chain
        # - varied skills get a small diversity bonus
        # - repeating the exact same skill is still viable, but suffers a
        #   repetition penalty so one-button spam is never optimal
        combo=int(state.get("combo",0))
        if combo>0:
            combo_bonus=min(.45, .035*combo)
            unique_count=len(set(state.get("combo_unique",[])))
            diversity_bonus=min(.08, .015*max(0,unique_count-1))
            repeat_penalty=min(.18, .035*max(0,int(state.get("combo_repeat",0))-1))
            mult*=1+max(0.0,combo_bonus+diversity_bonus-repeat_penalty)
        if stats.get("trait_combo_pct"):
            mult*=1+min(.40,float(stats["trait_combo_pct"])*float(state.get("combo",0))/100)
        if stats.get("trait_next_skill_pct") and state.get("trait_next_skill_bonus",0):
            mult*=1+float(stats["trait_next_skill_pct"])/100
            state["trait_next_skill_bonus"]=0
        if state.get("trait_dodge_bonus",0):
            mult*=1+float(state["trait_dodge_bonus"])/100
            state["trait_dodge_bonus"]=0
        if debuff.get("vulnerable"):
            mult*=1+float(debuff["vulnerable"])
        if debuff.get("marked"):
            mult*=1+float(debuff["marked"])
        if ignore_def:
            raw=max(2,int(stats["atk"]*mult*random.uniform(0.92,1.08)))
            return raw
        return self._damage(stats["atk"],enemy_def,mult)

    def _apply_enemy_status(self, state, status, turns, power=0.0, source=""):
        statuses=state.setdefault("enemy_statuses",{})
        current=statuses.get(status)
        statuses[status]={"turns":max(int(turns),int(current.get("turns",0)) if current else 0),"power":max(float(power),float(current.get("power",0)) if current else 0.0),"source":source}

    def _status_summary(self, statuses):
        if not statuses:return "None"
        labels={"bleed":"🩸 Bleed","poison":"☠️ Poison","burn":"🔥 Burn","freeze":"❄️ Freeze","stun":"💫 Stun","silence":"🔇 Silence","slow":"🐌 Slow","vulnerable":"🔻 Vulnerable","weaken":"⬇️ Weaken"}
        return " • ".join(f"{labels.get(k,k.title())} {int(v.get('turns',0))}t" for k,v in statuses.items() if int(v.get("turns",0))>0)

    def _tick_enemy_statuses(self, state):
        statuses=state.setdefault("enemy_statuses",{})
        if not statuses:return []
        enemy=state["enemy"]; logs=[]
        total_dot=0
        for name,data in list(statuses.items()):
            turns=int(data.get("turns",0)); power=float(data.get("power",0))
            if turns<=0: statuses.pop(name,None); continue
            if name in {"bleed","poison","burn"}:
                amount=max(2,int(state.get("combat_stats",{}).get("atk",10)*power))
                amount=min(amount,max(2,int(enemy.get("hp",100)*.08)))
                state["enemy_hp"]=max(0,state["enemy_hp"]-amount); total_dot+=amount
                logs.append(f"{ {'bleed':'🩸','poison':'☠️','burn':'🔥'}.get(name,'')} {name.title()} dealt **{amount}** damage.")
            data["turns"]=turns-1
            if data["turns"]<=0: statuses.pop(name,None)
        if total_dot: state["enemy_dot"]=total_dot
        return logs

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
            state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*0.22))); self._apply_enemy_status(state,"bleed",3,.08,skill["name"]); log.append(f"🩸 **{skill['name']}** dealt **{dmg}** and applied **Bleed** for 3 turns.")
        elif effect=="multi":
            hits=[]
            for _ in range(2):
                hit=self._skill_damage(stats,enemy,skill,state,skill["mult"]*0.58); hit=min(hit,max(2,int(enemy["hp"]*0.16))); state["enemy_hp"]-=hit; hits.append(hit)
            log.append(f"⚔️ **{skill['name']}** struck twice for **{sum(hits)}** total.")
        elif effect in {"heal","team_heal","recovery"}:
            ratio={"heal":0.22,"team_heal":0.30,"recovery":0.34}[effect]
            ratio*=1+float(stats.get("heal_pct",0)+stats.get("trait_skill_heal_pct",0))/100
            if state["player_hp"]<=stats["max_hp"]*.60:
                ratio*=1+float(stats.get("trait_conditional_skill_heal",0))/100
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
            state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.22))); state["enemy_debuffs"]["def_down"]=.18; state["enemy_debuffs"]["def_turns"]=3; self._apply_enemy_status(state,"weaken",3,.18,skill["name"]); log.append(f"🗡️ **{skill['name']}** dealt **{dmg}** and reduced defense for 3 turns.")
        elif effect=="mark":
            state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.18))); state["enemy_debuffs"]["marked"]=.16; state["enemy_debuffs"]["mark_turns"]=3; log.append(f"🎯 **{skill['name']}** marked the enemy; follow-up damage is increased.")
        elif effect in {"poison","burn"}:
            state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.18))); self._apply_enemy_status(state,effect,3 if effect=="burn" else 4,.07,skill["name"]); log.append(f"{'🔥' if effect=='burn' else '☠️'} **{skill['name']}** dealt **{dmg}** and applied **{effect.title()}**.")
        elif effect=="freeze":
            state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.20))); self._apply_enemy_status(state,"freeze",2,.0,skill["name"]); state["enemy_debuffs"]["slow_turns"]=2
            if random.random()<.35: self._apply_enemy_status(state,"stun",1,.0,skill["name"]); log.append(f"💫 **{skill['name']}** also stunned the enemy!")
            log.append(f"❄️ **{skill['name']}** dealt **{dmg}** and applied **Freeze** for 2 turns.")
        elif effect=="crit":
            state["buffs"]["crit_up"]=12; state["buffs"]["crit_turns"]=2; state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.18))); log.append(f"🎯 **{skill['name']}** sharpened your critical chance.")
        elif effect in {"dodge","dodge"}:
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
            state["enemy_hp"]-=min(dmg,max(2,int(enemy["hp"]*.15))); state["enemy_debuffs"]["vulnerable"]=.20; state["enemy_debuffs"]["vuln_turns"]=2; self._apply_enemy_status(state,"vulnerable",2,.20,skill["name"]); log.append(f"🔻 **{skill['name']}** exposed a weakness for 2 turns.")
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
            dmg=self._skill_damage(stats,enemy,skill,state,skill["mult"]*1.08); dmg=min(dmg,max(2,int(enemy["hp"]*.30))); state["enemy_hp"]-=dmg; gain=max(3,int(stats["max_mp"]*.06)); state["player_mp"]=min(stats["max_mp"],state["player_mp"]+gain); log.append(f"💧 **{skill['name']}** released **{dmg}** damage and restored {gain} MP.")
        elif effect=="curse":
            dmg=self._skill_damage(stats,enemy,skill,state); dmg=min(dmg,max(2,int(enemy["hp"]*.18))); state["enemy_hp"]-=dmg; state["enemy_debuffs"].update(vulnerable=.14,vuln_turns=3); self._apply_enemy_status(state,"curse",3,.06,skill["name"]); self._apply_enemy_status(state,"vulnerable",3,.14,skill["name"]); log.append(f"🕯️ **{skill['name']}** cursed the target after dealing **{dmg}** damage.")
        elif effect=="focus":
            state["buffs"].update(crit_up=10,crit_turns=3); log.append(f"🎯 **{skill['name']}** focused your next attacks.")
        elif effect=="ultimate":
            hit=self._skill_damage(stats,enemy,skill,state,skill["mult"]*1.18); state["enemy_hp"]-=min(hit,max(2,int(enemy["hp"]*.38))); heal=max(4,int(stats["max_hp"]*.08)); state["player_hp"]=min(stats["max_hp"],state["player_hp"]+heal); log.append(f"🌠 **{skill['name']}** unleashed **{hit}** damage and restored **{heal} HP**.")
        elif effect=="mythic":
            hit=self._skill_damage(stats,enemy,skill,state,skill["mult"]*1.15); state["enemy_hp"]-=min(hit,max(2,int(enemy["hp"]*.38))); state["enemy_debuffs"]["vulnerable"]=.12; state["enemy_debuffs"]["vuln_turns"]=2; log.append(f"👑 **{skill['name']}** combined damage and exposure for **{hit}**.")
        elif effect=="signature":
            hit=self._skill_damage(stats,enemy,skill,state,skill["mult"]*1.2); state["enemy_hp"]-=min(hit,max(2,int(enemy["hp"]*.40))); state["buffs"]["atk_up"]=.18; state["buffs"]["atk_turns"]=2; log.append(f"✨ **{skill['name']}** unleashed your class signature for **{hit}** damage.")
        # Advanced combo engine.
        # A combo is a sequence of successful skills, not a single skill being
        # pressed repeatedly. Every damaging technique can continue it.
        dealt_before_combo=max(0,start_enemy_hp-state["enemy_hp"])
        if dealt_before_combo>0:
            skill_key=str(skill.get("key",effect))
            previous_key=state.get("combo_last_skill","")
            previous_effect=state.get("last_skill_effect","")
            chain=state.setdefault("combo_chain",[])
            unique=state.setdefault("combo_unique",[])
            if previous_key:
                state["combo"]=min(10,int(state.get("combo",0))+1)
            else:
                state["combo"]=1
            if skill_key==previous_key:
                state["combo_repeat"]=int(state.get("combo_repeat",0))+1
            else:
                state["combo_repeat"]=0
            if skill_key not in unique:
                unique.append(skill_key)
                del unique[:-6]
            chain.append(skill_key)
            del chain[:-5]
            state["combo_peak"]=max(int(state.get("combo_peak",0)),int(state["combo"]))

            # Specific technique pairings create a small tactical bonus.
            combo_pairs={
                ("armor_break","heavy"):("🗡️ Armor shattered → Power Blow",.07),
                ("mark","execute"):("🎯 Mark → Execution",.10),
                ("vulnerability","execute"):("🔻 Exposure → Execution",.12),
                ("bleed","lifesteal"):("🩸 Bleed → Blood Drain",.08),
                ("poison","execute"):("☠️ Venom → Execution",.10),
                ("curse","execute"):("🕯️ Curse → Execution",.10),
                ("def_buff","attack_buff"):("🛡️ Guard → Counterpressure",.05),
                ("attack_buff","heavy"):("⚔️ Power → Heavy Strike",.07),
                ("multi","bleed"):("⚔️ Flurry → Bleeding Wound",.06),
                ("freeze","heavy"):("❄️ Freeze → Shatter",.10),
                ("mana_drain","ultimate"):("💧 Siphon → Ultimate",.08),
                ("combo","multi"):("🔗 Chain → Flurry",.07),
            }
            pair=combo_pairs.get((previous_effect,effect))
            if pair:
                label,percent=pair
                extra=max(1,int(dealt_before_combo*percent))
                state["enemy_hp"]=max(0,state["enemy_hp"]-extra)
                log.append(f"{label} • **+{extra} combo damage**")

            # Finishers cash in the chain. They get stronger from the combo,
            # then the chain resets so players must build it again.
            if effect in {"execute","ultimate","signature","mythic"}:
                finisher_combo=int(state.get("combo",1))
                finisher_bonus=min(.60,.10*finisher_combo)
                extra=max(1,int(max(1,stats["atk"])*finisher_bonus))
                state["enemy_hp"]=max(0,state["enemy_hp"]-extra)
                log.append(f"💥 **COMBO FINISHER x{finisher_combo}** • +{extra} bonus damage")
                state["combo"]=0
                state["combo_chain"]=[]
                state["combo_unique"]=[]
                state["combo_repeat"]=0
            else:
                unique_count=len(set(state.get("combo_unique",[])))
                combo_bonus=min(45,int(round((.035*int(state["combo"])+.015*max(0,unique_count-1))*100)))
                if combo_bonus>0:
                    log.append(f"🔗 **COMBO x{state['combo']}** • +{combo_bonus}% chain damage")
        else:
            # Missed/zero-damage techniques break the offensive chain.
            state["combo"]=0
            state["combo_chain"]=[]
            state["combo_unique"]=[]
            state["combo_repeat"]=0

        state["last_skill_effect"]=effect
        dealt=max(0,start_enemy_hp-state["enemy_hp"])
        if dealt:
            if stats.get("trait_skill_evasion"):
                state["buffs"]["evasion"]=max(float(state["buffs"].get("evasion",0)),float(stats["trait_skill_evasion"])/100)
                state["buffs"]["evasion_turns"]=max(1,int(state["buffs"].get("evasion_turns",0)))
            if stats.get("trait_resource_gain"):
                state["player_mp"]=min(stats["max_mp"],state["player_mp"]+int(stats["trait_resource_gain"]))
            if stats.get("trait_resource_pct"):
                state["player_mp"]=min(stats["max_mp"],state["player_mp"]+max(1,int(stats["max_mp"]*stats["trait_resource_pct"]/100)))
            if stats.get("trait_lifesteal"):
                cap=max(1,int(stats["max_hp"]*max(.01,stats.get("trait_lifesteal_cap",5))/100))
                heal=min(cap,max(1,int(dealt*stats["trait_lifesteal"]/100)))
                state["player_hp"]=min(stats["max_hp"],state["player_hp"]+heal)
            if stats.get("trait_next_skill_pct"):
                state["trait_next_skill_bonus"]=1
        if stats.get("lifesteal_pct") and dealt:
            heal=min(max(1,int(stats.get("max_hp",100)*float(stats.get("lifesteal_cap_pct",1)))), max(int(stats.get("lifesteal_min",1)),int(dealt*float(stats["lifesteal_pct"])))); state["player_hp"]=min(stats["max_hp"],state["player_hp"]+heal); log.append(f"🩸 Blood Hunger restored **{heal} HP**.")
        return log,defending

    def _enemy_ability_action(self, state, stats):
        enemy=state.get("enemy",{})
        abilities=[k for k in enemy.get("abilities",[]) if k in ENEMY_ABILITIES]
        if not abilities or state.get("enemy_debuffs",{}).get("silence_turns",0)>0:return []
        cooldowns=state.setdefault("enemy_ability_cooldowns",{})
        ready=[k for k in abilities if int(cooldowns.get(k,0))<=0]
        if not ready:return []
        chance=min(0.34,0.12+float(enemy.get("speed",5))/350.0+(0.05 if enemy.get("is_boss") else 0))
        if random.random()>chance:return []
        key=random.choice(ready); ability=ENEMY_ABILITIES[key]; kind=ability["type"]
        enemy_atk=float(enemy.get("atk",1))*(1+float(state.get("enemy_atk_up",0)))
        player_def=float(stats["defense"])*(1-float(state.get("player_debuff_def",0)))
        if kind=="guard":
            dmg=self._damage(enemy_atk,player_def,float(ability["mult"]),ENEMY_DAMAGE_VARIANCE); dmg,crit=self._crit_damage(dmg,int(enemy.get("crit",0)))
            dmg=min(dmg,max(2,int(stats["max_hp"]*.20))); state["player_hp"]-=dmg; state["enemy_guard_pct"]=.35; state["enemy_guard_turns"]=2; cooldowns[key]=int(ability["cooldown"])
            return [f"🛡️ **{enemy['name']}** used **{ability['name']}** for **{dmg}** damage and raised its guard."]
        if kind=="pierce": player_def=max(0,player_def*.55)
        dmg=self._damage(enemy_atk,player_def,float(ability["mult"]),ENEMY_DAMAGE_VARIANCE); dmg,crit=self._crit_damage(dmg,int(enemy.get("crit",0)))
        dmg=min(dmg,max(2,int(stats["max_hp"]*(.30 if kind in {"burst","magic","pierce"} else .25)))); state["player_hp"]-=dmg
        logs=[f"✨ **{enemy['name']}** used **{ability['name']}** for **{dmg}**{' CRITICAL' if crit else ''} damage."]
        if kind=="heal":
            heal=max(5,int(enemy.get("hp",1)*.10)); state["enemy_hp"]=min(enemy.get("hp",state["enemy_hp"]),state["enemy_hp"]+heal); logs.append(f"💚 **{enemy['name']}** regenerated **{heal} HP**.")
        elif kind=="drain":
            heal=max(3,int(dmg*.35)); state["enemy_hp"]=min(enemy.get("hp",state["enemy_hp"]),state["enemy_hp"]+heal); logs.append(f"🩸 **{enemy['name']}** drained **{heal} HP**.")
        elif kind in {"burn","poison"}:
            dot=max(2,int(stats["max_hp"]*(.045 if kind=="burn" else .035))); state["player_dot"]=max(int(state.get("player_dot",0)),dot); state["player_dot_turns"]=3; logs.append(f"☠️ You are afflicted with **{'Burn' if kind=='burn' else 'Poison'}** for 3 turns.")
        elif kind=="buff":
            state["enemy_atk_up"]=max(float(state.get("enemy_atk_up",0)),.20); state["enemy_atk_turns"]=3; logs.append("🔥 Its attack rose for 3 turns.")
        elif kind=="debuff":
            state["player_debuff_def"]=.15; state["player_debuff_def_turns"]=2; logs.append("🔻 Your effective defense was reduced for 2 turns.")
        cooldowns[key]=int(ability["cooldown"])
        return logs

    async def combat_action(self,guild_id,user_id,action):
        key=(guild_id,user_id)
        lock=self.combat_locks.setdefault(key, asyncio.Lock())
        if lock.locked():
            return {"error":"Your previous combat action is still processing. Please wait a moment."}
        async with lock:
            return await self._combat_action_locked(guild_id,user_id,action)

    async def _safe_player_level(self,guild_id,user_id,fallback=1):
        """Read level for a victory panel without allowing a DB failure to hide victory."""
        try:
            p=await self.player(guild_id,user_id)
            return int(p.get("level",fallback)) if p else int(fallback)
        except Exception:
            log.exception("Failed to read player level for victory panel: guild=%s user=%s",guild_id,user_id)
            return int(fallback)

    async def _combat_action_locked(self,guild_id,user_id,action):
        key=(guild_id,user_id); state=self.active_combats.get(key)
        # Recover the authoritative persistent state if a Discord view timed
        # out or the process briefly lost its in-memory combat cache. Never let
        # a stale UI create a second battle or silently lose the real one.
        if not state:
            persisted=await self._load_combat_session(guild_id,user_id)
            if persisted:
                try:
                    if persisted.get("mode") in {"adventure","dungeon"} and (persisted.get("enemy") or {}).get("name") and float(persisted.get("enemy_hp",0))>0:
                        state=persisted
                        self.active_combats[key]=state
                except (TypeError,ValueError):
                    state=None
        if not state:return {"error":"No active battle."}
        # A completed enemy must never receive another enemy turn. This guard
        # lets the final player action resolve cleanly even if a stale Discord
        # component arrives a moment later.
        try:
            if float(state.get("enemy_hp",0))<=0:
                await self._delete_combat_session(guild_id,user_id)
                self.active_combats.pop(key,None)
                return {"finished":True,"win":False,"already_completed":True,"state":state,"log":[*state.get("log",[]),"🏆 This battle was already completed. No additional rewards were granted."]}
        except (TypeError,ValueError):
            self.active_combats.pop(key,None); await self._delete_combat_session(guild_id,user_id)
            return {"error":"Horizon cleared an invalid battle state. You can start a new battle."}
        p=await self.player(guild_id,user_id)
        if not p:return {"error":"Character not found."}
        pet_bonus=await self._pet_bonus(guild_id,user_id)
        stats=await self._combat_full_stats(guild_id,user_id,p,pet_bonus); state["combat_stats"]=stats; state["player_max_hp"]=stats["max_hp"]; state["player_max_mp"]=stats["max_mp"]
        state["player_hp"]=max(0,min(state["player_hp"],stats["max_hp"]))
        state["player_mp"]=max(0,min(state.get("player_mp",stats["mp"]),stats["max_mp"]))
        stats["crit"]=min(35,stats.get("crit",0)+int(state.get("buffs",{}).get("crit_up",0)))
        action=action.lower().strip(); log=[]; defending=False
        if action=="attack":
            dmg, crit = self._crit_damage(self._damage(stats["atk"], state["enemy"].get("def",0)*(1+float(state.get("enemy_guard_pct",0))), 0.85), stats["crit"])
            dmg=min(dmg, max(2,int(state["enemy"].get("hp",1)*0.28)))
            state["enemy_hp"]-=dmg; log.append(f"⚔️ You hit **{state['enemy']['name']}** for **{dmg}**{' CRITICAL' if crit else ''}.")
            if stats.get("lifesteal_pct"):
                heal=min(max(1,int(stats.get("max_hp",100)*float(stats.get("lifesteal_cap_pct",1)))), max(int(stats.get("lifesteal_min",1)),int(dmg*float(stats["lifesteal_pct"])))); state["player_hp"]=min(stats["max_hp"],state["player_hp"]+heal); log.append(f"🩸 Blood Hunger restored **{heal} HP**.")
        elif action.startswith("skill:") or action=="skill":
            loadout=await self.skill_loadout(guild_id,user_id)
            equipped={skill["key"] for _slot,skill in loadout if skill}
            if action=="skill":
                skills=[skill for _slot,skill in loadout if skill and self._skill_available(p,skill)]
                return {"choose_skill":True,"skills":skills,"state":state}
            skill_key=action.split(":",1)[1].strip(); skill=self._skill_for_player(p,skill_key)
            if not skill:return {"error":"That skill is not available to your class."}
            if skill_key not in equipped:return {"error":"That skill is not equipped. You can equip up to **4 skills** with `!rpg equip-skill <skill> <slot>`."}
            if not self._skill_available(p,skill):
                return {"error":f"**{skill['name']}** unlocks at level **{skill.get('unlock',1)}**. You are level **{p['level']}**."}
            cooldown=int(state.get("skill_cooldowns",{}).get(skill_key,0))
            if cooldown>0:return {"error":f"**{skill['name']}** is on cooldown for **{cooldown}** more turn(s)."}
            cost=skill["cost"]
            if state["player_mp"]<cost:return {"error":f"You need **{cost} MP** for **{skill['name']}**. Current MP: {state['player_mp']}."}
            state["player_mp"]-=cost
            mastery=await self.skill_masteries(guild_id,user_id)
            skill=dict(skill)
            skill_rank=max(1,int(mastery.get(skill["key"],1)))
            skill["mastery_rank"]=skill_rank
            skill["mult"]=float(skill.get("mult",1.0))*(1+SKILL_RANK_DAMAGE*(skill_rank-1))
            if skill.get("heal_pct"):
                skill["heal_pct"]=float(skill["heal_pct"])+SKILL_RANK_HEAL*(skill_rank-1)
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
                dmg=self._damage(max(2,pet_bonus.get("atk",0)*2), state["enemy"].get("def",0), 0.65); dmg=min(dmg,max(2,int(state["enemy"].get("hp",1)*0.15))); dmg=int(dmg*(1+float(stats.get("pet_damage_pct",0))/100)); state["enemy_hp"]-=dmg; log.append(f"🐾 **{pet_bonus['name']}** used **{pet_bonus['ability']}** for **{dmg}** damage.")
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
            # Fleeing is allowed from every dungeon floor. A flee abandons the
            # entire run and gives no dungeon-clear reward, but never traps the
            # player on a later floor.
            if random.random()<0.65:
                self.active_combats.pop(key,None); await self._save_combat_hp(guild_id,user_id,state); await self._delete_combat_session(guild_id,user_id)
                return {"finished":True,"win":False,"fled":True,"log":[*state["log"],"🏃 You escaped the battle."]}
            log.append("You failed to escape!")
        else:return {"error":"Choose Attack, Skill, Potion, Pet, Defend or Flee."}
        state["log"].extend(log)
        if state["enemy_hp"]<=0:
            if state["mode"]=="dungeon" and state["floor"]<state["floors"]:
                state["floor"]+=1
                if state["floor"]==state["floors"]:
                    state["enemy"]=self._enemy_for_level(p["level"]+state["floor"]+1,p.get("area_key","horizon_village"))
                    state["enemy"]["name"]=DUNGEON_BOSSES.get(state["name"],state["enemy"]["name"])
                    state["enemy"]["is_boss"]=True
                    state["enemy"]["hp"]=int(state["enemy"]["hp"]*2.6); state["enemy"]["atk"]=int(state["enemy"]["atk"]*1.35); state["enemy"]["def"]=int(state["enemy"]["def"]*1.25)
                else:
                    state["enemy"]=self._enemy_for_level(p["level"]+state["floor"]+1,p.get("area_key","horizon_village")); state["enemy"]["is_boss"]=False
                state["enemy_hp"]=state["enemy"]["hp"]
                state["player_hp"]=min(stats["max_hp"],state["player_hp"]+max(5,stats["max_hp"]//8)); state["player_mp"]=min(stats["max_mp"],state["player_mp"]+max(3,stats["max_mp"]//10))
                state["enemy_statuses"]={}; state["combo"]=0; state["combo_chain"]=[]; state["last_skill_effect"]=""
                boss_tag=" 👑 BOSS" if state["enemy"].get("is_boss") else ""
                state["log"].append(f"🏰 **Floor {state['floor']}/{state['floors']}** — **{state['enemy']['name']}**{boss_tag} appears. You recover HP and MP between floors.")
                await self.progress_quests(guild_id,user_id,"dungeon",1); await self._save_combat_hp(guild_id,user_id,state)
                async with aiosqlite.connect(self.path) as db: await db.execute("UPDATE rpg_players SET mp=? WHERE guild_id=? AND user_id=?",(state["player_mp"],guild_id,user_id)); await db.commit()
                return {"finished":False,"state":state,"stats":stats}
            # Victory is authoritative before rewards: once enemy HP reaches 0,
            # the battle is resolved and the Discord panel must be able to render
            # victory even if any optional reward subsystem fails afterward.
            xp=(state.get("enemy",{}).get("xp",40)+random.randint(0,25)) if state["mode"]=="adventure" else state["reward_xp"]+state["floors"]*55
            gold=(state.get("enemy",{}).get("gold",30)+random.randint(0,35)) if state["mode"]=="adventure" else state["reward_gold"]+random.randint(0,120)
            drop=random.choice(state["enemy"].get("drops",["herb"]))
            if random.random()<0.08:
                egg_pool=[k for k,v in ITEMS.items() if v.get("slot")=="egg" and (v.get("rarity") in {"common","uncommon","rare"} or p["level"]>=20)]
                if egg_pool: drop=random.choice(egg_pool)

            # Persist the resolved state and remove the live session BEFORE reward
            # processing. Reward code is secondary to the fact that the enemy died.
            state["battle_status"]="victory"
            state["victory_at"]=time.time()
            state["reward_status"]="processing"
            try:
                await self._save_combat_hp(guild_id,user_id,state)
            except Exception:
                log.exception("Failed to save final victory HP: guild=%s user=%s",guild_id,user_id)
            self.active_combats.pop(key,None)
            try:
                await self._delete_combat_session(guild_id,user_id)
            except Exception:
                log.exception("Failed to delete resolved combat session: guild=%s user=%s",guild_id,user_id)

            old_level=await self._safe_player_level(guild_id,user_id,p.get("level",1))
            new_level=old_level
            extra_loot=[]
            pet_xp=0
            reward_errors=[]

            # Each reward category is isolated. A bug in pet XP, achievements,
            # loot, or renown can never erase the already-established victory.
            try:
                old_level,new_level=await self.add_rewards(guild_id,user_id,xp,gold)
            except Exception as exc:
                reward_errors.append("XP/Gold")
                await self._queue_pending_reward(guild_id,user_id,"xp_gold",{"xp":xp,"gold":gold,"battle_at":state.get("victory_at",time.time())},source="combat_victory")
                log.exception("Combat XP/Gold reward failed after victory: guild=%s user=%s",guild_id,user_id)
            try:
                await self.add_item(guild_id,user_id,drop,1,event_type="combat_drop")
            except Exception:
                reward_errors.append("loot")
                await self._queue_pending_reward(guild_id,user_id,"item",{"item_key":drop,"quantity":1,"battle_at":state.get("victory_at",time.time())},source="combat_victory")
                log.exception("Combat loot reward failed after victory: guild=%s user=%s",guild_id,user_id)
            try:
                extra_loot=await self._combat_loot(guild_id,user_id,p,state.get("enemy",{}))
            except Exception:
                reward_errors.append("extra loot")
                log.exception("Combat extra loot failed after victory: guild=%s user=%s",guild_id,user_id)
            try:
                pet_xp=await self._grant_pet_xp(guild_id,user_id,12 if state["mode"]=="adventure" else 20)
            except Exception:
                reward_errors.append("pet XP")
                await self._queue_pending_reward(guild_id,user_id,"pet_xp",{"amount":12 if state["mode"]=="adventure" else 20,"battle_at":state.get("victory_at",time.time())},source="combat_victory")
                log.exception("Combat pet XP failed after victory: guild=%s user=%s",guild_id,user_id)
            try:
                async with aiosqlite.connect(self.path) as db:
                    await db.execute("UPDATE rpg_players SET renown=renown+?,fame=fame+? WHERE guild_id=? AND user_id=?",(2 if state["mode"]=="adventure" else 5,1,guild_id,user_id)); await db.commit()
            except Exception:
                reward_errors.append("renown")
                await self._queue_pending_reward(guild_id,user_id,"renown",{"renown":2 if state["mode"]=="adventure" else 5,"fame":1,"battle_at":state.get("victory_at",time.time())},source="combat_victory")
                log.exception("Combat renown reward failed after victory: guild=%s user=%s",guild_id,user_id)
            try:
                await self.progress_quests(guild_id,user_id,"hunt",1)
                if state["mode"]=="dungeon":
                    await self.progress_quests(guild_id,user_id,"dungeon",1)
                    if state["floors"]>=5:
                        try:
                            await self.add_item(guild_id,user_id,"dragon_trophy",1,event_type="combat_dungeon_trophy")
                        except Exception:
                            reward_errors.append("dragon trophy")
                            await self._queue_pending_reward(guild_id,user_id,"item",{"item_key":"dragon_trophy","quantity":1,"battle_at":state.get("victory_at",time.time())},source="combat_victory")
            except Exception:
                reward_errors.append("quest progress")
                log.exception("Combat quest reward/progress failed after victory: guild=%s user=%s",guild_id,user_id)
            try:
                await self.check_achievements(guild_id,user_id)
            except Exception:
                reward_errors.append("achievements")
                log.exception("Combat achievement processing failed after victory: guild=%s user=%s",guild_id,user_id)

            state["reward_status"]="complete" if not reward_errors else "recovery_needed"
            if reward_errors:
                state["reward_errors"]=reward_errors
                state["log"].append("⚠️ Victory was secured, but some rewards could not be processed. Use !rpg pending to recover the saved rewards without replaying the battle.")

            return {"finished":True,"win":True,"xp":xp,"gold":gold,"drop":drop,"extra_loot":extra_loot,"pet_xp":pet_xp,"state":state,"level_before":old_level,"level_after":new_level,"reward_status":state["reward_status"],"reward_errors":reward_errors}
        # Enemy turn: monsters have their own speed, crit chance and active ability kits.
        status_logs=self._tick_enemy_statuses(state)
        if status_logs: state["log"].extend(status_logs)
        if state.get("player_dot_turns",0)>0 and state.get("player_dot",0)>0 and state["player_hp"]>0:
            dot=min(int(state["player_dot"]),max(1,int(stats["max_hp"]*.10))); state["player_hp"]-=dot; state["log"].append(f"☠️ Ongoing damage dealt **{dot}** to you."); state["player_dot_turns"]-=1
            if state["player_dot_turns"]<=0: state["player_dot"]=0
        if state.get("delayed_damage",0)>0:
            delayed=state["delayed_damage"]; state["enemy_hp"]=max(1,state["enemy_hp"]-min(delayed,max(2,int(state["enemy"]["hp"]*.35)))); state["delayed_damage"]=0; state["log"].append(f"⏳ The delayed strike detonated for **{delayed}** damage.")
        enemy_status=state.get("enemy_statuses",{})
        if "stun" in enemy_status or "freeze" in enemy_status:
            state["log"].append(f"💫 **{state['enemy']['name']}** is unable to act because of a status effect.")
        elif state["enemy_hp"]<=0 or state["player_hp"]<=0:
            pass
        else:
            ability_logs=self._enemy_ability_action(state,stats)
            if ability_logs: state["log"].extend(ability_logs)
            elif not defending and random.random()<min(.30,float(state["enemy"].get("speed",5))/220 + float(state.get("buffs",{}).get("evasion",0))):
                state["log"].append(f"💨 You dodged **{state['enemy']['name']}**.")
            else:
                def_up=float(state.get("buffs",{}).get("def_up",0)); effective_def=stats["defense"]*(1+def_up); effective_def*=max(.50,1-float(state.get("player_debuff_def",0)))
                enemy_atk=float(state["enemy"]["atk"])*(1+float(state.get("enemy_atk_up",0)))
                if "weaken" in enemy_status or "silence" in enemy_status: enemy_atk*=.82
                if state["enemy"].get("is_boss") and state["enemy_hp"]<state["enemy"].get("hp",1)*.25: enemy_atk*=1.18
                dmg=self._damage(enemy_atk,effective_def,.90,ENEMY_DAMAGE_VARIANCE); dmg,crit=self._crit_damage(dmg,int(state["enemy"].get("crit",0)))
                reduction=float(stats.get("trait_damage_reduction",0))
                if state["player_hp"]<=stats["max_hp"]*.5: reduction+=float(stats.get("trait_low_hp_reduction",0))
                if crit: reduction+=float(stats.get("trait_crit_damage_reduction",0))
                if defending: reduction+=float(stats.get("trait_defend_reduction",0))
                if state["player_hp"]>stats["max_hp"]*.70:
                    reduction+=float(stats.get("trait_high_hp_reduction",0))
                dmg=min(dmg,max(2,int(stats["max_hp"]*MAX_NORMAL_DAMAGE_FRACTION)))
                dmg=max(1,int(dmg*(1-min(45,reduction)/100)))
                if stats.get("trait_reflect") and state.get("shield_turns",0)>0:
                    state["enemy_hp"]=max(0,state["enemy_hp"]-max(1,int(dmg*stats["trait_reflect"]/100)))
                shield=state.get("shield_pct",.5) if (defending or state.get("shield_turns",0)>0) else 0
                if shield:dmg=max(1,int(dmg*(1-shield)))
                state["player_hp"]-=dmg; state["log"].append(f"🩸 **{state['enemy']['name']}** hit you for **{dmg}**{' CRITICAL' if crit else ''}.")
        for enemy_key in list(state.get("enemy_ability_cooldowns",{})): state["enemy_ability_cooldowns"][enemy_key]=max(0,int(state["enemy_ability_cooldowns"][enemy_key])-1)
        for key2 in ("enemy_guard_turns","enemy_atk_turns","player_debuff_def_turns"):
            if key2 in state:
                state[key2]-=1
                if state[key2]<=0:
                    state.pop(key2,None)
                    if key2=="enemy_guard_turns": state["enemy_guard_pct"]=0
                    elif key2=="enemy_atk_turns": state["enemy_atk_up"]=0
                    elif key2=="player_debuff_def_turns": state["player_debuff_def"]=0
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
        for _status_key,_status_data in list(state.get("enemy_statuses",{}).items()):
            # Tick durations after the enemy has had its turn. Damage statuses were already processed above.
            if _status_key in {"stun","freeze","silence","slow","vulnerable","weaken"}:
                _status_data["turns"]=int(_status_data.get("turns",0))-1
                if _status_data["turns"]<=0: state["enemy_statuses"].pop(_status_key,None)
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
            state["player_hp"]=1; await self._set_hp(guild_id,user_id,1); self.active_combats.pop(key,None); await self._delete_combat_session(guild_id,user_id)
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
        if (guild_id,user_id) in self.active_combats:
            await self._persist_combat_session(guild_id,user_id,state)

    async def _set_hp(self,guild_id,user_id,hp):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET hp=? WHERE guild_id=? AND user_id=?",(max(1,int(hp)),guild_id,user_id)); await db.commit()

    async def _apply_recovery(self,guild_id,user_id,heal,mana):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET hp=min(max_hp,hp+?),mp=min(max_mp,mp+?) WHERE guild_id=? AND user_id=?",(heal,mana,guild_id,user_id)); await db.commit()

    async def travel(self,guild_id,user_id,area_key):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        area_key=area_key.lower().strip(); area=AREAS.get(area_key)
        if not area:return False,"Unknown area. Use `!rpg areas`."
        if p["level"]<int(area["level"]):return False,f"That area requires level **{area['level']}**."
        current=p.get("area_key","horizon_village") or "horizon_village"
        if area_key!=current:
            async with aiosqlite.connect(self.path) as db:
                cur=await db.execute("SELECT 1 FROM rpg_area_discoveries WHERE guild_id=? AND user_id=? AND area_key=?",(guild_id,user_id,area_key)); discovered=await cur.fetchone()
            adjacent=area_key in AREA_CONNECTIONS.get(current,[])
            if not discovered and not adjacent:
                return False,f"You cannot travel directly from **{AREAS.get(current,{'name':current})['name']}** to **{area['name']}**. Discover an adjacent route first with `!rpg explore`."
        distance_level=max(0,int(area["level"])-int(AREAS.get(current,area).get("level",1)))
        stamina_cost=min(20,5+distance_level//5) if area_key!=current else 0
        if stamina_cost and int(p.get("stamina",0))<stamina_cost:return False,f"You need **{stamina_cost} stamina** to travel there. Use `!rpg rest`."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET area_key=?,location=?,stamina=max(0,stamina-?) WHERE guild_id=? AND user_id=?",(area_key,area["name"],stamina_cost,guild_id,user_id))
            await db.execute("INSERT OR IGNORE INTO rpg_area_discoveries(guild_id,user_id,area_key,discovered_at,source) VALUES(?,?,?,?,?)",(guild_id,user_id,area_key,time.time(),"travel")); await db.commit()
        await self.progress_quests(guild_id,user_id,"explore",1)
        cost_text=f" • −{stamina_cost} stamina" if stamina_cost else ""
        return True,f"🧭 You traveled to **{area['name']}**.{cost_text}\n{area['desc']}"

    async def egg_hatch(self,guild_id,user_id,egg_key,name="Spirit"):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        egg_key=egg_key.lower().strip(); data=ITEMS.get(egg_key)
        if not data or data.get("slot")!="egg":return False,"That isn't a pet egg. Use `!rpg eggs` to see your eggs."
        pool=PET_EGG_POOLS.get(egg_key, [])
        if not pool:return False,"That egg has no configured pet pool."
        species=random.choice(pool)
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
            await db.execute("UPDATE rpg_players SET gold=gold-50000,kingdom_name=?,kingdom_role=?,title='King',renown=renown+100 WHERE guild_id=? AND user_id=?",(name,"king",guild_id,user_id)); await db.commit()
        return True,f"**{name}** has been founded. You are its **King**."

    async def kingdom_join(self,guild_id,user_id,name):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT name FROM rpg_kingdoms WHERE guild_id=? AND lower(name)=lower(?)",(guild_id,name)); row=await cur.fetchone()
            if not row:return False,"Kingdom not found."
            await db.execute("DELETE FROM rpg_kingdom_members WHERE guild_id=? AND user_id=?",(guild_id,user_id))
            await db.execute("INSERT INTO rpg_kingdom_members VALUES(?,?,?,?,?)",(guild_id,row[0],user_id,"citizen",time.time()))
            await db.execute("UPDATE rpg_players SET kingdom_name=?,kingdom_role='citizen' WHERE guild_id=? AND user_id=?",(row[0],guild_id,user_id)); await db.commit()
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

    async def bounty_post(self,guild_id,user_id,target_name,reward,target_id=0):
        if reward<100:return False,"Bounties must be at least 100 gold."
        p=await self.player(guild_id,user_id)
        if not p or p["gold"]<reward:return False,"You don't have enough gold."
        if int(target_id or 0)==int(user_id):return False,"You can't place a bounty on yourself."
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_players SET gold=gold-? WHERE guild_id=? AND user_id=?",(reward,guild_id,user_id))
            await db.execute("INSERT INTO rpg_bounties(guild_id,poster_id,target_name,target_id,reward,created_at) VALUES(?,?,?,?,?,?)",(guild_id,user_id,target_name[:64],int(target_id or 0),reward,time.time())); await db.commit()
        target_note=f" on <@{target_id}>" if target_id else f" on **{target_name}**"
        return True,f"Bounty posted{target_note} for **{reward} gold**. Use `!rpg bounty claim <id>` when the target is defeated/eligible."

    async def bounties(self,guild_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT id,target_name,reward,poster_id,status,target_id FROM rpg_bounties WHERE guild_id=? AND status='open' ORDER BY reward DESC LIMIT 20",(guild_id,)); return await cur.fetchall()

    async def bounty_claim(self,guild_id,user_id,bounty_id):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT id,target_name,target_id,reward,poster_id,status FROM rpg_bounties WHERE guild_id=? AND id=?",(guild_id,bounty_id)); row=await cur.fetchone()
            if not row:return False,"Bounty not found."
            bid,target_name,target_id,reward,poster_id,status=row
            if status!="open":return False,"That bounty has already been claimed or closed."
            if int(poster_id)==int(user_id):return False,"You cannot claim your own bounty."
            target_id=int(target_id or 0)
            if target_id and target_id==int(user_id):
                return False,"You are the target of this bounty, so you cannot claim it yourself."
            # A claim closes the bounty and pays the hunter. Member-targeted
            # bounties are safer because the target is recorded explicitly; the
            # actual defeat can be verified by the server's PvP/event rules.
            await db.execute("UPDATE rpg_bounties SET status='claimed' WHERE id=? AND status='open'",(bid,))
            await db.execute("UPDATE rpg_players SET gold=gold+? WHERE guild_id=? AND user_id=?",(reward,guild_id,user_id))
            await db.commit()
        return True,f"🎯 Bounty **#{bid}** claimed for **+{reward} gold** against **{target_name}**."

    # ------------------------------------------------------------------
    # Phase 5 — PvP Arenas / Seasons
    # ------------------------------------------------------------------
    async def _ensure_pvp_season(self, guild_id):
        now = time.time(); period = 30 * 86400
        season_number = int(now // period) + 1
        started = (season_number - 1) * period; ends = season_number * period
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_pvp_seasons SET status='ended' WHERE guild_id=? AND status='active' AND season_number<?", (guild_id, season_number))
            await db.execute("INSERT OR IGNORE INTO rpg_pvp_seasons(guild_id,season_number,name,started_at,ends_at,status) VALUES(?,?,?,?,?,'active')", (guild_id,season_number,f"Arena Season {season_number}",started,ends))
            cur=await db.execute("SELECT id,season_number,name,started_at,ends_at FROM rpg_pvp_seasons WHERE guild_id=? AND season_number=?",(guild_id,season_number)); row=await cur.fetchone()
            await db.commit()
        return row

    async def arena_rating(self, guild_id, user_id):
        season=await self._ensure_pvp_season(guild_id)
        sid=season[0]
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT OR IGNORE INTO rpg_pvp_ratings(guild_id,season_id,user_id) VALUES(?,?,?)",(guild_id,sid,user_id))
            cur=await db.execute("SELECT rating,wins,losses,streak,best_rating FROM rpg_pvp_ratings WHERE guild_id=? AND season_id=? AND user_id=?",(guild_id,sid,user_id)); row=await cur.fetchone(); await db.commit()
        return {"season":season,"rating":row[0],"wins":row[1],"losses":row[2],"streak":row[3],"best":row[4]}

    async def arena_ratings(self, guild_id, limit=50):
        season=await self._ensure_pvp_season(guild_id); sid=season[0]
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT user_id,rating,wins,losses,streak,best_rating FROM rpg_pvp_ratings WHERE guild_id=? AND season_id=? ORDER BY rating DESC,wins DESC LIMIT ?",(guild_id,sid,limit)); rows=await cur.fetchall()
        return season,rows

    async def start_arena(self, guild_id, user_id, target_id):
        result=await self.start_duel(guild_id,user_id,target_id)
        if "error" in result: return result
        season=await self._ensure_pvp_season(guild_id)
        result["state"]["arena"]=True; result["state"]["season_id"]=season[0]
        await self.arena_rating(guild_id,user_id); await self.arena_rating(guild_id,target_id)
        return result

    async def _record_arena_result(self, guild_id, season_id, winner_id, loser_id, key):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT OR IGNORE INTO rpg_pvp_ratings(guild_id,season_id,user_id) VALUES(?,?,?)",(guild_id,season_id,winner_id))
            await db.execute("INSERT OR IGNORE INTO rpg_pvp_ratings(guild_id,season_id,user_id) VALUES(?,?,?)",(guild_id,season_id,loser_id))
            cur=await db.execute("SELECT user_id,rating,streak FROM rpg_pvp_ratings WHERE guild_id=? AND season_id=? AND user_id IN (?,?)",(guild_id,season_id,winner_id,loser_id)); rows=await cur.fetchall(); data={r[0]:r for r in rows}
            wr=data[winner_id][1]; lr=data[loser_id][1]
            expected=1/(1+10**((lr-wr)/400)); delta=max(8,min(32,round(32*(1-expected))))
            await db.execute("UPDATE rpg_pvp_ratings SET rating=rating+?,wins=wins+1,streak=streak+1,best_rating=MAX(best_rating,rating+?) WHERE guild_id=? AND season_id=? AND user_id=?",(delta,delta,guild_id,season_id,winner_id))
            await db.execute("UPDATE rpg_pvp_ratings SET rating=MAX(0,rating-?),losses=losses+1,streak=0 WHERE guild_id=? AND season_id=? AND user_id=?",(delta,guild_id,season_id,loser_id))
            await db.execute("INSERT INTO rpg_arena_matches(guild_id,season_id,player_a,player_b,winner_id,rating_delta_a,rating_delta_b,created_at) VALUES(?,?,?,?,?,?,?,?)",(guild_id,season_id,key[1],key[2],winner_id,delta if key[1]==winner_id else -delta,delta if key[2]==winner_id else -delta,time.time()))
            await db.commit()
        return delta

    # ------------------------------------------------------------------
    # Phase 5 — Server Raid Bosses
    # ------------------------------------------------------------------
    async def _ensure_raid(self, guild_id):
        now=time.time(); week=time.strftime("%Y-W%W",time.gmtime(now))
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT id,raid_key,name,description,level,max_hp,hp,status,started_at,expires_at FROM rpg_raid_bosses WHERE guild_id=? AND weekly_key=?",(guild_id,week)); row=await cur.fetchone()
            if row and row[7] in {"active","defeated"} and row[9]>now:return row
            level=60; max_hp=150000
            await db.execute("INSERT OR IGNORE INTO rpg_raid_bosses(guild_id,raid_key,name,description,level,max_hp,hp,status,started_at,expires_at,weekly_key) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(guild_id,"elder_abyss_dragon","Elder Abyss Dragon","A server-wide raid boss. Every hero contributes to the same health pool.",level,max_hp,max_hp,"active",now,now+7*86400,week))
            cur=await db.execute("SELECT id,raid_key,name,description,level,max_hp,hp,status,started_at,expires_at FROM rpg_raid_bosses WHERE guild_id=? AND weekly_key=?",(guild_id,week)); row=await cur.fetchone(); await db.commit()
        return row

    async def raid_info(self,guild_id):
        return await self._ensure_raid(guild_id)

    async def raid_leaderboard(self,guild_id,limit=10):
        raid=await self._ensure_raid(guild_id)
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT user_id,damage,attacks,claimed FROM rpg_raid_damage WHERE raid_id=? ORDER BY damage DESC LIMIT ?",(raid[0],limit)); rows=await cur.fetchall()
        return raid,rows

    async def raid_attack(self,guild_id,user_id):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        raid=await self._ensure_raid(guild_id); now=time.time()
        if raid[7]!="active":return False,"This raid is already defeated. A new weekly raid will appear next cycle."
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT last_attack FROM rpg_raid_damage WHERE raid_id=? AND user_id=?",(raid[0],user_id)); row=await cur.fetchone(); last=row[0] if row else 0
            if now-last<20:return False,f"Your raid attack is on cooldown for **{int(20-(now-last))}s**."
        combat=await self._combat_full_stats(guild_id,user_id,p)
        if not combat:return False,"Create a hero first."
        base=max(10,int(combat["atk"]*random.uniform(1.6,2.3)))
        # Endgame builds and secret classes get a modest raid specialization.
        if p.get("class_name") in SECRET_CLASS_KEYS: base=int(base*1.18)
        damage=max(10,base)
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO rpg_raid_damage(raid_id,guild_id,user_id,damage,attacks,last_attack) VALUES(?,?,?,?,?,?) ON CONFLICT(raid_id,user_id) DO UPDATE SET damage=damage+excluded.damage,attacks=attacks+1,last_attack=excluded.last_attack",(raid[0],guild_id,user_id,damage,1,now))
            await db.execute("UPDATE rpg_raid_bosses SET hp=MAX(0,hp-?) WHERE id=? AND status='active'",(damage,raid[0]))
            cur=await db.execute("SELECT hp FROM rpg_raid_bosses WHERE id=?",(raid[0],)); hp=(await cur.fetchone())[0]
            defeated=hp<=0
            if defeated: await db.execute("UPDATE rpg_raid_bosses SET status='defeated',hp=0 WHERE id=?",(raid[0],))
            await db.commit()
        if defeated:
            async with aiosqlite.connect(self.path) as db:
                cur=await db.execute("SELECT user_id,damage,claimed FROM rpg_raid_damage WHERE raid_id=?",(raid[0],)); participants=await cur.fetchall()
            # Pay outside the participant read connection to avoid SQLite lock contention.
            for uid,personal_damage,claimed in participants:
                if not claimed:
                    reward_xp=2500+min(10000,personal_damage//20); reward_gold=2000+min(10000,personal_damage//40)
                    await self.add_rewards(guild_id,uid,reward_xp,reward_gold)
                    if personal_damage>=10000: await self.add_item(guild_id,uid,"dragon_trophy",2,event_type="raid_reward")
                    async with aiosqlite.connect(self.path) as db:
                        await db.execute("UPDATE rpg_raid_damage SET claimed=1 WHERE raid_id=? AND user_id=?",(raid[0],uid)); await db.commit()
            return True,f"💥 **{damage:,}** damage! **{raid[2]}** has been defeated. All contributors received raid rewards; high contributors earned bonus trophies."
        return True,f"⚔️ You dealt **{damage:,}** damage to **{raid[2]}**. Remaining HP: **{hp:,}/{raid[5]:,}**."

    # ------------------------------------------------------------------
    # Phase 5 — Secret Classes
    # ------------------------------------------------------------------
    async def secret_class_list(self,guild_id,user_id):
        p=await self.player(guild_id,user_id)
        if not p:return []
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT class_key FROM rpg_secret_class_unlocks WHERE guild_id=? AND user_id=?",(guild_id,user_id)); unlocked={r[0] for r in await cur.fetchall()}
        result=[]
        for key,data in SECRET_CLASSES.items():
            result.append((key,data,key in unlocked))
        return result

    async def _secret_requirements(self,guild_id,user_id,key):
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        if key not in SECRET_CLASSES:return False,"Unknown secret class."
        data=SECRET_CLASSES[key]
        if p["level"]<data["req_level"]:return False,f"Requires level **{data['req_level']}**."
        if data.get("req_renown",0) and p.get("renown",0)<data["req_renown"]:return False,f"Requires **{data['req_renown']} Renown**."
        if data.get("req_pvp_wins",0):
            season=await self._ensure_pvp_season(guild_id)
            async with aiosqlite.connect(self.path) as db:
                cur=await db.execute("SELECT COALESCE(SUM(wins),0) FROM rpg_pvp_ratings WHERE guild_id=? AND user_id=?",(guild_id,user_id)); wins=(await cur.fetchone())[0]
            if wins<data["req_pvp_wins"]:return False,f"Requires **{data['req_pvp_wins']} Arena wins**; you have **{wins}**."
        if data.get("req_raid_damage",0):
            async with aiosqlite.connect(self.path) as db:
                cur=await db.execute("SELECT COALESCE(SUM(damage),0) FROM rpg_raid_damage WHERE guild_id=? AND user_id=?",(guild_id,user_id)); damage=(await cur.fetchone())[0]
            if damage<data["req_raid_damage"]:return False,f"Requires **{data['req_raid_damage']:,} total Raid damage**; you have **{damage:,}**."
        return True,"Requirements met."

    async def awaken_secret_class(self,guild_id,user_id,key):
        key=key.lower().strip(); ok,msg=await self._secret_requirements(guild_id,user_id,key)
        if not ok:return False,msg
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT 1 FROM rpg_secret_class_unlocks WHERE guild_id=? AND user_id=? AND class_key=?",(guild_id,user_id,key))
            if await cur.fetchone():return False,"You have already awakened this secret class."
            await db.execute("INSERT INTO rpg_secret_class_unlocks(guild_id,user_id,class_key,unlocked_at) VALUES(?,?,?,?)",(guild_id,user_id,key,time.time()))
            data=SECRET_CLASSES[key]; s=self._class_stats((await self.player(guild_id,user_id))["race"],key)
            await db.execute("UPDATE rpg_players SET class_name=?,max_hp=?,hp=?,max_mp=?,mp=?,atk=?,defense=?,speed=?,crit=?,subclass='' WHERE guild_id=? AND user_id=?",(key,s["max_hp"],s["max_hp"],s["max_mp"],s["max_mp"],s["atk"],s["defense"],s["speed"],s["crit"],guild_id,user_id)); await db.commit()
        return True,f"🌌 You awakened **{data['name']}**. Your class has been transformed into a Phase 5 secret class."

    # ------------------------------------------------------------------
    # Phase 5 — Legendary Endgame
    # ------------------------------------------------------------------
    async def legendary_list(self,guild_id,user_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT challenge_key,completed,completions,last_completed FROM rpg_legendary_challenges WHERE guild_id=? AND user_id=?",(guild_id,user_id)); rows={r[0]:r for r in await cur.fetchall()}
        return [(key,data,rows.get(key,(key,0,0,0))) for key,data in LEGENDARY_CHALLENGES.items()]

    async def legendary_challenge(self,guild_id,user_id,key):
        p=await self.player(guild_id,user_id); key=key.lower().strip()
        if not p:return False,"Create a hero first."
        boss=LEGENDARY_CHALLENGES.get(key)
        if not boss:return False,"Unknown legendary challenge. Use `!rpg legendary` to see the trials."
        if p["level"]<boss["level"]:return False,f"Requires level **{boss['level']}**."
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT completed,last_completed FROM rpg_legendary_challenges WHERE guild_id=? AND user_id=? AND challenge_key=?",(guild_id,user_id,key)); row=await cur.fetchone()
        if row and row[1] and time.time()-row[1]<86400:return False,"That legendary trial can be challenged once every **24 hours**."
        combat=await self._combat_full_stats(guild_id,user_id,p)
        if not combat:return False,"Create a hero first."
        power=combat["atk"]*2.0+combat["defense"]*1.5+combat["speed"]*1.2+combat["max_hp"]*.25+combat.get("crit",0)*4
        boss_power=boss["atk"]*1.8+boss["def"]*1.4+boss["hp"]*.06
        chance=max(.08,min(.92,power/max(1,boss_power)))
        # Three-round simulation prevents a single lucky random roll from deciding the entire trial.
        score=0
        for _ in range(3): score += power*random.uniform(.82,1.18)
        success=score >= boss_power*2.15 or random.random()<chance*.35
        if not success:
            await self.add_rewards(guild_id,user_id,boss["xp"]//5,boss["gold"]//5)
            return False,f"**{boss['name']}** defeated the attempt. You earned a consolation reward, but the legendary trial remains incomplete."
        await self.add_rewards(guild_id,user_id,boss["xp"],boss["gold"])
        await self.add_item(guild_id,user_id,boss["reward"],1,event_type="legendary_reward",metadata={"challenge":key})
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO rpg_legendary_challenges(guild_id,user_id,challenge_key,completed,completions,last_completed) VALUES(?,?,?,?,?,?) ON CONFLICT(guild_id,user_id,challenge_key) DO UPDATE SET completed=1,completions=completions+1,last_completed=excluded.last_completed",(guild_id,user_id,key,1,1,time.time())); await db.commit()
        return True,f"👑 **Legendary Trial Cleared:** {boss['name']}\nRewards: **+{boss['xp']:,} XP**, **+{boss['gold']:,} Gold**, and **{ITEMS[boss['reward']]['name']}**."

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
            skill_key=action.split(":",1)[1].strip(); skill=self._skill(me["class"],skill_key,me.get("subclass",""))
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
                    mult*=1+float(me["stats"].get("skill_pct",0))/100
                    if effect in {"heavy","ultimate","execute","mythic","signature"}:
                        mult*=1.15+float(me["stats"].get("finisher_pct",0))/100
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
        # Completing a player-targeted bounty through PvP immediately pays the
        # hunter. The separate `bounty claim` command remains available for
        # text/name bounties and manually verified events.
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT id FROM rpg_bounties WHERE guild_id=? AND target_id=? AND status='open' ORDER BY reward DESC",(guild_id,loser_id))
            bounty_ids=[int(r[0]) for r in await cur.fetchall()]
        for bounty_id in bounty_ids:
            await self.bounty_claim(guild_id,winner_id,bounty_id)
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
        if state.get("arena"):
            try:
                delta=await self._record_arena_result(guild_id,state.get("season_id"),winner_id,loser_id,key)
                await self.add_rewards(guild_id,winner_id,300,450)
                await self.add_rewards(guild_id,loser_id,100,150)
                state["arena_rating_delta"]=delta
            except Exception:
                pass
        return {"finished":True,"state":state,"winner":winner_id,"loser":loser_id}




    async def _seed_factions(self, guild_id):
        factions = [
            ("horizon_guard", "Horizon Guard", "Protectors of roads, settlements and adventurers.", "order"),
            ("free_merchants", "Free Merchants", "Traders who value open routes, markets and independent commerce.", "commerce"),
            ("arcane_circle", "Arcane Circle", "Scholars who pursue magic and relics.", "knowledge"),
            ("wildbound", "Wildbound", "Explorers and wardens who defend the wilderness.", "nature"),
        ]
        async with aiosqlite.connect(self.path) as db:
            for key, name, desc, ideology in factions:
                await db.execute(
                    "INSERT OR IGNORE INTO rpg_factions(guild_id,faction_key,name,description,ideology) VALUES(?,?,?,?,?)",
                    (guild_id, key, name, desc, ideology),
                )
            await db.commit()

    async def quest_journal(self, guild_id, user_id):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "SELECT status,COUNT(*) FROM rpg_player_quests WHERE guild_id=? AND user_id=? GROUP BY status",
                (guild_id, user_id),
            )
            counts = {r[0]: r[1] for r in await cur.fetchall()}
        return counts, []

    async def factions(self, guild_id):
        await self._seed_factions(guild_id)
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT faction_key,name,description,ideology FROM rpg_factions WHERE guild_id=? ORDER BY name", (guild_id,))
            return await cur.fetchall()

    async def faction_status(self, guild_id, user_id):
        await self._seed_factions(guild_id)
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT faction_key,reputation,rank,joined_at FROM rpg_faction_members WHERE guild_id=? AND user_id=?", (guild_id, user_id))
            return await cur.fetchone()

    async def faction_join(self, guild_id, user_id, faction_key):
        key = str(faction_key).lower().strip()
        faction_rows = await self.factions(guild_id)
        factions = {r[0]: r for r in faction_rows}
        if key not in factions:
            return False, "Choose a faction key from `!rpg factions`."
        existing = await self.faction_status(guild_id, user_id)
        if existing and existing[0] != key:
            current = factions.get(existing[0], (existing[0], existing[0]))
            return False, f"You already serve **{current[1]}**. Leave your faction before changing allegiance."
        if existing:
            return False, "You are already a member of that faction."
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO rpg_faction_members(guild_id,user_id,faction_key,reputation,rank,joined_at) VALUES(?,?,?,?,?,?)",
                (guild_id, user_id, key, 0, "outsider", time.time()),
            )
            await db.commit()
        return True, f"You joined **{factions[key][1]}**. Your faction reputation starts at **0**."

    async def endgame_status(self, guild_id, user_id):
        p = await self.player(guild_id, user_id)
        if not p:
            return None
        arena = await self.arena_rating(guild_id, user_id)
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT COUNT(*) FROM rpg_legendary_challenges WHERE guild_id=? AND user_id=? AND completed=1", (guild_id, user_id))
            legendary = (await cur.fetchone())[0]
            cur = await db.execute("SELECT COUNT(*) FROM rpg_secret_class_unlocks WHERE guild_id=? AND user_id=?", (guild_id, user_id))
            secrets = (await cur.fetchone())[0]
            cur = await db.execute("SELECT COALESCE(SUM(damage),0) FROM rpg_raid_damage WHERE guild_id=? AND user_id=?", (guild_id, user_id))
            raid_damage = (await cur.fetchone())[0]
            mastery = legendary * 10 + secrets * 15 + int(raid_damage // 10000) + int(arena.get("rating", 1000) // 100)
            cur = await db.execute("SELECT ascension FROM rpg_endgame_progress WHERE guild_id=? AND user_id=?", (guild_id, user_id))
            row = await cur.fetchone()
            ascension = row[0] if row else 0
            await db.execute(
                "INSERT INTO rpg_endgame_progress(guild_id,user_id,mastery,ascension,milestones_json,updated_at) VALUES(?,?,?,?,?,?) "
                "ON CONFLICT(guild_id,user_id) DO UPDATE SET mastery=excluded.mastery,milestones_json=excluded.milestones_json,updated_at=excluded.updated_at",
                (guild_id, user_id, mastery, ascension, json.dumps({"legendary": legendary, "secret_classes": secrets, "raid_damage": raid_damage}), time.time()),
            )
            await db.commit()
        return {"level": p["level"], "arena": arena, "legendary": legendary, "secret_classes": secrets, "raid_damage": raid_damage, "mastery": mastery, "ascension": ascension}


    async def endgame_ascend(self, guild_id, user_id):
        status = await self.endgame_status(guild_id, user_id)
        if not status:
            return False, "Create a hero first."
        if status["level"] < 80:
            return False, "Ascension unlocks at level **80**."
        if status["mastery"] < 100:
            return False, "You need **100 Endgame Mastery** before Ascension."
        async with aiosqlite.connect(self.path) as db:
            if status["ascension"] >= 5:
                return False, "You have reached the current Ascension cap."
            new_level = status["ascension"] + 1
            await db.execute("UPDATE rpg_endgame_progress SET ascension=?,updated_at=? WHERE guild_id=? AND user_id=?", (new_level, time.time(), guild_id, user_id))
            await db.execute("UPDATE rpg_players SET renown=renown+500,fame=fame+250 WHERE guild_id=? AND user_id=?", (guild_id, user_id))
            await db.commit()
        return True, f"**Ascension {new_level}** achieved. You gained **+500 Renown** and **+250 Fame**."