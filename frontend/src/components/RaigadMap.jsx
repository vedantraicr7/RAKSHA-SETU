import {
  useEffect,
  useState,
} from "react";

import {
  MapContainer,
  TileLayer,
  GeoJSON,
  useMap,
} from "react-leaflet";

import axios from "axios";
import L from "leaflet";

const API =
  "http://127.0.0.1:8000";

function FitBounds({ data }) {
  const map = useMap();

  useEffect(() => {
    if (
      !data?.features?.length
    ) {
      return;
    }

    const layer =
      L.geoJSON(data);

    const bounds =
      layer.getBounds();

    if (bounds.isValid()) {
      map.fitBounds(bounds, {
        padding: [30, 30],
        maxZoom: 11,
      });
    }
  }, [data, map]);

  return null;
}

function FitSelection({
  habitation,
  site,
}) {
  const map = useMap();

  useEffect(() => {
    if (!habitation?.geometry) {
      return;
    }

    const features = [
      habitation,
    ];

    if (site?.geometry) {
      features.push(site);
    }

    const collection = {
      type: "FeatureCollection",
      features,
    };

    const layer =
      L.geoJSON(collection);

    const bounds =
      layer.getBounds();

    if (bounds.isValid()) {
      map.flyToBounds(bounds, {
        padding: [80, 80],
        maxZoom: 12,
        duration: 1.2,
      });
    }
  }, [
    habitation,
    site,
    map,
  ]);

  return null;
}

