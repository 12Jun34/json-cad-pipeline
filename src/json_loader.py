import json
from pathlib import Path


def load_plan(path: str | Path) -> dict:
    plan_path = Path(path)
    with plan_path.open("r", encoding="utf-8") as file:
        return json.load(file)
