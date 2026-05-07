from pathlib import Path

from commands import emit_command
from kompas_macro_builder import KompasMacroBuilder


def generate_macro_text(plan: dict) -> str:
    builder = KompasMacroBuilder()
    builder.add_header(plan["part_name"])

    for command in plan["commands"]:
        emit_command(builder, command)

    return builder.build()


def write_macro(plan: dict, output_dir: str | Path = "artifacts/macros") -> Path:
    macro_text = generate_macro_text(plan)
    output_path = Path(output_dir) / f"{plan['part_name']}.m3m"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(macro_text, encoding="utf-8")
    return output_path
