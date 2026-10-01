import React, { useState } from "react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Polygon,
  Popup,
  useMap,
} from "react-leaflet";
import RiskBadge, { RISK_LEVELS, getRiskLevelConfig } from "./RiskBadge";
import RiskLegend from "./RiskLegend";
import { formatDetectedDate } from "../utils/formatters";
import "./RiskMapView.css";

export { formatDetectedDate };

/**
 * MVP Region Coordinates & Zoom Level (Configurable)
 * Center: Florida Gulf Coast / West Coast Marine Monitoring Corridor
 */
export const MVP_MAP_CENTER = [27.5, -83.2];
export const MVP_MAP_ZOOM = 7;

/**
 * Map Recenter Controller Component
 */
function MapRecenter({ center, zoom }) {
  const map = useMap();
  React.useEffect(() => {
    if (center) {
      map.setView(center, zoom || MVP_MAP_ZOOM, { animate: true });
    }
  }, [center, zoom, map]);
  return null;
}

/**
 * Map View Component for OceanWatch HAB Detection Zones
 *
 * @param {Object} props.geoData - GeoJSON FeatureCollection
 * @param {Array<number>} [props.center=MVP_MAP_CENTER] - [lat, lon]
 * @param {number} [props.zoom=MVP_MAP_ZOOM]
 * @param {Function} [props.onSelectZone] - Callback when zone marker is clicked
 * @param {string} [props.legendPosition="bottom-left"]
 * @param {string} [props.className]
 */
