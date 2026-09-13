from pathlib import Path
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="RAKSHA-SETU API",
    description=(
        "Multi-hazard risk and relocation "
        "decision-support API for Raigad"
    ),
    version="0.1.0",
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# DATA PATHS
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = (
    BASE_DIR
    / "data"
    / "processed"
    / "frontend"
)


FILES = {
    "decisions":
        DATA_DIR / "priority_decisions.geojson",

    "sites":
        DATA_DIR / "recommended_sites.geojson",

    "links":
        DATA_DIR / "relocation_links.geojson",

    "recommended_habitations":
        DATA_DIR / "recommended_habitations.geojson",
}


# ---------------------------------------------------------
# LOAD GEOJSON
# ---------------------------------------------------------

def load_geojson(path: Path):

    if not path.exists():
        raise RuntimeError(
            f"Required dataset not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


DECISIONS = load_geojson(
    FILES["decisions"]
)

SITES = load_geojson(
    FILES["sites"]
)

LINKS = load_geojson(
    FILES["links"]
)

RECOMMENDED_HABITATIONS = load_geojson(
    FILES["recommended_habitations"]
)


# ---------------------------------------------------------
# HEALTH
# ---------------------------------------------------------

@app.get("/")
def root():

    return {
        "system": "RAKSHA-SETU",
        "status": "online",
        "module": (
            "Multi-Hazard Relocation "
            "Decision Support"
        ),
    }


@app.get("/api/health")
def health():

    return {
        "status": "healthy",
        "priority_habitations":
            len(DECISIONS["features"]),
        "recommended_sites":
            len(SITES["features"]),
        "relocation_links":
            len(LINKS["features"]),
    }


# ---------------------------------------------------------
# PRIORITY HABITATIONS
# ---------------------------------------------------------

@app.get("/api/priority-habitations")
def priority_habitations():

    return DECISIONS


# ---------------------------------------------------------
# RELOCATION SITES
# ---------------------------------------------------------

@app.get("/api/relocation-sites")
def relocation_sites():

    return SITES


# ---------------------------------------------------------
# RELOCATION LINKS
# ---------------------------------------------------------

@app.get("/api/relocation-links")
def relocation_links():

    return LINKS


# ---------------------------------------------------------
# SINGLE HABITATION
# ---------------------------------------------------------

@app.get("/api/habitations/{vlcode}")
def habitation(vlcode: str):

    for feature in DECISIONS["features"]:

        properties = feature.get(
            "properties",
            {}
        )

        if str(
            properties.get("vlcode")
        ) == str(vlcode):

            return feature

    raise HTTPException(
        status_code=404,
        detail="Habitation not found",
    )


# ---------------------------------------------------------
# RECOMMENDATIONS FOR HABITATION
# ---------------------------------------------------------

@app.get(
    "/api/habitations/{vlcode}/recommendations"
)
def habitation_recommendations(
    vlcode: str
):

    habitation_feature = None

    for feature in DECISIONS["features"]:

        properties = feature.get(
            "properties",
            {}
        )

        if str(
            properties.get("vlcode")
        ) == str(vlcode):

            habitation_feature = feature
            break


    if habitation_feature is None:

        raise HTTPException(
            status_code=404,
            detail="Habitation not found",
        )


    matching_sites = []

    for feature in SITES["features"]:

        properties = feature.get(
            "properties",
            {}
        )

        if str(
            properties.get("vlcode")
        ) == str(vlcode):

            matching_sites.append(
                feature
            )


    matching_sites.sort(
        key=lambda x: (
            x.get(
                "properties",
                {}
            ).get(
                "recommendation_rank",
                999
            )
        )
    )


    return {
        "habitation":
            habitation_feature,

        "decision_status":
            habitation_feature[
                "properties"
            ].get(
                "decision_status"
            ),

        "recommendations":
            matching_sites,

        "recommendation_count":
            len(matching_sites),
    }
@app.get("/api/summary")
def summary():

    decisions = [
        f.get("properties", {})
        for f in DECISIONS["features"]
    ]

    recommended = sum(
        1
        for d in decisions
        if d.get("decision_status")
        == "Recommended"
    )

    no_capacity = sum(
        1
        for d in decisions
        if d.get("decision_status")
        == "No Capacity-Feasible Site"
    )

    no_nearby = sum(
        1
        for d in decisions
        if d.get("decision_status")
        == "No Nearby Strict Site"
    )

    flood_dominant = sum(
        1
        for d in decisions
        if d.get("dominant_hazard")
        == "Flood-dominant"
    )

    landslide_dominant = sum(
        1
        for d in decisions
        if d.get("dominant_hazard")
        == "Landslide-dominant"
    )

    mixed = sum(
        1
        for d in decisions
        if d.get("dominant_hazard")
        == "Mixed"
    )

    return {
        "priority_habitations":
            len(decisions),

        "recommended":
            recommended,

        "no_capacity_feasible_site":
            no_capacity,

        "no_nearby_strict_site":
            no_nearby,

        "dominant_hazards": {
            "flood":
                flood_dominant,

            "landslide":
                landslide_dominant,

            "mixed":
                mixed,
        },

        "recommended_sites":
            len(SITES["features"]),

        "relocation_links":
            len(LINKS["features"]),
    }
