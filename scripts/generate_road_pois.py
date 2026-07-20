from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from shapely.geometry import Point
from shapely.ops import unary_union

from generate_highway_overlays import (
    aichi_context,
    features_by_name,
    gunma_context,
    isesaki_features,
    isesaki_school_context,
    load_highways,
    miyago_context,
    school_town_contexts,
)


ROOT = Path(__file__).resolve().parents[1]
OSM_SOURCES = [
    (
        ROOT / "data-source" / "osm" / "gunma_motorway_pois.json",
        (36.0, 138.3, 37.1, 139.8),
    ),
    (
        ROOT / "data-source" / "osm" / "aichi_motorway_pois.json",
        (34.45, 136.55, 35.55, 137.9),
    ),
]
TARGET = ROOT / "src" / "data" / "roadPois.ts"
MAX_DISTANCE_FROM_HIGHWAY = 0.008
NEARBY_POI_MERGE_DISTANCE = 5
OVERLAPPING_NAME_MERGE_DISTANCE = 32
EXCLUDED_NAME_PARTS = ("道の駅",)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_QUERY_TEMPLATE = """[out:json][timeout:30];
(
  node["highway"="motorway_junction"]({bbox});
  way["highway"="services"]({bbox});
  way["highway"="rest_area"]({bbox});
  relation["highway"="services"]({bbox});
  relation["highway"="rest_area"]({bbox});
);
out center tags;"""


def ensure_osm_source(path: Path, bbox: tuple[float, float, float, float]):
    if path.exists():
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    bbox_text = ",".join(str(value) for value in bbox)
    query = OVERPASS_QUERY_TEMPLATE.format(bbox=bbox_text)
    data = urlencode({"data": query}).encode()
    request = Request(
        OVERPASS_URL,
        data=data,
        headers={"User-Agent": "gunma-puzzle-dev/1.0"},
    )
    with urlopen(request, timeout=90) as response:
        path.write_bytes(response.read())


def format_number(value: float) -> str:
    text = f"{value:.1f}"
    if text.endswith(".0"):
        return text[:-2]
    return text


def poi_kind(tags: dict):
    highway = tags.get("highway")
    name = tags.get("name", "")

    if (
        "SA" in name
        or "ＳＡ" in name
        or "サービスエリア" in name
    ):
        return "sa"
    if (
        "PA" in name
        or "ＰＡ" in name
        or "パーキングエリア" in name
    ):
        return "pa"
    if highway == "motorway_junction":
        return "ic"
    if highway == "services":
        return "sa"
    if highway == "rest_area":
        return "pa"
    return None


def poi_name(tags: dict, kind: str):
    return tags.get("name") or tags.get("name:ja")


def display_name(name: str, kind: str):
    normalized = unicodedata.normalize("NFKC", name).strip()
    if kind == "ic":
        normalized = re.sub(r"(入口|出口)$", "", normalized)

    # Directional up/down or east/west facilities are close together on a children's map.
    normalized = re.sub(r"[（(](上り|下り|東行き|西行き)[）)]", "", normalized)
    normalized = normalized.replace("スマートIC", "スマートIC")

    parts = []
    for part in re.split(r"\s*[;/／、]\s*", normalized):
        cleaned = part.strip()
        if cleaned and cleaned not in parts:
            parts.append(cleaned)

    return " / ".join(parts)


def merge_kind(kinds):
    if "sa" in kinds:
        return "sa"
    if "pa" in kinds:
        return "pa"
    return "ic"


def merge_name_parts(items):
    parts = []
    for item in items:
        for part in item["name"].split(" / "):
            if part and part not in parts:
                parts.append(part)

    return " / ".join(parts)


def name_parts_for_cluster(cluster):
    return {
        part
        for item in cluster["items"]
        for part in item["name"].split(" / ")
        if part
    }


def merge_cluster(target, source):
    target["x_total"] += source["x_total"]
    target["y_total"] += source["y_total"]
    target["count"] += source["count"]
    target["x"] = target["x_total"] / target["count"]
    target["y"] = target["y_total"] / target["count"]
    target["items"].extend(source["items"])


def merge_overlapping_name_clusters(clusters):
    index = 0
    while index < len(clusters):
        current = clusters[index]
        current_parts = name_parts_for_cluster(current)
        merged = False

        for other_index in range(index + 1, len(clusters)):
            other = clusters[other_index]
            other_parts = name_parts_for_cluster(other)
            distance = (
                (current["x"] - other["x"]) ** 2
                + (current["y"] - other["y"]) ** 2
            ) ** 0.5

            if distance <= OVERLAPPING_NAME_MERGE_DISTANCE and current_parts & other_parts:
                merge_cluster(current, other)
                clusters.pop(other_index)
                merged = True
                break

        if not merged:
            index += 1

    return clusters


