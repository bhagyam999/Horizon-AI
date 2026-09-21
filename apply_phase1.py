from pathlib import Path
p=Path('/mnt/data/phase1')
rpg=p/'rpg.py'; bot=p/'bot.py'
s=rpg.read_text(); b=bot.read_text()

# 1) Expand dungeon catalog and add map/boss/objective data.
old='''DUNGEONS = [\n    ("Goblin Caves", 1, 3, 140, 90, "A beginner dungeon with three floors."),\n    ("Moonlit Ruins", 5, 4, 360, 240, "Ancient ruins filled with arcane enemies."),\n    ("Dragonspire", 10, 5, 800, 550, "A dangerous tower ending in a dragon boss."),\n]\n'''
new='''DUNGEONS = [\n    ("Goblin Caves", 1, 3, 140, 90, "A beginner dungeon with three floors."),\n    ("Moonlit Ruins", 5, 4, 360, 240, "Ancient ruins filled with arcane enemies."),\n    ("Dragonspire", 10, 5, 800, 550, "A dangerous tower ending in a dragon boss."),\n    ("Sunken Catacombs", 15, 5, 1250, 850, "Flooded burial halls where drowned kings still rule."),\n    ("Obsidian Bastion", 23, 6, 1900, 1300, "A fortress defended by cursed knights and war machines."),\n    ("Ashen Caldera", 28, 6, 2700, 1850, "A volcanic dungeon where every chamber burns."),\n    ("Crystal Labyrinth", 34, 7, 3900, 2500, "A shifting maze of living crystal and mirrored beasts."),\n    ("Thunder Sanctum", 40, 7, 5200, 3400, "A storm temple whose guardians wield living lightning."),\n    ("Void Threshold", 46, 8, 7000, 4600, "A broken reality where monsters phase between worlds."),\n    ("Dragon Grave", 52, 8, 9000, 6000, "The bones of dead dragons hide an ancient sovereign."),\n    ("Eternal Library", 58, 9, 11500, 7600, "Living spells guard forbidden knowledge."),\n    ("Time Ruins", 64, 9, 14500, 9500, "Every floor exists in a different moment."),\n    ("Godfall Citadel", 70, 10, 18000, 12000, "A fallen divine fortress inhabited by exiled powers."),\n    ("Endless Night", 78, 10, 23000, 15500, "A lightless labyrinth where sound attracts predators."),\n    ("Reality's Edge", 86, 11, 29000, 19500, "The world fractures more deeply with every floor."),\n    ("Origin Sanctum", 94, 12, 37000, 25000, "A primordial dungeon said to predate Horizon itself."),\n    ("Horizon Core", 100, 12, 50000, 35000, "The ultimate dungeon at the heart of the world."),\n]\n\nDUNGEON_BOSSES = {\n    "Goblin Caves": "Goblin Warchief Grakk", "Moonlit Ruins": "The Moonbound Archivist",\n    "Dragonspire": "Veyrath, the Young Dragon", "Sunken Catacombs": "Drowned King Marrow",\n    "Obsidian Bastion": "General Blacksteel", "Ashen Caldera": "Cindermaw, Lord of Ash",\n    "Crystal Labyrinth": "Prismatic Hydra", "Thunder Sanctum": "Raijin's Last Disciple",\n    "Void Threshold": "The Reality Eater", "Dragon Grave": "Elder Wyrm Ossuary",\n    "Eternal Library": "The Living Grimoire", "Time Ruins": "Chronarch Zero",\n    "Godfall Citadel": "The Fallen God-King", "Endless Night": "Nocturne, Eater of Light",\n    "Reality's Edge": "The Boundary Walker", "Origin Sanctum": "The First Guardian",\n    "Horizon Core": "HORIZON, Worldheart Sovereign",\n}\n\n# A readable world graph. Travel remains backward-compatible (players can still\n# travel to any level-eligible region), while the graph powers the map/exploration\n# systems and shows the natural route between regions.\nAREA_CONNECTIONS = {}\n_area_order = sorted(AREAS.items(), key=lambda kv: (int(kv[1].get("level", 1)), kv[0]))\nfor _i, (_key, _data) in enumerate(_area_order):\n    AREA_CONNECTIONS.setdefault(_key, set())\n    if _i > 0:\n        AREA_CONNECTIONS[_key].add(_area_order[_i-1][0])\n        AREA_CONNECTIONS[_area_order[_i-1][0]].add(_key)\n# Important regional shortcuts make the graph feel like a world rather than a line.\nfor _a, _c in [\n    ("horizon_village", "whispering_woods"), ("whispering_woods", "mossy_grotto"),\n    ("silver_coast", "pirate_isles"), ("frostpeak", "frostwood"),\n    ("sunken_ruins", "forgotten_catacombs"), ("skyreach", "floating_gardens"),\n    ("demon_wastes", "inferno_gate"), ("crystal_desert", "glass_dunes"),\n    ("astral_frontier", "dreaming_sea"), ("world_tree", "worldroot_caves"),\n    ("dragon_graveyard", "dragon_grave" if "dragon_grave" in AREAS else "dragon_graveyard"),\n    ("horizon_core", "origin_sanctum"),\n]:\n    if _a in AREAS and _c in AREAS:\n        AREA_CONNECTIONS.setdefault(_a, set()).add(_c); AREA_CONNECTIONS.setdefault(_c, set()).add(_a)\nAREA_CONNECTIONS = {k: sorted(v) for k, v in AREA_CONNECTIONS.items()}\n\nWORLD_BOSS_TEMPLATES = [\n    ("abyssal_tyrant", "Abyssal Tyrant", "void_border", 70, "A colossal creature that emerged from a crack in reality."),\n    ("elder_dragon", "Elder Dragon Avarax", "dragon_graveyard", 80, "An ancient dragon awakened by the bones of its kin."),\n    ("fallen_seraph", "Fallen Seraph Elyra", "godfall", 90, "A divine exile whose wings still burn with corrupted light."),\n    ("worldroot_colossus", "Worldroot Colossus", "worldroot_caves", 100, "A living mountain born from the roots of the World Tree."),\n]\n\nOBJECTIVE_TEMPLATES = {\n    "daily": [\n        ("daily_hunt", "Monster Hunter", "Defeat enemies", "hunt", 5, 220, 350, "wolf_pelt", 2),\n        ("daily_explore", "Pathfinder", "Explore or travel through the world", "explore", 2, 180, 280, "herb", 3),\n        ("daily_dungeon", "Dungeon Runner", "Clear dungeon floors", "dungeon", 2, 300, 450, "arcane_shard", 2),\n        ("daily_gather", "Field Collector", "Gather resources", "gather", 4, 180, 300, "mat_blue_herb", 2),\n    ],\n    "weekly": [\n        ("weekly_hunt", "Monster Exterminator", "Defeat enemies", "hunt", 30, 1600, 2400, "arcane_shard", 8),\n        ("weekly_dungeon", "Dungeon Delver", "Clear dungeon floors", "dungeon", 12, 2200, 3400, "dragon_trophy", 2),\n        ("weekly_boss", "World Challenger", "Deal damage to a world boss", "worldboss", 1, 2500, 4000, "mat_void_crystal", 5),\n    ],\n}\n'''
if old not in s: raise SystemExit('DUNGEONS block not found')
s=s.replace(old,new)

