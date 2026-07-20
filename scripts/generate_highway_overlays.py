from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from shapely.geometry import LineString, MultiLineString, Polygon, shape
from shapely.ops import unary_union

from generate_isesaki_school_pieces import (
    BOARD_HEIGHT,
    BOARD_WIDTH,
    BOARD_X,
    BOARD_Y,
    SCHOOL_DEFINITIONS,
    SOURCE as ISESAKI_SOURCE,
    assign_ambiguous_features,
    ensure_source as ensure_isesaki_source,
    format_number,
    geometry_to_shape,
)
from generate_miyago_town_pieces import TOWN_DEFINITIONS as MIYAGO_TOWN_DEFINITIONS
from generate_pieces import (
    BOARD_HEIGHT as GUNMA_BOARD_HEIGHT,
    BOARD_WIDTH as GUNMA_BOARD_WIDTH,
    BOARD_X as GUNMA_BOARD_X,
    BOARD_Y as GUNMA_BOARD_Y,
    MAP_SCALE as GUNMA_MAP_SCALE,
    SOURCE as GUNMA_SOURCE,
)
from generate_isesaki_school_town_puzzles import source_candidates


ROOT = Path(__file__).resolve().parents[1]
OSM_SOURCE = ROOT / "data-source" / "osm" / "gunma_motorways.json"
TARGET = ROOT / "src" / "data" / "highwayOverlays.ts"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_QUERY = """[out:json][timeout:25];
(
  way["highway"="motorway"](36.0,138.3,37.1,139.8);
);
out geom tags;"""

HIGHWAY_SIMPLIFY_TOLERANCE = 0.00035


def ensure_osm_source():
    if OSM_SOURCE.exists():
        return

    OSM_SOURCE.parent.mkdir(parents=True, exist_ok=True)
    data = urlencode({"data": OVERPASS_QUERY}).encode()
    request = Request(
        OVERPASS_URL,
        data=data,
        headers={"User-Agent": "gunma-puzzle-dev/1.0"},
    )
    with urlopen(request, timeout=60) as response:
        OSM_SOURCE.write_bytes(response.read())


def load_highways():
    ensure_osm_source()
    data = json.loads(OSM_SOURCE.read_text(encoding="utf-8"))
    highways = []

    for element in data["elements"]:
        geometry = element.get("geometry")
        if not geometry or len(geometry) < 2:
            continue

        tags = element.get("tags", {})
        name = tags.get("name") or tags.get("ref") or "高速道路"
        line = LineString((point["lon"], point["lat"]) for point in geometry)
        highways.append(
            {
                "id": str(element["id"]),
                "name": name,
                "geometry": line.simplify(HIGHWAY_SIMPLIFY_TOLERANCE, preserve_topology=True),
            }
        )

    return highways


def lines_from_geometry(geometry):
    if geometry.is_empty:
        return []
    if isinstance(geometry, LineString):
        return [geometry]
    if isinstance(geometry, MultiLineString):
        return list(geometry.geoms)
    if hasattr(geometry, "geoms"):
        lines = []
        for part in geometry.geoms:
            lines.extend(lines_from_geometry(part))
        return lines
    return []


def line_to_path(line: LineString, transform):
    coords = list(line.coords)
    if len(coords) < 2:
        return ""

    first_x, first_y = transform(*coords[0])
    commands = [f"M{format_number(first_x)} {format_number(first_y)}"]
    for x, y in coords[1:]:
        point_x, point_y = transform(x, y)
        commands.append(f"L{format_number(point_x)} {format_number(point_y)}")
    return " ".join(commands)


def overlays_for_area(puzzle_id: str, area_geometry, transform, highways):
    paths_by_name = defaultdict(list)

    for highway in highways:
        clipped = highway["geometry"].intersection(area_geometry)
        paths = [
            line_to_path(line, transform)
            for line in lines_from_geometry(clipped)
            if line.length > 0.0005
        ]
        paths = [path for path in paths if path]
        if not paths:
            continue

        paths_by_name[highway["name"]].extend(paths)

    overlays = []
    for index, (name, paths) in enumerate(sorted(paths_by_name.items())):
        overlays.append(
            {
                "id": f"{puzzle_id}-highway-{index}",
                "name": name,
                "path": " ".join(paths),
            }
        )

    return overlays


