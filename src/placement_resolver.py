from __future__ import annotations

from copy import deepcopy

from validator import ValidationError


DEFAULT_PLANE = "YOZ"


def resolve_placements(plan: dict) -> tuple[dict, bool]:
    resolved_plan = {
        "version": plan.get("version"),
        "units": plan.get("units"),
        "part_name": plan.get("part_name"),
        "commands": [],
    }
    objects: dict[str, dict] = {}
    changed = False

    for command in plan.get("commands", []):
        needs_resolve = "placement" in command or "attach" in command

        if needs_resolve:
            resolved_command, metadata = resolve_command(command, objects)
            resolved_plan["commands"].append(resolved_command)
            if metadata is not None:
                objects[command["id"]] = metadata
            changed = True
            continue

        resolved_command = deepcopy(command)
        resolved_plan["commands"].append(resolved_command)
        metadata = metadata_from_low_level(resolved_command)
        if metadata is not None:
            objects[resolved_command["id"]] = metadata

    return resolved_plan, changed


def resolve_command(command: dict, objects: dict[str, dict]) -> tuple[dict, dict | None]:
    command_type = command.get("type")
    if command_type in {"create_box", "cut_box"}:
        return resolve_box(command, objects)
    if command_type in {"create_triangle", "cut_triangle"}:
        return resolve_triangle(command, objects)
    if command_type in {"create_cylinder", "cut_cylinder"}:
        return resolve_cylinder(command, objects)

    raise ValidationError(f"Placement is not supported for command type: {command_type}")


def resolve_box(command: dict, objects: dict[str, dict]) -> tuple[dict, dict | None]:
    size = command.get("size")
    if not _is_number_list(size, 3):
        raise ValidationError("placed create_box.size must be [width, height, depth]")

    width, height, depth = size
    if min(width, height, depth) <= 0:
        raise ValidationError("placed create_box.size values must be positive")

    if "attach" in command:
        origin = attach_origin(command["attach"], objects, width, height)
    else:
        placement = command.get("placement", {})
        origin = placement.get("origin", command.get("origin", [0, 0, 0]))

    if not _is_number_list(origin, 3):
        raise ValidationError("placed create_box origin must be [x, y, z]")

    x, y, z = origin
    resolved = {
        "id": command["id"],
        "type": command_type_or_default(command, "create_box"),
        "origin": [x, y, z],
        "size": [height, depth, width],
        "plane": DEFAULT_PLANE,
        "extrude": command.get("extrude", "middle"),
        "select_point": [x, y - width / 2, z],
    }
    metadata = box_metadata(command["id"], origin, width, height, depth)
    return resolved, metadata


def resolve_triangle(command: dict, objects: dict[str, dict]) -> tuple[dict, dict | None]:
    size = command.get("size")
    if not _is_number_list(size, 3):
        raise ValidationError("placed create_triangle.size must be [width, height, depth]")

    width, height, depth = size
    if min(width, height, depth) <= 0:
        raise ValidationError("placed create_triangle.size values must be positive")

    if "attach" in command:
        target = target_metadata(command["attach"], objects)
        select_x = target["x"]
        face = command["attach"].get("face")
        if face != "top":
            raise ValidationError("placed create_triangle currently supports attach.face='top'")
        center_y, base_z = attach_center(command["attach"], target)
        base_z = target["z_max"]
    else:
        placement = command.get("placement", {})
        origin = placement.get("origin", command.get("origin", [0, 0, 0]))
        if not _is_number_list(origin, 3):
            raise ValidationError("placed create_triangle origin must be [x, y, z]")
        select_x, origin_y, origin_z = origin
        center_y = origin_y - width / 2
        base_z = origin_z

    points = [
        [center_y + width / 2, base_z],
        [center_y - width / 2, base_z],
        [center_y, base_z + height],
    ]
    resolved = {
        "id": command["id"],
        "type": command_type_or_default(command, "create_triangle"),
        "plane": DEFAULT_PLANE,
        "points": points,
        "depth": depth,
        "extrude": command.get("extrude", "middle"),
        "select_point": [select_x, center_y + width / 4, base_z + height / 2],
    }
    return resolved, None