# 2) Add tables in setup.
needle='''            CREATE TABLE IF NOT EXISTS rpg_bounties (\n                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, poster_id INTEGER NOT NULL,\n                target_name TEXT NOT NULL, reward INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'open', created_at REAL NOT NULL\n            );\n'''
insert='''            CREATE TABLE IF NOT EXISTS rpg_bounties (\n                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, poster_id INTEGER NOT NULL,\n                target_name TEXT NOT NULL, reward INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'open', created_at REAL NOT NULL\n            );\n            CREATE TABLE IF NOT EXISTS rpg_area_discoveries (\n                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, area_key TEXT NOT NULL,\n                discovered_at REAL NOT NULL, source TEXT NOT NULL DEFAULT 'exploration',\n                PRIMARY KEY (guild_id, user_id, area_key)\n            );\n            CREATE TABLE IF NOT EXISTS rpg_objectives (\n                guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, period TEXT NOT NULL,\n                objective_key TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL,\n                progress_type TEXT NOT NULL, target INTEGER NOT NULL, progress INTEGER NOT NULL DEFAULT 0,\n                reward_xp INTEGER NOT NULL DEFAULT 0, reward_gold INTEGER NOT NULL DEFAULT 0,\n                reward_item TEXT, reward_qty INTEGER NOT NULL DEFAULT 0, claimed INTEGER NOT NULL DEFAULT 0,\n                period_key TEXT NOT NULL, created_at REAL NOT NULL,\n                PRIMARY KEY (guild_id, user_id, period, objective_key, period_key)\n            );\n            CREATE TABLE IF NOT EXISTS rpg_world_events (\n                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, event_key TEXT NOT NULL,\n                name TEXT NOT NULL, description TEXT NOT NULL, area_key TEXT NOT NULL, level INTEGER NOT NULL,\n                max_hp INTEGER NOT NULL, hp INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'active',\n                started_at REAL NOT NULL, expires_at REAL NOT NULL, created_by INTEGER NOT NULL\n            );\n            CREATE TABLE IF NOT EXISTS rpg_world_event_participants (\n                event_id INTEGER NOT NULL, guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,\n                damage INTEGER NOT NULL DEFAULT 0, attacks INTEGER NOT NULL DEFAULT 0, last_attack REAL NOT NULL DEFAULT 0,\n                PRIMARY KEY (event_id, user_id), FOREIGN KEY (event_id) REFERENCES rpg_world_events(id) ON DELETE CASCADE\n            );\n            CREATE INDEX IF NOT EXISTS idx_rpg_world_events_active ON rpg_world_events(guild_id,status,expires_at);\n            CREATE INDEX IF NOT EXISTS idx_rpg_world_event_participants_damage ON rpg_world_event_participants(event_id,damage DESC);\n'''
if needle not in s: raise SystemExit('table needle not found')
s=s.replace(needle,insert)

# 3) Add quest columns migration.
needle='''            cur = await db.execute("PRAGMA table_info(rpg_bounties)")\n'''
insert='''            cur = await db.execute("PRAGMA table_info(rpg_quests)")\n            quest_existing = {row[1] for row in await cur.fetchall()}\n            quest_migrations = {"chain_key": "TEXT NOT NULL DEFAULT ''", "chain_step": "INTEGER NOT NULL DEFAULT 0"}\n            for column, definition in quest_migrations.items():\n                if column not in quest_existing:\n                    await db.execute(f"ALTER TABLE rpg_quests ADD COLUMN {column} {definition}")\n            cur = await db.execute("PRAGMA table_info(rpg_bounties)")\n'''
if needle not in s: raise SystemExit('migration needle not found')
s=s.replace(needle,insert,1)

# 4) Seed discoveries on player creation. Insert after initial player insert/skill loadout.
needle='''            for slot,skill_key in enumerate(("skill_1","skill_2","skill_3"),1):\n                await db.execute("INSERT OR IGNORE INTO rpg_skill_loadout(guild_id,user_id,slot,skill_key) VALUES(?,?,?,?)",(guild_id,user_id,slot,skill_key))\n            await db.commit()\n'''
replace='''            for slot,skill_key in enumerate(("skill_1","skill_2","skill_3"),1):\n                await db.execute("INSERT OR IGNORE INTO rpg_skill_loadout(guild_id,user_id,slot,skill_key) VALUES(?,?,?,?)",(guild_id,user_id,slot,skill_key))\n            await db.execute("INSERT OR IGNORE INTO rpg_area_discoveries(guild_id,user_id,area_key,discovered_at,source) VALUES(?,?,?,?,?)",(guild_id,user_id,"horizon_village",time.time(),"starting_area"))\n            await db.commit()\n'''
if needle not in s: raise SystemExit('create player block not found')
s=s.replace(needle,replace,1)

# 5) Make existing players discover their current area on setup.
needle='''            # Preserve an existing single-pet character while upgrading to a true\n'''
insert='''            cur = await db.execute("SELECT guild_id,user_id,area_key FROM rpg_players")\n            for _gid,_uid,_area in await cur.fetchall():\n                _area = _area or "horizon_village"\n                if _area in AREAS:\n                    await db.execute("INSERT OR IGNORE INTO rpg_area_discoveries(guild_id,user_id,area_key,discovered_at,source) VALUES(?,?,?,?,?)",(_gid,_uid,_area,time.time(),"migration"))\n            # Preserve an existing single-pet character while upgrading to a true\n'''
if needle not in s: raise SystemExit('existing discovery insertion point not found')
s=s.replace(needle,insert,1)

