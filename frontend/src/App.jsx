import { useEffect, useState } from "react";
import axios from "axios";
import "./App.css";

import PriorityTable from "./components/PriorityTable";
import RaigadMap from "./components/RaigadMap";
import DynamicRiskTwin from "./components/DynamicRiskTwin";

const API = "http://127.0.0.1:8000";

function App() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Shared state between table and map
  const [selectedVillageCode, setSelectedVillageCode] =
    useState(null);

  useEffect(() => {
    axios
      .get(`${API}/api/summary`)
      .then((response) => {
        setSummary(response.data);
      })
      .catch((err) => {
        console.error(err);

        setError(
          "Could not load RAKSHA-SETU backend data."
        );
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  function handleTableVillageSelect(vlcode) {
    setSelectedVillageCode(String(vlcode));

    setTimeout(() => {
      document
        .getElementById("raigad-map-section")
        ?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
    }, 100);
  }

  if (loading) {
    return (
      <div className="page-center">
        <h2>Loading RAKSHA-SETU...</h2>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-center">
        <h2>{error}</h2>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>RAKSHA-SETU</h1>

          <p>
            Multi-Hazard Risk & Relocation Decision Support
          </p>
        </div>

        <div className="status">
          ● System Online
        </div>
      </header>

      <main className="content">
        <section className="hero">
          <h2>
            Raigad Multi-Hazard Command Dashboard
          </h2>

          <p>
            Prioritize high-risk habitations and identify
            safer relocation candidates using flood,
            landslide, vulnerability, exposure and
            accessibility analysis.
          </p>
        </section>

        <section className="cards">
          <div className="card">
            <span>Priority Habitations</span>

            <strong>
              {summary.priority_habitations}
            </strong>

            <small>
              Top high-risk habitations under analysis
            </small>
          </div>

          <div className="card success-card">
            <span>
              Relocation Recommendations
            </span>

            <strong>
              {summary.recommended}
            </strong>

            <small>
              Capacity-feasible strict sites identified
            </small>
          </div>

          <div className="card warning-card">
            <span>
              Capacity Constraints
            </span>

            <strong>
              {
                summary
                  .no_capacity_feasible_site
              }
            </strong>

            <small>
              Safe sites exist, but land capacity is
              insufficient
            </small>
          </div>

          <div className="card danger-card">
            <span>
              No Nearby Strict Site
            </span>

            <strong>
              {
                summary
                  .no_nearby_strict_site
              }
            </strong>

            <small>
              No strict candidate found within 25 km
            </small>
          </div>
        </section>

        <section className="panel-grid">
          <div className="panel">
            <h3>
              Dominant Hazard Distribution
            </h3>

            <div className="hazard-stat">
              <div>
                <span>
                  Flood-dominant
                </span>

                <small>
                  {
                    summary
                      .dominant_hazards
                      .flood
                  }{" "}
                  of{" "}
                  {
                    summary
                      .priority_habitations
                  }{" "}
                  habitations
                </small>
              </div>

              <strong>
                {
                  summary
                    .dominant_hazards
                    .flood
                }
              </strong>
            </div>

            <div className="hazard-stat">
              <div>
                <span>
                  Landslide-dominant
                </span>

                <small>
                  {
                    summary
                      .dominant_hazards
                      .landslide
                  }{" "}
                  of{" "}
                  {
                    summary
                      .priority_habitations
                  }{" "}
                  habitations
                </small>
              </div>

              <strong>
                {
                  summary
                    .dominant_hazards
                    .landslide
                }
              </strong>
            </div>

            <div className="hazard-stat">
              <div>
                <span>
                  Mixed hazard
                </span>

                <small>
                  {
                    summary
                      .dominant_hazards
                      .mixed
                  }{" "}
                  of{" "}
                  {
                    summary
                      .priority_habitations
                  }{" "}
                  habitations
                </small>
              </div>

              <strong>
                {
                  summary
                    .dominant_hazards
                    .mixed
                }
              </strong>
            </div>
          </div>

          <div className="panel">
            <h3>Relocation Engine</h3>

            <div className="hazard-stat">
              <div>
                <span>
                  Recommended Sites
                </span>

                <small>
                  Model-screened relocation candidates
                </small>
              </div>

              <strong>
                {summary.recommended_sites}
              </strong>
            </div>

            <div className="hazard-stat">
              <div>
                <span>
                  Relocation Links
                </span>

                <small>
                  Habitation-to-site decision connections
                </small>
              </div>

              <strong>
                {summary.relocation_links}
              </strong>
            </div>

            <div className="system-note">
              Candidate sites are model-generated
              decision-support recommendations. Final
              relocation decisions require engineering,
              legal, land-ownership and field verification.
            </div>
          </div>
        </section>

        <DynamicRiskTwin />

        <PriorityTable
          onVillageSelect={
            handleTableVillageSelect
          }
        />

        <div id="raigad-map-section">
          <RaigadMap
            externalVillageCode={
              selectedVillageCode
            }
          />
        </div>
      </main>
    </div>
  );
}

export default App;
