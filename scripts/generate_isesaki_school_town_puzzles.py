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
    SCHOOL_DEFINITIONS,
    SOURCE,
    ensure_source,
    format_number,
    geometry_to_path,
    geometry_to_shape,
)


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "src" / "data" / "isesakiSchoolTownPuzzles.ts"
SIMPLIFY_TOLERANCE = 0.0001

READING_OVERRIDES = {
    "ひろせ町": "ひろせちょう",
    "上之宮町": "かみのみやまち",
    "長沼町": "ながぬままち",
    "波志江町": "はしえまち",
    "馬見塚町": "まみづかまち",
}


def town_id(name: str) -> str:
    return (
        name.replace("町", "")
        .replace("一丁目", "-1")
        .replace("二丁目", "-2")
        .replace("三丁目", "-3")
        .replace("ヶ", "ga")
        .replace("ケ", "ga")
    )


def source_candidates(source_name: str, features_by_name: dict[str, list]):
    if source_name in {"東上之宮町", "西上之宮町"}:
        return "上之宮町", features_by_name.get("上之宮町", [])

    if source_name in {"波志江町", "馬見塚町", "長沼町"}:
        geometries = []
        for name, candidates in features_by_name.items():
            if name.startswith(source_name):
                geometries.extend(candidates)
        return source_name, geometries

    return source_name, features_by_name.get(source_name, [])


def infer_reading(name: str, school_reading: str) -> str:
    return READING_OVERRIDES.get(name, name)


def build_pieces(definition, features_by_name):
    school_id, _school_name, school_reading, source_names = definition
    town_geometries = defaultdict(list)
    missing = []

    for source_name in source_names:
        display_name, geometries = source_candidates(source_name, features_by_name)
        if not geometries:
            missing.append(source_name)
            continue
        town_geometries[display_name].extend(geometries)

    if not town_geometries:
        return [], missing

    merged = {
        name: unary_union(geometries).simplify(
            SIMPLIFY_TOLERANCE,
            preserve_topology=True,
        )
        for name, geometries in town_geometries.items()
    }

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
    for index, name in enumerate(merged.keys()):
        geom = merged[name]
        geom_min_x, geom_min_y, geom_max_x, geom_max_y = geom.bounds
        transformed_min_x, transformed_max_y = transform(geom_min_x, geom_min_y)
        transformed_max_x, transformed_min_y = transform(geom_max_x, geom_max_y)
        width = transformed_max_x - transformed_min_x
        height = transformed_max_y - transformed_min_y
        representative = geom.representative_point()
        label_x, label_y = transform(representative.x, representative.y)

        pieces.append(
            {
                "id": f"{school_id}-{town_id(name)}-{index}",
                "name": name,
                "reading": infer_reading(name, school_reading),
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

    return pieces, missing


def piece_lines(piece):
    return [
        "      {",
        f'        id: "{piece["id"]}",',
        f'        name: "{piece["name"]}",',
        f'        reading: "{piece["reading"]}",',
        f'        path: "{piece["path"]}",',
        f'        width: {format_number(piece["width"])},',
        f'        height: {format_number(piece["height"])},',
        f'        labelX: {format_number(piece["labelX"])},',
        f'        labelY: {format_number(piece["labelY"])},',
        f'        correctX: {format_number(piece["correctX"])},',
        f'        correctY: {format_number(piece["correctY"])},',
        f'        startX: {format_number(piece["startX"])},',
        f'        startY: {format_number(piece["startY"])},',
        f'        currentX: {format_number(piece["startX"])},',
        f'        currentY: {format_number(piece["startY"])},',
        "        placed: false,",
        "      },",
    ]


def main():
    ensure_source()
    topology = json.loads(SOURCE.read_text(encoding="utf-8"))
    features_by_name = defaultdict(list)

    for geometry in topology["objects"]["town"]["geometries"]:
        name = geometry["properties"]["S_NAME"]
        features_by_name[name].append(geometry_to_shape(topology, geometry))

    lines = [
        'import type { PuzzleConfig } from "./puzzles";',
        "",
        "export const isesakiSchoolTownPuzzles: PuzzleConfig[] = [",
    ]

    all_missing = {}
    for definition in SCHOOL_DEFINITIONS:
        school_id, school_name, _school_reading, _source_names = definition
        pieces, missing = build_pieces(definition, features_by_name)
        if missing:
            all_missing[school_name] = missing

        if not pieces:
            continue

        lines.extend(
            [
                "  {",
                f'    id: "towns-{school_id}",',
                f'    title: "{school_name} 町名パズル",',
                '    eyebrow: "伊勢崎市 町名 Ver.",',
                f'    modeLabel: "{school_name}町名",',
                "    snapDistance: 38,",
                '    note: "町丁境界をもとにした町名版です。一部地域は町単位で表示します。",',
                "    pieces: [",
            ]
        )
        for piece in pieces:
            lines.extend(piece_lines(piece))
        lines.extend(["    ],", "  },"])

    lines.append("];")
    TARGET.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Generated {len(SCHOOL_DEFINITIONS)} school town puzzle definitions")
    if all_missing:
        print("Missing source town names:")
        for school_name, missing in all_missing.items():
            print(f"- {school_name}: {', '.join(missing)}")


if __name__ == "__main__":
    main()
