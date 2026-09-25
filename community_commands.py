import ast
import io
import random
import re
import urllib.parse

import aiosqlite
import aiohttp
import discord
from discord.ext import commands

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = ImageDraw = ImageFont = None

ACTION_LINES = {
    "cuddle":"🫂 cuddles {target}.","hug":"🤗 gives {target} a big hug.","kiss":"💋 gives {target} a quick kiss.",
    "lick":"😛 gives {target} a harmless cartoon lick.","nom":"😋 nom noms near {target}.","pat":"🫳 pats {target}.",
    "poke":"👉 pokes {target}.","slap":"💥 playfully bonks {target} with a foam noodle.","stare":"👀 stares intensely at {target}.",
    "highfive":"✋ high-fives {target}!","bite":"🦷 gives {target} a tiny cartoon chomp.","greet":"👋 greets {target}.",
    "punch":"🥊 throws a cartoon pillow punch at {target}.","handholding":"🤝 holds hands with {target}.",
    "tickle":"😂 tickles {target}.","hold":"🫂 holds {target} close.","pats":"🫳🫳 gives {target} several pats.",
    "wave":"👋 waves at {target}.","boop":"👉👃 boops {target}.","snuggle":"🥰 snuggles with {target}.",
    "bully":"💀 gives {target} a friendship-grade roast.","kill":"⚔️ challenges {target} to a fictional anime duel."
}
EMOTES = {
    "blush":"😊 blushes.","cry":"😭 cries dramatically.","dance":"💃 starts dancing.","lewd":"😳 gets mischievous, then gets bonked by Horizon.",
    "pout":"😤 pouts.","shrug":"🤷 shrugs.","sleepy":"🥱 is sleepy.","smile":"😊 smiles.","smug":"😏 looks smug.",
    "thumbsup":"👍 gives a thumbs up.","wag":"🐾 wags happily.","thinking":"🤔 thinks deeply.","triggered":"💢 is triggered.",
    "teehee":"✨ giggles.","deredere":"💕 gets adorably affectionate.","thonking":"🗿 enters maximum thonk mode.",
    "scoff":"🙄 scoffs.","happy":"😄 is happy.","thumbs":"👍👍 gives two thumbs up.","grin":"😁 grins."
}
MEMES = ["spongebobchicken","slapcar","isthisa","drake","distractedbf","communismcat","eject","emergencymeeting","headpat","tradeoffer","waddle"]

async def _guard(ctx, name):
    if not ctx.guild:
        return False
    disabled = getattr(ctx.bot, "_community_disabled", {})
    if ctx.guild.id not in disabled:
        async with aiosqlite.connect(ctx.bot.db.path) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS community_settings (guild_id INTEGER PRIMARY KEY, disabled TEXT DEFAULT '')")
            cur = await db.execute("SELECT disabled FROM community_settings WHERE guild_id=?", (ctx.guild.id,))
            row = await cur.fetchone()
        disabled[ctx.guild.id] = set(filter(None, (row[0] if row else "").split(",")))
        ctx.bot._community_disabled = disabled
    if "*" in disabled[ctx.guild.id] or name in disabled[ctx.guild.id]:
        await ctx.send("🔕 !{} is disabled in this server.".format(name), delete_after=5)
        return False
    return True

async def _delete(ctx):
    try:
        await ctx.message.delete()
    except Exception:
        pass

async def _set_disabled(bot, guild_id, values):
    async with aiosqlite.connect(bot.db.path) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS community_settings (guild_id INTEGER PRIMARY KEY, disabled TEXT DEFAULT '')")
        await db.execute(
            "INSERT INTO community_settings(guild_id,disabled) VALUES(?,?) "
            "ON CONFLICT(guild_id) DO UPDATE SET disabled=excluded.disabled",
            (guild_id, ",".join(sorted(values)))
        )
        await db.commit()
    bot._community_disabled = getattr(bot, "_community_disabled", {})
    bot._community_disabled[guild_id] = set(values)

def _cmd(name, fn, help_text=""):
    return commands.Command(fn, name=name, help=help_text, description=help_text)

def _font(size, bold=False):
    if ImageFont is None:
        return None
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    try:
        return ImageFont.truetype(p, size)
    except Exception:
        return ImageFont.load_default()



# SFW anime GIF layer used by social, action, emote and meme commands.
# NEKOSBEST provides keyless SFW GIF categories such as hug, cuddle, pat,
# dance, blush, cry, happy, highfive, kiss, laugh, nom, poke, punch, shrug,
# sleep, smile, smug, stare, tickle, wag, wave, wink, etc.
GIF_API = "https://nekos.best/api/v2/{}"
GIF_HEADERS = {"User-Agent": "Horizon Discord Bot (https://github.com/bhagyam999/Horizon-AI)"}

