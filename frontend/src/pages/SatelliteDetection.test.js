import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { Simulate } from "react-dom/test-utils";
import SatelliteDetection from "./SatelliteDetection";
import {
  analyzeSatelliteImage,
  getSatelliteAnalysis,
  getSatelliteOutputUrl,
  uploadSatelliteImage,
  validateSatelliteImage,
} from "../services/api";

jest.mock("react-leaflet", () => {
  const ReactForMapMocks = require("react");
  const mockMap = { fitBounds: jest.fn() };
  return {
    ImageOverlay: ({ url, bounds }) => ReactForMapMocks.createElement(
      "div",
      {
        "data-testid": "satellite-overlay",
        "data-url": url,
        "data-bounds": JSON.stringify(bounds),
      }
    ),
    MapContainer: ({ children }) => ReactForMapMocks.createElement(
      "div",
      { "data-testid": "satellite-map" },
      children
    ),
    Rectangle: () => null,
    TileLayer: () => null,
    useMap: () => mockMap,
  };
});

jest.mock("../services/api", () => ({
  analyzeSatelliteImage: jest.fn(),
  apiFailureMessage: (error) => error?.message || "API request failed",
  getSatelliteAnalysis: jest.fn(),
  getSatelliteOutputUrl: jest.fn((path) => `http://localhost:8000${path}`),
  uploadSatelliteImage: jest.fn(),
  validateSatelliteImage: jest.fn(),
}));

global.IS_REACT_ACT_ENVIRONMENT = true;

let container;
let root;

