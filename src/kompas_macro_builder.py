from __future__ import annotations

from dataclasses import dataclass, field


PLANE_CONSTANTS = {
    "XOY": "o3d_planeXOY",
    "XOZ": "o3d_planeXOZ",
    "YOZ": "o3d_planeYOZ",
}

DEFAULT_SKETCH_ANGLES = {
    "XOY": 180,
    "XOZ": 180,
    "YOZ": 90,
}


@dataclass
class KompasMacroBuilder:
    lines: list[str] = field(default_factory=list)
    feature_index: int = 1

    def build(self) -> str:
        return "\n".join(self.lines).rstrip() + "\n"

    def add_header(self, part_name: str) -> None:
        self.lines.extend(
            [
                "# -*- coding: utf-8 -*-",
                "#|0",
                "",
                "import pythoncom",
                "from win32com.client import Dispatch, gencache",
                "",
                "import LDefin2D",
                "import MiscellaneousHelpers as MH",
                "",
                f'PART_NAME = "{part_name}"',
                "",
                "kompas6_constants = gencache.EnsureModule(",
                '    "{75C9F5D0-B5B8-4526-8681-9903C567D2ED}", 0, 1, 0',
                ").constants",
                "kompas6_constants_3d = gencache.EnsureModule(",
                '    "{2CAF168C-7961-4B90-9DA2-701419BEEFE3}", 0, 1, 0',
                ").constants",
                "",
                "kompas6_api5_module = gencache.EnsureModule(",
                '    "{0422828C-F174-495E-AC5D-D31014DBBE87}", 0, 1, 0',
                ")",
                "kompas_object = kompas6_api5_module.KompasObject(",
                '    Dispatch("Kompas.Application.5")._oleobj_.QueryInterface(',
                "        kompas6_api5_module.KompasObject.CLSID, pythoncom.IID_IDispatch",
                "    )",
                ")",
                "MH.iKompasObject = kompas_object",
                "",
                "kompas_api7_module = gencache.EnsureModule(",
                '    "{69AC2981-37C0-4379-84FD-5DD2F3C0A520}", 0, 1, 0',
                ")",
                "application = kompas_api7_module.IApplication(",
                '    Dispatch("Kompas.Application.7")._oleobj_.QueryInterface(',
                "        kompas_api7_module.IApplication.CLSID, pythoncom.IID_IDispatch",
                "    )",
                ")",
                "MH.iApplication = application",
                "",
                "Documents = application.Documents",
                "kompas_document = application.ActiveDocument",
                "kompas_document_3d = kompas_api7_module.IKompasDocument3D(kompas_document)",
                "iDocument3D = kompas_object.ActiveDocument3D()",
                "",
            ]
        )

    def refresh_part(self) -> None:
        self.lines.extend(
            [
                "iPart7 = kompas_document_3d.TopPart",
                "iPart = iDocument3D.GetPart(kompas6_constants_3d.pTop_Part)",
                "",
            ]
        )

    def begin_sketch_on_default_plane(self, plane: str, angle: int | float | None = None) -> None:
        plane_constant = PLANE_CONSTANTS[plane]
        self.refresh_part()
        self.lines.extend(
            [
                "iSketch = iPart.NewEntity(kompas6_constants_3d.o3d_sketch)",
                "iDefinition = iSketch.GetDefinition()",
                f"iPlane = iPart.GetDefaultEntity(kompas6_constants_3d.{plane_constant})",
                "iDefinition.SetPlane(iPlane)",
                "iSketch.Create()",
                "iDocument2D = iDefinition.BeginEdit()",
                "kompas_document_2d = kompas_api7_module.IKompasDocument2D(kompas_document)",
                "iDocument2D = kompas_object.ActiveDocument2D()",
                "",
            ]
        )
        if angle is not None:
            self.lines.append(f"iDefinition.angle = {format_number(angle)}")

    def draw_rectangle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        construction_diagonals: bool = True,
        add_origin_point: bool = True,
    ) -> None:
        x2 = x + width
        y2 = y + height
        self.lines.extend(
            [
                f"obj = iDocument2D.ksLineSeg({format_number(x)}, {format_number(y)}, {format_number(x2)}, {format_number(y)}, 1)",
                f"obj = iDocument2D.ksLineSeg({format_number(x2)}, {format_number(y)}, {format_number(x2)}, {format_number(y2)}, 1)",
                f"obj = iDocument2D.ksLineSeg({format_number(x2)}, {format_number(y2)}, {format_number(x)}, {format_number(y2)}, 1)",
                f"obj = iDocument2D.ksLineSeg({format_number(x)}, {format_number(y2)}, {format_number(x)}, {format_number(y)}, 1)",
            ]
        )
        if construction_diagonals:
            self.lines.extend(
                [
                    f"obj = iDocument2D.ksLineSeg({format_number(x2)}, {format_number(y)}, {format_number(x)}, {format_number(y2)}, 2)",
                    f"obj = iDocument2D.ksLineSeg({format_number(x)}, {format_number(y)}, {format_number(x2)}, {format_number(y2)}, 2)",
                ]
            )
        if add_origin_point:
            self.lines.append("obj = iDocument2D.ksPoint(0, 0, 0)")

    def draw_polygon(
        self,
        points: list[list[float]],
        construction_diagonals: bool = True,
        add_origin_point: bool = True,
    ) -> None:
        for index, point in enumerate(points):
            next_point = points[(index + 1) % len(points)]
            self.lines.append(
                "obj = iDocument2D.ksLineSeg("
                f"{format_number(point[0])}, {format_number(point[1])}, "
                f"{format_number(next_point[0])}, {format_number(next_point[1])}, 1)"
            )

        if construction_diagonals and len(points) == 4:
            self.lines.extend(
                [
                    "obj = iDocument2D.ksLineSeg("
                    f"{format_number(points[0][0])}, {format_number(points[0][1])}, "
                    f"{format_number(points[2][0])}, {format_number(points[2][1])}, 2)",
                    "obj = iDocument2D.ksLineSeg("
                    f"{format_number(points[1][0])}, {format_number(points[1][1])}, "
                    f"{format_number(points[3][0])}, {format_number(points[3][1])}, 2)",
                ]
            )

        if add_origin_point:
            self.lines.append("obj = iDocument2D.ksPoint(0, 0, 0)")

    def draw_circle(
        self,
        center_x: float,
        center_y: float,
        radius: float,
        add_origin_point: bool = True,
    ) -> None:
        self.lines.append(
            "obj = iDocument2D.ksCircle("
            f"{format_number(center_x)}, {format_number(center_y)}, {format_number(radius)}, 1)"
        )
        if add_origin_point:
            self.lines.append("obj = iDocument2D.ksPoint(0, 0, 0)")

    def end_sketch(self, angle: int | float | None = None, left_handed: bool = True) -> None:
        self.lines.append("iDefinition.EndEdit()")
        if angle is not None:
            self.lines.append(f"iDefinition.angle = {format_number(angle)}")
        self.lines.extend(
            [
                "iSketch = kompas_object.TransferInterface(iDefinition, kompas6_constants.ksAPI7Dual, 0)",
                f"iSketch.LeftHandedCS = {str(left_handed)}",
                "iSketch.Update()",
                "",
            ]
        )

    def add_boss_extrusion(
        self,
        depth: float,
        select_point: tuple[float, float, float],
        mode: str = "normal",
    ) -> None:
        self._add_extrusion(
            entity="o3d_bossExtrusion",
            name_prefix="Boss extrusion",
            depth=depth,
            select_point=select_point,
            mode=mode,
            cut=False,
        )

    def add_cut_extrusion(
        self,
        depth: float,
        select_point: tuple[float, float, float],
        mode: str = "normal",
    ) -> None:
        self._add_extrusion(
            entity="o3d_cutExtrusion",
            name_prefix="Cut extrusion",
            depth=depth,
            select_point=select_point,
            mode=mode,
            cut=True,
        )

    def _add_extrusion(
        self,
        entity: str,
        name_prefix: str,
        depth: float,
        select_point: tuple[float, float, float],
        mode: str,
        cut: bool,
    ) -> None:
        self.refresh_part()
        sx, sy, sz = select_point
        direction = "dtMiddlePlane" if mode == "middle" else "dtNormal"
        normal_depth = -depth if mode == "reverse" else depth
        reverse_depth = depth if mode == "middle" else 0
        self.lines.extend(
            [
                f"obj = iPart.NewEntity(kompas6_constants_3d.{entity})",
                "iDefinition = obj.GetDefinition()",
                "iCollection = iPart.EntityCollection(kompas6_constants_3d.o3d_edge)",
                f"iCollection.SelectByPoint({format_number(sx)}, {format_number(sy)}, {format_number(sz)})",
                "iEdge = iCollection.Last()",
                "iEdgeDefinition = iEdge.GetDefinition()",
                "iSketch = iEdgeDefinition.GetOwnerEntity()",
                "iDefinition.SetSketch(iSketch)",
            ]
        )
        if cut:
            self.lines.append("iDefinition.cut = True")
        self.lines.extend(
            [
                "iExtrusionParam = iDefinition.ExtrusionParam()",
                f"iExtrusionParam.direction = kompas6_constants_3d.{direction}",
                f"iExtrusionParam.depthNormal = {format_number(normal_depth)}",
                f"iExtrusionParam.depthReverse = {format_number(reverse_depth)}",
                "iExtrusionParam.draftOutwardNormal = False",
                "iExtrusionParam.draftOutwardReverse = False",
                "iExtrusionParam.draftValueNormal = 0",
                "iExtrusionParam.draftValueReverse = 0",
                "iExtrusionParam.typeNormal = kompas6_constants_3d.etBlind",
                "iExtrusionParam.typeReverse = kompas6_constants_3d.etBlind",
                "iThinParam = iDefinition.ThinParam()",
                "iThinParam.thin = False",
                f'obj.name = "{name_prefix}:{self.feature_index}"',
                "iColorParam = obj.ColorParam()",
                "iColorParam.ambient = 0.5",
                "iColorParam.color = 9474192",
                "iColorParam.diffuse = 0.6",
                "iColorParam.emission = 0.5",
                "iColorParam.shininess = 0.8",
                "iColorParam.specularity = 0.8",
                "iColorParam.transparency = 1",
                "obj.Create()",
                "",
            ]
        )
        self.feature_index += 1


def default_sketch_angle(plane: str) -> int:
    return DEFAULT_SKETCH_ANGLES[plane]


def format_number(value: float | int) -> str:
    if isinstance(value, int):
        return str(value)
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.12g}"
