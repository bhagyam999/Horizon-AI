import os
import time
import aiosqlite


class Database:
    def __init__(self, path=None):
        self.path = path or os.getenv('HORIZON_DB', 'horizon.db')

    async def setup(self):
        async with aiosqlite.connect(self.path) as db:
            await db.executescript('''
            CREATE TABLE IF NOT EXISTS settings (
                guild_id INTEGER PRIMARY KEY,
                ai_channel_id INTEGER DEFAULT 0,
                log_channel_id INTEGER DEFAULT 0,
                welcome_channel_id INTEGER DEFAULT 0,
                announcement_channel_id INTEGER DEFAULT 0,
                mod_enabled INTEGER DEFAULT 1,
                mod_action INTEGER DEFAULT 1,
                personality TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS profiles (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                nickname TEXT DEFAULT '',
                preferences TEXT DEFAULT '',
                xp INTEGER DEFAULT 0,
                coins INTEGER DEFAULT 0,
                warnings INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                fact TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS cooldowns (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                expires REAL NOT NULL,
                PRIMARY KEY (guild_id, user_id, name)
            );
            CREATE TABLE IF NOT EXISTS inventory (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                item TEXT NOT NULL,
                quantity INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id, item)
            );
            CREATE TABLE IF NOT EXISTS quests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                reward_xp INTEGER DEFAULT 0,
                reward_coins INTEGER DEFAULT 0,
                created_by INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                starts TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                message_id INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS event_signups (
                event_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (event_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            ''')
            await db.commit()

    async def _ensure_profile(self, db, guild_id, user_id):
        await db.execute('INSERT OR IGNORE INTO profiles(guild_id,user_id) VALUES(?,?)', (guild_id, user_id))

    async def settings(self, guild_id):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute('INSERT OR IGNORE INTO settings(guild_id) VALUES(?)', (guild_id,))
            await db.commit()
            cur = await db.execute('SELECT * FROM settings WHERE guild_id=?', (guild_id,))
            return dict(await cur.fetchone())

    async def set_setting(self, guild_id, key, value):
        allowed = {'ai_channel_id','log_channel_id','welcome_channel_id','announcement_channel_id','mod_enabled','mod_action','personality'}
        if key not in allowed:
            raise ValueError(f'Unknown setting: {key}')
        async with aiosqlite.connect(self.path) as db:
            await db.execute('INSERT OR IGNORE INTO settings(guild_id) VALUES(?)', (guild_id,))
            await db.execute(f'UPDATE settings SET {key}=? WHERE guild_id=?', (value, guild_id))
            await db.commit()

    async def profile(self, guild_id, user_id):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            await self._ensure_profile(db, guild_id, user_id)
            await db.commit()
            cur = await db.execute('SELECT * FROM profiles WHERE guild_id=? AND user_id=?', (guild_id,user_id))
            return dict(await cur.fetchone())

    async def set_profile(self, guild_id, user_id, nickname=None, preferences=None):
        current = await self.profile(guild_id, user_id)
        nickname = current['nickname'] if nickname is None else nickname
        preferences = current['preferences'] if preferences is None else preferences
        async with aiosqlite.connect(self.path) as db:
            await self._ensure_profile(db, guild_id, user_id)
            await db.execute('UPDATE profiles SET nickname=?, preferences=? WHERE guild_id=? AND user_id=?', (nickname,preferences,guild_id,user_id))
            await db.commit()

    async def add_xp(self, guild_id, user_id, xp, coins=0):
        async with aiosqlite.connect(self.path) as db:
            await self._ensure_profile(db, guild_id, user_id)
            await db.execute('UPDATE profiles SET xp=xp+?, coins=coins+? WHERE guild_id=? AND user_id=?', (xp,coins,guild_id,user_id))
            await db.commit()
        return await self.profile(guild_id, user_id)

    async def leaderboard(self, guild_id, limit=10):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute('SELECT user_id,xp,coins FROM profiles WHERE guild_id=? ORDER BY xp DESC LIMIT ?', (guild_id,limit))
            return await cur.fetchall()

    async def add_memory(self, guild_id, fact, created_by):
        async with aiosqlite.connect(self.path) as db:
            await db.execute('INSERT INTO memories(guild_id,fact,created_by) VALUES(?,?,?)', (guild_id,fact,created_by))
            await db.commit()

    async def memories(self, guild_id, limit=30):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute('SELECT id,fact,created_by,created_at FROM memories WHERE guild_id=? ORDER BY id DESC LIMIT ?', (guild_id,limit))
            return await cur.fetchall()

    async def delete_memory(self, guild_id, memory_id):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute('DELETE FROM memories WHERE id=? AND guild_id=?', (memory_id,guild_id))
            await db.commit()
            return cur.rowcount > 0

    async def is_cooldown(self, guild_id, user_id, name):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute('SELECT expires FROM cooldowns WHERE guild_id=? AND user_id=? AND name=?', (guild_id,user_id,name))
            row = await cur.fetchone()
            return bool(row and row[0] > time.time())

    async def cooldown(self, guild_id, user_id, name, seconds):
        async with aiosqlite.connect(self.path) as db:
            await db.execute('INSERT OR REPLACE INTO cooldowns VALUES(?,?,?,?)', (guild_id,user_id,name,time.time()+seconds))
            await db.commit()

    async def inventory(self, guild_id, user_id):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute('SELECT item,quantity FROM inventory WHERE guild_id=? AND user_id=? AND quantity>0 ORDER BY item', (guild_id,user_id))
            return await cur.fetchall()

    async def create_quest(self, guild_id, title, description, reward_xp, reward_coins, created_by):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute('INSERT INTO quests(guild_id,title,description,reward_xp,reward_coins,created_by) VALUES(?,?,?,?,?,?)', (guild_id,title,description,reward_xp,reward_coins,created_by))
            await db.commit(); return cur.lastrowid

    async def quests(self, guild_id):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute('SELECT id,title,description,reward_xp,reward_coins FROM quests WHERE guild_id=? ORDER BY id DESC', (guild_id,))
            return await cur.fetchall()

    async def create_event(self, guild_id, channel_id, title, description, starts, created_by):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute('INSERT INTO events(guild_id,channel_id,title,description,starts,created_by) VALUES(?,?,?,?,?,?)', (guild_id,channel_id,title,description,starts,created_by))
            await db.commit(); return cur.lastrowid

    async def events(self, guild_id):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute('SELECT id,title,description,starts,channel_id,message_id FROM events WHERE guild_id=? ORDER BY id DESC', (guild_id,))
            return await cur.fetchall()

    async def signup(self, event_id, user_id):
        async with aiosqlite.connect(self.path) as db:
            await db.execute('INSERT OR IGNORE INTO event_signups(event_id,user_id) VALUES(?,?)', (event_id,user_id)); await db.commit()

    async def add_warning(self, guild_id, user_id, moderator_id, reason):
        async with aiosqlite.connect(self.path) as db:
            await self._ensure_profile(db,guild_id,user_id)
            await db.execute('INSERT INTO warnings(guild_id,user_id,moderator_id,reason) VALUES(?,?,?,?)', (guild_id,user_id,moderator_id,reason))
            await db.execute('UPDATE profiles SET warnings=warnings+1 WHERE guild_id=? AND user_id=?', (guild_id,user_id)); await db.commit()
        return await self.profile(guild_id,user_id)

    async def warnings(self, guild_id, user_id):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute('SELECT id,moderator_id,reason,created_at FROM warnings WHERE guild_id=? AND user_id=? ORDER BY id DESC', (guild_id,user_id))
            return await cur.fetchall()
