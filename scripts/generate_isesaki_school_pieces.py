from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from urllib.request import Request, urlopen

from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data-source" / "isesaki" / "r2ka10204.topojson"
TARGET = ROOT / "src" / "data" / "isesakiSchoolPieces.ts"
SOURCE_URL = "https://geoshape.ex.nii.ac.jp/ka/topojson/2020/10/r2ka10204.topojson"

BOARD_X = 20
BOARD_Y = 20
BOARD_WIDTH = 760
BOARD_HEIGHT = 560
SIMPLIFY_TOLERANCE = 0.00018

SCHOOL_DEFINITIONS = [
    ("kita", "北小学校", "きたしょうがっこう", ["曲輪町", "大手町", "平和町", "若葉町", "安堀町", "太田町", "連取本町", "連取元町"]),
    ("minami", "南小学校", "みなみしょうがっこう", ["本町", "中央町", "緑町", "三光町", "若葉町", "上泉町", "八坂町", "今泉町二丁目", "連取本町", "連取元町", "連取町"]),
    ("uehasu", "殖蓮小学校", "うえはすしょうがっこう", ["三和町", "本関町", "鹿島町", "上植木本町", "豊城町", "上諏訪町", "昭和町", "宮前町"]),
    ("moro", "茂呂小学校", "もろしょうがっこう", ["今泉町一丁目", "粕川町", "北千木町", "南千木町", "茂呂町一丁目", "茂呂町二丁目", "美茂呂町", "茂呂南町", "羽黒町"]),
    ("misato", "三郷小学校", "みさとしょうがっこう", ["波志江町", "安堀町", "太田町"]),
    ("miyago", "宮郷小学校", "みやごうしょうがっこう", ["稲荷町", "宮子町", "田中島町", "田中町", "東上之宮町", "西上之宮町", "宮古町"]),
    ("nawa", "名和小学校", "なわしょうがっこう", ["韮塚町", "阿弥大寺町", "今井町", "山王町", "堀口町", "中町", "柴町", "戸谷塚町"]),
    ("toyoke", "豊受小学校", "とようけしょうがっこう", ["除ケ町", "大正寺町", "富塚町", "下道寺町", "馬見塚町", "長沼町", "上蓮町", "下蓮町", "国領町", "飯島町", "羽黒町"]),
    ("kita-daini", "北第二小学校", "きただいにしょうがっこう", ["喜多町", "宗高町", "柳原町", "寿町", "西田町", "華蔵寺町", "堤西町", "堤下町", "八幡町", "末広町", "乾町"]),
    ("uehasu-daini", "殖蓮第二小学校", "うえはすだいにしょうがっこう", ["豊城町", "上諏訪町", "日乃出町", "昭和町", "宮前町", "東本町", "下植木町"]),
    ("hirose", "広瀬小学校", "ひろせしょうがっこう", ["美茂呂町", "ひろせ町", "茂呂南町", "新栄町", "連取元町", "連取町", "山王町", "中町"]),
    ("bando", "坂東小学校", "ばんどうしょうがっこう", ["福島町", "八斗島町", "除ケ町", "大正寺町", "富塚町", "下道寺町"]),
    ("miyago-daini", "宮郷第二小学校", "みやごうだいにしょうがっこう", ["太田町", "連取本町", "連取元町", "連取町"]),
    ("akabori", "赤堀小学校", "あかぼりしょうがっこう", ["西久保町一丁目", "西久保町二丁目", "西久保町三丁目", "野町", "磯町", "西野町", "赤堀今井町二丁目", "市場町一丁目"]),
    ("akabori-minami", "赤堀南小学校", "あかぼりみなみしょうがっこう", ["赤堀今井町一丁目", "下触町", "五目牛町", "市場町二丁目", "堀下町"]),
    ("akabori-higashi", "赤堀東小学校", "あかぼりひがししょうがっこう", ["曲沢町", "赤堀鹿島町", "間野谷町", "香林町一丁目", "香林町二丁目"]),
    ("azuma", "あずま小学校", "あずましょうがっこう", ["小泉町", "東小保方町", "東町", "八寸町", "田部井町一丁目", "田部井町二丁目", "田部井町三丁目", "上田町", "西小保方町"]),
    ("azuma-minami", "あずま南小学校", "あずまみなみしょうがっこう", ["平井町", "東小保方町", "八寸町", "三室町"]),
    ("azuma-kita", "あずま北小学校", "あずまきたしょうがっこう", ["田部井町一丁目", "田部井町二丁目", "田部井町三丁目", "国定町一丁目", "国定町二丁目"]),
    ("sakai", "境小学校", "さかいしょうがっこう", ["境東", "境", "境萩原", "境百々東", "境美原", "境百々", "境中島", "境西今井", "境上矢島", "境木島", "境下武士", "境島村", "境栄"]),
    ("sakai-uneme", "境采女小学校", "さかいうねめしょうがっこう", ["境伊与久", "境木島", "境下渕名", "境上渕名", "境東新井"]),
    ("sakai-goshi", "境剛志小学校", "さかいごうししょうがっこう", ["境保泉", "境保泉一丁目", "境上武士", "境下武士", "境小此木"]),
    ("sakai-higashi", "境東小学校", "さかいひがししょうがっこう", ["境平塚", "境新栄", "境米岡", "境栄", "境女塚", "境三ツ木"]),
]

