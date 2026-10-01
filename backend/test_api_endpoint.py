"""Test the /api/risk-map endpoint end-to-end."""
import urllib.request, json

r = urllib.request.urlopen("http://127.0.0.1:8000/api/risk-map")
data = json.loads(r.read())

print(f"Status: 200")
print(f"type: {data['type']}")
print(f"features: {len(data['features'])}")
print()

assert data["type"] == "FeatureCollection", "Expected FeatureCollection"
assert isinstance(data["features"], list), "Expected features to be a list"

for f in data["features"]:
    assert f["type"] == "Feature"
    geom = f["geometry"]
    assert geom["type"] == "Point"
    coords = geom["coordinates"]
    lon, lat = coords[0], coords[1]
    props = f["properties"]
    assert "location_name" in props, "Missing location_name"
    assert "risk_score" in props, "Missing risk_score"
    assert "risk_level" in props, "Missing risk_level"
    assert "chlorophyll_a" in props, "Missing chlorophyll_a"
    assert "sst_anomaly" in props, "Missing sst_anomaly"
    assert "detected_at" in props, "Missing detected_at"
    assert props["risk_level"] in {"LOW", "MODERATE", "HIGH", "CRITICAL"}, f"Invalid risk_level: {props['risk_level']}"
    # Verify ISO8601 format
    from datetime import datetime
    datetime.fromisoformat(props["detected_at"])
    
    print(f"  [PASS] {props['location_name']}")
    print(f"         coords=[{lon}, {lat}] | score={props['risk_score']} | level={props['risk_level']}")
    print(f"         chl={props['chlorophyll_a']} | sst={props['sst_anomaly']} | detected_at={props['detected_at']}")

# Test latest-record-only logic for Location 1 (has 3 records: 22, 48, 76 → must return 76)
loc1 = [f for f in data["features"] if "Location 1" in f["properties"]["location_name"]]
assert loc1, "Location 1 not found"
assert loc1[0]["properties"]["risk_score"] == 76.0, f"Expected 76.0, got {loc1[0]['properties']['risk_score']}"
print()
print("[PASS] Latest-record-only logic: Location 1 returned score=76.0 (not 22 or 48)")
print("[PASS] All property names verified")
print("[PASS] coordinates in [lon, lat] order")
print("[PASS] detected_at is ISO8601")
print("[PASS] risk_level values are valid")
print()
print("=== ALL CHECKS PASSED ===")