# 6) Replace quest_seed with richer daily + chain seed logic, preserving old quests.
start=s.index('    async def quest_seed(self,guild_id):')
end=s.index('    async def quests(self,guild_id,user_id):',start)
new_func='''    async def quest_seed(self,guild_id):\n        now=time.time()\n        async with aiosqlite.connect(self.path) as db:\n            cur=await db.execute("SELECT COUNT(*) FROM rpg_quests WHERE guild_id=? AND expires_at>?",(guild_id,now)); count=(await cur.fetchone())[0]\n            if count < 8:\n                templates=[\n                    ("daily","Wolf Hunt","Defeat 3 enemies.",1,3,"hunt",180,260,"wolf_pelt",2),\n                    ("daily","Gatherer","Collect 3 materials from adventures.",1,3,"gather",160,220,"herb",2),\n                    ("daily","Dungeon Call","Clear a dungeon floor.",1,1,"dungeon",250,350,"life_potion",2),\n                    ("weekly","Champion's Path","Win 8 battles or adventures.",5,8,"hunt",800,1200,"arcane_shard",2),\n                ]\n                for kind,title,desc,lvl,target,ptype,xp,gold,item,qty in templates:\n                    await db.execute("INSERT INTO rpg_quests(guild_id,kind,title,description,level_req,target,progress_type,reward_xp,reward_gold,reward_item,reward_qty,expires_at,chain_key,chain_step) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(guild_id,kind,title,desc,lvl,target,ptype,xp,gold,item,qty,now+86400*(7 if kind=='weekly' else 1),"",0))\n            # Persistent story chains: one quest must be claimed before the next appears.\n            chains=[\n                ("first_steps","The First Steps",[("Reach the Whispering Woods", "Travel to the Whispering Woods.", "explore", 1, 250, 350, "herb", 3),("Clear the Path", "Defeat 3 enemies.", "hunt", 3, 300, 450, "wolf_pelt", 4),("Old Hunter's Map", "Explore 2 different areas.", "explore", 2, 450, 600, "mat_ancient_bone", 2),("The First Gate", "Clear a dungeon floor.", "dungeon", 1, 550, 800, "arcane_shard", 3)]),\n                ("abyss_whispers","Whispers of the Abyss",[("Strange Signs", "Explore a high-level region.", "explore", 1, 700, 900, "mat_shadow_essence", 3),("Corrupted Beasts", "Defeat 8 enemies.", "hunt", 8, 900, 1200, "mat_demon_horn", 3),("Break the Seal", "Clear 2 dungeon floors.", "dungeon", 2, 1200, 1700, "mat_void_crystal", 2),("A Voice in the Dark", "Deal damage to a world boss.", "worldboss", 1, 1800, 2600, "void_egg", 1)]),\n                ("horizon_legend","The Horizon Legend",[("Across the World", "Explore 5 different areas.", "explore", 5, 1200, 1800, "mat_star_fragment", 4),("Trial of Steel", "Defeat 15 enemies.", "hunt", 15, 1500, 2200, "steel_sword", 1),("The Deep", "Clear 5 dungeon floors.", "dungeon", 5, 2200, 3200, "dragon_trophy", 1),("Heart of Horizon", "Deal damage to a world boss.", "worldboss", 1, 3000, 5000, "dragon_egg", 1)])]\n            for chain_key,_title,steps in chains:\n                for idx,(title,desc,ptype,target,xp,gold,item,qty) in enumerate(steps,1):\n                    cur=await db.execute("SELECT 1 FROM rpg_quests WHERE guild_id=? AND chain_key=? AND chain_step=?",(guild_id,chain_key,idx))\n                    if not await cur.fetchone():\n                        await db.execute("INSERT INTO rpg_quests(guild_id,kind,title,description,level_req,target,progress_type,reward_xp,reward_gold,reward_item,reward_qty,expires_at,chain_key,chain_step) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(guild_id,"story",title,desc,1,target,ptype,xp,gold,item,qty,now+86400*365,chain_key,idx))\n            await db.commit()\n\n'''
s=s[:start]+new_func+s[end:]

# 7) Modify quests query to expose chain fields.
old='''            cur=await db.execute("SELECT q.id,q.title,q.description,q.level_req,q.target,q.progress_type,q.reward_xp,q.reward_gold,q.reward_item,q.reward_qty,COALESCE(p.progress,0),COALESCE(p.status,'available') FROM rpg_quests q LEFT JOIN rpg_player_quests p ON q.id=p.quest_id AND p.guild_id=? AND p.user_id=? WHERE q.guild_id=? AND q.expires_at>? ORDER BY q.kind,q.id",(guild_id,user_id,guild_id,time.time())); return await cur.fetchall()\n'''
new='''            cur=await db.execute("SELECT q.id,q.title,q.description,q.level_req,q.target,q.progress_type,q.reward_xp,q.reward_gold,q.reward_item,q.reward_qty,COALESCE(p.progress,0),COALESCE(p.status,'available'),q.kind,q.chain_key,q.chain_step FROM rpg_quests q LEFT JOIN rpg_player_quests p ON q.id=p.quest_id AND p.guild_id=? AND p.user_id=? WHERE q.guild_id=? AND q.expires_at>? ORDER BY CASE q.kind WHEN 'story' THEN 0 WHEN 'daily' THEN 1 ELSE 2 END,q.chain_key,q.chain_step,q.id",(guild_id,user_id,guild_id,time.time())); return await cur.fetchall()\n'''
if old not in s: raise SystemExit('quests query not found')
s=s.replace(old,new,1)

# 8) Add chain prerequisite to accept_quest.
needle='''            cur=await db.execute("SELECT id,level_req FROM rpg_quests WHERE guild_id=? AND id=?",(guild_id,qid)); q=await cur.fetchone()\n            if not q:return False,"Quest not found."\n            if p["level"]<q[1]:return False,f"You need level {q[1]}."\n'''
rep='''            cur=await db.execute("SELECT id,level_req,chain_key,chain_step,title FROM rpg_quests WHERE guild_id=? AND id=?",(guild_id,qid)); q=await cur.fetchone()\n            if not q:return False,"Quest not found."\n            if p["level"]<q[1]:return False,f"You need level {q[1]}."\n            if q[2] and int(q[3])>1:\n                cur=await db.execute("SELECT q.id,COALESCE(p.status,'available') FROM rpg_quests q LEFT JOIN rpg_player_quests p ON q.id=p.quest_id AND p.guild_id=? AND p.user_id=? WHERE q.guild_id=? AND q.chain_key=? AND q.chain_step=?",(guild_id,user_id,guild_id,q[2],int(q[3])-1)); prev=await cur.fetchone()\n                if not prev or prev[1] != "claimed":\n                    return False,f"Complete the previous step of **{q[2].replace('_',' ').title()}** first."\n'''
if needle not in s: raise SystemExit('accept quest block not found')
s=s.replace(needle,rep,1)

