from __future__ import annotations

import random
import time
from dataclasses import dataclass
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
            """)
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
            while p[1] >= self._level_xp(new_level): new_level += 1
            if new_level != old_level:
                await db.execute("UPDATE rpg_players SET level=?,skill_points=skill_points+? WHERE guild_id=? AND user_id=?", (new_level,new_level-old_level,guild_id,user_id))
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

    async def stats(self,guild_id,user_id):
        p=await self.player(guild_id,user_id)
        if not p:return None
        gear={}
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT slot,item_key FROM rpg_equipment WHERE guild_id=? AND user_id=?",(guild_id,user_id)); gear=dict(await cur.fetchall())
        bonus={"atk":0,"defense":0,"hp":0,"mp":0,"speed":0,"crit":0}
        for key in gear.values():
            item=ITEMS.get(key,{})
            bonus["atk"]+=item.get("atk",0); bonus["defense"]+=item.get("def",0); bonus["hp"]+=item.get("hp",0); bonus["mp"]+=item.get("mp",0); bonus["speed"]+=item.get("spd",0); bonus["crit"]+=item.get("crit",0)
        return p,gear,bonus

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
        return [(k,v) for k,v in ITEMS.items() if v.get("price") and v["slot"] in {"weapon","armor","offhand","consumable"}]

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
