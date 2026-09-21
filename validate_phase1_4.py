import ast
from pathlib import Path

for name in ("rpg.py", "bot.py", "database.py", "ai_provider.py", "games.py"):
    ast.parse(Path(name).read_text(encoding="utf-8"), filename=name)
print("Syntax validation passed for core Python modules.")
