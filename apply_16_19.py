from pathlib import Path
p=Path('/mnt/data/v13work/rpg.py')
s=p.read_text()
marker='            await db.commit()\n\n        # Phase 4 launches on a clean RPG economy/progression state.'
insert=r'''            # v14 — Phases 16-19: mysteries, world-scale events, persistent world memory, RPG completion audit.
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
            await db.commit()

        # Phase 4 launches on a clean RPG economy/progression state.'''
if marker not in s: raise SystemExit('schema marker missing')
s=s.replace(marker,insert,1)
# Insert methods before endgame_ascend
marker2='    async def endgame_ascend(self, guild_id, user_id):\n'
methods=r'''    async def _seed_v14_content(self, guild_id):
        mysteries = [
            ("worldroot_echo", "Echo of the Worldroot", "A pulse beneath Horizon Village repeats an event from the distant past.", "worldroot", 10, "", "horizon_village", 3, 1200, 900, "chronicle_shard", 1),
            ("nameless_city", "The Nameless City", "A city appears on maps only when the eastern seal is disturbed.", "location", 25, "", "sealed_gate", 5, 2500, 1800, "arcane_shard", 5),
            ("broken_compass", "The Compass That Lies", "The Broken Compass points toward a place that should not exist.", "artifact", 35, "story_guard", "whispering_woods", 7, 5000, 3500, "chronicle_shard", 2),
            ("silent_moon", "The Silent Moon", "For one night the moon casts no shadow, and old NPC records change.", "cosmic", 50, "", "horizon_village", 10, 9000, 6000, "star_fragment", 1),
        ]
        events = [
            ("worldroot_wake", "Worldroot Awakening", "The Worldroot is stirring. Players must stabilize four regions before the anomaly spreads.", "world_threat", 1000, 12000, 9000, "chronicle_shard", 1),
            ("rift_storm", "Riftstorm", "Reality fractures across the world. Exploration and combat contributions close the rifts.", "world_threat", 1500, 16000, 12000, "arcane_shard", 8),
        ]
        async with aiosqlite.connect(self.path) as db:
            for row in mysteries:
                await db.execute("INSERT OR IGNORE INTO rpg_mysteries(guild_id,mystery_key,name,description,category,required_level,required_flag,area_key,discovery_threshold,reward_xp,reward_gold,reward_item,reward_qty) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (guild_id,*row))
            # A world-scale event is opt-in to activation; only one can be active at a time.
            for key,name,desc,etype,target,xp,gold,item,qty in events:
                await db.execute("INSERT OR IGNORE INTO rpg_server_events(guild_id,event_key,name,description,event_type,target,reward_xp,reward_gold,reward_item,reward_qty,status,started_at,expires_at) VALUES(?,?,?,?,?,?,?,?,?,?, 'dormant',0,0)", (guild_id,key,name,desc,etype,target,xp,gold,item,qty))
            await db.execute("INSERT OR IGNORE INTO rpg_world_event_state(guild_id) VALUES(?)", (guild_id,))
            await db.execute("INSERT OR IGNORE INTO rpg_rpg_completion(guild_id,updated_at) VALUES(?,?)", (guild_id,time.time()))
            await db.commit()

    async def mysteries(self, guild_id, user_id):
        await self._seed_v14_content(guild_id)
        p=await self.player(guild_id,user_id)
        level=int(p['level']) if p else 0
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT mystery_key,name,description,category,required_level,area_key,discovery_threshold,reward_xp,reward_gold,reward_item,reward_qty FROM rpg_mysteries WHERE guild_id=? ORDER BY required_level,mystery_key", (guild_id,))
            rows=await cur.fetchall()
            out=[]
            for r in rows:
                cur2=await db.execute("SELECT progress,discovered FROM rpg_mystery_progress WHERE guild_id=? AND user_id=? AND mystery_key=?", (guild_id,user_id,r[0]))
                pr=await cur2.fetchone()
                out.append((*r, int(pr[0]) if pr else 0, bool(pr[1]) if pr else False, level>=int(r[4])))
            return out

    async def investigate_mystery(self, guild_id, user_id, key):
        key=str(key).lower().strip(); rows=await self.mysteries(guild_id,user_id)
        row=next((r for r in rows if r[0]==key),None)
        if not row:return False,"That mystery does not exist."
        _,name,desc,category,req,area,threshold,xp,gold,item,qty,progress,discovered,eligible=row
        if not eligible:return False,f"**{name}** requires level **{req}**."
        if discovered:return True,f"**{name}** is already recorded in your discoveries."
        progress=min(int(threshold),int(progress)+1)
        now=time.time()
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO rpg_mystery_progress(guild_id,user_id,mystery_key,progress,discovered,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(guild_id,user_id,mystery_key) DO UPDATE SET progress=excluded.progress,discovered=excluded.discovered,updated_at=excluded.updated_at", (guild_id,user_id,key,progress,int(progress>=threshold),now))
            if progress>=threshold:
                await db.execute("INSERT OR IGNORE INTO rpg_world_memory(guild_id,user_id,memory_key,category,summary,consequence_json,created_at) VALUES(?,?,?,?,?,?,?)", (guild_id,user_id,'mystery:'+key,'mystery',f'{name}: {desc}',json.dumps({'reward_xp':xp,'reward_gold':gold,'reward_item':item,'reward_qty':qty}),now))
                await db.commit()
            else:
                await db.commit()
        if progress>=threshold:
            await self.add_rewards(guild_id,user_id,xp,gold)
            if item: await self.add_item(guild_id,user_id,item,qty,event_type='mystery_reward')
            await self._chronicle(guild_id,user_id,'mystery_discovered',f'Mystery discovered — {name}',desc,area)
            return True,f"**{name}** discovered. Rewards: **+{xp} XP**, **+{gold} gold**" + (f", **{item} ×{qty}**" if item else '') + "."
        return True,f"You found another clue for **{name}**. Progress: **{progress}/{threshold}**."

    async def anomalies(self, guild_id):
        await self._seed_v14_content(guild_id)
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT anomaly_key,area_key,severity,state,started_at,resolved_at FROM rpg_anomalies WHERE guild_id=? ORDER BY id DESC",(guild_id,))
            return await cur.fetchall()

    async def world_event_status(self,guild_id):
        await self._seed_v14_content(guild_id)
        now=time.time()
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_server_events SET status='expired' WHERE guild_id=? AND status='active' AND expires_at<=?",(guild_id,now))
            await db.commit()
            cur=await db.execute("SELECT id,event_key,name,description,event_type,target,progress,reward_xp,reward_gold,reward_item,reward_qty,status,started_at,expires_at FROM rpg_server_events WHERE guild_id=? AND event_type='world_threat' ORDER BY id DESC",(guild_id,))
            return await cur.fetchall()

    async def start_world_event(self,guild_id,user_id,key):
        rows=await self.world_event_status(guild_id); key=str(key).lower().strip()
        row=next((r for r in rows if r[1]==key),None)
        if not row:return False,"That world-scale event does not exist."
        if row[11]=='active':return False,"A world-scale event is already active."
        if row[11]=='complete':return False,"That event has already been completed."
        now=time.time(); expires=now+72*3600
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_server_events SET status='dormant' WHERE guild_id=? AND event_type='world_threat' AND status='active'",(guild_id,))
            await db.execute("UPDATE rpg_server_events SET status='active',started_at=?,expires_at=?,progress=0 WHERE guild_id=? AND event_key=?",(now,expires,guild_id,key))
            await db.execute("UPDATE rpg_world_event_state SET event_key=?,phase='awakening',threat=25,world_progress=0,started_at=?,updated_at=? WHERE guild_id=?",(key,now,now,guild_id))
            await db.commit()
        await self._chronicle(guild_id,user_id,'world_event_started',f'World-scale event — {row[2]}',row[3])
        return True,f"**{row[2]}** has begun. The entire server can contribute for the next **72 hours**."

    async def contribute_world_event(self,guild_id,user_id,event_id,amount=1):
        amount=max(1,min(1000,int(amount)))
        rows=await self.world_event_status(guild_id); row=next((r for r in rows if int(r[0])==int(event_id)),None)
        if not row or row[11]!='active':return False,"That world event is not active."
        p=await self.player(guild_id,user_id)
        if not p:return False,"Create a hero first."
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT progress,target FROM rpg_server_events WHERE guild_id=? AND id=?",(guild_id,event_id)); e=await cur.fetchone()
            if not e:return False,"Event not found."
            amount=min(amount,max(0,int(e[1])-int(e[0])))
            if amount<=0:return False,"The event is already complete."
            await db.execute("UPDATE rpg_server_events SET progress=MIN(target,progress+?) WHERE guild_id=? AND id=?",(amount,guild_id,event_id))
            await db.execute("INSERT INTO rpg_server_event_contributions(event_id,guild_id,user_id,contribution) VALUES(?,?,?,?) ON CONFLICT(event_id,user_id) DO UPDATE SET contribution=contribution+excluded.contribution",(event_id,guild_id,user_id,amount))
            await db.execute("UPDATE rpg_world_event_state SET world_progress=world_progress+?,threat=MAX(0,threat-?),phase='containment',updated_at=? WHERE guild_id=?",(amount,max(1,amount//10),time.time(),guild_id))
            cur=await db.execute("SELECT progress,target,reward_xp,reward_gold,reward_item,reward_qty,name FROM rpg_server_events WHERE guild_id=? AND id=?",(guild_id,event_id)); after=await cur.fetchone()
            complete=int(after[0])>=int(after[1])
            if complete: await db.execute("UPDATE rpg_server_events SET status='complete' WHERE guild_id=? AND id=?",(guild_id,event_id))
            await db.commit()
        if complete:
            await self.add_rewards(guild_id,user_id,after[2],after[3])
            if after[4]: await self.add_item(guild_id,user_id,after[4],after[5],event_type='world_event_reward')
            await self._chronicle(guild_id,user_id,'world_event_complete',f'World-scale event resolved — {after[6]}','The community reached the required contribution target.')
            return True,f"The server completed **{after[6]}**. You earned **+{after[2]} XP** and **+{after[3]} gold**."
        await self._chronicle(guild_id,user_id,'world_event_contribution',f'Contribution to {after[6]}',f'You contributed {amount} progress to a world-scale threat.')
        return True,f"You contributed **{amount}**. Event progress: **{after[0]}/{after[1]}**."

    async def memory_list(self,guild_id,user_id=0,limit=20):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT memory_key,category,summary,consequence_json,created_at,user_id FROM rpg_world_memory WHERE guild_id=? AND (user_id=? OR user_id=0) ORDER BY created_at DESC LIMIT ?",(guild_id,user_id,int(limit)))
            return await cur.fetchall()

    async def record_memory(self,guild_id,user_id,memory_key,category,summary,consequence=None):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO rpg_world_memory(guild_id,user_id,memory_key,category,summary,consequence_json,created_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(guild_id,user_id,memory_key) DO UPDATE SET summary=excluded.summary,consequence_json=excluded.consequence_json,created_at=excluded.created_at",(guild_id,user_id,memory_key,category,summary,json.dumps(consequence or {},separators=(',',':')),time.time()))
            await db.commit()
        return True

    async def completion_audit(self,guild_id,user_id):
        p=await self.player(guild_id,user_id)
        checks={
            'character': bool(p),
            'world': bool(p and p.get('area_key')),
            'combat': bool(p),
            'equipment': bool(p),
            'crafting': False,
            'economy': False,
            'pets': False,
            'life': False,
            'social': False,
            'quests': False,
            'living_world': False,
            'story_memory': False,
            'construction': False,
            'factions': False,
            'endgame': False,
            'mysteries': False,
            'world_events': False,
            'world_memory': False,
        }
        async with aiosqlite.connect(self.path) as db:
            tables=['rpg_professions','rpg_market','rpg_pet_inventory','rpg_housing','rpg_social_reputation','rpg_player_quests','rpg_world_state','rpg_story_memory','rpg_world_structures','rpg_faction_members','rpg_endgame_progress','rpg_mysteries','rpg_server_events','rpg_world_memory']
            for key,table in zip(['crafting','economy','pets','life','social','quests','living_world','story_memory','construction','factions','endgame','mysteries','world_events','world_memory'],tables):
                cur=await db.execute(f'SELECT 1 FROM {table} WHERE guild_id=? LIMIT 1',(guild_id,)); checks[key]=bool(await cur.fetchone())
        # RPG completion is an integration audit, not a claim that Phase 20 public-platform work is done.
        completed=sum(1 for v in checks.values() if v); total=len(checks)
        now=time.time()
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO rpg_rpg_completion(guild_id,phase16,phase17,phase18,phase19,audit_json,updated_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(guild_id) DO UPDATE SET phase16=excluded.phase16,phase17=excluded.phase17,phase18=excluded.phase18,phase19=excluded.phase19,audit_json=excluded.audit_json,updated_at=excluded.updated_at",(guild_id,int(checks['mysteries']),int(checks['world_events']),int(checks['world_memory']),int(completed==total),json.dumps(checks,separators=(',',':')),now))
            await db.commit()
        return checks,completed,total

'''
if marker2 not in s: raise SystemExit('method marker missing')
s=s.replace(marker2,methods+marker2,1)
p.write_text(s)