def gunma_context():
    with GUNMA_SOURCE.open(encoding="utf-8") as file:
        data = json.load(file)

    geometries = [shape(feature["geometry"]) for feature in data["features"]]
    area_geometry = unary_union(geometries)
    min_x, min_y, max_x, max_y = area_geometry.bounds
    map_width = (max_x - min_x) * GUNMA_MAP_SCALE
    map_height = (max_y - min_y) * GUNMA_MAP_SCALE
    margin_x = GUNMA_BOARD_X + (GUNMA_BOARD_WIDTH - map_width) / 2
    margin_y = GUNMA_BOARD_Y + (GUNMA_BOARD_HEIGHT - map_height) / 2

    def transform(x: float, y: float):
        return (
            margin_x + (x - min_x) * GUNMA_MAP_SCALE,
            margin_y + (max_y - y) * GUNMA_MAP_SCALE,
        )

    return area_geometry, transform


def isesaki_features():
    ensure_isesaki_source()
    topology = json.loads(ISESAKI_SOURCE.read_text(encoding="utf-8"))
    features = []

    for geometry in topology["objects"]["town"]["geometries"]:
        features.append(
            {
                "name": geometry["properties"]["S_NAME"],
                "geometry": geometry_to_shape(topology, geometry),
            }
        )

    return features


def transform_for_area(area_geometry):
    min_x, min_y, max_x, max_y = area_geometry.bounds
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

    return transform


def isesaki_school_context(features):
    town_to_schools = defaultdict(list)
    for school_id, _name, _reading, towns in SCHOOL_DEFINITIONS:
        for town in towns:
            town_to_schools[town].append(school_id)

    assignments = assign_ambiguous_features(features, town_to_schools)
    geometries = [features[index]["geometry"] for index in assignments]
    area_geometry = unary_union(geometries)
    return area_geometry, transform_for_area(area_geometry)


def features_by_name(features):
    by_name = defaultdict(list)
    for feature in features:
        by_name[feature["name"]].append(feature["geometry"])
    return by_name


def miyago_context(by_name):
    geometries = []
    for _town_id, _name, _reading, source_names in MIYAGO_TOWN_DEFINITIONS:
        for source_name in source_names:
            geometries.extend(by_name[source_name])

    area_geometry = unary_union(geometries)
    return area_geometry, transform_for_area(area_geometry)


def school_town_contexts(by_name):
    contexts = {}

    for school_id, _school_name, _school_reading, source_names in SCHOOL_DEFINITIONS:
        town_geometries = []
        for source_name in source_names:
            _display_name, geometries = source_candidates(source_name, by_name)
            town_geometries.extend(geometries)

        if not town_geometries:
            continue

        area_geometry = unary_union(town_geometries)
        contexts[f"towns-{school_id}"] = (area_geometry, transform_for_area(area_geometry))

    return contexts


def write_output(overlays_by_puzzle_id):
    lines = [
        'import type { MapOverlay } from "./puzzles";',
        "",
        "export const highwayOverlaysByPuzzleId: Record<string, MapOverlay[]> = {",
    ]

    for puzzle_id, overlays in overlays_by_puzzle_id.items():
        lines.append(f'  "{puzzle_id}": [')
        for overlay in overlays:
            lines.extend(
                [
                    "    {",
                    f'      id: "{overlay["id"]}",',
                    f'      name: "{overlay["name"]}",',
                    f'      path: "{overlay["path"]}",',
                    "    },",
                ]
            )
        lines.append("  ],")

    lines.append("};")
    TARGET.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    highways = load_highways()
    overlays_by_puzzle_id = {}

    area_geometry, transform = gunma_context()
    overlays_by_puzzle_id["gunma-municipalities"] = overlays_for_area(
        "gunma-municipalities",
        area_geometry,
        transform,
        highways,
    )

    features = isesaki_features()
    by_name = features_by_name(features)

    area_geometry, transform = isesaki_school_context(features)
    overlays_by_puzzle_id["isesaki-schools"] = overlays_for_area(
        "isesaki-schools",
        area_geometry,
        transform,
        highways,
    )

    area_geometry, transform = miyago_context(by_name)
    overlays_by_puzzle_id["miyago-towns"] = overlays_for_area(
        "miyago-towns",
        area_geometry,
        transform,
        highways,
    )

    for puzzle_id, (area_geometry, transform) in school_town_contexts(by_name).items():
        overlays_by_puzzle_id[puzzle_id] = overlays_for_area(
            puzzle_id,
            area_geometry,
            transform,
            highways,
        )

    write_output(overlays_by_puzzle_id)
    print(f"Generated highway overlays for {len(overlays_by_puzzle_id)} puzzles")


if __name__ == "__main__":
    main()
