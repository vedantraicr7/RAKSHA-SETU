import {
  useEffect,
  useMemo,
  useState,
} from "react";
import axios from "axios";

const API =
  "http://127.0.0.1:8000";

function PriorityTable({
  onVillageSelect,
}) {
  const [features, setFeatures] =
    useState([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [search, setSearch] =
    useState("");

  useEffect(() => {
    axios
      .get(
        `${API}/api/priority-habitations`
      )
      .then((response) => {
        setFeatures(
          response.data?.features || []
        );
      })
      .catch((err) => {
        console.error(err);

        setError(
          "Unable to load priority habitation table."
        );
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const rows =
    useMemo(() => {
      const term =
        search
          .trim()
          .toLowerCase();

      return features
        .map(
          (feature) =>
            feature.properties || {}
        )
        .filter((row) => {
          if (!term) {
            return true;
          }

          return (
            String(
              row.village || ""
            )
              .toLowerCase()
              .includes(term) ||
            String(
              row.subdistric || ""
            )
              .toLowerCase()
              .includes(term) ||
            String(
              row.vlcode || ""
            )
              .toLowerCase()
              .includes(term)
          );
        })
        .sort(
          (a, b) =>
            Number(
              b.multihazard_priority_100 ||
                0
            ) -
            Number(
              a.multihazard_priority_100 ||
                0
            )
        );
    }, [features, search]);

  if (loading) {
    return (
      <section className="priority-table-section">
        <h2>
          Priority Habitations
        </h2>

        <p>
          Loading priority table...
        </p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="priority-table-section">
        <h2>
          Priority Habitations
        </h2>

        <p className="table-error">
          {error}
        </p>
      </section>
    );
  }

  return (
    <section className="priority-table-section">
      <div className="priority-table-header">
        <div>
          <h2>
            Top Priority Habitations
          </h2>

          <p>
            Ranked high-risk habitations
            with relocation decision status.
            Click a row to inspect it on
            the GIS map.
          </p>
        </div>

        <input
          type="text"
          className="table-search"
          value={search}
          onChange={(e) =>
            setSearch(
              e.target.value
            )
          }
          placeholder="Search village, taluka or code..."
        />
      </div>

      <div className="table-wrapper">
        <table className="priority-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Village</th>
              <th>Taluka</th>
              <th>Population</th>
              <th>Priority</th>
              <th>
                Dominant Hazard
              </th>
              <th>Decision</th>
              <th>Patch</th>
              <th>Distance</th>
              <th>Feasibility</th>
            </tr>
          </thead>

          <tbody>
            {rows.map(
              (row, index) => (
                <tr
                  key={
                    row.vlcode
                  }
                  className="clickable-priority-row"
                  onClick={() =>
                    onVillageSelect?.(
                      row.vlcode
                    )
                  }
                  title={`Open ${row.village} on map`}
                >
                  <td>
                    {index + 1}
                  </td>

                  <td>
                    <strong>
                      {
                        row.village
                      }
                    </strong>

                    <div className="table-subtext">
                      {
                        row.vlcode
                      }
                    </div>
                  </td>

                  <td>
                    {
                      row.subdistric
                    }
                  </td>

                  <td>
                    {Number(
                      row.population ||
                        0
                    ).toLocaleString()}
                  </td>

                  <td>
                    <strong>
                      {Number(
                        row.multihazard_priority_100 ||
                          0
                      ).toFixed(1)}
                    </strong>
                  </td>

                  <td>
                    {
                      row.dominant_hazard
                    }
                  </td>

                  <td>
                    <span
                      className={`decision-badge ${
                        row.decision_status ===
                        "Recommended"
                          ? "decision-good"
                          : row.decision_status ===
                            "No Capacity-Feasible Site"
                          ? "decision-warning"
                          : "decision-bad"
                      }`}
                    >
                      {
                        row.decision_status
                      }
                    </span>
                  </td>

                  <td>
                    {row.patch_id !=
                    null
                      ? Number(
                          row.patch_id
                        ).toFixed(
                          0
                        )
                      : "-"}
                  </td>

                  <td>
                    {row.distance_km !=
                    null
                      ? `${Number(
                          row.distance_km
                        ).toFixed(
                          1
                        )} km`
                      : "-"}
                  </td>

                  <td>
                    {row.final_feasibility_score !=
                    null
                      ? Number(
                          row.final_feasibility_score
                        ).toFixed(
                          1
                        )
                      : "-"}
                  </td>
                </tr>
              )
            )}
          </tbody>
        </table>
      </div>

      <div className="table-footer">
        Showing {rows.length} of{" "}
        {features.length} priority
        habitations
      </div>
    </section>
  );
}

export default PriorityTable;
