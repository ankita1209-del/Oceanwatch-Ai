from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import rasterio
from httpx import ASGITransport, AsyncClient
from affine import Affine
from rasterio.transform import from_origin
from rasterio.transform import array_bounds, rowcol, xy
from rasterio.warp import transform_bounds
from pyproj import Transformer
from PIL import Image

from backend.main import app
from backend.routes import satellite_detection as satellite_route
from backend.services import satellite_processor
from backend.services.satellite_processor import analyze_ci_cyano
from backend.services.satellite_validator import (
    SatelliteValidationError,
    inspect_satellite_raster,
)

QUALITY_TAGS = {
    "SAPS_product_flag_saturated": "250",
    "SAPS_product_flag_ci_adj": "251",
    "SAPS_product_flag_land": "252",
    "SAPS_product_flag_cloud": "253",
    "SAPS_product_flag_mixed_pixel": "254",
    "SAPS_product_flag_nodata": "255",
    "SAPS_product_flag_nodetect": "0",
}
TEST_CRS_WKT = (
    'PROJCS["WGS 84 / UTM zone 17N",GEOGCS["WGS 84",DATUM["World Geodetic System 1984",'
    'SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],'
    'UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]]],'
    'PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],'
    'PARAMETER["central_meridian",-81],PARAMETER["scale_factor",0.9996],'
    'PARAMETER["false_easting",500000],PARAMETER["false_northing",0],'
    'UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH]]'
)


def _raster_bytes(
    values: np.ndarray,
    *,
    crs: str | None = TEST_CRS_WKT,
    description: str = "CIcyano",
    product_source: str = "sentinel-3.test.v9110V20255_2.tif",
    count: int = 1,
    nodata: int | None = 255,
    scale_formula: str | None = "10**(3.0 / 250.0 * DN - 4.2)",
    transform=None,
) -> bytes:
    height, width = values.shape[-2:]
    output = BytesIO()
    bundled_proj_data = Path(rasterio.__file__).parent / "proj_data"
    with patch.dict(
        os.environ,
        {"PROJ_DATA": str(bundled_proj_data), "PROJ_LIB": str(bundled_proj_data)},
    ):
        with rasterio.open(
            output,
            "w",
            driver="GTiff",
            width=width,
            height=height,
            count=count,
            dtype="uint8",
            crs=crs,
            transform=transform or from_origin(500000, 4500000, 300, 300),
            nodata=nodata,
        ) as dataset:
            data = np.repeat(values[np.newaxis, ...], count, axis=0) if values.ndim == 2 else values
            dataset.write(data.astype(np.uint8))
            tags = {
                "TIFFTAG_IMAGEDESCRIPTION": description,
                "SAPS_product_name": description,
                "SAPS_product_version": "1.5",
                "SAPS_product_type": "standard_prod",
                "SAPS_product_desc": "Chlorophyll Cyanobacteria Index - cyano only",
                "SAPS_product_src": product_source,
                **QUALITY_TAGS,
            }
            if scale_formula is not None:
                tags["SAPS_product_rev_scaling"] = scale_formula
            dataset.update_tags(
                **tags,
            )
    return output.getvalue()


async def _post_upload(client: AsyncClient, filename: str, payload: bytes):
    return await client.post(
        "/api/satellite-detection/upload",
        files={"file": (filename, payload, "image/tiff")},
    )


@pytest.fixture
def upload_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(satellite_route, "UPLOAD_DIRECTORY", tmp_path / "satellite-uploads")
    return tmp_path / "satellite-uploads"