# bot commands append before Message handling marker
bp=Path('/mnt/data/v13work/bot.py'); b=bp.read_text()
marker3='# -------------------- Message handling --------------------'
cmds=r'''# ---------------------------------------------------------------------------
# v14 — Phases 16-19 commands
# ---------------------------------------------------------------------------

@rpg_root.command(name="mysteries", aliases=["mystery", "discoveries"])
async def rpg_mysteries(ctx):
    await _rpg_delete(ctx)
    rows=await bot.rpg.mysteries(ctx.guild.id,ctx.author.id)
    lines=[]
    for key,name,desc,category,req,area,threshold,xp,gold,item,qty,progress,discovered,eligible in rows:
        state="DISCOVERED" if discovered else (f"CLUE {progress}/{threshold}" if eligible else f"LOCKED — Lv {req}")
        lines.append(f"**{name}** · `{key}`\n{desc}\n**{state}**")
    await _rpg_panel(ctx,[_rpg_embed("🜂 Mysteries of Horizon","\n\n".join(lines) or "No mysteries have surfaced yet.")])

@rpg_root.command(name="investigate", aliases=["investigate-mystery", "mystery-search"])
async def rpg_investigate(ctx, mystery_key:str=""):
    await _rpg_delete(ctx)
    if not mystery_key:
        await _rpg_action_panel(ctx,"🜂 Investigation","Use `!rpg investigate <mystery_key>`.",False); return
    ok,msg=await bot.rpg.investigate_mystery(ctx.guild.id,ctx.author.id,mystery_key)
    await _rpg_action_panel(ctx,"🜂 Investigation",msg,ok)

@rpg_root.command(name="anomalies", aliases=["anomaly", "rifts"])
async def rpg_anomalies(ctx):
    await _rpg_delete(ctx)
    rows=await bot.rpg.anomalies(ctx.guild.id)
    body="\n".join(f"• **{key}** — `{state}` · Severity {severity} · `{area}`" for key,area,severity,state,started,resolved in rows) or "No recorded anomalies."
    await _rpg_action_panel(ctx,"🜂 World Anomalies",body,True)

@rpg_root.command(name="worldevents", aliases=["worldevent", "worldthreats"])
async def rpg_worldevents(ctx):
    await _rpg_delete(ctx)
    rows=await bot.rpg.world_event_status(ctx.guild.id)
    body="\n\n".join(f"**#{r[0]} {r[2]}** — `{r[11]}`\n{r[3]}\nProgress: **{r[6]}/{r[5]}**" for r in rows) or "No world-scale events have been seeded yet."
    body += "\n\nStart one with `!rpg worldeventstart <event_key>` and contribute with `!rpg worldeventcontribute <id> <amount>`."
    await _rpg_action_panel(ctx,"🌌 World-Scale Events",body[:4000],True)

@rpg_root.command(name="worldeventstart", aliases=["startworldevent", "start-event"])
async def rpg_worldeventstart(ctx,event_key:str=""):
    await _rpg_delete(ctx)
    if not event_key:
        await _rpg_action_panel(ctx,"🌌 World Event","Use `!rpg worldeventstart <event_key>`.",False); return
    ok,msg=await bot.rpg.start_world_event(ctx.guild.id,ctx.author.id,event_key)
    await _rpg_action_panel(ctx,"🌌 World Event",msg,ok)

@rpg_root.command(name="worldeventcontribute", aliases=["worldcontribute", "threatcontribute"])
async def rpg_worldeventcontribute(ctx,event_id:int=0,amount:int=1):
    await _rpg_delete(ctx)
    ok,msg=await bot.rpg.contribute_world_event(ctx.guild.id,ctx.author.id,event_id,amount)
    await _rpg_action_panel(ctx,"🌌 World Event Contribution",msg,ok)

@rpg_root.command(name="memory", aliases=["worldmemorylog", "memories"])
async def rpg_memory(ctx):
    await _rpg_delete(ctx)
    rows=await bot.rpg.memory_list(ctx.guild.id,ctx.author.id)
    body="\n\n".join(f"**{category.title()}** — {summary}" for key,category,summary,consequence,created,uid in rows) or "No persistent memories have been recorded yet."
    await _rpg_action_panel(ctx,"🧠 World Memory",body[:4000],True)

@rpg_root.command(name="remember", aliases=["recordmemory"])
async def rpg_remember(ctx,key:str="",category:str="world",*,summary:str=""):
    await _rpg_delete(ctx)
    if not key or not summary:
        await _rpg_action_panel(ctx,"🧠 Memory","Use `!rpg remember <key> <category> <summary>`.",False); return
    await bot.rpg.record_memory(ctx.guild.id,ctx.author.id,key,category,summary)
    await _rpg_action_panel(ctx,"🧠 Memory Recorded",f"Recorded **{key}** as a persistent {category} memory.",True)

@rpg_root.command(name="rpgstatus", aliases=["completion", "rpg-complete"])
async def rpg_completion(ctx):
    await _rpg_delete(ctx)
    checks,completed,total=await bot.rpg.completion_audit(ctx.guild.id,ctx.author.id)
    lines="\n".join(f"{'✅' if value else '⬜'} **{key.replace('_',' ').title()}**" for key,value in checks.items())
    body=f"**Integration audit:** {completed}/{total} systems active\n\n{lines}\n\nPhase 20 (public Horizon platform) is separate from this RPG completion audit."
    await _rpg_action_panel(ctx,"🧭 Horizon RPG Completion",body[:4000],True)

'''
if marker3 not in b: raise SystemExit('bot marker missing')
b=b.replace(marker3,cmds+marker3,1)
bp.write_text(b)

# Docs
(Path('/mnt/data/v13work/PHASES_16_19_BATCH.md')).write_text('''# v14 — Phases 16–19\n\n## Phase 16 — World Mysteries\n- Persistent mystery catalog and per-player clue progress\n- Investigation/discovery rewards\n- World anomalies registry\n\n## Phase 17 — World-Scale Events\n- 72-hour server-scale threats\n- One active threat at a time\n- Shared progress + individual contribution records\n- Completion rewards and Chronicle entries\n\n## Phase 18 — World Memory\n- Persistent player/world memories\n- Memory log command\n- Important discoveries/events feed into the Chronicle/world memory layer\n\n## Phase 19 — RPG Complete\n- Cross-system integration audit\n- `!rpg rpgstatus` reports active systems\n- Phase 20 public-platform work remains separate\n\nAll changes are additive; no RPG reset is introduced.\n''')
(Path('/mnt/data/v13work/VERSION_V14.md')).write_text('''# Horizon RPG v14 — Phases 16–19\n\nBuilt on v13 (Phases 10–15). Adds World Mysteries, World-Scale Events, World Memory, and the RPG integration/completion audit. No owner/OP commands and no fresh-start reset are introduced.\n''')
