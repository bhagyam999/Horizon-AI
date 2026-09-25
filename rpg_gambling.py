from __future__ import annotations

import json
import random
import time
import uuid
from typing import Any

import aiosqlite

MIN_BET = 10
MAX_BET = 100_000


class RPGGamblingService:
    """Horizon RPG casino/economy games with atomic wagers and persistent sessions."""

    def __init__(self, path: str):
        self.path = path

    async def setup(self):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS rpg_gambling_sessions (
                    session_id TEXT PRIMARY KEY,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    game TEXT NOT NULL,
                    bet INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_rpg_gambling_owner ON rpg_gambling_sessions(guild_id,user_id,status)")
            await db.commit()

    def _clamp_bet(self, bet: int):
        try:
            bet = int(bet)
        except (TypeError, ValueError):
            return False, 0, f"Bet must be a whole number between {MIN_BET:,} and {MAX_BET:,} Gold."
        if bet < MIN_BET:
            return False, bet, f"Minimum bet is **{MIN_BET:,} Gold**."
        if bet > MAX_BET:
            return False, bet, f"Maximum bet is **{MAX_BET:,} Gold**."
        return True, bet, ""

    async def _log(self, db, guild_id, user_id, event_type, *, gold_delta=0, balance_after=None, metadata=None):
        try:
            await db.execute(
                "INSERT INTO rpg_economy_log (event_id,guild_id,user_id,event_type,item_key,quantity,gold_delta,balance_after,metadata_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (uuid.uuid4().hex, guild_id, user_id, event_type, "", 0, int(gold_delta), balance_after,
                 json.dumps(metadata or {}, separators=(",", ":")), time.time()),
            )
        except Exception:
            pass

    async def _debit(self, guild_id, user_id, amount, event_type="gambling_bet", metadata=None):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("BEGIN IMMEDIATE")
            cur = await db.execute("SELECT gold FROM rpg_players WHERE guild_id=? AND user_id=?", (guild_id, user_id))
            row = await cur.fetchone()
            if not row:
                await db.rollback()
                return False, 0, "Create your RPG hero first with !rpg start."
            balance = int(row[0])
            if balance < amount:
                await db.rollback()
                return False, balance, f"You need **{amount:,} Gold**, but only have **{balance:,} Gold**."
            new_balance = balance - amount
            await db.execute("UPDATE rpg_players SET gold=? WHERE guild_id=? AND user_id=?", (new_balance, guild_id, user_id))
            await self._log(db, guild_id, user_id, event_type, gold_delta=-amount, balance_after=new_balance, metadata=metadata)
            await db.commit()
            return True, new_balance, ""

    async def _credit(self, guild_id, user_id, amount, event_type="gambling_payout", metadata=None):
        amount = max(0, int(amount))
        async with aiosqlite.connect(self.path) as db:
            await db.execute("BEGIN IMMEDIATE")
            cur = await db.execute("SELECT gold FROM rpg_players WHERE guild_id=? AND user_id=?", (guild_id, user_id))
            row = await cur.fetchone()
            if not row:
                await db.rollback()
                return False, 0
            new_balance = int(row[0]) + amount
            await db.execute("UPDATE rpg_players SET gold=? WHERE guild_id=? AND user_id=?", (new_balance, guild_id, user_id))
            await self._log(db, guild_id, user_id, event_type, gold_delta=amount, balance_after=new_balance, metadata=metadata)
            await db.commit()
            return True, new_balance

    async def _create_session(self, guild_id, user_id, game, bet, state):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("BEGIN IMMEDIATE")
            cur = await db.execute(
                "SELECT session_id FROM rpg_gambling_sessions WHERE guild_id=? AND user_id=? AND status='active' LIMIT 1",
                (guild_id, user_id),
            )
            if await cur.fetchone():
                await db.rollback()
                return None, "You already have an active RPG gambling game. Finish it or use !rpg gambling recover."
            sid = uuid.uuid4().hex
            now = time.time()
            await db.execute(
                "INSERT INTO rpg_gambling_sessions(session_id,guild_id,user_id,game,bet,state_json,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (sid, guild_id, user_id, game, int(bet), json.dumps(state), "active", now, now),
            )
            await db.commit()
            return sid, ""

    async def _load_session(self, guild_id, user_id, session_id=None):
        async with aiosqlite.connect(self.path) as db:
            if session_id:
                cur = await db.execute(
                    "SELECT session_id,game,bet,state_json,status FROM rpg_gambling_sessions WHERE session_id=? AND guild_id=? AND user_id=?",
                    (session_id, guild_id, user_id),
                )
            else:
                cur = await db.execute(
                    "SELECT session_id,game,bet,state_json,status FROM rpg_gambling_sessions WHERE guild_id=? AND user_id=? AND status='active' ORDER BY created_at DESC LIMIT 1",
                    (guild_id, user_id),
                )
            row = await cur.fetchone()
            if not row:
                return None
            return {"session_id": row[0], "game": row[1], "bet": int(row[2]), "state": json.loads(row[3]), "status": row[4]}

    async def _save_session(self, sid, state):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_gambling_sessions SET state_json=?,updated_at=? WHERE session_id=? AND status='active'", (json.dumps(state), time.time(), sid))
            await db.commit()

    async def _close_session(self, sid, status="finished"):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE rpg_gambling_sessions SET status=?,updated_at=? WHERE session_id=? AND status='active'", (status, time.time(), sid))
            await db.commit()

    async def active_session(self, guild_id, user_id):
        return await self._load_session(guild_id, user_id)

    async def recover(self, guild_id, user_id):
        session = await self._load_session(guild_id, user_id)
        if not session:
            return False, "You have no active gambling session to recover."
        game, bet, state, sid = session["game"], session["bet"], session["state"], session["session_id"]
        if game == "mines":
            guaranteed = int(state.get("cashout", bet))
        else:
            guaranteed = bet
        await self._close_session(sid, "recovered")
        ok, balance = await self._credit(guild_id, user_id, guaranteed, "gambling_recover", {"game": game, "session_id": sid})
        if not ok:
            return False, "Your RPG character could not be found."
        return True, f"Recovered **{guaranteed:,} Gold** from your unfinished **{game.title()}** game. Balance: **{balance:,} Gold**."

    async def _balance(self, guild_id, user_id):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT gold FROM rpg_players WHERE guild_id=? AND user_id=?", (guild_id, user_id))
            row = await cur.fetchone()
            return int(row[0]) if row else 0

    async def slots(self, guild_id, user_id, bet):
        valid, bet, error = self._clamp_bet(bet)
        if not valid:
            return {"error": error}
        ok, _, error = await self._debit(guild_id, user_id, bet, metadata={"game": "slots", "bet": bet})
        if not ok:
            return {"error": error}
        symbols = ["🍒", "🍋", "🔔", "💎", "7️⃣"]
        reels = [random.choice(symbols) for _ in range(3)]
        counts = {s: reels.count(s) for s in set(reels)}
        max_count = max(counts.values())
        multiplier = 0.0
        if max_count == 3:
            multiplier = {"🍒": 2.0, "🍋": 3.0, "🔔": 5.0, "💎": 10.0, "7️⃣": 25.0}[reels[0]]
        elif max_count == 2:
            multiplier = 0.5
        payout = int(bet * multiplier)
        if payout:
            _, balance = await self._credit(guild_id, user_id, payout, metadata={"game": "slots", "bet": bet, "payout": payout})
        else:
            balance = await self._balance(guild_id, user_id)
        return {"ok": True, "bet": bet, "reels": reels, "payout": payout, "net": payout-bet, "balance": balance}

    async def coinflip(self, guild_id, user_id, bet, choice):
        valid, bet, error = self._clamp_bet(bet)
        if not valid:
            return {"error": error}
        choice = str(choice).lower().strip()
        if choice not in {"heads", "tails"}:
            return {"error": "Choose heads or tails."}
        ok, _, error = await self._debit(guild_id, user_id, bet, metadata={"game": "coinflip", "bet": bet})
        if not ok:
            return {"error": error}
        flip = random.choice(["heads", "tails"])
        payout = int(bet * 1.9) if flip == choice else 0
        if payout:
            _, balance = await self._credit(guild_id, user_id, payout, metadata={"game": "coinflip", "bet": bet, "payout": payout})
        else:
            balance = await self._balance(guild_id, user_id)
        return {"ok": True, "bet": bet, "choice": choice, "flip": flip, "payout": payout, "net": payout-bet, "balance": balance}

    async def highlow(self, guild_id, user_id, bet, guess):
        valid, bet, error = self._clamp_bet(bet)
        if not valid:
            return {"error": error}
        guess = str(guess).lower().strip()
        if guess not in {"high", "low", "seven"}:
            return {"error": "Choose high, low, or seven. High = 8–13, Low = 1–6, Seven = exact 7."}
        ok, _, error = await self._debit(guild_id, user_id, bet, metadata={"game": "highlow", "bet": bet})
        if not ok:
            return {"error": error}
        number = random.randint(1, 13)
        actual = "seven" if number == 7 else ("high" if number >= 8 else "low")
        payout = int(bet * (6.0 if actual == "seven" and guess == "seven" else 1.9 if actual == guess else 0))
        if payout:
            _, balance = await self._credit(guild_id, user_id, payout, metadata={"game": "highlow", "bet": bet, "payout": payout})
        else:
            balance = await self._balance(guild_id, user_id)
        return {"ok": True, "bet": bet, "guess": guess, "number": number, "actual": actual, "payout": payout, "net": payout-bet, "balance": balance}

    async def lottery(self, guild_id, user_id, bet=100):
        valid, bet, error = self._clamp_bet(bet)
        if not valid:
            return {"error": error}
        ok, _, error = await self._debit(guild_id, user_id, bet, metadata={"game": "lottery", "bet": bet})
        if not ok:
            return {"error": error}
        ticket = sorted(random.sample(range(1, 31), 5))
        draw = sorted(random.sample(range(1, 31), 5))
        matches = len(set(ticket) & set(draw))
        multipliers = {5: 25.0, 4: 8.0, 3: 3.0, 2: 0.75}
        payout = int(bet * multipliers.get(matches, 0))
        if payout:
            _, balance = await self._credit(guild_id, user_id, payout, metadata={"game": "lottery", "bet": bet, "payout": payout, "matches": matches})
        else:
            balance = await self._balance(guild_id, user_id)
        return {"ok": True, "bet": bet, "ticket": ticket, "draw": draw, "matches": matches, "payout": payout, "net": payout-bet, "balance": balance}

    async def snailgarden(self, guild_id, user_id, bet, pick):
        valid, bet, error = self._clamp_bet(bet)
        if not valid:
            return {"error": error}
        snails = ["Turbo", "Mochi", "Comet", "Shellshock"]
        pick = str(pick).title().strip()
        if pick not in snails:
            return {"error": "Pick one snail: Turbo, Mochi, Comet, Shellshock."}
        ok, _, error = await self._debit(guild_id, user_id, bet, metadata={"game": "snailgarden", "bet": bet})
        if not ok:
            return {"error": error}
        positions = {name: 0 for name in snails}
        for _ in range(8):
            for name in snails:
                positions[name] += random.randint(1, 5)
        ranking = sorted(snails, key=lambda x: positions[x], reverse=True)
        place = ranking.index(pick) + 1
        multipliers = {1: 3.0, 2: 1.5, 3: 0.5, 4: 0.0}
        payout = int(bet * multipliers[place])
        if payout:
            _, balance = await self._credit(guild_id, user_id, payout, metadata={"game": "snailgarden", "bet": bet, "payout": payout, "place": place})
        else:
            balance = await self._balance(guild_id, user_id)
        return {"ok": True, "bet": bet, "pick": pick, "ranking": ranking, "positions": positions, "place": place, "payout": payout, "net": payout-bet, "balance": balance}

    async def start_blackjack(self, guild_id, user_id, bet):
        valid, bet, error = self._clamp_bet(bet)
        if not valid:
            return {"error": error}
        ok, _, error = await self._debit(guild_id, user_id, bet, metadata={"game": "blackjack", "bet": bet})
        if not ok:
            return {"error": error}
        deck = self._deck()
        player, dealer = [deck.pop(), deck.pop()], [deck.pop(), deck.pop()]
        state = {"deck": deck, "player": player, "dealer": dealer}
        sid, error = await self._create_session(guild_id, user_id, "blackjack", bet, state)
        if not sid:
            await self._credit(guild_id, user_id, bet, "gambling_refund", {"game": "blackjack"})
            return {"error": error}
        if self._hand_total(player) == 21:
            payout = int(bet * 2.5)
            await self._credit(guild_id, user_id, payout, metadata={"game": "blackjack", "bet": bet, "payout": payout, "natural": True})
            await self._close_session(sid)
            return {"finished": True, "session_id": sid, "state": state, "payout": payout, "net": payout-bet, "message": "Natural blackjack! 2.5x payout."}
        return {"finished": False, "session_id": sid, "state": state}

    async def blackjack_action(self, guild_id, user_id, sid, action):
        session = await self._load_session(guild_id, user_id, sid)
        if not session or session["game"] != "blackjack" or session["status"] != "active":
            return {"error": "That blackjack table is no longer active."}
        state, bet = session["state"], session["bet"]
        if action == "hit":
            if not state["deck"]:
                state["deck"] = self._deck()
            state["player"].append(state["deck"].pop())
            total = self._hand_total(state["player"])
            if total > 21:
                await self._close_session(sid)
                return {"finished": True, "state": state, "payout": 0, "net": -bet, "message": "Bust! The dealer takes the wager."}
            await self._save_session(sid, state)
            return {"finished": False, "state": state}
        if action != "stand":
            return {"error": "Choose Hit or Stand."}
        while self._hand_total(state["dealer"]) < 17:
            if not state["deck"]:
                state["deck"] = self._deck()
            state["dealer"].append(state["deck"].pop())
        pt, dt = self._hand_total(state["player"]), self._hand_total(state["dealer"])
        if dt > 21 or pt > dt:
            payout, message = bet * 2, "You win!"
        elif pt == dt:
            payout, message = bet, "Push — your bet is returned."
        else:
            payout, message = 0, "Dealer wins."
        if payout:
            await self._credit(guild_id, user_id, payout, metadata={"game": "blackjack", "bet": bet, "payout": payout})
        await self._close_session(sid)
        return {"finished": True, "state": state, "payout": payout, "net": payout-bet, "message": message}

    async def start_mines(self, guild_id, user_id, bet, size=5, mine_count=5):
        valid, bet, error = self._clamp_bet(bet)
        if not valid:
            return {"error": error}
        ok, _, error = await self._debit(guild_id, user_id, bet, metadata={"game": "mines", "bet": bet})
        if not ok:
            return {"error": error}
        cells = list(range(size * size))
        mines = set(random.sample(cells, mine_count))
        state = {"size": size, "mine_count": mine_count, "mines": sorted(mines), "revealed": [], "multiplier": 1.0, "cashout": bet}
        sid, error = await self._create_session(guild_id, user_id, "mines", bet, state)
        if not sid:
            await self._credit(guild_id, user_id, bet, "gambling_refund", {"game": "mines"})
            return {"error": error}
        return {"finished": False, "session_id": sid, "state": state}

    async def mines_action(self, guild_id, user_id, sid, cell=None, cashout=False):
        session = await self._load_session(guild_id, user_id, sid)
        if not session or session["game"] != "mines" or session["status"] != "active":
            return {"error": "That Mines board is no longer active."}
        state, bet = session["state"], session["bet"]
        if cashout:
            payout = int(state.get("cashout", bet))
            await self._credit(guild_id, user_id, payout, metadata={"game": "mines", "bet": bet, "payout": payout, "cashout": True})
            await self._close_session(sid)
            return {"finished": True, "state": state, "payout": payout, "net": payout-bet, "message": "You cashed out safely."}
        try:
            cell = int(cell)
        except (TypeError, ValueError):
            return {"error": "Choose a board cell."}
        if cell in state["revealed"]:
            return {"error": "That tile is already open."}
        if cell in state["mines"]:
            state["revealed"].append(cell)
            await self._close_session(sid)
            return {"finished": True, "state": state, "payout": 0, "net": -bet, "message": "BOOM! You hit a mine and lost the wager."}
        state["revealed"].append(cell)
        safe_count = len(state["revealed"])
        state["multiplier"] = round(1.0 + safe_count * 0.24 + safe_count * safe_count * 0.018, 2)
        state["cashout"] = int(bet * state["multiplier"])
        if safe_count >= state["size"] * state["size"] - state["mine_count"]:
            payout = state["cashout"]
            await self._credit(guild_id, user_id, payout, metadata={"game": "mines", "bet": bet, "payout": payout, "clear": True})
            await self._close_session(sid)
            return {"finished": True, "state": state, "payout": payout, "net": payout-bet, "message": "Perfect clear! Every safe tile found."}
        await self._save_session(sid, state)
        return {"finished": False, "state": state}

    @staticmethod
    def _deck():
        deck = [rank for rank in range(2, 11) for _ in range(4)] + ["J", "Q", "K", "A"] * 4
        random.shuffle(deck)
        return deck

    @staticmethod
    def _hand_total(cards):
        total, aces = 0, 0
        for card in cards:
            if card in {"J", "Q", "K"}:
                total += 10
            elif card == "A":
                total += 11
                aces += 1
            else:
                total += int(card)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total