@pytest.mark.asyncio
async def test_upload_analyze_result_and_georeferenced_outputs(upload_directory):
    values = np.array(
        [
            [0, 1, 2, 3, 4],
            [5, 6, 7, 8, 9],
            [10, 11, 12, 100, 253],
            [252, 251, 254, 255, 1],
        ],
        dtype=np.uint8,
    )
    payload = _raster_bytes(values)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        uploaded = await _post_upload(client, "sentinel-3-test-CIcyano-v9110V20255_2.tif", payload)
        assert uploaded.status_code == 200, uploaded.text
        upload_data = uploaded.json()
        file_id = upload_data["file_id"]
        assert upload_data["validation"]["status"] == "VALID_WITH_WARNINGS"
        assert upload_data["validation"]["band_count"] == 1
        assert upload_data["validation"]["spatial_resolution"] == [300, 300]
        assert upload_data["validation"]["valid_pixel_percentage"] == 75

        validation = await client.get(f"/api/satellite-detection/validate/{file_id}")
        assert validation.status_code == 200

        analyzed = await client.post(f"/api/satellite-detection/analyze/{file_id}")
        assert analyzed.status_code == 200
        result = analyzed.json()
        analysis_id = result["analysis_id"]
        assert result["hab_detection"]["hab_probability"] is None
        assert result["hab_detection"]["risk_score"] is None
        assert result["hab_detection"]["risk_level"] is None
        assert result["hab_detection"]["model"]["status"] in {
            "not_run",
            "experimental",
        }
        assert result["hab_detection"]["model"]["inference_ran"] == (
            result["hab_detection"]["model"]["status"] == "experimental"
        )
        assert result["analysis"]["possible_hab_indicator"] is None
        assert result["analysis"]["indicator_hotspots_found"] is True
        assert result["analysis"]["threshold_source"].startswith("Scene-specific Tukey upper fence")
        assert result["analysis"]["high_indicator_pixel_percentage"] > 0
        assert result["analysis"]["invalid_pixel_count"] == 5
        assert result["analysis"]["standard_deviation_indicator"] is not None
        assert set(result["analysis"]["percentiles"]) == {
            "p25", "p50", "p75", "p90", "p95", "p99"
        }
        assert result["display"]["crs"] == "EPSG:3857"
        assert result["display"]["indicator_resampling"] == "bilinear"
        assert result["display"]["hotspot_mask_resampling"] == "nearest"
        assert result["quality"]["cloud_percentage"] == 5
        assert result["bounds"]["min_longitude"] < result["bounds"]["max_longitude"]
        assert result["bounds"]["min_latitude"] < result["bounds"]["max_latitude"]
        assert result["analysis"]["mean_indicator"] == pytest.approx(
            np.mean(
                np.where(
                    values[values <= 249] == 0,
                    0,
                    10 ** (3.0 / 250.0 * values[values <= 249] - 4.2),
                )
            )
        )

        fetched = await client.get(f"/api/satellite-detection/result/{analysis_id}")
        overlay = await client.get(f"/api/satellite-detection/result/{analysis_id}/overlay")
        indicator = await client.get(f"/api/satellite-detection/result/{analysis_id}/indicator")
        mask = await client.get(f"/api/satellite-detection/result/{analysis_id}/mask")
        assert fetched.status_code == overlay.status_code == 200
        assert overlay.headers["content-type"] == "image/png"
        assert indicator.content[:4] in {b"II*\x00", b"MM\x00*"}
        assert mask.content[:4] in {b"II*\x00", b"MM\x00*"}
        assert (upload_directory / f"{analysis_id}-overlay.png").is_file()


@pytest.mark.asyncio
async def test_rejects_unsupported_extension_corrupt_raster_and_oversized_upload(
    upload_directory, monkeypatch
):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        extension = await client.post(
            "/api/satellite-detection/upload",
            files={"file": ("image.png", b"not a tiff", "image/png")},
        )
        corrupt = await _post_upload(client, "bad.tif", b"not a TIFF")
        assert extension.status_code == 415
        assert corrupt.status_code == 422
        assert corrupt.json()["detail"]["status"] == "INVALID_RASTER"

        monkeypatch.setattr(satellite_route, "MAX_UPLOAD_BYTES", 8)
        oversized = await _post_upload(client, "large.tif", b"0123456789")
        oversized_request = await client.post(
            "/api/satellite-detection/upload",
            content=b"small",
            headers={
                "content-type": "multipart/form-data; boundary=unused",
                "content-length": str(102 * 1024 * 1024),
            },
        )
        assert oversized.status_code == 413
        assert oversized_request.status_code == 413
        assert not list(upload_directory.glob("*.tif"))