ACTION_GIFS = {
    "cuddle":"cuddle","hug":"hug","kiss":"kiss","lick":"blush","nom":"nom","pat":"pat",
    "poke":"poke","slap":"slap","stare":"stare","highfive":"highfive","bite":"bite",
    "greet":"wave","punch":"punch","handholding":"handhold","tickle":"tickle","hold":"cuddle",
    "pats":"pat","wave":"wave","boop":"boop","snuggle":"cuddle","bully":"bonk","kill":"bonk",
    "feed":"feed","carry":"carry","bonk":"bonk","comfort":"cuddle","cheer":"happy",
    "protect":"shield","shield":"shield","fistbump":"handshake","salute":"salute","bow":"bow",
    "laughwith":"laugh","crywith":"cry","dancewith":"dance",
}
EMOTE_GIFS = {
    "blush":"blush","cry":"cry","dance":"dance","lewd":"blush","pout":"pout","shrug":"shrug",
    "sleepy":"sleep","smile":"smile","smug":"smug","thumbsup":"thumbsup","wag":"wag",
    "thinking":"think","triggered":"angry","teehee":"teehee","deredere":"happy",
    "thonking":"think","scoff":"shrug","happy":"happy","thumbs":"thumbsup","grin":"smile",
}
SOCIAL_GIFS = {
    "cookie":"feed","ship":"happy","pray":"nod","curse":"angry","marry":"handshake",
    "emoji":"happy","level":"happy","wallpaper":"smile","owoify":"wink",
    "friendship":"handshake","compatibility":"happy","couple":"handshake","duo":"highfive",
    "crush":"blush","bestie":"hug","rival":"stare","adopt":"happy","breakup":"cry","divorce":"cry",
}
MEME_GIFS = {
    "spongebobchicken":"baka","slapcar":"slap","isthisa":"confused","drake":"smug",
    "distractedbf":"stare","communismcat":"smug","eject":"yeet","emergencymeeting":"shocked",
    "headpat":"pat","tradeoffer":"handshake","waddle":"dance",
}

async def _get_gif(category):
    category = str(category or "").lower().strip()
    if not category:
        return None
    try:
        async with aiohttp.ClientSession(headers=GIF_HEADERS, timeout=aiohttp.ClientTimeout(total=6)) as session:
            async with session.get(GIF_API.format(category)) as response:
                if response.status != 200:
                    return None
                data = await response.json()
                result = (data.get("results") or [None])[0]
                if not result:
                    return None
                return {
                    "url": result.get("url"),
                    "anime": result.get("anime_name") or "Horizon GIF",
                }
    except Exception:
        return None

def _gif_embed(title, text, gif):
    e = discord.Embed(title=title, description=text, colour=discord.Colour.blurple())
    if gif and gif.get("url"):
        e.set_image(url=gif["url"])
        e.set_footer(text="Horizon GIF • {}".format(gif.get("anime","NEKOSBEST")))
    return e

