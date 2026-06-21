from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data-source" / "N03-20240101_10_GML" / "N03-20240101_10.geojson"
TARGET = ROOT / "src" / "data" / "pieces.ts"

BOARD_X = 20
BOARD_Y = 20
BOARD_WIDTH = 760
BOARD_HEIGHT = 560
TRAY_X = 20
TRAY_Y = 610
TRAY_WIDTH = 760
TRAY_HEIGHT = 760
TRAY_COLUMNS = 5
TRAY_ROWS = 7
SIMPLIFY_TOLERANCE = 0.0012
MAP_SCALE = 520

READINGS = {
    "10201": "まえばしし",
    "10202": "たかさきし",
    "10203": "きりゅうし",
    "10204": "いせさきし",
    "10205": "おおたし",
    "10206": "ぬまたし",
    "10207": "たてばやしし",
    "10208": "しぶかわし",
    "10209": "ふじおかし",
    "10210": "とみおかし",
    "10211": "あんなかし",
    "10212": "みどりし",
    "10344": "しんとうむら",
    "10345": "よしおかまち",
    "10366": "うえのむら",
    "10367": "かんなまち",
    "10382": "しもにたまち",
    "10383": "なんもくむら",
    "10384": "かんらまち",
    "10421": "なかのじょうまち",
    "10424": "ながのはらまち",
    "10425": "つまごいむら",
    "10426": "くさつまち",
    "10428": "たかやまむら",
    "10429": "ひがしあがつままち",
    "10443": "かたしなむら",
    "10444": "かわばむら",
    "10448": "しょうわむら",
    "10449": "みなかみまち",
    "10464": "たまむらまち",
    "10521": "いたくらまち",
    "10522": "めいわまち",
    "10523": "ちよだまち",
    "10524": "おおいずみまち",
    "10525": "おうらまち",
}


def format_number(value: float) -> str:
    text = f"{value:.1f}"
    if text.endswith(".0"):
        return text[:-2]
    return text


def ring_to_path(coords, offset_x: float, offset_y: float, transform):
    points = [transform(x, y) for x, y in coords]
    commands = [f"M{format_number(points[0][0] - offset_x)} {format_number(points[0][1] - offset_y)}"]
    for x, y in points[1:]:
        commands.append(f"L{format_number(x - offset_x)} {format_number(y - offset_y)}")
    commands.append("Z")
    return " ".join(commands)


def geometry_to_path(geom: Polygon | MultiPolygon, offset_x: float, offset_y: float, transform):
    polygons = [geom] if isinstance(geom, Polygon) else list(geom.geoms)
    parts: list[str] = []
    for polygon in polygons:
        parts.append(ring_to_path(polygon.exterior.coords, offset_x, offset_y, transform))
        for interior in polygon.interiors:
            parts.append(ring_to_path(interior.coords, offset_x, offset_y, transform))
    return " ".join(parts)


def main():
    with SOURCE.open(encoding="utf-8") as file:
        data = json.load(file)

    by_code = defaultdict(list)
    names: dict[str, str] = {}
    all_geometries = []

    for feature in data["features"]:
        geometry = shape(feature["geometry"])
        props = feature["properties"]
        code = props["N03_007"]
        by_code[code].append(geometry)
        names[code] = props["N03_004"]
        all_geometries.append(geometry)

    merged = {code: unary_union(geometries).simplify(SIMPLIFY_TOLERANCE, preserve_topology=True) for code, geometries in by_code.items()}
    full_bounds = unary_union(all_geometries).bounds
    min_x, min_y, max_x, max_y = full_bounds
    map_width = (max_x - min_x) * MAP_SCALE
    map_height = (max_y - min_y) * MAP_SCALE
    margin_x = BOARD_X + (BOARD_WIDTH - map_width) / 2
    margin_y = BOARD_Y + (BOARD_HEIGHT - map_height) / 2

    def transform(x: float, y: float):
        return (
            margin_x + (x - min_x) * MAP_SCALE,
            margin_y + (max_y - y) * MAP_SCALE,
        )

    inner_width = TRAY_WIDTH - 80
    inner_height = TRAY_HEIGHT - 100
    cell_width = inner_width / TRAY_COLUMNS
    cell_height = inner_height / TRAY_ROWS

    city_codes = sorted(merged.keys())
    pieces = []

    for index, code in enumerate(city_codes):
        geom = merged[code]
        geom_min_x, geom_min_y, geom_max_x, geom_max_y = geom.bounds
        transformed_min_x, transformed_max_y = transform(geom_min_x, geom_min_y)
        transformed_max_x, transformed_min_y = transform(geom_max_x, geom_max_y)
        width = transformed_max_x - transformed_min_x
        height = transformed_max_y - transformed_min_y

        col = index % TRAY_COLUMNS
        row = index // TRAY_COLUMNS
        start_x = TRAY_X + 40 + col * cell_width + max((cell_width - width) / 2, 0)
        start_y = TRAY_Y + 56 + row * cell_height + max((cell_height - height) / 2, 0)

        representative = geom.representative_point()
        label_x, label_y = transform(representative.x, representative.y)

        pieces.append(
            {
                "id": code,
                "name": names[code],
                "reading": READINGS[code],
                "path": geometry_to_path(geom, transformed_min_x, transformed_min_y, transform),
                "width": width,
                "height": height,
                "labelX": label_x - transformed_min_x,
                "labelY": label_y - transformed_min_y,
                "correctX": transformed_min_x,
                "correctY": transformed_min_y,
                "startX": start_x,
                "startY": start_y,
            }
        )

    lines = [
        "export type Piece = {",
        "  id: string;",
        "  name: string;",
        "  reading: string;",
        "  path: string;",
        "  width: number;",
        "  height: number;",
        "  labelX: number;",
        "  labelY: number;",
        "  correctX: number;",
        "  correctY: number;",
        "  startX: number;",
        "  startY: number;",
        "  currentX: number;",
        "  currentY: number;",
        "  placed: boolean;",
        "};",
        "",
        "export const SNAP_DISTANCE = 42;",
        "",
        "// Source: MLIT National Land Numerical Information",
        "// Administrative districts 2024-01-01 for Gunma (N03-20240101_10)",
        "export const initialPieces: Piece[] = [",
    ]

    for piece in pieces:
        lines.extend(
            [
                "  {",
                f'    id: "{piece["id"]}",',
                f'    name: "{piece["name"]}",',
                f'    reading: "{piece["reading"]}",',
                f'    path: "{piece["path"]}",',
                f'    width: {format_number(piece["width"])},',
                f'    height: {format_number(piece["height"])},',
                f'    labelX: {format_number(piece["labelX"])},',
                f'    labelY: {format_number(piece["labelY"])},',
                f'    correctX: {format_number(piece["correctX"])},',
                f'    correctY: {format_number(piece["correctY"])},',
                f'    startX: {format_number(piece["startX"])},',
                f'    startY: {format_number(piece["startY"])},',
                f'    currentX: {format_number(piece["startX"])},',
                f'    currentY: {format_number(piece["startY"])},',
                "    placed: false,",
                "  },",
            ]
        )

    lines.append("];")
    TARGET.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