# 9) Add objective methods and map/explore methods before check_achievements.
marker='    async def check_achievements(self,guild_id,user_id):\n'
idx=s.index(marker)
methods=r'''    async def _objective_period_key(self, period):
        from datetime import datetime, timezone
        now=datetime.now(timezone.utc)
        return now.strftime("%Y-%m-%d") if period=="daily" else now.strftime("%G-W%V")

    async def ensure_objectives(self,guild_id,user_id):
        now=time.time()
        async with aiosqlite.connect(self.path) as db:
            for period in ("daily","weekly"):
                period_key=await self._objective_period_key(period)
                for key,title,desc,ptype,target,xp,gold,item,qty in OBJECTIVE_TEMPLATES[period]:
                    await db.execute("INSERT OR IGNORE INTO rpg_objectives(guild_id,user_id,period,objective_key,title,description,progress_type,target,progress,reward_xp,reward_gold,reward_item,reward_qty,claimed,period_key,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(guild_id,user_id,period,key,title,desc,ptype,target,0,xp,gold,item,qty,0,period_key,now))
            await db.commit()

    async def progress_objectives(self,guild_id,user_id,ptype,amount=1):
        await self.ensure_objectives(guild_id,user_id)
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_objectives SET progress=MIN(target,progress+?) WHERE guild_id=? AND user_id=? AND progress_type=? AND claimed=0",(max(1,int(amount)),guild_id,user_id,ptype))
            await db.commit()

    async def objectives(self,guild_id,user_id):
        await self.ensure_objectives(guild_id,user_id)
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT period,objective_key,title,description,target,progress,reward_xp,reward_gold,reward_item,reward_qty,claimed,period_key FROM rpg_objectives WHERE guild_id=? AND user_id=? ORDER BY CASE period WHEN 'daily' THEN 0 ELSE 1 END,objective_key",(guild_id,user_id))
            return await cur.fetchall()

    async def claim_objective(self,guild_id,user_id,objective_key):
        await self.ensure_objectives(guild_id,user_id)
        async with aiosqlite.connect(self.path) as db:
            period_key=await self._objective_period_key("daily")
            cur=await db.execute("SELECT period,objective_key,target,progress,reward_xp,reward_gold,reward_item,reward_qty,claimed,period_key FROM rpg_objectives WHERE guild_id=? AND user_id=? AND objective_key=? AND period_key IN (?,?)",(guild_id,user_id,objective_key,period_key,await self._objective_period_key("weekly")))
            row=await cur.fetchone()
            if not row:return False,"Objective not found. Use `!rpg objectives`."
            period,key,target,progress,xp,gold,item,qty,claimed,row_period=row
            if claimed:return False,"That objective has already been claimed."
            if progress<target:return False,f"Progress: {progress}/{target}."
            await db.execute("UPDATE rpg_objectives SET claimed=1 WHERE guild_id=? AND user_id=? AND objective_key=? AND period_key=?",(guild_id,user_id,key,row_period))
            await db.execute("UPDATE rpg_players SET gold=gold+? WHERE guild_id=? AND user_id=?",(gold,guild_id,user_id)); await db.commit()
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
        current=p.get("area_key","horizon_village") or "horizon_village"
        neighbors=AREA_CONNECTIONS.get(current,[])
        eligible=[k for k in neighbors if k in AREAS and int(p["level"])>=int(AREAS[k]["level"])]
        if not eligible:return False,"There are no new level-appropriate routes from this region yet. Check `!rpg map` for the world atlas."
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT area_key FROM rpg_area_discoveries WHERE guild_id=? AND user_id=?",(guild_id,user_id)); known={r[0] for r in await cur.fetchall()}
            unknown=[k for k in eligible if k not in known]
            target=random.choice(unknown or eligible)
            fresh=target not in known
            await db.execute("INSERT OR IGNORE INTO rpg_area_discoveries(guild_id,user_id,area_key,discovered_at,source) VALUES(?,?,?,?,?)",(guild_id,user_id,target,time.time(),"exploration"))
            await db.commit()
        if fresh:
            await self.add_rewards(guild_id,user_id,80+int(AREAS[target]["level"])*8,60+int(AREAS[target]["level"])*6)
            await self.progress_quests(guild_id,user_id,"explore",1)
            return True,f"🧭 You discovered **{AREAS[target]['name']}**!\n{AREAS[target]['desc']}\n\n+XP and Gold for discovering a new region."
        await self.progress_quests(guild_id,user_id,"explore",1)
        return True,f"🧭 You explored around **{AREAS[current]['name']}** and found signs of **{AREAS[target]['name']}**."

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
            skill=self._skill(p["class_name"],skill_key.lower().strip())
            if not skill:return False,"That skill doesn't exist for your class.",event
            equipped={x["key"] for _s,x in await self.skill_loadout(guild_id,user_id) if x}
            if skill["key"] not in equipped:return False,"That skill isn't equipped.",event
            if int(p["mp"])<int(skill["cost"]):return False,f"You need {skill['cost']} MP.",event
        # World-boss damage is intentionally capped so a single player cannot delete the event.\n        pseudo={"enemy": {"name":name,"level":level,"hp":max_hp,"atk":max(10,int(level*2.2)),"def":max(5,int(level*1.4)},"enemy_hp":hp,"buffs":{},"enemy_debuffs":{}}\n        if skill:\n            pseudo["enemy"]["def"]=max(1,int(level*1.2)); damage=self._skill_damage(stats,pseudo["enemy"],skill,pseudo); damage=max(1,min(int(max_hp*.045),damage)); cost=int(skill["cost"])\n            async with aiosqlite.connect(self.path) as db: await db.execute("UPDATE rpg_players SET mp=max(0,mp-?) WHERE guild_id=? AND user_id=?",(cost,guild_id,user_id)); await db.commit()\n            action_name=skill["name"]\n        else:\n            damage=max(1,min(int(max_hp*.025),self._damage(stats["atk"],int(level*1.2),1.0)))\n            action_name="Basic Attack"\n        new_hp=max(0,int(hp)-damage)\n        async with aiosqlite.connect(self.path) as db:\n            await db.execute("INSERT INTO rpg_world_event_participants(event_id,guild_id,user_id,damage,attacks,last_attack) VALUES(?,?,?,?,?,?) ON CONFLICT(event_id,user_id) DO UPDATE SET damage=damage+excluded.damage,attacks=attacks+1,last_attack=excluded.last_attack",(eid,guild_id,user_id,damage,1,now))\n            await db.execute("UPDATE rpg_world_events SET hp=?,status=? WHERE id=?",(new_hp,"defeated" if new_hp<=0 else "active",eid)); await db.commit()\n        await self.progress_objectives(guild_id,user_id,"worldboss",1)\n        await self.progress_quests(guild_id,user_id,"worldboss",1)\n        if new_hp<=0:\n            async with aiosqlite.connect(self.path) as db:\n                cur=await db.execute("SELECT user_id,damage FROM rpg_world_event_participants WHERE event_id=? ORDER BY damage DESC",(eid,)); participants=await cur.fetchall()\n                await db.commit()\n            # Reward everyone who meaningfully participated, with a top-damage bonus.\n            for rank,(uid,damage_done) in enumerate(participants,1):\n                base_xp=900+int(level)*30; base_gold=900+int(level)*40\n                mult=1.5 if rank==1 else (1.25 if rank<=3 else 1.0)\n                await self.add_rewards(guild_id,int(uid),int(base_xp*mult),int(base_gold*mult))\n                await self.add_item(guild_id,int(uid),"dragon_trophy" if rank<=3 else "arcane_shard",1 if rank<=3 else 2)\n            return True,f"🌎 **{name} has been defeated!**\nYour **{action_name}** dealt **{damage:,}** damage.\n🏆 You were part of the victory and earned a contribution reward.",await self.world_boss_active(guild_id)\n        phase="I" if new_hp>max_hp*.75 else ("II" if new_hp>max_hp*.5 else ("III" if new_hp>max_hp*.25 else "ENRAGED"))\n        return True,f"🌎 **{name}** — Phase **{phase}**\nYour **{action_name}** dealt **{damage:,}** damage.\n❤️ Boss HP: **{new_hp:,}/{max_hp:,}**",await self.world_boss_active(guild_id)\n\n'''
s=s[:idx]+methods+s[idx:]

# 10) Hook objectives into quest progress.
old='''            await db.commit()\n\n    async def claim_quest(self,guild_id,user_id,qid):\n'''
new='''            await db.commit()\n        await self.progress_objectives(guild_id,user_id,ptype,amount)\n\n    async def claim_quest(self,guild_id,user_id,qid):\n'''
# only first occurrence after progress_quests? It may match earlier commit. Use around function segment.
pos=s.index('    async def progress_quests')
seg=s[pos:s.index('    async def claim_quest',pos)]
if '            await db.commit()' not in seg: raise SystemExit('progress quest commit not found')
seg=seg.rsplit('            await db.commit()',1)[0]+'            await db.commit()\n        await self.progress_objectives(guild_id,user_id,ptype,amount)\n'
s=s[:pos]+seg+s[s.index('    async def claim_quest',pos):]

