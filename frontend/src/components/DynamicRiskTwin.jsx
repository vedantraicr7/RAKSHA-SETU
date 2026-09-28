import {
  useEffect,
  useMemo,
  useState,
} from "react";

import axios from "axios";
import L from "leaflet";

import {
  CircleMarker,
  MapContainer,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";


const API =
  "http://127.0.0.1:8000";


const SCENARIOS = [
  {
    value: 0,
    label: "Baseline",
  },
  {
    value: 0.25,
    label: "Elevated",
  },
  {
    value: 0.5,
    label: "Severe",
  },
  {
    value: 0.75,
    label: "Very Severe",
  },
  {
    value: 1,
    label: "Extreme",
  },
];


const numberFormatter =
  new Intl.NumberFormat("en-IN");


function formatNumber(value) {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  return numberFormatter.format(
    Math.round(value)
  );
}


function formatScore(value) {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  return Number(value).toFixed(2);
}


function zoneColor(zone) {
  switch (zone) {
    case "RED":
      return "#dc2626";

    case "ORANGE":
      return "#f97316";

    case "YELLOW":
      return "#eab308";

    case "GREEN":
      return "#16a34a";

    default:
      return "#64748b";
  }
}


function FitDynamicBounds({
  features,
}) {
  const map = useMap();

  useEffect(() => {
    if (!features?.length) {
      return;
    }

    const coordinates =
      features
        .map((feature) => {
          const coordinates =
            feature?.geometry?.coordinates;

          if (
            !Array.isArray(coordinates) ||
            coordinates.length < 2
          ) {
            return null;
          }

          const [
            longitude,
            latitude,
          ] = coordinates;

          if (
            !Number.isFinite(longitude) ||
            !Number.isFinite(latitude)
          ) {
            return null;
          }

          return [
            latitude,
            longitude,
          ];
        })
        .filter(Boolean);

    if (!coordinates.length) {
      return;
    }

    const bounds =
      L.latLngBounds(
        coordinates
      );

    if (bounds.isValid()) {
      map.fitBounds(
        bounds,
        {
          padding: [25, 25],
          maxZoom: 10,
        }
      );
    }
  }, [
    features,
    map,
  ]);

  return null;
}


function DynamicRiskTwin() {
  const [
    trigger,
    setTrigger,
  ] = useState(0);

  const [
    data,
    setData,
  ] = useState(null);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState("");

  const [
    mapFilter,
    setMapFilter,
  ] = useState("All");


  useEffect(() => {
    let cancelled = false;

    const timer =
      setTimeout(
        async () => {
          try {
            setLoading(true);
            setError("");

            const response =
              await axios.get(
                `${API}/api/dynamic-risk`,
                {
                  params: {
                    rainfall_trigger:
                      trigger,
                  },
                }
              );

            if (!cancelled) {
              setData(
                response.data
              );
            }
          } catch (err) {
            console.error(err);

            if (!cancelled) {
              setError(
                "Dynamic risk simulation could not be loaded."
              );
            }
          } finally {
            if (!cancelled) {
              setLoading(false);
            }
          }
        },
        200
      );

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [
    trigger,
  ]);


  const summary =
    data?.summary;


  const allFeatures =
    useMemo(
      () =>
        data?.geojson?.features
        ?? [],
      [
        data,
      ]
    );


  const visibleFeatures =
    useMemo(() => {
      if (
        mapFilter === "RED"
      ) {
        return allFeatures.filter(
          (feature) =>
            feature
              ?.properties
              ?.dynamic_zone
            ===
            "RED"
        );
      }

      if (
        mapFilter
        ===
        "Newly Red"
      ) {
        return allFeatures.filter(
          (feature) =>
            feature
              ?.properties
              ?.newly_red
            ===
            true
        );
      }

      if (
        mapFilter
        ===
        "Immediate"
      ) {
        return allFeatures.filter(
          (feature) =>
            feature
              ?.properties
              ?.relocation_urgency
            ===
            "Immediate"
        );
      }

      return allFeatures;
    }, [
      allFeatures,
      mapFilter,
    ]);


  return (
    <section
      className="dynamic-twin"
      id="dynamic-risk-simulator"
    >
      <div className="dynamic-heading">
        <div>
          <span className="dynamic-eyebrow">
            DIGITAL TWIN PROTOTYPE
          </span>

          <h2>
            Dynamic Multi-Hazard
            Scenario Simulator
          </h2>

          <p>
            Simulate changing rainfall
            conditions and observe how
            habitation risk, Red Zones,
            exposed population and
            planning urgency change
            across Raigad.
          </p>
        </div>

        <div className="dynamic-engine-status">
          <span />
          Dynamic Engine Online
        </div>
      </div>


      <div className="scenario-controller">
        <div className="scenario-title-row">
          <div>
            <span>
              Rainfall Scenario Trigger
            </span>

            <strong>
              {summary?.scenario_name
                ?? "Loading..."}
            </strong>
          </div>

          <div className="trigger-value">
            {Number(
              trigger
            ).toFixed(2)}
          </div>
        </div>


        <div className="scenario-buttons">
          {SCENARIOS.map(
            (scenario) => (
              <button
                type="button"
                key={
                  scenario.value
                }
                className={
                  trigger
                    ===
                  scenario.value
                    ?
                    "scenario-button active"
                    :
                    "scenario-button"
                }
                onClick={() =>
                  setTrigger(
                    scenario.value
                  )
                }
              >
                {
                  scenario.label
                }
              </button>
            )
          )}
        </div>


        <input
          className="scenario-slider"
          type="range"
          min="0"
          max="1"
          step="0.25"
          value={trigger}
          onChange={
            (event) =>
              setTrigger(
                Number(
                  event.target.value
                )
              )
          }
        />


        <div className="slider-labels">
          <span>
            Baseline
          </span>

          <span>
            Extreme
          </span>
        </div>


        <div className="prototype-note">
          Scenario intensity is a
          normalized prototype trigger.
          It is not rainfall percentage
          and is not an official
          meteorological warning level.
        </div>
      </div>


      {error && (
        <div className="dynamic-error">
          {error}
        </div>
      )}


      <div className="dynamic-kpis">
        <div className="dynamic-kpi red-kpi">
          <span>
            Red-Zone Habitations
          </span>

          <strong>
            {
              loading
                ?
                "..."
                :
                formatNumber(
                  summary
                    ?.red_habitations
                )
            }
          </strong>

          <small>
            Current scenario
          </small>
        </div>


        <div className="dynamic-kpi">
          <span>
            Population in Red Zones
          </span>

          <strong>
            {
              loading
                ?
                "..."
                :
                formatNumber(
                  summary
                    ?.red_population
                )
            }
          </strong>

          <small>
            Population exposed
          </small>
        </div>


        <div className="dynamic-kpi new-red-kpi">
          <span>
            Newly Red Habitations
          </span>

          <strong>
            {
              loading
                ?
                "..."
                :
                formatNumber(
                  summary
                    ?.newly_red_habitations
                )
            }
          </strong>

          <small>
            Newly crossed Red threshold
          </small>
        </div>


        <div className="dynamic-kpi">
          <span>
            Newly Exposed Population
          </span>

          <strong>
            {
              loading
                ?
                "..."
                :
                formatNumber(
                  summary
                    ?.newly_red_population
                )
            }
          </strong>

          <small>
            Newly entering Red Zone
          </small>
        </div>


        <div className="dynamic-kpi immediate-kpi">
          <span>
            Immediate Priority
          </span>

          <strong>
            {
              loading
                ?
                "..."
                :
                formatNumber(
                  summary
                    ?.immediate_habitations
                )
            }
          </strong>

          <small>
            Planning / review priority
          </small>
        </div>


        <div className="dynamic-kpi">
          <span>
            Immediate-Priority Population
          </span>

          <strong>
            {
              loading
                ?
                "..."
                :
                formatNumber(
                  summary
                    ?.immediate_population
                )
            }
          </strong>

          <small>
            Population requiring priority review
          </small>
        </div>
      </div>


      <div className="dynamic-map-panel">
        <div className="dynamic-map-header">
          <div>
            <h3>
              Dynamic Habitation
              Risk Map
            </h3>

            <p>
              {
                formatNumber(
                  visibleFeatures.length
                )
              }{" "}
              habitation markers shown
            </p>
          </div>


          <div className="dynamic-map-filters">
            {[
              "All",
              "RED",
              "Newly Red",
              "Immediate",
            ].map(
              (filter) => (
                <button
                  type="button"
                  key={filter}
                  className={
                    mapFilter
                      ===
                    filter
                      ?
                      "dynamic-filter active"
                      :
                      "dynamic-filter"
                  }
                  onClick={() =>
                    setMapFilter(
                      filter
                    )
                  }
                >
                  {filter}
                </button>
              )
            )}
          </div>
        </div>


        <div className="dynamic-map-wrapper">
          {loading && (
            <div className="dynamic-map-loading">
              Recalculating district
              risk scenario...
            </div>
          )}


          <MapContainer
            center={[
              18.5,
              73.2,
            ]}
            zoom={9}
            scrollWheelZoom
            className="dynamic-map"
          >
            <TileLayer
              attribution={
                '&copy; OpenStreetMap contributors'
              }
              url={
                "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              }
            />


            <FitDynamicBounds
              features={
                visibleFeatures
              }
            />


            {visibleFeatures.map(
              (
                feature,
                index
              ) => {
                const p =
                  feature
                    .properties
                  ?? {};

                const coordinates =
                  feature
                    ?.geometry
                    ?.coordinates;

                if (
                  !Array.isArray(
                    coordinates
                  )
                  ||
                  coordinates.length
                  <
                  2
                ) {
                  return null;
                }

                const [
                  longitude,
                  latitude,
                ] =
                  coordinates;

                const color =
                  zoneColor(
                    p.dynamic_zone
                  );

                const radius =
                  p.newly_red
                    ?
                    7
                    :
                    p.dynamic_zone
                      ===
                      "RED"
                      ?
                      5
                      :
                      4;

                return (
                  <CircleMarker
                    key={
                      p.vlcode
                      ??
                      index
                    }
                    center={[
                      latitude,
                      longitude,
                    ]}
                    radius={
                      radius
                    }
                    pathOptions={{
                      color:
                        p.newly_red
                          ?
                          "#ffffff"
                          :
                          color,

                      weight:
                        p.newly_red
                          ?
                          3
                          :
                          1,

                      fillColor:
                        color,

                      fillOpacity:
                        p.dynamic_zone
                          ===
                          "Insufficient Data"
                          ?
                          0.35
                          :
                          0.78,
                    }}
                  >
                    <Popup>
                      <div className="dynamic-popup">
                        <strong>
                          {
                            p.village
                          }
                        </strong>

                        <span>
                          {
                            p.subdistric
                          }
                        </span>

                        <hr />

                        <div>
                          Population:
                          {" "}
                          <b>
                            {
                              formatNumber(
                                p.population
                              )
                            }
                          </b>
                        </div>

                        <div>
                          Baseline priority:
                          {" "}
                          <b>
                            {
                              formatScore(
                                p.baseline_priority
                              )
                            }
                          </b>
                        </div>

                        <div>
                          Dynamic priority:
                          {" "}
                          <b>
                            {
                              formatScore(
                                p.dynamic_priority
                              )
                            }
                          </b>
                        </div>

                        <div>
                          Priority change:
                          {" "}
                          <b>
                            {
                              formatScore(
                                p.priority_change
                              )
                            }
                          </b>
                        </div>

                        <div>
                          Zone:
                          {" "}
                          <b>
                            {
                              p.dynamic_zone
                            }
                          </b>
                        </div>

                        <div>
                          Planning urgency:
                          {" "}
                          <b>
                            {
                              p.relocation_urgency
                            }
                          </b>
                        </div>

                        <div>
                          Hazard driver:
                          {" "}
                          <b>
                            {
                              p.dominant_hazard
                            }
                          </b>
                        </div>

                        {
                          p.newly_red
                          &&
                          (
                            <div className="new-red-popup">
                              Newly entered
                              Red Zone
                            </div>
                          )
                        }
                      </div>
                    </Popup>
                  </CircleMarker>
                );
              }
            )}
          </MapContainer>


          <div className="dynamic-legend">
            <div>
              <i className="legend-green" />
              GREEN
            </div>

            <div>
              <i className="legend-yellow" />
              YELLOW
            </div>

            <div>
              <i className="legend-orange" />
              ORANGE
            </div>

            <div>
              <i className="legend-red" />
              RED
            </div>

            <div>
              <i className="legend-new-red" />
              Newly Red
            </div>
          </div>
        </div>


        <div className="dynamic-map-note">
          Markers represent habitation-level
          dynamic risk classifications, not
          continuous hazard polygons. “Immediate”
          indicates immediate planning/review
          priority and does not itself constitute
          an evacuation order.
        </div>
      </div>
    </section>
  );
}


export default DynamicRiskTwin;
