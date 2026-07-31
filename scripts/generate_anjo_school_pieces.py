from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from urllib.request import Request, urlopen

from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data-source" / "anjo" / "r2ka23212.topojson"
SOURCE_URL = "https://geoshape.ex.nii.ac.jp/ka/topojson/2020/23/r2ka23212.topojson"
TARGET = ROOT / "src" / "data" / "anjoSchoolPieces.ts"

BOARD_X = 20
BOARD_Y = 20
BOARD_WIDTH = 760
BOARD_HEIGHT = 560
SIMPLIFY_TOLERANCE = 0.00012

SCHOOL_DEFINITIONS = [
    (
        "anjo-chubu",
        "安城中部小学校",
        "あんじょうちゅうぶしょうがっこう",
        ["昭和町", "大東町", "明治本町", "池浦町"],
    ),
    (
        "anjo-nanbu",
        "安城南部小学校",
        "あんじょうなんぶしょうがっこう",
        ["河野町", "安城町赤塚", "古井町", "東明町"],
    ),
    (
        "anjo-seibu",
        "安城西部小学校",
        "あんじょうせいぶしょうがっこう",
        ["赤松町", "福釜町"],
    ),
    (
        "anjo-tobu",
        "安城東部小学校",
        "あんじょうとうぶしょうがっこう",
        [
            "大岡町",
            "北山崎町",
            "上条町",
            "高木町",
            "西別所町",
            "浜富町",
            "東別所町",
            "別郷町",
            "法連町",
            "山崎町",
        ],
    ),
    (
        "anjo-hokubu",
        "安城北部小学校",
        "あんじょうほくぶしょうがっこう",
        ["今本町", "東栄町", "浜屋町"],
    ),
    (
        "nishikimachi",
        "錦町小学校",
        "にしきまちしょうがっこう",
        [
            "相生町",
            "朝日町",
            "末広町",
            "錦町",
            "日の出町",
            "南町",
            "小堤町",
            "城南町",
            "大山町",
        ],
    ),
    ("takatana", "高棚小学校", "たかたなしょうがっこう", ["高棚町"]),
    (
        "meiwa",
        "明和小学校",
        "めいわしょうがっこう",
        ["東端町", "根崎町"],
    ),
    (
        "shiki",
        "志貴小学校",
        "しきしょうがっこう",
        ["宇頭茶屋町", "尾崎町", "柿碕町", "橋目町"],
    ),
    (
        "sakurai",
        "桜井小学校",
        "さくらいしょうがっこう",
        ["小川町", "木戸町", "寺領町", "野寺町", "姫小川町", "藤井町"],
    ),
    (
        "sakuno",
        "作野小学校",
        "さくのしょうがっこう",
        ["住吉町一丁目", "住吉町二丁目", "住吉町五丁目", "住吉町七丁目", "住吉町荒曽根"],
    ),
    (
        "shonan",
        "祥南小学校",
        "しょうなんしょうがっこう",
        ["安城町秋葉西"],
    ),
    (
        "joyama",
        "丈山小学校",
        "じょうざんしょうがっこう",
        ["石井町", "和泉町", "榎前町", "城ケ入町"],
    ),
    (
        "nihongi",
        "二本木小学校",
        "にほんぎしょうがっこう",
        ["二本木町", "三河安城本町", "美園町", "緑町"],
    ),
    (
        "satomachi",
        "里町小学校",
        "さとまちしょうがっこう",
        ["里町"],
    ),
    (
        "sakuramachi",
        "桜町小学校",
        "さくらまちしょうがっこう",
        ["桜町", "御幸本町", "花ノ木町", "百石町"],
    ),
    (
        "orin",
        "桜林小学校",
        "おうりんしょうがっこう",
        ["川島町", "東町", "堀内町", "村高町", "桜井町"],
    ),
    (
        "shinden",
        "新田小学校",
        "しんでんしょうがっこう",
        ["新明町", "弁天町", "新田町", "東新町"],
    ),
    (
        "imaike",
        "今池小学校",
        "いまいけしょうがっこう",
        ["今池町", "住吉町三丁目"],
    ),
    (
        "mikawa-anjo",
        "三河安城小学校",
        "みかわあんじょうしょうがっこう",
        ["三河安城東町", "三河安城南町", "三河安城町一丁目", "箕輪町", "横山町"],
    ),
    (
        "nashinosato",
        "梨の里小学校",
        "なしのさとしょうがっこう",
        ["井杭山町", "二本木新町", "三河安城町二丁目", "篠目町"],
    ),
]