# 11) Enhance explore/travel to objective and discovery.
old='''        async with aiosqlite.connect(self.path) as db:\n            await db.execute("UPDATE rpg_players SET area_key=?,location=? WHERE guild_id=? AND user_id=?",(area_key.lower(),area["name"],guild_id,user_id)); await db.commit()\n        return True,f"You traveled to **{area['name']}**. {area['desc']}"\n'''
new='''        async with aiosqlite.connect(self.path) as db:\n            await db.execute("UPDATE rpg_players SET area_key=?,location=? WHERE guild_id=? AND user_id=?",(area_key.lower(),area["name"],guild_id,user_id))\n            await db.execute("INSERT OR IGNORE INTO rpg_area_discoveries(guild_id,user_id,area_key,discovered_at,source) VALUES(?,?,?,?,?)",(guild_id,user_id,area_key.lower(),time.time(),"travel")); await db.commit()\n        await self.progress_quests(guild_id,user_id,"explore",1)\n        return True,f"You traveled to **{area['name']}**. {area['desc']}"\n'''
if old not in s: raise SystemExit('travel block not found')
s=s.replace(old,new,1)

# 12) Modify start_combat state with status/last skill and dungeon boss floor.
old='''base={"player_hp":stats["hp"],"player_max_hp":stats["max_hp"],"player_mp":stats["mp"],"player_max_mp":stats["max_mp"],"player_stamina":p["stamina"],"class_name":p["class_name"],"turn":1,"skill_cooldowns":{},"pet_cooldown":0,"pet":pet_bonus,"combat_stats":stats,"player_level":p["level"],"equipped_skill_keys":[skill["key"] for _slot,skill in loadout if skill],"buffs":{},"enemy_debuffs":{},"enemy_dot":0,"enemy_dot_turns":0,"combo":0,"delayed_damage":0}\n'''
new='''base={"player_hp":stats["hp"],"player_max_hp":stats["max_hp"],"player_mp":stats["mp"],"player_max_mp":stats["max_mp"],"player_stamina":p["stamina"],"class_name":p["class_name"],"turn":1,"skill_cooldowns":{},"pet_cooldown":0,"pet":pet_bonus,"combat_stats":stats,"player_level":p["level"],"equipped_skill_keys":[skill["key"] for _slot,skill in loadout if skill],"buffs":{},"enemy_debuffs":{},"enemy_statuses":{},"enemy_dot":0,"enemy_dot_turns":0,"combo":0,"combo_chain":[],"last_skill_effect":"","delayed_damage":0}\n'''
if old not in s: raise SystemExit('combat base not found')
s=s.replace(old,new,1)
# Add boss flag to dungeon enemy selection.
old='''            enemy=self._enemy_for_level(p["level"]+max(0, req-p["level"])+1,"horizon_village")\n'''
new='''            enemy=self._enemy_for_level(p["level"]+max(0, req-p["level"])+1,p.get("area_key","horizon_village"))\n            enemy["dungeon_name"]=n; enemy["is_boss"]=False\n'''
if old not in s: raise SystemExit('dungeon enemy selection not found')
s=s.replace(old,new,1)
# Mark first floor not boss and later final boss.
old='''state={"mode":"dungeon","enemy":enemy,"enemy_hp":enemy["hp"],"floor":1,"floors":floors,"name":n,"reward_xp":xp,"reward_gold":gold,"log":[f"**Floor 1/{floors}** — {enemy['name']} blocks your path."],"started":time.time(),**base}\n'''
new='''state={"mode":"dungeon","enemy":enemy,"enemy_hp":enemy["hp"],"floor":1,"floors":floors,"name":n,"reward_xp":xp,"reward_gold":gold,"log":[f"**Floor 1/{floors}** — {enemy['name']} blocks your path."],"started":time.time(),**base}\n'''
# same, no-op intentionally
s=s.replace(old,new,1)

# 13) Add explicit status system helpers before _apply_skill_effect.
marker='    def _apply_skill_effect(self, skill, stats, state):\n'
idx=s.index(marker)
status_methods=r'''    def _apply_enemy_status(self, state, status, turns, power=0.0, source=""):
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

'''
s=s[:idx]+status_methods+s[idx:]

# 14) Inject status applications in skill effects.
repls={
'''state["enemy_dot"]+=max(3,int(stats["atk"]*0.08)); state["enemy_dot_turns"]=2; log.append(f"🩸 **{skill['name']}** dealt **{dmg}** and applied Bleed.")''':'''self._apply_enemy_status(state,"bleed",3,.08,skill["name"]); log.append(f"🩸 **{skill['name']}** dealt **{dmg}** and applied **Bleed** for 3 turns.")''',
'''state["enemy_dot"]+=max(4,int(stats["atk"]*.07)); state["enemy_dot_turns"]=3; log.append(f"☠️ **{skill['name']}** dealt **{dmg}** and applied {effect.title()}.")''':'''self._apply_enemy_status(state,effect,3 if effect=="burn" else 4,.07,skill["name"]); log.append(f"{'🔥' if effect=='burn' else '☠️'} **{skill['name']}** dealt **{dmg}** and applied **{effect.title()}**.")''',
'''state["enemy_debuffs"]["slow_turns"]=2; log.append(f"❄️ **{skill['name']}** dealt **{dmg}** and slowed the enemy.")''':'''self._apply_enemy_status(state,"freeze",2,.0,skill["name"]); state["enemy_debuffs"]["slow_turns"]=2; log.append(f"❄️ **{skill['name']}** dealt **{dmg}** and applied **Freeze** for 2 turns.")''',
'''state["enemy_debuffs"]["vulnerable"]=.20; state["enemy_debuffs"]["vuln_turns"]=2; log.append(f"🔻 **{skill['name']}** exposed a weakness.")''':'''state["enemy_debuffs"]["vulnerable"]=.20; state["enemy_debuffs"]["vuln_turns"]=2; self._apply_enemy_status(state,"vulnerable",2,.20,skill["name"]); log.append(f"🔻 **{skill['name']}** exposed a weakness for 2 turns.")''',
'''state["enemy_debuffs"]["def_down"]=.18; state["enemy_debuffs"]["def_turns"]=3; log.append(f"🗡️ **{skill['name']}** dealt **{dmg}** and reduced defense.")''':'''state["enemy_debuffs"]["def_down"]=.18; state["enemy_debuffs"]["def_turns"]=3; self._apply_enemy_status(state,"weaken",3,.18,skill["name"]); log.append(f"🗡️ **{skill['name']}** dealt **{dmg}** and reduced defense for 3 turns.")''',
}
for old,new in repls.items():
    if old not in s: print('warning missing effect',old[:50])
    s=s.replace(old,new)
