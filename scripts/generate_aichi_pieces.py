from __future__ import annotations

import json
import zipfile
from collections import defaultdict
from pathlib import Path
from urllib.request import Request, urlopen

from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data-source" / "N03-20240101_23_GML"
SOURCE = SOURCE_DIR / "N03-20240101_23.geojson"
SOURCE_ZIP = ROOT / "data-source" / "N03-20240101_23_GML.zip"
SOURCE_URL = "https://nlftp.mlit.go.jp/ksj/gml/data/N03/N03-2024/N03-20240101_23_GML.zip"
TARGET = ROOT / "src" / "data" / "aichiPieces.ts"

BOARD_X = 20
BOARD_Y = 20
BOARD_WIDTH = 760
BOARD_HEIGHT = 560
SIMPLIFY_TOLERANCE = 0.0009
MAP_PADDING_SCALE = 0.86

READINGS = {
    "名古屋市": "なごやし",
    "豊橋市": "とよはしし",
    "岡崎市": "おかざきし",
    "一宮市": "いちのみやし",
    "瀬戸市": "せとし",
    "半田市": "はんだし",
    "春日井市": "かすがいし",
    "豊川市": "とよかわし",
    "津島市": "つしまし",
    "碧南市": "へきなんし",
    "刈谷市": "かりやし",
    "豊田市": "とよたし",
    "安城市": "あんじょうし",
    "西尾市": "にしおし",
    "蒲郡市": "がまごおりし",
    "犬山市": "いぬやまし",
    "常滑市": "とこなめし",
    "江南市": "こうなんし",
    "小牧市": "こまきし",
    "稲沢市": "いなざわし",
    "新城市": "しんしろし",
    "東海市": "とうかいし",
    "大府市": "おおぶし",
    "知多市": "ちたし",
    "知立市": "ちりゅうし",
    "尾張旭市": "おわりあさひし",
    "高浜市": "たかはまし",
    "岩倉市": "いわくらし",
    "豊明市": "とよあけし",
    "日進市": "にっしんし",
    "田原市": "たはらし",
    "愛西市": "あいさいし",
    "清須市": "きよすし",
    "北名古屋市": "きたなごやし",
    "弥富市": "やとみし",
    "みよし市": "みよしし",
    "あま市": "あまし",
    "長久手市": "ながくてし",
    "東郷町": "とうごうちょう",
    "豊山町": "とよやまちょう",
    "大口町": "おおぐちちょう",
    "扶桑町": "ふそうちょう",
    "大治町": "おおはるちょう",
    "蟹江町": "かにえちょう",
    "飛島村": "とびしまむら",
    "阿久比町": "あぐいちょう",
    "東浦町": "ひがしうらちょう",
    "南知多町": "みなみちたちょう",
    "美浜町": "みはまちょう",
    "武豊町": "たけとよちょう",
    "幸田町": "こうたちょう",
    "設楽町": "したらちょう",
    "東栄町": "とうえいちょう",
    "豊根村": "とよねむら",
}


def ensure_source():
    if SOURCE.exists():
        return

    SOURCE_ZIP.parent.mkdir(parents=True, exist_ok=True)
    if not SOURCE_ZIP.exists():
        request = Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=120) as response:
            SOURCE_ZIP.write_bytes(response.read())

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SOURCE_ZIP) as archive:
        archive.extractall(SOURCE_DIR)


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
    ensure_source()
    with SOURCE.open(encoding="utf-8") as file:
        data = json.load(file)

    geometries_by_name = defaultdict(list)
    all_geometries = []

    for feature in data["features"]:
        props = feature["properties"]
        name = props["N03_004"]
        if name == "所属未定地":
            continue

        geometry = shape(feature["geometry"])
        geometries_by_name[name].append(geometry)
        all_geometries.append(geometry)

    merged = {
        name: unary_union(geometries).simplify(
            SIMPLIFY_TOLERANCE,
            preserve_topology=True,
        )
        for name, geometries in geometries_by_name.items()
    }

    full_bounds = unary_union(all_geometries).bounds
    min_x, min_y, max_x, max_y = full_bounds
    map_scale = min(BOARD_WIDTH / (max_x - min_x), BOARD_HEIGHT / (max_y - min_y)) * MAP_PADDING_SCALE
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
    for index, name in enumerate(sorted(merged.keys())):
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
                "id": f"aichi-{index + 1:02d}",
                "name": name,
                "reading": READINGS[name],
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
        "// Source: MLIT National Land Numerical Information",
        "// Administrative districts 2024-01-01 for Aichi (N03-20240101_23)",
        "export const aichiPieces: Piece[] = [",
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
    print(f"Generated {len(pieces)} Aichi municipality pieces")


if __name__ == "__main__":
    main()
