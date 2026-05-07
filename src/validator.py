SUPPORTED_VERSION = "0.1"
SUPPORTED_UNITS = "mm"
SUPPORTED_COMMANDS = {
    "create_box",
    "cut_box",
    "create_prism",
    "cut_prism",
    "create_triangle",
    "cut_triangle",
    "create_cylinder",
    "cut_cylinder",
}
SUPPORTED_PLANES = {"XOY", "XOZ", "YOZ"}
SUPPORTED_EXTRUDE_MODES = {"normal", "middle", "reverse"}


class ValidationError(ValueError):
    pass


def validate_plan(plan: dict) -> None:
    if not isinstance(plan, dict):
        raise ValidationError("Plan must be a JSON object")

    if plan.get("version") != SUPPORTED_VERSION:
        raise ValidationError("Only version 0.1 is supported")

    if plan.get("units") != SUPPORTED_UNITS:
        raise ValidationError("Only mm units are supported")

    if not isinstance(plan.get("part_name"), str) or not plan["part_name"].strip():
        raise ValidationError("part_name is required")

    commands = plan.get("commands")
    if not isinstance(commands, list):
        raise ValidationError("commands must be a list")

    if not commands:
        raise ValidationError("commands must not be empty")

    seen_ids: set[str] = set()
    for index, command in enumerate(commands, start=1):
        validate_command(command, index, seen_ids)


def validate_command(command: dict, index: int, seen_ids: set[str]) -> None:
    if not isinstance(command, dict):
        raise ValidationError(f"commands[{index}] must be an object")

    command_id = command.get("id")
    if not isinstance(command_id, str) or not command_id.strip():
        raise ValidationError(f"commands[{index}].id is required")
    if command_id in seen_ids:
        raise ValidationError(f"Duplicate command id: {command_id}")
    seen_ids.add(command_id)

    command_type = command.get("type")
    if command_type not in SUPPORTED_COMMANDS:
        raise ValidationError(f"Unsupported command type: {command_type}")

    if command_type in {"create_box", "cut_box"}:
        validate_create_box(command)
    elif command_type in {"create_prism", "cut_prism"}:
        validate_create_prism(command)
    elif command_type in {"create_triangle", "cut_triangle"}:
        validate_create_triangle(command)
    elif command_type in {"create_cylinder", "cut_cylinder"}:
        validate_create_cylinder(command)


def validate_create_box(command: dict) -> None:
    origin = command.get("origin", [0, 0, 0])
    size = command.get("size")
    plane = command.get("plane", "XOY")
    extrude = command.get("extrude", "normal")

    if not _is_number_list(origin, 3):
        raise ValidationError("create_box.origin must be a list of 3 numbers")

    if not _is_number_list(size, 3):
        raise ValidationError("create_box.size must be a list of 3 numbers")

    select_point = command.get("select_point")
    if select_point is not None and not _is_number_list(select_point, 3):
        raise ValidationError("create_box.select_point must be a list of 3 numbers")

    if any(value <= 0 for value in size):
        raise ValidationError("create_box.size values must be positive numbers")

    if plane not in SUPPORTED_PLANES:
        raise ValidationError("create_box.plane must be one of: XOY, XOZ, YOZ")

    if extrude not in SUPPORTED_EXTRUDE_MODES:
        raise ValidationError("create_box.extrude must be one of: normal, middle, reverse")


def validate_create_prism(command: dict) -> None:
    points = command.get("points")
    plane = command.get("plane", "YOZ")
    depth = command.get("depth")
    extrude = command.get("extrude", "middle")
    select_point = command.get("select_point")

    if not isinstance(points, list) or len(points) < 3:
        raise ValidationError("create_prism.points must be a list of at least 3 points")

    for point in points:
        if not _is_number_list(point, 2):
            raise ValidationError("create_prism.points must contain [x, y] number pairs")

    if not isinstance(depth, (int, float)) or isinstance(depth, bool) or depth <= 0:
        raise ValidationError("create_prism.depth must be a positive number")

    if plane not in SUPPORTED_PLANES:
        raise ValidationError("create_prism.plane must be one of: XOY, XOZ, YOZ")

    if extrude not in SUPPORTED_EXTRUDE_MODES:
        raise ValidationError("create_prism.extrude must be one of: normal, middle, reverse")

    if not _is_number_list(select_point, 3):
        raise ValidationError("create_prism.select_point must be a list of 3 numbers")


def validate_create_triangle(command: dict) -> None:
    points = command.get("points")
    if not isinstance(points, list) or len(points) != 3:
        raise ValidationError("create_triangle.points must contain exactly 3 points")

    validate_create_prism(command)


def validate_create_cylinder(command: dict) -> None:
    center = command.get("center")
    radius = command.get("radius")
    depth = command.get("depth")
    plane = command.get("plane", "YOZ")
    extrude = command.get("extrude", "middle")
    select_point = command.get("select_point")

    if not _is_number_list(center, 2):
        raise ValidationError("create_cylinder.center must be a list of 2 numbers")

    if not isinstance(radius, (int, float)) or isinstance(radius, bool) or radius <= 0:
        raise ValidationError("create_cylinder.radius must be a positive number")

    if not isinstance(depth, (int, float)) or isinstance(depth, bool) or depth <= 0:
        raise ValidationError("create_cylinder.depth must be a positive number")

    if plane not in SUPPORTED_PLANES:
        raise ValidationError("create_cylinder.plane must be one of: XOY, XOZ, YOZ")

    if extrude not in SUPPORTED_EXTRUDE_MODES:
        raise ValidationError("create_cylinder.extrude must be one of: normal, middle, reverse")

    if select_point is not None and not _is_number_list(select_point, 3):
        raise ValidationError("create_cylinder.select_point must be a list of 3 numbers")


def _is_number_list(value: object, length: int) -> bool:
    return (
        isinstance(value, list)
        and len(value) == length
        and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)
    )
