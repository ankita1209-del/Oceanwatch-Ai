import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { Simulate } from "react-dom/test-utils";
import MapView from "./MapView";
import { getEvents, getHealth, getRiskMap } from "../services/api";

jest.mock("leaflet", () => ({
  divIcon: (options) => ({ options }),
}));

jest.mock("react-leaflet", () => {
  const ReactForMapMocks = require("react");
  return {
    MapContainer: ({ children }) => ReactForMapMocks.createElement("div", { "data-testid": "map" }, children),
    TileLayer: () => null,
    Marker: ({ children, position, icon }) => ReactForMapMocks.createElement(
      "div",
      {
        "data-testid": "map-marker",
        "data-position": JSON.stringify(position),
        "data-icon-html": icon.options.html,
      },
      children
    ),
    Popup: ({ children }) => ReactForMapMocks.createElement("div", { "data-testid": "map-popup" }, children),
  };
});

jest.mock("../services/api", () => ({
  apiFailureMessage: (error) => error?.message || "API request failed",
  getEvents: jest.fn(),
  getHealth: jest.fn(),
  getRiskMap: jest.fn(),
}));

global.IS_REACT_ACT_ENVIRONMENT = true;

const event = (id, overrides = {}) => ({
  id,
  lat: 27.5,
  lon: -83.1,
  date: "2024-03-04",
  location_name: "Test location",
  species: `Species ${id}`,
  severity: null,
  source: "NOAA NCEI HABSOS",
  source_record_id: `HABSOS-${id}`,
  description: "Source category: test category",
  chlorophyll_a: null,
  sea_surface_temperature: null,
  sample_water_temperature: null,
  turbidity: null,
  wind_speed: null,
  risk_score: null,
  risk_level: null,
  confidence: null,
  created_at: "2024-03-05T12:34:56+00:00",
  ...overrides,
});

const riskFeature = (sourceType, properties = {}, coordinates = [-83.1, 27.5]) => ({
  type: "Feature",
  geometry: { type: "Point", coordinates },
  properties: { source_type: sourceType, ...properties },
});

let container;
let root;

async function flushAsyncWork() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

async function renderMap() {
  await act(async () => root.render(<MapView />));
  await flushAsyncWork();
}

function changeInput(input, value) {
  const valueSetter = Object.getOwnPropertyDescriptor(input.constructor.prototype, "value").set;
  valueSetter.call(input, value);
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
}

beforeEach(() => {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  getHealth.mockResolvedValue({ database: "connected", postgis: "available", prediction_model: "available" });
  getRiskMap.mockResolvedValue({ type: "FeatureCollection", features: [] });
  getEvents.mockResolvedValue([]);
});

afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  jest.clearAllMocks();
});

describe("Risk Map record provenance and grouped markers", () => {
  test("distinguishes sources, shows missing values honestly, and labels known versus unknown assessment provenance", async () => {
    getEvents.mockResolvedValue([
      event(1, { location_name: "Development Sample Location 1 (Tampa Bay Offshore)" }),
    ]);
    getRiskMap.mockResolvedValue({
      type: "FeatureCollection",
      features: [
        riskFeature("stored_risk_assessment", {
          risk_assessment_id: 10,
          location_name: "Development Sample Location 1 (Tampa Bay Offshore)",
          risk_score: null,
          risk_level: null,
          hab_probability: null,
          chlorophyll_a: null,
          sst_anomaly: null,
          date: "2024-03-04",
          detected_at: "2024-03-04T12:13:14+00:00",
        }),
        riskFeature("model_prediction", {
          prediction_id: 20,
          location_name: null,
          risk_score: null,
          risk_level: null,
          hab_probability: null,
          date: "2024-03-04",
        }),
        riskFeature("stored_risk_assessment", {
          risk_assessment_id: 11,
          location_name: "Unclassified location",
          risk_score: 0,
          risk_level: null,
          hab_probability: null,
          date: "2024-03-04",
          detected_at: "2024-03-04T13:13:14+00:00",
        }, [-82.9, 27.4]),
      ],
    });

    await renderMap();

    expect(container.textContent).toContain("HABSOS source observation");
    expect(container.textContent).toContain("Stored risk assessment");
    expect(container.textContent).toContain("Model prediction");
    expect(container.textContent).toContain("bloom confirmation status unavailable");
    expect(container.textContent).toContain("Development/test seed sample");
    expect(container.textContent).toContain("Assessment provenance: Unavailable from the risk-map API");
    expect(container.textContent).toContain("Assessment timestamp: 2024-03-04T12:13:14+00:00");
    expect(container.textContent).toContain("Prediction date (date only): 2024-03-04");
    expect(container.textContent).toContain("Prediction timestamp: Unavailable from the risk-map API");
    expect(container.textContent).toContain("Severity: Unavailable");
    expect(container.textContent).toContain("Risk Score: Unavailable");
    expect(container.textContent).toContain("HAB Probability: Unavailable");
    expect(container.textContent).toContain("Chlorophyll-a: Unavailable");
    expect(container.textContent).toContain("SST Anomaly: Unavailable");
    expect(container.textContent).toContain("Source category/details: Source category: test category");
    expect(container.textContent).toContain("Risk Score: 0 / 100");
    expect(container.querySelectorAll('[data-testid="map-marker"]')).toHaveLength(2);

    const sharedMarker = container.querySelector('[data-position="[27.5,-83.1]"]');
    expect(sharedMarker).not.toBeNull();
    expect(sharedMarker.textContent).toContain("Species 1");
    expect(sharedMarker.textContent).toContain("Assessment ID: 10");
    expect(sharedMarker.textContent).toContain("Prediction ID: 20");
  });
});

