
"""Product-aware validation for Sentinel-3 OLCI GeoTIFF products.

Only the verified CIcyano product is eligible for relative-hotspot screening.
Other products are identified and made available for safe preview/inspection.
"""

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

# Both source-version identifiers passed the metadata audit:
# v9110V20255_2: 58/58
# v9110V20255_2_4: 91/91
SUPPORTED_PRODUCT_VERSIONS = {
    "v9110v20255_2",
    "v9110v20255_2_4",
}

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

CI_CYANO_QUALITY_TAGS = {
    "SAPS_product_flag_saturated": "250",
    "SAPS_product_flag_ci_adj": "251",
    "SAPS_product_flag_land": "252",
    "SAPS_product_flag_cloud": "253",
    "SAPS_product_flag_mixed_pixel": "254",
    "SAPS_product_flag_nodata": "255",
    "SAPS_product_flag_nodetect": "0",
}

KNOWN_PRODUCTS = {
    "cicyano": {
        "display_name": "CIcyano",
        "family": "cyanobacteria_index",
        "capability": "ci_cyano_screening",
    },
    "ci-cicyano": {
        "display_name": "CI-CIcyano",
        "family": "composite_cyanobacteria_index",
        "capability": "metadata_preview",
    },
    "ci": {
        "display_name": "CI",
        "family": "chlorophyll_index",
        "capability": "indicator_preview",
    },
    "cinonfluor": {
        "display_name": "CInonfluor",
        "family": "non_fluorescence_index",
        "capability": "indicator_preview",
    },
    "kd_rhos": {
        "display_name": "Kd_Rhos",
        "family": "diffuse_attenuation_coefficient",
        "capability": "indicator_preview",
    },
    "truecolor": {
        "display_name": "truecolor",
        "family": "rgb_image",
        "capability": "rgb_preview",
    },
    "landwatercolor": {
        "display_name": "landwatercolor",
        "family": "rgb_image",
        "capability": "rgb_preview",
    },
    "rbd_rhos": {
        "display_name": "rbd_rhos",
        "family": "remote_sensing_reflectance",
        "capability": "metadata_preview",
    },
    "rrs665": {
        "display_name": "rrs665",
        "family": "remote_sensing_reflectance_665nm",
        "capability": "metadata_preview",
    },
    "chloc4_global": {
        "display_name": "chloc4_global",
        "family": "chlorophyll_product",
        "capability": "metadata_preview",
    },
    "chl_switch": {
        "display_name": "chl_switch",
        "family": "chlorophyll_product",
        "capability": "metadata_preview",
    },
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
            return datetime.fromisoformat(
                candidate.replace("Z", "+00:00")
            ).date().isoformat()
        except ValueError:
            continue

    return None


def _window_iter(dataset: rasterio.io.DatasetReader):
    """Read a raster in bounded windows instead of loading it all at once."""
    block_height, block_width = dataset.block_shapes[0]
    block_height = max(1, min(block_height, 512))
    block_width = max(1, min(block_width, 512))

    for row in range(0, dataset.height, block_height):
        for col in range(0, dataset.width, block_width):
            height = min(block_height, dataset.height - row)
            width = min(block_width, dataset.width - col)

            yield rasterio.windows.Window(
                col, row, width, height
            )


def _valid_product_pixels(
    values: np.ndarray,
    dataset_mask: np.ndarray,
) -> np.ndarray:
    """CIcyano-specific valid-pixel rule.

    Values 250-255 are reserved quality flags, not valid CIcyano values.
    Do not reuse this rule for unrelated products.
    """
    return (
        (dataset_mask > 0)
        & np.isfinite(values)
        & (values >= 0)
        & (values <= 249)
    )


def _normalise_product_name(value: str | None) -> str:
    return (value or "").strip().lower()


def _identify_product(
    tags: dict[str, str],
    band_count: int,
) -> dict[str, str]:
    """Identify a product from its metadata without guessing its science."""

    raw_name = (
        tags.get("SAPS_product_name")
        or tags.get("TIFFTAG_IMAGEDESCRIPTION")
        or ""
    ).strip()

    normalized_name = _normalise_product_name(raw_name)

    # TIFF image descriptions are sometimes more specific than the
    # SAPS_product_name field. Prefer the explicit SAPS name when present.
    if normalized_name not in KNOWN_PRODUCTS:
        image_description = _normalise_product_name(
            tags.get("TIFFTAG_IMAGEDESCRIPTION")
        )
        if image_description in KNOWN_PRODUCTS:
            normalized_name = image_description

    product = KNOWN_PRODUCTS.get(normalized_name)

    if product is None:
        return {
            "product_name": raw_name or "Unknown",
            "product_type": raw_name or "Unknown",
            "product_family": "unknown",
            "analysis_capability": "metadata_preview",
            "identification_method": (
                "GeoTIFF product metadata not matched to a verified product rule"
            ),
        }

    capability = product["capability"]

    # An RGB product must actually contain three bands.
    if capability == "rgb_preview" and band_count != 3:
        capability = "metadata_preview"

    # A one-band product must not be treated as an RGB image.
    if capability == "rgb_preview" and band_count == 1:
        capability = "metadata_preview"

    return {
        "product_name": product["display_name"],
        "product_type": product["display_name"],
        "product_family": product["family"],
        "analysis_capability": capability,
        "identification_method": "GeoTIFF product metadata",
    }


def _geographic_bounds(src: rasterio.io.DatasetReader) -> dict[str, float]:
    if src.transform.is_identity:
        raise SatelliteValidationError(
            "INVALID_RASTER",
            "The GeoTIFF has no usable geospatial transform.",
        )

    try:
        transformer = Transformer.from_crs(
            CRS.from_wkt(src.crs.to_wkt()),
            CRS.from_epsg(4326),
            always_xy=True,
        )

        west, south, east, north = transformer.transform_bounds(
            *src.bounds,
            densify_pts=21,
        )

    except (ProjError, ValueError, TypeError) as exc:
        raise SatelliteValidationError(
            "INVALID_CRS",
            "The raster CRS cannot be transformed to geographic coordinates.",
        ) from exc

    if not all(
        math.isfinite(value)
        for value in (west, south, east, north)
    ):
        raise SatelliteValidationError(
            "INVALID_CRS",
            "The raster produced invalid geographic bounds.",
        )

    return {
        "min_latitude": south,
        "max_latitude": north,
        "min_longitude": west,
        "max_longitude": east,
    }


def _validate_ci_cyano_metadata(
    src: rasterio.io.DatasetReader,
    tags: dict[str, str],
    product_source: str,
) -> tuple[str, list[str]]:
    """Apply strict scientific checks only to the CIcyano workflow."""

    warnings: list[str] = []

    if src.count != 1:
        raise SatelliteValidationError(
            "MISSING_REQUIRED_BANDS",
            "The CIcyano screening workflow requires exactly one band.",
        )

    # Find every source-version identifier in the metadata.
    # The source metadata can contain more than one source file.
    source_versions = re.findall(
        r"(?<![a-z0-9_])v\d+v\d+(?:_\d+)*(?![a-z0-9_])",
        product_source.lower(),
    )

    # Reject missing, unknown, or mixed unsupported source versions.
    if not source_versions or not all(
        version in SUPPORTED_PRODUCT_VERSIONS
        for version in source_versions
    ):
        raise SatelliteValidationError(
            "UNSUPPORTED_PRODUCT_VERSION",
            "The CIcyano source version is not supported for screening. "
            "Supported source versions: "
            "v9110V20255_2 and v9110V20255_2_4.",
        )

    if (
        tags.get("SAPS_product_version") != "1.5"
        or tags.get("SAPS_product_type") != "standard_prod"
    ):
        raise SatelliteValidationError(
            "UNSUPPORTED_PRODUCT_VERSION",
            "The CIcyano processing version or product type is unsupported.",
        )

    scale_formula = tags.get("SAPS_product_rev_scaling")

    if not scale_formula or not scale_formula.strip():
        raise SatelliteValidationError(
            "MISSING_SCALING_METADATA",
            "The CIcyano product must include its reverse-scaling formula metadata.",
        )

    if not _SCALING_EXPRESSION.fullmatch(scale_formula.strip()):
        raise SatelliteValidationError(
            "MALFORMED_SCALING_METADATA",
            "The CIcyano reverse-scaling formula metadata is malformed.",
        )

    normalized_formula = re.sub(
        r"\s+", "", scale_formula
    ).lower()

    expected_formula = re.sub(
        r"\s+", "", SUPPORTED_SCALE_FORMULA
    ).lower()

    if normalized_formula != expected_formula:
        raise SatelliteValidationError(
            "UNSUPPORTED_SCALING",
            f"Only the verified CIcyano scaling formula "
            f"{SUPPORTED_SCALE_FORMULA!r} is supported.",
        )

    if src.dtypes[0] != "uint8":
        raise SatelliteValidationError(
            "UNSUPPORTED_DATA_TYPE",
            "The supported CIcyano product must use 8-bit stored pixel values.",
        )

    if any(
        tags.get(key) != value
        for key, value in CI_CYANO_QUALITY_TAGS.items()
    ):
        raise SatelliteValidationError(
            "UNSUPPORTED_QUALITY_MASK",
            "The CIcyano quality-mask definitions do not match the verified product specification.",
        )

    return SUPPORTED_SCALE_FORMULA, warnings


def inspect_satellite_raster(
    path: Path,
    original_filename: str,
) -> dict[str, Any]:
    """Inspect a Sentinel-3 GeoTIFF and determine its safe processing path."""

    if Path(original_filename).suffix.lower() not in {
        ".tif",
        ".tiff",
    }:
        raise SatelliteValidationError(
            "INVALID_RASTER",
            "Only .tif and .tiff uploads are accepted.",
        )

    try:
        dataset = rasterio.open(path)
    except (RasterioError, OSError, ValueError) as exc:
        raise SatelliteValidationError(
            "INVALID_RASTER",
            "The uploaded file is not a readable GeoTIFF.",
        ) from exc

    with dataset as src:
        if src.driver != "GTiff":
            raise SatelliteValidationError(
                "INVALID_RASTER",
                "The uploaded raster must use the GeoTIFF format.",
            )

        if (
            src.width <= 0
            or src.height <= 0
            or src.width > MAX_RASTER_SIDE
            or src.height > MAX_RASTER_SIDE
        ):
            raise SatelliteValidationError(
                "INVALID_RASTER",
                "Raster dimensions exceed the supported limits.",
            )

        if src.width * src.height > MAX_RASTER_PIXELS:
            raise SatelliteValidationError(
                "INVALID_RASTER",
                "Raster contains too many pixels for safe processing.",
            )

        if not src.crs:
            raise SatelliteValidationError(
                "INVALID_CRS",
                "The GeoTIFF has no coordinate reference system.",
            )

        transform_values = tuple(src.transform)
        determinant = (
            src.transform.a * src.transform.e
            - src.transform.b * src.transform.d
        )

        if (
            not all(
                math.isfinite(value)
                for value in (*transform_values, *src.bounds)
            )
            or determinant == 0
        ):
            raise SatelliteValidationError(
                "INVALID_RASTER",
                "The GeoTIFF has an invalid geospatial transform or bounds.",
            )

        if src.count < 1 or src.count > 3:
            raise SatelliteValidationError(
                "UNSUPPORTED_BAND_COUNT",
                "This application currently accepts GeoTIFFs with 1 to 3 bands.",
            )

        tags = src.tags()
        band_tags = [
            src.tags(index)
            for index in range(1, src.count + 1)
        ]
        descriptions = list(src.descriptions)

        product_source = tags.get(
            "SAPS_product_src", ""
        ).strip()

        is_sentinel_3 = (
            "sentinel-3" in product_source.lower()
        )

        if not is_sentinel_3:
            raise SatelliteValidationError(
                "UNSUPPORTED_SENSOR",
                "The sensor could not be identified as Sentinel-3 from the GeoTIFF product-source metadata.",
            )

        product = _identify_product(tags, src.count)

        product_name = product["product_name"]
        capability = product["analysis_capability"]

        scale_formula = tags.get(
            "SAPS_product_rev_scaling"
        )

        # CIcyano gets its own strict validation path.
        if capability == "ci_cyano_screening":
            image_description = _normalise_product_name(
                tags.get("TIFFTAG_IMAGEDESCRIPTION")
            )
            product_description = tags.get(
                "SAPS_product_desc", ""
            ).lower()

            if (
                _normalise_product_name(
                    tags.get("SAPS_product_name")
                ) != "cicyano"
                or image_description != "cicyano"
                or not re.search(
                    r"\b(?:cicyano|chlorophyll cyanobacteria index)\b",
                    product_description,
                )
            ):
                raise SatelliteValidationError(
                    "PRODUCT_METADATA_MISMATCH",
                    "The CIcyano product metadata fields do not agree.",
                )

            scale_formula, _ = _validate_ci_cyano_metadata(
                src,
                tags,
                product_source.lower(),
            )

        # Do not apply CIcyano reserved values or scale formula to other products.
        warnings: list[str] = []

        if capability == "rgb_preview":
            if src.count != 3:
                raise SatelliteValidationError(
                    "UNSUPPORTED_BAND_COUNT",
                    "An RGB preview requires exactly three bands.",
                )

            if not all(dtype == "uint8" for dtype in src.dtypes):
                warnings.append(
                    "The RGB product is not uint8. Preview rendering must use a product-aware stretch."
                )

        elif capability == "metadata_preview":
            warnings.append(
                "This product is identified, but its scientific scaling and quality-mask rules are not yet verified. Only safe preview and metadata inspection should be enabled."
            )

        elif capability == "indicator_preview":
            warnings.append(
                "This is a single-band scientific indicator product. CIcyano hotspot screening is not applicable to this product."
            )

        bounds = _geographic_bounds(src)

        valid_pixels = 0
        cloud_pixels = 0
        total_pixels = src.width * src.height

        deadline = time.monotonic() + VALIDATION_TIMEOUT_SECONDS

        for window in _window_iter(src):
            if time.monotonic() > deadline:
                raise SatelliteValidationError(
                    "PROCESSING_TIMEOUT",
                    "Raster validation exceeded the 30-second processing limit.",
                )

            if capability == "ci_cyano_screening":
                values = src.read(
                    1,
                    window=window,
                    masked=False,
                )
                mask = src.read_masks(
                    1,
                    window=window,
                )

                valid_pixels += int(
                    np.count_nonzero(
                        _valid_product_pixels(values, mask)
                    )
                )

                cloud_pixels += int(
                    np.count_nonzero(values == 253)
                )

            else:
                # Generic structural validity only.
                # This does not interpret product-specific quality flags.
                mask = src.dataset_mask(window=window)
                valid_pixels += int(
                    np.count_nonzero(mask > 0)
                )

        valid_percentage = (
            valid_pixels * 100.0 / total_pixels
            if total_pixels
            else 0.0
        )

        cloud_percentage = (
            cloud_pixels * 100.0 / total_pixels
            if total_pixels
            else 0.0
        )

        if valid_pixels == 0:
            raise SatelliteValidationError(
                "INSUFFICIENT_VALID_PIXELS",
                "No valid raster pixels were found.",
            )

        if capability == "ci_cyano_screening":
            if valid_percentage < 10:
                warnings.append(
                    "Fewer than 10% of raster pixels are valid CIcyano data. Hotspot screening will be blocked by the existing 10% safeguard."
                )

            if cloud_pixels:
                warnings.append(
                    "The CIcyano product contains pixels marked with its cloud quality code."
                )

            if cloud_percentage > 50:
                warnings.append(
                    "More than half of the raster pixels are cloud-masked. Interpret the screening cautiously."
                )

        acquisition_date = _date_from_metadata(tags)

        if acquisition_date is None:
            warnings.append(
                "No acquisition date was present in the GeoTIFF metadata. No date has been inferred from the filename."
            )

        product_version = tags.get(
            "SAPS_product_version"
        )

        if not product_version:
            product_version = "Not specified in metadata"

        identification_status = (
            "METADATA_CONSISTENT_NOT_AUTHENTICATED"
            if capability == "ci_cyano_screening"
            else "PRODUCT_IDENTIFIED_FROM_METADATA_NOT_AUTHENTICATED"
        )

        return {
            "status": (
                "VALID_WITH_WARNINGS"
                if warnings
                else "VALID"
            ),
            "product_identification_status": identification_status,
            "provenance_authenticated": False,
            "sensor": "Sentinel-3 OLCI",
            "product_name": product_name,
            "product_type": product["product_type"],
            "product_family": product["product_family"],
            "analysis_capability": capability,
            "identification_method": product["identification_method"],
            "product_version": product_version,
            "product_source": product_source or None,
            "product_description": tags.get(
                "SAPS_product_desc"
            ),
            "scale_formula": (
                scale_formula
                if capability == "ci_cyano_screening"
                else None
            ),
            "scale_formula_metadata": scale_formula,
            "scale_formula_evidence": (
                "Verified against the configured CIcyano formula; GeoTIFF metadata is not independently authenticated."
                if capability == "ci_cyano_screening"
                else "Not scientifically verified by this application."
            ),
            "indicator_units": (
                "dimensionless CIcyano index"
                if capability == "ci_cyano_screening"
                else None
            ),
            "acquisition_date": acquisition_date,
            "crs": src.crs.to_string(),
            "bounds": bounds,
            "spatial_resolution": [
                abs(src.res[0]),
                abs(src.res[1]),
            ],
            "width": src.width,
            "height": src.height,
            "band_count": src.count,
            "band_descriptions": descriptions,
            "band_metadata": band_tags,
            "transform": list(transform_values),
            "data_type": (
                src.dtypes[0]
                if len(set(src.dtypes)) == 1
                else list(src.dtypes)
            ),
            "band_data_types": list(src.dtypes),
            "nodata": src.nodata,
            "valid_pixel_percentage": valid_percentage,
            "cloud_percentage": (
                cloud_percentage
                if capability == "ci_cyano_screening"
                else None
            ),
            "warnings": warnings,
        }