def ts_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def load_pois():
    elements = []
    for path, bbox in OSM_SOURCES:
        ensure_osm_source(path, bbox)
        data = json.loads(path.read_text(encoding="utf-8"))
        elements.extend(data["elements"])

    pois = []
    seen = set()

    for element in elements:
        tags = element.get("tags", {})
        kind = poi_kind(tags)
        if kind is None:
            continue

        if "lat" in element and "lon" in element:
            lon = element["lon"]
            lat = element["lat"]
        elif "center" in element:
            lon = element["center"]["lon"]
            lat = element["center"]["lat"]
        else:
            continue

        raw_name = poi_name(tags, kind)
        if not raw_name:
            continue

        name = display_name(raw_name, kind)
        if any(excluded in name for excluded in EXCLUDED_NAME_PARTS):
            continue

        key = (kind, name, round(lon, 4), round(lat, 4))
        if key in seen:
            continue
        seen.add(key)

        pois.append(
            {
                "source_id": f"{element['type']}-{element['id']}",
                "kind": kind,
                "name": name,
                "point": Point(lon, lat),
            }
        )

    return pois


def filter_pois_near_highways(pois):
    highway_geometry = unary_union([highway["geometry"] for highway in load_highways()])

    return [
        poi
        for poi in pois
        if poi["point"].distance(highway_geometry) <= MAX_DISTANCE_FROM_HIGHWAY
    ]


def pois_for_area(puzzle_id: str, area_geometry, transform, pois):
    clusters = []

    for poi in pois:
        if not area_geometry.covers(poi["point"]):
            continue

        x, y = transform(poi["point"].x, poi["point"].y)
        matching_cluster = None

        for cluster in clusters:
            distance = ((x - cluster["x"]) ** 2 + (y - cluster["y"]) ** 2) ** 0.5
            if distance <= NEARBY_POI_MERGE_DISTANCE:
                matching_cluster = cluster
                break

        if matching_cluster is None:
            clusters.append(
                {
                    "x": x,
                    "y": y,
                    "x_total": x,
                    "y_total": y,
                    "count": 1,
                    "items": [poi],
                }
            )
            continue

        matching_cluster["x_total"] += x
        matching_cluster["y_total"] += y
        matching_cluster["count"] += 1
        matching_cluster["x"] = matching_cluster["x_total"] / matching_cluster["count"]
        matching_cluster["y"] = matching_cluster["y_total"] / matching_cluster["count"]
        matching_cluster["items"].append(poi)

    clusters = merge_overlapping_name_clusters(clusters)
    results = []
    for index, cluster in enumerate(
        sorted(
            clusters,
            key=lambda item: (
                merge_kind({poi["kind"] for poi in item["items"]}),
                merge_name_parts(item["items"]),
            ),
        ),
        start=1,
    ):
        kind = merge_kind({poi["kind"] for poi in cluster["items"]})
        results.append(
            {
                "id": f"{puzzle_id}-{kind}-{index}",
                "kind": kind,
                "name": merge_name_parts(cluster["items"]),
                "x": cluster["x"],
                "y": cluster["y"],
            }
        )

    return results


def write_output(pois_by_puzzle_id):
    lines = [
        'import type { MapPoi } from "./puzzles";',
        "",
        "export const roadPoisByPuzzleId: Record<string, MapPoi[]> = {",
    ]

    for puzzle_id, pois in pois_by_puzzle_id.items():
        lines.append(f'  "{puzzle_id}": [')
        for poi in pois:
            lines.extend(
                [
                    "    {",
                    f'      id: {ts_string(poi["id"])},',
                    f'      kind: "{poi["kind"]}",',
                    f'      name: {ts_string(poi["name"])},',
                    f'      x: {format_number(poi["x"])},',
                    f'      y: {format_number(poi["y"])},',
                    "    },",
                ]
            )
        lines.append("  ],")

    lines.append("};")
    TARGET.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    pois = filter_pois_near_highways(load_pois())
    pois_by_puzzle_id = {}

    area_geometry, transform = gunma_context()
    pois_by_puzzle_id["gunma-municipalities"] = pois_for_area(
        "gunma-municipalities",
        area_geometry,
        transform,
        pois,
    )

    area_geometry, transform = aichi_context()
    pois_by_puzzle_id["aichi-municipalities"] = pois_for_area(
        "aichi-municipalities",
        area_geometry,
        transform,
        pois,
    )

    features = isesaki_features()
    by_name = features_by_name(features)

    area_geometry, transform = isesaki_school_context(features)
    pois_by_puzzle_id["isesaki-schools"] = pois_for_area(
        "isesaki-schools",
        area_geometry,
        transform,
        pois,
    )

    area_geometry, transform = miyago_context(by_name)
    pois_by_puzzle_id["miyago-towns"] = pois_for_area(
        "miyago-towns",
        area_geometry,
        transform,
        pois,
    )

    for puzzle_id, (area_geometry, transform) in school_town_contexts(by_name).items():
        pois_by_puzzle_id[puzzle_id] = pois_for_area(
            puzzle_id,
            area_geometry,
            transform,
            pois,
        )

    write_output(pois_by_puzzle_id)
    print(f"Generated road POIs for {len(pois_by_puzzle_id)} puzzles")


if __name__ == "__main__":
    main()