describe("Risk Map observation pagination", () => {
  test("loads the next page, removes an overlapping ID only, and retains all other records", async () => {
    const firstPage = Array.from({ length: 200 }, (_, index) => event(index + 1));
    getEvents
      .mockResolvedValueOnce(firstPage)
      .mockResolvedValueOnce([event(200, { species: "Duplicate page row" }), event(201), event(202)]);

    await renderMap();
    expect(container.textContent).toContain("HABSOS observations loaded: 200");
    expect(container.querySelectorAll('[data-testid="map-marker"]')).toHaveLength(1);
    expect(container.querySelector('[data-testid="map-marker"]').getAttribute("data-icon-html")).toContain(">200</span>");

    const moreButton = Array.from(container.querySelectorAll("button")).find((button) => button.textContent === "Load more observations");
    await act(async () => {
      Simulate.click(moreButton);
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(getEvents).toHaveBeenLastCalledWith({ limit: 200, offset: 200 });
    expect(container.textContent).toContain("HABSOS observations loaded: 202");
    expect(container.textContent).toContain("Species 1");
    expect(container.textContent).toContain("Species 201");
    expect(container.textContent).toContain("Species 202");
    expect(container.textContent).not.toContain("Duplicate page row");
    expect(container.querySelector('[data-testid="map-marker"]').getAttribute("data-icon-html")).toContain(">202</span>");
  });
});

describe("Risk Map filters", () => {
  test("sends valid date and bounds with supported risk-map and event parameter names", async () => {
    await renderMap();

    await act(async () => {
      changeInput(container.querySelector("#risk-map-date"), "2024-03-04");
      changeInput(container.querySelector("#risk-map-bbox"), "-84, 27, -82, 29");
      Simulate.submit(container.querySelector("form"));
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(getRiskMap).toHaveBeenLastCalledWith({ date: "2024-03-04", bbox: "-84,27,-82,29" });
    expect(getEvents).toHaveBeenLastCalledWith({
      limit: 200,
      offset: 0,
      date_from: "2024-03-04",
      date_to: "2024-03-04",
      min_lon: -84,
      min_lat: 27,
      max_lon: -82,
      max_lat: 29,
    });
  });

  test("rejects invalid bounding boxes without making filtered requests", async () => {
    await renderMap();
    const initialRiskCalls = getRiskMap.mock.calls.length;
    const initialEventCalls = getEvents.mock.calls.length;

    await act(async () => {
      changeInput(container.querySelector("#risk-map-bbox"), "-80, 27, -84, 29");
      Simulate.submit(container.querySelector("form"));
    });

    expect(container.textContent).toContain("Minimum bounds must not exceed maximum bounds.");
    expect(getRiskMap).toHaveBeenCalledTimes(initialRiskCalls);
    expect(getEvents).toHaveBeenCalledTimes(initialEventCalls);
  });

  test("clears filters and reloads the unfiltered view", async () => {
    await renderMap();
    await act(async () => {
      changeInput(container.querySelector("#risk-map-date"), "2024-03-04");
      Simulate.submit(container.querySelector("form"));
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    const clearButton = Array.from(container.querySelectorAll("button")).find((button) => button.textContent === "Clear filters");
    await act(async () => {
      Simulate.click(clearButton);
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(getRiskMap).toHaveBeenLastCalledWith({ date: null, bbox: null });
    expect(getEvents).toHaveBeenLastCalledWith({ limit: 200, offset: 0 });
  });
});

test("shows loading, retry, and end-of-results states for observation pages", async () => {
  let finishFirstRequest;
  const firstPage = Array.from({ length: 200 }, (_, index) => event(index + 1));
  getEvents.mockReturnValueOnce(new Promise((resolve) => { finishFirstRequest = resolve; }));
  await act(async () => root.render(<MapView />));

  expect(container.textContent).toContain("Loading observations…");
  await act(async () => {
    finishFirstRequest(firstPage);
    await new Promise((resolve) => setTimeout(resolve, 0));
  });

  getEvents.mockRejectedValueOnce(new Error("temporarily unavailable")).mockResolvedValueOnce([]);
  await act(async () => {
    Simulate.click(Array.from(container.querySelectorAll("button")).find((button) => button.textContent === "Load more observations"));
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
  expect(container.textContent).toContain("temporarily unavailable");
  expect(container.textContent).toContain("Retry loading observations");

  await act(async () => {
    Simulate.click(Array.from(container.querySelectorAll("button")).find((button) => button.textContent === "Retry loading observations"));
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
  expect(container.textContent).toContain("All available observations are loaded.");
});

test("shows the empty end-of-results state when the first observation page is empty", async () => {
  getEvents.mockResolvedValue([]);
  await renderMap();
  expect(container.textContent).toContain("HABSOS observations loaded: 0");
  expect(container.textContent).toContain("No observations available.");
});
