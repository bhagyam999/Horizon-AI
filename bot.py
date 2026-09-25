import asyncio        await bot.db.set_setting(ctx.guild.id, "prefix", value)
        bot.prefix_cache[ctx.guild.id] = value
        await ctx.send(f"✅ Horizon's prefix for **{ctx.guild.name}** is now `{value}`." if value != "!" else f"✅ Horizon's prefix has been reset to `!`.")


@bot.command(name="8ball", aliases=["eightball"])
async def prefix_8ball(ctx, *, question: str = ""):
    await _quiet_delete(ctx.message)
    if not question.strip():
        await ctx.send("🎱 Ask me a yes/no question.", delete_after=7)
        return
    answers = ["It is certain.", "Without a doubt.", "Most likely.", "Signs point to yes.",
               "Ask again later.", "The answer is unclear.", "Probably not.", "Very doubtful."]
    await ctx.send(f"🎱 **8-Ball:** {random.choice(answers)}")

@bot.command(name="coinflip", aliases=["coin"])
async def prefix_coinflip(ctx):
    await _quiet_delete(ctx.message)
    await ctx.send(f"🪙 **{random.choice(['Heads', 'Tails'])}**")

@bot.command(name="roll")
async def prefix_roll(ctx, sides: int = 100):
    await _quiet_delete(ctx.message)
    sides = max(2, min(int(sides), 100000))
    await ctx.send(f"🎲 **{ctx.author.display_name}** rolled **{random.randint(1, sides)}** / {sides}")

@bot.command(name="choose")
async def prefix_choose(ctx, *, choices: str = ""):
    await _quiet_delete(ctx.message)
    options = [x.strip() for x in choices.split("|") if x.strip()]
    if len(options) < 2:
        await ctx.send("Use !choose option 1 | option 2 | option 3.", delete_after=8)
        return
    await ctx.send(f"🎯 I choose **{random.choice(options)}**")