def resolve_cylinder(command: dict, objects: dict[str, dict]) -> tuple[dict, dict | None]:
    radius = command.get("radius")
    if not isinstance(radius, (int, float)) or isinstance(radius, bool) or radius <= 0:
        raise ValidationError("placed cylinder.radius must be a positive number")

    if "attach" in command:
        target = target_metadata(command["attach"], objects)
        select_x = target["x"]
        face = command["attach"].get("face")
        if face != "front":
            raise ValidationError("placed cylinder currently supports attach.face='front'")
        center_y, center_z = attach_center(command["attach"], target)
        depth = resolve_depth(command.get("depth", "half"), target)
    else:
        placement = command.get("placement", {})
        center = placement.get("center", command.get("center"))
        if not _is_number_list(center, 2):
            raise ValidationError("placed cylinder center must be [y, z]")
        center_y, center_z = center
        select_x = placement.get("x", 0)
        depth = command.get("depth")

    if not isinstance(depth, (int, float)) or isinstance(depth, bool) or depth <= 0:
        raise ValidationError("placed cylinder.depth must be a positive number or 'half'")

    resolved = {
        "id": command["id"],
        "type": command_type_or_default(command, "create_cylinder"),
        "plane": DEFAULT_PLANE,
        "center": [center_y, center_z],
        "radius": radius,
        "depth": depth,
        "extrude": command.get("extrude", "normal"),
        "select_point": [select_x, center_y + radius, center_z],
    }
    return resolved, None


def attach_origin(attach: dict, objects: dict[str, dict], width: float, height: float) -> list[float]:
    target = target_metadata(attach, objects)
    face = attach.get("face")
    center_y, center_z = attach_center(attach, target)

    if face == "top":
        return [target["x"], center_y + width / 2, target["z_max"]]
    if face == "bottom":
        return [target["x"], center_y + width / 2, target["z_min"] - height]
    if face == "front":
        return [target["x"], center_y + width / 2, center_z + height / 2]

    raise ValidationError("attach.face must be one of: top, bottom, front")


def attach_center(attach: dict, target: dict) -> tuple[float, float]:
    position = attach.get("position", "center")
    offset = attach.get("offset", [0, 0])
    if not _is_number_list(offset, 2):
        raise ValidationError("attach.offset must be [dy, dz]")

    if position != "center":
        raise ValidationError("attach.position currently supports only 'center'")

    center_y = (target["y_min"] + target["y_max"]) / 2 + offset[0]
    center_z = (target["z_min"] + target["z_max"]) / 2 + offset[1]
    return center_y, center_z


def target_metadata(attach: dict, objects: dict[str, dict]) -> dict:
    target_id = attach.get("target")
    if target_id not in objects:
        raise ValidationError(f"attach target not found: {target_id}")
    return objects[target_id]


def resolve_depth(value: object, target: dict) -> float:
    if value == "half":
        return target["depth"] / 2
    if value == "through":
        return target["depth"] * 3
    return value


def metadata_from_low_level(command: dict) -> dict | None:
    if command.get("type") != "create_box":
        return None
    if command.get("plane") != DEFAULT_PLANE:
        return None
    if not _is_number_list(command.get("size"), 3):
        return None
    origin = command.get("origin", [0, 0, 0])
    if not _is_number_list(origin, 3):
        return None

    height, depth, width = command["size"]
    return box_metadata(command["id"], origin, width, height, depth)


def box_metadata(command_id: str, origin: list[float], width: float, height: float, depth: float) -> dict:
    x, y, z = origin
    return {
        "id": command_id,
        "type": "box",
        "x": x,
        "y_min": y - width,
        "y_max": y,
        "z_min": z - height,
        "z_max": z,
        "width": width,
        "height": height,
        "depth": depth,
    }


def command_type_or_default(command: dict, default_type: str) -> str:
    return command.get("type", default_type)


def _is_number_list(value: object, length: int) -> bool:
    return (
        isinstance(value, list)
        and len(value) == length
        and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)
    )