@pytest.mark.asyncio
async def test_validation_reports_missing_crs_bands_and_unsupported_sensor(upload_directory):
    valid_values = np.arange(1, 17, dtype=np.uint8).reshape(4, 4)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        missing_crs = await _post_upload(
            client,
            "sentinel-3-test-CIcyano-v9110V20255_2.tif",
            _raster_bytes(valid_values, crs=None),
        )
        rgb = await _post_upload(
            client,
            "sentinel-3-test-CIcyano-v9110V20255_2.tif",
            _raster_bytes(np.repeat(valid_values[np.newaxis, ...], 3, axis=0), count=3),
        )
        unsupported = await _post_upload(
            client,
            "unknown-CIcyano-v9110V20255_2.tif",
            _raster_bytes(valid_values, product_source="unknown-product.tif"),
        )
    assert missing_crs.status_code == 422
    assert missing_crs.json()["detail"]["status"] == "INVALID_CRS"
    assert rgb.status_code == 422
    assert rgb.json()["detail"]["status"] == "MISSING_REQUIRED_BANDS"
    assert unsupported.status_code == 422
    assert unsupported.json()["detail"]["status"] == "UNSUPPORTED_SENSOR"


def test_validator_rejects_empty_valid_pixel_raster(tmp_path):
    path = tmp_path / "sentinel-3-test-CIcyano-v9110V20255_2.tif"
    path.write_bytes(_raster_bytes(np.full((4, 4), 255, dtype=np.uint8)))
    with pytest.raises(SatelliteValidationError) as error:
        inspect_satellite_raster(path, path.name)
    assert error.value.status == "INSUFFICIENT_VALID_PIXELS"


def test_validator_does_not_accept_a_product_version_prefix_lookalike(tmp_path):
    path = tmp_path / "sentinel-3-version-lookalike.tif"
    path.write_bytes(
        _raster_bytes(
            np.arange(1, 17, dtype=np.uint8).reshape(4, 4),
            product_source="sentinel-3.test.v9110V20255_20.tif",
        )
    )

    with pytest.raises(SatelliteValidationError) as error:
        inspect_satellite_raster(path, path.name)

    assert error.value.status == "UNSUPPORTED_PRODUCT_VERSION"


def test_processor_uses_quality_codes_and_preserves_georeferencing(tmp_path):
    values = np.array(
        [
            [0, 1, 2, 3],
            [4, 5, 6, 7],
            [8, 9, 100, 253],
            [252, 251, 254, 255],
        ],
        dtype=np.uint8,
    )
    source_path = tmp_path / "sentinel-3-test-CIcyano-v9110V20255_2.tif"
    source_path.write_bytes(_raster_bytes(values))
    metadata = inspect_satellite_raster(source_path, source_path.name)
    metadata["filename"] = source_path.name

    result = analyze_ci_cyano(source_path, "a" * 32, tmp_path, metadata)

    assert result["analysis"]["valid_pixel_count"] == 11
    assert result["analysis"]["invalid_pixel_count"] == 5
    assert result["quality"]["coverage_category"] == "BETTER_COVERAGE"
    assert result["quality"]["quality_pixel_counts"]["cloud"] == 1
    assert result["analysis"]["indicator_hotspots_found"] is True
    assert result["analysis"]["indicator_units"] == "dimensionless CIcyano index"
    with rasterio.open(tmp_path / f"{'a' * 32}-indicator.tif") as indicator:
        assert indicator.crs.to_string() == "EPSG:32617"
        assert indicator.transform == rasterio.transform.from_origin(500000, 4500000, 300, 300)
        assert indicator.tags()["scale_formula"] == "10**(3.0 / 250.0 * DN - 4.2)"
        indicator_values = indicator.read(1)
        assert indicator_values[0, 0] == 0.0
        assert np.all(indicator_values[[2, 3], 3] == -9999.0)
    with rasterio.open(tmp_path / f"{'a' * 32}-mask.tif") as hotspot_mask:
        mask_values = hotspot_mask.read(1)
        assert set(np.unique(mask_values)).issubset({0, 1, 255})
        assert mask_values[0, 0] in {0, 1}
        assert mask_values[2, 3] == 255
    with pytest.raises(TimeoutError):
        analyze_ci_cyano(
            source_path,
            "c" * 32,
            tmp_path,
            metadata,
            timeout_seconds=-1,
        )
    assert not (tmp_path / f"{'c' * 32}-indicator.tif").exists()
    assert not (tmp_path / f"{'c' * 32}-mask.tif").exists()
    assert not (tmp_path / f"{'c' * 32}-overlay.png").exists()


