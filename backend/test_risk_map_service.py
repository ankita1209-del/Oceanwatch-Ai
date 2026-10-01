"""Quick test script for get_current_risk_map() service."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.risk_map import get_current_risk_map

async def main():
    records = await get_current_risk_map()
    print(f"Total records returned: {len(records)}")
    for r in records:
        print(
            f"  {r['location_name']}: "
            f"score={r['risk_score']}, level={r['risk_level']}, "
            f"lat={r['lat']}, lon={r['lon']}, "
            f"chl={r['chlorophyll_a']}, sst={r['sst_anomaly']}, "
            f"detected_at={r['detected_at']}"
        )
    # Verify latest-only logic: Location 1 has 3 records (scores 22, 48, 76). Must return 76.
    loc1 = [r for r in records if "Location 1" in r["location_name"]]
    if loc1:
        assert loc1[0]["risk_score"] == 76.0, f"Expected 76.0, got {loc1[0]['risk_score']}"
        print("\n[PASS] Latest-record-only logic verified: Location 1 returned score=76.0 (not 22 or 48)")
    else:
        print("\n[WARN] Location 1 not found in results")

asyncio.run(main())
