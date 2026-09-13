CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS hazard;
CREATE SCHEMA IF NOT EXISTS infrastructure;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS metadata;

CREATE TABLE IF NOT EXISTS metadata.datasets (

    dataset_id SERIAL PRIMARY KEY,

    name TEXT NOT NULL,
    provider TEXT NOT NULL,

    source_url TEXT,

    reference_year INTEGER,
    download_date DATE,

    format TEXT,
    spatial_resolution TEXT,
    crs TEXT,

    authority_level TEXT,

    freshness_score NUMERIC,
    completeness_score NUMERIC,
    quality_score NUMERIC,

    license TEXT,

    limitations TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);

CREATE TABLE IF NOT EXISTS core.habitations (

    habitation_id BIGSERIAL PRIMARY KEY,

    census_code TEXT,

    name TEXT NOT NULL,

    district TEXT,
    subdistrict TEXT,
    state TEXT,

    population INTEGER,
    households INTEGER,

    area_sqkm NUMERIC,

    geometry GEOMETRY(MULTIPOLYGON, 4326),

    source_dataset_id INTEGER
        REFERENCES metadata.datasets(dataset_id),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);

CREATE INDEX IF NOT EXISTS
idx_habitations_geometry

ON core.habitations
USING GIST(geometry);

CREATE TABLE IF NOT EXISTS hazard.habitation_risk (

    risk_id BIGSERIAL PRIMARY KEY,

    habitation_id BIGINT
        REFERENCES core.habitations(habitation_id),

    landslide_score NUMERIC,
    flood_score NUMERIC,
    rainfall_score NUMERIC,

    compound_hazard_score NUMERIC,

    risk_category TEXT,

    confidence NUMERIC,

    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);

CREATE TABLE IF NOT EXISTS analytics.candidate_sites (

    site_id BIGSERIAL PRIMARY KEY,

    name TEXT,

    geometry GEOMETRY(POLYGON, 4326),

    area_sqkm NUMERIC,

    landslide_risk NUMERIC,
    flood_risk NUMERIC,

    road_access_score NUMERIC,
    health_access_score NUMERIC,
    water_access_score NUMERIC,

    suitability_score NUMERIC,

    status TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);