def _meme(title, parts):
    if Image is None:
        return None
    img = Image.new("RGB", (1200, 700), (32, 32, 42))
    d = ImageDraw.Draw(img)
    title_font = _font(48, True)
    body_font = _font(44, True)
    small = _font(22)
    d.rounded_rectangle((25,25,1175,675), 25, outline=(120,120,150), width=4)
    d.text((55,45), title.upper(), fill=(255,220,80), font=title_font)
    box_h = max(90, 500 // max(1,len(parts)))
    for i, part in enumerate(parts[:3]):
        y = 125 + i*box_h
        d.rounded_rectangle((55,y,1145,min(y+box_h-15,640)), 18, fill=(50,50,62), outline=(90,90,110), width=2)
        text = str(part)[:120]
        while len(text) > 4 and d.textbbox((0,0), text, font=body_font)[2] > 1020:
            text = text[:-4] + "..."
        w = d.textbbox((0,0), text, font=body_font)[2]
        d.text(((1200-w)//2,y+35), text, fill=(245,245,245), font=body_font)
    d.text((55,645), "HORIZON • Community Meme Generator", fill=(150,150,165), font=small)
    out = io.BytesIO()
    img.save(out, "PNG")
    out.seek(0)
    return out

async def setup(bot):
    async with aiosqlite.connect(bot.db.path) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS community_settings (guild_id INTEGER PRIMARY KEY, disabled TEXT DEFAULT '')")
        await db.commit()

    async def add(name, fn, help_text=""):
        if not bot.get_command(name):
            bot.add_command(_cmd(name, fn, help_text))

    async def action(ctx, member: discord.Member=None):
        name = ctx.command.name
        if not await _guard(ctx, name): return
        await _delete(ctx)
        target = member.mention if member else ctx.author.mention
        text = ACTION_LINES.get(name, "interacts with {target}.").format(target=target)
        gif = await _get_gif(ACTION_GIFS.get(name))
        await ctx.send(embed=_gif_embed("✨ Horizon • {}".format(name.title()), "**{}** {}".format(ctx.author.display_name, text), gif))

    async def emote(ctx):
        name = ctx.command.name
        if not await _guard(ctx, name): return
        await _delete(ctx)
        gif = await _get_gif(EMOTE_GIFS.get(name))
        await ctx.send(embed=_gif_embed("🙂 Horizon • {}".format(name.title()), "**{}** {}".format(ctx.author.display_name, EMOTES.get(name, "emotes.")), gif))

    for name in ACTION_LINES:
        if name != "kill":
            await add(name, action, "Perform the {} action.".format(name))
    for name in EMOTES:
        await add(name, emote, "Use the {} emote.".format(name))

    async def cookie(ctx, member: discord.Member=None):
        if not await _guard(ctx,"cookie"): return
        await _delete(ctx)
        target = member.mention if member else ctx.author.mention
        gif=await _get_gif(SOCIAL_GIFS["cookie"])
        await ctx.send(embed=_gif_embed("🍪 Cookie", "**{}** gives {} a fresh cookie.".format(ctx.author.display_name,target), gif))
    await add("cookie",cookie,"Give someone a cookie.")

    async def ship(ctx, left: discord.Member=None, right: discord.Member=None):
        if not await _guard(ctx,"ship"): return
        await _delete(ctx)
        a = left or ctx.author
        candidates = [m for m in ctx.guild.members if not m.bot and m.id != a.id]
        b = right or (random.choice(candidates) if candidates else ctx.author)
        score = random.randint(0,100)
        gif=await _get_gif(SOCIAL_GIFS["ship"])
        await ctx.send(embed=_gif_embed("💞 Ship Check", "{} × {}\n**{}%** ❤️".format(a.mention,b.mention,score), gif))
    await add("ship",ship,"Calculate a playful compatibility percentage.")

    async def pray(ctx, *, reason=""):
        if not await _guard(ctx,"pray"): return
        await _delete(ctx)
        gif=await _get_gif(SOCIAL_GIFS["pray"])
        await ctx.send(embed=_gif_embed("🙏 Prayer", "**{}** prays{}. May the RNG be kind.".format(ctx.author.display_name,(" for "+reason) if reason else ""), gif))
    await add("pray",pray,"Pray to the RNG gods.")

    async def curse(ctx, member: discord.Member=None, *, reason=""):
        if not await _guard(ctx,"curse"): return
        await _delete(ctx)
        target = member.mention if member else ctx.author.mention
        gif=await _get_gif(SOCIAL_GIFS["curse"])
        await ctx.send(embed=_gif_embed("🔮 Curse", "**{}** places a fictional curse on {}{}.".format(ctx.author.display_name,target,(" — "+reason) if reason else ""), gif))
    await add("curse",curse,"Playfully curse a member.")

    async def marry(ctx, member: discord.Member=None):
        if not await _guard(ctx,"marry"): return
        await _delete(ctx)
        if not member or member.id == ctx.author.id:
            await ctx.send("💍 Use !marry @member to send a playful proposal.",delete_after=6); return
        gif=await _get_gif(SOCIAL_GIFS["marry"])
        await ctx.send(embed=_gif_embed("💍 Proposal", "**{}** proposes to {}! Do they accept? 💕".format(ctx.author.display_name,member.mention), gif))
    await add("marry",marry,"Send a playful marriage proposal.")

    async def emoji(ctx, *, name=""):
        if not await _guard(ctx,"emoji"): return
        await _delete(ctx)
        pool=["😀","😂","😭","😎","🤨","😳","🥹","😈","🤔","🗿","✨","🔥","💀","🫂","💖","🐉","⚔️","🌌"]
        aliases={"happy":"😄","sad":"😢","love":"❤️","fire":"🔥","skull":"💀","think":"🤔","cool":"😎"}
        await ctx.send(aliases.get(name.lower().strip()," ".join(random.sample(pool,8))) if name else " ".join(random.sample(pool,8)))
    await add("emoji",emoji,"Show a random emoji.")

    async def level(ctx, member: discord.Member=None):
        if not await _guard(ctx,"level"): return
        await _delete(ctx)
        target=member or ctx.author
        p=await bot.db.profile(ctx.guild.id,target.id)
        xp=int(p.get("xp",0)); lvl=xp//100+1
        await ctx.send("✨ **{}** — Level **{}**\nXP: **{} / {}**".format(target.display_name,lvl,xp,lvl*100))
    await add("level",level,"Show a member's Horizon level.")

    async def wallpaper(ctx, *, query=""):
        if not await _guard(ctx,"wallpaper"): return
        await _delete(ctx)
        q=urllib.parse.quote(query.strip() or "anime wallpaper")
        await ctx.send("🖼️ Wallpaper search: https://unsplash.com/s/photos/{}".format(q))
    await add("wallpaper",wallpaper,"Search for a wallpaper.")

    async def owoify(ctx, *, text=""):
        if not await _guard(ctx,"owoify"): return
        await _delete(ctx)
        if not text.strip():
            await ctx.send("Usage: !owoify <text>",delete_after=6); return
        out=re.sub(r"[rl]","w",text,flags=re.I)
        out=re.sub(r"n([aeiou])",r"ny\1",out,flags=re.I)
        await ctx.send("**OwO:** {}".format(out[:1900]))
    await add("owoify",owoify,"OwOify text.")

    async def eightball(ctx, *, question=""):
        if not await _guard(ctx,"8b"): return
        await _delete(ctx)
        answers=["It is certain.","Without a doubt.","Most likely.","Ask again later.","Maybe.","Don't count on it.","Very unlikely.","The RNG says no."]
        await ctx.send("🎱 **8-Ball:** {}".format(random.choice(answers)))
    await add("8b",eightball,"Ask the magic 8-ball.")

    async def define(ctx, *, word=""):
        if not await _guard(ctx,"define"): return
        await _delete(ctx)
        if not word.strip():
            await ctx.send("Usage: !define <word>",delete_after=6); return
        url="https://api.dictionaryapi.dev/api/v2/entries/en/"+urllib.parse.quote(word.split()[0])
        result=None
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=6)) as s:
                async with s.get(url) as r:
                    if r.status==200:
                        data=await r.json()
                        defs=data[0].get("meanings",[])
                        if defs and defs[0].get("definitions"):
                            result=defs[0]["definitions"][0].get("definition")
        except Exception:
            pass
        await ctx.send("📖 **{}**\n{}".format(word,result or "Definition lookup is unavailable right now."))
    await add("define",define,"Look up a dictionary definition.")

    async def gif(ctx, *, query=""):
        if not await _guard(ctx,"gif"): return
        await _delete(ctx)
        await ctx.send("🎞️ GIF search: https://tenor.com/search/{}-gifs".format(urllib.parse.quote(query or "anime")))
    await add("gif",gif,"Search for a GIF.")

    async def pic(ctx, *, query=""):
        if not await _guard(ctx,"pic"): return
        await _delete(ctx)
        await ctx.send("🖼️ Picture search: https://www.google.com/search?tbm=isch&q={}".format(urllib.parse.quote(query or "anime")))
    await add("pic",pic,"Search for a picture.")

    async def translate(ctx, target="en", *, text=""):
        if not await _guard(ctx,"translate"): return
        await _delete(ctx)
        if not text.strip():
            await ctx.send("Usage: !translate <language> <text>",delete_after=6); return
        result=None
        try:
            url="https://api.mymemory.translated.net/get?"+urllib.parse.urlencode({"q":text,"langpair":"en|"+target})
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=7)) as s:
                async with s.get(url) as r:
                    if r.status==200:
                        result=(await r.json()).get("responseData",{}).get("translatedText")
        except Exception:
            pass
        await ctx.send("🌐 **{}** — {}".format(target.upper(),result or "Translation unavailable right now."))
    await add("translate",translate,"Translate text.")

    async def roll(ctx, sides=100):
        if not await _guard(ctx,"roll"): return
        await _delete(ctx)
        try: sides=max(2,min(1000000,int(sides)))
        except Exception: sides=100
        await ctx.send("🎲 **{}** rolled **{} / {}**.".format(ctx.author.display_name,random.randint(1,sides),sides))
    await add("roll",roll,"Roll a die. Default d100.")

    async def choose(ctx, *, choices=""):
        if not await _guard(ctx,"choose"): return
        await _delete(ctx)
        items=[x.strip() for x in re.split(r"\s*\|\s*|\s*,\s*",choices) if x.strip()]
        if len(items)<2:
            await ctx.send("Usage: !choose pizza | ramen | curry",delete_after=6); return
        await ctx.send("🎯 I choose: **{}**".format(random.choice(items)))
    await add("choose",choose,"Choose randomly between options.")

    async def bell(ctx):
        if not await _guard(ctx,"bell"): return
        await _delete(ctx); await ctx.send("🔔 **Ding ding!** Horizon bell rung.")
    await add("bell",bell,"Ring the Horizon bell.")

    async def slots(ctx):
        if not await _guard(ctx,"slots"): return
        await _delete(ctx)
        s=[random.choice(["🍒","🍋","🔔","⭐","💎","7️⃣"]) for _ in range(3)]
        await ctx.send("🎰 **SLOTS**\n{}\n**{}**".format(" | ".join(s),"JACKPOT! 🎉" if len(set(s))==1 else "No match — spin again."))
    await add("slots",slots,"Play slots.")

    async def coinflip(ctx, choice=""):
        if not await _guard(ctx,"coinflip"): return
        await _delete(ctx)
        result=random.choice(["heads","tails"])
        if choice.lower() in {"h","heads","t","tails"}:
            won=(choice.lower().startswith("h") and result=="heads") or (choice.lower().startswith("t") and result=="tails")
            await ctx.send("🪙 **{}!** You **{}** the guess.".format(result.title(),"won" if won else "lost"))
        else: await ctx.send("🪙 **{}!**".format(result.title()))
    await add("coinflip",coinflip,"Flip a coin.")

    async def lottery(ctx):
        if not await _guard(ctx,"lottery"): return
        await _delete(ctx)
        await ctx.send("🎟️ **Horizon Lottery**\nNumbers: **{}**\nLucky: **{}**".format(", ".join(map(str,sorted(random.sample(range(1,50),6)))),random.randint(1,49)))
    await add("lottery",lottery,"Draw a lottery ticket.")

    async def blackjack(ctx):
        if not await _guard(ctx,"blackjack"): return
        await _delete(ctx)
        card=lambda:[random.randint(2,11),random.randint(2,11)]
        score=lambda x:sum(x)
        p=card(); d=card()
        while score(p)<17:p.append(random.randint(2,11))
        while score(d)<17:d.append(random.randint(2,11))
        ps,ds=score(p),score(d)
        outcome="You bust." if ps>21 else "Dealer busts — you win!" if ds>21 else "You win!" if ps>ds else "Draw." if ps==ds else "Dealer wins."
        await ctx.send("🃏 **Blackjack**\nYou: {} = **{}**\nDealer: {} = **{}**\n**{}**".format(p,ps,d,ds,outcome))
    await add("blackjack",blackjack,"Play a quick blackjack round.")

    async def snailgarden(ctx):
        if not await _guard(ctx,"snailgarden"): return
        await _delete(ctx)
        await ctx.send("🐌 **Snail Garden**\nMeet **{}**. It is currently **{}**.\n🐌...".format(random.choice(["Turbo","Shelly","Mochi","Noodle","Speedy"]),random.choice(["sleepy","hungry","zooming","vibing","plotting"])))
    await add("snailgarden",snailgarden,"Visit the snail garden.")

    async def mines(ctx, square=""):
        if not await _guard(ctx,"mines"): return
        await _delete(ctx)
        safe=random.randint(0,8)
        if square.isdigit() and 0<=int(square)<=8:
            await ctx.send("💣 **Mines**\n0 1 2\n3 4 5\n6 7 8\n{}".format("💎 SAFE! You found the gem." if int(square)==safe else "💥 BOOM! You hit a mine."))
        else: await ctx.send("💣 Pick a square from 0 to 8.")
    await add("mines",mines,"Play a tiny 3x3 mines game.")

    async def highlow(ctx, guess=""):
        if not await _guard(ctx,"highlow"): return
        await _delete(ctx)
        a,b=random.randint(1,13),random.randint(1,13)
        actual="same" if a==b else "high" if b>a else "low"
        if guess.lower()[:1] not in {"h","l","s"}:
            await ctx.send("⬆️⬇️ Current card: **{}**. Guess high, low, or same.".format(a),delete_after=7); return
        await ctx.send("⬆️⬇️ **{} → {}** — **{}** ({})".format(a,b,"WIN" if guess.lower()[0]==actual[0] else "LOSE",actual))
    await add("highlow",highlow,"Play high/low.")

    async def meme(ctx, *, raw=""):
        name=ctx.command.name
        if not await _guard(ctx,name): return
        await _delete(ctx)
        parts=[x.strip() for x in raw.split("|") if x.strip()]
        if not parts:
            await ctx.send("Usage: !{} top | bottom".format(name),delete_after=7); return
        image=_meme(name.replace("distractedbf","distracted boyfriend"),parts[:3])
        gif=await _get_gif(MEME_GIFS.get(name, "laugh"))
        if image:
            embed=_gif_embed("😂 Horizon • {}".format(name.title()), "Reaction GIF • {}" .format(gif.get("anime","Horizon") if gif else "Horizon"), gif)
            await ctx.send(file=discord.File(image,filename="horizon_{}.png".format(name)), embed=embed)
        else:
            if gif:
                await ctx.send(embed=embed)
            else:
                await ctx.send("Meme generation is unavailable.",delete_after=7)
    for name in MEMES:
        await add(name,meme,"Generate a {} meme.".format(name))

    async def stats(ctx, member: discord.Member=None):
        if not await _guard(ctx,"stats"): return
        await _delete(ctx)
        target=member or ctx.author; p=await bot.db.profile(ctx.guild.id,target.id); xp=int(p["xp"])
        await ctx.send("📊 **{}**\nXP: **{}**\nLevel: **{}**\nCoins: **{}**\nWarnings: **{}**".format(target.display_name,xp,xp//100+1,p["coins"],p["warnings"]))
    await add("stats",stats,"Show profile stats.")

    async def link(ctx):
        if not await _guard(ctx,"link"): return
        await _delete(ctx)
        try: inv=await ctx.channel.create_invite(max_age=0,max_uses=0,unique=False,reason="Horizon link")
        except discord.Forbidden: await ctx.send("🔗 I need Create Invite permission."); return
        await ctx.send("🔗 **Server Invite:** {}".format(inv.url))
    await add("link",link,"Create a permanent server invite.")

    async def guildlink(ctx):
        if not await _guard(ctx,"guildlink"): return
        await _delete(ctx)
        try: inv=await ctx.channel.create_invite(max_age=86400,max_uses=0,unique=False,reason="Horizon guild link")
        except discord.Forbidden: await ctx.send("🌐 I need Create Invite permission."); return
        await ctx.send("🌐 **Guild Link (24h):** {}".format(inv.url))
    await add("guildlink",guildlink,"Create a 24-hour invite.")

    async def disable(ctx, command=""):
        if not ctx.guild or not ctx.author.guild_permissions.manage_guild:
            await ctx.send("You need Manage Server to use this.",delete_after=6); return
        await _delete(ctx)
        name=command.lower().strip().lstrip("!")
        if not name:
            await ctx.send("Usage: !disable <command> or !disable all",delete_after=7); return
        current=set(getattr(bot,"_community_disabled",{}).get(ctx.guild.id,set()))
        if name=="all": current={"*"}
        else: current.discard("*"); current.add(name)
        await _set_disabled(bot,ctx.guild.id,current)
        await ctx.send("🔕 Disabled **{}**.".format(name))
    await add("disable",disable,"Disable a community command.")

    async def enable(ctx, command=""):
        if not ctx.guild or not ctx.author.guild_permissions.manage_guild:
            await ctx.send("You need Manage Server to use this.",delete_after=6); return
        await _delete(ctx)
        name=command.lower().strip().lstrip("!")
        current=set(getattr(bot,"_community_disabled",{}).get(ctx.guild.id,set()))
        if name=="all": current.clear()
        else: current.discard(name)
        await _set_disabled(bot,ctx.guild.id,current)
        await ctx.send("🔔 Enabled **{}**.".format(name or "community commands"))
    await add("enable",enable,"Re-enable a community command.")

    async def censor(ctx, *, text=""):
        if not await _guard(ctx,"censor"): return
        await _delete(ctx)
        if not text.strip(): await ctx.send("Usage: !censor <text>",delete_after=6); return
        await ctx.send("🫥 {}".format("".join("█" if c.isalpha() and i%3==1 else c for i,c in enumerate(text))[:1900]))
    await add("censor",censor,"Censor part of a message.")

    async def patreon(ctx):
        if not await _guard(ctx,"patreon"): return
        await _delete(ctx); await ctx.send("💜 No Patreon/support page is configured for Horizon yet.")
    await add("patreon",patreon,"Show Patreon/support information.")

    async def announcement(ctx, *, text=""):
        if not await _guard(ctx,"announcement"): return
        await _delete(ctx)
        if not text.strip(): await ctx.send("Usage: !announcement <text>",delete_after=6); return
        e=discord.Embed(title="📢 Horizon Announcement",description=text[:4000],colour=discord.Colour.blurple())
        e.set_footer(text="Posted by {}".format(ctx.author.display_name)); await ctx.send(embed=e)
    await add("announcement",announcement,"Post a simple announcement.")

    async def rules(ctx):
        if not await _guard(ctx,"rules"): return
        await _delete(ctx)
        await ctx.send("📜 **Horizon Rules**\n1. Respect members.\n2. No harassment or spam.\n3. Keep channels on-topic.\n4. Follow Discord and server rules.\n5. Have fun without ruining someone else's fun.")
    await add("rules",rules,"Show community rules.")

    async def suggest(ctx, *, text=""):
        if not await _guard(ctx,"suggest"): return
        await _delete(ctx)
        if not text.strip(): await ctx.send("Usage: !suggest <idea>",delete_after=6); return
        e=discord.Embed(title="💡 New Suggestion",description=text[:4000],colour=discord.Colour.gold())
        e.set_author(name=ctx.author.display_name,icon_url=ctx.author.display_avatar.url)
        m=await ctx.send(embed=e)
        for x in ("👍","👎"):
            try: await m.add_reaction(x)
            except discord.HTTPException: pass
    await add("suggest",suggest,"Post a suggestion.")

    async def shards(ctx):
        if not await _guard(ctx,"shards"): return
        await _delete(ctx)
        try:
            p=await bot.rpg.player(ctx.guild.id,ctx.author.id)
            if p: await ctx.send("💠 **Shards/Diamonds:** {:,}".format(int(p.get("gems",0)))); return
        except Exception: pass
        await ctx.send("💠 Start an RPG hero first with !rpg start.")
    await add("shards",shards,"Show RPG shards/diamonds.")

    async def math_cmd(ctx, *, expression=""):
        if not await _guard(ctx,"math"): return
        await _delete(ctx)
        try:
            tree=ast.parse(expression.replace("^","**"),mode="eval")
            allowed=(ast.Expression,ast.BinOp,ast.UnaryOp,ast.Add,ast.Sub,ast.Mult,ast.Div,ast.FloorDiv,ast.Mod,ast.Pow,ast.USub,ast.UAdd,ast.Constant,ast.Load)
            if not all(isinstance(n,allowed) for n in ast.walk(tree)): raise ValueError("Only basic arithmetic is allowed.")
            result=eval(compile(tree,"<math>","eval"),{"__builtins__":{}},{})
            await ctx.send("🧮 **{}**".format(result))
        except Exception as exc: await ctx.send("🧮 Invalid expression: {}".format(exc),delete_after=7)
    await add("math",math_cmd,"Calculate basic arithmetic.")

    async def color(ctx, value="#5865F2"):
        if not await _guard(ctx,"color"): return
        await _delete(ctx)
        raw=value.strip().lstrip("#")
        if not re.fullmatch(r"[0-9a-fA-F]{6}",raw):
            await ctx.send("Usage: !color #5865F2",delete_after=6); return
        e=discord.Embed(title="#"+raw.upper(),description="Hex: #"+raw.upper(),colour=discord.Colour(int(raw,16)))
        await ctx.send(embed=e)
    await add("color",color,"Preview a hex color.")

    # -------------------- Expanded Horizon community pack --------------------
    EXTRA_ACTIONS = {
        "feed": "🍰 feeds {target} a little snack.",
        "carry": "🏋️ carries {target} like an anime protagonist.",
        "bonk": "🔨 bonks {target} with the official Horizon bonk hammer.",
        "comfort": "🫂 comforts {target}. Everything will be okay.",
        "cheer": "📣 cheers for {target}!",
        "protect": "🛡️ stands between danger and {target}.",
        "shield": "🛡️ gives {target} a temporary friendship shield.",
        "fistbump": "👊 fist-bumps {target}.",
        "salute": "🫡 salutes {target}.",
        "bow": "🙇 bows respectfully to {target}.",
        "laughwith": "😂 laughs together with {target}.",
        "crywith": "😭 cries together with {target}.",
        "dancewith": "💃🕺 dances with {target}.",
    }

    async def extra_action(ctx, member: discord.Member=None):
        name = ctx.command.name
        if not await _guard(ctx, name): return
        await _delete(ctx)
        target = member.mention if member else ctx.author.mention
        await ctx.send("**{}** {}".format(ctx.author.display_name, EXTRA_ACTIONS[name].format(target=target)))

    for name in EXTRA_ACTIONS:
        await add(name, extra_action, "Perform the {} action.".format(name))

    async def relationship(ctx, left: discord.Member=None, right: discord.Member=None, *, mode="friendship"):
        name = ctx.command.name
        if not await _guard(ctx, name): return
        await _delete(ctx)
        a = left or ctx.author
        candidates = [m for m in ctx.guild.members if not m.bot and m.id != a.id]
        b = right or (random.choice(candidates) if candidates else ctx.author)
        score = random.randint(1,100)
        labels = {
            "friendship": ("🤝 Friendship Check", "friendship"),
            "compatibility": ("💞 Compatibility Check", "compatibility"),
            "couple": ("💖 Couple Check", "couple potential"),
            "duo": ("⚔️ Duo Check", "duo synergy"),
        }
        title, label = labels.get(name, ("💫 Relationship Check", "connection"))
        gif=await _get_gif(SOCIAL_GIFS.get(name, "happy"))
        await ctx.send(embed=_gif_embed(title, "{} × {}\n**{}% {}**".format(a.mention, b.mention, score, label), gif))

    for name in ("friendship", "compatibility", "couple", "duo"):
        await add(name, relationship, "Generate a playful {} result.".format(name))

    async def crush(ctx, member: discord.Member=None):
        if not await _guard(ctx,"crush"): return
        await _delete(ctx)
        target = member
        if not target:
            candidates=[m for m in ctx.guild.members if not m.bot and m.id != ctx.author.id]
            target=random.choice(candidates) if candidates else ctx.author
        gif=await _get_gif(SOCIAL_GIFS["crush"])
        await ctx.send(embed=_gif_embed("💘 Crush Detector", "{} has a fictional server crush on **{}**. 💕".format(ctx.author.mention,target.display_name), gif))
    await add("crush",crush,"Reveal a playful fictional crush.")

    async def bestie(ctx, member: discord.Member=None):
        if not await _guard(ctx,"bestie"): return
        await _delete(ctx)
        target=member
        if not target:
            candidates=[m for m in ctx.guild.members if not m.bot and m.id != ctx.author.id]
            target=random.choice(candidates) if candidates else ctx.author
        gif=await _get_gif(SOCIAL_GIFS["bestie"])
        await ctx.send(embed=_gif_embed("👯 Bestie Check", "{} and {} are now certified besties. 🤝".format(ctx.author.mention,target.mention), gif))
    await add("bestie",bestie,"Declare a playful best-friend pairing.")

    async def rival(ctx, member: discord.Member=None):
        if not await _guard(ctx,"rival"): return
        await _delete(ctx)
        target=member
        if not target:
            candidates=[m for m in ctx.guild.members if not m.bot and m.id != ctx.author.id]
            target=random.choice(candidates) if candidates else ctx.author
        gif=await _get_gif(SOCIAL_GIFS["rival"])
        await ctx.send(embed=_gif_embed("⚔️ Rivalry Detected", "{} vs {} — the anime arc begins.".format(ctx.author.mention,target.mention), gif))
    await add("rival",rival,"Create a playful rivalry.")

    async def adopt(ctx, member: discord.Member=None):
        if not await _guard(ctx,"adopt"): return
        await _delete(ctx)
        target=member
        if not target:
            candidates=[m for m in ctx.guild.members if not m.bot and m.id != ctx.author.id]
            target=random.choice(candidates) if candidates else ctx.author
        gif=await _get_gif(SOCIAL_GIFS["adopt"])
        await ctx.send(embed=_gif_embed("🧸 Adoption Papers", "{} has been adopted by {}. Family unlocked. 💖".format(target.mention,ctx.author.mention), gif))
    await add("adopt",adopt,"Create a playful adoption pairing.")

    async def breakup(ctx, member: discord.Member=None):
        if not await _guard(ctx,"breakup"): return
        await _delete(ctx)
        target=member or ctx.author
        gif=await _get_gif(SOCIAL_GIFS["breakup"])
        await ctx.send(embed=_gif_embed("💔 Breakup Arc", "{} and {} have entered the dramatic anime separation episode.".format(ctx.author.mention,target.mention), gif))
    await add("breakup",breakup,"Start a fictional breakup scene.")

    async def divorce(ctx, member: discord.Member=None):
        if not await _guard(ctx,"divorce"): return
        await _delete(ctx)
        target=member or ctx.author
        gif=await _get_gif(SOCIAL_GIFS["divorce"])
        await ctx.send(embed=_gif_embed("📜 Divorce Papers", "{} and {} are officially divorced in the fictional Horizon universe.".format(ctx.author.mention,target.mention), gif))
    await add("divorce",divorce,"End a fictional marriage.")

    async def truth(ctx):
        if not await _guard(ctx,"truth"): return
        await _delete(ctx)
        truths=["What is the weirdest thing you have ever searched?","Who was your first fictional crush?","What game could you play for 100 hours?","What is one harmless secret you have?"]
        await ctx.send("🟦 **Truth:** {}".format(random.choice(truths)))
    await add("truth",truth,"Get a random truth question.")

    async def dare(ctx):
        if not await _guard(ctx,"dare"): return
        await _delete(ctx)
        dares=["Send a completely random emoji.","Change your status to something silly for 5 minutes.","Compliment the next person who talks.","Type your next message without using the letter e."]
        await ctx.send("🟥 **Dare:** {}".format(random.choice(dares)))
    await add("dare",dare,"Get a random harmless dare.")

    async def wyr(ctx):
        if not await _guard(ctx,"wyr"): return
        await _delete(ctx)
        rounds=[
            ("be able to teleport anywhere","be able to fly anywhere"),
            ("have infinite money","have infinite free time"),
            ("live in your favorite anime","live in your favorite game"),
            ("master every instrument","master every language"),
        ]
        a,b=random.choice(rounds)
        await ctx.send("🤔 **Would You Rather?**\nA) {}\nB) {}\n\nReply with **A** or **B**.".format(a,b))
    await add("wyr",wyr,"Get a random Would You Rather.")

    async def rate(ctx, member: discord.Member=None):
        if not await _guard(ctx,"rate"): return
        await _delete(ctx)
        target=member or ctx.author
        score=random.randint(1,100)
        await ctx.send("⭐ **Horizon Rating:** {} gets **{}/100** today.".format(target.mention,score))
    await add("rate",rate,"Give a random playful rating.")

    async def judge(ctx, *, thing=""):
        if not await _guard(ctx,"judge"): return
        await _delete(ctx)
        if not thing.strip():
            await ctx.send("Usage: !judge <thing>",delete_after=6); return
        verdict=random.choice(["Approved by the Council.","Suspicious, but acceptable.","Absolutely chaotic.","Certified Horizon moment.","The Council needs more evidence.","10/10 nonsense."])
        await ctx.send("⚖️ **Horizon Court**\n**{}**\n{}".format(thing[:500],verdict))
    await add("judge",judge,"Give a playful verdict.")

    async def roast(ctx, member: discord.Member=None):
        if not await _guard(ctx,"roast"): return
        await _delete(ctx)
        target=member or ctx.author
        lines=["You have the confidence of a final boss and the strategy of an NPC.","Your Wi-Fi has better decision-making than you.","Even the tutorial is asking you to slow down.","You are not late; you are on your own timezone."]
        await ctx.send("🔥 **Roast for {}:** {}".format(target.mention,random.choice(lines)))
    await add("roast",roast,"Give a harmless playful roast.")

    async def compliment(ctx, member: discord.Member=None):
        if not await _guard(ctx,"compliment"): return
        await _delete(ctx)
        target=member or ctx.author
        lines=["You make the server more fun to be around.","Your energy is genuinely nice to have here.","You have main-character levels of determination.","You deserve a small W today."]
        await ctx.send("💙 **Compliment for {}:** {}".format(target.mention,random.choice(lines)))
    await add("compliment",compliment,"Give a positive compliment.")

    async def fortune(ctx):
        if not await _guard(ctx,"fortune"): return
        await _delete(ctx)
        await ctx.send("🔮 **Horizon Fortune:** {}".format(random.choice(["A lucky roll is coming.","Someone will make you laugh today.","Your next idea will be better than expected.","A tiny victory is closer than it looks.","The RNG is watching. Be brave."])))
    await add("fortune",fortune,"Reveal a random fortune.")

    async def dice(ctx, count=1, sides=6):
        if not await _guard(ctx,"dice"): return
        await _delete(ctx)
        try:
            count=max(1,min(20,int(count))); sides=max(2,min(1000,int(sides)))
        except Exception:
            count,sides=1,6
        rolls=[random.randint(1,sides) for _ in range(count)]
        await ctx.send("🎲 **Dice:** {} → **{}**".format(" + ".join(map(str,rolls)),sum(rolls)))
    await add("dice",dice,"Roll one or more dice.")

    async def pick(ctx, *, choices=""):
        if not await _guard(ctx,"pick"): return
        await _delete(ctx)
        items=[x.strip() for x in re.split(r"\s*\|\s*|\s*,\s*",choices) if x.strip()]
        if len(items)<2:
            await ctx.send("Usage: !pick pizza | ramen | curry",delete_after=6); return
        await ctx.send("🎯 **Horizon Pick:** {}".format(random.choice(items)))
    await add("pick",pick,"Pick one option at random.")

    async def random_cmd(ctx, *, text=""):
        if not await _guard(ctx,"random"): return
        await _delete(ctx)
        if not text.strip():
            await ctx.send("🎲 **Random:** {}".format(random.randint(1,100)))
            return
        items=[x.strip() for x in re.split(r"\s*\|\s*|\s*,\s*",text) if x.strip()]
        if len(items)<2:
            await ctx.send("Usage: !random one | two | three",delete_after=6); return
        await ctx.send("🎲 **Random choice:** {}".format(random.choice(items)))
    await add("random",random_cmd,"Choose randomly from options.")

    async def prefix(ctx):
        if not await _guard(ctx,"prefix"): return
        await _delete(ctx)
        await ctx.send("⌨️ **Horizon Prefix:** !")
    await add("prefix",prefix,"Show the current prefix.")
