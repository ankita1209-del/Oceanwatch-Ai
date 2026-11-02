
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  ImageOverlay,
  MapContainer,
  Rectangle,
  TileLayer,
  useMap,
} from "react-leaflet";

import {
  analyzeSatelliteImage,
  apiFailureMessage,
  getSatelliteAnalysis,
  getSatelliteOutputUrl,
  uploadSatelliteImage,
  validateSatelliteImage,
} from "../services/api";

import "./SatelliteDetection.css";

const MAX_FILE_SIZE = 100 * 1024 * 1024;

const DISCLAIMER =
  "Research prototype only — not an operational HAB warning system. Relative CIcyano hotspots are experimental statistical outliers, not confirmed HAB detections or probabilities; independent field and laboratory verification may be required.";

function isGeoTiff(file) {
  return /\.(tif|tiff)$/i.test(file.name);
}

function display(value, suffix = "") {
  if (value === null || value === undefined || value === "") {
    return "Not available";
  }

  if (typeof value === "number" && !Number.isFinite(value)) {
    return "Not available";
  }

  return `${value}${suffix}`;
}

function displayNumber(value, digits = 2, suffix = "") {
  return typeof value === "number" && Number.isFinite(value)
    ? `${value.toFixed(digits)}${suffix}`
    : "Not available";
}

