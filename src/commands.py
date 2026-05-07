from __future__ import annotations

from kompas_macro_builder import KompasMacroBuilder, default_sketch_angle


def emit_command(builder: KompasMacroBuilder, command: dict) -> None:
    command_type = command["type"]
    if command_type in {"create_box", "cut_box"}:
        emit_box(builder, command)
        return
    if command_type in {"create_prism", "cut_prism", "create_triangle", "cut_triangle"}:
        emit_prism(builder, command)
        return
    if command_type in {"create_cylinder", "cut_cylinder"}:
        emit_cylinder(builder, command)
        return

    raise ValueError(f"Unsupported command type: {command_type}")


def emit_box(builder: KompasMacroBuilder, command: dict) -> None:
    origin = command.get("origin", [0, 0, 0])
    size = command["size"]
    plane = command.get("plane", "XOY")
    extrude_mode = command.get("extrude", "normal")
    is_cut = command["type"] == "cut_box"

    sketch_x, sketch_y, sketch_width, sketch_height, depth, select_point = _box_geometry(
        origin, size, plane, extrude_mode
    )

    builder.begin_sketch_on_default_plane(plane)
    builder.draw_rectangle(sketch_x, sketch_y, sketch_width, sketch_height)
    builder.end_sketch(angle=command.get("angle", default_sketch_angle(plane)))
    if "select_point" in command:
        select_point = tuple(command["select_point"])
    _add_extrusion(builder, is_cut, depth, select_point, extrude_mode)


def emit_prism(builder: KompasMacroBuilder, command: dict) -> None:
    plane = command.get("plane", "YOZ")
    extrude_mode = command.get("extrude", "middle")
    depth = command["depth"]
    is_cut = command["type"].startswith("cut_")
    if extrude_mode == "middle":
        depth = depth / 2

    builder.begin_sketch_on_default_plane(plane)
    builder.draw_polygon(command["points"])
    builder.end_sketch(angle=command.get("angle", default_sketch_angle(plane)))
    _add_extrusion(builder, is_cut, depth, tuple(command["select_point"]), extrude_mode)


def emit_cylinder(builder: KompasMacroBuilder, command: dict) -> None:
    plane = command.get("plane", "YOZ")
    extrude_mode = command.get("extrude", "middle")
    center_x, center_y = command["center"]
    radius = command["radius"]
    depth = command["depth"]
    is_cut = command["type"] == "cut_cylinder"
    if extrude_mode == "middle":
        depth = depth / 2

    select_point = tuple(command.get("select_point", _circle_select_point(plane, center_x, center_y, radius)))

    builder.begin_sketch_on_default_plane(plane)
    builder.draw_circle(center_x, center_y, radius)
    builder.end_sketch(angle=command.get("angle", default_sketch_angle(plane)))
    _add_extrusion(builder, is_cut, depth, select_point, extrude_mode)


def _add_extrusion(
    builder: KompasMacroBuilder,
    is_cut: bool,
    depth: float,
    select_point: tuple[float, float, float],
    extrude_mode: str,
) -> None:
    if is_cut:
        builder.add_cut_extrusion(depth=depth, select_point=select_point, mode=extrude_mode)
    else:
        builder.add_boss_extrusion(depth=depth, select_point=select_point, mode=extrude_mode)


def _circle_select_point(
    plane: str,
    center_x: float,
    center_y: float,
    radius: float,
) -> tuple[float, float, float]:
    if plane == "XOY":
        return (center_x + radius, center_y, 0)
    if plane == "XOZ":
        return (center_x + radius, 0, center_y)
    if plane == "YOZ":
        return (0, center_x + radius, center_y)
    raise ValueError(f"Unsupported plane: {plane}")


def _box_geometry(
    origin: list[float],
    size: list[float],
    plane: str,
    extrude_mode: str,
) -> tuple[float, float, float, float, float, tuple[float, float, float]]:
    x, y, z = origin
    width, height, depth = size

    extrusion_depth = depth
    if plane == "XOY":
        sketch_x = x
        sketch_y = y
        sketch_width = width
        sketch_height = -height
        select_point = (x + width, y + height / 2, z)
        extrusion_depth = depth
    elif plane == "XOZ":
        sketch_x = x
        sketch_y = z
        sketch_width = width
        sketch_height = -height
        select_point = (x + width, y, z + height / 2)
        extrusion_depth = depth
    elif plane == "YOZ":
        # This follows the most stable recorded pattern: rectangle on YOZ,
        # negative sketch coordinates, angle=90, middle-plane extrusion.
        sketch_x = y
        sketch_y = z
        sketch_width = -depth
        sketch_height = -width
        select_point = (x, y - depth / 2, z)
        extrusion_depth = height
    else:
        raise ValueError(f"Unsupported plane: {plane}")

    if extrude_mode == "middle":
        extrusion_depth = extrusion_depth / 2

    return sketch_x, sketch_y, sketch_width, sketch_height, extrusion_depth, select_point
