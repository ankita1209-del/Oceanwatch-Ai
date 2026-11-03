import api, { apiFailureMessage, getEvents, uploadSatelliteImage } from "./api";

jest.mock("axios", () => ({
  create: jest.fn(() => ({ get: jest.fn(), post: jest.fn() })),
}));

test("forwards supported event pagination, date, and geographic parameters", async () => {
  api.get.mockResolvedValue({ data: [] });

  await getEvents({
    limit: 200,
    offset: 400,
    date_from: "2024-03-04",
    date_to: "2024-03-04",
    min_lon: -84,
    min_lat: 27,
    max_lon: -82,
    max_lat: 29,
  });

  expect(api.get).toHaveBeenCalledWith("/api/events", {
    params: {
      limit: 200,
      offset: 400,
      date_from: "2024-03-04",
      date_to: "2024-03-04",
      min_lon: -84,
      min_lat: 27,
      max_lon: -82,
      max_lat: 29,
    },
  });
});

test("explains an API route 404 instead of showing the backend's bare Not Found", () => {
  expect(
    apiFailureMessage({
      response: { status: 404, data: { detail: "Not Found" } },
    })
  ).toMatch(/API endpoint was not found/);
});

test("preserves safe backend messages for missing satellite resources", () => {
  expect(
    apiFailureMessage({
      response: {
        status: 404,
        data: { detail: "Uploaded satellite image was not found or has expired." },
      },
    })
  ).toBe("Uploaded satellite image was not found or has expired.");
});

test("reports validation, upload-size, server, and timeout errors clearly", () => {
  expect(
    apiFailureMessage({
      response: { status: 422, data: { detail: { message: "CIcyano band is missing." } } },
    })
  ).toBe("CIcyano band is missing.");
  expect(
    apiFailureMessage({
      response: { status: 422, data: { detail: [{ msg: "Field required" }] } },
    })
  ).toBe("Field required");
  expect(apiFailureMessage({ response: { status: 413, data: {} } })).toMatch(/100 MiB/);
  expect(
    apiFailureMessage({
      response: { status: 500, data: { detail: "internal traceback" } },
    })
  ).toMatch(/check the server logs/);
  expect(apiFailureMessage({ code: "ECONNABORTED", message: "timeout exceeded" })).toMatch(
    /timed out/
  );
  expect(apiFailureMessage({ message: "Network Error" })).toMatch(/Cannot connect/);
});

test("uploads a file as FormData without overriding its multipart boundary", async () => {
  const file = new File(["raster"], "scene.tif", { type: "image/tiff" });
  api.post.mockResolvedValue({ data: { file_id: "a".repeat(32) } });

  const response = await uploadSatelliteImage(file);

  expect(response.file_id).toBe("a".repeat(32));
  expect(api.post).toHaveBeenCalledWith(
    "/api/satellite-detection/upload",
    expect.any(FormData),
    { timeout: 120000 }
  );
  expect(api.post.mock.calls[0][1].get("file")).toBe(file);
});
