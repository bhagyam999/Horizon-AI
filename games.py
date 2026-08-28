import random

GAMES = {
    "werewolf": (
        "Werewolf",
        "Secret roles, night actions, daytime discussion and voting. "
        "Horizon explains the rules and can act as moderator."
    ),
    "mafia": (
        "Mafia",
        "A hidden-role game where Mafia act at night and Town investigates "
        "and votes during the day."
    ),
    "trivia": (
        "Horizon Trivia",
        "Question rounds where players answer in chat and Horizon keeps score."
    ),
    "hangman": (
        "Hangman",
        "Horizon chooses a word and players guess letters."
    ),
    "wyr": (
        "Would You Rather",
        "Horizon posts two choices and the server votes."
    ),
    "truth": (
        "Truth or Dare",
        "Players choose truth or dare with server-safe prompts."
    ),
    "rpg": (
        "Horizon RPG",
        "Persistent characters, classes, quests, inventory and dice rolls."
    ),
    "rps": (
        "Rock Paper Scissors",
        "Instant match against Horizon."
    ),
}


class GameManager:
    def __init__(self):
        self.games = GAMES

    def recommend(self):
        key = random.choice(list(self.games))
        name, description = self.games[key]
        return key, name, description

    def question(self):
        questions = [
            (
                "What planet is known as the Red Planet?",
                ["Mars", "Venus", "Jupiter", "Mercury"],
                0,
            ),
            (
                "How many sides does a hexagon have?",
                ["5", "6", "7", "8"],
                1,
            ),
            (
                "Which ocean is the largest?",
                ["Atlantic", "Indian", "Pacific", "Arctic"],
                2,
            ),
            (
                "What is H2O?",
                ["Oxygen", "Water", "Hydrogen", "Salt"],
                1,
            ),
        ]
        return random.choice(questions)
