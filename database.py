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
            CREATE TABLE IF NOT EXISTS ai_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                scope_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user','model')),
                content TEXT NOT NULL,
                created_at REAL DEFAULT (strftime('%s','now'))
            );
            CREATE INDEX IF NOT EXISTS idx_ai_conversations_scope ON ai_conversations(guild_id, scope_id, id);
            CREATE TABLE IF NOT EXISTS ai_server_messages (
                message_id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                author_name TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL DEFAULT (strftime('%s','now'))
            );
            DROP INDEX IF EXISTS idx_ai_server_messages_guild;
            CREATE INDEX IF NOT EXISTS idx_ai_server_messages_guild ON ai_server_messages(guild_id, message_id);
            DROP INDEX IF EXISTS idx_ai_server_messages_channel;
            CREATE INDEX IF NOT EXISTS idx_ai_server_messages_channel ON ai_server_messages(guild_id, channel_id, message_id);
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
            CREATE TABLE IF NOT EXISTS reaction_roles (
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                emoji TEXT NOT NULL,
                role_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, message_id, emoji)
            );
            CREATE TABLE IF NOT EXISTS giveaways (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                prize TEXT NOT NULL,
                winners INTEGER DEFAULT 1,
                ends_at REAL NOT NULL,
                host_id INTEGER NOT NULL,
                ended INTEGER DEFAULT 0,
                created_at REAL DEFAULT (strftime('%s','now'))
            );
            CREATE TABLE IF NOT EXISTS giveaway_entries (
                giveaway_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (giveaway_id, user_id)
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

    async def add_ai_message(self, guild_id, scope_id, role, content):
        content = str(content or '').strip()[:8000]
        if not content or role not in {'user','model'}:
            return
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                'INSERT INTO ai_conversations(guild_id,scope_id,role,content) VALUES(?,?,?,?)',
                (guild_id, str(scope_id), role, content),
            )
            # Keep a long-lived but bounded private conversation history per user.
            await db.execute(
                '''DELETE FROM ai_conversations
                   WHERE guild_id=? AND scope_id=? AND id NOT IN
                     (SELECT id FROM ai_conversations WHERE guild_id=? AND scope_id=? ORDER BY id DESC LIMIT 120)''',
                (guild_id, str(scope_id), guild_id, str(scope_id)),
            )
            await db.commit()

    async def ai_conversation(self, guild_id, scope_id, limit=120):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                'SELECT id,role,content,created_at FROM ai_conversations WHERE guild_id=? AND scope_id=? ORDER BY id DESC LIMIT ?',
                (guild_id, str(scope_id), int(limit)),
            )
            rows = await cur.fetchall()
        return list(reversed(rows))


    async def add_ai_server_message(self, message_id, guild_id, channel_id, author_id, author_name, content):
        content = str(content or '').strip()[:4000]
        if not content:
            return
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                '''INSERT OR REPLACE INTO ai_server_messages
                   (message_id,guild_id,channel_id,author_id,author_name,content,created_at)
                   VALUES(?,?,?,?,?,?,?)''',
                (int(message_id), int(guild_id), int(channel_id), int(author_id), str(author_name)[:100], content, time.time()),
            )
            # Keep a bounded server history so the AI can learn from old chats without
            # turning the database into an unbounded transcript archive.
            await db.execute(
                '''DELETE FROM ai_server_messages WHERE guild_id=? AND message_id NOT IN
                   (SELECT message_id FROM ai_server_messages WHERE guild_id=? ORDER BY message_id DESC LIMIT 8000)''',
                (int(guild_id), int(guild_id)),
            )
            await db.commit()

    async def ai_server_messages(self, guild_id, limit=2000, channel_id=None):
        async with aiosqlite.connect(self.path) as db:
            if channel_id is None:
                cur = await db.execute(
                    'SELECT message_id,channel_id,author_id,author_name,content,created_at FROM ai_server_messages WHERE guild_id=? ORDER BY message_id DESC LIMIT ?',
                    (int(guild_id), int(limit)),
                )
            else:
                cur = await db.execute(
                    'SELECT message_id,channel_id,author_id,author_name,content,created_at FROM ai_server_messages WHERE guild_id=? AND channel_id=? ORDER BY message_id DESC LIMIT ?',
                    (int(guild_id), int(channel_id), int(limit)),
                )
            rows = await cur.fetchall()
        return list(reversed(rows))

    async def clear_ai_conversation(self, guild_id, scope_id):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute('DELETE FROM ai_conversations WHERE guild_id=? AND scope_id=?', (guild_id, str(scope_id)))
            await db.commit()
            return cur.rowcount

    async def remove_last_ai_message(self, guild_id, scope_id, role=None):
        async with aiosqlite.connect(self.path) as db:
            if role:
                cur = await db.execute('SELECT id FROM ai_conversations WHERE guild_id=? AND scope_id=? AND role=? ORDER BY id DESC LIMIT 1', (guild_id, str(scope_id), role))
            else:
                cur = await db.execute('SELECT id FROM ai_conversations WHERE guild_id=? AND scope_id=? ORDER BY id DESC LIMIT 1', (guild_id, str(scope_id)))
            row = await cur.fetchone()
            if not row:
                return False
            await db.execute('DELETE FROM ai_conversations WHERE id=?', (row[0],))
            await db.commit()
            return True

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

    async def add_reaction_role(self, guild_id, channel_id, message_id, emoji, role_id):
        async with aiosqlite.connect(self.path) as db:
            await db.execute('INSERT OR REPLACE INTO reaction_roles(guild_id,channel_id,message_id,emoji,role_id) VALUES(?,?,?,?,?)', (guild_id,channel_id,message_id,str(emoji),role_id))
            await db.commit()

    async def reaction_role(self, guild_id, message_id, emoji):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute('SELECT role_id FROM reaction_roles WHERE guild_id=? AND message_id=? AND emoji=?', (guild_id,message_id,str(emoji)))
            row=await cur.fetchone()
            return row[0] if row else None

    async def reaction_roles(self, guild_id, message_id=None):
        async with aiosqlite.connect(self.path) as db:
            if message_id:
                cur=await db.execute('SELECT message_id,emoji,role_id,channel_id FROM reaction_roles WHERE guild_id=? AND message_id=? ORDER BY message_id', (guild_id,message_id))
            else:
                cur=await db.execute('SELECT message_id,emoji,role_id,channel_id FROM reaction_roles WHERE guild_id=? ORDER BY message_id', (guild_id,))
            return await cur.fetchall()

    async def remove_reaction_role(self, guild_id, message_id, emoji):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute('DELETE FROM reaction_roles WHERE guild_id=? AND message_id=? AND emoji=?', (guild_id,message_id,str(emoji)))
            await db.commit()
            return cur.rowcount > 0

    async def create_giveaway(self, guild_id, channel_id, message_id, prize, winners, ends_at, host_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute('INSERT INTO giveaways(guild_id,channel_id,message_id,prize,winners,ends_at,host_id) VALUES(?,?,?,?,?,?,?)', (guild_id,channel_id,message_id,prize,winners,ends_at,host_id))
            await db.commit(); return cur.lastrowid

    async def giveaway(self, giveaway_id):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory=aiosqlite.Row
            cur=await db.execute('SELECT * FROM giveaways WHERE id=?', (giveaway_id,))
            row=await cur.fetchone(); return dict(row) if row else None

    async def active_giveaways(self):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory=aiosqlite.Row
            cur=await db.execute('SELECT * FROM giveaways WHERE ended=0')
            return [dict(r) for r in await cur.fetchall()]

    async def add_giveaway_entry(self, giveaway_id, user_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute('INSERT OR IGNORE INTO giveaway_entries(giveaway_id,user_id) VALUES(?,?)', (giveaway_id,user_id))
            await db.commit(); return cur.rowcount > 0

    async def remove_giveaway_entry(self, giveaway_id, user_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute('DELETE FROM giveaway_entries WHERE giveaway_id=? AND user_id=?', (giveaway_id,user_id))
            await db.commit(); return cur.rowcount > 0

    async def giveaway_entries(self, giveaway_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute('SELECT user_id FROM giveaway_entries WHERE giveaway_id=?', (giveaway_id,))
            return [r[0] for r in await cur.fetchall()]

    async def end_giveaway(self, giveaway_id):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute('UPDATE giveaways SET ended=1 WHERE id=? AND ended=0', (giveaway_id,))
            await db.commit(); return cur.rowcount > 0

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
