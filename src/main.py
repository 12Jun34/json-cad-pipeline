import sys
from pathlib import Path

from json_loader import load_plan
from macro_generator import write_macro
from placement_resolver import resolve_placements
from validator import ValidationError, validate_plan


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN_PATH = PROJECT_ROOT / "examples" / "box.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "macros"


def main() -> int:
    if len(sys.argv) > 2:
        print("Usage: python src/main.py [examples/box.json]")
        return 1

    input_path = DEFAULT_PLAN_PATH if len(sys.argv) == 1 else resolve_project_path(sys.argv[1])

    try:
        plan = load_plan(input_path)
        print(f"Plan loaded: {input_path}")

        plan, was_resolved = resolve_placements(plan)
        if was_resolved:
            print("Placement resolved: OK")

        validate_plan(plan)
        print("Validation: OK")

        output_path = write_macro(plan, DEFAULT_OUTPUT_DIR)
        print(f"Macro generated: {output_path}")
        return 0
    except FileNotFoundError:
        print(f"File not found: {input_path}")
        return 1
    except ValidationError as error:
        print(f"Validation error: {error}")
        return 1
    except Exception as error:
        print(f"Error: {error}")
        return 1


def resolve_project_path(path: str) -> Path:
    input_path = Path(path)
    if input_path.is_absolute():
        return input_path
    return PROJECT_ROOT / input_path


if __name__ == "__main__":
    raise SystemExit(main())