function RaigadMap({
  externalVillageCode,
}) {
  const [
    habitations,
    setHabitations,
  ] = useState(null);

  const [
    sites,
    setSites,
  ] = useState(null);

  const [
    links,
    setLinks,
  ] = useState(null);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [error, setError] =
    useState("");

  const [
    selectedHabitation,
    setSelectedHabitation,
  ] = useState(null);

  const [
    selectedRecommendation,
    setSelectedRecommendation,
  ] = useState(null);

  const [
    selectionLoading,
    setSelectionLoading,
  ] = useState(false);

  const [
    searchTerm,
    setSearchTerm,
  ] = useState("");

  const [
    searchResults,
    setSearchResults,
  ] = useState([]);

  const [
    focusedFeature,
    setFocusedFeature,
  ] = useState(null);

  const [
    focusedSite,
    setFocusedSite,
  ] = useState(null);

  const [
    focusedLink,
    setFocusedLink,
  ] = useState(null);

  const [
    decisionFilter,
    setDecisionFilter,
  ] = useState("All");

  const [
    hazardFilter,
    setHazardFilter,
  ] = useState("All");

  useEffect(() => {
    async function loadMapData() {
      try {
        const [
          habRes,
          siteRes,
          linkRes,
        ] =
          await Promise.all([
            axios.get(
              `${API}/api/priority-habitations`
            ),

            axios.get(
              `${API}/api/relocation-sites`
            ),

            axios.get(
              `${API}/api/relocation-links`
            ),
          ]);

        setHabitations(
          habRes.data
        );

        setSites(
          siteRes.data
        );

        setLinks(
          linkRes.data
        );
      } catch (err) {
        console.error(err);

        setError(
          "Unable to load GIS data from backend."
        );
      } finally {
        setLoading(false);
      }
    }

    loadMapData();
  }, []);

  useEffect(() => {
    if (
      !habitations?.features
    ) {
      setSearchResults([]);
      return;
    }

    const term =
      searchTerm
        .trim()
        .toLowerCase();

    if (!term) {
      setSearchResults([]);
      return;
    }

    const results =
      habitations.features
        .filter(
          (feature) => {
            const p =
              feature.properties ||
              {};

            const village =
              String(
                p.village || ""
              ).toLowerCase();

            const subdistrict =
              String(
                p.subdistric ||
                  ""
              ).toLowerCase();

            const code =
              String(
                p.vlcode || ""
              ).toLowerCase();

            return (
              village.includes(
                term
              ) ||
              subdistrict.includes(
                term
              ) ||
              code.includes(
                term
              )
            );
          }
        )
        .slice(0, 8);

    setSearchResults(
      results
    );
  }, [
    searchTerm,
    habitations,
  ]);

  const filteredHabitations = {
    type: "FeatureCollection",

    features:
      habitations?.features?.filter(
        (feature) => {
          const p =
            feature.properties ||
            {};

          const decisionMatches =
            decisionFilter ===
              "All" ||
            p.decision_status ===
              decisionFilter;

          const hazardMatches =
            hazardFilter ===
              "All" ||
            p.dominant_hazard ===
              hazardFilter;

          return (
            decisionMatches &&
            hazardMatches
          );
        }
      ) || [],
  };

  async function selectHabitation(
    feature
  ) {
    if (!feature) return;

    const p =
      feature.properties || {};

    setSelectedHabitation(p);

    setFocusedFeature(
      feature
    );

    setSelectedRecommendation(
      null
    );

    setFocusedSite(null);
    setFocusedLink(null);

    setSearchTerm(
      p.village || ""
    );

    setSearchResults([]);

    setSelectionLoading(
      true
    );

    try {
      const response =
        await axios.get(
          `${API}/api/habitations/${p.vlcode}/recommendations`
        );

      const recommendations =
        response.data
          ?.recommendations ||
        [];

      if (
        recommendations.length >
        0
      ) {
        const bestRecommendation =
          recommendations[0];

        const recommendationProperties =
          bestRecommendation.properties ||
          {};

        setSelectedRecommendation(
          recommendationProperties
        );

        const patchId =
          recommendationProperties.patch_id;

        const matchingSite =
          sites?.features?.find(
            (site) =>
              String(
                site.properties
                  ?.patch_id
              ) ===
              String(patchId)
          );

        if (matchingSite) {
          setFocusedSite(
            matchingSite
          );
        }

        const matchingLink =
          links?.features?.find(
            (link) =>
              String(
                link.properties
                  ?.vlcode
              ) ===
                String(
                  p.vlcode
                ) &&
              String(
                link.properties
                  ?.patch_id
              ) ===
                String(
                  patchId
                )
          );

        if (matchingLink) {
          setFocusedLink(
            matchingLink
          );
        }
      }
    } catch (err) {
      console.error(
        "Unable to load recommendation:",
        err
      );
    } finally {
      setSelectionLoading(
        false
      );
    }
  }

  /*
   * TABLE -> MAP CONNECTION
   *
   * Whenever App.jsx sends a village code,
   * locate that habitation and run the exact
   * same selection logic used by map/search.
   */
  useEffect(() => {
    if (
      !externalVillageCode ||
      !habitations?.features ||
      !sites ||
      !links
    ) {
      return;
    }

    const feature =
      habitations.features.find(
        (item) =>
          String(
            item.properties
              ?.vlcode
          ) ===
          String(
            externalVillageCode
          )
      );

    if (feature) {
      // Make sure an externally selected
      // habitation remains visible.
      setDecisionFilter("All");
      setHazardFilter("All");

      selectHabitation(
        feature
      );
    }
  }, [
    externalVillageCode,
    habitations,
    sites,
    links,
  ]);

  const habitationStyle = (
    feature
  ) => {
    const status =
      feature?.properties
        ?.decision_status;

    if (
      status ===
      "Recommended"
    ) {
      return {
        color: "#ef4444",
        weight: 2,
        fillColor:
          "#ef4444",
        fillOpacity: 0.55,
      };
    }

    if (
      status ===
      "No Capacity-Feasible Site"
    ) {
      return {
        color: "#f59e0b",
        weight: 2,
        fillColor:
          "#f59e0b",
        fillOpacity: 0.55,
      };
    }

    return {
      color: "#a855f7",
      weight: 2,
      fillColor: "#a855f7",
      fillOpacity: 0.55,
    };
  };

  const focusedHabitationStyle =
    {
      color: "#ffffff",
      weight: 5,
      fillColor:
        "#ef4444",
      fillOpacity: 0.9,
    };

  const siteStyle = {
    color: "#22c55e",
    weight: 2,
    fillColor: "#22c55e",
    fillOpacity: 0.6,
  };

  const focusedSiteStyle = {
    color: "#ffffff",
    weight: 5,
    fillColor: "#22c55e",
    fillOpacity: 0.9,
  };

  const linkStyle = {
    color: "#38bdf8",
    weight: 1.5,
    opacity: 0.25,
    dashArray: "6 6",
  };

  const focusedLinkStyle = {
    color: "#00e5ff",
    weight: 5,
    opacity: 1,
    dashArray: "10 6",
  };

  const bindHabitationPopup =
    (feature, layer) => {
      const p =
        feature.properties ||
        {};

      layer.bindPopup(`
        <div>
          <strong>
            ${p.village || "Unknown"}
          </strong>
          <br/>

          Taluka:
          ${p.subdistric || "-"}
          <br/>

          Population:
          ${p.population ?? "-"}
          <br/>

          Priority Score:
          ${
            p.multihazard_priority_100 !=
            null
              ? Number(
                  p.multihazard_priority_100
                ).toFixed(2)
              : "-"
          }
          <br/>

          Hazard:
          ${p.dominant_hazard || "-"}
          <br/>

          Decision:
          ${p.decision_status || "-"}
        </div>
      `);

      layer.on(
        "click",
        () => {
          selectHabitation(
            feature
          );
        }
      );
    };

  const bindSitePopup =
    (feature, layer) => {
      const p =
        feature.properties ||
        {};

      layer.bindPopup(`
        <div>
          <strong>
            Relocation Candidate
          </strong>
          <br/>

          Patch ID:
          ${p.patch_id ?? "-"}
          <br/>

          Area:
          ${
            p.area_ha != null
              ? Number(
                  p.area_ha
                ).toFixed(2)
              : "-"
          } ha
          <br/>

          Flood Score:
          ${
            p.site_flood != null
              ? Number(
                  p.site_flood
                ).toFixed(2)
              : "-"
          }
          <br/>

          Landslide Score:
          ${
            p.site_landslide !=
            null
              ? Number(
                  p.site_landslide
                ).toFixed(2)
              : "-"
          }
        </div>
      `);
    };

  if (loading) {
    return (
      <div className="map-message">
        Loading Raigad GIS
        layers...
      </div>
    );
  }

  if (error) {
    return (
      <div className="map-message map-error">
        {error}
      </div>
    );
  }

  return (
    <section className="map-section">
      <div className="map-heading">
        <div>
          <h2>
            Raigad Relocation
            Decision Map
          </h2>

          <p>
            Priority habitations,
            recommended relocation
            sites and decision-support
            connections.
          </p>
        </div>

        <div className="map-legend">
          <span>
            🔴 Recommended
          </span>

          <span>
            🟠 Capacity
            constraint
          </span>

          <span>
            🟣 No nearby site
          </span>

          <span>
            🟢 Relocation site
          </span>

          <span>
            🔵 Relocation link
          </span>
        </div>
      </div>

      <div className="map-filters">
        <button
          className={
            decisionFilter ===
            "All"
              ? "filter-btn active"
              : "filter-btn"
          }
          onClick={() =>
            setDecisionFilter(
              "All"
            )
          }
        >
          All
        </button>

        <button
          className={
            decisionFilter ===
            "Recommended"
              ? "filter-btn active"
              : "filter-btn"
          }
          onClick={() =>
            setDecisionFilter(
              "Recommended"
            )
          }
        >
          Recommended
        </button>

        <button
          className={
            decisionFilter ===
            "No Capacity-Feasible Site"
              ? "filter-btn active"
              : "filter-btn"
          }
          onClick={() =>
            setDecisionFilter(
              "No Capacity-Feasible Site"
            )
          }
        >
          Capacity Constraint
        </button>

        <button
          className={
            decisionFilter ===
            "No Nearby Strict Site"
              ? "filter-btn active"
              : "filter-btn"
          }
          onClick={() =>
            setDecisionFilter(
              "No Nearby Strict Site"
            )
          }
        >
          No Nearby Site
        </button>
      </div>

      <div className="map-filters hazard-filters">
        <button
          className={
            hazardFilter ===
            "All"
              ? "filter-btn active"
              : "filter-btn"
          }
          onClick={() =>
            setHazardFilter(
              "All"
            )
          }
        >
          All Hazards
        </button>

        <button
          className={
            hazardFilter ===
            "Flood-dominant"
              ? "filter-btn active"
              : "filter-btn"
          }
          onClick={() =>
            setHazardFilter(
              "Flood-dominant"
            )
          }
        >
          Flood-dominant
        </button>

        <button
          className={
            hazardFilter ===
            "Landslide-dominant"
              ? "filter-btn active"
              : "filter-btn"
          }
          onClick={() =>
            setHazardFilter(
              "Landslide-dominant"
            )
          }
        >
          Landslide-dominant
        </button>

        <button
          className={
            hazardFilter ===
            "Mixed"
              ? "filter-btn active"
              : "filter-btn"
          }
          onClick={() =>
            setHazardFilter(
              "Mixed"
            )
          }
        >
          Mixed
        </button>
      </div>

      <div className="habitation-search">
        <div className="search-label">
          Search Habitation
        </div>

        <input
          type="text"
          value={searchTerm}
          onChange={(e) =>
            setSearchTerm(
              e.target.value
            )
          }
          placeholder="Search village, taluka or village code..."
          className="search-input"
        />

        {searchResults.length >
          0 && (
          <div className="search-results">
            {searchResults.map(
              (feature) => {
                const p =
                  feature.properties ||
                  {};

                return (
                  <button
                    key={
                      p.vlcode
                    }
                    className="search-result-item"
                    onClick={() =>
                      selectHabitation(
                        feature
                      )
                    }
                  >
                    <strong>
                      {
                        p.village
                      }
                    </strong>

                    <span>
                      {
                        p.subdistric
                      }
                      {" · "}
                      {
                        p.vlcode
                      }
                    </span>
                  </button>
                );
              }
            )}
          </div>
        )}
      </div>

      <div className="map-wrapper">
        <MapContainer
          center={[
            18.45,
            73.15,
          ]}
          zoom={9}
          scrollWheelZoom={
            true
          }
          className="raigad-map"
        >
          <FitBounds
            data={habitations}
          />

          <FitSelection
            habitation={
              focusedFeature
            }
            site={
              focusedSite
            }
          />

          <TileLayer
            attribution="&copy; OpenStreetMap contributors"
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {links && (
            <GeoJSON
              data={links}
              style={
                linkStyle
              }
            />
          )}

          {focusedLink && (
            <GeoJSON
              key={`focused-link-${focusedLink.properties?.vlcode}-${focusedLink.properties?.patch_id}`}
              data={
                focusedLink
              }
              style={
                focusedLinkStyle
              }
            />
          )}

          {habitations && (
            <GeoJSON
              key={`${decisionFilter}-${hazardFilter}`}
              data={
                filteredHabitations
              }
              style={
                habitationStyle
              }
              onEachFeature={
                bindHabitationPopup
              }
            />
          )}

          {focusedFeature && (
            <GeoJSON
              key={`focused-habitation-${focusedFeature.properties?.vlcode}`}
              data={
                focusedFeature
              }
              style={
                focusedHabitationStyle
              }
            />
          )}

          {sites && (
            <GeoJSON
              data={sites}
              style={
                siteStyle
              }
              onEachFeature={
                bindSitePopup
              }
            />
          )}

          {focusedSite && (
            <GeoJSON
              key={`focused-site-${focusedSite.properties?.patch_id}`}
              data={
                focusedSite
              }
              style={
                focusedSiteStyle
              }
            />
          )}
        </MapContainer>
      </div>

      {selectedHabitation && (
        <div className="decision-panel">
          <div className="decision-panel-header">
            <div>
              <h3>
                {
                  selectedHabitation
                    .village
                }
              </h3>

              <p>
                {
                  selectedHabitation
                    .subdistric
                }
                {
                  " · Village Code "
                }
                {
                  selectedHabitation
                    .vlcode
                }
              </p>
            </div>

            <button
              className="close-panel"
              onClick={() => {
                setSelectedHabitation(
                  null
                );

                setSelectedRecommendation(
                  null
                );

                setFocusedFeature(
                  null
                );

                setFocusedSite(
                  null
                );

                setFocusedLink(
                  null
                );
              }}
            >
              ×
            </button>
          </div>

          <div className="decision-grid">
            <div>
              <span>
                Population
              </span>

              <strong>
                {Number(
                  selectedHabitation
                    .population
                ).toLocaleString()}
              </strong>
            </div>

            <div>
              <span>
                Priority Score
              </span>

              <strong>
                {Number(
                  selectedHabitation
                    .multihazard_priority_100
                ).toFixed(1)}
              </strong>
            </div>

            <div>
              <span>
                Dominant Hazard
              </span>

              <strong>
                {
                  selectedHabitation
                    .dominant_hazard
                }
              </strong>
            </div>

            <div>
              <span>
                Decision
              </span>

              <strong>
                {
                  selectedHabitation
                    .decision_status
                }
              </strong>
            </div>
          </div>

          <div className="decision-reason">
            {
              selectedHabitation
                .decision_reason
            }
          </div>

          {selectionLoading && (
            <p>
              Loading relocation
              recommendation...
            </p>
          )}

          {!selectionLoading &&
            selectedRecommendation && (
              <>
                <h4>
                  Recommended
                  Relocation Site
                </h4>

                <div className="decision-grid">
                  <div>
                    <span>
                      Patch ID
                    </span>

                    <strong>
                      {
                        selectedRecommendation
                          .patch_id
                      }
                    </strong>
                  </div>

                  <div>
                    <span>
                      Available Area
                    </span>

                    <strong>
                      {Number(
                        selectedRecommendation
                          .area_ha
                      ).toFixed(
                        2
                      )}{" "}
                      ha
                    </strong>
                  </div>

                  <div>
                    <span>
                      Required Area
                    </span>

                    <strong>
                      {Number(
                        selectedRecommendation
                          .required_area_ha
                      ).toFixed(
                        2
                      )}{" "}
                      ha
                    </strong>
                  </div>

                  <div>
                    <span>
                      Capacity Ratio
                    </span>

                    <strong>
                      {Number(
                        selectedRecommendation
                          .capacity_ratio
                      ).toFixed(
                        2
                      )}
                      ×
                    </strong>
                  </div>

                  <div>
                    <span>
                      Distance
                    </span>

                    <strong>
                      {Number(
                        selectedRecommendation
                          .distance_km
                      ).toFixed(
                        2
                      )}{" "}
                      km
                    </strong>
                  </div>

                  <div>
                    <span>
                      Flood Score
                    </span>

                    <strong>
                      {Number(
                        selectedRecommendation
                          .site_flood
                      ).toFixed(
                        1
                      )}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Landslide Score
                    </span>

                    <strong>
                      {Number(
                        selectedRecommendation
                          .site_landslide
                      ).toFixed(
                        1
                      )}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Slope
                    </span>

                    <strong>
                      {Number(
                        selectedRecommendation
                          .site_slope_deg
                      ).toFixed(
                        1
                      )}
                      °
                    </strong>
                  </div>

                  <div>
                    <span>
                      Road Distance
                    </span>

                    <strong>
                      {Number(
                        selectedRecommendation
                          .site_road_dist_m
                      ).toFixed(
                        0
                      )}{" "}
                      m
                    </strong>
                  </div>

                  <div>
                    <span>
                      Feasibility Score
                    </span>

                    <strong>
                      {Number(
                        selectedRecommendation
                          .final_feasibility_score
                      ).toFixed(
                        1
                      )}
                    </strong>
                  </div>
                </div>
              </>
            )}

          {!selectionLoading &&
            !selectedRecommendation &&
            selectedHabitation
              .decision_status !==
              "Recommended" && (
              <div className="no-site-message">
                No relocation site is
                recommended under the
                current safety and
                capacity constraints.
              </div>
            )}
        </div>
      )}
    </section>
  );
}

export default RaigadMap;