@pytest.mark.parametrize(
    ("valid_count", "expected_category", "expected_status", "screening_permitted"),
    [
        (0, "NO_VALID_PIXELS", "NO_VALID_PIXELS", False),
        (9, "INSUFFICIENT_COVERAGE", "INSUFFICIENT_COVERAGE", False),
        (10, "LOW_COVERAGE", "RELATIVE_HOTSPOTS_DETECTED", True),
        (24, "LOW_COVERAGE", "RELATIVE_HOTSPOTS_DETECTED", True),
        (25, "MODERATE_COVERAGE", "RELATIVE_HOTSPOTS_DETECTED", True),
        (50, "BETTER_COVERAGE", "RELATIVE_HOTSPOTS_DETECTED", True),
        (51, "BETTER_COVERAGE", "RELATIVE_HOTSPOTS_DETECTED", True),
    ],
)
def test_coverage_categories_and_threshold_behavior(
    tmp_path, valid_count, expected_category, expected_status, screening_permitted
):
    values = np.full((10, 10), 255, dtype=np.uint8)
    if valid_count:
        values.flat[:valid_count] = 1
        values.flat[valid_count - 1] = 249
    source_path = tmp_path / f"coverage-{valid_count}.tif"
    source_path.write_bytes(_raster_bytes(values))
    metadata = {
        "filename": source_path.name,
        "sensor": "Sentinel-3 OLCI",
        "product_type": "CIcyano",
        "product_version": "v9110V20255_2",
        "acquisition_date": None,
        "crs": "EPSG:32617",
        "bounds": {},
        "spatial_resolution": [300, 300],
        "band_count": 1,
        "band_descriptions": [None],
        "valid_pixel_percentage": valid_count,
        "indicator_units": "dimensionless CIcyano index",
        "scale_formula": "10**(3.0 / 250.0 * DN - 4.2)",
        "warnings": [],
    }

    result = analyze_ci_cyano(
        source_path, f"{valid_count:032x}", tmp_path, metadata
    )
    analysis = result["analysis"]
    quality = result["quality"]

    assert analysis["screening_status"] == expected_status
    assert analysis["coverage_category"] == expected_category
    assert quality["coverage_category"] == expected_category
    assert quality["valid_pixel_percentage"] == pytest.approx(valid_count)
    assert analysis["valid_pixel_count"] == valid_count
    assert analysis["invalid_pixel_count"] == 100 - valid_count

    if screening_permitted:
        assert analysis["threshold"] is not None
        assert analysis["hotspot_pixel_count"] == 1
        assert analysis["hotspot_pixel_percentage"] == pytest.approx(100 / valid_count)
        if expected_category == "LOW_COVERAGE":
            assert any("may be unstable" in warning for warning in quality["warnings"])
    else:
        assert analysis["threshold"] is None
        assert analysis["hotspot_pixel_count"] is None
        assert analysis["hotspot_pixel_percentage"] is None
        assert analysis["indicator_hotspots_found"] is None
        assert any("screening was not performed" in warning for warning in quality["warnings"])
        with rasterio.open(tmp_path / f"{valid_count:032x}-mask.tif") as mask:
            assert set(np.unique(mask.read(1))) == {255}
        with rasterio.open(tmp_path / f"{valid_count:032x}-indicator.tif") as indicator:
            indicator_values = indicator.read(1)
            assert np.count_nonzero(indicator_values != -9999.0) == valid_count
        if valid_count:
            overlay = np.asarray(
                Image.open(
                    tmp_path / f"{valid_count:032x}-overlay.png"
                ).convert("RGBA")
            )
            assert np.any(overlay[:, :, 3] > 0)