# Replace curse dot with named status.
s=s.replace('''state["enemy_debuffs"].update(vulnerable=.14,vuln_turns=3); state["enemy_dot"]+=max(3,int(stats["atk"]*.06)); state["enemy_dot_turns"]=3; log.append(f"🕯️ **{skill['name']}** cursed the target after dealing **{dmg}** damage.")''','''state["enemy_debuffs"].update(vulnerable=.14,vuln_turns=3); self._apply_enemy_status(state,"curse",3,.06,skill["name"]); self._apply_enemy_status(state,"vulnerable",3,.14,skill["name"]); log.append(f"🕯️ **{skill['name']}** cursed the target after dealing **{dmg}** damage.")''')
# Add combo tracking at end of skill effect before dealt calculation.
needle='''        dealt=max(0,start_enemy_hp-state["enemy_hp"])\n'''
rep='''        # Skill-combo engine: repeated compatible effects create escalating but capped bonus damage.\n        effect=skill.get("effect","damage")\n        chain=state.setdefault("combo_chain",[])\n        if state.get("last_skill_effect"):\n            previous=state.get("last_skill_effect")\n            combo_pairs={("armor_break","heavy"),("mark","execute"),("vulnerability","execute"),("burn","freeze"),("bleed","lifesteal"),("poison","execute"),("curse","execute"),("def_buff","attack_buff"),("attack_buff","heavy"),("multi","bleed"),("freeze","heavy"),("mana_drain","ultimate"),("combo","multi")}\n            if (previous,effect) in combo_pairs or previous==effect:\n                state["combo"]=min(6,int(state.get("combo",0))+1); chain.append(effect); chain=chain[-4:]; state["combo_chain"]=chain\n                bonus=min(.30,.04*state["combo"]); extra=max(1,int(max(1,stats["atk"])*bonus)); state["enemy_hp"]=max(0,state["enemy_hp"]-extra); log.append(f"🔗 **COMBO x{state['combo']}!** +{extra} bonus damage.")\n            else:\n                state["combo"]=0; state["combo_chain"]=[]\n        state["last_skill_effect"]=effect\n        dealt=max(0,start_enemy_hp-state["enemy_hp"])\n'''
if needle not in s: raise SystemExit('dealt marker not found')
s=s.replace(needle,rep,1)

# 15) Fix undefined hit helper in mana_burst/curse by using _skill_damage.
s=s.replace('''        elif effect=="mana_burst":\n            dmg=hit(skill["mult"]*1.08,.30); gain=max(3,int(stats["max_mp"]*.06)); state["player_mp"]=min(stats["max_mp"],state["player_mp"]+gain); log.append(f"💧 **{skill['name']}** released **{dmg}** damage and restored {gain} MP.")\n''','''        elif effect=="mana_burst":\n            dmg=self._skill_damage(stats,enemy,skill,state,skill["mult"]*1.08); dmg=min(dmg,max(2,int(enemy["hp"]*.30))); state["enemy_hp"]-=dmg; gain=max(3,int(stats["max_mp"]*.06)); state["player_mp"]=min(stats["max_mp"],state["player_mp"]+gain); log.append(f"💧 **{skill['name']}** released **{dmg}** damage and restored {gain} MP.")\n''')
s=s.replace('''        elif effect=="curse":\n            dmg=hit(None,.18); state["enemy_debuffs"].update(vulnerable=.14,vuln_turns=3); self._apply_enemy_status(state,"curse",3,.06,skill["name"]); self._apply_enemy_status(state,"vulnerable",3,.14,skill["name"]); log.append(f"🕯️ **{skill['name']}** cursed the target after dealing **{dmg}** damage.")\n''','''        elif effect=="curse":\n            dmg=self._skill_damage(stats,enemy,skill,state); dmg=min(dmg,max(2,int(enemy["hp"]*.18))); state["enemy_hp"]-=dmg; state["enemy_debuffs"].update(vulnerable=.14,vuln_turns=3); self._apply_enemy_status(state,"curse",3,.06,skill["name"]); self._apply_enemy_status(state,"vulnerable",3,.14,skill["name"]); log.append(f"🕯️ **{skill['name']}** cursed the target after dealing **{dmg}** damage.")\n''')

# 16) Make dungeon final floor a boss and show boss stats. Replace floor transition block.
old='''                state["floor"]+=1; state["enemy"]=self._enemy_for_level(p["level"]+state["floor"]+1,p.get("area_key","horizon_village")); state["enemy_hp"]=state["enemy"]["hp"]\n                state["player_hp"]=min(stats["max_hp"],state["player_hp"]+max(5,stats["max_hp"]//8)); state["player_mp"]=min(stats["max_mp"],state["player_mp"]+max(3,stats["max_mp"]//10))\n                state["log"].append(f"🏰 **Floor {state['floor']}/{state['floors']}** — **{state['enemy']['name']}** appears. You recover HP and MP between floors.")\n'''
new='''                state["floor"]+=1\n                if state["floor"]==state["floors"]:\n                    state["enemy"]=self._enemy_for_level(p["level"]+state["floor"]+1,p.get("area_key","horizon_village"))\n                    state["enemy"]["name"]=DUNGEON_BOSSES.get(state["name"],state["enemy"]["name"])\n                    state["enemy"]["is_boss"]=True\n                    state["enemy"]["hp"]=int(state["enemy"]["hp"]*2.6); state["enemy"]["atk"]=int(state["enemy"]["atk"]*1.35); state["enemy"]["def"]=int(state["enemy"]["def"]*1.25)\n                else:\n                    state["enemy"]=self._enemy_for_level(p["level"]+state["floor"]+1,p.get("area_key","horizon_village")); state["enemy"]["is_boss"]=False\n                state["enemy_hp"]=state["enemy"]["hp"]\n                state["player_hp"]=min(stats["max_hp"],state["player_hp"]+max(5,stats["max_hp"]//8)); state["player_mp"]=min(stats["max_mp"],state["player_mp"]+max(3,stats["max_mp"]//10))\n                state["enemy_statuses"]={}; state["combo"]=0; state["combo_chain"]=[]; state["last_skill_effect"]=""\n                boss_tag=" 👑 BOSS" if state["enemy"].get("is_boss") else ""\n                state["log"].append(f"🏰 **Floor {state['floor']}/{state['floors']}** — **{state['enemy']['name']}**{boss_tag} appears. You recover HP and MP between floors.")\n'''
if old not in s: raise SystemExit('floor transition not found')
s=s.replace(old,new,1)

