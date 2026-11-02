"""Validation for the supported Sentinel-3 OLCI CIcyano GeoTIFF product."""

from __future__ import annotations

import math
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from pyproj.exceptions import ProjError
from rasterio.errors import RasterioError

MAX_RASTER_PIXELS = 20_000_000
MAX_RASTER_SIDE = 20_000
VALIDATION_TIMEOUT_SECONDS = 30
SUPPORTED_PRODUCT_VERSION = "v9110V20255_2"
SUPPORTED_SCALE_FORMULA = "10**(3.0 / 250.0 * DN - 4.2)"
_SCALING_EXPRESSION = re.compile(
    r"^10\s*\*\*\s*\(\s*\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?"
    r"\s*\*\s*DN\s*[-+]\s*\d+(?:\.\d+)?\s*\)$",
    re.IGNORECASE,
)
RESERVED_QUALITY_VALUES = {
    250: "saturated",
    251: "adjacency",
    252: "land",
    253: "cloud",
    254: "mixed",
    255: "nodata",
}
class SatelliteValidationError(ValueError):
    """A user-correctable error found while validating an uploaded raster."""

    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _date_from_metadata(tags: dict[str, str]) -> str | None:
    for key, value in tags.items():
        if key.lower() not in {
            "acquisition_date",
            "acquisition_datetime",
            "sensing_time",
            "date_acquired",
        }:
            continue
        candidate = value.strip()
        try:
            return datetime.fromisoformat(candidate.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            continue
    return None


def _window_iter(dataset: rasterio.io.DatasetReader):
    block_height, block_width = dataset.block_shapes[0]
    block_height = max(1, min(block_height, 512))
    block_width = max(1, min(block_width, 512))
    for row in range(0, dataset.height, block_height):
        for col in range(0, dataset.width, block_width):
            height = min(block_height, dataset.height - row)
            width = min(block_width, dataset.width - col)
            yield rasterio.windows.Window(col, row, width, height)


def _valid_product_pixels(values: np.ndarray, dataset_mask: np.ndarray) -> np.ndarray:
    return (
        (dataset_mask > 0)
        & np.isfinite(values)
        & (values >= 0)
        & (values <= 249)
    )


def inspect_satellite_raster(path: Path, original_filename: str) -> dict[str, Any]:
    """Inspect raster structure and determine whether the product is supported."""
    if Path(original_filename).suffix.lower() not in {".tif", ".tiff"}:
        raise SatelliteValidationError("INVALID_RASTER", "Only .tif and .tiff uploads are accepted.")

    try:
        dataset = rasterio.open(path)
    except (RasterioError, OSError, ValueError) as exc:
        raise SatelliteValidationError("INVALID_RASTER", "The uploaded file is not a readable GeoTIFF.") from exc

    with dataset as src:
        if src.driver != "GTiff":
            raise SatelliteValidationError("INVALID_RASTER", "The uploaded raster must use the GeoTIFF format.")
        if src.width <= 0 or src.height <= 0 or src.width > MAX_RASTER_SIDE or src.height > MAX_RASTER_SIDE:
            raise SatelliteValidationError("INVALID_RASTER", "Raster dimensions exceed the supported limits.")
        if src.width * src.height > MAX_RASTER_PIXELS:
            raise SatelliteValidationError("INVALID_RASTER", "Raster contains too many pixels for safe processing.")
        if not src.crs:
            raise SatelliteValidationError("INVALID_CRS", "The GeoTIFF has no coordinate reference system.")
        transform_values = tuple(src.transform)
        determinant = src.transform.a * src.transform.e - src.transform.b * src.transform.d
        if (
            not all(math.isfinite(value) for value in (*transform_values, *src.bounds))
            or determinant == 0
        ):
            raise SatelliteValidationError("INVALID_RASTER", "The GeoTIFF has invalid geospatial transform or bounds.")
        if src.count != 1:
            raise SatelliteValidationError(
                "MISSING_REQUIRED_BANDS",
                "This workflow requires a single-band CIcyano product; RGB previews and other band sets are unsupported.",
            )

        tags = src.tags()
        band_tags = src.tags(1)
        descriptions = src.descriptions
        product_source = tags.get("SAPS_product_src", "").lower()
        product_name = tags.get("SAPS_product_name", "").strip().lower()
        product_description = tags.get("SAPS_product_desc", "").lower()
        image_description = tags.get("TIFFTAG_IMAGEDESCRIPTION", "").strip().lower()
        is_sentinel_3 = "sentinel-3" in product_source
        is_ci_cyano = (
            product_name == "cicyano"
            and image_description == "cicyano"
            and "chlorophyll cyanobacteria index" in product_description
        )
        has_supported_version = bool(
            re.search(
                rf"(?<![a-z0-9_]){re.escape(SUPPORTED_PRODUCT_VERSION.lower())}(?![a-z0-9_])",
                product_source,
            )
        )
        scale_formula = tags.get("SAPS_product_rev_scaling")
        normalized_formula = re.sub(r"\s+", "", scale_formula or "").lower()
        has_supported_scale = normalized_formula == "10**(3.0/250.0*dn-4.2)"

        if not is_sentinel_3:
            raise SatelliteValidationError(
                "UNSUPPORTED_SENSOR",
                "Sensor could not be identified as the supported Sentinel-3 OLCI product.",
            )
        if not is_ci_cyano:
            raise SatelliteValidationError(
                "MISSING_REQUIRED_BANDS",
                "The raster is not identified as a CIcyano product; raw bands and RGB previews are not supported.",
            )
        if not has_supported_version:
            raise SatelliteValidationError(
                "UNSUPPORTED_SENSOR",
                f"Only the CIcyano product version {SUPPORTED_PRODUCT_VERSION} is supported.",
            )
        if tags.get("SAPS_product_version") != "1.5" or tags.get("SAPS_product_type") != "standard_prod":
            raise SatelliteValidationError(
                "UNSUPPORTED_SENSOR",
                "The uploaded CIcyano processing version or product type is unsupported.",
            )
        if not scale_formula or not scale_formula.strip():
            raise SatelliteValidationError(
                "MISSING_SCALING_METADATA",
                "The supported CIcyano product must include its reverse-scaling formula metadata.",
            )
        if not _SCALING_EXPRESSION.fullmatch(scale_formula.strip()):
            raise SatelliteValidationError(
                "MALFORMED_SCALING_METADATA",
                "The CIcyano reverse-scaling formula metadata is malformed.",
            )
        if not has_supported_scale:
            raise SatelliteValidationError(
                "UNSUPPORTED_SCALING",
                f"Only the verified CIcyano scaling formula {SUPPORTED_SCALE_FORMULA!r} is supported.",
            )
        if src.dtypes[0] != "uint8":
            raise SatelliteValidationError(
                "UNSUPPORTED_SENSOR",
                "The supported CIcyano product must use 8-bit stored pixel values.",
            )
        expected_quality_tags = {
            "SAPS_product_flag_saturated": "250",
            "SAPS_product_flag_ci_adj": "251",
            "SAPS_product_flag_land": "252",
            "SAPS_product_flag_cloud": "253",
            "SAPS_product_flag_mixed_pixel": "254",
            "SAPS_product_flag_nodata": "255",
            "SAPS_product_flag_nodetect": "0",
        }
        if any(tags.get(key) != value for key, value in expected_quality_tags.items()):
            raise SatelliteValidationError(
                "UNSUPPORTED_SENSOR",
                "The CIcyano quality-mask definitions do not match the supported product specification.",
            )

        if not src.transform.is_identity and src.crs:
            try:
                transformer = Transformer.from_crs(
                    CRS.from_wkt(src.crs.to_wkt()),
                    CRS.from_epsg(4326),
                    always_xy=True,
                )
                west, south, east, north = transformer.transform_bounds(
                    *src.bounds, densify_pts=21
                )
            except (ProjError, ValueError, TypeError) as exc:
                raise SatelliteValidationError(
                    "INVALID_CRS", "The raster CRS cannot be transformed to geographic coordinates."
                ) from exc
        else:
            raise SatelliteValidationError("INVALID_RASTER", "The GeoTIFF has no usable geospatial transform.")

        valid_pixels = 0
        cloud_pixels = 0
        deadline = time.monotonic() + VALIDATION_TIMEOUT_SECONDS
        for window in _window_iter(src):
            if time.monotonic() > deadline:
                raise SatelliteValidationError(
                    "PROCESSING_TIMEOUT",
                    "Raster validation exceeded the 30-second processing limit.",
                )
            values = src.read(1, window=window, masked=False)
            mask = src.read_masks(1, window=window)
            valid_pixels += int(np.count_nonzero(_valid_product_pixels(values, mask)))
            cloud_pixels += int(np.count_nonzero(values == 253))

        total_pixels = src.width * src.height
        valid_percentage = valid_pixels * 100.0 / total_pixels
        cloud_percentage = cloud_pixels * 100.0 / total_pixels
        if valid_pixels == 0:
            raise SatelliteValidationError(
                "INSUFFICIENT_VALID_PIXELS", "No valid CIcyano pixels were found in this raster."
            )

        warnings: list[str] = []
        if valid_percentage < 10:
            warnings.append("Fewer than 10% of raster pixels are valid CIcyano data.")
        if _date_from_metadata(tags) is None:
            warnings.append("No acquisition date was present in the GeoTIFF metadata.")
        if cloud_pixels:
            warnings.append("The CIcyano product contains pixels marked with its cloud quality code.")
        if cloud_percentage > 50:
            warnings.append("More than half of the raster pixels are cloud-masked; interpret the screening cautiously.")
        acquisition_date = _date_from_metadata(tags)
        return {
            "status": "VALID_WITH_WARNINGS" if warnings else "VALID",
            "product_identification_status": "METADATA_CONSISTENT_NOT_AUTHENTICATED",
            "provenance_authenticated": False,
            "sensor": "Sentinel-3 OLCI",
            "product_type": "CIcyano",
            "product_version": SUPPORTED_PRODUCT_VERSION,
            "scale_formula": SUPPORTED_SCALE_FORMULA,
            "scale_formula_evidence": "SAPS_product_rev_scaling GeoTIFF metadata; not independently authenticated",
            "indicator_units": "dimensionless CIcyano index",
            "acquisition_date": acquisition_date,
            "crs": src.crs.to_string(),
            "bounds": {
                "min_latitude": south,
                "max_latitude": north,
                "min_longitude": west,
                "max_longitude": east,
            },
            "spatial_resolution": [abs(src.res[0]), abs(src.res[1])],
            "width": src.width,
            "height": src.height,
            "band_count": src.count,
            "band_descriptions": list(descriptions),
            "band_metadata": band_tags,
            "transform": list(transform_values),
            "data_type": src.dtypes[0],
            "nodata": src.nodata,
            "valid_pixel_percentage": valid_percentage,
            "cloud_percentage": cloud_percentage,
            "warnings": warnings,
        }