@pytest.mark.parametrize(
    ("product_name", "band_count"),
    [
        ("truecolor", 3),
        ("landwatercolor", 3),
        ("CI", 1),
        ("CInonfluor", 1),
        ("Kd_Rhos", 1),
        ("CI-CIcyano", 1),
        ("rbd_rhos", 1),
        ("rrs665", 1),
        ("chloc4_global", 1),
        ("chl_switch", 1),
    ],
)
@pytest.mark.asyncio
async def test_supported_preview_products_return_unavailable_hab_metrics(
    upload_directory, product_name, band_count
):
    values = np.arange(
        1, band_count * 16 + 1, dtype=np.uint8
    ).reshape((band_count, 4, 4))
    payload = _raster_bytes(
        values,
        description=product_name,
        count=band_count,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        uploaded = await _post_upload(
            client,
            f"sentinel-3-test-{product_name}.tif",
            payload,
        )
        assert uploaded.status_code == 200, uploaded.text
        file_id = uploaded.json()["file_id"]

        analyzed = await client.post(
            f"/api/satellite-detection/analyze/{file_id}"
        )

    assert analyzed.status_code == 200, analyzed.text
    result = analyzed.json()
    assert result["hab_detection"]["hab_probability"] is None
    assert result["hab_detection"]["risk_score"] is None
    assert result["hab_detection"]["risk_level"] is None
    assert result["outputs"]["preview_url"]


@pytest.mark.asyncio
async def test_insufficient_ci_cyano_coverage_is_reported_in_analysis(
    upload_directory,
):
    values = np.full((10, 10), 255, dtype=np.uint8)
    values.flat[:9] = np.arange(1, 10, dtype=np.uint8)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        uploaded = await _post_upload(
            client,
            "sentinel-3-low-coverage-CIcyano-v9110V20255_2.tif",
            _raster_bytes(values),
        )
        assert uploaded.status_code == 200, uploaded.text
        file_id = uploaded.json()["file_id"]

        analyzed = await client.post(
            f"/api/satellite-detection/analyze/{file_id}"
        )

    assert analyzed.status_code == 200, analyzed.text
    result = analyzed.json()
    assert result["quality"]["coverage_category"] == "INSUFFICIENT_COVERAGE"
    assert result["hab_detection"]["hab_probability"] is None
    assert result["hab_detection"]["model"]["inference_ran"] is False
    assert "insufficient" in result["hab_detection"]["reasons"][
        "hab_probability"
    ].lower()


def test_low_coverage_without_hotspots_still_reports_no_relative_hotspots(tmp_path):
    values = np.full((10, 10), 255, dtype=np.uint8)
    values.flat[:10] = 1
    source_path = tmp_path / "low-coverage-no-hotspots.tif"
    source_path.write_bytes(_raster_bytes(values))
    metadata = {
        "filename": source_path.name,
        "sensor": "Sentinel-3 OLCI",
        "product_type": "CIcyano",
        "product_version": "v9110V20255_2",
        "acquisition_date": None,
        "crs": "EPSG:32617",
        "bounds": {},
        "spatial_resolution": [300, 300],
        "band_count": 1,
        "band_descriptions": [None],
        "indicator_units": "dimensionless CIcyano index",
        "scale_formula": "10**(3.0 / 250.0 * DN - 4.2)",
        "warnings": [],
    }

    result = analyze_ci_cyano(source_path, "1" * 32, tmp_path, metadata)

    assert result["analysis"]["screening_status"] == "NO_RELATIVE_HOTSPOTS"
    assert result["analysis"]["threshold"] is not None
    assert result["analysis"]["hotspot_pixel_count"] == 0
    assert result["analysis"]["hotspot_pixel_percentage"] == 0
    assert any("Low valid-pixel coverage" in warning for warning in result["quality"]["warnings"])


def test_failure_during_overlay_generation_cleans_all_analysis_outputs(tmp_path, monkeypatch):
    source_path = tmp_path / "overlay-failure.tif"
    source_path.write_bytes(
        _raster_bytes(np.arange(1, 17, dtype=np.uint8).reshape(4, 4))
    )
    metadata = inspect_satellite_raster(source_path, source_path.name)
    metadata["filename"] = source_path.name
    analysis_id = "2" * 32

    def fail_overlay(*args, **kwargs):
        raise ValueError("synthetic display failure")

    monkeypatch.setattr(satellite_processor, "_create_display_overlay", fail_overlay)
    with pytest.raises(ValueError, match="synthetic display failure"):
        analyze_ci_cyano(source_path, analysis_id, tmp_path, metadata)

    for suffix in ("-indicator.tif", "-mask.tif", "-overlay.png"):
        assert not (tmp_path / f"{analysis_id}{suffix}").exists()


@pytest.mark.parametrize(
    ("formula", "expected_status"),
    [
        (None, "MISSING_SCALING_METADATA"),
        ("10**(2.0 / 250.0 * DN - 4.2)", "UNSUPPORTED_SCALING"),
        ("10**(3.0 / 250.0 * DN -", "MALFORMED_SCALING_METADATA"),
    ],
)
def test_validator_rejects_missing_unsupported_and_malformed_scaling(
    tmp_path, formula, expected_status
):
    path = tmp_path / "sentinel-3-test-CIcyano-v9110V20255_2.tif"
    path.write_bytes(_raster_bytes(np.arange(1, 17, dtype=np.uint8).reshape(4, 4), scale_formula=formula))

    with pytest.raises(SatelliteValidationError) as error:
        inspect_satellite_raster(path, path.name)

    assert error.value.status == expected_status


def test_scaled_statistics_use_scaled_valid_pixels_and_mask_quality_codes(tmp_path):
    values = np.array([[0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 249, 250, 255]], dtype=np.uint8)
    source_path = tmp_path / "sentinel-3-boundary-CIcyano-v9110V20255_2.tif"
    source_path.write_bytes(_raster_bytes(values))
    metadata = inspect_satellite_raster(source_path, source_path.name)
    metadata["filename"] = source_path.name

    result = analyze_ci_cyano(source_path, "d" * 32, tmp_path, metadata)

    scaled = np.array(
        [0.0]
        + [10 ** (3.0 / 250.0 - 4.2)] * 9
        + [10 ** (3.0 / 250.0 * 249 - 4.2)]
    )
    analysis = result["analysis"]
    assert analysis["valid_pixel_count"] == 11
    assert analysis["invalid_pixel_count"] == 2
    assert analysis["minimum_indicator"] == pytest.approx(scaled.min())
    assert analysis["maximum_indicator"] == pytest.approx(scaled.max())
    assert analysis["mean_indicator"] == pytest.approx(scaled.mean())
    assert analysis["median_indicator"] == pytest.approx(np.median(scaled))
    assert analysis["standard_deviation_indicator"] == pytest.approx(np.std(scaled))
    assert analysis["percentiles"]["p25"] == pytest.approx(np.percentile(scaled, 25))
    assert analysis["percentiles"]["p50"] == pytest.approx(np.percentile(scaled, 50))
    assert analysis["percentiles"]["p75"] == pytest.approx(np.percentile(scaled, 75))
    assert analysis["hotspot_pixel_count"] == 1
    assert analysis["threshold"] == pytest.approx(
        np.percentile(scaled, 75)
        + 1.5 * (np.percentile(scaled, 75) - np.percentile(scaled, 25))
    )
    with rasterio.open(source_path) as source, rasterio.open(
        tmp_path / f"{'d' * 32}-indicator.tif"
    ) as indicator:
        assert source.read(1).tolist() == values.tolist()
        output_values = indicator.read(1)[0]
        assert output_values[0] == pytest.approx(0.0)
        assert output_values[1] == pytest.approx(scaled[1], rel=1e-6)
        assert output_values[10] == pytest.approx(scaled[-1], rel=1e-6)
        assert output_values[11] == -9999.0
        assert output_values[12] == -9999.0


@pytest.mark.parametrize(
    ("crs", "transform"),
    [
        (TEST_CRS_WKT, from_origin(500000, 4500000, 300, 300)),
        ("EPSG:4326", from_origin(-81.0, 27.0, 0.01, 0.01)),
    ],
)
def test_display_overlay_is_reprojected_without_flipping_or_interpolating_mask(
    tmp_path, crs, transform
):
    values = np.arange(1, 21, dtype=np.uint8).reshape(4, 5)
    values[0, 4] = 249
    values[1, 1] = 255
    source_path = tmp_path / "sentinel-3-asymmetric-CIcyano-v9110V20255_2.tif"
    source_path.write_bytes(_raster_bytes(values, crs=crs, transform=transform))
    metadata = inspect_satellite_raster(source_path, source_path.name)
    metadata["filename"] = source_path.name
    analysis_id = "e" * 32

    result = analyze_ci_cyano(source_path, analysis_id, tmp_path, metadata)
    display = result["display"]
    display_transform = Affine(*display["transform"][:6])
    overlay = np.asarray(
        Image.open(tmp_path / f"{analysis_id}-overlay.png").convert("RGBA")
    )

    with rasterio.open(source_path) as source, rasterio.open(
        tmp_path / f"{analysis_id}-mask.tif"
    ) as hotspot_mask:
        transformer = Transformer.from_crs(source.crs, "EPSG:3857", always_xy=True)
        hotspot_x, hotspot_y = xy(source.transform, 0, 4, offset="center")
        hotspot_map_x, hotspot_map_y = transformer.transform(hotspot_x, hotspot_y)
        hotspot_row, hotspot_col = rowcol(display_transform, hotspot_map_x, hotspot_map_y)
        invalid_x, invalid_y = xy(source.transform, 1, 1, offset="center")
        invalid_map_x, invalid_map_y = transformer.transform(invalid_x, invalid_y)
        invalid_row, invalid_col = rowcol(display_transform, invalid_map_x, invalid_map_y)
        assert hotspot_mask.read(1)[0, 4] == 1

        # A true upper-right source hotspot must remain at its projected position in the PNG.
        assert overlay[hotspot_row, hotspot_col, :3].tolist() == [255, 184, 61]
        assert overlay[invalid_row, invalid_col, 3] == 0
        mirrored_row = display["height"] - hotspot_row - 1
        mirrored_col = display["width"] - hotspot_col - 1
        assert overlay[mirrored_row, mirrored_col, :3].tolist() != [255, 184, 61]

        expected_bounds = transform_bounds(
            "EPSG:3857",
            "EPSG:4326",
            *array_bounds(display["height"], display["width"], display_transform),
            densify_pts=21,
        )
        actual = display["bounds"]
        assert actual["min_longitude"] == pytest.approx(expected_bounds[0])
        assert actual["min_latitude"] == pytest.approx(expected_bounds[1])
        assert actual["max_longitude"] == pytest.approx(expected_bounds[2])
        assert actual["max_latitude"] == pytest.approx(expected_bounds[3])

        # Compare Leaflet's projected ImageOverlay placement with the EPSG:3857
        # raster affine at destination cell centres (registration, not resampling error).
        image_bounds = transform_bounds(
            "EPSG:4326",
            "EPSG:3857",
            actual["min_longitude"],
            actual["min_latitude"],
            actual["max_longitude"],
            actual["max_latitude"],
            densify_pts=21,
        )
        destination_points = [
            (0, 0),
            (0, display["width"] - 1),
            (display["height"] - 1, 0),
            (display["height"] - 1, display["width"] - 1),
            (display["height"] // 2, display["width"] // 2),
        ]
        registration_errors = []
        for row, col in destination_points:
            raster_x, raster_y = display_transform @ (col + 0.5, row + 0.5)
            image_x = image_bounds[0] + (col + 0.5) / display["width"] * (
                image_bounds[2] - image_bounds[0]
            )
            image_y = image_bounds[3] - (row + 0.5) / display["height"] * (
                image_bounds[3] - image_bounds[1]
            )
            registration_errors.append(np.hypot(image_x - raster_x, image_y - raster_y))
        assert max(registration_errors) < 0.01


def test_empty_valid_pixel_statistics_are_unavailable_not_zero(tmp_path):
    source_path = tmp_path / "sentinel-3-empty-CIcyano-v9110V20255_2.tif"
    source_path.write_bytes(_raster_bytes(np.full((4, 4), 255, dtype=np.uint8)))
    metadata = {
        "filename": source_path.name,
        "sensor": "Sentinel-3 OLCI",
        "product_type": "CIcyano",
        "product_version": "v9110V20255_2",
        "acquisition_date": None,
        "crs": "EPSG:32617",
        "bounds": {},
        "spatial_resolution": [300, 300],
        "band_count": 1,
        "band_descriptions": [None],
        "valid_pixel_percentage": 0.0,
        "indicator_units": "dimensionless CIcyano index",
        "scale_formula": "10**(3.0 / 250.0 * DN - 4.2)",
        "warnings": [],
    }

    result = analyze_ci_cyano(source_path, "f" * 32, tmp_path, metadata)

    assert result["analysis"]["screening_status"] == "NO_VALID_PIXELS"
    assert result["analysis"]["valid_pixel_count"] == 0
    assert result["analysis"]["invalid_pixel_count"] == 16
    assert result["analysis"]["mean_indicator"] is None
    assert result["analysis"]["median_indicator"] is None
    assert result["analysis"]["standard_deviation_indicator"] is None
    assert result["analysis"]["threshold"] is None
    assert result["analysis"]["hotspot_pixel_percentage"] is None
    assert result["analysis"]["coverage_category"] == "NO_VALID_PIXELS"
    assert result["analysis"]["indicator_hotspots_found"] is None
    assert "not performed" in " ".join(result["quality"]["warnings"])
    assert "no valid pixels remained" in result["analysis"]["threshold_source"]


def test_backend_uses_rasterio_proj_database_and_known_utm_transform():
    bundled_proj_data = Path(rasterio.__file__).parent / "proj_data"
    assert Path(os.environ["PROJ_LIB"]) == bundled_proj_data
    transformer = Transformer.from_crs("EPSG:32617", "EPSG:4326", always_xy=True)
    longitude, latitude = transformer.transform(500000, 0)
    assert longitude == pytest.approx(-81.0, abs=1e-8)
    assert latitude == pytest.approx(0.0, abs=1e-8)


@pytest.mark.asyncio
async def test_health_and_unknown_ids_return_explicit_responses():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        health = await client.get("/api/satellite-detection/health")
        unknown = await client.get("/api/satellite-detection/validate/not-a-uuid")
        openapi = await client.get("/openapi.json")
        preflight = await client.options(
            "/api/satellite-detection/upload",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
    assert health.status_code == 200
    assert {
        "CIcyano",
        "truecolor",
        "landwatercolor",
    }.issubset(set(health.json()["supported_products"]))
    assert unknown.status_code == 404
    paths = openapi.json()["paths"]
    assert {
        "/api/satellite-detection/upload",
        "/api/satellite-detection/analyze/{file_id}",
        "/api/satellite-detection/result/{analysis_id}",
        "/api/satellite-detection/health",
    }.issubset(paths)
    assert "post" in paths["/api/satellite-detection/upload"]
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:3000"