# 17) Replace enemy turn status handling with new tick/stun/weaken/silence.
old='''        dot=int(state.get("enemy_dot",0))\n        if dot and state.get("enemy_dot_turns",0)>0:\n            state["enemy_hp"]=max(1,state["enemy_hp"]-dot); state["enemy_dot_turns"]-=1; state["log"].append(f"☠️ Damage-over-time effects dealt **{dot}**.")\n        if state.get("delayed_damage",0)>0:\n'''
new='''        status_logs=self._tick_enemy_statuses(state)\n        if status_logs: state["log"].extend(status_logs)\n        if state.get("delayed_damage",0)>0:\n'''
if old not in s: raise SystemExit('dot turn block not found')
s=s.replace(old,new,1)
# enemy attack block
old='''        if not defending and random.random()<min(.30,stats["speed"]/220 + float(state.get("buffs",{}).get("evasion",0))):\n            state["log"].append(f"💨 You dodged **{state['enemy']['name']}**.")\n        else:\n            def_up=float(state.get("buffs",{}).get("def_up",0)); effective_def=stats["defense"]*(1+def_up)\n            dmg=self._damage(state["enemy"]["atk"], effective_def, 0.90, ENEMY_DAMAGE_VARIANCE)\n            dmg=min(dmg, max(2, int(stats["max_hp"]*MAX_NORMAL_DAMAGE_FRACTION)))\n            shield=state.get("shield_pct",.5) if (defending or state.get("shield_turns",0)>0) else 0\n            if shield:dmg=max(1,int(dmg*(1-shield)))\n            state["player_hp"]-=dmg; state["log"].append(f"🩸 **{state['enemy']['name']}** hit you for **{dmg}**.")\n            if state.get("buffs",{}).get("reflect"):\n                reflected=max(1,int(dmg*state["buffs"]["reflect"])); state["enemy_hp"]=max(1,state["enemy_hp"]-reflected); state["log"].append(f"↩️ Your barrier reflected **{reflected}** damage.")\n'''
new='''        enemy_status=state.get("enemy_statuses",{})\n        if "stun" in enemy_status or "freeze" in enemy_status:\n            state["log"].append(f"💫 **{state['enemy']['name']}** is unable to act because of a status effect.")\n        elif state["enemy_hp"]<=0:\n            pass\n        elif not defending and random.random()<min(.30,stats["speed"]/220 + float(state.get("buffs",{}).get("evasion",0))):\n            state["log"].append(f"💨 You dodged **{state['enemy']['name']}**.")\n        else:\n            def_up=float(state.get("buffs",{}).get("def_up",0)); effective_def=stats["defense"]*(1+def_up)\n            enemy_atk=float(state["enemy"]["atk"])\n            if "weaken" in enemy_status or "silence" in enemy_status: enemy_atk*=.82\n            if state["enemy"].get("is_boss") and state["enemy_hp"]<state["enemy"].get("hp",1)*.25: enemy_atk*=1.18\n            dmg=self._damage(enemy_atk, effective_def, 0.90, ENEMY_DAMAGE_VARIANCE)\n            dmg=min(dmg, max(2, int(stats["max_hp"]*MAX_NORMAL_DAMAGE_FRACTION)))\n            shield=state.get("shield_pct",.5) if (defending or state.get("shield_turns",0)>0) else 0\n            if shield:dmg=max(1,int(dmg*(1-shield)))\n            state["player_hp"]-=dmg; state["log"].append(f"🩸 **{state['enemy']['name']}** hit you for **{dmg}**.")\n            if state.get("buffs",{}).get("reflect"):\n                reflected=max(1,int(dmg*state["buffs"]["reflect"])); state["enemy_hp"]=max(1,state["enemy_hp"]-reflected); state["log"].append(f"↩️ Your barrier reflected **{reflected}** damage.")\n'''
if old not in s: raise SystemExit('enemy attack block not found')
s=s.replace(old,new,1)
# Status turn cleanup: add enemy_statuses decrement. Insert before cooldown loop.
needle='''        for key2 in list(state.get("skill_cooldowns",{})):\n'''
rep='''        for _status_key,_status_data in list(state.get("enemy_statuses",{}).items()):\n            # Tick durations after the enemy has had its turn. Damage statuses were already processed above.\n            if _status_key in {"stun","freeze","silence","slow","vulnerable","weaken"}:\n                _status_data["turns"]=int(_status_data.get("turns",0))-1\n                if _status_data["turns"]<=0: state["enemy_statuses"].pop(_status_key,None)\n        for key2 in list(state.get("skill_cooldowns",{})):\n'''
# first occurrence likely correct after enemy turn; there may be earlier. Find near _combat_action_locked.
pos=s.index('    async def _combat_action_locked')
sub=s[pos:]
if needle not in sub: raise SystemExit('cooldown marker not found in combat sub')
sub=sub.replace(needle,rep,1); s=s[:pos]+sub

# 18) Improve status application: freeze should stun only 35% chance. Add after freeze application.
s=s.replace('''self._apply_enemy_status(state,"freeze",2,.0,skill["name"]); state["enemy_debuffs"]["slow_turns"]=2; log.append''','''self._apply_enemy_status(state,"freeze",2,.0,skill["name"]); state["enemy_debuffs"]["slow_turns"]=2\n            if random.random()<.35: self._apply_enemy_status(state,"stun",1,.0,skill["name"]); log.append(f"💫 **{skill['name']}** also stunned the enemy!")\n            log.append''')

rpg.write_text(s)

# BOT modifications: combat embed statuses, new commands, quest tuple compatibility.
# Combat embed add boss tag/status/combo.
b=b.replace('''    floor=f" • Floor {state['floor']}/{state['floors']}" if state["mode"]=="dungeon" else ""\n''','''    floor=f" • Floor {state['floor']}/{state['floors']}" if state["mode"]=="dungeon" else ""\n    boss_tag=" 👑 BOSS" if enemy.get("is_boss") else ""\n''',1)
b=b.replace('''          f"👹 **{enemy['name']}** · Lv **{enemy['level']}**\n"''','''          f"👹 **{enemy['name']}**{boss_tag} · Lv **{enemy['level']}**\n"''',1)
b=b.replace('''    if skill_lines:\n        desc += "\\n\\n✨ **Skills**\\n" + "\\n".join(skill_lines)\n''','''    if skill_lines:\n        desc += "\\n\\n✨ **Skills**\\n" + "\\n".join(skill_lines)\n    statuses=bot.rpg._status_summary(state.get("enemy_statuses",{})) if hasattr(bot.rpg,"_status_summary") else "None"\n    desc += f"\\n\\n🧿 **Enemy Status:** {statuses}"\n    if state.get("combo",0): desc += f"\\n🔗 **Combo:** x{state.get('combo',0)}"\n''',1)

# Fix quest list formatter indexes by replacing relevant block. Locate rpg_quests command start.
start=b.index('@rpg_root.group(name="quests"') if '@rpg_root.group(name="quests"' in b else -1
if start==-1: raise SystemExit('quests group not found')
# inspect and replace only formatter section via known old strings.
b=b.replace('''        qid,title,desc,lvl,target,ptype,xp,gold,item,qty,progress,status=q\n        return f"**#{qid} — {title}**\\n{desc}\\nLv {lvl}+ • {progress}/{target} • {status.title()}\\nReward: +{xp} XP • +{gold}g" + (f" • {ITEMS.get(item,{\'name\':item})[\'name\']} ×{qty}" if item else "")\n''','''        qid,title,desc,lvl,target,ptype,xp,gold,item,qty,progress,status,kind,chain_key,chain_step=q\n        chain=f" • Story {chain_step}" if kind=="story" else ""\n        return f"**#{qid} — {title}**{chain}\\n{desc}\\nLv {lvl}+ • {progress}/{target} • {status.title()}\\nReward: +{xp} XP • +{gold}g" + (f" • {ITEMS.get(item,{\'name\':item})[\'name\']} ×{qty}" if item else "")\n''')
# Other tuple unpackings in quest info/accept root.
b=b.replace('''        qid,title,desc,lvl,target,ptype,xp,gold,item,qty,progress,status=q\n''','''        qid,title,desc,lvl,target,ptype,xp,gold,item,qty,progress,status,kind,chain_key,chain_step=q\n''')
# There are two occurrences likely; okay.