async function dispatchFile(file) {
  const input = container.querySelector('input[type="file"]');
  Object.defineProperty(input, "files", { configurable: true, value: [file] });
  await act(async () => {
    Simulate.change(input);
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

async function renderAnalysisResult(result) {
  uploadSatelliteImage.mockResolvedValue({
    file_id: "a".repeat(32),
    validation: { status: "VALID", warnings: [] },
  });
  validateSatelliteImage.mockResolvedValue({
    status: "VALID",
    sensor: "Sentinel-3 OLCI",
    product_type: "CIcyano",
    product_version: "v9110V20255_2",
    warnings: [],
  });
  analyzeSatelliteImage.mockResolvedValue({
    analysis_id: result.analysis_id,
  });
  getSatelliteAnalysis.mockResolvedValue(result);

  await act(async () => root.render(<SatelliteDetection />));
  await dispatchFile(new File(["tiff"], "scene.tif", { type: "image/tiff" }));
  const analyzeButton = Array.from(container.querySelectorAll("button"))
    .find((button) => button.textContent.includes("Analyze satellite image"));
  await act(async () => {
    Simulate.click(analyzeButton);
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

beforeEach(() => {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  jest.clearAllMocks();
});

test("rejects a non-GeoTIFF before contacting the backend", async () => {
  await act(async () => root.render(<SatelliteDetection />));
  await dispatchFile(new File(["image"], "preview.png", { type: "image/png" }));

  expect(container.textContent).toContain("Choose a GeoTIFF file");
  expect(uploadSatelliteImage).not.toHaveBeenCalled();
});

test("uploads, analyzes, and renders screening results and map overlay", async () => {
  const result = {
    analysis_id: "b".repeat(32),
    acquisition_date: null,
    bounds: {
      min_latitude: 26.6,
      max_latitude: 27.3,
      min_longitude: -81.2,
      max_longitude: -80.5,
    },
    display: {
      crs: "EPSG:3857",
      bounds: {
        min_latitude: 26.61,
        max_latitude: 27.29,
        min_longitude: -81.19,
        max_longitude: -80.51,
      },
    },
    outputs: { overlay_url: `/api/satellite-detection/result/${"b".repeat(32)}/overlay` },
    analysis: {
      mean_indicator: 0.02,
      maximum_indicator: 0.12,
      minimum_indicator: 0.001,
      median_indicator: 0.02,
      standard_deviation_indicator: 0.01,
      valid_pixel_count: 824,
      invalid_pixel_count: 176,
      hotspot_pixel_count: 37,
      high_indicator_pixel_percentage: 4.5,
      hotspot_pixel_percentage: 4.5,
      screening_status: "RELATIVE_HOTSPOTS_DETECTED",
      threshold_source: "Scene-specific Tukey upper fence; relative screen only.",
      threshold: 0.08,
      percentiles: { p25: 0.01, p50: 0.02, p75: 0.03, p90: 0.05, p95: 0.07, p99: 0.1 },
    },
    quality: { valid_pixel_percentage: 82.4, cloud_percentage: 4.1, warnings: [] },
    disclaimer: "Experimental screening, not confirmed HAB diagnosis.",
  };
  uploadSatelliteImage.mockResolvedValue({
    file_id: "a".repeat(32),
    validation: { status: "VALID", warnings: [] },
  });
  validateSatelliteImage.mockResolvedValue({
    status: "VALID",
    sensor: "Sentinel-3 OLCI",
    product_type: "CIcyano",
    product_version: "v9110V20255_2",
    product_identification_status: "METADATA_CONSISTENT_NOT_AUTHENTICATED",
    provenance_authenticated: false,
    scale_formula: "10**(3.0 / 250.0 * DN - 4.2)",
    band_descriptions: [null],
    acquisition_date: null,
    crs: "EPSG:32617",
    spatial_resolution: [300, 300],
    width: 20,
    height: 10,
    band_count: 1,
    valid_pixel_percentage: 82.4,
    bounds: {
      min_latitude: 26.6,
      max_latitude: 27.3,
      min_longitude: -81.2,
      max_longitude: -80.5,
    },
  });
  analyzeSatelliteImage.mockResolvedValue(result);
  getSatelliteAnalysis.mockResolvedValue(result);

  await act(async () => root.render(<SatelliteDetection />));
  await dispatchFile(new File(["fake tiff bytes"], "scene.tif", { type: "image/tiff" }));
  expect(container.textContent).toContain("Sentinel-3 OLCI");
  expect(validateSatelliteImage).toHaveBeenCalledWith("a".repeat(32));

  const analyzeButton = Array.from(container.querySelectorAll("button"))
    .find((button) => button.textContent.includes("Analyze satellite image"));
  await act(async () => {
    Simulate.click(analyzeButton);
    await new Promise((resolve) => setTimeout(resolve, 0));
  });

  expect(analyzeSatelliteImage).toHaveBeenCalledWith("a".repeat(32));
  expect(getSatelliteAnalysis).toHaveBeenCalledWith("b".repeat(32));
  expect(container.textContent).toContain("Mean CIcyano index");
  expect(container.textContent).toContain("Standard deviation");
  expect(container.textContent).toContain("Invalid / masked pixels");
  expect(container.textContent).toContain("P99 CIcyano index");
  expect(container.textContent).toContain("Relative CIcyano hotspots — requires independent verification.");
  expect(container.textContent).toContain("Metadata-consistent; not independently authenticated");
  expect(container.textContent).toContain("0.02");
  expect(container.textContent).toContain("4.50%");
  expect(container.textContent).toContain("Spatial screening map");
  expect(container.textContent).toContain("EPSG:3857");
  expect(container.textContent).toContain("Experimental screening, not confirmed HAB diagnosis.");
  expect(container.querySelector('[data-testid="satellite-overlay"]')).not.toBeNull();
  expect(container.querySelector('[data-testid="satellite-overlay"]').getAttribute("data-bounds"))
    .toBe(JSON.stringify([
      [26.61, -81.19],
      [27.29, -80.51],
    ]));
  expect(getSatelliteOutputUrl).toHaveBeenCalledWith(result.outputs.overlay_url);
});

test.each([
  {
    name: "insufficient coverage",
    status: "INSUFFICIENT_COVERAGE",
    category: "INSUFFICIENT_COVERAGE",
    validPercentage: 9,
    validCount: 9,
    invalidCount: 91,
    hotspotCount: null,
    hotspotPercentage: null,
    warnings: ["Hotspot screening was not performed below 10% valid coverage."],
    expectedMessage: "too little of the image contains valid data",
    expectedCoverage: "9.0%",
    shouldShowNoHotspotsMessage: false,
  },
  {
    name: "no valid pixels",
    status: "NO_VALID_PIXELS",
    category: "NO_VALID_PIXELS",
    validPercentage: 0,
    validCount: 0,
    invalidCount: 100,
    hotspotCount: null,
    hotspotPercentage: null,
    warnings: ["No valid pixels remained; screening was not performed."],
    expectedMessage: "No valid pixels were available",
    expectedCoverage: "0.0%",
    shouldShowNoHotspotsMessage: false,
  },
  {
    name: "low-coverage detection",
    status: "RELATIVE_HOTSPOTS_DETECTED",
    category: "LOW_COVERAGE",
    validPercentage: 10,
    validCount: 10,
    invalidCount: 90,
    hotspotCount: 1,
    hotspotPercentage: 10,
    warnings: ["Low valid-pixel coverage: results may be unstable."],
    expectedMessage: "results may be unstable or unrepresentative",
    expectedCoverage: "10.0%",
    shouldShowNoHotspotsMessage: false,
  },
  {
    name: "low-coverage no-hotspot result",
    status: "NO_RELATIVE_HOTSPOTS",
    category: "LOW_COVERAGE",
    validPercentage: 24,
    validCount: 24,
    invalidCount: 76,
    hotspotCount: 0,
    hotspotPercentage: 0,
    warnings: ["Low valid-pixel coverage: results may be unstable."],
    expectedMessage: "does not establish that the waterbody is HAB-free",
    expectedCoverage: "24.0%",
    shouldShowNoHotspotsMessage: true,
  },
  {
    name: "moderate coverage",
    status: "NO_RELATIVE_HOTSPOTS",
    category: "MODERATE_COVERAGE",
    validPercentage: 25,
    validCount: 25,
    invalidCount: 75,
    hotspotCount: 0,
    hotspotPercentage: 0,
    warnings: [],
    expectedMessage: "does not establish that the waterbody is HAB-free",
    expectedCoverage: "25.0%",
    shouldShowNoHotspotsMessage: true,
  },
  {
    name: "better coverage detection",
    status: "RELATIVE_HOTSPOTS_DETECTED",
    category: "BETTER_COVERAGE",
    validPercentage: 50,
    validCount: 50,
    invalidCount: 50,
    hotspotCount: 2,
    hotspotPercentage: 4,
    warnings: [],
    expectedMessage: "Relative hotspots were identified",
    expectedCoverage: "50.0%",
    shouldShowNoHotspotsMessage: false,
  },
])(
  "presents $name coverage without overstating the result",
  async ({
    status,
    category,
    validPercentage,
    validCount,
    invalidCount,
    hotspotCount,
    hotspotPercentage,
    warnings,
    expectedMessage,
    expectedCoverage,
    shouldShowNoHotspotsMessage,
  }) => {
    const result = {
      analysis_id: "b".repeat(32),
      crs: "EPSG:32617",
      bounds: {
        min_latitude: 26.6,
        max_latitude: 27.3,
        min_longitude: -81.2,
        max_longitude: -80.5,
      },
      display: {
        crs: "EPSG:3857",
        bounds: {
          min_latitude: 26.61,
          max_latitude: 27.29,
          min_longitude: -81.19,
          max_longitude: -80.51,
        },
      },
      outputs: { overlay_url: "/analysis/overlay" },
      analysis: {
        screening_status: status,
        coverage_category: category,
        mean_indicator: null,
        median_indicator: null,
        standard_deviation_indicator: null,
        minimum_indicator: null,
        maximum_indicator: null,
        valid_pixel_count: validCount,
        invalid_pixel_count: invalidCount,
        hotspot_pixel_count: hotspotCount,
        hotspot_pixel_percentage: hotspotPercentage,
        threshold: null,
        threshold_source: "Not calculated.",
        percentiles: {},
      },
      quality: {
        valid_pixel_percentage: validPercentage,
        coverage_category: category,
        warnings,
      },
      disclaimer: "Experimental screening only.",
    };

    await renderAnalysisResult(result);

    expect(container.textContent).toContain(expectedMessage);
    expect(container.textContent).toContain(expectedCoverage);
    expect(container.textContent).toContain(category);
    expect(container.textContent).toContain(
      shouldShowNoHotspotsMessage ? "0 (0.00%)" : status === "RELATIVE_HOTSPOTS_DETECTED"
        ? `${hotspotCount} (${hotspotPercentage.toFixed(2)}%)`
        : "Not screened"
    );
    if (warnings.length) {
      expect(container.textContent).toContain(warnings[0]);
    }
    if (status === "INSUFFICIENT_COVERAGE") {
      expect(container.textContent).not.toContain("No high relative-indicator pixels");
      expect(container.querySelector('[role="alert"][aria-label="Screening warnings"]'))
        .not.toBeNull();
    }
    if (status === "INSUFFICIENT_COVERAGE" || status === "NO_VALID_PIXELS") {
      expect(container.textContent).toContain("Relative hotspot screening not performed");
    }
  }
);

test("shows distinct processing states and prevents duplicate analysis requests", async () => {
  let finishUpload;
  let finishAnalysis;
  uploadSatelliteImage.mockReturnValue(
    new Promise((resolve) => {
      finishUpload = resolve;
    })
  );
  validateSatelliteImage.mockResolvedValue({
    status: "VALID",
    sensor: "Sentinel-3 OLCI",
    product_type: "CIcyano",
    warnings: [],
  });
  analyzeSatelliteImage.mockReturnValue(
    new Promise((resolve) => {
      finishAnalysis = resolve;
    })
  );
  getSatelliteAnalysis.mockResolvedValue({ analysis_id: "b".repeat(32) });

  await act(async () => root.render(<SatelliteDetection />));
  await dispatchFile(new File(["tiff"], "scene.tif", { type: "image/tiff" }));
  expect(container.textContent).toContain("Uploading and validating…");

  await act(async () => {
    finishUpload({ file_id: "a".repeat(32) });
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
  expect(container.textContent).toContain("VALID");

  const analyzeButton = Array.from(container.querySelectorAll("button"))
    .find((button) => button.textContent.includes("Analyze satellite image"));
  await act(async () => {
    Simulate.click(analyzeButton);
    await Promise.resolve();
  });
  expect(container.textContent).toContain("Calculating scaled pixel statistics");
  expect(analyzeButton.disabled).toBe(true);

  await act(async () => {
    Simulate.click(analyzeButton);
    await Promise.resolve();
  });
  expect(analyzeSatelliteImage).toHaveBeenCalledTimes(1);

  await act(async () => {
    finishAnalysis({ analysis_id: "b".repeat(32) });
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
});
