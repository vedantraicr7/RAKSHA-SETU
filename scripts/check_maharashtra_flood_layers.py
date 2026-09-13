import requests
import xml.etree.ElementTree as ET

WMS = "https://bhuvan-gp1.nrsc.gov.in/bhuvan/gwc/service/wms"

layers = [
    "mh_2026_24_07_18",
    "mh_2026_24_07_06",
    "mh_2026_23_07_18",
    "mh_2026_08_07_06",
    "mh_2026_09_07_18",
    "mh_2026_08_07_18",
    "mh_2026_06_07_18",
    "mh_2026_07_07_06",
]

# Raigad bbox in WGS84
RAIGAD = {
    "west": 72.81232910045199,
    "south": 17.850620870059018,
    "east": 73.66627541364355,
    "north": 19.1354826345965,
}

params = {
    "service": "WMS",
    "request": "GetCapabilities",
    "version": "1.1.1",
}

print("Fetching WMS capabilities...")

r = requests.get(
    WMS,
    params=params,
    timeout=60
)

r.raise_for_status()

root = ET.fromstring(r.content)

print("\nChecking Maharashtra flood layers")
print("=" * 90)

found = 0

for layer in root.findall(".//Layer"):

    name = layer.findtext("Name")

    if name not in layers:
        continue

    found += 1

    title = layer.findtext("Title")

    bbox = layer.find("LatLonBoundingBox")

    if bbox is None:
        print("\nLayer:", name)
        print("Title:", title)
        print("No LatLonBoundingBox found")
        continue

    west = float(bbox.attrib["minx"])
    south = float(bbox.attrib["miny"])
    east = float(bbox.attrib["maxx"])
    north = float(bbox.attrib["maxy"])

    overlaps = not (
        east < RAIGAD["west"]
        or west > RAIGAD["east"]
        or north < RAIGAD["south"]
        or south > RAIGAD["north"]
    )

    print("\nLayer:", name)
    print("Title:", title)
    print(
        "BBox:",
        west,
        south,
        east,
        north
    )
    print(
        "Overlaps Raigad:",
        "YES" if overlaps else "NO"
    )

print("\nLayers found in capabilities:", found)
