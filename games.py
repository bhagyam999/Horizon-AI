from __future__ import annotations

import random
from dataclasses import dataclass, field

import discord


GAMES = {
    "werewolf": (
        "Werewolf",
        "A hidden-role social deduction game. Players receive secret roles, the night phase resolves role actions, and the day phase is discussion plus voting.",
    ),
    "mafia": (
        "Mafia",
        "A hidden-role social deduction game. Mafia coordinate secretly while Town discusses, investigates and votes to eliminate suspects.",
    ),
    "trivia": (
        "Horizon Trivia",
        "A multiple-choice quiz. Horizon asks a question, players choose an answer, and the first correct response wins the round.",
    ),
    "hangman": (
        "Hangman",
        "Horizon chooses a word. Players guess letters until the word is solved or the guess limit is reached.",
    ),
    "wyr": (
        "Would You Rather",
        "Horizon presents two choices. Players vote with buttons and the result is revealed after everyone has voted or the host ends the round.",
    ),
    "truth": (
        "Truth or Dare",
        "Choose Truth or Dare and Horizon gives a server-safe prompt. Use the buttons to keep the round moving.",
    ),
    "rpg": (
        "Horizon RPG",
        "A persistent community RPG using your profile, character, quests, inventory and dice-roll systems.",
    ),
    "rps": (
        "Rock Paper Scissors",
        "Choose rock, paper or scissors and Horizon immediately plays against you.",
    ),
}


TRIVIA = [
    ("What planet is known as the Red Planet?", ["Mars", "Venus", "Jupiter", "Mercury"], 0),
    ("How many sides does a hexagon have?", ["5", "6", "7", "8"], 1),
    ("Which ocean is the largest?", ["Atlantic", "Indian", "Pacific", "Arctic"], 2),
    ("What is H2O?", ["Oxygen", "Water", "Hydrogen", "Salt"], 1),
    ("Which language is primarily used to style web pages?", ["HTML", "CSS", "Python", "SQL"], 1),
    ("Which animal is known for changing its color to camouflage?", ["Chameleon", "Penguin", "Dolphin", "Elephant"], 0),
]

HANGMAN_WORDS = ["horizon", "galaxy", "dragon", "samurai", "adventure", "portal", "constellation", "phantom"]
WYR_ROUNDS = [
    ("Explore a new planet", "Explore a new dimension"),
    ("Master every game", "Master every anime"),
    ("Teleport anywhere", "Read minds"),
    ("Have infinite money", "Have infinite free time"),
]
TRUTHS = [
    "What game could you play for hours without getting bored?",
    "What fictional world would you visit for one day?",
    "What is one skill you wish you could instantly master?",
    "What is your most unusual gaming habit?",
]
DARES = [
    "Send the next message using only three words.",
    "Describe your favorite character without naming them.",
    "Use a random emoji in your next three messages.",
    "Write a dramatic one-line villain speech.",
]


@dataclass
class GameManager:
    games: dict = field(default_factory=lambda: GAMES)
    active: dict = field(default_factory=dict)

    def recommend(self):
        key = random.choice(list(self.games))
        name, description = self.games[key]
        return key, name, description

    def question(self):
        return random.choice(TRIVIA)

    def start(self, guild_id: int, channel_id: int, key: str, host_id: int):
        session = {"key": key, "host_id": host_id, "started_by": host_id}
        self.active[(guild_id, channel_id)] = session
        return session

    def get(self, guild_id: int, channel_id: int):
        return self.active.get((guild_id, channel_id))

    def stop(self, guild_id: int, channel_id: int):
        return self.active.pop((guild_id, channel_id), None)


class TriviaView(discord.ui.View):
    def __init__(self, manager: GameManager, guild_id: int, channel_id: int, question, options, answer):
        super().__init__(timeout=60)
        self.manager = manager
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.answer = answer
        self.question = question
        self.answered = False
        for index, option in enumerate(options):
            button = discord.ui.Button(label=f"{index + 1}. {option}", style=discord.ButtonStyle.primary, custom_id=f"trivia:{index}")
            button.callback = self._make_callback(index)
            self.add_item(button)

    def _make_callback(self, index):
        async def callback(interaction: discord.Interaction):
            if self.answered:
                await interaction.response.send_message("This trivia round is already over.", ephemeral=True)
                return
            self.answered = True
            self.stop()
            self.manager.stop(self.guild_id, self.channel_id)
            if index == self.answer:
                result = f"Correct! **{interaction.user.display_name}** got it first."
            else:
                result = f"Not quite. The correct answer was **{self.question_options[self.answer]}**."
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(content=f"**Horizon Trivia**\n{self.question}\n\n{result}\n\n*Round finished.*", view=self)
        return callback

    @property
    def question_options(self):
        return getattr(self, "_options", [])


