
import React, {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

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


function isGeoTiff(file) {
  return /\.(tif|tiff)$/i.test(file.name);
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
          typeof value === "number" &&
          Number.isFinite(value)
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
  const bounds = isValidGeographicBounds(
    result?.display?.bounds
  )
    ? result.display.bounds
    : result?.bounds;

  if (!isValidGeographicBounds(bounds)) {
    return null;
  }

  return [
    [
      bounds.min_latitude,
      bounds.min_longitude,
    ],
    [
      bounds.max_latitude,
      bounds.max_longitude,
    ],
  ];
}


function FitMapToBounds({ bounds }) {
  const map = useMap();

  useEffect(() => {
    if (bounds) {
      map.fitBounds(
        bounds,
        {
          padding: [18, 18],
        }
      );
    }
  }, [bounds, map]);

  return null;
}


function getProductName(validation) {
  return (
    validation?.product_name ||
    validation?.product_type ||
    validation?.product_family ||
    "Unknown satellite product"
  );
}


function isCiCyano(validation, result) {
  return (
    validation?.product_name === "CIcyano" &&
    validation?.analysis_capability === "ci_cyano_screening"
  ) || (
    result?.product_type === "CIcyano" &&
    result?.analysis?.analysis_type === "ci_cyano_screening"
  );
}


function getPreviewUrl(result) {
  const path =
    result?.outputs?.preview_url ||
    result?.outputs?.overlay_url ||
    result?.preview_url;

  return path
    ? getSatelliteOutputUrl(path)
    : null;
}


function HabResultCard({
  label,
  value,
  detail,
  score,
  showProgress = false,
}) {
  const isAvailable =
    typeof score === "number" &&
    Number.isFinite(score) &&
    score >= 0 &&
    score <= 100;

  return (
    <article className="satellite-hab-result-card">
      <span>{label}</span>

      <strong>{value}</strong>

      {showProgress ? (
        <div
          className="satellite-probability-track"
          role="progressbar"
          aria-label={label}
          aria-valuemin={0}
          aria-valuemax={100}
          {...(
            isAvailable
              ? {
                  "aria-valuenow": score,
                }
              : {
                  "aria-valuetext": "Not available",
                }
          )}
        >
          <div
            className="satellite-probability-fill"
            style={{
              width: `${isAvailable ? score : 0}%`,
            }}
          />
        </div>
      ) : null}

      {detail ? (
        <small>{detail}</small>
      ) : null}
    </article>
  );
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
      const uploaded = await uploadSatelliteImage(
        selectedFile
      );

      if (!uploaded?.file_id) {
        throw new Error(
          "Backend did not return a valid uploaded file ID."
        );
      }

      setFileId(uploaded.file_id);

      const validationResponse =
        await validateSatelliteImage(
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
      const analyzed = await analyzeSatelliteImage(
        fileId
      );

      if (!analyzed?.analysis_id) {
        throw new Error(
          "Backend did not return a valid analysis ID."
        );
      }

      const analysisResult =
        await getSatelliteAnalysis(
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

    selectFile(
      event.dataTransfer.files?.[0]
    );
  }


  const ciCyanoProduct = isCiCyano(
    validation,
    result
  );

  const bounds = useMemo(
    () => (
      ciCyanoProduct
        ? mapBounds(result)
        : null
    ),
    [result, ciCyanoProduct]
  );

  const center = bounds
    ? [
        (bounds[0][0] + bounds[1][0]) / 2,
        (bounds[0][1] + bounds[1][1]) / 2,
      ]
    : [24, -45];

  const previewUrl = getPreviewUrl(result);

  const productName = getProductName(validation);

  const habDetection = result?.hab_detection;

  const probability =
    habDetection?.model?.probability_calibrated === true &&
    typeof habDetection.hab_probability === "number" &&
    Number.isFinite(habDetection.hab_probability) &&
    habDetection.hab_probability >= 0 &&
    habDetection.hab_probability <= 1
      ? habDetection.hab_probability * 100
      : null;

  const riskScore =
    typeof habDetection?.risk_score === "number" &&
    Number.isFinite(habDetection.risk_score) &&
    habDetection.risk_score >= 0 &&
    habDetection.risk_score <= 100
      ? habDetection.risk_score
      : null;

  const allowedRiskLevels = ["LOW", "MODERATE", "HIGH", "CRITICAL"];
  const riskLevel = allowedRiskLevels.includes(
    habDetection?.risk_level
  )
    ? habDetection.risk_level
    : null;

  const model = habDetection?.model;
  const modelVersion =
    model?.inference_ran === true &&
    typeof model.name === "string" &&
    typeof model.version === "string" &&
    model.name.trim() &&
    model.version.trim()
      ? `${model.name} v${model.version}`
      : "Not available";


  return (
    <section className="satellite-detection-page">

      <header className="satellite-detection-header">
        <p className="satellite-eyebrow">
          OCEANWATCH AI / SATELLITE ANALYSIS
        </p>

        <h1>Satellite Product Analysis</h1>

        <p>
          Upload a supported satellite GeoTIFF to view its
          preview and analysis.
        </p>
      </header>


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
              GeoTIFF only (.tif, .tiff);
              maximum upload size 100 MiB.
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

          onDragOver={(event) => {
            event.preventDefault();
          }}

          onDragLeave={(event) => {
            if (
              !event.currentTarget.contains(
                event.relatedTarget
              )
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
              selectFile(
                event.target.files?.[0]
              )
            }

            disabled={busy}
          />


          <div
            className="satellite-drop-icon"
            aria-hidden="true"
          >
            <svg
              viewBox="0 0 48 48"
              focusable="false"
            >
              <path d="M24 7v19" />
              <path d="m17 17 7-10 7 10" />
              <path d="M11 27v12h26V27" />
              <path d="M17 33h14" />
            </svg>
          </div>


          <p>
            Drag and drop your GeoTIFF here
          </p>

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
              <span>
                {formatFileSize(file.size)}
              </span>
            </div>


            <div className="satellite-file-status">
              <span>
                {busy
                  ? activity === "uploading"
                    ? "Uploading and validating..."
                    : "Analyzing..."
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
          <div
            className="satellite-error"
            role="alert"
          >
            {error}
          </div>
        ) : null}


        {validation?.warnings?.length ? (
          <ul
            className="satellite-warning-list"
            aria-label="Validation warnings"
          >
            {validation.warnings.map(
              (warning, index) => (
                <li key={`${index}-${warning}`}>
                  {warning}
                </li>
              )
            )}
          </ul>
        ) : null}

      </section>


      {validation ? (
        <section
          className="satellite-panel satellite-analysis-panel"
          aria-labelledby="satellite-analysis-title"
        >

          <div className="satellite-section-heading">
            <div>
              <h2 id="satellite-analysis-title">
                Analyze image
              </h2>

              <p>
                View the satellite preview and available
                analysis results.
              </p>
            </div>


            <button
              className="satellite-primary-button"
              type="button"
              onClick={handleAnalyze}
              disabled={busy || !fileId}
            >
              {busy
                ? "Processing..."
                : "Analyze satellite image"}
            </button>

          </div>


          {busy ? (
            <div
              className="satellite-progress"
              role="status"
            >
              {activity === "uploading"
                ? "Uploading and validating product metadata..."
                : "Analyzing the satellite image..."}
            </div>
          ) : null}

        </section>
      ) : null}


      {result ? (
        <>
          <section
            className="satellite-panel"
            aria-labelledby="satellite-hab-results-title"
          >
            <div className="satellite-section-heading">
              <div>
                <h2 id="satellite-hab-results-title">
                  HAB detection results
                </h2>
                <p>{productName}</p>
              </div>
            </div>

            <div className="satellite-hab-result-grid">
              <HabResultCard
                label="HAB Probability"
                value={
                  probability === null
                    ? "Not available"
                    : `${probability.toFixed(1)}%`
                }
                score={probability}
                showProgress
                detail={
                  habDetection?.reasons?.hab_probability ||
                  "A calibrated satellite HAB probability is not available."
                }
              />

              <HabResultCard
                label="Risk Score"
                value={riskScore === null ? "Not available" : riskScore}
                detail={
                  habDetection?.reasons?.risk_score ||
                  "A validated environmental risk score is not available."
                }
              />

              <HabResultCard
                label="Risk Level"
                value={riskLevel || "Not available"}
                detail={
                  habDetection?.reasons?.risk_level ||
                  "A risk level cannot be assigned without a risk score."
                }
              />

              <HabResultCard
                label="Model Version"
                value={modelVersion}
                detail={
                  model?.reason ||
                  "No compatible satellite HAB model is available for this product."
                }
              />
            </div>
          </section>


          {ciCyanoProduct ? (
            <section
              className="satellite-panel"
              aria-labelledby="satellite-map-title"
            >
              <div className="satellite-section-heading">
                <h2 id="satellite-map-title">
                  Satellite map preview
                </h2>
              </div>

              {bounds ? (

                <div className="satellite-map-frame">

                  <MapContainer
                    center={center}
                    zoom={6}
                    scrollWheelZoom
                    className="satellite-map"
                  >

                    <FitMapToBounds
                      bounds={bounds}
                    />


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

              ) : (

                <p className="satellite-map-unavailable">
                  The map preview is unavailable for this image.
                </p>

              )}

            </section>
          ) : null}


          {!ciCyanoProduct ? (
            <section
              className="satellite-panel"
              aria-labelledby="satellite-preview-title"
            >

              <div className="satellite-section-heading">
                <div>
                  <h2 id="satellite-preview-title">
                    {productName} preview
                  </h2>
                </div>
              </div>


              {previewUrl ? (

                <div className="satellite-generic-preview">

                  <img
                    src={previewUrl}
                    alt={`${productName} satellite product preview`}
                    loading="lazy"
                  />

                  <p>
                    Satellite image preview.
                  </p>

                </div>

              ) : (

                <p className="satellite-map-unavailable">
                  The image preview is unavailable.
                </p>

              )}

            </section>
          ) : null}

        </>
      ) : null}

    </section>
  );
}