ALIASES = {
    "上之宮町": ["東上之宮町", "西上之宮町"],
    "長沼町本郷": ["長沼町"],
}

PREFERRED_AMBIGUOUS_ASSIGNMENTS = {
    "太田町": "miyago-daini",
    "連取本町": "miyago-daini",
    "連取元町": "miyago-daini",
    "連取町": "miyago-daini",
}


def format_number(value: float) -> str:
    text = f"{value:.1f}"
    if text.endswith(".0"):
        return text[:-2]
    return text


def ensure_source():
    if SOURCE.exists():
        return

    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    request = Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        SOURCE.write_bytes(response.read())


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


def normalized_names(name: str):
    if name.startswith("波志江町"):
        return ["波志江町"]
    if name.startswith("馬見塚町"):
        return ["馬見塚町"]
    return ALIASES.get(name, [name])


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


def assign_ambiguous_features(features, town_to_schools):
    unique_geometries = defaultdict(list)
    assignments = {}
    ambiguous = []

    for index, feature in enumerate(features):
        candidates = []
        for name in normalized_names(feature["name"]):
            candidates.extend(town_to_schools.get(name, []))
        candidates = sorted(set(candidates))

        if not candidates:
            continue

        if len(candidates) == 1:
            assignments[index] = candidates[0]
            unique_geometries[candidates[0]].append(feature["geometry"])
        elif (
            feature["name"] in PREFERRED_AMBIGUOUS_ASSIGNMENTS
            and PREFERRED_AMBIGUOUS_ASSIGNMENTS[feature["name"]] in candidates
        ):
            school_id = PREFERRED_AMBIGUOUS_ASSIGNMENTS[feature["name"]]
            assignments[index] = school_id
            unique_geometries[school_id].append(feature["geometry"])
        else:
            ambiguous.append((index, candidates))

    school_unions = {
        school_id: unary_union(geometries)
        for school_id, geometries in unique_geometries.items()
        if geometries
    }

    for index, candidates in ambiguous:
        geometry = features[index]["geometry"]

        def score(school_id: str):
            school_geometry = school_unions.get(school_id)
            if school_geometry is None:
                return (-1, float("-inf"))
            shared_border = geometry.boundary.intersection(school_geometry.boundary).length
            distance = geometry.distance(school_geometry)
            return (shared_border, -distance)

        assignments[index] = max(candidates, key=score)

    return assignments


def main():
    ensure_source()
    topology = json.loads(SOURCE.read_text(encoding="utf-8"))

    town_to_schools = defaultdict(list)
    school_meta = {}
    for school_id, name, reading, towns in SCHOOL_DEFINITIONS:
        school_meta[school_id] = {"name": name, "reading": reading}
        for town in towns:
            town_to_schools[town].append(school_id)

    features = []
    for geometry in topology["objects"]["town"]["geometries"]:
        features.append(
            {
                "name": geometry["properties"]["S_NAME"],
                "geometry": geometry_to_shape(topology, geometry),
            }
        )

    assignments = assign_ambiguous_features(features, town_to_schools)
    school_geometries = defaultdict(list)
    for index, school_id in assignments.items():
        school_geometries[school_id].append(features[index]["geometry"])

    merged = {
        school_id: unary_union(geometries).simplify(SIMPLIFY_TOLERANCE, preserve_topology=True)
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
    for index, school_id in enumerate([definition[0] for definition in SCHOOL_DEFINITIONS]):
        geom = merged[school_id]
        geom_min_x, geom_min_y, geom_max_x, geom_max_y = geom.bounds
        transformed_min_x, transformed_max_y = transform(geom_min_x, geom_min_y)
        transformed_max_x, transformed_min_y = transform(geom_max_x, geom_max_y)
        width = transformed_max_x - transformed_min_x
        height = transformed_max_y - transformed_min_y
        representative = geom.representative_point()
        label_x, label_y = transform(representative.x, representative.y)
        meta = school_meta[school_id]

        pieces.append(
            {
                "id": school_id,
                "name": meta["name"],
                "reading": meta["reading"],
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
        "export const isesakiSchoolPieces: Piece[] = [",
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

    unassigned = sorted(
        {
            feature["name"]
            for index, feature in enumerate(features)
            if index not in assignments
        }
    )
    if unassigned:
        print("Unassigned town features:")
        for name in unassigned:
            print(f"- {name}")

    print(f"Generated {len(pieces)} school district pieces")


if __name__ == "__main__":
    main()