# Add map/explore/objectives/worldboss/dungeons commands before profile.
marker='@rpg_root.command(name="profile", aliases=["character", "sheet"])\n'
idx=b.index(marker)
commands=r'''@rpg_root.command(name="map", aliases=["worldmap", "atlas"])
async def rpg_map(ctx):
    await _rpg_delete(ctx)
    data=await bot.rpg.world_map(ctx.guild.id,ctx.author.id)
    if not data:
        await _rpg_action_panel(ctx,"World Map","Create your hero first with `!rpg start`.",False); return
    current,discovered=data
    rows=[]
    ordered=sorted(AREAS.items(), key=lambda kv:(int(kv[1].get("level",1)),kv[0]))
    for key,area in ordered:
        marker="📍" if key==current else ("🟢" if key in discovered else "🔒")
        routes=bot.rpg.__class__.__dict__.get("_dummy",None)
        rows.append((key,area))
    pages=_rpg_pages("🌎 World Map",rows,page_size=5,icon="🗺️",formatter=lambda x:(f"**{'📍' if x[0]==current else ('🟢' if x[0] in discovered else '🔒')} {x[1]['name']}** — `{x[0]}`\nLv {x[1]['level']}+ • {x[1]['type'].title()}\n{x[1]['desc']}"))
    await _rpg_panel(ctx,pages)

@rpg_root.command(name="explore")
async def rpg_explore(ctx):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.explore(ctx.guild.id,ctx.author.id); await _rpg_action_panel(ctx,"🧭 Exploration",msg,ok)

@rpg_root.command(name="dungeons", aliases=["dungeonlist"])
async def rpg_dungeons(ctx):
    await _rpg_delete(ctx)
    rows=[(d[0],d) for d in DUNGEONS]
    def fmt(x):
        d=x[1]; boss=bot.rpg.__class__  # keep formatter deterministic
        from rpg import DUNGEON_BOSSES
        return f"**{d[0]}** — `{d[0].lower().replace(' ','_')}`\nLv **{d[1]}+** • {d[2]} floors • +{d[3]} base XP • +{d[4]} base Gold\n👑 Boss: **{DUNGEON_BOSSES.get(d[0],'Unknown')}**\n{d[5]}"
    await _rpg_panel(ctx,_rpg_pages("🏰 Dungeon Atlas",rows,page_size=3,icon="🏰",formatter=fmt))

@rpg_root.command(name="objectives", aliases=["goals", "tasks"])
async def rpg_objectives(ctx):
    await _rpg_delete(ctx)
    rows=await bot.rpg.objectives(ctx.guild.id,ctx.author.id)
    def fmt(x):
        period,key,title,desc,target,progress,xp,gold,item,qty,claimed,period_key=x
        state="CLAIMED" if claimed else ("READY" if progress>=target else f"{progress}/{target}")
        reward=f"+{xp} XP • +{gold}g" + (f" • {ITEMS.get(item,{'name':item}).get('name',item)} ×{qty}" if item else "")
        return f"**{title}** · {period.title()} · **{state}**\n{desc}\nReward: {reward}\nKey: `{key}`"
    pages=_rpg_pages("🎯 Daily & Weekly Objectives",rows,page_size=4,icon="🎯",formatter=fmt)
    await _rpg_panel(ctx,pages)

@rpg_root.command(name="objective")
async def rpg_objective_claim(ctx,key:str=""):
    await _rpg_delete(ctx)
    if not key:
        await _rpg_action_panel(ctx,"Objective","Use `!rpg objective <objective_key>` to claim a completed objective. See `!rpg objectives`.",False); return
    ok,msg=await bot.rpg.claim_objective(ctx.guild.id,ctx.author.id,key.lower()); await _rpg_action_panel(ctx,"🎯 Objective Reward",msg,ok)

@rpg_root.group(name="worldboss", invoke_without_command=True)
async def rpg_worldboss(ctx):
    await _rpg_delete(ctx)
    event=await bot.rpg.world_boss_active(ctx.guild.id)
    if not event:
        await _rpg_action_panel(ctx,"🌎 World Boss","No world boss is active. Use `!rpg worldboss spawn` to summon one.",False); return
    eid,gid,event_key,name,desc,area,level,max_hp,hp,status,started,expires,created_by=event
    remaining=max(0,int(expires-time.time()))
    e=_rpg_embed(f"🌎 WORLD BOSS — {name}",f"👑 Level **{level}**\n❤️ **{hp:,}/{max_hp:,} HP**\n📍 **{AREAS.get(area,{'name':area})['name']}**\n⏳ {remaining//60}m {remaining%60}s remaining\n\n{desc}\n\n`!rpg worldboss attack` — basic attack\n`!rpg worldboss attack <skill_key>` — use an equipped skill")
    e.set_image(url=_mob_image({'name':name,'level':level,'type':'boss','element':'world','role':'boss'}))
    await _rpg_panel(ctx,[e])

@rpg_worldboss.command(name="spawn")
async def rpg_worldboss_spawn(ctx, template:str=""):
    await _rpg_delete(ctx); ok,msg,event=await bot.rpg.world_boss_spawn(ctx.guild.id,ctx.author.id,template.lower() or None); await _rpg_action_panel(ctx,"🌎 World Boss",msg,ok)

@rpg_worldboss.command(name="attack")
async def rpg_worldboss_attack(ctx, *, skill_key:str=""):
    await _rpg_delete(ctx); ok,msg,event=await bot.rpg.world_boss_attack(ctx.guild.id,ctx.author.id,skill_key.strip()); await _rpg_action_panel(ctx,"⚔️ World Boss Attack",msg,ok)

'''
b=b[:idx]+commands+b[idx:]

# Help text add phase 1 commands.
b=b.replace('''`!rpg areas` — world atlas\n`!rpg travel <area_key>` — travel\n`!rpg quests` — quest board\n`!rpg daily` — daily reward''','''`!rpg map` — connected world map\n`!rpg areas` — world atlas\n`!rpg explore` — discover nearby regions\n`!rpg travel <area_key>` — travel\n`!rpg dungeons` — dungeon atlas + bosses\n`!rpg quests` — quest board + story chains\n`!rpg objectives` — daily/weekly objectives\n`!rpg objective <key>` — claim an objective\n`!rpg worldboss` — server world boss\n`!rpg daily` — daily reward''',1)
# Add phase 1 note to root help combat and world progression if exact exists.
b=b.replace('''`!rpg adventure` — live battle\n`!rpg dungeon [name]` — multi-floor battle''','''`!rpg adventure` — live battle with status effects and combos\n`!rpg dungeon [name]` — multi-floor battle with final bosses''',1)

bot.write_text(b)
print('phase1 patch applied')
