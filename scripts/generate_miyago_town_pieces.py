from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from shapely.ops import unary_union

from generate_isesaki_school_pieces import (
    BOARD_HEIGHT,
    BOARD_WIDTH,
    BOARD_X,
    BOARD_Y,
    SOURCE,
    ensure_source,
    format_number,
    geometry_to_path,
    geometry_to_shape,
)


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "src" / "data" / "miyagoTownPieces.ts"

SIMPLIFY_TOLERANCE = 0.0001

TOWN_DEFINITIONS = [
    ("inari", "稲荷町", "いなりちょう", ["稲荷町"]),
    ("miyako", "宮子町", "みやこまち", ["宮子町"]),
    ("tanakajima", "田中島町", "たなかじままち", ["田中島町"]),
    ("tanaka", "田中町", "たなかまち", ["田中町"]),
    ("kaminomiya", "上之宮町", "かみのみやまち", ["上之宮町"]),
    ("miyafuru", "宮古町", "みやふるまち", ["宮古町"]),
    ("ota", "太田町", "おおたまち", ["太田町"]),
    ("tsunatori-hon", "連取本町", "つなとりほんまち", ["連取本町"]),
    ("tsunatori-moto", "連取元町", "つなとりもとまち", ["連取元町"]),
    ("tsunatori", "連取町", "つなとりまち", ["連取町"]),
]


def main():
    ensure_source()
    topology = json.loads(SOURCE.read_text(encoding="utf-8"))

    features_by_name = defaultdict(list)
    for geometry in topology["objects"]["town"]["geometries"]:
        name = geometry["properties"]["S_NAME"]
        features_by_name[name].append(geometry_to_shape(topology, geometry))

    merged = {}
    missing = []
    for town_id, _name, _reading, source_names in TOWN_DEFINITIONS:
        geometries = []
        for source_name in source_names:
            geometries.extend(features_by_name.get(source_name, []))

        if not geometries:
            missing.extend(source_names)
            continue

        merged[town_id] = unary_union(geometries).simplify(
            SIMPLIFY_TOLERANCE,
            preserve_topology=True,
        )

    if missing:
        raise ValueError(f"Missing town boundaries: {', '.join(missing)}")

    full_bounds = unary_union(list(merged.values())).bounds
    min_x, min_y, max_x, max_y = full_bounds
    map_scale = min(BOARD_WIDTH / (max_x - min_x), BOARD_HEIGHT / (max_y - min_y)) * 0.94
    map_width = (max_x - min_x) * map_scale
    map_height = (max_y - min_y) * map_scale
    margin_x = BOARD_X + (BOARD_WIDTH - map_width) / 2
    margin_y = BOARD_Y + (BOARD_HEIGHT - map_height) / 2

    def transform(x: float, y: float):
        return (
            margin_x + (x - min_x) * map_scale,
            margin_y + (max_y - y) * map_scale,
        )

    pieces = []
    for town_id, name, reading, _source_names in TOWN_DEFINITIONS:
        geom = merged[town_id]
        geom_min_x, geom_min_y, geom_max_x, geom_max_y = geom.bounds
        transformed_min_x, transformed_max_y = transform(geom_min_x, geom_min_y)
        transformed_max_x, transformed_min_y = transform(geom_max_x, geom_max_y)
        width = transformed_max_x - transformed_min_x
        height = transformed_max_y - transformed_min_y
        representative = geom.representative_point()
        label_x, label_y = transform(representative.x, representative.y)

        pieces.append(
            {
                "id": town_id,
                "name": name,
                "reading": reading,
                "path": geometry_to_path(geom, transformed_min_x, transformed_min_y, transform),
                "width": width,
                "height": height,
                "labelX": label_x - transformed_min_x,
                "labelY": label_y - transformed_min_y,
                "correctX": transformed_min_x,
                "correctY": transformed_min_y,
                "startX": 0,
                "startY": 0,
            }
        )

    lines = [
        'import type { Piece } from "./pieces";',
        "",
        "export const miyagoTownPieces: Piece[] = [",
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
    print(f"Generated {len(pieces)} Miyago town pieces")


if __name__ == "__main__":
    main()