@bot.command(name="ship")
async def prefix_ship(ctx, member1: discord.Member = None, member2: discord.Member = None):
    await _quiet_delete(ctx.message)
    if member1 is None:
        member1 = ctx.author
    if member2 is None:
        await ctx.send("Use !ship @user @user or !ship @user.", delete_after=8)
        return
    score = random.randint(0, 100)
    hearts = "❤️" * max(1, min(10, score // 10))
    await ctx.send(f"💞 **{member1.display_name} × {member2.display_name}**\n{hearts} **{score}%** compatibility")

ACTION_RESPONSES = {
    "hug": ("🤗", "{a} gives {b} a warm hug."),
    "pat": ("🫳", "{a} pats {b} on the head."),
    "highfive": ("✋", "{a} high-fives {b}!"),
    "slap": ("👋", "{a} gives {b} a playful slap."),
    "poke": ("👉", "{a} pokes {b}."),
    "wave": ("👋", "{a} waves at everyone!"),
}
EMOTE_RESPONSES = {
    "dance": ("💃", "{a} starts dancing."),
    "shrug": ("🤷", "{a} shrugs."),
    "blush": ("😊", "{a} blushes."),
    "cry": ("😢", "{a} starts crying."),
    "smug": ("😏", "{a} looks smug."),
    "think": ("🤔", "{a} is thinking."),
}

def _make_action_command(name, icon, template, needs_member=False):
    async def action(ctx, member: discord.Member = None):
        await _quiet_delete(ctx.message)
        if needs_member and member is None:
            await ctx.send(f"Use !{name} @user.", delete_after=7)
            return
        target = member.mention if member else "everyone"
        await ctx.send(f"{icon} " + template.format(a=ctx.author.mention, b=target))
    action.__name__ = f"prefix_{name}"
    bot.command(name=name)(action)

for _name, (_icon, _template) in ACTION_RESPONSES.items():
    _make_action_command(_name, _icon, _template, _name not in {"wave"})
for _name, (_icon, _template) in EMOTE_RESPONSES.items():
    _make_action_command(_name, _icon, _template, False)

@bot.command(name="meme")
async def prefix_meme(ctx):
    await _quiet_delete(ctx.message)
    memes = [
        "When the code works on the first try: **impossible.**",
        "Me: I'll fix one bug.\nThe bug: *summons three more bugs.*",
        "Horizon RPG players: *just one more quest.*\nAlso Horizon RPG: **here are twelve.**",
        "Discord at 3 AM: **perfectly reasonable time to deploy.**",
        "Developer: it's a small change.\nThe database: **oh no.**",
    ]
    await ctx.send(f"😂 {random.choice(memes)}")

@bot.command(name="ping")
async def prefix_ping(ctx):
    await _quiet_delete(ctx.message)
    await ctx.send(f"🏓 Pong! `{round(bot.latency * 1000)} ms`", delete_after=10)


@bot.command(name="sync")
@commands.is_owner()
async def prefix_sync(ctx, scope: str = "guild"):
    """Manually register slash commands without blocking bot startup."""
    await _quiet_delete(ctx.message)
    scope = scope.lower().strip()
    if scope not in {"guild", "global"}:
        await ctx.send("Usage: `!sync guild` or `!sync global`", delete_after=10)
        return
    try:
        async with ctx.typing():
            await bot._sync_commands_safely(global_sync=(scope == "global"))
        target = "globally" if scope == "global" else "to the configured server"
        await ctx.send(f"Slash commands synced {target}.", delete_after=15)
    except discord.HTTPException as exc:
        retry = getattr(exc, "retry_after", None)
        if retry:
            await ctx.send(f"Discord rate-limited command sync. Try again after about {retry:.0f}s. The bot itself is still online.", delete_after=20)
        else:
            await ctx.send(f"Command sync failed: `{exc}`. The bot itself is still online.", delete_after=20)
    except Exception as exc:
        log.exception("Manual slash-command sync failed.")
        await ctx.send(f"Command sync failed: `{exc}`. The bot itself is still online.", delete_after=20)


@bot.command(name="ask")
async def prefix_ask(ctx, *, question: str = ""):
    await _quiet_delete(ctx.message)
    if not question.strip():
        await ctx.send("Use `!ask <question>`.", delete_after=6); return
    async with ctx.typing():
        try:
            answer = await ai_reply(ctx.guild.id, ctx.author.id, ctx.author.display_name, question.strip(), ctx.channel.id)
            for chunk in split_text(answer): await ctx.send(chunk)
        except Exception:
            log.exception("Prefix ask failed")
            await ctx.send("Horizon AI is temporarily unavailable.", delete_after=8)


@bot.command(name="aistatus", aliases=["ai-status"])
async def prefix_ai_status(ctx):
    await _quiet_delete(ctx.message)
    try:
        ok, detail = await bot.ai.status()
        # Discord caps normal message content at 2000 characters. Model health can
        # contain many models, so always split it instead of letting this command fail.
        chunks = split_text(f"**Horizon AI:** {'Online' if ok else 'Offline'}\n{detail}", 1900)
        for chunk in chunks:
            await ctx.send(chunk, delete_after=15)
    except Exception as exc:
        log.exception("AI status failed")
        await ctx.send(f"AI status failed: {str(exc)[:300]}", delete_after=12)


@bot.command(name="aimodels", aliases=["ai_models"])
async def prefix_ai_models(ctx):
    await _quiet_delete(ctx.message)
    try:
        names = await bot.ai.gemini.model_names()
        usable = [n for n in names if "gemini" in n.lower()]
        await ctx.send("**Gemini models visible to Horizon:**\n" + ("\n".join(f"• `{n}`" for n in usable[:40]) or "No Gemini models returned."))
    except Exception:
        await ctx.send("I couldn't retrieve the model list right now.", delete_after=8)


@bot.command(name="personality")
@commands.has_guild_permissions(manage_guild=True)
async def prefix_personality(ctx, *, personality: str = ""):
    await _quiet_delete(ctx.message)
    if not personality.strip():
        await ctx.send("Use `!personality <how Horizon should behave>`.", delete_after=6); return
    await bot.db.set_setting(ctx.guild.id, "personality", personality.strip())
    await ctx.send("Horizon server personality updated.", delete_after=7)


@bot.command(name="remember")
@commands.has_guild_permissions(manage_guild=True)
async def prefix_remember(ctx, *, fact: str = ""):
    await _quiet_delete(ctx.message)
    if not fact.strip():
        await ctx.send("Use `!remember <server fact>`.", delete_after=6); return
    await bot.db.add_memory(ctx.guild.id, fact.strip(), ctx.author.id)
    await ctx.send("Saved to Horizon server knowledge.", delete_after=7)


@bot.command(name="forget")
@commands.has_guild_permissions(manage_guild=True)
async def prefix_forget(ctx, memory_id: int = 0):
    await _quiet_delete(ctx.message)
    removed = await bot.db.delete_memory(ctx.guild.id, memory_id)
    await ctx.send("Memory removed." if removed else "Memory not found.", delete_after=7)


@bot.command(name="memories")
@commands.has_guild_permissions(manage_guild=True)
async def prefix_memories(ctx):
    await _quiet_delete(ctx.message)
    rows = await bot.db.memories(ctx.guild.id, 50)
    text = "\n".join(f"`{row[0]}` — {row[1]}" for row in rows) or "No memories saved."
    await ctx.send(text[:4000])


@bot.command(name="aiforget", aliases=["forgetai", "clearai"])
async def prefix_ai_forget(ctx):
    await _quiet_delete(ctx.message)
    removed=await bot.db.clear_ai_conversation(ctx.guild.id,str(ctx.author.id))
    await ctx.send(f"Cleared your private Horizon conversation memory ({removed} messages).",delete_after=8)



# -------------------- Discord server control center --------------------

def _parse_duration(value: str):
    text=str(value or "").strip().lower().replace(" ","")
    matches=re.findall(r"(\d+)([smhd])",text)
    if not matches or "".join(n+u for n,u in matches) != text:
        raise ValueError("Use a duration like 30m, 2h, 1d, or 1h30m.")
    seconds=sum(int(n)*{"s":1,"m":60,"h":3600,"d":86400}[u] for n,u in matches)
    if seconds < 30 or seconds > 30*86400:
        raise ValueError("Duration must be between 30 seconds and 30 days.")
    return seconds


class HorizonSettingsModal(discord.ui.Modal, title="Horizon Server Settings"):
    welcome_channel=discord.ui.TextInput(label="Welcome channel ID",placeholder="Channel ID, or 0 to disable",required=False,max_length=25)
    log_channel=discord.ui.TextInput(label="Log channel ID",placeholder="Channel ID, or 0 to disable",required=False,max_length=25)
    personality=discord.ui.TextInput(label="AI server personality",placeholder="Optional; leave blank to keep current",required=False,style=discord.TextStyle.paragraph,max_length=1000)

    def __init__(self,author_id):
        super().__init__(); self.author_id=author_id

    async def on_submit(self,interaction):
        if interaction.user.id!=self.author_id:
            await interaction.response.send_message("Only the dashboard owner can change it.",ephemeral=True); return
        guild=interaction.guild; changed=[]
        for key,raw in (("welcome_channel_id",str(self.welcome_channel.value).strip()),("log_channel_id",str(self.log_channel.value).strip())):
            if raw:
                if not raw.isdigit():
                    await interaction.response.send_message(f"{raw} is not a valid channel ID.",ephemeral=True); return
                cid=int(raw)
                if cid and not isinstance(guild.get_channel(cid),discord.TextChannel):
                    await interaction.response.send_message(f"I couldn't find text channel {cid}.",ephemeral=True); return
                await bot.db.set_setting(guild.id,key,cid); changed.append(key.replace("_channel_id",""))
        personality=str(self.personality.value).strip()
        if personality:
            await bot.db.set_setting(guild.id,"personality",personality); changed.append("personality")
        await interaction.response.send_message("Updated: "+(", ".join(changed) if changed else "nothing"),ephemeral=True)


class ReactionRoleModal(discord.ui.Modal, title="Create Reaction Role"):
    channel_id=discord.ui.TextInput(label="Message channel ID",placeholder="Channel containing the target message",required=True,max_length=25)
    message_id=discord.ui.TextInput(label="Message ID",placeholder="Copy Message ID",required=True,max_length=25)
    emoji=discord.ui.TextInput(label="Emoji",placeholder="Example: 🎮",required=True,max_length=100)
    role_id=discord.ui.TextInput(label="Role ID",placeholder="Role members should receive",required=True,max_length=25)

    def __init__(self,author_id):
        super().__init__(); self.author_id=author_id

    async def on_submit(self,interaction):
        if interaction.user.id!=self.author_id:
            await interaction.response.send_message("Only the dashboard owner can configure this.",ephemeral=True); return
        guild=interaction.guild
        try:
            cid=int(str(self.channel_id.value).strip()); mid=int(str(self.message_id.value).strip()); rid=int(str(self.role_id.value).strip())
        except ValueError:
            await interaction.response.send_message("IDs must be numbers.",ephemeral=True); return
        role=guild.get_role(rid); me=guild.me
        if not role:
            await interaction.response.send_message("I couldn't find that role.",ephemeral=True); return
        if not me or not me.guild_permissions.manage_roles:
            await interaction.response.send_message("I need Manage Roles.",ephemeral=True); return
        if role>=me.top_role:
            await interaction.response.send_message("That role is above my highest role.",ephemeral=True); return
        try:
            channel=guild.get_channel(cid) or await bot.fetch_channel(cid)
            message=await channel.fetch_message(mid)
            emoji=str(self.emoji.value).strip()
            await message.add_reaction(emoji)
        except Exception as exc:
            await interaction.response.send_message(f"Couldn't access the message: {str(exc)[:180]}",ephemeral=True); return
        await bot.db.add_reaction_role(guild.id,cid,mid,emoji,rid)
        await interaction.response.send_message(f"Reaction role created: {emoji} -> {role.name}",ephemeral=True)


class GiveawayModal(discord.ui.Modal, title="Create Giveaway"):
    prize=discord.ui.TextInput(label="Prize",placeholder="Example: 500k Gold",required=True,max_length=200)
    duration=discord.ui.TextInput(label="Duration",placeholder="30m, 2h, 1d, or 1h30m",required=True,max_length=30)
    winners=discord.ui.TextInput(label="Number of winners",placeholder="1",required=True,max_length=3)
    channel_id=discord.ui.TextInput(label="Channel ID",placeholder="Blank = dashboard channel",required=False,max_length=25)

    def __init__(self,author_id,default_channel):
        super().__init__(); self.author_id=author_id; self.default_channel=default_channel

    async def on_submit(self,interaction):
        if interaction.user.id!=self.author_id:
            await interaction.response.send_message("Only the dashboard owner can create this.",ephemeral=True); return
        try:
            seconds=_parse_duration(self.duration.value); winners=int(str(self.winners.value).strip())
            if winners<1 or winners>20: raise ValueError("Winners must be between 1 and 20.")
        except ValueError as exc:
            await interaction.response.send_message(str(exc),ephemeral=True); return
        raw=str(self.channel_id.value).strip()
        cid=self.default_channel if not raw else int(raw) if raw.isdigit() else 0
        channel=interaction.guild.get_channel(cid)
        if not isinstance(channel,discord.TextChannel):
            await interaction.response.send_message("I couldn't find that text channel.",ephemeral=True); return
        ends=time.time()+seconds
        embed=discord.Embed(title="🎉 GIVEAWAY",description=f"Prize: **{self.prize.value.strip()}**\nWinners: **{winners}**\nEnds: <t:{int(ends)}:R>\n\nReact with 🎉 to enter!",colour=discord.Colour.gold())
        embed.set_footer(text=f"Hosted by {interaction.user.display_name}")
        message=await channel.send(embed=embed)
        await message.add_reaction("🎉")
        gid=await bot.db.create_giveaway(interaction.guild.id,channel.id,message.id,self.prize.value.strip(),winners,ends,interaction.user.id)
        await interaction.response.send_message(f"Giveaway #{gid} created in {channel.mention}.",ephemeral=True)


class DiscordControlView(discord.ui.View):
    def __init__(self,ctx):
        super().__init__(timeout=600); self.ctx=ctx

    async def interaction_check(self,interaction):
        if interaction.user.id!=self.ctx.author.id:
            await interaction.response.send_message("This dashboard belongs to the person who opened it.",ephemeral=True); return False
        return True

    @discord.ui.button(label="Server Settings",style=discord.ButtonStyle.primary,emoji="⚙️")
    async def settings(self,interaction,button):
        await interaction.response.send_modal(HorizonSettingsModal(interaction.user.id))

    @discord.ui.button(label="Reaction Role",style=discord.ButtonStyle.success,emoji="🎭")
    async def reaction_role(self,interaction,button):
        await interaction.response.send_modal(ReactionRoleModal(interaction.user.id))

    @discord.ui.button(label="Giveaway",style=discord.ButtonStyle.success,emoji="🎉")
    async def giveaway(self,interaction,button):
        await interaction.response.send_modal(GiveawayModal(interaction.user.id,interaction.channel.id))

    @discord.ui.button(label="Toggle Moderation",style=discord.ButtonStyle.secondary,emoji="🛡️")
    async def moderation(self,interaction,button):
        settings=await bot.db.settings(interaction.guild.id); enabled=not bool(settings["mod_enabled"])
        await bot.db.set_setting(interaction.guild.id,"mod_enabled",1 if enabled else 0)
        await interaction.response.send_message(f"Moderation is now {'ON' if enabled else 'OFF'}.",ephemeral=True)

    @discord.ui.button(label="Refresh",style=discord.ButtonStyle.secondary,emoji="🔄")
    async def refresh(self,interaction,button):
        await interaction.response.edit_message(embed=await dashboard_embed(interaction.guild),view=self)


async def dashboard_embed(guild):
    settings=await bot.db.settings(guild.id)
    roles=await bot.db.reaction_roles(guild.id)
    active=[x for x in await bot.db.active_giveaways() if x["guild_id"]==guild.id]
    embed=discord.Embed(title="🌌 Horizon Control Center",description="Manage Horizon without memorizing commands.",colour=discord.Colour.blurple())
    embed.add_field(name="🛡️ Moderation",value="Enabled" if settings["mod_enabled"] else "Disabled",inline=True)
    embed.add_field(name="👋 Welcome",value=f"<#{settings['welcome_channel_id']}>" if settings["welcome_channel_id"] else "Off",inline=True)
    embed.add_field(name="📋 Logs",value=f"<#{settings['log_channel_id']}>" if settings["log_channel_id"] else "Off",inline=True)
    embed.add_field(name="🎭 Reaction Roles",value=str(len(roles)),inline=True)
    embed.add_field(name="🎉 Active Giveaways",value=str(len(active)),inline=True)
    embed.add_field(name="🧠 AI",value="Ready",inline=True)
    embed.add_field(name="💡 Planned",value="Auto roles • Tickets • Suggestions • Starboard • Level rewards • Polls",inline=False)
    embed.set_footer(text="Horizon • Server Control Center")
    return embed



# -------------------- Community slash commands --------------------
community_group = app_commands.Group(
    name="community",
    description="Giveaways, reaction roles and other community tools.",
)
community_giveaway = app_commands.Group(
    name="giveaway",
    description="Create and manage Horizon giveaways.",
)
community_reactionrole = app_commands.Group(
    name="reactionrole",
    description="Create and manage reaction roles.",
)


@community_giveaway.command(name="create", description="Create a reaction-based giveaway.")
@app_commands.describe(
    prize="What the winner receives.",
    duration="Duration such as 30m, 2h, 1d or 1h30m.",
    winners="Number of winners, from 1 to 20.",
    channel="Channel where the giveaway should be posted.",
)
@app_commands.checks.has_permissions(manage_guild=True)
async def community_giveaway_create(
    interaction: discord.Interaction,
    prize: str,
    duration: str,
    winners: int = 1,
    channel: discord.TextChannel | None = None,
):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    try:
        seconds = _parse_duration(duration)
        winners = int(winners)
        if winners < 1 or winners > 20:
            raise ValueError("Winners must be between 1 and 20.")
    except ValueError as exc:
        await interaction.response.send_message(str(exc), ephemeral=True)
        return

    target = channel or interaction.channel
    if not isinstance(target, discord.TextChannel):
        await interaction.response.send_message("Choose a text channel for the giveaway.", ephemeral=True)
        return

    ends = time.time() + seconds
    embed = discord.Embed(
        title="🎉 GIVEAWAY",
        description=(
            f"Prize: **\${prize.strip()}**\n"
            f"Winners: **\${winners}**\n"
            f"Ends: <t:\${int(ends)}:R>\n\n"
            "React with 🎉 to enter!"
        ),
        colour=discord.Colour.gold(),
    )
    embed.set_footer(text=f"Hosted by \${interaction.user.display_name}")

    try:
        message = await target.send(embed=embed)
        await message.add_reaction("🎉")
        giveaway_id = await bot.db.create_giveaway(
            interaction.guild.id,
            target.id,
            message.id,
            prize.strip(),
            winners,
            ends,
            interaction.user.id,
        )
    except discord.HTTPException as exc:
        await interaction.response.send_message(
            f"I couldn't create the giveaway: {str(exc)[:250]}",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        f"Giveaway #\${giveaway_id} created in \${target.mention}.",
        ephemeral=True,
    )


@community_giveaway.command(name="end", description="End an active giveaway immediately.")
@app_commands.describe(giveaway_id="The giveaway ID shown when it was created.")
async def community_giveaway_end(interaction: discord.Interaction, giveaway_id: int):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    giveaway = await bot.db.giveaway(giveaway_id)
    if not giveaway or giveaway["guild_id"] != interaction.guild.id:
        await interaction.response.send_message("I couldn't find that giveaway in this server.", ephemeral=True)
        return
    if giveaway["ended"]:
        await interaction.response.send_message("That giveaway has already ended.", ephemeral=True)
        return
    if giveaway["host_id"] != interaction.user.id and not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("Only the giveaway host or a server manager can end it.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    await bot._finish_giveaway(giveaway_id)
    await interaction.followup.send(f"Giveaway #\${giveaway_id} ended.", ephemeral=True)


@community_giveaway.command(name="reroll", description="Pick new winner(s) for an ended giveaway.")
@app_commands.describe(giveaway_id="The giveaway ID to reroll.")
@app_commands.checks.has_permissions(manage_guild=True)
async def community_giveaway_reroll(interaction: discord.Interaction, giveaway_id: int):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    giveaway = await bot.db.giveaway(giveaway_id)
    if not giveaway or giveaway["guild_id"] != interaction.guild.id:
        await interaction.response.send_message("I couldn't find that giveaway in this server.", ephemeral=True)
        return
    if not giveaway["ended"]:
        await interaction.response.send_message("End the giveaway before rerolling it.", ephemeral=True)
        return

    entries = await bot.db.giveaway_entries(giveaway_id)
    if not entries:
        await interaction.response.send_message("There are no recorded entries to reroll.", ephemeral=True)
        return

    selected = random.sample(entries, min(int(giveaway["winners"]), len(entries)))
    mentions = ", ".join(f"<@\${uid}>" for uid in selected)
    channel = interaction.guild.get_channel(giveaway["channel_id"])
    if isinstance(channel, discord.TextChannel):
        try:
            await channel.send(
                f"Giveaway #\${giveaway_id} reroll! Congratulations \${mentions}! "
                f"You won **\${giveaway['prize']}**."
            )
        except discord.HTTPException:
            pass
    await interaction.response.send_message(
        f"Rerolled giveaway #\${giveaway_id}: \${mentions}",
        ephemeral=True,
    )


@community_giveaway.command(name="list", description="List active giveaways in this server.")
async def community_giveaway_list(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    active = [
        giveaway for giveaway in await bot.db.active_giveaways()
        if giveaway["guild_id"] == interaction.guild.id
    ]
    if not active:
        await interaction.response.send_message("There are no active giveaways.")
        return

    lines = []
    for giveaway in active:
        lines.append(
            f"#{giveaway['id']} — {giveaway['prize']} • "
            f"{giveaway['winners']} winner(s) • channel <#{giveaway['channel_id']}> • "
            f"ends <t:{int(giveaway['ends_at'])}:R>"
        )
    await interaction.response.send_message("\n".join(lines)[:4000])


@community_reactionrole.command(name="create", description="Attach a role to a message reaction.")
@app_commands.describe(
    channel="Channel containing the target message.",
    message_id="ID of the target message.",
    emoji="Emoji users should react with.",
    role="Role to give when users react.",
)
@app_commands.checks.has_permissions(manage_guild=True)
async def community_reactionrole_create(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    message_id: int,
    emoji: str,
    role: discord.Role,
):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    me = interaction.guild.me
    if not me or not me.guild_permissions.manage_roles:
        await interaction.response.send_message("Horizon needs Manage Roles to create reaction roles.", ephemeral=True)
        return
    if role >= me.top_role:
        await interaction.response.send_message("That role is above Horizon's highest role.", ephemeral=True)
        return
    if role.is_default() or role.managed:
        await interaction.response.send_message("That role cannot be assigned by Horizon.", ephemeral=True)
        return

    emoji = emoji.strip()
    if not emoji:
        await interaction.response.send_message("Enter an emoji.", ephemeral=True)
        return

    try:
        message = await channel.fetch_message(message_id)
        await message.add_reaction(emoji)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException, ValueError) as exc:
        await interaction.response.send_message(
            f"I couldn't access that message or emoji: {str(exc)[:250]}",
            ephemeral=True,
        )
        return

    await bot.db.add_reaction_role(
        interaction.guild.id,
        channel.id,
        message_id,
        emoji,
        role.id,
    )
    await interaction.response.send_message(
        f"Reaction role created: {emoji} -> {role.mention}",
        ephemeral=True,
    )


@community_reactionrole.command(name="remove", description="Remove a reaction-role mapping.")
@app_commands.describe(
    message_id="ID of the target message.",
    emoji="Emoji used by the reaction-role mapping.",
)
@app_commands.checks.has_permissions(manage_guild=True)
async def community_reactionrole_remove(
    interaction: discord.Interaction,
    message_id: int,
    emoji: str,
):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    removed = await bot.db.remove_reaction_role(interaction.guild.id, message_id, emoji.strip())
    await interaction.response.send_message(
        "Reaction role mapping removed." if removed else "No matching reaction-role mapping was found.",
        ephemeral=True,
    )


@community_reactionrole.command(name="list", description="List this server's reaction-role mappings.")
@app_commands.checks.has_permissions(manage_guild=True)
async def community_reactionrole_list(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    rows = await bot.db.reaction_roles(interaction.guild.id)
    if not rows:
        await interaction.response.send_message("No reaction roles are configured.")
        return
    lines = [
        f"• channel <#{channel_id}> • message {message_id} • {emoji} -> <@&{role_id}>"
        for message_id, emoji, role_id, channel_id in rows
    ]
    await interaction.response.send_message("\n".join(lines)[:4000])


community_group.add_command(community_giveaway)
community_group.add_command(community_reactionrole)
bot.tree.add_command(community_group)


@bot.tree.command(name="dashboard", description="Open Horizon's interactive server control center.")
@app_commands.checks.has_permissions(manage_guild=True)
async def slash_dashboard(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    context = type("DashboardContext", (), {"author": interaction.user})()
    await interaction.response.send_message(
        embed=await dashboard_embed(interaction.guild),
        view=DiscordControlView(context),
    )


@bot.command(name="dashboard",aliases=["control","controlpanel","serverpanel"])
@commands.has_guild_permissions(manage_guild=True)
async def prefix_dashboard(ctx):
    await _quiet_delete(ctx.message)
    await ctx.send(embed=await dashboard_embed(ctx.guild),view=DiscordControlView(ctx))


# -------------------- Persistent Horizon RPG --------------------

async def _rpg_delete(ctx):
    await _quiet_delete(ctx.message)

async def _rpg_require(ctx):
    ok, value = await bot.rpg.ensure_player(ctx.guild.id, ctx.author.id)
    if not ok:
        await ctx.send(value, delete_after=8)
        return None
    return value


def _rpg_embed(title, description=""):
    return discord.Embed(title=title, description=description, colour=discord.Colour.teal())


def _rpg_image_url(kind, seed):
    # Use the live Railway art renderer when SITE_URL is configured. Unlike the
    # old random-avatar service, the renderer builds a stable full-body scene
    # from race/class/species identity. DiceBear remains a safe fallback.
    base=os.getenv("SITE_URL", "").strip().rstrip("/")
    if base:
        return f"{base}/api/rpg/art?kind={quote(kind, safe='')}&seed={quote(seed, safe='')}&v=3"
    style = {"character": "adventurer", "mob": "notionists", "pet": "notionists"}.get(kind, "adventurer")
    return f"https://api.dicebear.com/9.x/{style}/png?seed={quote(seed, safe='')}&backgroundColor=b6e3f4,c0aede,d1d4f9"


def _character_image(p):
    parts=[str(p.get(k) or "none") for k in ("race","subrace","class_name","subclass","evolution")]
    return _rpg_image_url("character", "|".join(parts))


def _mob_image(enemy):
    parts=[str(enemy.get(k) or "") for k in ("name","level","region","element","role","type")]
    return _rpg_image_url("mob", "|".join(parts))


def _pet_image(pet):
    parts=[str(pet.get(k) or "") for k in ("species","level","ability","rarity")]
    return _rpg_image_url("pet", "|".join(parts))


def _bar(current, maximum, length=16):
    maximum=max(1,int(maximum)); current=max(0,min(int(current),maximum)); filled=int(length*current/maximum)
    return "█"*filled + "░"*(length-filled)



class RPGPaginationView(discord.ui.View):
    """Compact RPG panel controls inspired by polished Discord game bots.

    The original command message is removed; this panel owns its state and edits
    one message in place. Only the command author can navigate it, and the
    trash button removes the panel when they are finished.
    """
    def __init__(self, ctx, pages, *, select_options=None, select_callback=None, select_options_by_page=None, deletable=True):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.deletable = deletable
        self.pages = pages or [discord.Embed(title="Horizon RPG", description="Nothing to display.", colour=discord.Colour.blurple())]
        self.index = 0
        self.message = None
        self.select_callback = select_callback
        self.select_options_by_page = select_options_by_page
        self._select = None
        if select_options:
            options = []
            for value, label, description in select_options[:25]:
                options.append(discord.SelectOption(label=label[:100], value=value[:100], description=(description or '')[:100]))
            if options:
                self._select = discord.ui.Select(placeholder="Info...", min_values=1, max_values=1, options=options)
                self._select.callback = self._select_changed
                self.add_item(self._select)
        if not deletable:
            for child in list(self.children):
                if getattr(child, "custom_id", None) == "rpg:delete":
                    self.remove_item(child)
                    break
        self._sync()

    def _sync(self):
        # Five-button layout like the reference UI: first, previous, next, last, delete.
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id in {"rpg:first", "rpg:prev"}:
                    child.disabled = self.index <= 0
                elif child.custom_id in {"rpg:next", "rpg:last"}:
                    child.disabled = self.index >= len(self.pages) - 1
        if self._select:
            self._select.disabled = False
            if self.select_options_by_page is not None:
                opts = []
                for value, label, description in self.select_options_by_page[min(self.index, len(self.select_options_by_page)-1)][:25]:
                    opts.append(discord.SelectOption(label=label[:100], value=value[:100], description=(description or '')[:100]))
                self._select.options = opts

    async def interaction_check(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This panel belongs to another hero.", ephemeral=True)
            return False
        return True

    async def _edit(self, interaction):
        self._sync()
        await interaction.response.edit_message(embed=self.pages[self.index], view=self)

    @discord.ui.button(label="", emoji="⏮️", style=discord.ButtonStyle.primary, custom_id="rpg:first")
    async def first(self, interaction, button):
        self.index = 0
        await self._edit(interaction)

    @discord.ui.button(label="", emoji="◀️", style=discord.ButtonStyle.primary, custom_id="rpg:prev")
    async def previous(self, interaction, button):
        self.index = max(0, self.index - 1)
        await self._edit(interaction)

    @discord.ui.button(label="", emoji="▶️", style=discord.ButtonStyle.primary, custom_id="rpg:next")
    async def next_page(self, interaction, button):
        self.index = min(len(self.pages) - 1, self.index + 1)
        await self._edit(interaction)

    @discord.ui.button(label="", emoji="⏭️", style=discord.ButtonStyle.primary, custom_id="rpg:last")
    async def last(self, interaction, button):
        self.index = len(self.pages) - 1
        await self._edit(interaction)

    @discord.ui.button(label="", emoji="🗑️", style=discord.ButtonStyle.danger, custom_id="rpg:delete")
    async def delete(self, interaction, button):
        if not self.deletable:
            await interaction.response.defer()
            return
        await interaction.response.defer()
        try:
            await interaction.message.delete()
        except (discord.NotFound, discord.Forbidden):
            pass
        self.stop()

    async def _select_changed(self, interaction):
        if not self.select_callback:
            await interaction.response.defer()
            return
        value = self._select.values[0]
        await self.select_callback(interaction, value)

    async def on_timeout(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.custom_id == "rpg:delete":
                child.disabled = False
            else:
                child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


class RPGEquipmentSlotSelect(discord.ui.Select):
    """One equipment-slot dropdown. Discord permits 25 options per select."""
    def __init__(self, owner_view, slot, options):
        self.owner_view = owner_view
        self.slot = slot
        super().__init__(
            placeholder=f"Choose {slot.title()}...",
            min_values=1,
            max_values=1,
            options=options[:25],
            row=None,
        )

    async def callback(self, interaction):
        if not await self.owner_view.interaction_check(interaction):
            return
        value=self.values[0]
        if value == f"__unequip__:{self.slot}":
            ok,msg=await bot.rpg.unequip_slot(self.owner_view.ctx.guild.id,self.owner_view.ctx.author.id,self.slot)
        else:
            ok,msg=await bot.rpg.equip(self.owner_view.ctx.guild.id,self.owner_view.ctx.author.id,value)
        self.owner_view.last_message=msg
        embed=await self.owner_view.render()
        # Keep the loadout open so the player can fill the next slot immediately.
        await interaction.response.edit_message(embed=embed,view=self.owner_view)


class RPGEquipmentLoadoutView(discord.ui.View):
    """MMO-style equipment screen: each visible slot has its own dropdown."""
    SLOT_ORDER=("weapon","armor","offhand","accessory","ring","amulet","relic")
    SLOT_ICONS={
        "weapon":"⚔️","armor":"🛡️","offhand":"🔰","accessory":"📿",
        "ring":"💍","amulet":"📿","relic":"🔮"
    }

    def __init__(self, ctx, inventory_rows, gear, *, page=0):
        super().__init__(timeout=300)
        self.ctx=ctx
        self.inventory_rows=list(inventory_rows)
        self.gear=dict(gear)
        self.page=max(0,int(page))
        self.last_message=""
        self.page_size=4
        self._build_components()

    async def interaction_check(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This equipment panel belongs to another hero.", ephemeral=True)
            return False
        return True

    def _slot_items(self, slot):
        rows=[]
        for key,qty in self.inventory_rows:
            d=ITEMS.get(key,{})
            if d.get("slot") != slot or int(qty)<=0:
                continue
            rows.append((key,int(qty),d))
        current=self.gear.get(slot)
        if current and not any(key==current for key,_,_ in rows):
            d=ITEMS.get(current,{})
            rows.append((current,1,d))
        rarity_order={r:i for i,r in enumerate(RARITIES)}
        rows.sort(key=lambda x:(0 if x[0]==current else 1,-rarity_order.get(x[2].get("rarity","common"),0),int(x[2].get("level_req",1)),x[2].get("name",x[0])))
        return rows

    def _options(self, slot):
        current=self.gear.get(slot)
        options=[discord.SelectOption(
            label=f"Unequip {slot.title()}"[:100],
            value=f"__unequip__:{slot}",
            description="Leave this slot empty."[:100]
        )]
        for key,qty,d in self._slot_items(slot)[:24]:
            name=d.get("name",key)
            marker="✓ Equipped • " if key==current else ""
            desc=f"{marker}{d.get('rarity','common').title()} • Lv {d.get('level_req',1)}+ • {qty} owned"
            options.append(discord.SelectOption(label=name[:100],value=key[:100],description=desc[:100]))
        return options

    def _build_components(self):
        self.clear_items()
        start=self.page*self.page_size
        slots=self.SLOT_ORDER[start:start+self.page_size]
        for slot in slots:
            self.add_item(RPGEquipmentSlotSelect(self,slot,self._options(slot)))

    async def render(self):
        # Refresh equipment from the DB so the panel always reflects the actual state.
        data=await bot.rpg.stats(self.ctx.guild.id,self.ctx.author.id)
        if data:
            _,gear,_=data
            self.gear=dict(gear)
        total_pages=max(1,(len(self.SLOT_ORDER)+self.page_size-1)//self.page_size)
        start=self.page*self.page_size
        slots=self.SLOT_ORDER[start:start+self.page_size]
        lines=[]
        for slot in slots:
            icon=self.SLOT_ICONS.get(slot,"🎒")
            key=self.gear.get(slot)
            if key:
                d=ITEMS.get(key,{})
                lines.append(f"{icon} **{slot.title()}** — **{d.get('name',key)}** · {d.get('rarity','common').title()} · Lv {d.get('level_req',1)}+")
            else:
                lines.append(f"{icon} **{slot.title()}** — *Empty*")
        description=("Choose equipment directly from the dropdown for each slot.\n"
                     "Your owned items are shown in that slot's menu; selecting one equips it immediately.\n\n"
                     + "\n".join(lines))
        if self.last_message:
            description += f"\n\n{self.last_message}"
        if any(len(self._slot_items(slot))>24 for slot in slots):
            description += "\n\n⚠️ Discord limits each dropdown to 25 choices. Extra items remain equippable with `!rpg equip <item_key>` and can be added to the UI through the item browser."
        description += f"\n\n**Equipment page {self.page+1}/{total_pages}**"
        embed=_rpg_embed("⚔️ Equipment Loadout",description)
        self._build_components()
        self._add_navigation(total_pages)
        return embed

    def _add_navigation(self,total_pages):
        # Navigation occupies one action row, leaving four rows for slot dropdowns.
        row=4
        first=discord.ui.Button(label="First",emoji="⏮️",style=discord.ButtonStyle.secondary,row=row,disabled=self.page<=0)
        prev=discord.ui.Button(label="Prev",emoji="◀️",style=discord.ButtonStyle.secondary,row=row,disabled=self.page<=0)
        nxt=discord.ui.Button(label="Next",emoji="▶️",style=discord.ButtonStyle.secondary,row=row,disabled=self.page>=total_pages-1)
        last=discord.ui.Button(label="Last",emoji="⏭️",style=discord.ButtonStyle.secondary,row=row,disabled=self.page>=total_pages-1)
        close=discord.ui.Button(label="Close",emoji="🗑️",style=discord.ButtonStyle.danger,row=row)
        async def first_cb(i): self.page=0; await i.response.edit_message(embed=await self.render(),view=self)
        async def prev_cb(i): self.page=max(0,self.page-1); await i.response.edit_message(embed=await self.render(),view=self)
        async def next_cb(i): self.page=min(total_pages-1,self.page+1); await i.response.edit_message(embed=await self.render(),view=self)
        async def last_cb(i): self.page=total_pages-1; await i.response.edit_message(embed=await self.render(),view=self)
        async def close_cb(i): await i.response.defer(); self.stop();
        first.callback=first_cb; prev.callback=prev_cb; nxt.callback=next_cb; last.callback=last_cb; close.callback=close_cb
        self.add_item(first); self.add_item(prev); self.add_item(nxt); self.add_item(last); self.add_item(close)

    async def on_timeout(self):
        for child in self.children:
            child.disabled=True
        if self.message:
            try: await self.message.edit(view=self)
            except Exception: pass


class RPGConfirmationView(discord.ui.View):
    def __init__(self, ctx, title, description, on_confirm):
        super().__init__(timeout=60)
        self.ctx=ctx; self.title=title; self.description=description; self.on_confirm=on_confirm; self.message=None

    async def interaction_check(self, interaction):
        if interaction.user.id!=self.ctx.author.id:
            await interaction.response.send_message("Only the hero who requested this change can confirm it.",ephemeral=True); return False
        return True

    @discord.ui.button(label="Confirm",emoji="✅",style=discord.ButtonStyle.success)
    async def confirm(self,interaction,button):
        ok,msg=await self.on_confirm()
        for child in self.children: child.disabled=True
        await interaction.response.edit_message(embed=_rpg_action_embed(self.title,msg,ok),view=self)
        self.stop()

    @discord.ui.button(label="Cancel",emoji="❌",style=discord.ButtonStyle.danger)
    async def cancel(self,interaction,button):
        for child in self.children: child.disabled=True
        await interaction.response.edit_message(embed=_rpg_action_embed(self.title,"Change cancelled. Nothing was modified.",False),view=self)
        self.stop()

    async def on_timeout(self):
        for child in self.children: child.disabled=True
        if self.message:
            try: await self.message.edit(view=self)
            except Exception: pass


async def _rpg_panel(ctx, pages, *, select_options=None, select_callback=None, select_options_by_page=None, deletable=True):
    view = RPGPaginationView(ctx, pages, select_options=select_options, select_callback=select_callback, select_options_by_page=select_options_by_page, deletable=deletable)
    view.message = await ctx.send(embed=pages[0], view=view)
    return view


def _rpg_pages(title, entries, *, page_size=8, icon="📜", colour=None, formatter=None):
    entries = list(entries)
    if not entries:
        return [discord.Embed(title=f"{icon} {title}", description="Nothing to display yet.", colour=colour or discord.Colour.blurple())]
    pages = []
    total = max(1, (len(entries) + page_size - 1) // page_size)
    for n in range(total):
        chunk = entries[n * page_size:(n + 1) * page_size]
        body = "\n\n".join(formatter(x) if formatter else str(x) for x in chunk)
        e = discord.Embed(title=f"{icon} {title}", description=body, colour=colour or discord.Colour.blurple())
        e.set_footer(text=f"Page {n + 1} / {total} • {len(entries)} entries")
        pages.append(e)
    return pages


def _rpg_action_embed(title, message, ok=True):
    return discord.Embed(
        title=("✅ " if ok else "❌ ") + title,
        description=message,
        colour=discord.Colour.green() if ok else discord.Colour.red(),
    )


async def _rpg_action_panel(ctx, title, message, ok=True):
    return await _rpg_panel(ctx, [_rpg_action_embed(title, message, ok)], deletable=False)

def _combat_embed(state, result=None):
    enemy=state["enemy"]
    hp=max(0,state["player_hp"]); ehp=max(0,state["enemy_hp"])
    max_hp=state.get("player_max_hp",100); max_mp=state.get("player_max_mp",100); mp=max(0,state.get("player_mp",0))
    stats=state.get("combat_stats",{})
    mode="🏰 Dungeon" if state["mode"]=="dungeon" else "🗺️ Adventure"
    floor=f" • Floor {state['floor']}/{state['floors']}" if state["mode"]=="dungeon" else ""
    boss_tag=" 👑 BOSS" if enemy.get("is_boss") else ""
    pet=state.get("pet",{}) or {}
    skill_cds=state.get("skill_cooldowns",{})
    skill_lines=[]
    player_level=int(state.get("player_level",1))
    equipped_keys=state.get("equipped_skill_keys",[])[:4]
    for key in equipped_keys:
        skill=next((x for x in bot.rpg.skills_for_player(state) if x["key"]==key),None)
        if not skill: continue
        cd=skill_cds.get(skill["key"],0)
        skill_lines.append(f"**{skill['name']}** · {skill['cost']} MP · CD {skill['cooldown']}t · {skill['mechanic']} · {skill.get('buff_text','No buff')} · {skill.get('debuff_text','No debuff')}" + (f" · READY" if not cd else f" · CD {cd}"))
    desc=(f"**{mode}{floor}** · Turn **{state.get('turn',1)}**\n\n"
          f"👹 **{enemy['name']}** · Lv **{enemy['level']}**\n"
          f"❤️ `{_bar(ehp,enemy['hp'])}` **{ehp}/{enemy['hp']} HP**\n"
          f"⚔️ ATK **{enemy.get('atk',0)}** · 🛡️ DEF **{enemy.get('def',0)}** · 💨 SPD **{enemy.get('speed',0)}** · 🎯 Crit **{enemy.get('crit',0)}%**\n"           f"✨ Abilities: **{', '.join(ENEMY_ABILITIES[k]['name'] for k in enemy.get('abilities',[]) if k in ENEMY_ABILITIES) or 'Basic attacks'}**\n\n"
          f"🧑 **Your Hero**\n"
          f"❤️ `{_bar(hp,max_hp)}` **{hp}/{max_hp} HP**\n"
          f"💧 `{_bar(mp,max_mp)}` **{mp}/{max_mp} MP**\n"
          f"⚡ Stamina **{state.get('player_stamina',100)}/100**\n"
          f"⚔️ ATK **{stats.get('atk',0)}** · 🛡️ DEF **{stats.get('defense',0)}** · 💨 SPD **{stats.get('speed',0)}** · 🎯 Crit **{stats.get('crit',0)}%**")
    if pet.get("name"):
        pet_cd=state.get("pet_cooldown",0)
        desc += f"\n\n🐾 **{pet['name']}** · {pet.get('species','Companion')}\n+{pet.get('atk',0)} ATK · +{pet.get('defense',0)} DEF · +{pet.get('hp',0)} HP · +{pet.get('speed',0)} SPD · +{pet.get('crit',0)}% Crit\nAbility: **{pet.get('ability','Pet Assist')}**" + (f" · Ready in {pet_cd}" if pet_cd else " · **READY**")
    if skill_lines:
        desc += "\n\n✨ **Skills**\n" + "\n".join(skill_lines)
    statuses=bot.rpg._status_summary(state.get("enemy_statuses",{})) if hasattr(bot.rpg,"_status_summary") else "None"
    desc += f"\n\n🧿 **Enemy Status:** {statuses}"
    if state.get("combo",0):
        chain=state.get("combo_chain",[])
        chain_text=" → ".join(chain[-4:]) if chain else "Building"
        desc += f"\n🔗 **Combo x{state.get('combo',0)}** · {chain_text}"
        if state.get("combo_repeat",0)>=2:
            desc += " · ⚠️ Repetition penalty"
    desc += "\n\n" + "\n".join(f"• {line}" for line in state["log"][-5:])
    if result and result.get("finished"):
        if result.get("win"):
            if result.get("reward_status") == "recovery_needed":
                failed=", ".join(result.get("reward_errors",[])) or "some rewards"
                desc += "\n\n🏆 **Victory!**"
                desc += "\n⚠️ **Victory secured.** Reward processing was incomplete for: **" + failed + "**."
                desc += "\nThe battle is permanently resolved and will not be replayed because of a reward error."
            else:
                desc += f"\n\n🏆 **Victory!** +{result.get('xp',0)} XP • +{result.get('gold',0)} gold • **{ITEMS.get(result.get('drop'),{'name':result.get('drop','loot')})['name']}**"
                if result.get("pet_xp"):
                    desc += f"\n🐾 Equipped pet gained **+{result['pet_xp']} XP**"
                if result.get("extra_loot"):
                    extras=[]
                    for key,qty in result["extra_loot"]:
                        extras.append(f"{ITEMS.get(key,{'name':key}).get('name',key)} ×{qty}")
                    desc += f"\n🎁 **Bonus loot:** {', '.join(extras)}"
                if result.get("level_after",0)>result.get("level_before",0): desc += f"\n✨ **LEVEL UP!** Level {result['level_before']} → **{result['level_after']}**"
        elif result.get("fled"): desc += "\n\n🏃 **You escaped.**"
        else: desc += "\n\n💀 **Defeated.** You survived with 1 HP. Rest before trying again."
    e=_rpg_embed(f"⚔️ {state['name']}",desc)
    e.set_image(url=_mob_image(enemy))
    return e


class RPGCombatSkillView(discord.ui.View):
    def __init__(self, battle_view, skills):
        super().__init__(timeout=45)
        self.battle_view=battle_view
        options=[]
        cooldowns=battle_view.state.get("skill_cooldowns",{})
        mp=battle_view.state.get("player_mp",0)
        for skill in skills[:25]:
            if int(getattr(battle_view.ctx.author, "id", 0)) and int(skill.get("unlock",1)) > int(battle_view.state.get("player_level", 1)):
                continue
            cd=int(cooldowns.get(skill["key"],0))
            status=f"CD {cd}" if cd else (f"{skill['cost']} MP" if mp>=skill["cost"] else f"Need {skill['cost']} MP")
            dmg=f"~{int(max(1,battle_view.state.get('combat_stats',{}).get('atk',10))*float(skill.get('mult',0))*.92)}–{int(max(1,battle_view.state.get('combat_stats',{}).get('atk',10))*float(skill.get('mult',0))*1.08)} dmg" if skill.get("effect") not in {"heal","counter","barrier"} else (f"~{int(battle_view.state.get('combat_stats',{}).get('max_hp',100)*skill.get('heal_pct',0))} HP" if skill.get("effect")=="heal" else "utility")
            options.append(discord.SelectOption(label=skill["name"][:100],value=skill["key"],description=f"{status} • {skill.get('desc','Effect unavailable')}"[:100]))
        select=discord.ui.Select(placeholder="Choose a skill...",min_values=1,max_values=1,options=options)
        select.callback=self.choose
        self.add_item(select)

    async def choose(self,interaction):
        if interaction.user.id!=self.battle_view.ctx.author.id:
            await interaction.response.send_message("This battle belongs to another hero.",ephemeral=True); return
        # Acknowledge immediately; resolving a skill can take long enough to
        # exceed Discord's interaction response window.
        await interaction.response.defer()
        skill=self.children[0].values[0]
        result=await bot.rpg.combat_action(self.battle_view.ctx.guild.id,self.battle_view.ctx.author.id,f"skill:{skill}")
        if result.get("error"):
            await interaction.followup.send(result["error"],ephemeral=True); return
        self.stop()
        self.battle_view.state=result.get("state",self.battle_view.state)
        if result.get("finished"):
            for child in self.battle_view.children: child.disabled=True
            try: await self.battle_view.message.edit(embed=_combat_embed(self.battle_view.state,result),view=self.battle_view)
            except discord.HTTPException: pass
            self.battle_view.stop()
        else:
            try: await self.battle_view.message.edit(embed=_combat_embed(self.battle_view.state),view=self.battle_view)
            except discord.HTTPException: pass

    async def on_timeout(self):
        for child in self.children: child.disabled=True


def _pvp_embed(state, result=None):
    players=list(state["players"].items())
    left_id,left=players[0]; right_id,right=players[1]
    turn=state.get("turn")
    def block(uid,data):
        active=" ◀️ TURN" if turn==uid else ""
        pet=data.get("pet",{}) or {}
        skills=[x for x in bot.rpg.skills_for_player(data) if x["key"] in data.get("equipped_skill_keys",[])][:4]
        return (f"**{data['name']}** · Lv **{data.get('level',1)}** · {data.get('race','human').title()} {data.get('class','warrior').title()}{active}\n"
                f"❤️ `{_bar(data['hp'],data['max_hp'])}` **{max(0,data['hp'])}/{data['max_hp']}**\n"
                f"💧 `{_bar(data['mp'],data['max_mp'])}` **{max(0,data['mp'])}/{data['max_mp']} MP**\n"
                f"⚔️ {data['stats']['atk']} · 🛡️ {data['stats']['defense']} · 💨 {data['stats']['speed']} · 🎯 {data['stats']['crit']}%\n"
                f"🐾 {pet.get('name','No pet')}" + (f" ({pet.get('ability','Pet Assist')})" if pet.get('name') else "") +
                f"\n✨ Skills: {', '.join(x['name'] for x in skills)}")
    desc=f"**Round {state.get('round',1)}**\n\n{block(left_id,left)}\n\n⚔️ **VS** ⚔️\n\n{block(right_id,right)}\n\n" + "\n".join(f"• {x}" for x in state.get("log",[])[-6:])
    if result and result.get("finished"):
        winner=state.get("winner"); loser=state.get("loser")
        if state.get("arena"):
            desc += f"\n\n🏆 **Arena Victory:** <@{winner}>\n💀 **Defeated:** <@{loser}>\n📈 Ranked result recorded for the current season."
        else:
            desc += f"\n\n🏆 **Victory:** <@{winner}>\n💀 **Defeated:** <@{loser}>\n🎁 Winner: **80 XP + 120 gold**"
    e=_rpg_embed("🏆 Ranked Arena" if state.get("arena") else "⚔️ PvP Duel",desc)
    e.set_image(url=_character_image(left))
    e.set_thumbnail(url=_character_image(right))
    return e


class RPGPvPSkillView(discord.ui.View):
    def __init__(self,battle_view,user_id):
        super().__init__(timeout=45); self.battle_view=battle_view; self.user_id=user_id
        data=battle_view.state["players"][user_id]; options=[]
        for skill in [x for x in bot.rpg.skills_for_player(data) if x["key"] in data.get("equipped_skill_keys",[])][:4]:
            if int(data.get("level",1)) < int(skill.get("unlock",1)):
                continue
            cd=int(data.get("skill_cooldowns",{}).get(skill["key"],0)); status=f"CD {cd}" if cd else f"{skill['cost']} MP"
            dmg=f"~{int(max(1,battle_view.state.get('combat_stats',{}).get('atk',10))*float(skill.get('mult',0))*.92)}–{int(max(1,battle_view.state.get('combat_stats',{}).get('atk',10))*float(skill.get('mult',0))*1.08)} dmg" if skill.get("effect") not in {"heal","counter","barrier"} else (f"~{int(battle_view.state.get('combat_stats',{}).get('max_hp',100)*skill.get('heal_pct',0))} HP" if skill.get("effect")=="heal" else "utility")
            options.append(discord.SelectOption(label=skill["name"][:100],value=skill["key"],description=f"{status} • {dmg} • {skill.get('buff_text','No buff')} • {skill.get('debuff_text','No debuff')}"[:100]))
        select=discord.ui.Select(placeholder="Choose your skill...",min_values=1,max_values=1,options=options); select.callback=self.choose; self.add_item(select)
    async def choose(self,interaction):
        if interaction.user.id!=self.user_id:
            await interaction.response.send_message("Only the active duelist can choose a skill.",ephemeral=True); return
        foe=next(uid for uid in self.battle_view.state["players"] if uid!=self.user_id)
        result=await bot.rpg.duel_action(self.battle_view.guild_id,self.user_id,foe,f"skill:{self.children[0].values[0]}")
        if result.get("error"): await interaction.response.send_message(result["error"],ephemeral=True); return
        await interaction.response.defer(); self.stop(); self.battle_view.state=result.get("state",self.battle_view.state)
        if result.get("finished"):
            for c in self.battle_view.children:c.disabled=True
            await self.battle_view.message.edit(embed=_pvp_embed(self.battle_view.state,result),view=self.battle_view); self.battle_view.stop()
        else: await self.battle_view.message.edit(embed=_pvp_embed(self.battle_view.state),view=self.battle_view)


class RPGPvPView(discord.ui.View):
    def __init__(self,ctx,state,key):
        super().__init__(timeout=600); self.ctx=ctx; self.state=state; self.key=key; self.guild_id=ctx.guild.id; self.message=None
    async def interaction_check(self,interaction):
        if interaction.user.id not in self.state["players"]:
            await interaction.response.send_message("This duel is only for the two participating heroes.",ephemeral=True); return False
        if self.state.get("turn")!=interaction.user.id:
            await interaction.response.send_message(f"It is <@{self.state.get('turn')}>. Let them take their turn.",ephemeral=True); return False
        return True
    async def _act(self,interaction,action):
        uid=interaction.user.id; foe=next(x for x in self.state["players"] if x!=uid)
        result=await bot.rpg.duel_action(self.guild_id,uid,foe,action)
        if result.get("error"): await interaction.response.send_message(result["error"],ephemeral=True); return
        if result.get("choose_skill"):
            await interaction.response.send_message("✨ **Choose a skill:**",ephemeral=True,view=RPGPvPSkillView(self,uid)); return
        self.state=result.get("state",self.state)
        if result.get("finished"):
            for c in self.children:c.disabled=True
            await interaction.response.edit_message(embed=_pvp_embed(self.state,result),view=self); self.stop(); return
        await interaction.response.edit_message(embed=_pvp_embed(self.state),view=self)
    @discord.ui.button(label="Attack",emoji="⚔️",style=discord.ButtonStyle.primary)
    async def attack(self,i,b): await self._act(i,"attack")
    @discord.ui.button(label="Skills",emoji="✨",style=discord.ButtonStyle.success)
    async def skills(self,i,b):
        uid=i.user.id
        if self.state.get("turn")!=uid:
            await i.response.send_message(f"It is <@{self.state.get('turn')}>.",ephemeral=True); return
        await i.response.send_message("✨ **Choose a skill:**",ephemeral=True,view=RPGPvPSkillView(self,uid))
    @discord.ui.button(label="Pet Assist",emoji="🐾",style=discord.ButtonStyle.success)
    async def pet(self,i,b): await self._act(i,"pet")
    @discord.ui.button(label="Defend",emoji="🛡️",style=discord.ButtonStyle.secondary)
    async def defend(self,i,b): await self._act(i,"defend")
    @discord.ui.button(label="Surrender",emoji="🏳️",style=discord.ButtonStyle.danger)
    async def surrender(self,i,b): await self._act(i,"surrender")
    async def on_timeout(self):
        bot.rpg.active_duels.pop(self.key,None)
        for c in self.children:c.disabled=True
        if self.message:
            try: await self.message.edit(view=self)
            except Exception: pass


class RPGCombatItemView(discord.ui.View):
    def __init__(self, battle_view, choices):
        super().__init__(timeout=45)
        self.battle_view=battle_view
        options=[discord.SelectOption(label=ITEMS[k].get("name",k)[:100],value=k,description=f"{ITEMS[k].get('rarity','common').title()} • {q} owned"[:100]) for k,q in choices[:25]]
        select=discord.ui.Select(placeholder="Choose a potion or food...",min_values=1,max_values=1,options=options)
        select.callback=self.choose
        self.add_item(select)

    async def choose(self,interaction):
        if interaction.user.id!=self.battle_view.ctx.author.id:
            await interaction.response.send_message("This battle belongs to another hero.",ephemeral=True); return
        # Acknowledge immediately; item use can also perform several database
        # operations before the combat result is ready.
        await interaction.response.defer()
        item=self.children[0].values[0]
        result=await bot.rpg.combat_action(self.battle_view.ctx.guild.id,self.battle_view.ctx.author.id,f"potion:{item}")
        if result.get("error"):
            await interaction.followup.send(result["error"],ephemeral=True); return
        self.stop()
        self.battle_view.state=result.get("state",self.battle_view.state)
        if result.get("finished"):
            for child in self.battle_view.children: child.disabled=True
            try:
                await self.battle_view.message.edit(embed=_combat_embed(self.battle_view.state,result),view=self.battle_view)
            except discord.HTTPException: pass
            self.battle_view.stop()
        else:
            try: await self.battle_view.message.edit(embed=_combat_embed(self.battle_view.state),view=self.battle_view)
            except discord.HTTPException: pass

    async def on_timeout(self):
        for child in self.children: child.disabled=True
        try:
            if self.children: await self.children[0].edit(disabled=True)
        except Exception: pass


class RPGCombatView(discord.ui.View):
    def __init__(self, ctx, state):
        super().__init__(timeout=180)
        self.ctx=ctx
        self.state=state
        self.message=None
        # Prevent rapid taps/stale Discord component interactions from
        # resolving multiple turns against the same battle message.
        self.processing=False
        self.resolved=False

    async def interaction_check(self, interaction):
        if interaction.user.id!=self.ctx.author.id:
            await interaction.response.send_message("This battle belongs to another hero.", ephemeral=True)
            return False
        if self.resolved:
            await interaction.response.send_message("This battle has already been resolved.", ephemeral=True)
            return False
        return True

    def _set_action_buttons(self, disabled):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled=disabled

    async def _act(self, interaction, action):
        if self.processing or self.resolved:
            await interaction.response.send_message("That battle action is already being processed.", ephemeral=True)
            return
        # A combat turn can touch SQLite, loot, XP, pets, and several other
        # systems. Discord requires an interaction to be acknowledged quickly;
        # waiting for combat_action() before deferring can cause the client to
        # show "This application did not respond" even though the turn
        # actually completed on the server. Acknowledge first, then process.
        await interaction.response.defer()
        self.processing=True
        self._set_action_buttons(True)
        try:
            result=await bot.rpg.combat_action(self.ctx.guild.id,self.ctx.author.id,action)
            if result.get("error"):
                self.processing=False
                self._set_action_buttons(False)
                await interaction.followup.send(result["error"], ephemeral=True)
                return
            if result.get("already_completed"):
                self.resolved=True
                self._set_action_buttons(True)
                await interaction.followup.send("🏆 This battle has already been resolved. No additional turn or rewards were applied.", ephemeral=True)
                self.stop()
                return
            if result.get("choose_item"):
                self.processing=False
                self._set_action_buttons(False)
                choices=result.get("items",[])
                await interaction.followup.send("🧪 **Choose exactly which item to use:**",ephemeral=True,view=RPGCombatItemView(self,choices))
                return
            if result.get("choose_skill"):
                self.processing=False
                self._set_action_buttons(False)
                await interaction.followup.send("✨ **Choose a skill:**",ephemeral=True,view=RPGCombatSkillView(self,result.get("skills",[])))
                return
            self.state=result.get("state",self.state)
            if result.get("finished"):
                self.resolved=True
                self._set_action_buttons(True)
                # Victory is terminal. If editing the deferred interaction fails,
                # fall back to a follow-up message so the player still sees the
                # result instead of an apparently dead battle panel.
                victory_embed=_combat_embed(self.state,result)
                try:
                    await interaction.edit_original_response(embed=victory_embed,view=self)
                except discord.HTTPException:
                    try:
                        await interaction.followup.send(embed=victory_embed,view=self)
                    except discord.HTTPException:
                        log.exception("Failed to deliver final victory panel: guild=%s user=%s",self.ctx.guild.id,self.ctx.author.id)
                self.stop()
                return
            self.processing=False
            self._set_action_buttons(False)
            await interaction.edit_original_response(embed=_combat_embed(self.state),view=self)
        except Exception:
            self.processing=False
            self._set_action_buttons(False)
            raise

    @discord.ui.button(label="Attack",emoji="⚔️",style=discord.ButtonStyle.primary)
    async def attack(self,interaction,button): await self._act(interaction,"attack")

    @discord.ui.button(label="Skills",emoji="✨",style=discord.ButtonStyle.success)
    async def skill(self,interaction,button): await self._act(interaction,"skill")

    @discord.ui.button(label="Pet Assist",emoji="🐾",style=discord.ButtonStyle.success)
    async def pet(self,interaction,button): await self._act(interaction,"pet")

    @discord.ui.button(label="Potion/Food",emoji="🧪",style=discord.ButtonStyle.secondary)
    async def potion(self,interaction,button): await self._act(interaction,"potion")

    @discord.ui.button(label="Defend",emoji="🛡️",style=discord.ButtonStyle.secondary)
    async def defend(self,interaction,button): await self._act(interaction,"defend")

    @discord.ui.button(label="Flee",emoji="🏃",style=discord.ButtonStyle.danger)
    async def flee(self,interaction,button): await self._act(interaction,"flee")

    async def on_timeout(self):
        # Keep the authoritative combat state alive in memory and in the
        # database. The old behavior removed the in-memory state here, which
        # could make a live battle appear dead while a stale Discord component
        # was still visible. The next !rpg adventure/!rpg dungeon command can
        # recover the same battle and rebuild its controls.
        for child in self.children: child.disabled=True
        if self.message:
            try: await self.message.edit(view=self)
            except Exception: pass


@bot.group(name="rpg", invoke_without_command=True)
async def rpg_root(ctx):
    await _rpg_delete(ctx)
    if ctx.invoked_subcommand is not None:
        return
    e=_rpg_embed("🌌 HORIZON RPG", "A persistent multiplayer RPG inside Log Horizon.")
    e.add_field(name="⚔️ Adventure", value="`!rpg adventure` — live battle\n`!rpg dungeon` — floor-by-floor dungeon", inline=False)
    e.add_field(name="🧬 Hero", value="`!rpg profile` • `!rpg change` • `!rpg evolve`", inline=True)
    e.add_field(name="🏰 Society", value="`!rpg party` • `!rpg guild` • `!rpg kingdom`", inline=True)
    e.add_field(name="👑 Endgame", value="`!rpg arena` • `!rpg raid` • `!rpg secretclasses` • `!rpg legendary`", inline=False)
    e.add_field(name="🎒 Collection", value="`!rpg inventory` • `!rpg items` • `!rpg eggs` • `!rpg pet`", inline=False)
    e.set_footer(text="Every RPG panel can be paged • use 🗑️ to remove it")
    await _rpg_panel(ctx,[e])

@rpg_root.command(name="help")
async def rpg_help(ctx):
    """Show every registered RPG command, including nested commands and aliases."""
    await _rpg_delete(ctx)

    # Short explanations for the commands that need a little more context.
    # Commands without a special entry still receive a useful generated
    # explanation, so newly added RPG commands automatically appear in help.
    descriptions = {
        "rpg": "Open the RPG home panel.",
        "rpg help": "Show this complete RPG command guide.",
        "rpg start": "Create your RPG hero with a name, race and class.",
        "rpg classes": "Browse playable classes and their starter skills.",
        "rpg class": "Inspect one class, its stats, strengths and skills.",
        "rpg races": "Browse playable races and their racial traits.",
        "rpg race": "Inspect one race, its bonuses and matchup notes.",
        "rpg subraces": "See the subraces available to each race.",
        "rpg subclasses": "Browse class specializations and their bonuses.",
        "rpg change": "Change an eligible character choice after confirmation.",
        "rpg evolve": "View or select an unlocked character evolution.",
        "rpg spend": "Spend available progression points on a supported stat.",
        "rpg profile": "Show your complete RPG character sheet.",
        "rpg stats": "Show your current combat and progression statistics.",
        "rpg stat": "Spend one Stat Point on a core stat.",
        "rpg skills": "Browse your class skills, mastery and active loadout.",
        "rpg skill": "Spend a Skill Point to increase a skill's mastery.",
        "rpg talents": "View your class and race talent trees.",
        "rpg talent": "Spend a Talent Point on a class or race talent.",
        "rpg equip-skill": "Put an unlocked skill into one of your four active slots.",
        "rpg adventure": "Start a normal PvE adventure battle.",
        "rpg dungeon": "Enter a dungeon and fight through its floors.",
        "rpg battle": "Challenge another player to a turn-based duel.",
        "rpg arena": "View your ranked rating or start a ranked PvP match.",
        "rpg season": "View the current ranked PvP season and leaderboard.",
        "rpg raid": "View the server raid or attack the shared raid boss.",
        "rpg worldboss": "Open world-boss controls.",
        "rpg worldboss spawn": "Spawn an available world boss.",
        "rpg worldboss attack": "Attack the active world boss with a skill.",
        "rpg secretclasses": "View hidden class requirements and awakening status.",
        "rpg awaken": "Awaken a secret class when its requirements are met.",
        "rpg legendary": "Browse legendary endgame trials.",
        "rpg challenge": "Attempt a legendary endgame challenge.",
        "rpg areas": "Browse the world atlas and known areas.",
        "rpg travel": "Travel to a connected or discovered area.",
        "rpg map": "Open the world map/atlas.",
        "rpg explore": "Explore your current area for discoveries and encounters.",
        "rpg dungeons": "Browse available dungeons and their requirements.",
        "rpg objectives": "View your daily and weekly objectives.",
        "rpg objective": "Claim a completed objective reward.",
        "rpg pending": "Recover any combat rewards that could not be delivered automatically.",
        "rpg inventory": "View the items currently in your inventory.",
        "rpg items": "Browse the item codex by category and page.",
        "rpg iteminfo": "Inspect one item, its stats and compatible details.",
        "rpg equipment": "Open your equipped gear and loadout.",
        "rpg equip": "Equip an item from your inventory.",
        "rpg use": "Consume a usable item such as food or a potion.",
        "rpg upgrade": "Upgrade equipped gear using materials and Gold.",
        "rpg vault": "View equipment stored safely in the Gear Vault.",
        "rpg vaultequip": "Move a stored Gear Vault item back into your loadout.",
        "rpg sets": "View equipment sets and their set bonuses.",
        "rpg enchantments": "Browse available enchantment types.",
        "rpg enchant": "Apply an available enchantment to eligible gear.",
        "rpg gacha": "View gacha rates, Gems, pulls and pity information.",
        "rpg open-chest": "Open a gacha chest from your inventory.",
        "rpg eggs": "View owned pet eggs.",
        "rpg hatch": "Hatch a pet egg and give the new pet a name.",
        "rpg adopt": "Adopt a starter companion if eligible.",
        "rpg pet": "Show your equipped companion.",
        "rpg pets": "View your full pet collection.",
        "rpg equip-pet": "Equip a pet from your collection.",
        "rpg unequip-pet": "Store your currently equipped pet.",
        "rpg petfeed": "Feed your active pet and improve its progression.",
        "rpg petcollection": "View pet species collected and discovered.",
        "rpg rename": "Rename your equipped pet.",
        "rpg release": "Release your currently equipped pet.",
        "rpg shop": "View the standard RPG shop and its available goods.",
        "rpg buy": "Buy an item from the standard RPG shop.",
        "rpg sell": "Sell an item to the standard RPG shop.",
        "rpg recipes": "Browse available crafting recipes.",
        "rpg craft": "Craft an item from a known recipe.",
        "rpg gather": "Gather materials from the current area.",
        "rpg fish": "Fish for materials and catches.",
        "rpg mine": "Mine for ore and other materials.",
        "rpg professions": "View your gathering and crafting profession levels.",
        "rpg economy": "View the RPG economy transaction log.",
        "rpg economyinfo": "View your economy statistics and transaction summary.",
        "rpg market": "Browse the player marketplace.",
        "rpg list": "List an eligible item on the player marketplace.",
        "rpg marketbuy": "Buy an active marketplace listing.",
        "rpg marketcancel": "Cancel one of your marketplace listings.",
        "rpg trade": "Start or view a direct player-to-player trade.",
        "rpg trades": "View your active trade offers.",
        "rpg tradeview": "Inspect a specific trade.",
        "rpg tradeadd": "Add an item to an active trade.",
        "rpg tradepet": "Add a pet to an active trade.",
        "rpg tradegold": "Add Gold to an active trade.",
        "rpg tradediamonds": "Add Diamonds to an active trade.",
        "rpg tradeclear": "Remove your offered items/currency from a trade.",
        "rpg tradeaccept": "Accept the current trade after reviewing it.",
        "rpg tradecancel": "Cancel an active trade.",
        "rpg quests": "Open the unified Quest 2.0 board.",
        "rpg quests accept": "Accept an available quest.",
        "rpg quests claim": "Claim the reward for a completed quest.",
        "rpg quest": "Open a specific quest by its ID.",
        "rpg claim": "Claim a completed quest by its ID.",
        "rpg journal": "View your quest journal and objective progress.",
        "rpg party": "View your current party or party directory.",
        "rpg party create": "Create an adventure party.",
        "rpg party join": "Join an existing party by ID.",
        "rpg party leave": "Leave your current party.",
        "rpg party dungeon": "Start a dungeon run for your party.",
        "rpg party info": "View party members and party details.",
        "rpg guild": "View your guild or the guild directory.",
        "rpg guild list": "List guilds in the server.",
        "rpg guild create": "Create a new guild.",
        "rpg guild join": "Join an existing guild.",
        "rpg guild info": "Inspect a guild's level, bank and members.",
        "rpg guild members": "List the members of your guild.",
        "rpg guild leave": "Leave your current guild.",
        "rpg guild deposit": "Deposit Gold into your guild treasury.",
        "rpg guild upgrade": "Upgrade your guild using its available resources.",
        "rpg kingdom": "View your kingdom or the kingdom directory.",
        "rpg kingdom list": "List kingdoms in the server.",
        "rpg kingdom create": "Create a new kingdom.",
        "rpg kingdom join": "Join an existing kingdom.",
        "rpg kingdom info": "Inspect a kingdom's level, treasury and members.",
        "rpg kingdom appoint": "Appoint a kingdom member to an available role.",
        "rpg kingdom leave": "Leave your current kingdom.",
        "rpg bounty": "View the server bounty board.",
        "rpg bounty list": "List active bounties.",
        "rpg bounty post": "Post a bounty with a Gold reward.",
        "rpg bounty claim": "Claim a completed bounty reward.",
        "rpg social": "View your social, party, guild and trade activity.",
        "rpg titles": "View titles and title progress you have earned.",
        "rpg achievements": "View your RPG achievements and progress.",
        "rpg leaderboard": "View server RPG leaderboards.",
        "rpg factions": "Browse the server's major factions.",
        "rpg factionjoin": "Join an available faction.",
        "rpg endgamemastery": "View your Endgame Mastery progression.",
        "rpg ascend": "Ascend when you meet the Endgame Mastery requirements.",
    }

    def pretty(name):
        return name.replace("-", " ").title()

    def usage(command):
        params = []
        for key, param in getattr(command, "clean_params", {}).items():
            # Discord.py's Parameter objects expose required/default information;
            # keep the help compact rather than dumping Python type annotations.
            required = getattr(param, "required", False)
            params.append(f"<{key}>" if required else f"[{key}]")
        return "!" + command.qualified_name + (" " + " ".join(params) if params else "")

    def command_entry(command):
        q = command.qualified_name
        aliases = list(getattr(command, "aliases", []) or [])
        alias_text = f" • aliases: {', '.join('`'+a+'`' for a in aliases)}" if aliases else ""
        desc = descriptions.get(q)
        if not desc:
            if isinstance(command, commands.Group):
                desc = f"Open the {pretty(command.name)} RPG menu and its subcommands."
            else:
                desc = f"Use this command to manage {pretty(command.name).lower()} in your RPG."
        return f"`{usage(command)}`{alias_text}\n{desc}"

    def walk(group):
        # Include the group itself, then every nested command.
        yield group
        for child in sorted(group.commands, key=lambda c: c.qualified_name):
            if isinstance(child, commands.Group):
                yield from walk(child)
            else:
                yield child

    commands_to_show = list(walk(rpg_root))
    # Put the most useful entry points first; everything else remains alphabetic.
    priority = {"rpg": 0, "rpg help": 1, "rpg start": 2, "rpg profile": 3, "rpg adventure": 4, "rpg quests": 5, "rpg party": 6, "rpg guild": 7, "rpg equipment": 8, "rpg inventory": 9}
    commands_to_show.sort(key=lambda c: (priority.get(c.qualified_name, 100), c.qualified_name))

    # Discord embeds have a finite description/field budget. Ten commands per
    # page keeps this complete guide readable on mobile while still being fast.
    pages = []
    page_size = 8
    for index in range(0, len(commands_to_show), page_size):
        chunk = commands_to_show[index:index + page_size]
        page_no = index // page_size + 1
        total = (len(commands_to_show) + page_size - 1) // page_size
        e = _rpg_embed(f"📖 Horizon RPG — Complete Command Guide", "\n\n".join(command_entry(c) for c in chunk))
        e.set_footer(text=f"Page {page_no}/{total} • {len(commands_to_show)} RPG commands • Use the buttons to browse")
        pages.append(e)
    await _rpg_panel(ctx, pages)

@rpg_root.command(name="pending", aliases=["pending-rewards", "pendingrewards"])
async def rpg_pending_rewards(ctx):
    """Recover durable rewards that failed during automatic combat processing."""
    await _rpg_delete(ctx)
    ok, msg = await bot.rpg.claim_pending_rewards(ctx.guild.id, ctx.author.id)
    await _rpg_action_panel(ctx, "🎁 Pending Rewards", msg, ok)


@rpg_root.command(name="start")
async def rpg_start(ctx, name: str = "", race: str = "human", class_name: str = "warrior"):
    await _rpg_delete(ctx)
    if not name:
        await _rpg_action_panel(ctx,"Hero Creation","Use `!rpg start <name> <race> <class>`.\nSee `!rpg races` and `!rpg classes` for the expanded choices.",False); return
    try:
        ok, text = await bot.rpg.create_player(ctx.guild.id, ctx.author.id, name, race, class_name)
    except ValueError:
        ok, text = False, "Invalid race or class. Use `!rpg races` and `!rpg classes`."
    await _rpg_action_panel(ctx, "Hero Creation", text, ok)


@rpg_root.command(name="classes")
async def rpg_classes(ctx):
    await _rpg_delete(ctx)
    rows=[(k,v) for k,v in CLASSES.items() if k not in SECRET_CLASS_KEYS]
    def fmt(x):
        key,data=x; skills=SKILLS.get(key,[])[:6]; profile=CLASS_PROFILES.get(key,{"strength":data['desc'],"weakness":"No special weakness listed."})
        return (f"**{key.replace('_',' ').title()}** · {data.get('resource','Resource')}\n{data['desc']}\n"
                f"🟢 {profile['strength']}\n🔴 {profile['weakness']}\n"
                f"❤️ HP +{data['hp']} • 💧 MP +{data['mp']} • ⚔️ ATK +{data['atk']} • 🛡️ DEF +{data['def']} • 💨 SPD +{data['spd']} • 🎯 Crit +{data['crit']}%\n"
                f"✨ Starter skills: {', '.join(sk['name'] for sk in skills)}\n`!rpg class {key}` for full details, strengths and counters.")
    await _rpg_panel(ctx,_rpg_pages("Class Selection Guide",rows,page_size=4,icon="⚔️",formatter=fmt))

@rpg_root.command(name="class", aliases=["classinfo","class-info"])
async def rpg_class_info(ctx, *, class_name: str = ""):
    await _rpg_delete(ctx)
    key=class_name.lower().strip()
    if key in SECRET_CLASS_KEYS:
        data=SECRET_CLASSES[key]
        unlocked_rows=await bot.rpg.secret_class_list(ctx.guild.id,ctx.author.id)
        unlocked=next((x[2] for x in unlocked_rows if x[0]==key),False)
        status="AWAKENED" if unlocked else "SECRET / LOCKED"
        body=(f"**{data['desc']}**\n\n**Status:** {status}\n**Requirement:** {data['requirement']}\n\n"
              f"❤️ HP +{data['hp']} • 💧 MP +{data['mp']} • ⚔️ ATK +{data['atk']} • 🛡️ DEF +{data['def']} • 💨 SPD +{data['spd']} • 🎯 Crit +{data['crit']}%\n"
              f"**Resource:** {data['resource']}\n\nUse `!rpg awaken {key}` when the requirement is met.")
        await _rpg_action_panel(ctx,"🌌 Secret Class — "+data['name'],body,True); return
    if key not in CLASSES:
        await _rpg_action_panel(ctx,"Class Details","Use `!rpg classes` first, then `!rpg class <class>`." ,False); return
    data=CLASSES[key]; skills=bot.rpg.skills_for_player({"class_name":key})
    strong=[k.replace('_',' ').title() for k,v in CLASS_MATCHUPS.get(key,{}).items() if v>1]
    weak=[k.replace('_',' ').title() for k,v in CLASS_MATCHUPS.items() if key in v and v[key]<1]
    profile=CLASS_PROFILES.get(key,{"strength":data.get("desc","Flexible class"),"weakness":"No special weakness listed."})
    body=(f"**{data['desc']}**\n\n**Resource:** {data.get('resource','Resource')}\n"
          f"❤️ HP +{data['hp']} • 💧 MP +{data['mp']} • ⚔️ ATK +{data['atk']} • 🛡️ DEF +{data['def']} • 💨 SPD +{data['spd']} • 🎯 Crit +{data['crit']}%\n\n"
          f"🟢 **Core strength:** {profile['strength']}\n"
          f"🔴 **Core weakness:** {profile['weakness']}\n"
          f"**Matchup advantages:** {', '.join(strong) or 'None'}\n"
          f"**Matchup disadvantages:** {', '.join(weak) or 'None'}\n\n"
          "**Skill progression:** 20 skills per class. The first 12 are class-defining; start with 3 and unlock more from Lv 6 onward. Only 4 can be active at once.\n"
          + "\n".join(f"`{sk['key']}` · **{sk['name']}** · Lv {sk['unlock']} · {sk['cost']} MP · **{sk['mechanic']}** — {sk['desc']}" for sk in skills[:12])
          + "\n\nUse `!rpg skills` to browse all unlocked skills and `!rpg equip-skill <skill_key> <slot>` to choose your four active skills.")
    e=_rpg_embed(f"⚔️ {key.title()} — Full Class Preview",body); e.set_image(url=_rpg_image_url("character",key)); await _rpg_panel(ctx,[e])

@rpg_root.command(name="races")
async def rpg_races(ctx):
    await _rpg_delete(ctx)
    rows=list(RACES.items())
    def fmt(x):
        key,data=x; strong=[k.replace('_',' ').title() for k,v in RACE_MATCHUPS.get(key,{}).items() if v>1]; weak=[k.replace('_',' ').title() for k,v in RACE_MATCHUPS.items() if key in v and v[key]<1]
        ability=RACE_ABILITIES.get(key,("Ability",""))[0]
        return (f"**{key.replace('_',' ').title()}** · {ability}\n{data['desc']}\n❤️ HP {data['hp']:+} • ⚔️ ATK {data['atk']:+} • 🛡️ DEF {data['def']:+} • 💨 SPD {data['spd']:+} • 🎯 Crit {data['crit']:+}%\n"
                f"Strong vs: {', '.join(strong) or '—'} • Weaker vs: {', '.join(weak) or '—'}\n`!rpg race {key}` for the full preview.")
    await _rpg_panel(ctx,_rpg_pages("Race Selection Guide",rows,page_size=4,icon="🧬",formatter=fmt))

@rpg_root.command(name="race", aliases=["raceinfo","race-info"])
async def rpg_race_info(ctx, *, race: str = ""):
    await _rpg_delete(ctx); key=race.lower().strip()
    if key not in RACES:
        await _rpg_action_panel(ctx,"Race Details","Use `!rpg races` first, then `!rpg race <race>`.",False); return
    data=RACES[key]; strong=[k.replace('_',' ').title() for k,v in RACE_MATCHUPS.get(key,{}).items() if v>1]; weak=[k.replace('_',' ').title() for k,v in RACE_MATCHUPS.items() if key in v and v[key]<1]; ability,ability_desc=RACE_ABILITIES.get(key,("Unknown","")); profile=RACE_PROFILES.get(key,{"strength":data.get("desc","Balanced"),"weakness":"No special weakness listed."})
    e=_rpg_embed(f"🧬 {key.title()} — Full Race Preview",f"**{data['desc']}**\n\n**Racial ability:** {ability} — {ability_desc}\n\n❤️ HP {data['hp']:+} • ⚔️ ATK {data['atk']:+} • 🛡️ DEF {data['def']:+} • 💨 SPD {data['spd']:+} • 🎯 Crit {data['crit']:+}%\n\n🟢 **Core strength:** {profile['strength']}\n🔴 **Core weakness:** {profile['weakness']}\n\n**Matchup advantages:** {', '.join(strong) or 'None'}\n**Matchup disadvantages:** {', '.join(weak) or 'None'}\n\nRace matchups are now meaningful enough to matter, but not so extreme that they hard-lock a build.\n\nUse `!rpg subraces {key}` to see the subraces available to this race.")
    e.set_image(url=_rpg_image_url("character",key)); await _rpg_panel(ctx,[e])

@rpg_root.command(name="subraces")
async def rpg_subraces(ctx, *, race: str = ""):
    await _rpg_delete(ctx)
    race=race.lower().strip()
    rows=[(k,v) for k,v in SUBRACES.items() if not race or v[0]==race]
    if not rows:
        await _rpg_action_panel(ctx,"Subraces","No matching subraces. Use `!rpg subraces <race>`.",False); return
    pages=_rpg_pages("Subraces",rows,page_size=6,icon="🧬",formatter=lambda x:f"**{x[0].replace('_',' ').title()}** → {x[1][0].title()}\n❤️ HP {x[1][1]['hp']:+} • ⚔️ ATK {x[1][1]['atk']:+} • 🛡️ DEF {x[1][1]['def']:+} • 💨 SPD {x[1][1]['spd']:+} • 🎯 Crit {x[1][1]['crit']:+}%\n✨ **{SUBRACE_TRAITS.get(x[0],{}).get('name','Unique Trait')}** — {SUBRACE_TRAITS.get(x[0],{}).get('desc','No special trait.')}")
    await _rpg_panel(ctx,pages)
@rpg_root.command(name="subclasses")
async def rpg_subclasses(ctx, *, class_name: str = ""):
    await _rpg_delete(ctx)
    class_name=class_name.lower().strip()
    rows=[(k,v) for k,v in SUBCLASSES.items() if not class_name or v[0]==class_name]
    if not rows:
        await _rpg_action_panel(ctx,"Subclasses","No matching subclasses. Use `!rpg subclasses <class>`.",False); return
    pages=_rpg_pages("Subclasses • Level 10+",rows,page_size=4,icon="⚔️",formatter=lambda x:f"**{x[0].replace('_',' ').title()}** → {x[1][0].title()}\n{x[1][1]}\n✨ **{SUBCLASS_TRAITS.get(x[0],{}).get('name','Unique Trait')}** — {SUBCLASS_TRAITS.get(x[0],{}).get('desc','No special trait.')}\n\n⚔️ **Skills:** {", ".join(s["name"] for s in SUBCLASS_SKILLS.get(x[0],[])[:6])}")
    await _rpg_panel(ctx,pages)
@rpg_root.command(name="change")
async def rpg_change(ctx, kind: str = "", *, value: str = ""):
    await _rpg_delete(ctx)
    if not kind or not value:
        await _rpg_action_panel(ctx,"Build Change","Use `!rpg change <race|subrace|class|subclass|path|evolution> <name>`.\n\nImportant identity changes always require confirmation before gold is spent or your build is changed.",False); return
    p=await bot.rpg.player(ctx.guild.id,ctx.author.id)
    if not p:
        await _rpg_action_panel(ctx,"Build Change","Create a hero first.",False); return
    kind=kind.lower().strip(); value=value.lower().strip()
    costs={"race":1500,"class":1200,"subrace":2200,"subclass":3000,"path":1800,"evolution":5000}
    if kind not in costs:
        await _rpg_action_panel(ctx,"Build Change","Choose race, subrace, class, subclass, path or evolution.",False); return
    summary=(f"You are about to change **{kind}** to **{value.replace('_',' ').title()}**.\n\n"
             f"💰 Cost: **{costs[kind]} gold**\n"
             f"⚠️ This can replace your current {kind} choice and may change your combat stats.\n\n"
             "Press **Confirm** only if you have reviewed the choice.")
    async def confirm():
        return await bot.rpg.change_identity(ctx.guild.id,ctx.author.id,kind,value)
    view=RPGConfirmationView(ctx,"Confirm Build Change",summary,confirm)
    view.message=await ctx.send(embed=_rpg_embed("⚠️ Confirm Important Change",summary),view=view)


@rpg_root.command(name="evolve")
async def rpg_evolve(ctx, *, evolution: str = ""):
    await _rpg_delete(ctx)
    p=await bot.rpg.player(ctx.guild.id,ctx.author.id)
    if not p:
        await _rpg_action_panel(ctx,"Evolution","Create a hero first.",False); return
    available=[(lvl,name) for lvl,name in CLASS_EVOLUTIONS.get(p["class_name"],[]) if p["level"]>=lvl]
    if not evolution:
        if not available:
            next_req=CLASS_EVOLUTIONS.get(p["class_name"],[(20,"evolution")])[0][0]
            await _rpg_action_panel(ctx,"Evolution",f"Your next evolution unlocks at level **{next_req}**.",False); return
        pages=_rpg_pages("Available Evolutions",available,page_size=6,icon="✨",formatter=lambda x:f"**{x[1]}**\nUnlocked at level **{x[0]}**")
        await _rpg_panel(ctx,pages); return
    ok,msg=await bot.rpg.change_identity(ctx.guild.id,ctx.author.id,"evolution",evolution)
    await _rpg_action_panel(ctx,"Evolution",msg,ok)


@rpg_root.command(name="spend")
async def rpg_spend(ctx, stat: str = "", points: int = 1):
    await _rpg_delete(ctx)
    ok,msg=await bot.rpg.spend_stat(ctx.guild.id,ctx.author.id,stat,points)
    await _rpg_action_panel(ctx, "Stat Upgrade", msg, ok)


@rpg_root.command(name="areas")
async def rpg_areas(ctx):
    await _rpg_delete(ctx)
    rows=list(AREAS.items())
    pages=_rpg_pages("World Atlas",rows,page_size=5,icon="🗺️",formatter=lambda x:f"**{x[1]['name']}** — `{x[0]}`\nLv **{x[1]['level']}+** • {x[1]['type'].title()}\n{x[1]['desc']}")
    await _rpg_panel(ctx,pages)
@rpg_root.command(name="travel")
async def rpg_travel(ctx, *, area: str = ""):
    await _rpg_delete(ctx)
    if not area:
        await _rpg_action_panel(ctx,"Travel","Use `!rpg travel <area_key>`. See `!rpg areas`.",False); return
    ok,msg=await bot.rpg.travel(ctx.guild.id,ctx.author.id,area)
    await _rpg_action_panel(ctx, "Travel", msg, ok)


@rpg_root.command(name="map", aliases=["worldmap", "atlas"])
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
    pages=_rpg_pages("🎯 Quest 2.0 • Daily / Weekly / Monthly",rows,page_size=4,icon="🎯",formatter=fmt)
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

@rpg_root.command(name="profile", aliases=["character", "sheet"])
async def rpg_profile(ctx):
    await _rpg_delete(ctx)
    data=await bot.rpg.stats(ctx.guild.id,ctx.author.id)
    if not data:
        await _rpg_action_panel(ctx, "Hero Required", "Start your hero with `!rpg start <name> <race> <class>`.", False); return
    p,gear,b=data
    xp_next=bot.rpg._level_xp(p['level'])
    equipment="\n".join(f"**{slot.title()}** — {ITEMS.get(item, {'name':item})['name']}" for slot,item in gear.items()) or "No equipment"
    e=_rpg_embed(f"⚔️ {p['name']}",
        f"**Level {p['level']} {p['race'].title()} {p['class_name'].title()}** • {p['title']}\n"
        f"Subrace: **{p.get('subrace') or 'None'}** • Subclass: **{p.get('subclass') or 'None'}** • Evolution: **{p.get('evolution') or 'None'}**\n"
        f"Kingdom: **{p.get('kingdom_name') or 'None'}** ({p.get('kingdom_role') or 'wanderer'})\n"
        f"XP **{p['xp']}/{xp_next}** • Gold **{p['gold']}** • Gems **{p.get('gems',0)}** • Prestige **{p['prestige']}** • Renown **{p.get('renown',0)}**\n"
        f"❤️ HP **{p['hp']+b['hp']}/{p['max_hp']+b['hp']}** • 💧 MP **{p['mp']+b['mp']}/{p['max_mp']+b['mp']}** • ⚡ Stamina **{p['stamina']}/100**\n"
        f"⚔️ ATK **{p['atk']+b['atk']}** • 🛡️ DEF **{p['defense']+b['defense']}** • 💨 SPD **{p['speed']+b['speed']}** • 🎯 Crit **{p['crit']+b['crit']}%**\n"
        f"Gear % bonuses: ATK +{b.get('pct',{}).get('atk',0)}% • DEF +{b.get('pct',{}).get('defense',0)}% • HP +{b.get('pct',{}).get('hp',0)}% • MP +{b.get('pct',{}).get('mp',0)}% • SPD +{b.get('pct',{}).get('speed',0)}% • Crit +{b.get('pct',{}).get('crit',0)}%\n"
        f"Unspent: **{p.get('stat_points',0)} stat** / **{p.get('skill_points',0)} skill** / **{p.get('talent_points',0)} talent** points\n"
        f"📍 Location: **{p['location']}**\n\n**Equipment**\n{equipment}")
    e.set_image(url=_character_image(p))
    pet=await bot.rpg.pet_record(ctx.guild.id,ctx.author.id)
    if pet:
        e.add_field(name="🐾 Companion",value=f"**{pet['name']}** · {pet['species']} · Lv {pet['level']}\n+{pet['bonus_atk']} ATK • +{pet['bonus_def']} DEF • +{pet.get('bonus_hp',0)} HP • +{pet.get('bonus_speed',0)} SPD • +{pet.get('bonus_crit',0)}% Crit\nAbility: **{pet.get('ability','Pet Assist')}**",inline=False)
    await _rpg_panel(ctx,[e])
@rpg_root.command(name="stats")
async def rpg_stats(ctx):
    await rpg_profile.callback(ctx)


@rpg_root.command(name="equipment", aliases=["gear", "loadout", "equipui"])
async def rpg_equipment(ctx):
    """Open an interactive equipment loadout with one dropdown per slot."""
    await _rpg_delete(ctx)
    data=await bot.rpg.stats(ctx.guild.id,ctx.author.id)
    if not data:
        await _rpg_action_panel(ctx,"Hero Required","Start your hero with `!rpg start <name> <race> <class>`.",False); return
    inventory_rows=await bot.rpg.inventory(ctx.guild.id,ctx.author.id)
    _,gear,_=data
    view=RPGEquipmentLoadoutView(ctx,inventory_rows,gear,page=0)
    embed=await view.render()
    view.message=await ctx.send(embed=embed,view=view)


@rpg_root.command(name="adventure", aliases=["hunt"])
async def rpg_adventure(ctx):
    await _rpg_delete(ctx)
    result=await bot.rpg.start_combat(ctx.guild.id,ctx.author.id,"adventure")
    if "error" in result:
        await _rpg_action_panel(ctx,"Adventure",result["error"],False); return
    view=RPGCombatView(ctx,result["state"])
    view.message=await ctx.send(embed=_combat_embed(result["state"]),view=view)


@rpg_root.command(name="rest")
async def rpg_rest(ctx):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.rest(ctx.guild.id,ctx.author.id); await _rpg_action_panel(ctx, "Rest", msg, ok)


@rpg_root.command(name="daily")
async def rpg_daily(ctx):
    await _rpg_delete(ctx); result,msg=await bot.rpg.daily(ctx.guild.id,ctx.author.id)
    if msg: await _rpg_action_panel(ctx,"Daily Chest",msg,False); return
    xp,gold,gems,level=result; await _rpg_action_panel(ctx, "Daily Chest", f"🎁 **Daily chest opened!**\n\n+**{gold} gold**\n+**{gems} Gems**\n+**{xp} XP**\nCurrent level: **{level}**", True)


@rpg_root.command(name="inventory", aliases=["inv"])
async def rpg_inventory(ctx):
    await _rpg_delete(ctx); ok=await _rpg_require(ctx)
    if not ok:return
    rows=await bot.rpg.inventory(ctx.guild.id,ctx.author.id)
    per_page=8
    pages=[]
    for n in range(max(1,(len(rows)+per_page-1)//per_page)):
        chunk=rows[n*per_page:(n+1)*per_page]
        lines=[]
        for key,qty in chunk:
            d=ITEMS.get(key,{})
            lines.append(f"**{d.get('name',key)}** × **{qty}**\n`{key}` • {d.get('rarity','common').title()} • {d.get('slot','item').title()}")
        e=_rpg_embed(f"🎒 {ctx.author.display_name}'s Inventory", "\n\n".join(lines) if lines else "Your inventory is empty.")
        e.set_footer(text=f"Page {n+1} / {max(1,(len(rows)+per_page-1)//per_page)} • {len(rows)} item stacks")
        pages.append(e)
    options_by_page=[]
    for start in range(0,len(rows),per_page):
        page_opts=[]
        for key,qty in rows[start:start+per_page]:
            d=ITEMS.get(key,{})
            page_opts.append((key,d.get('name',key),f"{d.get('rarity','common').title()} • {qty} owned"))
        options_by_page.append(page_opts)
    if not options_by_page: options_by_page=[[]]
    async def item_info(interaction,value):
        d=ITEMS.get(value,{})
        stats=[]
        for k,label in (("atk","ATK"),("def","DEF"),("hp","HP"),("mp","MP"),("spd","SPD"),("crit","Crit"),("heal","Heal"),("mana","Mana"),("price","Value")):
            if k in d: stats.append(f"**{label}:** {d[k]}" + ("%" if k=="crit" else ""))
        owned=dict(rows).get(value,0)
        e=_rpg_embed(f"📦 {d.get('name',value)}", f"**Rarity:** {d.get('rarity','common').title()}\n**Type:** {d.get('slot','item').title()}\n**Owned:** {owned}\n\n"+" • ".join(stats) if stats else f"**Owned:** {owned}")
        await interaction.response.send_message(embed=e,ephemeral=True)
    await _rpg_panel(ctx,pages,select_options=options_by_page[0],select_callback=item_info,select_options_by_page=options_by_page)
@rpg_root.command(name="items", aliases=["item", "codex"])
async def rpg_items(ctx, category: str = "all", page: int = 1):
    await _rpg_delete(ctx)
    category=category.lower().strip() or "all"
    allowed={"all","weapon","armor","offhand","consumable","food","material","egg","relic","accessory","ring","amulet","chest"}
    if category not in allowed:
        await _rpg_action_panel(ctx,"Item Codex","Categories: `all`, `weapon`, `armor`, `offhand`, `accessory`, `ring`, `amulet`, `consumable`, `food`, `material`, `egg`, `relic`, `chest`.\nExample: `!rpg items weapon 2`.",False); return
    rows=[(k,v) for k,v in ITEMS.items() if category=="all" or v.get("slot")==category]
    rarity_order={r:i for i,r in enumerate(RARITIES)}
    rows.sort(key=lambda x:(rarity_order.get(x[1].get('rarity','common'),0),int(x[1].get('level_req',1)),x[1].get('name',x[0])))
    per_page=6; total=max(1,(len(rows)+per_page-1)//per_page); page=min(max(1,int(page)),total)
    pages=[]
    for n in range(total):
        chunk=rows[n*per_page:(n+1)*per_page]
        lines=[]
        for k,v in chunk:
            pct=[]
            for field,label in (("pct_atk","ATK"),("pct_def","DEF"),("pct_hp","HP"),("pct_mp","MP"),("pct_speed","SPD"),("pct_crit","Crit")):
                if v.get(field): pct.append(f"+{v[field]}% {label}")
            lines.append(f"**{v.get('name',k)}**\n`{k}` • {v.get('rarity','common').title()} • Lv {v.get('level_req',1)}+ • {v.get('slot','item').title()} • {v.get('price',0)}g • {v.get('enchant_slots',0)} empty enchant slot(s)\n" + (" • ".join(pct) if pct else "Base item — no intrinsic % bonus"))
        e=_rpg_embed(f"📚 Item Codex — {category.title()}","\n\n".join(lines) or "No items in this category.")
        e.set_footer(text=f"Page {n+1} / {total} • {len(rows)} items • Use `!rpg iteminfo <key>` for exact details")
        pages.append(e)
    options_by_page=[[(k,v.get('name',k),f"{v.get('rarity','common').title()} • Lv {v.get('level_req',1)}+") for k,v in rows[start:start+per_page]] for start in range(0,len(rows),per_page)] or [[]]
    async def info(interaction,value):
        d=ITEMS.get(value,{})
        stats=[f"**{label}:** {d[k]}" + ("%" if k.startswith("pct_") or k=="crit" else "") for k,label in (("atk","ATK"),("def","DEF"),("hp","HP"),("mp","MP"),("spd","SPD"),("crit","Crit"),("heal","Heal"),("mana","Mana"),("stamina","Stamina"),("pct_atk","ATK %"),("pct_def","DEF %"),("pct_hp","HP %"),("pct_mp","MP %"),("pct_speed","SPD %"),("pct_crit","Crit %")) if k in d and d[k]]
        compatible=compatible_enchantments(d) if d.get('slot') in ENCHANTMENT_COMPATIBILITY else []
        enchant_lines=[f"• **{e['name']}** — {e['desc']} (`{key}`)" for key,e in compatible]
        desc=(f"**Rarity:** {d.get('rarity','common').title()}\n**Type:** {d.get('slot','item').title()}\n**Level requirement:** {d.get('level_req',1)}\n**Empty enchantment slots:** {d.get('enchant_slots',0)}\n"
              + ("\n".join(stats) if stats else "No extra stats.")
              + ("\n\n**Compatible Enchantments**\n" + "\n".join(enchant_lines) if enchant_lines else ""))
        await interaction.response.send_message(embed=_rpg_embed(f"📦 {d.get('name',value)} — Full Preview",desc),ephemeral=True)
    view=RPGPaginationView(ctx,pages,select_options=options_by_page[page-1],select_callback=info,select_options_by_page=options_by_page)
    view.index=page-1; view._sync(); view.message=await ctx.send(embed=view.pages[view.index],view=view)

@rpg_root.command(name="iteminfo", aliases=["inspect","item-info"])
async def rpg_item_info(ctx, *, item_key: str = ""):
    await _rpg_delete(ctx)
    d=ITEMS.get(item_key.lower().strip())
    if not d:
        await _rpg_action_panel(ctx,"Item Details","Unknown item. Use `!rpg items` to browse the full classified catalogue.",False); return
    pct=[f"+{d[k]}% {label}" for k,label in (("pct_atk","ATK"),("pct_def","DEF"),("pct_hp","HP"),("pct_mp","MP"),("pct_speed","SPD"),("pct_crit","Crit")) if d.get(k)]
    stats=[f"**{label}:** {d[k]}" + ("%" if k=="crit" else "") for k,label in (("atk","ATK"),("def","DEF"),("hp","HP"),("mp","MP"),("spd","SPD"),("crit","Crit")) if d.get(k)]
    compatible=compatible_enchantments(d) if d.get('slot') in ENCHANTMENT_COMPATIBILITY else []
    enchant_lines=[f"• **{e['name']}** — {e['desc']} (`{key}`)" for key,e in compatible]
    desc=f"**Base Item — no enchantment applied**\n\nRarity: **{d.get('rarity','common').title()}**\nCategory: **{d.get('slot','item').title()}**\nLevel requirement: **{d.get('level_req',1)}**\nValue: **{d.get('price',0)} gold**\nEmpty enchantment slots: **{d.get('enchant_slots',0)}**\n"
    if stats: desc += "\n**Base Stats**\n" + " • ".join(stats) + "\n"
    if pct: desc+=f"\n**Intrinsic percentage bonuses:** {' • '.join(pct)}\n"
    if enchant_lines: desc += "\n**Enchantments You Can Equip**\n" + "\n".join(enchant_lines)
    e=_rpg_embed(f"📦 {d['name']} — Full Preview",desc); e.set_image(url=_rpg_image_url("item",item_key)); await _rpg_panel(ctx,[e])

@bot.command(name="items", aliases=["item"])
async def prefix_items(ctx, category: str = "all", page: int = 1):
    # Direct !items / !item aliases make the old item command path reliable even
    # if a user forgets the !rpg group prefix.
    await rpg_items.callback(ctx, category, page)

@rpg_root.command(name="eggs")
async def rpg_eggs(ctx):
    """Show the eggs the player actually owns and the simple hatch command."""
    await _rpg_delete(ctx)
    if not await _rpg_require(ctx): return
    inventory=await bot.rpg.inventory(ctx.guild.id,ctx.author.id)
    owned=[(k,q,ITEMS[k]) for k,q in inventory if q>0 and ITEMS.get(k,{}).get("slot")=="egg"]
    if not owned:
        await _rpg_action_panel(ctx,"🥚 Your Eggs","You don't have any eggs yet. Find eggs while adventuring or in dungeon loot.",False)
        return
    lines=[f"🥚 **{d['name']}** ×{q} — {d.get('rarity','common').title()}\n`!rpg hatch {k}` or `!rpg hatch {k} <name>`" for k,q,d in owned]
    text="\n\n".join(lines)
    text += "\n\n**Simple pet commands**\n`!rpg pet` — view your pet\n`!rpg hatch <egg>` — hatch an egg\n`!rpg adopt <name>` — adopt a random companion\n`!rpg rename <name>` — rename your pet\n`!rpg release` — release your pet"
    await _rpg_action_panel(ctx,"🥚 Pet Eggs",text,True)

@rpg_root.command(name="hatch")
async def rpg_hatch(ctx,egg_key:str="",*,name:str="Spirit"):
    """Simple shortcut: !rpg hatch <egg> [name]."""
    await _rpg_delete(ctx)
    if not egg_key:
        await _rpg_action_panel(ctx,"🥚 Hatch","Use `!rpg hatch <egg>` or `!rpg hatch <egg> <name>`.\nExample: `!rpg hatch common_egg Luna`",False)
        return
    pet_name=(name or "Spirit").strip() or "Spirit"
    ok,msg=await bot.rpg.egg_hatch(ctx.guild.id,ctx.author.id,egg_key,pet_name)
    await _rpg_action_panel(ctx,"🥚 Hatch Egg",msg,ok)

@rpg_root.command(name="adopt")
async def rpg_adopt(ctx,*,name:str="Spirit"):
    """Simple shortcut: !rpg adopt [name]."""
    await _rpg_delete(ctx)
    pet_name=(name or "Spirit").strip() or "Spirit"
    ok,msg=await bot.rpg.pet(ctx.guild.id,ctx.author.id,"adopt",pet_name)
    await _rpg_action_panel(ctx,"🐾 Adopt Pet",msg,ok)

@rpg_root.command(name="rename")
async def rpg_rename(ctx,*,name:str=""):
    await _rpg_delete(ctx)
    if not name.strip():
        await _rpg_action_panel(ctx,"🐾 Rename Pet","Use `!rpg rename <new name>`.",False)
        return
    ok,msg=await bot.rpg.pet(ctx.guild.id,ctx.author.id,"rename",name.strip())
    await _rpg_action_panel(ctx,"🐾 Rename Pet",msg,ok)

@rpg_root.command(name="release")
async def rpg_release(ctx):
    await _rpg_delete(ctx)
    ok,msg=await bot.rpg.pet(ctx.guild.id,ctx.author.id,"release")
    await _rpg_action_panel(ctx,"🐾 Release Pet",msg,ok)
@rpg_root.command(name="use")
async def rpg_use(ctx, item_key: str = "", quantity: int = 1):
    await _rpg_delete(ctx)
    if not await _rpg_require(ctx): return
    rows=await bot.rpg.inventory(ctx.guild.id,ctx.author.id)
    usable=[(k,q) for k,q in rows if q>0 and ITEMS.get(k,{}).get("slot") in {"consumable","food"}]
    if not item_key:
        if not usable:
            await _rpg_action_panel(ctx,"Use Item","You don't have any usable potions or food.",False); return
        options=[(k,ITEMS[k]["name"],f"{ITEMS[k].get('rarity','common').title()} • {q} owned") for k,q in usable[:25]]
        async def choose(interaction,value):
            ok,msg=await bot.rpg.use_item(ctx.guild.id,ctx.author.id,value,1)
            await interaction.response.edit_message(embed=_rpg_action_embed("Use Item",msg,ok),view=None)
        view=RPGPaginationView(ctx,[_rpg_embed("🧪 Use an Item","Choose the potion or food you want to consume from the menu below.")],select_options=options,select_callback=choose)
        view.message=await ctx.send(embed=view.pages[0],view=view); return
    ok,msg=await bot.rpg.use_item(ctx.guild.id,ctx.author.id,item_key,quantity)
    await _rpg_action_panel(ctx,"Use Item",msg,ok)

@rpg_root.command(name="equip")
async def rpg_equip(ctx,item_key: str=""):
    await _rpg_delete(ctx)
    if not item_key: await _rpg_action_panel(ctx,"Equipment","Use `!rpg equip <item_key>`.",False); return
    ok,msg=await bot.rpg.equip(ctx.guild.id,ctx.author.id,item_key); await _rpg_action_panel(ctx, "Equipment", msg, ok)


@rpg_root.command(name="shop")
async def rpg_shop(ctx):
    await _rpg_delete(ctx)
    items=await bot.rpg.shop(ctx.guild.id,ctx.author.id)
    from rpg import rotation_label
    pages=_rpg_pages(f"Horizon Shop • {rotation_label('shop')}",items,page_size=8,icon="⚔️",formatter=lambda x:f"**{x[1]['name']}**\n`{x[0]}` • {x[1].get('rarity','common').title()} • Lv {x[1].get('level_req',1)}+ • **{x[1]['price']} gold**\n" + (" • ".join(f"+{x[1][k]} {label}" for k,label in (("atk","ATK"),("def","DEF"),("hp","HP"),("mp","MP"),("spd","SPD"),("crit","Crit")) if x[1].get(k)) or "Weapon") + f"\nBuy: `!rpg buy {x[0]} [qty]`")
    await _rpg_panel(ctx,pages)
@rpg_root.command(name="buy")
async def rpg_buy(ctx,item_key: str="",quantity: int=1):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.buy(ctx.guild.id,ctx.author.id,item_key,quantity); await _rpg_action_panel(ctx, "Purchase", msg, ok)


@rpg_root.command(name="sell")
async def rpg_sell(ctx,item_key: str="",quantity: int=1):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.sell(ctx.guild.id,ctx.author.id,item_key,quantity); await _rpg_action_panel(ctx, "Sale", msg, ok)


@rpg_root.command(name="recipes")
async def rpg_recipes(ctx):
    await _rpg_delete(ctx)
    rows=list(RECIPES.items())
    pages=_rpg_pages("Crafting Recipes",rows,page_size=6,icon="🔨",formatter=lambda x:f"**{ITEMS.get(x[0],{'name':x[0]})['name']}**\nCraft key: `{x[0]}`\nMaterials: "+", ".join(f"{ITEMS.get(m,{'name':m})['name']} ×{n}" for m,n in x[1].items() if m!="_meta") + f"\nReq Lv {x[1].get('_meta',{}).get('level_req',1)} • Fee {x[1].get('_meta',{}).get('gold_fee',0)}g")
    await _rpg_panel(ctx,pages)
@rpg_root.command(name="craft")
async def rpg_craft(ctx,item_key: str="",quantity: int=1):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.craft(ctx.guild.id,ctx.author.id,item_key,quantity); await _rpg_action_panel(ctx, "Crafting", msg, ok)


@rpg_root.command(name="gather")
async def rpg_gather(ctx):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.gather(ctx.guild.id,ctx.author.id,"gather"); await _rpg_action_panel(ctx, "Gathering", msg, ok)


@rpg_root.command(name="fish")
async def rpg_fish(ctx):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.gather(ctx.guild.id,ctx.author.id,"fish"); await _rpg_action_panel(ctx, "Fishing", msg, ok)


@rpg_root.command(name="mine")
async def rpg_mine(ctx):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.gather(ctx.guild.id,ctx.author.id,"mine"); await _rpg_action_panel(ctx, "Mining", msg, ok)


@rpg_root.command(name="professions", aliases=["prof"])
async def rpg_professions(ctx):
    await _rpg_delete(ctx); rows=await bot.rpg.professions(ctx.guild.id,ctx.author.id)
    text="\n".join(f"**{name.title()}** — Lv **{level}** • {xp} XP" for name,level,xp in rows)
    await _rpg_action_panel(ctx,"🛠️ Professions",text+"\n\nGathering Lv 10+ yields an extra material.",True)

@rpg_root.command(name="social", aliases=["reputation","rep"])
async def rpg_social(ctx):
    await _rpg_delete(ctx); data=await bot.rpg.social_stats(ctx.guild.id,ctx.author.id)
    text=(f"🤝 Helpful actions: **{data['helpful']}**\n"
          f"🛡️ Party runs: **{data['party_runs']}**\n"
          f"🔄 Completed trades: **{data['trades_completed']}**\n"
          f"🏰 Guild contributions: **{data['guild_contributions']}**")
    await _rpg_action_panel(ctx,"🤝 Social Reputation",text,True)

@rpg_root.command(name="economyinfo", aliases=["econstats","economy-stats"])
async def rpg_economy_info(ctx):
    await _rpg_delete(ctx); data=await bot.rpg.economy_summary(ctx.guild.id,ctx.author.id)
    if not data: await _rpg_action_panel(ctx,"Economy","Create a hero first.",False); return
    text=f"💰 Gold: **{data['gold']}**\n💎 Gems: **{data['gems']}**\n\nGold earned: **{data['earned']}**\nGold spent: **{data['spent']}**\nEconomy events: **{data['events']}**\nMarket sales: **{data['market_sold']}**"
    await _rpg_action_panel(ctx,"📊 Personal Economy",text,True)

class QuestBoardView(discord.ui.View):
    CATEGORIES = [
        ("story","📖","Main Story"),("daily","☀️","Daily"),
        ("weekly","📅","Weekly"),("monthly","🗓️","Monthly"),
        ("class","⚔️","Class"),("race","🧬","Race"),
        ("faction","🏛️","Faction"),("bounty","🎯","Bounty"),
        ("secret","❓","Secret"),("legendary","👑","Legendary"),
    ]
    DESCRIPTIONS = {
        "story":"Your permanent story progression.",
        "daily":"Rotating objectives that reset every day.",
        "weekly":"Longer objectives that reset every Monday.",
        "monthly":"Large objectives that reset on the 1st of each month.",
        "class":"Quests based on your current class.",
        "race":"Quests based on your current race.",
        "faction":"Quests tied to your faction allegiance.",
        "bounty":"Open player-posted targets and rewards.",
        "secret":"Hidden quests. Their real conditions stay secret.",
        "legendary":"High-end trials with major rewards.",
    }

    def __init__(self, ctx, data, category="story"):
        super().__init__(timeout=900)
        self.ctx=ctx
        self.data=data
        self.message=None
        self.current_category=category

        options=[
            discord.SelectOption(label=label,value=key,emoji=emoji,description=self.DESCRIPTIONS[key][:100])
            for key,emoji,label in self.CATEGORIES
        ]
        select=discord.ui.Select(placeholder="Choose a quest category…",options=options,row=0)
        async def select_callback(interaction):
            if not await self.interaction_check(interaction): return
            category=select.values[0]
            data=await bot.rpg.quest2_categories(self.ctx.guild.id,self.ctx.author.id)
            new_view=QuestBoardView(self.ctx,data,category=category)
            await interaction.response.edit_message(embed=new_view.render(category),view=new_view)
        select.callback=select_callback
        self.add_item(select)

        self._add_claim_buttons()

        refresh=discord.ui.Button(label="Refresh",emoji="🔄",style=discord.ButtonStyle.primary,row=4)
        async def refresh_callback(interaction):
            if not await self.interaction_check(interaction): return
            data=await bot.rpg.quest2_categories(self.ctx.guild.id,self.ctx.author.id)
            new_view=QuestBoardView(self.ctx,data,category=self.current_category)
            await interaction.response.edit_message(embed=new_view.render(self.current_category),view=new_view)
        refresh.callback=refresh_callback
        self.add_item(refresh)

    def _claimable(self):
        rows=self.data.get(self.current_category,[])
        result=[]
        for index,q in enumerate(rows[:10],1):
            if q.get("period") in {"daily","weekly","monthly"} and not int(q.get("claimed",0)) and int(q.get("progress",0)) >= int(q.get("target",1)):
                result.append((index,q))
        return result

    def _add_claim_buttons(self):
        for button_index,(index,q) in enumerate(self._claimable()):
            # Five buttons fit on each Discord action-row; completed quests
            # therefore get their own clearly numbered claim control.
            row=1+(button_index//5)
            button=discord.ui.Button(
                label=f"Claim #{index}",
                emoji="🎁",
                style=discord.ButtonStyle.success,
                row=row,
            )
            async def claim_callback(interaction,index=index,q=q):
                if not await self.interaction_check(interaction): return
                # Acknowledge immediately: reward/database work can take longer than
                # Discord's 3-second interaction response window.
                await interaction.response.defer()
                ok,msg=await bot.rpg.claim_quest2_objective(
                    self.ctx.guild.id,self.ctx.author.id,
                    q.get("period"),q.get("objective_key"),q.get("period_key")
                )
                if not ok:
                    await interaction.edit_original_response(content=msg,embed=None,view=self)
                    return
                data=await bot.rpg.quest2_categories(self.ctx.guild.id,self.ctx.author.id)
                new_view=QuestBoardView(self.ctx,data,category=self.current_category)
                await interaction.edit_original_response(embed=new_view.render(self.current_category),view=new_view)
                await interaction.followup.send(f"🎁 {msg}",ephemeral=True)
            button.callback=claim_callback
            self.add_item(button)

    async def interaction_check(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This quest board belongs to another hero.",ephemeral=True)
            return False
        return True

    def _reset_line(self, category):
        if category not in {"daily","weekly","monthly"}:
            return "Permanent quest category"
        key,nxt=bot.rpg.rotation_status()[category]
        label={"daily":"Daily reset","weekly":"Weekly reset","monthly":"Monthly reset"}[category]
        return f"{label}: <t:{int(nxt.timestamp())}:R>"

    def _reward(self, q):
        parts=[]
        if q.get("reward_xp"): parts.append(f"+{int(q['reward_xp'])} XP")
        if q.get("reward_gold"): parts.append(f"+{int(q['reward_gold'])}g")
        if q.get("reward_item"):
            item=ITEMS.get(q["reward_item"],{"name":q["reward_item"]})
            parts.append(f"{item.get('name',q['reward_item'])} ×{q.get('reward_qty',1)}")
        return " • ".join(parts) or "No reward shown"

    def _quest_text(self, q):
        state=str(q.get("state","")).upper()
        if q.get("period") in {"daily","weekly","monthly"}:
            if int(q.get("claimed",0)):
                status="🎁 CLAIMED"
            elif int(q.get("progress",0)) >= int(q.get("target",1)):
                status="✅ COMPLETE — claim button below"
            else:
                status=f"🔹 ACTIVE — {int(q.get('progress',0))}/{int(q.get('target',1))}"
        elif q.get("target"):
            status=f"🔹 AVAILABLE — 0/{int(q['target'])}"
        else:
            status={
                "LOCKED":"🔒 LOCKED","OPEN":"🎯 OPEN","HIDDEN":"❓ HIDDEN",
                "LEGENDARY":"👑 LEGENDARY","INFO":"ℹ️ INFO","MAIN":"📖 STORY",
                "AVAILABLE":"🔹 AVAILABLE",
            }.get(state,"🔹 AVAILABLE")
        text=f"{q.get('description','')}"
        if q.get("target"):
            text += f"\n\n**Progress:** {status}"
        else:
            text += f"\n\n**Status:** {status}"
        reward=self._reward(q)
        if reward!="No reward shown":
            text += f"\n**Reward:** {reward}"
        return text

    def render(self, category="story"):
        self.current_category=category
        names={k:f"{e} {n}" for k,e,n in self.CATEGORIES}
        rows=self.data.get(category,[])
        title=names.get(category,"📖 Main Story")
        embed=_rpg_embed(f"📜 Quest Board — {title}",self.DESCRIPTIONS.get(category,"Choose a quest category."))
        embed.add_field(name="⏱ Rotation",value=self._reset_line(category),inline=False)
        if not rows:
            embed.add_field(name="No quests",value="There are no quests available in this category right now.",inline=False)
        else:
            for index,q in enumerate(rows[:10],1):
                embed.add_field(name=f"{index}. {q.get('title','Quest')}",value=self._quest_text(q),inline=False)
        claimable=self._claimable()
        if claimable:
            names_ready=", ".join(f"#{index}" for index,_ in claimable)
            embed.add_field(
                name="🎁 Rewards Ready",
                value=f"Completed quests: {names_ready}\nUse the green **Claim** buttons below to collect them.",
                inline=False,
            )
        embed.set_footer(text="Use the category menu above to switch quests • 🔄 Refresh to update progress")
        return embed


@rpg_root.command(name="quests", aliases=["questboard","quest-board"])
async def rpg_quests(ctx):
    await _rpg_delete(ctx)
    data=await bot.rpg.quest2_categories(ctx.guild.id,ctx.author.id)
    view=QuestBoardView(ctx,data)
    view.message=await ctx.send(embed=view.render("story"),view=view)
    return view


@rpg_root.command(name="quest")
async def rpg_quest(ctx,quest_id:int=0):
    if not quest_id:
        await rpg_quests.callback(ctx); return
    await _rpg_delete(ctx)
    rows=await bot.rpg.quests(ctx.guild.id,ctx.author.id)
    q=next((x for x in rows if x[0]==quest_id),None)
    if not q:
        await _rpg_action_panel(ctx,"Quest","Quest not found.",False); return
    qid,title,desc,lvl,target,ptype,xp,gold,item,qty,progress,status,kind,chain_key,chain_step=q
    reward=f"+{xp} XP • +{gold} gold" + (f" • {ITEMS.get(item,{'name':item})['name']} ×{qty}" if item else "")
    e=_rpg_embed(f"📜 Quest #{qid} — {title}",f"{desc}\\n\\n**Required:** Level {lvl}+\\n**Progress:** {min(progress,target)}/{target}\\n**Status:** {status.title()}\\n**Reward:** {reward}\\n\\nAccept: `rpg questactions accept {qid}`\\nClaim: `rpg questactions claim {qid}`")
    await _rpg_panel(ctx,[e])


@rpg_root.group(name="questactions", invoke_without_command=True)
async def rpg_questactions(ctx):
    await _rpg_delete(ctx)
    await _rpg_action_panel(ctx,"Quest Actions","Use `!rpg questactions accept <id>` or `!rpg questactions claim <id>`.",True)


@rpg_questactions.command(name="accept")
async def rpg_quest_accept(ctx,quest_id:int=0):
    await _rpg_delete(ctx)
    ok,msg=await bot.rpg.accept_quest(ctx.guild.id,ctx.author.id,quest_id)
    await _rpg_action_panel(ctx,"Quest Accepted",msg,ok)


@rpg_questactions.command(name="claim")
async def rpg_quest_claim(ctx,quest_id:int=0):
    await _rpg_delete(ctx)
    ok,msg=await bot.rpg.claim_quest(ctx.guild.id,ctx.author.id,quest_id)
    await _rpg_action_panel(ctx,"Quest Reward",msg,ok)


@rpg_root.command(name="claim")
async def rpg_claim(ctx,quest_id:int=0):
    await rpg_quest_claim.callback(ctx,quest_id)


@rpg_root.group(name="party", invoke_without_command=True)
async def rpg_party(ctx):
    await _rpg_delete(ctx); info=await bot.rpg.party_info(ctx.guild.id,user_id=ctx.author.id)
    if not info:
        await _rpg_action_panel(ctx,"Party Finder","No open party. Use `!rpg party create <name>` to start one.",False); return
    party,members=info
    e=_rpg_embed(f"🛡️ Party — {party[1]}",f"Party ID: **{party[0]}**\nLeader: <@{party[3]}>\nStatus: **{party[4].title()}**\nMembers: **{len(members)}/4**\n\n"+"\n".join(f"• <@{uid}> — **{role.title()}**" for uid,role in members))
    await _rpg_panel(ctx,[e])
@rpg_party.command(name="create")
async def rpg_party_create(ctx,*,name:str="Adventure Party"):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.create_party(ctx.guild.id,ctx.author.id,name); await _rpg_action_panel(ctx, "Party", msg, ok)


@rpg_party.command(name="join")
async def rpg_party_join(ctx,party_id:int=0):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.join_party(ctx.guild.id,ctx.author.id,party_id); await _rpg_action_panel(ctx, "Party", msg, ok)


@rpg_party.command(name="leave")
async def rpg_party_leave(ctx):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.leave_party(ctx.guild.id,ctx.author.id); await _rpg_action_panel(ctx, "Party", msg, ok)


@rpg_party.command(name="dungeon")
async def rpg_party_dungeon(ctx,*,name:str=""):
    await _rpg_delete(ctx); result=await bot.rpg.party_dungeon(ctx.guild.id,ctx.author.id,name.strip() or None)
    if "error" in result: await _rpg_action_panel(ctx,"Party Dungeon",result["error"],False); return
    if not result["win"]:
        e=_rpg_embed(f"💀 Party Dungeon — {result['name']}","\n".join("• "+x for x in result['log']),discord.Colour.red())
        await _rpg_panel(ctx,[e]); return
    lines=[f"<@{uid}>: +{xp} XP / +{gold} gold" for uid,xp,gold in result["rewards"]]
    e=_rpg_embed(f"🏆 Party Dungeon Cleared — {result['name']}","\n".join("• "+x for x in result['log'])+"\n\n"+"\n".join(lines),discord.Colour.green())
    await _rpg_panel(ctx,[e])


@rpg_party.command(name="info")
async def rpg_party_info(ctx,party_id:int=0):
    await _rpg_delete(ctx); info=await bot.rpg.party_info(ctx.guild.id,pid=party_id if party_id else None,user_id=ctx.author.id)
    if not info: await _rpg_action_panel(ctx,"Party","Party not found.",False); return
    party,members=info
    e=_rpg_embed(f"🛡️ {party[1]}",f"Party ID: **{party[0]}**\nLeader: <@{party[3]}>\nMembers: **{len(members)}/4**\n\n"+"\n".join(f"• <@{uid}> — **{role.title()}**" for uid,role in members))
    await _rpg_panel(ctx,[e])


@rpg_root.group(name="guild", invoke_without_command=True)
async def rpg_guild(ctx):
    await _rpg_delete(ctx); info=await bot.rpg.guild_info(ctx.guild.id,user_id=ctx.author.id)
    if info:
        g,members=info
        e=_rpg_embed(f"🏰 {g[1]}",f"Level **{g[3]}** • Guild XP **{g[4]}** • Bank **{g[5]} gold**\nLeader: <@{g[2]}>\nMembers: **{len(members)}**")
        await _rpg_panel(ctx,[e])
    else:
        rows=await bot.rpg.guilds(ctx.guild.id)
        pages=_rpg_pages("Guild Directory",rows,page_size=6,icon="🏰",formatter=lambda x:f"**{x[0]}**\nLv **{x[2]}** • XP **{x[3]}** • Bank **{x[4]}g** • Leader <@{x[1]}>")
        await _rpg_panel(ctx,pages)

@rpg_guild.command(name="list")
async def rpg_guild_list(ctx):
    await _rpg_delete(ctx); rows=await bot.rpg.guilds(ctx.guild.id)
    pages=_rpg_pages("Guild Directory",rows,page_size=6,icon="🏰",formatter=lambda x:f"**{x[0]}**\nLv **{x[2]}** • XP **{x[3]}** • Bank **{x[4]}g** • Leader <@{x[1]}>")
    await _rpg_panel(ctx,pages)
@rpg_guild.command(name="create")
async def rpg_guild_create(ctx,*,name:str=""):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.create_guild(ctx.guild.id,ctx.author.id,name); await _rpg_action_panel(ctx, "Guild", msg, ok)


@rpg_guild.command(name="join")
async def rpg_guild_join(ctx,*,name:str=""):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.join_guild(ctx.guild.id,ctx.author.id,name); await _rpg_action_panel(ctx, "Guild", msg, ok)


@rpg_guild.command(name="info")
async def rpg_guild_info(ctx,*,name:str=""):
    await _rpg_delete(ctx); info=await bot.rpg.guild_info(ctx.guild.id,name or None)
    if not info: await _rpg_action_panel(ctx,"Guild","Guild not found. Use `!rpg guild list`.",False); return
    g,members=info
    e=_rpg_embed(f"🏰 {g[1]}",f"Level **{g[3]}**\nGuild XP: **{g[4]}** • Bank: **{g[5]} gold**\nLeader: <@{g[2]}>\nMembers: **{len(members)}**")
    await _rpg_panel(ctx,[e])


@rpg_guild.command(name="members")
async def rpg_guild_members(ctx):
    await _rpg_delete(ctx); info=await bot.rpg.guild_info(ctx.guild.id,user_id=ctx.author.id)
    if not info: await _rpg_action_panel(ctx,"Guild Members","You are not in a guild.",False); return
    g,members=info
    pages=_rpg_pages(f"{g[1]} — Members",members,page_size=10,icon="🏰",formatter=lambda x:f"<@{x[0]}> — **{x[1].title()}**")
    await _rpg_panel(ctx,pages)
@rpg_guild.command(name="leave")
async def rpg_guild_leave(ctx):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.leave_guild(ctx.guild.id,ctx.author.id); await _rpg_action_panel(ctx, "Guild", msg, ok)


@rpg_guild.command(name="deposit")
async def rpg_guild_deposit(ctx,amount:int=0):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.guild_deposit(ctx.guild.id,ctx.author.id,amount); await _rpg_action_panel(ctx, "Guild Treasury", msg, ok)


@rpg_guild.command(name="upgrade")
async def rpg_guild_upgrade(ctx):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.guild_upgrade(ctx.guild.id,ctx.author.id); await _rpg_action_panel(ctx, "Guild Upgrade", msg, ok)


@rpg_root.group(name="kingdom", invoke_without_command=True)
async def rpg_kingdom(ctx):
    await _rpg_delete(ctx)
    info=await bot.rpg.kingdom_info(ctx.guild.id,user_id=ctx.author.id)
    if info:
        k,members=info
        e=_rpg_embed(f"👑 {k[1]}",f"Level **{k[3]}** • Treasury **{k[4]}g** • Renown **{k[5]}**\nSovereign: <@{k[2]}>\nMembers: **{len(members)}**")
        await _rpg_panel(ctx,[e])
    else:
        rows=await bot.rpg.kingdom_list(ctx.guild.id)
        pages=_rpg_pages("Kingdoms of Horizon",rows,page_size=6,icon="👑",formatter=lambda x:f"**{x[0]}**\nLevel **{x[2]}** • Treasury **{x[3]}g** • Renown **{x[4]}**\nSovereign: <@{x[1]}>")
        await _rpg_panel(ctx,pages)

@rpg_kingdom.command(name="list")
async def rpg_kingdom_list(ctx):
    await _rpg_delete(ctx); rows=await bot.rpg.kingdom_list(ctx.guild.id)
    pages=_rpg_pages("Kingdoms of Horizon",rows,page_size=6,icon="👑",formatter=lambda x:f"**{x[0]}**\nLevel **{x[2]}** • Treasury **{x[3]}g** • Renown **{x[4]}**\nSovereign: <@{x[1]}>")
    await _rpg_panel(ctx,pages)
@rpg_kingdom.command(name="create")
async def rpg_kingdom_create(ctx, *, name: str = ""):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.kingdom_create(ctx.guild.id,ctx.author.id,name); await _rpg_action_panel(ctx, "Kingdom", msg, ok)


@rpg_kingdom.command(name="join")
async def rpg_kingdom_join(ctx, *, name: str = ""):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.kingdom_join(ctx.guild.id,ctx.author.id,name); await _rpg_action_panel(ctx, "Kingdom", msg, ok)


@rpg_kingdom.command(name="info")
async def rpg_kingdom_info(ctx, *, name: str = ""):
    await _rpg_delete(ctx); info=await bot.rpg.kingdom_info(ctx.guild.id,name or None,user_id=ctx.author.id)
    if not info: await _rpg_action_panel(ctx,"Kingdom", "Kingdom not found.",False); return
    k,members=info
    e=_rpg_embed(f"👑 {k[1]}",f"Level **{k[3]}** • Treasury **{k[4]}g** • Renown **{k[5]}**\nSovereign: <@{k[2]}>\nMembers: **{len(members)}**")
    await _rpg_panel(ctx,[e])
@rpg_kingdom.command(name="appoint")
async def rpg_kingdom_appoint(ctx, member: discord.Member = None, role: str = "citizen"):
    await _rpg_delete(ctx)
    if not member: await _rpg_action_panel(ctx,"Kingdom Appointment","Use `!rpg kingdom appoint @user <duke|count|knight|citizen|outlaw>`.",False); return
    ok,msg=await bot.rpg.kingdom_promote(ctx.guild.id,ctx.author.id,member.id,role)
    await _rpg_action_panel(ctx,"Kingdom Appointment",msg,ok)


@rpg_kingdom.command(name="leave")
async def rpg_kingdom_leave(ctx):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.kingdom_leave(ctx.guild.id,ctx.author.id); await _rpg_action_panel(ctx, "Kingdom", msg, ok)


@rpg_root.group(name="bounty", invoke_without_command=True)
async def rpg_bounty(ctx):
    await _rpg_delete(ctx)
    rows=await bot.rpg.bounties(ctx.guild.id)
    pages=_rpg_pages("Bounty Board",rows,page_size=8,icon="🎯",formatter=lambda x:f"`#{x[0]}` — **{x[1]}**\nReward: **{x[2]} gold** • Posted by <@{x[3]}> • **{x[4].title()}**")
    await _rpg_panel(ctx,pages)

@rpg_bounty.command(name="list")
async def rpg_bounty_list(ctx): await rpg_bounty.callback(ctx)


@rpg_bounty.command(name="post")
async def rpg_bounty_post(ctx, *, target_and_reward: str = ""):
    await _rpg_delete(ctx)
    parts=target_and_reward.strip().rsplit(maxsplit=1)
    reward=0; target=""; target_id=0
    if len(parts)==2 and parts[-1].isdigit():
        target,reward=parts[0],int(parts[-1])
    elif len(parts)==2 and parts[0].isdigit():
        reward,target=int(parts[0]),parts[1]
    if ctx.message.mentions:
        target_id=ctx.message.mentions[0].id
        target=ctx.message.mentions[0].display_name
    if not target or reward<=0:
        await _rpg_action_panel(ctx,"Bounty","Use `!rpg bounty post @player <gold>` or `!rpg bounty post <name> <gold>`." ,False); return
    ok,msg=await bot.rpg.bounty_post(ctx.guild.id,ctx.author.id,target,reward,target_id)
    await _rpg_action_panel(ctx, "Bounty", msg, ok)


@rpg_bounty.command(name="claim")
async def rpg_bounty_claim(ctx, bounty_id:int=0):
    await _rpg_delete(ctx)
    if not bounty_id:
        await _rpg_action_panel(ctx,"Bounty Claim","Use `!rpg bounty claim <bounty_id>` after completing the bounty.",False); return
    ok,msg=await bot.rpg.bounty_claim(ctx.guild.id,ctx.author.id,bounty_id)
    await _rpg_action_panel(ctx,"Bounty Claim",msg,ok)


@rpg_root.command(name="dungeon")
async def rpg_dungeon(ctx,*,name:str=""):
    await _rpg_delete(ctx)
    result=await bot.rpg.start_combat(ctx.guild.id,ctx.author.id,"dungeon",name.strip() or None)
    if "error" in result: await _rpg_action_panel(ctx,"Dungeon",result["error"],False); return
    view=RPGCombatView(ctx,result["state"])
    view.message=await ctx.send(embed=_combat_embed(result["state"]),view=view)


@rpg_root.command(name="stat")
async def rpg_stat(ctx,stat:str="",points:int=1):
    await _rpg_delete(ctx)
    if not stat:
        await _rpg_action_panel(ctx,"Stat Points","Use `!rpg stat <attack|defense|speed|crit|hp|mana> [points]` to spend one or multiple Stat Points.",False); return
    ok,msg=await bot.rpg.spend_stat(ctx.guild.id,ctx.author.id,stat,points); await _rpg_action_panel(ctx,"Stat Point",msg,ok)


@rpg_root.command(name="skill")
async def rpg_skill(ctx,skill_key:str="",points:int=1):
    await _rpg_delete(ctx)
    if not skill_key:
        await _rpg_action_panel(ctx,"Skill Points","Use `!rpg skill <skill_key> [points]` to spend one or multiple Skill Points and raise that unlocked skill's mastery (max 5).\n\nUse `!rpg skills` to see skill keys and mastery ranks.",False); return
    ok,msg=await bot.rpg.skill_mastery(ctx.guild.id,ctx.author.id,skill_key,points); await _rpg_action_panel(ctx,"Skill Mastery",msg,ok)


@rpg_root.command(name="talents")
async def rpg_talents(ctx):
    await _rpg_delete(ctx)
    p=await bot.rpg.player(ctx.guild.id,ctx.author.id)
    if not p:
        await _rpg_action_panel(ctx,"Talent Trees","Create your hero first with `!rpg start`.",False); return
    ranks=await bot.rpg.talent_ranks(ctx.guild.id,ctx.author.id)
    def fmt_node(node,tree):
        key,name,desc,effect=node; rank=ranks.get((tree,key),0)
        return f"`{key}` **{name}** · Rank **{rank}/5**\n{desc}"
    class_nodes=bot.rpg._talent_nodes(p,"class")
    race_nodes=bot.rpg._talent_nodes(p,"race")
    pages=[_rpg_embed(f"🌟 {p['class_name'].title()} Talent Tree",f"Unspent Talent Points: **{p.get('talent_points',0)}**\nSpend with `!rpg talent class <talent_key>`\n\n"+"\n\n".join(fmt_node(x,"class") for x in class_nodes)),
           _rpg_embed(f"🧬 {p['race'].title()} Talent Tree",f"Unspent Talent Points: **{p.get('talent_points',0)}**\nSpend with `!rpg talent race <talent_key>`\n\n"+"\n\n".join(fmt_node(x,"race") for x in race_nodes))]
    await _rpg_panel(ctx,pages)


@rpg_root.command(name="talent")
async def rpg_talent(ctx,tree:str="",talent_key:str="",points:int=1):
    await _rpg_delete(ctx)
    if not tree or not talent_key:
        await _rpg_action_panel(ctx,"Talent Point","Use `!rpg talent <class|race> <talent_key> [points]`. Spend multiple points at once; a talent can reach Rank 5/5.",False); return
    ok,msg=await bot.rpg.spend_talent(ctx.guild.id,ctx.author.id,tree,talent_key,points); await _rpg_action_panel(ctx,"Talent Point",msg,ok)


@rpg_root.command(name="skills")
async def rpg_skills(ctx, page: int = 1):
    await _rpg_delete(ctx)
    p=await bot.rpg.player(ctx.guild.id,ctx.author.id)
    if not p:
        await _rpg_action_panel(ctx,"Combat Skills","Create your hero first with `!rpg start`.",False); return
    rows=bot.rpg.skills_for_player(p)
    mastery=await bot.rpg.skill_masteries(ctx.guild.id,ctx.author.id)
    loadout=await bot.rpg.skill_loadout(ctx.guild.id,ctx.author.id); active={slot:skill["key"] for slot,skill in loadout if skill}
    def fmt(x):
        unlocked=p["level"]>=x["unlock"]; slots=[str(slot) for slot,key in active.items() if key==x["key"]]
        rank=max(1,int(mastery.get(x["key"],1))) if unlocked else 0
        atk=max(1,int(p.get("atk",10))); mult=float(x.get("mult",0))*(1+0.035*max(0,rank-1)); effect=x.get("effect")
        if effect=="heal": damage_text="Damage: —"
        elif effect in {"counter","barrier"}: damage_text="Damage: utility"
        else: damage_text=f"Damage: ~{int(atk*mult*.92)}–{int(atk*mult*1.08)} base"
        heal=x.get("heal_pct",0)
        heal_text=f"Heal: ~{int(p.get('max_hp',100)*heal)} HP" if heal else "Heal: —"
        return (f"`{x['key']}` **{x['name']}** · Unlock Lv **{x['unlock']}** · Mastery **{rank}/5** · **{x['cost']} MP** · CD **{x['cooldown']}t**\n"
                f"{damage_text} • {heal_text}\n"
                f"Buff: **{x.get('buff_text','None')}** • Debuff: **{x.get('debuff_text','None')}**\n"
                f"Effect: **{x['desc']}**\n"
                f"{'✅ UNLOCKED' if unlocked else '🔒 LOCKED'}" + (f" · Active slot {slots[0]}" if slots else ""))
    pages=_rpg_pages(f"{p['class_name'].title()} Skills — 20 Distinct Skills",rows,page_size=4,icon="✨",formatter=fmt)
    # Add loadout overview to the first page.
    if pages:
        active_text="\n".join(f"**Slot {slot}:** {skill['name']} · Mastery {mastery.get(skill['key'],1)}/5" for slot,skill in loadout if skill) or "No active skills."
        pages[0].description=f"**Active 4-skill loadout** · Unspent Skill Points: **{p.get('skill_points',0)}**\n{active_text}\n\n`!rpg skill <skill_key>` → spend 1 Skill Point to master a skill.\n\n"+pages[0].description
    await _rpg_panel(ctx,pages)

@rpg_root.command(name="equip-skill", aliases=["equipskill","skill-equip"])
async def rpg_equip_skill(ctx, skill_key: str = "", slot: int = 0):
    await _rpg_delete(ctx)
    if not skill_key or not slot:
        await _rpg_action_panel(ctx,"Skill Loadout","Use `!rpg equip-skill <skill_key> <1-4>`.\nYou can have exactly **4 active skills**; unlocked skills remain available to swap in and out.",False); return
    ok,msg=await bot.rpg.equip_skill(ctx.guild.id,ctx.author.id,skill_key,slot)
    await _rpg_action_panel(ctx,"Skill Loadout",msg,ok)


@rpg_root.command(name="battle", aliases=["duel"])
async def rpg_battle(ctx,member:discord.Member=None):
    await _rpg_delete(ctx)
    if not member:
        await _rpg_action_panel(ctx,"PvP Duel","Use `!rpg battle @player` to start a turn-based duel.",False); return
    result=await bot.rpg.start_duel(ctx.guild.id,ctx.author.id,member.id)
    if "error" in result:
        await _rpg_action_panel(ctx,"PvP Duel",result["error"],False); return
    view=RPGPvPView(ctx,result["state"],result["key"])
    view.message=await ctx.send(embed=_pvp_embed(result["state"]),view=view)


@rpg_root.command(name="arena", aliases=["ranked","rankedpvp"])
async def rpg_arena(ctx, member: discord.Member = None):
    await _rpg_delete(ctx)
    if not member:
        rating=await bot.rpg.arena_rating(ctx.guild.id,ctx.author.id)
        await _rpg_action_panel(ctx,"🏆 Ranked Arena",f"**Season:** {rating['season'][2]}\n**Rating:** {rating['rating']}\n**Record:** {rating['wins']}W / {rating['losses']}L\n**Streak:** {rating['streak']}\n\nUse `!rpg arena @player` to start a ranked match.",True); return
    result=await bot.rpg.start_arena(ctx.guild.id,ctx.author.id,member.id)
    if "error" in result:
        await _rpg_action_panel(ctx,"🏆 Ranked Arena",result["error"],False); return
    view=RPGPvPView(ctx,result["state"],result["key"])
    view.message=await ctx.send(embed=_pvp_embed(result["state"]),view=view)

@rpg_root.command(name="season", aliases=["pvpseason","rankings"])
async def rpg_season(ctx):
    await _rpg_delete(ctx)
    season,rows=await bot.rpg.arena_ratings(ctx.guild.id)
    body=f"**{season[2]}**\nEnds <t:{int(season[4])}:R>\n\n" + ("\n".join(f"**#{i}** <@{r[0]}> — **{r[1]} Rating** · {r[2]}W / {r[3]}L · Best {r[5]}" for i,r in enumerate(rows,1)) or "No ranked matches yet.")
    await _rpg_action_panel(ctx,"🏆 PvP Season",body,True)

@rpg_root.command(name="raid", aliases=["raidboss","worldraid"])
async def rpg_raid(ctx, action: str = "info"):
    await _rpg_delete(ctx); action=action.lower().strip()
    if action in {"attack","fight","hit"}:
        ok,msg=await bot.rpg.raid_attack(ctx.guild.id,ctx.author.id)
        await _rpg_action_panel(ctx,"🐉 Server Raid",msg,ok); return
    raid,rows=await bot.rpg.raid_leaderboard(ctx.guild.id)
    top="\n".join(f"**#{i}** <@{r[0]}> — **{r[1]:,} damage** · {r[2]} attacks" for i,r in enumerate(rows,1)) or "No contributors yet."
    await _rpg_action_panel(ctx,"🐉 "+raid[2],f"{raid[3]}\n\n❤️ **{max(0,raid[6]):,}/{raid[5]:,} HP**\nStatus: **{raid[7].title()}**\nExpires <t:{int(raid[9])}:R>\n\n**Top Contributors**\n{top}\n\nAttack with `!rpg raid attack`.",True)

@rpg_root.command(name="secretclasses", aliases=["secret-classes","secretclass"])
async def rpg_secret_classes(ctx):
    await _rpg_delete(ctx)
    rows=await bot.rpg.secret_class_list(ctx.guild.id,ctx.author.id)
    def fmt(x):
        key,data,unlocked=x
        return f"**{data['name']}** · `{key}`\n{data['desc']}\n**Requirement:** {data['requirement']}\n{'AWAKENED' if unlocked else 'LOCKED'}\nAwaken: `!rpg awaken {key}`"
    await _rpg_panel(ctx,_rpg_pages("🌌 Secret Classes",rows,page_size=2,icon="🌌",formatter=fmt))

@rpg_root.command(name="awaken", aliases=["awakenclass","unlockclass"])
async def rpg_awaken(ctx, class_key: str = ""):
    await _rpg_delete(ctx)
    if not class_key:
        await _rpg_action_panel(ctx,"🌌 Secret Class Awakening","Use `!rpg awaken <class_key>`. See `!rpg secretclasses`.",False); return
    ok,msg=await bot.rpg.awaken_secret_class(ctx.guild.id,ctx.author.id,class_key)
    await _rpg_action_panel(ctx,"🌌 Secret Class Awakening",msg,ok)

@rpg_root.command(name="legendary", aliases=["endgame","legendarycontent"])
async def rpg_legendary(ctx):
    await _rpg_delete(ctx)
    rows=await bot.rpg.legendary_list(ctx.guild.id,ctx.author.id)
    def fmt(x):
        key,data,state=x
        return f"👑 **{data['name']}** · Lv {data['level']}\n{data['desc']}\nReward: **{ITEMS[data['reward']]['name']}** + {data['xp']:,} XP + {data['gold']:,}g\n{'CLEARED' if state[1] else 'LOCKED'} · Completions: {state[2]}\nChallenge: `!rpg challenge {key}`"
    await _rpg_panel(ctx,_rpg_pages("👑 Legendary Endgame",rows,page_size=2,icon="👑",formatter=fmt))

@rpg_root.command(name="challenge", aliases=["legendarychallenge","trial"])
async def rpg_challenge(ctx, challenge_key: str = ""):
    await _rpg_delete(ctx)
    if not challenge_key:
        await _rpg_action_panel(ctx,"👑 Legendary Trial","Use `!rpg challenge <challenge_key>`. See `!rpg legendary`.",False); return
    ok,msg=await bot.rpg.legendary_challenge(ctx.guild.id,ctx.author.id,challenge_key)
    await _rpg_action_panel(ctx,"👑 Legendary Trial",msg,ok)

@rpg_root.command(name="pet")
async def rpg_pet(ctx):
    await _rpg_delete(ctx)
    pet=await bot.rpg.pet_record(ctx.guild.id,ctx.author.id); pets=await bot.rpg.pet_inventory(ctx.guild.id,ctx.author.id)
    if not pets:
        await _rpg_action_panel(ctx,"🐾 Pet Inventory","You have no pets yet.\n\n`!rpg adopt <name>` — get a companion\n`!rpg hatch <egg> <name>` — hatch an egg\n`!rpg pets` — manage your collection",False); return
    if not pet:
        await _rpg_action_panel(ctx,"🐾 Pet Inventory",f"You own **{len(pets)}** pets but none is equipped. Use `!rpg pets` and `!rpg equip-pet <pet_id>`.",False); return
    data=PET_SPECIES.get(pet["species"],{})
    e=_rpg_embed(f"🐾 {pet['name']} — {pet['species']}",f"Pet **#{pet.get('pet_id','?')}** · Level **{pet['level']}** · XP **{pet['xp']}**\n\n"
                 f"⚔️ +{pet['bonus_atk']} ATK • 🛡️ +{pet['bonus_def']} DEF • ❤️ +{pet.get('bonus_hp',0)} HP • 💨 +{pet.get('bonus_speed',0)} SPD • 🎯 +{pet.get('bonus_crit',0)}% Crit\n\n"
                 f"🐾 **{pet.get('ability','Pet Assist')}** — {data.get('ability_desc','A passive companion ability.')}\n\n"
                 f"You have **{len(pets)}** pets stored safely. Pets no longer need to be released just to switch companions.")
    e.set_image(url=_pet_image(pet)); await _rpg_panel(ctx,[e])

@rpg_root.command(name="pets", aliases=["petinventory","pet-inventory"])
async def rpg_pets(ctx):
    await _rpg_delete(ctx); pets=await bot.rpg.pet_inventory(ctx.guild.id,ctx.author.id)
    if not pets:
        await _rpg_action_panel(ctx,"🐾 Pet Inventory","No pets yet. Use `!rpg adopt <name>` or hatch an egg.",False); return
    rows=[(p["pet_id"],p) for p in pets]
    def fmt(x):
        p=x[1]; data=PET_SPECIES.get(p["species"],{}); active="🟢 EQUIPPED" if p.get("equipped") else "📦 Stored"
        return f"**#{p['pet_id']} {p['name']}** — {p['species']} · Lv {p['level']} · {active}\n🐾 {p.get('ability','Pet Assist')} — {data.get('ability_desc','Companion combat effect.')}\n⚔️ +{p['bonus_atk']} ATK • 🛡️ +{p['bonus_def']} DEF • ❤️ +{p.get('bonus_hp',0)} HP • 💨 +{p.get('bonus_speed',0)} SPD • 🎯 +{p.get('bonus_crit',0)}% Crit\nEquip: `!rpg equip-pet {p['pet_id']}`"
    await _rpg_panel(ctx,_rpg_pages("Pet Inventory",rows,page_size=4,icon="🐾",formatter=fmt))

@rpg_root.command(name="equip-pet", aliases=["equippet","pet-equip"])
async def rpg_equip_pet(ctx, pet_id: int = 0):
    await _rpg_delete(ctx)
    if not pet_id:
        await _rpg_action_panel(ctx,"Pet Equipment","Use `!rpg equip-pet <pet_id>`. Your other pets remain stored.",False); return
    ok,msg=await bot.rpg.equip_pet(ctx.guild.id,ctx.author.id,pet_id); await _rpg_action_panel(ctx,"Pet Equipment",msg,ok)

@rpg_root.command(name="unequip-pet", aliases=["unequippet","pet-unequip"])
async def rpg_unequip_pet(ctx):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.unequip_pet(ctx.guild.id,ctx.author.id); await _rpg_action_panel(ctx,"Pet Equipment",msg,ok)

@rpg_root.command(name="petfeed", aliases=["feedpet","pet-feed"])
async def rpg_pet_feed(ctx, pet_id:int=0):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.pet_feed(ctx.guild.id,ctx.author.id,pet_id or None); await _rpg_action_panel(ctx,"🐾 Pet Care",msg,ok)

@rpg_root.command(name="egg-pets", aliases=["eggpets","eggpet","egg-pet"])
async def rpg_egg_pets(ctx, egg_key: str = ""):
    """Show the exclusive pets that can hatch from each pet egg."""
    await _rpg_delete(ctx)
    if egg_key:
        key=egg_key.lower().strip()
        if key not in PET_EGGS or key not in PET_EGG_POOLS:
            await _rpg_action_panel(ctx,"🥚 Egg Pet List","Unknown egg. Use `!rpg egg-pets` to see every egg.",False); return
        egg_name, rarity, price=PET_EGGS[key]
        rows=[]
        for species in PET_EGG_POOLS[key]:
            d=PET_SPECIES.get(species,{})
            rows.append((species,f"🐾 **{species}** — {d.get('rarity','common').title()}\n⚔️ +{d.get('atk',0)} ATK • 🛡️ +{d.get('def',0)} DEF • ❤️ +{d.get('hp',0)} HP • 💨 +{d.get('spd',0)} SPD • 🎯 +{d.get('crit',0)}% Crit\n✨ **{d.get('ability','Pet Ability')}** — {d.get('role','companion').title()}"))
        pages=_rpg_pages(f"🥚 {egg_name} — Available Pets",rows,page_size=5,icon="🐾",formatter=lambda x:x[1])
        await _rpg_panel(ctx,pages); return
    rows=[]
    for key,(name,rarity,price) in PET_EGGS.items():
        species=PET_EGG_POOLS.get(key,[])
        rows.append((key,f"🥚 **{name}** — {rarity}\n🐾 **{len(species)} exclusive pets**\n" + ", ".join(species) + f"\nView: `!rpg egg-pets {key}`"))
    await _rpg_panel(ctx,_rpg_pages("🥚 Pet Egg Catalogue",rows,page_size=3,icon="🥚",formatter=lambda x:x[1]))

@rpg_root.command(name="petcollection", aliases=["petdex","pet-collection"])
async def rpg_pet_collection(ctx):
    await _rpg_delete(ctx); rows=await bot.rpg.pet_collection(ctx.guild.id,ctx.author.id)
    known={r[0]:r for r in rows}; lines=[]
    for species,data in PET_SPECIES.items():
        lines.append(("🟢" if species in known else "⚪")+f" **{species}** — {data['rarity'].title()}"+(f" • seen {known[species][1]}x" if species in known else " • undiscovered"))
    pages=_rpg_pages("🐾 Pet Codex",[(i,"\n".join(lines[i*8:(i+1)*8])) for i in range((len(lines)+7)//8)],page_size=1,icon="🐾",formatter=lambda x:x[1])
    await _rpg_panel(ctx,pages)

@rpg_root.command(name="gacha", aliases=["summon","draw"])
async def rpg_gacha(ctx, count: int = 0):
    await _rpg_delete(ctx)
    info=await bot.rpg.gacha_info(ctx.guild.id,ctx.author.id)
    if not count:
        rates="\n".join(f"• **{rarity.title()}** — {rate*100:.1f}%" for rarity,rate in GACHA_RATES)
        body=(f"💎 **Gems:** {info['gems']}\n🎯 **Pity:** {info['pity']}/{GACHA_EPIC_PITY} to guarantee Epic+\n"\
              f"🌌 **Mythic pity:** {info['pity']}/{GACHA_MYTHIC_PITY}\n\n"\
              f"**Single:** {GACHA_COST_SINGLE} Gems\n**10-pull:** {GACHA_COST_TEN} Gems\n\n**Published rates**\n{rates}\n\n"\
              "Rewards can include weapons, armor, offhands, accessories, relics, consumables, chests and pets.\n"\
              "`!rpg gacha 1` — single pull\n`!rpg gacha 10` — ten-pull")
        await _rpg_action_panel(ctx,"🌌 Horizon Gacha",body,True); return
    if count not in {1,10}:
        await _rpg_action_panel(ctx,"Horizon Gacha","Choose **1** or **10** pulls. `!rpg gacha 1` or `!rpg gacha 10`.",False); return
    ok,result=await bot.rpg.gacha_pull(ctx.guild.id,ctx.author.id,count)
    if not ok:
        await _rpg_action_panel(ctx,"Horizon Gacha",result.get("error","Gacha unavailable."),False); return
    lines=[]
    for i,reward in enumerate(result["rewards"],1):
        if reward["type"].startswith("pet"):
            text=f"🐾 **{reward.get('name',reward.get('species'))}** — {reward.get('species','Pet')}"
            if reward["type"]=="pet_duplicate": text+=f" (duplicate → +{reward['refund']} Gems)"
        else:
            text=f"📦 **{reward['name']}** — {reward['rarity'].title()} / {reward.get('slot','item').title()}"
            if reward.get("level_req",1)>1:text+=f" · Lv {reward['level_req']}+"
            if reward.get("ability"):text+=f" · {reward['ability']}"
        lines.append(f"**{i}.** {text}")
    body=f"**Cost:** {result['cost']} Gems\n**Gems remaining:** {result['gems_left']}\n**Pity:** {result['pity']}/{GACHA_EPIC_PITY}\n\n"+"\n".join(lines)
    await _rpg_action_panel(ctx,"✨ Gacha Results",body,True)

@rpg_root.command(name="open-chest", aliases=["openchest","chest"])
async def rpg_open_chest(ctx, item_key: str = ""):
    await _rpg_delete(ctx)
    if not item_key:
        await _rpg_action_panel(ctx,"Chest Opening","Use `!rpg open-chest <chest_key>`. Browse chest keys with `!rpg items chest`.",False); return
    ok,msg=await bot.rpg.open_chest(ctx.guild.id,ctx.author.id,item_key); await _rpg_action_panel(ctx,"Chest Opening",msg,ok)

@rpg_root.command(name="enchantments", aliases=["enchants"])
async def rpg_enchantments(ctx):
    await _rpg_delete(ctx)
    rows=list(ENCHANTMENTS.items())
    pages=_rpg_pages("Equipment Enchantments",rows,page_size=6,icon="✨",formatter=lambda x:f"**{x[1]['name']}** · Max Lv {x[1]['max_level']}\n{x[1]['desc']}\nApply: `!rpg enchant <slot> <item_key> <enchant_key>`")
    await _rpg_panel(ctx,pages)

@rpg_root.command(name="enchant")
async def rpg_enchant(ctx, slot: str = "", item_key: str = "", enchant_key: str = ""):
    await _rpg_delete(ctx)
    if not slot or not item_key or not enchant_key:
        await _rpg_action_panel(ctx,"Enchant Gear","Use `!rpg enchant <slot> <item_key> <enchant_key>`.\nExample: `!rpg enchant weapon mithril_sword sharpness`.",False); return
    ok,msg=await bot.rpg.enchant_item(ctx.guild.id,ctx.author.id,slot,item_key,enchant_key); await _rpg_action_panel(ctx,"Enchant Gear",msg,ok)

@rpg_root.command(name="titles")
async def rpg_titles(ctx):
    await _rpg_delete(ctx); rows=await bot.rpg.title_list(ctx.guild.id,ctx.author.id)
    if not rows:
        await _rpg_action_panel(ctx,"🏷️ Titles","No titles unlocked yet. Titles can be earned through progression and achievements.",False); return
    await _rpg_panel(ctx,[_rpg_embed("🏷️ Unlocked Titles","\n".join(f"• **{k.replace('_',' ').title()}**" for k,_ in rows))])



@rpg_root.command(name="achievements", aliases=["achieve"])
async def rpg_achievements(ctx):
    await _rpg_delete(ctx)
    unlocked=await bot.rpg.achievement_list(ctx.guild.id,ctx.author.id)
    rows=[(k,ACHIEVEMENTS[k]) for k,_ in unlocked]
    pages=_rpg_pages("Achievements",rows,page_size=6,icon="🏆",formatter=lambda x:f"🏅 **{x[1][0]}**\n{x[1][1]} • Reward **{x[1][2]} XP**")
    await _rpg_panel(ctx,pages)
@rpg_root.command(name="leaderboard", aliases=["lb"])
async def rpg_leaderboard(ctx):
    await _rpg_delete(ctx)
    async with aiosqlite.connect(bot.rpg.path) as db:
        cur=await db.execute("SELECT user_id,level,xp,gold FROM rpg_players WHERE guild_id=? ORDER BY level DESC,xp DESC LIMIT 50",(ctx.guild.id,)); rows=await cur.fetchall()
    ranked=[(i+1,*row) for i,row in enumerate(rows)]
    pages=_rpg_pages("RPG Leaderboard",ranked,page_size=10,icon="🏆",formatter=lambda x:f"**#{x[0]}** <@{x[1]}> — **Lv {x[2]}** • {x[3]} XP • {x[4]}g")
    await _rpg_panel(ctx,pages) if rows else await _rpg_action_panel(ctx,"RPG Leaderboard","No RPG heroes yet.",False)
@rpg_root.command(name="list")
async def rpg_market_list(ctx,item_key:str="",quantity:int=1,price:int=1):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.create_market(ctx.guild.id,ctx.author.id,item_key,quantity,price); await ctx.send(("🏪 " if ok else "❌ ")+msg)


@rpg_root.command(name="market")
async def rpg_market(ctx):
    await _rpg_delete(ctx); rows=await bot.rpg.market(ctx.guild.id)
    pages=_rpg_pages("Player Market",rows,page_size=8,icon="🏪",formatter=lambda x:f"`#{x[0]}` — <@{x[1]}>\n**{ITEMS.get(x[2],{'name':x[2]})['name']}** ×{x[3]} • **{x[4]}g each**\nBuy: `!rpg marketbuy {x[0]}`")
    await _rpg_panel(ctx,pages)
@rpg_root.command(name="marketbuy")
async def rpg_market_buy(ctx,listing_id:int=0):
    await _rpg_delete(ctx); ok,msg=await bot.rpg.market_buy(ctx.guild.id,ctx.author.id,listing_id); await _rpg_action_panel(ctx, "Market Purchase", msg, ok)


@rpg_root.command(name="marketcancel", aliases=["cancelmarket", "market-cancel"])
async def rpg_market_cancel(ctx, listing_id:int=0):
    await _rpg_delete(ctx)
    if not listing_id:
        await _rpg_action_panel(ctx,"Player Market","Use `!rpg marketcancel <listing_id>`.",False); return
    ok,msg=await bot.rpg.market_cancel(ctx.guild.id,ctx.author.id,listing_id)
    await _rpg_action_panel(ctx,"Market Listing",msg,ok)


@rpg_root.command(name="upgrade", aliases=["upgradegear", "enhance"])
async def rpg_upgrade(ctx, slot:str=""):
    await _rpg_delete(ctx)
    if not slot:
        await _rpg_action_panel(ctx,"⬆️ Equipment Upgrade","Use `!rpg upgrade <slot>` — slots: weapon, armor, offhand, accessory, ring, amulet, relic.",False); return
    ok,msg=await bot.rpg.upgrade_equipment(ctx.guild.id,ctx.author.id,slot)
    await _rpg_action_panel(ctx,"⬆️ Equipment Upgrade",msg,ok)


@rpg_root.command(name="vault", aliases=["gearvault", "stash"])
async def rpg_vault(ctx):
    await _rpg_delete(ctx)
    rows=await bot.rpg.gear_vault(ctx.guild.id,ctx.author.id)
    if not rows:
        await _rpg_action_panel(ctx,"🧰 Gear Vault","Your gear vault is empty. Replaced or uniquely upgraded equipment is preserved here instead of being destroyed.",False); return
    lines=[]
    for r in rows[:30]:
        d=ITEMS.get(r["item_key"],{})
        try: intr=json.loads(r.get("intrinsic_json") or "{}")
        except Exception: intr={}
        intr_text=", ".join(f"+{v}{'%' if k.endswith('_pct') else ''} {k.replace('_pct','').replace('_flat','')}" for k,v in intr.items()) or "—"
        lines.append(f"`{r['instance_uid'][:10]}` **{d.get('name',r['item_key'])} +{r['upgrade_level']}** • {r['slot'].title()} • {r.get('set_key','').replace('_set','').title() or 'No set'}\n✨ {intr_text}\nEquip: `!rpg vaultequip {r['instance_uid'][:10]}`")
    await _rpg_panel(ctx,[_rpg_embed("🧰 Gear Vault","\n\n".join(lines))])


@rpg_root.command(name="vaultequip", aliases=["equipvault", "vault-equip"])
async def rpg_vault_equip(ctx, vault_id:str=""):
    await _rpg_delete(ctx)
    rows=await bot.rpg.gear_vault(ctx.guild.id,ctx.author.id)
    match=next((r for r in rows if r["instance_uid"].startswith(vault_id)),None)
    if not match:
        await _rpg_action_panel(ctx,"🧰 Gear Vault","Vault item not found. Use `!rpg vault` and copy its ID.",False); return
    ok,msg=await bot.rpg.equip_vault(ctx.guild.id,ctx.author.id,match["instance_uid"])
    await _rpg_action_panel(ctx,"🧰 Gear Vault",msg,ok)


@rpg_root.command(name="sets", aliases=["equipmentsets", "setbonus"])
async def rpg_sets(ctx):
    await _rpg_delete(ctx)
    rows=await bot.rpg.equipment_sets(ctx.guild.id,ctx.author.id)
    if not rows:
        await _rpg_action_panel(ctx,"🛡️ Equipment Sets","You are not currently wearing any set-linked gear.",False); return
    lines=[]
    for set_key,count,focus in rows:
        name=set_key.replace("_set","").replace("_"," ").title()
        bonuses=[]
        if count>=2: bonuses.append("2pc: +2% focus")
        if count>=4: bonuses.append("4pc: +7% focus total")
        if count>=6: bonuses.append("6pc: +15% focus total")
        next_req=2 if count<2 else 4 if count<4 else 6 if count<6 else None
        progress=f"{count} piece(s) equipped"
        if next_req: progress+=f" • next bonus at {next_req}"
        lines.append(f"**{name} Set** — {progress}\nFocus: **{focus}**\n" + (" • ".join(bonuses) if bonuses else "Equip 2 pieces to activate the first bonus."))
    await _rpg_panel(ctx,[_rpg_embed("🛡️ Equipment Set Bonuses","\n\n".join(lines))])


@rpg_root.command(name="economy", aliases=["economylog", "econ"])
async def rpg_economy(ctx, limit:int=15):
    await _rpg_delete(ctx)
    rows=await bot.rpg.economy_log(ctx.guild.id,ctx.author.id,limit)
    if not rows:
        await _rpg_action_panel(ctx,"📊 Economy Log","No economy transactions recorded yet.",False); return
    lines=[]
    for created,event,item,qty,gold_delta,balance,meta in rows:
        stamp=f"<t:{int(created)}:R>"
        item_name=ITEMS.get(item,{}).get("name",item) if item else ""
        money=f" • {gold_delta:+}g" if gold_delta else ""
        asset=f" • {item_name} ×{abs(qty)}" if item else ""
        lines.append(f"{stamp} **{event.replace('_',' ').title()}**{asset}{money}")
    await _rpg_panel(ctx,[_rpg_embed("📊 Personal Economy Log","\n".join(lines)+"\n\nEvery economy mutation is recorded server-side to make duplication bugs auditable.")])

# Keep the older top-level RPG shortcuts working, but route them through the real RPG engine.
@rpg_root.command(name="trade")
async def rpg_trade(ctx, member: discord.Member = None):
    await _rpg_delete(ctx)
    if not member:
        await _rpg_action_panel(ctx,"🤝 Direct Trading","Use `!rpg trade @player` to open a secure trade. Then add assets with `tradeadd`, `tradepet`, `tradegold`, or `tradediamonds`.",False); return
    ok,result=await bot.rpg.trade_create(ctx.guild.id,ctx.author.id,member.id)
    if not ok:
        await _rpg_action_panel(ctx,"🤝 Trade",result,False); return
    await _rpg_action_panel(ctx,"🤝 Trade Created",f"Trade **#{result}** opened with **{member.display_name}**.\n\nAdd your assets:\n`!rpg tradeadd {result} <item_key> <quantity>`\n`!rpg tradepet {result} <pet_id>`\n`!rpg tradegold {result} <amount>`\n`!rpg tradediamonds {result} <amount>`\n\n**{member.display_name}** can add their side too. When both sides look right, they can run `!rpg tradeaccept {result}`.",True)

@rpg_root.command(name="trades", aliases=["trade-list"])
async def rpg_trades(ctx):
    await _rpg_delete(ctx)
    rows=await bot.rpg.trade_list(ctx.guild.id,ctx.author.id)
    if not rows:
        await _rpg_action_panel(ctx,"🤝 Open Trades","You have no open trades. Start one with `!rpg trade @player`.",True); return
    lines=[]
    for tid,proposer,target,status,created,pg,tg,pd,gd in rows:
        role="Outgoing" if int(proposer)==ctx.author.id else "Incoming"
        other=target if role=="Outgoing" else proposer
        lines.append(f"**#{tid} · {role}** with <@{other}>\n💰 Offer: {pg if role=='Outgoing' else tg} Gold · 💎 {pd if role=='Outgoing' else gd} Diamonds\nView: `!rpg tradeview {tid}`")
    await _rpg_panel(ctx,[_rpg_embed("🤝 Your Open Trades","\n\n".join(lines))])

async def _render_trade(ctx, trade_id, title="🤝 Trade"):
    data=await bot.rpg.trade_details(ctx.guild.id,trade_id)
    if not data:return await _rpg_action_panel(ctx,title,"Trade not found.",False)
    t=data["trade"]; uid=ctx.author.id
    if uid not in {int(t["proposer_id"]),int(t["target_id"])}:return await _rpg_action_panel(ctx,title,"You are not part of that trade.",False)
    names={int(t["proposer_id"]):"Proposer",int(t["target_id"]):"Target"}
    sections=[]
    for side,owner in (("proposer",int(t["proposer_id"])),("target",int(t["target_id"]))):
        item_lines=[]
        for x in data["items"]:
            if x["side"]==side:item_lines.append(f"📦 {ITEMS.get(x['item_key'],{'name':x['item_key']})['name']} ×{x['quantity']}")
        for x in data["pets"]:
            if x["side"]==side:
                pets=await bot.rpg.pet_inventory(ctx.guild.id,owner); p=next((p for p in pets if int(p["pet_id"])==int(x["pet_id"])),None)
                item_lines.append(f"🐾 {p['name']} ({p['species']}) `#{x['pet_id']}`" if p else f"🐾 Pet `#{x['pet_id']}`")
        gold=int(t[f"{side}_gold"]); gems=int(t[f"{side}_gems"])
        item_lines.append(f"💰 {gold:,} Gold") if gold else None
        item_lines.append(f"💎 {gems:,} Diamonds") if gems else None
        sections.append(f"**{names[int(owner)]} — <@{owner}>**\n"+"\n".join(item_lines or ["_Nothing offered yet._"]))
    state="OPEN" if t["status"]=="open" else t["status"].upper()
    body=f"**Status:** {state}\n\n"+"\n\n".join(sections)
    if t["status"]=="open":body+=f"\n\n**Commands**\n`!rpg tradeadd {trade_id} <item_key> <qty>`\n`!rpg tradepet {trade_id} <pet_id>`\n`!rpg tradegold {trade_id} <amount>`\n`!rpg tradediamonds {trade_id} <amount>`\n`!rpg tradeclear {trade_id}`\n`!rpg tradeaccept {trade_id}` — target only\n`!rpg tradecancel {trade_id}`"
    await _rpg_panel(ctx,[_rpg_embed(title,body)])

@rpg_root.command(name="tradeview", aliases=["trade-info"])
async def rpg_trade_view(ctx,trade_id:int=0):
    await _rpg_delete(ctx)
    await _render_trade(ctx,trade_id)

@rpg_root.command(name="tradeadd")
async def rpg_trade_add(ctx,trade_id:int=0,item_key:str="",quantity:int=1):
    await _rpg_delete(ctx)
    if not trade_id or not item_key:
        await _rpg_action_panel(ctx,"Trade Item","Use `!rpg tradeadd <trade_id> <item_key> <quantity>`.",False); return
    ok,msg=await bot.rpg.trade_add_item(ctx.guild.id,ctx.author.id,trade_id,item_key,quantity)
    if not ok: await _rpg_action_panel(ctx,"Trade Item",msg,False); return
    await _render_trade(ctx,trade_id,"🤝 Trade Updated")

@rpg_root.command(name="tradepet")
async def rpg_trade_pet(ctx,trade_id:int=0,pet_id:int=0):
    await _rpg_delete(ctx)
    if not trade_id or not pet_id:
        await _rpg_action_panel(ctx,"Trade Pet","Use `!rpg tradepet <trade_id> <pet_id>`. Unequip the pet first.",False); return
    ok,msg=await bot.rpg.trade_add_pet(ctx.guild.id,ctx.author.id,trade_id,pet_id)
    if not ok: await _rpg_action_panel(ctx,"Trade Pet",msg,False); return
    await _render_trade(ctx,trade_id,"🤝 Trade Updated")

@rpg_root.command(name="tradegold")
async def rpg_trade_gold(ctx,trade_id:int=0,amount:int=0):
    await _rpg_delete(ctx)
    if not trade_id:
        await _rpg_action_panel(ctx,"Trade Gold","Use `!rpg tradegold <trade_id> <amount>`.",False); return
    ok,msg=await bot.rpg.trade_add_currency(ctx.guild.id,ctx.author.id,trade_id,"gold",amount)
    if not ok: await _rpg_action_panel(ctx,"Trade Gold",msg,False); return
    await _render_trade(ctx,trade_id,"🤝 Trade Updated")

@rpg_root.command(name="tradediamonds", aliases=["tradegems","trade-diamonds"])
async def rpg_trade_diamonds(ctx,trade_id:int=0,amount:int=0):
    await _rpg_delete(ctx)
    if not trade_id:
        await _rpg_action_panel(ctx,"Trade Diamonds","Use `!rpg tradediamonds <trade_id> <amount>`.",False); return
    ok,msg=await bot.rpg.trade_add_currency(ctx.guild.id,ctx.author.id,trade_id,"diamonds",amount)
    if not ok: await _rpg_action_panel(ctx,"Trade Diamonds",msg,False); return
    await _render_trade(ctx,trade_id,"🤝 Trade Updated")

@rpg_root.command(name="tradeclear")
async def rpg_trade_clear(ctx,trade_id:int=0):
    await _rpg_delete(ctx)
    ok,msg=await bot.rpg.trade_remove_all(ctx.guild.id,ctx.author.id,trade_id)
    await _rpg_action_panel(ctx,"Trade Clear",msg,ok)

@rpg_root.command(name="tradeaccept")
async def rpg_trade_accept(ctx,trade_id:int=0):
    await _rpg_delete(ctx)
    ok,msg=await bot.rpg.trade_accept(ctx.guild.id,ctx.author.id,trade_id)
    await _rpg_action_panel(ctx,"🤝 Trade Completed",msg,ok)

@rpg_root.command(name="tradecancel")
async def rpg_trade_cancel(ctx,trade_id:int=0):
    await _rpg_delete(ctx)
    ok,msg=await bot.rpg.trade_cancel(ctx.guild.id,ctx.author.id,trade_id)
    await _rpg_action_panel(ctx,"Trade Cancelled",msg,ok)


# Keep@bot.command(name="profile")
async def prefix_profile(ctx, nickname: str = None, *, preferences: str = None):
    if nickname or preferences:
        await _quiet_delete(ctx.message)
        data=await bot.rpg.player(ctx.guild.id,ctx.author.id)
        if data and nickname:
            async with aiosqlite.connect(bot.rpg.path) as db:
                await db.execute("UPDATE rpg_players SET name=? WHERE guild_id=? AND user_id=?",(nickname[:32],ctx.guild.id,ctx.author.id)); await db.commit()
    await rpg_profile.callback(ctx)


@bot.command(name="character")
async def prefix_character(ctx, name: str = None, role: str = None):
    if name or role:
        await _quiet_delete(ctx.message)
        p=await bot.rpg.player(ctx.guild.id,ctx.author.id)
        if not p:
            await ctx.send("Use `!rpg start <name> <race> <class>` first.",delete_after=8); return
    await rpg_profile.callback(ctx)


@bot.command(name="inventory", aliases=["inv"])
async def prefix_inventory(ctx): await rpg_inventory.callback(ctx)

@bot.command(name="daily")
async def prefix_daily(ctx): await rpg_daily.callback(ctx)

@bot.command(name="questlist", aliases=["quest_list", "quests"])
async def prefix_quest_list(ctx): await rpg_quests.callback(ctx)

@bot.command(name="rpgroll", aliases=["rpg_roll", "roll"])
async def prefix_rpg_roll(ctx):
    await _quiet_delete(ctx.message)
    p=await bot.rpg.player(ctx.guild.id,ctx.author.id)
    if not p: await ctx.send("Start your hero first with `!rpg start <name> <race> <class>`.",delete_after=8); return
    roll=random.randint(1,20); await ctx.send(f"🎲 **{ctx.author.display_name}** rolled **{roll}/20**.")


@bot.command(name="leaderboard", aliases=["lb"])
async def prefix_rpg_leaderboard(ctx): await rpg_leaderboard.callback(ctx)

@bot.command(name="warn")
@commands.has_guild_permissions(manage_messages=True)
async def prefix_warn(ctx, member: discord.Member = None, *, reason: str = "No reason provided"):
    await _quiet_delete(ctx.message)
    if not member:
        await ctx.send("Use `!warn @user [reason]`.", delete_after=6); return
    data = await bot.db.add_warning(ctx.guild.id, member.id, ctx.author.id, reason)
    await ctx.send(f"{member.mention} warned. Total warnings: **{data['warnings']}**.")


@bot.command(name="warnings")
@commands.has_guild_permissions(manage_messages=True)
async def prefix_warnings(ctx, member: discord.Member = None):
    await _quiet_delete(ctx.message)
    if not member:
        await ctx.send("Use `!warnings @user`.", delete_after=6); return
    rows = await bot.db.warnings(ctx.guild.id, member.id)
    await ctx.send("\n".join(f"`#{wid}` <@{mid}> — {reason} ({created})" for wid,mid,reason,created in rows) or "No warnings recorded.")


@bot.command(name="mod")
@commands.has_guild_permissions(manage_guild=True)
async def prefix_mod(ctx, state: str = ""):
    await _quiet_delete(ctx.message)
    state = state.lower().strip()
    if state not in {"on", "off"}:
        settings = await bot.db.settings(ctx.guild.id)
        await ctx.send(f"Contextual moderation is **{'on' if settings['mod_enabled'] else 'off'}**. Use `!mod on` or `!mod off`.", delete_after=8); return
    await bot.db.set_setting(ctx.guild.id, "mod_enabled", 1 if state == "on" else 0)
    await ctx.send(f"Contextual moderation is now **{state}**.", delete_after=7)


@bot.command(name="modaction")
@commands.has_guild_permissions(manage_guild=True)
async def prefix_mod_action(ctx, action: str = ""):
    await _quiet_delete(ctx.message)
    action = action.lower().strip()
    if action not in {"log","warn","timeout"}:
        await ctx.send("Use `!modaction log`, `!modaction warn`, or `!modaction timeout`.", delete_after=7); return
    await bot.db.set_setting(ctx.guild.id, "mod_action", {"log":0,"warn":1,"timeout":2}[action])
    await ctx.send(f"Severe-escalation moderation action set to **{action}**.", delete_after=7)


@bot.command(name="clear", aliases=["purge"])
@commands.has_guild_permissions(manage_messages=True)
async def prefix_clear(ctx, amount: int = 0):
    if amount < 1 or amount > 100:
        await _quiet_delete(ctx.message)
        await ctx.send("Use `!clear 1-100`.", delete_after=6); return
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)
        notice = await ctx.send(f"🧹 Deleted **{max(0, len(deleted)-1)}** messages.", delete_after=4)
    except discord.Forbidden:
        await ctx.send("I need **Manage Messages** to clear messages.", delete_after=7)


@bot.command(name="timeout")
@commands.has_guild_permissions(moderate_members=True)
async def prefix_timeout(ctx, member: discord.Member = None, minutes: int = 10, *, reason: str = "No reason provided"):
    await _quiet_delete(ctx.message)
    if not member:
        await ctx.send("Use `!timeout @user <minutes> [reason]`.", delete_after=7); return
    if minutes < 1 or minutes > 40320:
        await ctx.send("Minutes must be between 1 and 40320.", delete_after=7); return
    try:
        await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
        await ctx.send(f"⏳ {member.mention} timed out for **{minutes} minutes**.")
    except discord.Forbidden:
        await ctx.send("I can't timeout that member. Check my role position and Moderate Members permission.", delete_after=8)


@bot.command(name="kick")
@commands.has_guild_permissions(kick_members=True)
async def prefix_kick(ctx, member: discord.Member = None, *, reason: str = "No reason provided"):
    await _quiet_delete(ctx.message)
    if not member: await ctx.send("Use `!kick @user [reason]`.", delete_after=6); return
    try:
        await member.kick(reason=reason); await ctx.send(f"👢 {member.mention} was kicked.")
    except discord.Forbidden: await ctx.send("I can't kick that member. Check my role position and Kick Members permission.", delete_after=8)


@bot.command(name="ban")
@commands.has_guild_permissions(ban_members=True)
async def prefix_ban(ctx, member: discord.Member = None, *, reason: str = "No reason provided"):
    await _quiet_delete(ctx.message)
    if not member: await ctx.send("Use `!ban @user [reason]`.", delete_after=6); return
    try:
        await member.ban(reason=reason); await ctx.send(f"🔨 {member.mention} was banned.")
    except discord.Forbidden: await ctx.send("I can't ban that member. Check my role position and Ban Members permission.", delete_after=8)


@bot.command(name="userinfo", aliases=["user"])
async def prefix_userinfo(ctx, member: discord.Member = None):
    await _quiet_delete(ctx.message)
    member = member or ctx.author
    roles = ", ".join(r.mention for r in member.roles[1:][-10:]) or "None"
    await ctx.send(f"**{member.display_name}**\nID: `{member.id}`\nCreated: {discord.utils.format_dt(member.created_at, 'R')}\nJoined: {discord.utils.format_dt(member.joined_at, 'R') if member.joined_at else 'Unknown'}\nRoles: {roles}")


@bot.command(name="avatar")
async def prefix_avatar(ctx, member: discord.Member = None):
    await _quiet_delete(ctx.message)
    member = member or ctx.author
    embed = discord.Embed(title=f"{member.display_name}'s avatar", colour=discord.Colour.blurple())
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)


@bot.command(name="serverinfo", aliases=["server"])
async def prefix_serverinfo(ctx):
    await _quiet_delete(ctx.message)
    g = ctx.guild
    await ctx.send(f"**{g.name}**\nMembers: **{g.member_count}**\nChannels: **{len(g.channels)}**\nRoles: **{len(g.roles)-1}**\nCreated: {discord.utils.format_dt(g.created_at, 'R')}\nOwner: <@{g.owner_id}>")


@bot.command(name="channelinfo")
async def prefix_channelinfo(ctx):
    await _quiet_delete(ctx.message)
    c = ctx.channel
    await ctx.send(f"**#{getattr(c,'name','DM')}**\nID: `{c.id}`\nType: `{c.type}`\nCreated: {discord.utils.format_dt(c.created_at, 'R')}")


@bot.command(name="permissions")
async def prefix_permissions(ctx):
    await _quiet_delete(ctx.message)
    me = ctx.guild.me
    if not me:
        await ctx.send("I couldn't inspect my permissions here.", delete_after=6); return
    perms = me.guild_permissions
    important = {"Administrator":perms.administrator,"Manage Server":perms.manage_guild,"Manage Messages":perms.manage_messages,"Moderate Members":perms.moderate_members,"Manage Roles":perms.manage_roles,"Send Messages":perms.send_messages,"Embed Links":perms.embed_links,"Read Message History":perms.read_message_history,"Mention Everyone":perms.mention_everyone}
    await ctx.send("**Horizon Permission Check**\n" + "\n".join(f"{'✅' if v else '❌'} **{k}**" for k,v in important.items()))


@bot.group(name="config", invoke_without_command=True)
@commands.has_guild_permissions(manage_guild=True)
async def prefix_config(ctx):
    await _quiet_delete(ctx.message)
    settings = await bot.db.settings(ctx.guild.id)
    def ch(k): return f"<#{settings[k]}>" if settings[k] else "off"
    await ctx.send(f"**Horizon Config**\nWelcome: {ch('welcome_channel_id')}\nLogs: {ch('log_channel_id')}\nModeration: {'on' if settings['mod_enabled'] else 'off'}\nMod action: {['log','warn','timeout'][settings['mod_action']]}\nUse `!config welcome #channel`, `!config logs #channel`, or `!config show`.\nAI channels are not used; use `!ai <message>`.\nAnnouncements choose their channel and ping directly.")


@prefix_config.command(name="show")
async def config_show(ctx):
    await _quiet_delete(ctx.message)
    settings = await bot.db.settings(ctx.guild.id)
    def ch(k): return f"<#{settings[k]}>" if settings[k] else "off"
    await ctx.send(f"**Horizon Config**\nWelcome: {ch('welcome_channel_id')}\nLogs: {ch('log_channel_id')}\nModeration: {'on' if settings['mod_enabled'] else 'off'}\nMod action: {['log','warn','timeout'][settings['mod_action']]}\nAI channels: not used\nAnnouncements: choose type, ping and channel per announcement.")


@prefix_config.command(name="welcome")
async def config_welcome(ctx, channel: discord.TextChannel = None):
    await _quiet_delete(ctx.message)
    channel = channel or ctx.channel
    await bot.db.set_setting(ctx.guild.id, "welcome_channel_id", channel.id)
    await ctx.send(f"Welcome messages will be posted in {channel.mention}.", delete_after=7)


@prefix_config.command(name="logs")
async def config_logs(ctx, channel: discord.TextChannel = None):
    await _quiet_delete(ctx.message)
    channel = channel or ctx.channel
    await bot.db.set_setting(ctx.guild.id, "log_channel_id", channel.id)
    await ctx.send(f"Moderation logs will be posted in {channel.mention}.", delete_after=7)


@prefix_config.command(name="personality")
async def config_personality(ctx, *, personality: str = ""):
    await _quiet_delete(ctx.message)
    if not personality.strip():
        await ctx.send("Use `!config personality <text>`.", delete_after=6); return
    await bot.db.set_setting(ctx.guild.id, "personality", personality.strip())
    await ctx.send("Horizon personality updated.", delete_after=7)


@bot.command(name="announce")
@commands.has_guild_permissions(manage_guild=True)
async def prefix_announce(ctx, kind: str = "", ping: str = "none", *, raw: str = ""):
    """Typed announcements: !announce <type> <ping> [#channel] | <title> | <message>."""
    await _quiet_delete(ctx.message)
    if kind.lower() not in ANNOUNCEMENT_TYPES:
        await ctx.send("Use `!help announcements` for announcement types and examples.", delete_after=10); return
    parts = [part.strip() for part in raw.split("|")]
    if len(parts) < 2:
        await ctx.send("Format: `!announce <type> <ping> [#channel] | <title> | <message>`", delete_after=10); return
    title, message = parts[0], " | ".join(parts[1:])
    target = ctx.channel
    # Optional channel is accepted as the first token of ping, e.g. `#events`.
    channel_token = ping
    if channel_token.startswith("<#") and channel_token.endswith(">"):
        try:
            channel_id = int(channel_token[2:-1])
            candidate = ctx.guild.get_channel(channel_id)
            if isinstance(candidate, discord.TextChannel):
                target = candidate
                ping = "none"
        except ValueError:
            pass
    # More ergonomic form: `!announce event @role #events | title | body`
    if raw.startswith("#"):
        first, _, remainder = raw.partition(" ")
        if first.startswith("<#"):
            try:
                candidate = ctx.guild.get_channel(int(first[2:-1]))
                if isinstance(candidate, discord.TextChannel):
                    target = candidate
                    parts = [part.strip() for part in remainder.split("|")]
                    if len(parts) >= 2:
                        title, message = parts[0], " | ".join(parts[1:])
            except ValueError:
                pass
    mention, target_obj = resolve_announcement_ping(ctx.guild, ping)
    if ping.lower() in {"@everyone","everyone","@here","here"} and not ctx.author.guild_permissions.mention_everyone:
        await ctx.send("You need the Mention Everyone permission for that ping.", delete_after=8); return
    if isinstance(target_obj, discord.Role) and not target_obj.is_default():
        me = ctx.guild.me
        if not target_obj.mentionable and not (me and me.guild_permissions.manage_roles):
            await ctx.send("That role isn't mentionable and Horizon doesn't have Manage Roles.", delete_after=8); return
    if mention is None:
        await ctx.send("I couldn't resolve that ping. Use `none`, `@here`, `@everyone`, a role mention, or a member mention.", delete_after=8); return
    embed = announcement_embed(kind, title, message, ctx.author.display_name)
    await target.send(content=mention or None, embed=embed, allowed_mentions=discord.AllowedMentions(everyone=True, roles=True, users=True))
    await ctx.send(f"{embed.title} posted in {target.mention}.", delete_after=7)


async def start_hidden_role_game(channel, session, players):
    key = session["key"]
    random.shuffle(players)
    n = len(players)
    special_count = max(1, n // 4)
    roles = {}
    evil_role = "Werewolf" if key == "werewolf" else "Mafia"
    for uid in players[:special_count]: roles[uid] = evil_role
    remaining = players[special_count:]
    if remaining: roles[remaining.pop(0)] = "Seer" if key == "werewolf" else "Detective"
    if remaining: roles[remaining.pop(0)] = "Doctor"
    for uid in remaining: roles[uid] = "Villager" if key == "werewolf" else "Town"
    session.update({"started": True, "phase": "night", "round": 1, "roles": roles, "alive": set(players), "night_actions": {}, "votes": {}})
    for uid, role in roles.items():
        member = channel.guild.get_member(uid)
        if not member: continue
        instructions = f"You are **{role}** in {bot.games.games[key][0]}."
        if role in {evil_role, "Doctor", "Seer", "Detective"}:
            action = {evil_role:"`!kill @player`", "Doctor":"`!protect @player`", "Seer":"`!inspect @player`", "Detective":"`!inspect @player`"}[role]
            instructions += f"\nNight action: {action} (send it in this DM)."
        else:
            instructions += "\nYou have no night action. Wait for the day phase."
        instructions += "\nNever reveal your role publicly unless you choose to during the game."
        try: await member.send(instructions)
        except discord.HTTPException: pass
    await _edit_game_message(channel, session, f"**{bot.games.games[key][0]} — Night 1**\nRoles have been sent privately by DM.\n\nLiving players: **{len(session['alive'])}**\nNight actions happen privately. The host may use `!nightend` when ready.")

async def _hidden_action(ctx, action, member):
    session = None
    for (gid, cid), candidate in list(bot.games.active.items()):
        if candidate.get("phase") == "night" and ctx.author.id in candidate.get("alive", set()):
            # Night commands are intentionally private. Players act from their DMs.
            if isinstance(ctx.channel, discord.DMChannel):
                session = candidate
                break
    if not session:
        await _quiet_delete(ctx.message); return
    role = session["roles"].get(ctx.author.id)
    allowed = {"kill": {"Mafia", "Werewolf"}, "protect": {"Doctor"}, "inspect": {"Seer", "Detective"}}
    await _quiet_delete(ctx.message)
    if role not in allowed[action] or member is None or member.id not in session["alive"] or member.id == ctx.author.id:
        try: await ctx.send("That action is not available to you or that target is invalid.", delete_after=6)
        except discord.HTTPException: pass
        return
    session["night_actions"][ctx.author.id] = (action, member.id)
    try: await ctx.send(f"Your private action **{action}** on **{member.display_name}** is locked in.", delete_after=6)
    except discord.HTTPException: pass
    # Resolve automatically once every non-villager role that has an action has acted.
    required = [uid for uid, r in session["roles"].items() if r in allowed[action] or r in {"Mafia", "Werewolf", "Doctor", "Seer", "Detective"}]
    if all(uid in session["night_actions"] for uid in required):
        # Resolve in the public channel.
        for (gid, cid), candidate in bot.games.active.items():
            if candidate is session:
                guild = bot.get_guild(gid); channel = guild.get_channel(cid) if guild else None
                if channel: await resolve_night(channel, session)
                break

def day_status(session):
    alive_names = [f"<@{uid}>" for uid in session["alive"]]
    voted = len(session.get("votes", {}))
    return f"**{bot.games.games[session['key']][0]} — Day {session['round']}**\nDiscuss and vote privately with `!vote @player`.\nVotes received: **{voted}/{len(session['alive'])}**\n\nAlive: " + ", ".join(alive_names)

async def resolve_night(channel, session):
    actions = list(session.get("night_actions", {}).values())
    kills = [target for action, target in actions if action == "kill"]
    protects = {target for action, target in actions if action == "protect"}
    inspected = [(actor, target) for actor, (action, target) in session.get("night_actions", {}).items() if action == "inspect"]
    killed = None
    if kills:
        counts = {}
        for target in kills: counts[target] = counts.get(target, 0) + 1
        killed = max(counts, key=counts.get)
        if killed in protects: killed = None
    for actor, target in inspected:
        role = session["roles"].get(target, "Unknown")
        user = channel.guild.get_member(actor)
        if user:
            try: await user.send(f"Horizon's private report: **{channel.guild.get_member(target).display_name if channel.guild.get_member(target) else 'That player'}** is **{role}**.")
            except discord.HTTPException: pass
    if killed is not None and killed in session["alive"]:
        session["alive"].remove(killed)
    result = f"**{channel.guild.get_member(killed).display_name}** was eliminated during the night." if killed and channel.guild.get_member(killed) else "Nobody was eliminated during the night."
    session["phase"] = "day"; session["votes"] = {}; session["night_actions"] = {}
    winner = check_hidden_winner(session)
    if winner:
        await _edit_game_message(channel, session, f"**{bot.games.games[session['key']][0]} — {winner} wins!**\n\n{result}\nThe game is over.")
        bot.games.stop(channel.guild.id, channel.id); return
    await _edit_game_message(channel, session, f"**{bot.games.games[session['key']][0]} — Day {session['round']}**\n\n{result}\n\nDiscuss and vote using `!vote @player`. Votes are not displayed until the day resolves.\n\nAlive: " + ", ".join(f"<@{uid}>" for uid in session["alive"]))

def check_hidden_winner(session):
    alive_roles = [session["roles"][uid] for uid in session["alive"]]
    evil = "Werewolf" if session["key"] == "werewolf" else "Mafia"
    evil_count = alive_roles.count(evil)
    good_count = len(alive_roles) - evil_count
    if evil_count == 0: return "Town"
    if evil_count >= good_count: return evil
    return None

async def resolve_day(channel, session):
    votes = session.get("votes", {})
    if not votes:
        await _edit_game_message(channel, session, day_status(session)); return
    counts = {}
    for target in votes.values():
        if target in session["alive"]: counts[target] = counts.get(target, 0) + 1
    if not counts: return
    top = max(counts.values()); leaders = [uid for uid, count in counts.items() if count == top]
    if len(leaders) != 1:
        session["round"] += 1; session["phase"] = "night"; session["votes"] = {}; session["night_actions"] = {}
        await _edit_game_message(channel, session, f"**Day {session['round'] - 1} ended in a tie.**\nNo one was eliminated. Night {session['round']} begins; private roles will act.")
        return
    eliminated = leaders[0]
    session["alive"].remove(eliminated)
    member = channel.guild.get_member(eliminated)
    winner = check_hidden_winner(session)
    if winner:
        await _edit_game_message(channel, session, f"**{bot.games.games[session['key']][0]} — {winner} wins!**\n\n{member.mention if member else 'A player'} was eliminated by the vote.\nThe game is over.")
        bot.games.stop(channel.guild.id, channel.id); return
    session["round"] += 1; session["phase"] = "night"; session["votes"] = {}; session["night_actions"] = {}
    await _edit_game_message(channel, session, f"**{bot.games.games[session['key']][0]} — Night {session['round']}**\n\n{member.mention if member else 'A player'} was eliminated by the vote.\nRoles, check your DMs for your private night action.\nHost can use `!nightend` when ready.")

# ---------------------------------------------------------------------------
# v13 — Phases 10-15 commands
# ---------------------------------------------------------------------------

@rpg_root.command(name="journal", aliases=["questjournal", "quest-log"])
async def rpg_journal(ctx):
    await _rpg_delete(ctx)
    counts, chains = await bot.rpg.quest_journal(ctx.guild.id, ctx.author.id)
    body = (f"**Active:** {counts.get('active', 0)}\n" f"**Complete:** {counts.get('complete', 0)}\n" f"**Claimed:** {counts.get('claimed', 0)}")
    body += "\n\nUse `!rpg quests` to accept quests and complete objectives."
    await _rpg_action_panel(ctx, "📜 Quest Journal", body, True)

@rpg_root.command(name="factions", aliases=["faction-list", "factionlist"])
async def rpg_factions(ctx):
    await _rpg_delete(ctx)
    rows = await bot.rpg.factions(ctx.guild.id)
    status = await bot.rpg.faction_status(ctx.guild.id, ctx.author.id)
    body = "\n\n".join(f"**{key}** — {name}\n{desc}\nIdeology: **{ideology}**\nPassive: **{FACTION_PASSIVES.get(key,{}).get('name','None')}** — {FACTION_PASSIVES.get(key,{}).get('desc','')}" for key, name, desc, ideology in rows)
    body += f"\n\n**Your Allegiance:** `{status[0]}` • Rep **{status[1]}** • Rank **{status[2].title()}**" if status else "\n\nJoin with `!rpg factionjoin <faction_key>`."
    await _rpg_action_panel(ctx, "⚑ Factions of Horizon", body[:4000], True)

@rpg_root.command(name="factionjoin", aliases=["joinfaction", "faction-join"])
async def rpg_factionjoin(ctx, faction_key: str = ""):
    await _rpg_delete(ctx)
    if not faction_key:
        await _rpg_action_panel(ctx, "⚑ Faction", "Use `!rpg factions` first, then `!rpg factionjoin <faction_key>`.", False); return
    ok, msg = await bot.rpg.faction_join(ctx.guild.id, ctx.author.id, faction_key)
    await _rpg_action_panel(ctx, "⚑ Faction Allegiance", msg, ok)

@rpg_root.command(name="endgamemastery", aliases=["endgame-mastery", "mastery"])
async def rpg_endgame(ctx):
    await _rpg_delete(ctx)
    status = await bot.rpg.endgame_status(ctx.guild.id, ctx.author.id)
    if not status:
        await _rpg_action_panel(ctx, "👑 Endgame Mastery", "Create a hero first.", False); return
    arena = status["arena"]
    body = (f"**Level:** {status['level']}\n**Endgame Mastery:** {status['mastery']}\n**Ascension:** {status['ascension']}/5\n\n" f"**Arena Rating:** {arena.get('rating', 1000)}\n**Legendary Trials Cleared:** {status['legendary']}\n**Secret Classes:** {status['secret_classes']}\n**Raid Damage:** {status['raid_damage']:,}\n\nAscend with `!rpg ascend` at level 80 and 100 Mastery.")
    await _rpg_action_panel(ctx, "👑 Endgame Mastery", body, True)

@rpg_root.command(name="ascend", aliases=["ascension"])
async def rpg_ascend(ctx):
    await _rpg_delete(ctx)
    ok, msg = await bot.rpg.endgame_ascend(ctx.guild.id, ctx.author.id)
    await _rpg_action_panel(ctx, "🌌 Ascension", msg, ok)

# ---------------------------------------------------------------------------
# v14 — Phases 16-19 commands
# ---------------------------------------------------------------------------

# -------------------- Message handling --------------------

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.guild:
        if message.content.strip():
            try:
                await bot.db.add_ai_server_message(
                    message.id, message.guild.id, message.channel.id, message.author.id,
                    message.author.display_name, message.content,
                )
            except Exception:
                log.exception("Could not index message for AI history")
        await bot.xp_message(message)

        settings = await bot.db.settings(message.guild.id)
        history = bot.mod_history.get(message.guild.id, [])
        decision = bot.mod.inspect(message.content, history)

        if settings["mod_enabled"] and decision.alert:
            log.warning(
                "Moderation alert guild=%s user=%s reason=%s",
                message.guild.id,
                message.author.id,
                decision.reason,
            )

            if settings["log_channel_id"]:
                channel = message.guild.get_channel(settings["log_channel_id"])
                if channel:
                    try:
                        await channel.send(
                            f"⚠️ **Moderation alert** | {message.author.mention} | "
                            f"{decision.reason} | score={decision.score}"
                        )
                    except discord.HTTPException:
                        pass

        # Only severe, escalating cases can trigger automatic action.
        if (
            settings["mod_enabled"]
            and decision.score >= 6
            and decision.escalation
        ):
            if settings["mod_action"] == 1:
                await bot.db.add_warning(
                    message.guild.id,
                    message.author.id,
                    bot.user.id if bot.user else 0,
                    decision.reason or "Escalated harassment",
                )
            elif (
                settings["mod_action"] == 2
                and isinstance(message.author, discord.Member)
            ):
                try:
                    await message.author.timeout(
                        datetime.timedelta(minutes=10),
                        reason="Severe escalating harassment detected by Horizon",
                    )
                except discord.HTTPException:
                    log.exception("Could not timeout member.")

    if message.guild:
        mod_history=bot.mod_history.setdefault(message.guild.id,[])
        mod_history.append(f"{message.author.display_name}: {message.content[:500]}")
        bot.mod_history[message.guild.id]=mod_history[-20:]

    # Keep command processing alive when on_message is overridden.
    await bot.process_commands(message)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use that command.", delete_after=6)
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing argument. Use `!help` to see the command format.", delete_after=7)
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send("I couldn't understand one of those arguments. Use `!help` for the format.", delete_after=7)
        return
    log.exception("Prefix command error", exc_info=error)
    try:
        await ctx.send("Something went wrong while running that command.", delete_after=7)
    except discord.HTTPException:
        pass


@bot.tree.error
async def command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
):
    if isinstance(error, app_commands.MissingPermissions):
        message = "You don't have permission to use that command."
    elif isinstance(error, app_commands.CommandOnCooldown):
        message = "That command is temporarily on cooldown."
    else:
        log.exception("Command error", exc_info=error)
        message = "Something went wrong. Check the Horizon terminal for details."

    if interaction.response.is_done():
        await interaction.followup.send(message)
    else:
        await interaction.response.send_message(message)


if __name__ == "__main__":
    bot.run(TOKEN)