def ensure_source():
    if SOURCE.exists():
        return

    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    request = Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=60) as response:
        SOURCE.write_bytes(response.read())


def format_number(value: float) -> str:
    text = f"{value:.1f}"
    if text.endswith(".0"):
        return text[:-2]
    return text


def arc_points(topology: dict, arc_index: int):
    if arc_index >= 0:
        return topology["arcs"][arc_index]
    return list(reversed(topology["arcs"][~arc_index]))


def ring_points(topology: dict, arc_indexes: list[int]):
    points = []
    for arc_index in arc_indexes:
        points_in_arc = arc_points(topology, arc_index)
        if points:
            points.extend(points_in_arc[1:])
        else:
            points.extend(points_in_arc)
    return points


def geometry_to_shape(topology: dict, geometry: dict):
    if geometry["type"] == "Polygon":
        rings = [ring_points(topology, ring) for ring in geometry["arcs"]]
        return Polygon(rings[0], rings[1:])

    if geometry["type"] == "MultiPolygon":
        polygons = []
        for polygon in geometry["arcs"]:
            rings = [ring_points(topology, ring) for ring in polygon]
            polygons.append(Polygon(rings[0], rings[1:]))
        return MultiPolygon(polygons)

    raise ValueError(f"Unsupported geometry type: {geometry['type']}")


def ring_to_path(coords, offset_x: float, offset_y: float, transform):
    points = [transform(x, y) for x, y in coords]
    commands = [
        f"M{format_number(points[0][0] - offset_x)} {format_number(points[0][1] - offset_y)}"
    ]
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


def find_school_id(feature_name: str, town_to_school: dict[str, str]):
    matches = [
        (town_name, school_id)
        for town_name, school_id in town_to_school.items()
        if feature_name == town_name or feature_name.startswith(town_name)
    ]
    if not matches:
        return None

    return max(matches, key=lambda item: len(item[0]))[1]


def main():
    ensure_source()
    topology = json.loads(SOURCE.read_text(encoding="utf-8"))

    town_to_school = {}
    school_meta = {}
    school_order = []
    for school_id, name, reading, towns in SCHOOL_DEFINITIONS:
        school_order.append(school_id)
        school_meta[school_id] = {"name": name, "reading": reading}
        for town in towns:
            town_to_school[town] = school_id

    school_geometries = defaultdict(list)
    unassigned = []
    for geometry in topology["objects"]["town"]["geometries"]:
        name = geometry["properties"]["S_NAME"]
        school_id = find_school_id(name, town_to_school)
        if school_id is None:
            unassigned.append(name)
            continue

        school_geometries[school_id].append(geometry_to_shape(topology, geometry))

    merged = {
        school_id: unary_union(geometries).simplify(
            SIMPLIFY_TOLERANCE,
            preserve_topology=True,
        )
        for school_id, geometries in school_geometries.items()
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
    for school_id in school_order:
        geom = merged[school_id]
        geom_min_x, geom_min_y, geom_max_x, geom_max_y = geom.bounds
        transformed_min_x, transformed_max_y = transform(geom_min_x, geom_min_y)
        transformed_max_x, transformed_min_y = transform(geom_max_x, geom_max_y)
        representative = geom.representative_point()
        label_x, label_y = transform(representative.x, representative.y)
        meta = school_meta[school_id]

        pieces.append(
            {
                "id": school_id,
                "name": meta["name"],
                "reading": meta["reading"],
                "path": geometry_to_path(geom, transformed_min_x, transformed_min_y, transform),
                "width": transformed_max_x - transformed_min_x,
                "height": transformed_max_y - transformed_min_y,
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
        "// Source: Geoshape 2020 town boundaries for Anjo and Anjo City school district list.",
        "// Road- and address-number-based areas are approximated to available town/aza boundaries.",
        "export const anjoSchoolPieces: Piece[] = [",
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

    if unassigned:
        print("Unassigned town features:")
        for name in sorted(set(unassigned)):
            print(f"- {name}")

    print(f"Generated {len(pieces)} Anjo school district pieces")


if __name__ == "__main__":
    main()
