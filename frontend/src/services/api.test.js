import api, { getEvents } from "./api";

jest.mock("axios", () => ({
  create: jest.fn(() => ({ get: jest.fn() })),
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