function formatFileSize(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) {
    return "Unknown size";
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function isValidGeographicBounds(bounds) {
  return Boolean(
    bounds &&
      [
        bounds.min_latitude,
        bounds.max_latitude,
        bounds.min_longitude,
        bounds.max_longitude,
      ].every(
        (value) =>
          typeof value === "number" && Number.isFinite(value)
      ) &&
      bounds.min_latitude >= -90 &&
      bounds.max_latitude <= 90 &&
      bounds.min_longitude >= -180 &&
      bounds.max_longitude <= 180 &&
      bounds.min_latitude < bounds.max_latitude &&
      bounds.min_longitude < bounds.max_longitude
  );
}

function mapBounds(result) {
  const displayBounds = result?.display?.bounds;
  const sourceBounds = result?.bounds;

  const bounds = isValidGeographicBounds(displayBounds)
    ? displayBounds
    : sourceBounds;

  if (!isValidGeographicBounds(bounds)) {
    return null;
  }

  return [
    [bounds.min_latitude, bounds.min_longitude],
    [bounds.max_latitude, bounds.max_longitude],
  ];
}

function getScreeningMessage(status, coverageCategory) {
  if (status === "INSUFFICIENT_COVERAGE") {
    return "Hotspot screening was not performed because too little of the image contains valid data. This does not mean hotspots are absent or that the water is HAB-free.";
  }

  if (status === "NO_VALID_PIXELS") {
    return "No valid pixels were available. Hotspot screening was not performed; check the uploaded product and its quality mask.";
  }

  const lowCoverageNote =
    coverageCategory === "LOW_COVERAGE"
      ? " Low valid-pixel coverage means results may be unstable or unrepresentative."
      : "";

  switch (status) {
    case "RELATIVE_HOTSPOTS_DETECTED":
      return `Relative hotspots were identified under the scene-specific screening rule.${lowCoverageNote}`;

    case "NO_RELATIVE_HOTSPOTS":
      return `No high relative-indicator pixels were found under the scene-specific screening rule. This does not establish that the waterbody is HAB-free.${lowCoverageNote}`;

    default:
      return "Screening status is unavailable or unrecognized. Check the backend response.";
  }
}

function formatGeographicCoordinates(bounds) {
  if (!isValidGeographicBounds(bounds)) {
    return "Source geographic bounds are not available.";
  }

  return (
    `Latitude: ${bounds.min_latitude.toFixed(4)}° to ` +
    `${bounds.max_latitude.toFixed(4)}°; longitude: ` +
    `${bounds.min_longitude.toFixed(4)}° to ` +
    `${bounds.max_longitude.toFixed(4)}°.`
  );
}

function ResultCard({ label, value, detail }) {
  return (
    <article className="satellite-result-card">
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </article>
  );
}

function FitMapToBounds({ bounds }) {
  const map = useMap();

  useEffect(() => {
    if (bounds) {
      map.fitBounds(bounds, { padding: [18, 18] });
    }
  }, [bounds, map]);

  return null;
}

export default function SatelliteDetection() {
  const inputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [fileId, setFileId] = useState("");
  const [validation, setValidation] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [activity, setActivity] = useState("");
  const [dragging, setDragging] = useState(false);

  async function selectFile(selectedFile) {
    if (busy) return;

    setError("");
    setResult(null);
    setFileId("");
    setValidation(null);

    if (!selectedFile) return;

    if (!isGeoTiff(selectedFile)) {
      setFile(null);
      setError(
        "Choose a GeoTIFF file with a .tif or .tiff extension."
      );
      return;
    }

    if (
      selectedFile.size === 0 ||
      selectedFile.size > MAX_FILE_SIZE
    ) {
      setFile(null);
      setError(
        "Choose a non-empty GeoTIFF no larger than 100 MiB."
      );
      return;
    }

    setFile(selectedFile);
    setBusy(true);
    setActivity("uploading");

    try {
      const uploaded = await uploadSatelliteImage(selectedFile);

      if (!uploaded?.file_id) {
        throw new Error(
          "Backend did not return a valid uploaded file ID."
        );
      }

      setFileId(uploaded.file_id);

      const validationResponse = await validateSatelliteImage(
        uploaded.file_id
      );

      if (!validationResponse) {
        throw new Error(
          "Backend returned an empty validation response."
        );
      }

      setValidation(validationResponse);
    } catch (requestError) {
      setFile(null);
      setFileId("");
      setValidation(null);

      setError(
        requestError?.response
          ? apiFailureMessage(requestError)
          : requestError?.message ||
              "Satellite image upload or validation failed."
      );
    } finally {
      setBusy(false);
      setActivity("");
    }
  }

  async function handleAnalyze() {
    if (!fileId || busy) return;

    setBusy(true);
    setActivity("analyzing");
    setError("");
    setResult(null);

    try {
      const analyzed = await analyzeSatelliteImage(fileId);

      if (!analyzed?.analysis_id) {
        throw new Error(
          "Backend did not return a valid analysis ID."
        );
      }

      const analysisResult = await getSatelliteAnalysis(
        analyzed.analysis_id
      );

      if (!analysisResult) {
        throw new Error(
          "Backend returned an empty analysis result."
        );
      }

      setResult(analysisResult);
    } catch (requestError) {
      setError(
        requestError?.response
          ? apiFailureMessage(requestError)
          : requestError?.message ||
              "Satellite image analysis failed."
      );
    } finally {
      setBusy(false);
      setActivity("");
    }
  }

  function removeFile() {
    if (busy) return;

    setFile(null);
    setFileId("");
    setValidation(null);
    setResult(null);
    setError("");

    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  function handleDrop(event) {
    event.preventDefault();
    setDragging(false);

    if (busy) return;

    selectFile(event.dataTransfer.files?.[0]);
  }

  const bounds = useMemo(
    () => mapBounds(result),
    [result]
  );

  const center = bounds
    ? [
        (bounds[0][0] + bounds[1][0]) / 2,
        (bounds[0][1] + bounds[1][1]) / 2,
      ]
    : [24, -45];

  const analysis = result?.analysis;
  const quality = result?.quality;

  const sourceBounds = result?.bounds;
  const screeningPerformed = [
    "RELATIVE_HOTSPOTS_DETECTED",
    "NO_RELATIVE_HOTSPOTS",
  ].includes(analysis?.screening_status);

  return (
    <section className="satellite-detection-page">
      <header className="satellite-detection-header">
        <p className="satellite-eyebrow">
          OCEANWATCH AI / SATELLITE SCREENING
        </p>

        <h1>Satellite CIcyano Screening</h1>

        <p>
          Review relative CIcyano spectral-indicator patterns
          from a supported Sentinel-3 product. This workflow
          does not confirm HAB presence.
        </p>
      </header>

      <div className="satellite-notice" role="note">
        <strong>Supported input:</strong> Sentinel-3 OLCI CIcyano
        GeoTIFF product version v9110V20255_2. RGB previews and
        unrecognized products cannot be analyzed.
      </div>

      <div className="satellite-disclaimer" role="note">
        {DISCLAIMER}
      </div>

      <section
        className="satellite-panel"
        aria-labelledby="satellite-upload-title"
      >
        <div className="satellite-section-heading">
          <div>
            <h2 id="satellite-upload-title">
              Upload satellite image
            </h2>

            <p>
              GeoTIFF only (.tif, .tiff); maximum upload size
              100 MiB.
            </p>
          </div>
        </div>

        <div
          className={`satellite-dropzone${
            dragging ? " is-dragging" : ""
          }`}
          onDragEnter={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragOver={(event) => event.preventDefault()}
          onDragLeave={(event) => {
            if (
              !event.currentTarget.contains(event.relatedTarget)
            ) {
              setDragging(false);
            }
          }}
          onDrop={handleDrop}
        >
          <input
            ref={inputRef}
            className="satellite-file-input"
            type="file"
            accept=".tif,.tiff,image/tiff"
            aria-label="Choose a GeoTIFF satellite image"
            onChange={(event) =>
              selectFile(event.target.files?.[0])
            }
            disabled={busy}
          />

          <div className="satellite-drop-icon" aria-hidden="true">
            ↑
          </div>

          <p>Drag and drop your GeoTIFF here</p>
          <span>or</span>

          <button
            className="satellite-secondary-button"
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={busy}
          >
            Browse files
          </button>
        </div>

        {file ? (
          <div className="satellite-file-row">
            <div>
              <strong>{file.name}</strong>
              <span>{formatFileSize(file.size)}</span>
            </div>

            <div className="satellite-file-status">
              <span>
                {busy
                  ? activity === "uploading"
                    ? "Uploading and validating…"
                    : "Analyzing…"
                  : validation?.status || "Selected"}
              </span>

              <button
                type="button"
                onClick={removeFile}
                disabled={busy}
              >
                Remove
              </button>
            </div>
          </div>
        ) : null}

        {error ? (
          <div className="satellite-error" role="alert">
            {error}
          </div>
        ) : null}

        {validation?.warnings?.length ? (
          <ul
            className="satellite-warning-list"
            aria-label="Validation warnings"
          >
            {validation.warnings.map((warning, index) => (
              <li key={`${index}-${warning}`}>{warning}</li>
            ))}
          </ul>
        ) : null}
      </section>

      {validation ? (
        <section
          className="satellite-panel"
          aria-labelledby="satellite-metadata-title"
        >
          <div className="satellite-section-heading">
            <div>
              <h2 id="satellite-metadata-title">
                Image metadata
              </h2>

              <p>
                Metadata read from the uploaded GeoTIFF;
                missing values are not inferred.
              </p>
            </div>
          </div>

          <dl className="satellite-metadata-grid">
            <div>
              <dt>Sensor</dt>
              <dd>{display(validation.sensor)}</dd>
            </div>

            <div>
              <dt>Product</dt>
              <dd>{display(validation.product_type)}</dd>
            </div>

            <div>
              <dt>Product version</dt>
              <dd>{display(validation.product_version)}</dd>
            </div>

            <div>
              <dt>Product identification</dt>
              <dd>
                {validation.provenance_authenticated === false
                  ? "Metadata-consistent; not independently authenticated"
                  : display(
                      validation.product_identification_status
                    )}
              </dd>
            </div>

            <div>
              <dt>Acquisition date</dt>
              <dd>{display(validation.acquisition_date)}</dd>
            </div>

            <div>
              <dt>CRS</dt>
              <dd>{display(validation.crs)}</dd>
            </div>

            <div>
              <dt>Data type</dt>
              <dd>{display(validation.data_type)}</dd>
            </div>

            <div>
              <dt>Band description</dt>
              <dd>
                {display(validation.band_descriptions?.[0])}
              </dd>
            </div>

            <div>
              <dt>Scale formula</dt>
              <dd>{display(validation.scale_formula)}</dd>
            </div>

            <div>
              <dt>Pixel resolution</dt>
              <dd>
                {validation.spatial_resolution
                  ? `${validation.spatial_resolution.join(
                      " × "
                    )} source CRS units`
                  : "Not available"}
              </dd>
            </div>

            <div>
              <dt>Raster dimensions</dt>
              <dd>
                {validation.width && validation.height
                  ? `${validation.width} × ${validation.height}`
                  : "Not available"}
              </dd>
            </div>

            <div>
              <dt>Band count</dt>
              <dd>{display(validation.band_count)}</dd>
            </div>

            <div>
              <dt>Valid pixels</dt>
              <dd>
                {displayNumber(
                  validation.valid_pixel_percentage,
                  1,
                  "%"
                )}
              </dd>
            </div>

            <div>
              <dt>Geographic coverage</dt>
              <dd>
                {isValidGeographicBounds(validation.bounds)
                  ? formatGeographicCoordinates(validation.bounds)
                  : "Not available"}
              </dd>
            </div>
          </dl>
        </section>
      ) : null}

      {validation ? (
        <section
          className="satellite-panel satellite-analysis-panel"
          aria-labelledby="satellite-analysis-title"
        >
          <div className="satellite-section-heading">
            <div>
              <h2 id="satellite-analysis-title">
                Spectral screening
              </h2>

              <p>
                Calculates descriptive CIcyano pixel statistics
                and a scene-relative hotspot mask.
              </p>
            </div>

            <button
              className="satellite-primary-button"
              type="button"
              onClick={handleAnalyze}
              disabled={busy || !fileId}
            >
              {busy ? "Analyzing…" : "Analyze satellite image"}
            </button>
          </div>

          {busy ? (
            <div className="satellite-progress" role="status">
              {activity === "uploading"
                ? "Uploading and validating the product metadata…"
                : "Calculating scaled pixel statistics and generating the map preview…"}
            </div>
          ) : null}
        </section>
      ) : null}

      {result ? (
        <>
          <section
            className="satellite-panel"
            aria-labelledby="satellite-results-title"
          >
            <div className="satellite-section-heading">
              <div>
                <h2 id="satellite-results-title">
                  Screening results
                </h2>

                <p>
                  {getScreeningMessage(
                    analysis?.screening_status,
                    quality?.coverage_category
                  )}
                </p>
              </div>

              <span className="satellite-experimental-badge">
                Experimental screening
              </span>
            </div>

            <div className="satellite-result-grid">
              <ResultCard
                label="Mean CIcyano index"
                value={displayNumber(
                  analysis?.mean_indicator,
                  6
                )}
              />

              <ResultCard
                label="Median CIcyano index"
                value={displayNumber(
                  analysis?.median_indicator,
                  6
                )}
              />

              <ResultCard
                label="Standard deviation"
                value={displayNumber(
                  analysis?.standard_deviation_indicator,
                  6
                )}
              />

              <ResultCard
                label="Minimum CIcyano index"
                value={displayNumber(
                  analysis?.minimum_indicator,
                  6
                )}
              />

              <ResultCard
                label="Maximum CIcyano index"
                value={displayNumber(
                  analysis?.maximum_indicator,
                  6
                )}
              />

              <ResultCard
                label="Valid-pixel coverage"
                value={displayNumber(
                  quality?.valid_pixel_percentage,
                  1,
                  "%"
                )}
                detail={display(quality?.coverage_category)}
              />

              <ResultCard
                label="Valid pixels"
                value={display(analysis?.valid_pixel_count)}
              />

              <ResultCard
                label="Invalid / masked pixels"
                value={display(
                  analysis?.invalid_pixel_count
                )}
              />

              <ResultCard
                label="Relative scene hotspots"
                value={
                  screeningPerformed
                    ? `${display(
                        analysis?.hotspot_pixel_count
                      )} (${displayNumber(
                        analysis?.hotspot_pixel_percentage,
                        2,
                        "%"
                      )})`
                    : "Not screened"
                }
              />

              <ResultCard
                label="Cloud quality pixels"
                value={displayNumber(
                  quality?.cloud_percentage,
                  1,
                  "%"
                )}
              />
            </div>

            {quality?.warnings?.length ? (
              <ul
                className={`satellite-warning-list satellite-result-warnings${
                  analysis?.screening_status === "INSUFFICIENT_COVERAGE"
                    ? " is-insufficient"
                    : ""
                }`}
                aria-label="Screening warnings"
                role={
                  analysis?.screening_status === "INSUFFICIENT_COVERAGE"
                    ? "alert"
                    : "note"
                }
              >
                {quality.warnings.map((warning, index) => (
                  <li key={`${index}-${warning}`}>{warning}</li>
                ))}
              </ul>
            ) : null}

            <p className="satellite-threshold-note">
              {screeningPerformed
                ? `Relative CIcyano hotspots — requires independent verification. ${display(analysis?.threshold_source)}`
                : "Hotspot screening was not performed; no hotspot threshold or hotspot absence is reported."}
            </p>

            <details className="satellite-percentiles">
              <summary>
                Percentiles and scene-relative threshold
              </summary>

              <div className="satellite-result-grid satellite-percentile-grid">
                {[25, 50, 75, 90, 95, 99].map(
                  (percentile) => (
                    <ResultCard
                      key={percentile}
                      label={`P${percentile} CIcyano index`}
                      value={displayNumber(
                        analysis?.percentiles?.[
                          `p${percentile}`
                        ],
                        6
                      )}
                    />
                  )
                )}

                <ResultCard
                  label="Tukey upper fence"
                  value={displayNumber(
                    analysis?.threshold,
                    6
                  )}
                  detail="Q3 + 1.5 × IQR; not a validated HAB threshold"
                />
              </div>
            </details>
          </section>

          <section
            className="satellite-panel"
            aria-labelledby="satellite-map-title"
          >
            <div className="satellite-section-heading">
              <div>
                <h2 id="satellite-map-title">
                  Spatial screening map
                </h2>

                <p>
                  Map preview reprojected to{" "}
                  {display(result.display?.crs)}. The source
                  analysis rasters remain in{" "}
                  {display(result.crs)}.
                </p>
              </div>
            </div>

            {bounds ? (
              <>
                <div className="satellite-map-frame">
                  <MapContainer
                    center={center}
                    zoom={6}
                    scrollWheelZoom
                    className="satellite-map"
                  >
                    <FitMapToBounds bounds={bounds} />

                    <TileLayer
                      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />

                    <Rectangle
                      bounds={bounds}
                      pathOptions={{
                        color: "#d8ae6d",
                        weight: 2,
                        fillOpacity: 0,
                      }}
                    />

                    {result.outputs?.overlay_url ? (
                      <ImageOverlay
                        url={getSatelliteOutputUrl(
                          result.outputs.overlay_url
                        )}
                        bounds={bounds}
                        opacity={0.88}
                      />
                    ) : null}
                  </MapContainer>
                </div>

                <div className="satellite-map-legend">
                  <span className="legend-intensity">
                    <i className="legend-ramp" />
                    <span>
                      Continuous CIcyano indicator intensity
                      <small>
                        {displayNumber(
                          analysis?.minimum_indicator,
                          6
                        )}{" "}
                        to{" "}
                        {displayNumber(
                          analysis?.maximum_indicator,
                          6
                        )}
                      </small>
                    </span>
                  </span>

                  {screeningPerformed ? (
                    <span>
                      <i className="legend-high" />
                      Relative CIcyano hotspots — requires
                      independent verification
                    </span>
                  ) : (
                    <span>Relative hotspot screening not performed</span>
                  )}

                  <span>
                    <i className="legend-invalid" />
                    Invalid / masked pixels (transparent)
                  </span>

                  <span>
                    <i className="legend-footprint" />
                    Image footprint
                  </span>
                </div>

                <p className="satellite-map-coordinates">
                  {formatGeographicCoordinates(sourceBounds)}
                </p>
              </>
            ) : (
              <p className="satellite-map-unavailable">
                Geographic bounds were unavailable, so the map
                cannot be displayed.
              </p>
            )}
          </section>

          <div className="satellite-disclaimer" role="note">
            {result.disclaimer || DISCLAIMER}
          </div>
        </>
      ) : null}
    </section>
  );
}