class ChoiceView(discord.ui.View):
    def __init__(self, choices: list[tuple[str, str]], timeout: int = 90):
        super().__init__(timeout=timeout)
        self.choice = None
        for label, value in choices:
            button = discord.ui.Button(label=label, style=discord.ButtonStyle.primary)
            button.callback = self._make_callback(value)
            self.add_item(button)

    def _make_callback(self, value):
        async def callback(interaction: discord.Interaction):
            if self.choice is not None:
                await interaction.response.send_message("This round has already been answered.", ephemeral=True)
                return
            self.choice = value
            self.stop()
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
        return callback


class WyrView(discord.ui.View):
    def __init__(self, manager: GameManager, guild_id: int, channel_id: int, left: str, right: str, timeout: int = 90):
        super().__init__(timeout=timeout)
        self.manager = manager
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.votes = {"left": set(), "right": set()}
        self.left = left
        self.right = right
        self.message = None
        for label, value in [(left, "left"), (right, "right")]:
            button = discord.ui.Button(label=label, style=discord.ButtonStyle.primary)
            button.callback = self._make_callback(value)
            self.add_item(button)
        end = discord.ui.Button(label="End Vote", style=discord.ButtonStyle.secondary)
        end.callback = self.end_vote
        self.add_item(end)

    def _make_callback(self, side):
        async def callback(interaction: discord.Interaction):
            self.votes["left"].discard(interaction.user.id)
            self.votes["right"].discard(interaction.user.id)
            self.votes[side].add(interaction.user.id)
            await interaction.response.edit_message(content=self.render(), view=self)
        return callback

    async def end_vote(self, interaction: discord.Interaction):
        self.manager.stop(self.guild_id, self.channel_id)
        self.stop()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=self.render(final=True), view=self)

    def render(self, final=False):
        left = len(self.votes["left"])
        right = len(self.votes["right"])
        title = "**Would You Rather** — Final Result" if final else "**Would You Rather** — Vote below"
        return f"{title}\n\n**A:** {self.left}\nVotes: `{left}`\n\n**B:** {self.right}\nVotes: `{right}`\n\nChoose one. Your vote can be changed before the round ends."


class TruthDareView(discord.ui.View):
    def __init__(self, manager: GameManager, guild_id: int, channel_id: int, truth: str, dare: str, timeout=90):
        super().__init__(timeout=timeout)
        self.manager = manager
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.truth = truth
        self.dare = dare
        truth_button = discord.ui.Button(label="Truth", style=discord.ButtonStyle.primary)
        dare_button = discord.ui.Button(label="Dare", style=discord.ButtonStyle.danger)
        truth_button.callback = self.show_truth
        dare_button.callback = self.show_dare
        self.add_item(truth_button)
        self.add_item(dare_button)

    async def show_truth(self, interaction: discord.Interaction):
        await self.finish(interaction, "Truth", self.truth)

    async def show_dare(self, interaction: discord.Interaction):
        await self.finish(interaction, "Dare", self.dare)

    async def finish(self, interaction, label, prompt):
        self.manager.stop(self.guild_id, self.channel_id)
        self.stop()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=f"**{label}!**\n\n{prompt}\n\n*Round complete.*", view=self)


def make_trivia(manager: GameManager, guild_id: int, channel_id: int):
    question, options, answer = random.choice(TRIVIA)
    view = TriviaView(manager, guild_id, channel_id, question, options, answer)
    view._options = options
    return question, options, view


def make_hangman():
    word = random.choice(HANGMAN_WORDS)
    return {
        "word": word,
        "guessed": set(),
        "wrong": set(),
        "max_wrong": 6,
    }