export default function RiskMapView({
  geoData,
  center = MVP_MAP_CENTER,
  zoom = MVP_MAP_ZOOM,
  onSelectZone,
  legendPosition = "bottom-left",
  className = "",
}) {
  const [mapTileStyle, setMapTileStyle] = useState("dark"); // "dark" | "osm" | "ocean"

  const features = geoData?.features || [];

  const tileUrls = {
    dark: {
      url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
      maxZoom: 19,
    },
    osm: {
      url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    },
    ocean: {
      url: "https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}",
      attribution:
        "Tiles &copy; Esri &mdash; Sources: GEBCO, NOAA, CHS, OSU, UNH, CSUMB, National Geographic, DeLorme, NAVTEQ, and Esri",
      maxZoom: 13,
    },
  };

  const currentTile = tileUrls[mapTileStyle] || tileUrls.dark;

  return (
    <div className={`risk-map-wrapper ${className}`}>
      {/* Tile Layer & View Controls */}
      <div className="risk-map-controls-bar">
        <button
          type="button"
          className={`risk-map-control-btn ${mapTileStyle === "dark" ? "risk-map-control-btn--active" : ""}`}
          onClick={() => setMapTileStyle("dark")}
          title="Switch to Dark Basemap"
        >
          🌑 Dark
        </button>
        <button
          type="button"
          className={`risk-map-control-btn ${mapTileStyle === "ocean" ? "risk-map-control-btn--active" : ""}`}
          onClick={() => setMapTileStyle("ocean")}
          title="Switch to Bathymetric Ocean Basemap"
        >
          🌊 Ocean
        </button>
        <button
          type="button"
          className={`risk-map-control-btn ${mapTileStyle === "osm" ? "risk-map-control-btn--active" : ""}`}
          onClick={() => setMapTileStyle("osm")}
          title="Switch to Standard Street / Coastal Basemap"
        >
          🗺️ Standard
        </button>
      </div>

      <MapContainer
        center={center}
        zoom={zoom}
        className="risk-map-container"
        scrollWheelZoom={true}
      >
        <TileLayer
          key={mapTileStyle}
          attribution={currentTile.attribution}
          url={currentTile.url}
          maxZoom={currentTile.maxZoom}
        />

        <MapRecenter center={center} zoom={zoom} />

        {/* Render HAB Detection Zones */}
        {features.map((feature, idx) => {
          const props = feature.properties || {};
          const geom = feature.geometry;
          if (!geom || !geom.coordinates) return null;

          const riskConfig = getRiskLevelConfig(props.risk_level || props.risk_score);
          const score = typeof props.risk_score === "number" ? props.risk_score : 50;

          // Scaling calculations:
          // Radius scales from 10 to 22 based on risk score (0-100)
          const radius = Math.round(10 + (Math.min(100, Math.max(0, score)) / 100) * 12);
          // Opacity scales from 0.55 to 0.85
          const fillOpacity = (0.55 + (Math.min(100, Math.max(0, score)) / 100) * 0.35).toFixed(2);

          const locationName = props.location_name || `Zone #${idx + 1}`;
          const chlorophyllA =
            props.chlorophyll_a !== undefined && props.chlorophyll_a !== null
              ? `${Number(props.chlorophyll_a).toFixed(1)} mg/m³`
              : "N/A";
          const sstAnomaly =
            props.sst_anomaly !== undefined && props.sst_anomaly !== null
              ? `${Number(props.sst_anomaly) > 0 ? "+" : ""}${Number(props.sst_anomaly).toFixed(2)} °C`
              : "N/A";
          const detectedDate = formatDetectedDate(props.detected_at || props.date);

          // Handle Point Geometries (default standard for sensor / grid centerpoints)
          if (geom.type === "Point") {
            const [lon, lat] = geom.coordinates;
            if (typeof lat !== "number" || typeof lon !== "number") return null;

            return (
              <React.Fragment key={`zone-point-${idx}`}>
                {/* For critical or high zones, add an outer halo circle */}
                {(props.risk_level === "CRITICAL" || score > 80) && (
                  <CircleMarker
                    center={[lat, lon]}
                    radius={radius + 8}
                    pathOptions={{
                      color: riskConfig.color,
                      fillColor: riskConfig.color,
                      fillOpacity: 0.18,
                      weight: 1,
                      dashArray: "3, 6",
                    }}
                    interactive={false}
                  />
                )}

                <CircleMarker
                  center={[lat, lon]}
                  radius={radius}
                  pathOptions={{
                    color: riskConfig.color,
                    fillColor: riskConfig.color,
                    fillOpacity: parseFloat(fillOpacity),
                    weight: 2.5,
                  }}
                  eventHandlers={{
                    click: () => {
                      if (onSelectZone) onSelectZone(feature);
                    },
                  }}
                >
                  <Popup className="hab-custom-popup">
                    <div className="hab-popup">
                      <div className="hab-popup__header">
                        <div className="hab-popup__title-wrap">
                          <h3 className="hab-popup__title">
                            <span>📍</span> {locationName}
                          </h3>
                          <span className="hab-popup__coords">
                            {lat.toFixed(4)}°N, {Math.abs(lon).toFixed(4)}°W
                          </span>
                        </div>
                        <RiskBadge level={props.risk_level || riskConfig.label} size="sm" />
                      </div>

                      {/* Risk Score Progress Bar */}
                      <div className="hab-popup__score-bar-container">
                        <div className="hab-popup__score-header">
                          <span style={{ color: "#8b949e" }}>HAB Risk Index</span>
                          <span style={{ color: riskConfig.color }}>{score} / 100</span>
                        </div>
                        <div className="hab-popup__score-bar-bg">
                          <div
                            className="hab-popup__score-bar-fill"
                            style={{
                              width: `${Math.min(100, Math.max(0, score))}%`,
                              backgroundColor: riskConfig.color,
                            }}
                          />
                        </div>
                      </div>

                      {/* Environmental Telemetry Grid */}
                      <div className="hab-popup__grid">
                        <div className="hab-popup__metric">
                          <div className="hab-popup__metric-label">Chlorophyll-a</div>
                          <div className="hab-popup__metric-val">{chlorophyllA}</div>
                        </div>
                        <div className="hab-popup__metric">
                          <div className="hab-popup__metric-label">SST Anomaly</div>
                          <div className="hab-popup__metric-val">{sstAnomaly}</div>
                        </div>
                      </div>

                      {/* Secondary metrics if provided by backend */}
                      {props.hab_probability !== undefined && (
                        <div
                          style={{
                            fontSize: "0.75rem",
                            marginBottom: "0.6rem",
                            color: "#c9d1d9",
                            display: "flex",
                            justifyContent: "space-between",
                          }}
                        >
                          <span style={{ color: "#8b949e" }}>Bloom Probability:</span>
                          <span style={{ fontWeight: 600 }}>
                            {(props.hab_probability * 100).toFixed(1)}%
                          </span>
                        </div>
                      )}

                      <div className="hab-popup__footer">
                        <span className="hab-popup__date">
                          <span>🕒</span> {detectedDate}
                        </span>
                      </div>
                    </div>
                  </Popup>
                </CircleMarker>
              </React.Fragment>
            );
          }

          // Handle Polygon Geometries (for delineated bloom boundaries)
          if (geom.type === "Polygon") {
            const latLngs = geom.coordinates.map((ring) =>
              ring.map(([lon, lat]) => [lat, lon])
            );

            return (
              <Polygon
                key={`zone-poly-${idx}`}
                positions={latLngs}
                pathOptions={{
                  color: riskConfig.color,
                  fillColor: riskConfig.color,
                  fillOpacity: parseFloat(fillOpacity),
                  weight: 2,
                }}
                eventHandlers={{
                  click: () => {
                    if (onSelectZone) onSelectZone(feature);
                  },
                }}
              >
                <Popup className="hab-custom-popup">
                  <div className="hab-popup">
                    <div className="hab-popup__header">
                      <div className="hab-popup__title-wrap">
                        <h3 className="hab-popup__title">
                          <span>🌐</span> {locationName}
                        </h3>
                        <span className="hab-popup__coords">Polygon Zone</span>
                      </div>
                      <RiskBadge level={props.risk_level || riskConfig.label} size="sm" />
                    </div>

                    <div className="hab-popup__score-bar-container">
                      <div className="hab-popup__score-header">
                        <span style={{ color: "#8b949e" }}>HAB Risk Index</span>
                        <span style={{ color: riskConfig.color }}>{score} / 100</span>
                      </div>
                      <div className="hab-popup__score-bar-bg">
                        <div
                          className="hab-popup__score-bar-fill"
                          style={{
                            width: `${Math.min(100, Math.max(0, score))}%`,
                            backgroundColor: riskConfig.color,
                          }}
                        />
                      </div>
                    </div>

                    <div className="hab-popup__grid">
                      <div className="hab-popup__metric">
                        <div className="hab-popup__metric-label">Chlorophyll-a</div>
                        <div className="hab-popup__metric-val">{chlorophyllA}</div>
                      </div>
                      <div className="hab-popup__metric">
                        <div className="hab-popup__metric-label">SST Anomaly</div>
                        <div className="hab-popup__metric-val">{sstAnomaly}</div>
                      </div>
                    </div>

                    <div className="hab-popup__footer">
                      <span className="hab-popup__date">
                        <span>🕒</span> {detectedDate}
                      </span>
                    </div>
                  </div>
                </Popup>
              </Polygon>
            );
          }

          return null;
        })}
      </MapContainer>

      {/* Fixed Risk Level Legend Overlay */}
      <RiskLegend position={legendPosition} />
    </div>
  );
}
