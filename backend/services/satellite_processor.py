"""Windowed relative-hotspot screening for supported CIcyano rasters."""

from __future__ import annotations

import time
import re
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from PIL import Image
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject, transform_bounds
from rasterio.windows import Window

from backend.services.satellite_validator import (
    RESERVED_QUALITY_VALUES,
    SUPPORTED_SCALE_FORMULA,
    _valid_product_pixels,
)

TILE_SIZE = 512
NODATA_FLOAT = -9999.0
NODATA_MASK = 255
MAX_ANALYSIS_SECONDS = 120
DISPLAY_CRS = "EPSG:3857"
MAX_DISPLAY_PIXELS = 20_000_000
MIN_SCREENING_COVERAGE_PERCENT = 10.0


def _windows(width: int, height: int):
    for row in range(0, height, TILE_SIZE):
        for col in range(0, width, TILE_SIZE):
            yield Window(col, row, min(TILE_SIZE, width - col), min(TILE_SIZE, height - row))


def _scale_lookup(formula: str | None) -> np.ndarray:
    if re.sub(r"\s+", "", formula or "").lower() != re.sub(
        r"\s+", "", SUPPORTED_SCALE_FORMULA
    ).lower():
        raise ValueError("A supported CIcyano scale formula is required for analysis.")
    values = np.arange(250, dtype=np.float64)
    scaled = np.power(10.0, (3.0 / 250.0 * values) - 4.2)
    scaled[0] = 0.0
    return scaled


def _quantile_scaled(
    histogram: np.ndarray, quantile: float, scale_lookup: np.ndarray
) -> float | None:
    total = int(histogram.sum())
    if total == 0:
        return None
    occupied_bins = np.flatnonzero(histogram)
    cumulative = np.cumsum(histogram[occupied_bins])
    position = (total - 1) * quantile
    lower_rank = int(np.floor(position))
    upper_rank = int(np.ceil(position))
    lower_value = scale_lookup[
        occupied_bins[np.searchsorted(cumulative, lower_rank, side="right")]
    ]
    upper_value = scale_lookup[
        occupied_bins[np.searchsorted(cumulative, upper_rank, side="right")]
    ]
    fraction = position - lower_rank
    return float(lower_value + fraction * (upper_value - lower_value))


def _scaled_ci(values: np.ndarray, scale_lookup: np.ndarray) -> np.ndarray:
    stored_values = np.clip(values.astype(np.uint8, copy=False), 0, 249)
    return scale_lookup[stored_values]


def _create_display_overlay(
    indicator_path: Path,
    mask_path: Path,
    overlay_path: Path,
    minimum: float | None,
    maximum: float | None,
    deadline: float,
) -> dict[str, Any]:
    with rasterio.open(indicator_path) as indicator, rasterio.open(mask_path) as mask:
        display_transform, display_width, display_height = calculate_default_transform(
            indicator.crs,
            DISPLAY_CRS,
            indicator.width,
            indicator.height,
            *indicator.bounds,
        )
        if (
            display_width <= 0
            or display_height <= 0
            or display_width > 20_000
            or display_height > 20_000
            or display_width * display_height > MAX_DISPLAY_PIXELS
        ):
            raise ValueError("The raster cannot be safely reprojected to the map display grid.")

        with tempfile.TemporaryDirectory(
            prefix=f"{indicator_path.stem}-display-", dir=indicator_path.parent
        ) as temporary_directory:
            display_indicator_path = Path(temporary_directory) / "indicator.tif"
            display_mask_path = Path(temporary_directory) / "mask.tif"
            display_profile = indicator.profile.copy()
            display_profile.update(
                driver="GTiff",
                width=display_width,
                height=display_height,
                crs=DISPLAY_CRS,
                transform=display_transform,
                dtype="float32",
                nodata=NODATA_FLOAT,
                compress="deflate",
            )
            display_mask_profile = display_profile.copy()
            display_mask_profile.update(dtype="uint8", nodata=NODATA_MASK)

            with rasterio.open(display_indicator_path, "w", **display_profile) as display_indicator:
                reproject(
                    source=rasterio.band(indicator, 1),
                    destination=rasterio.band(display_indicator, 1),
                    src_transform=indicator.transform,
                    src_crs=indicator.crs,
                    src_nodata=NODATA_FLOAT,
                    dst_transform=display_transform,
                    dst_crs=DISPLAY_CRS,
                    dst_nodata=NODATA_FLOAT,
                    resampling=Resampling.bilinear,
                    init_dest_nodata=True,
                )
                display_indicator.update_tags(
                    resampling="bilinear",
                    source_crs=indicator.crs.to_string(),
                    display_crs=DISPLAY_CRS,
                )
            with rasterio.open(display_mask_path, "w", **display_mask_profile) as display_mask:
                reproject(
                    source=rasterio.band(mask, 1),
                    destination=rasterio.band(display_mask, 1),
                    src_transform=mask.transform,
                    src_crs=mask.crs,
                    src_nodata=NODATA_MASK,
                    dst_transform=display_transform,
                    dst_crs=DISPLAY_CRS,
                    dst_nodata=NODATA_MASK,
                    resampling=Resampling.nearest,
                    init_dest_nodata=True,
                )
                display_mask.update_tags(
                    resampling="nearest",
                    source_crs=mask.crs.to_string(),
                    display_crs=DISPLAY_CRS,
                )

            rgba = Image.new("RGBA", (display_width, display_height), (0, 0, 0, 0))
            with rasterio.open(display_indicator_path) as display_indicator, rasterio.open(
                display_mask_path
            ) as display_mask:
                for window in _windows(display_width, display_height):
                    if time.monotonic() > deadline:
                        raise TimeoutError("Satellite screening exceeded its processing time limit.")
                    values = display_indicator.read(1, window=window)
                    mask_values = display_mask.read(1, window=window)

                    valid = np.isfinite(values) & (values != NODATA_FLOAT)
                    hotspots = valid & (mask_values == 1)
                    if minimum is None or maximum is None or maximum <= minimum:
                        normalized = np.zeros(values.shape, dtype=np.float32)
                    else:
                        normalized = np.clip(
                            (values - minimum) / (maximum - minimum), 0.0, 1.0
                        )

                    red = (30 + 70 * normalized).astype(np.uint8)
                    green = (135 + 100 * normalized).astype(np.uint8)
                    blue = (205 + 20 * normalized).astype(np.uint8)
                    red[hotspots] = 255
                    green[hotspots] = 184
                    blue[hotspots] = 61
                    alpha = np.where(hotspots, 245, np.where(valid, 155, 0)).astype(np.uint8)
                    tile = Image.fromarray(
                        np.dstack((red, green, blue, alpha)), mode="RGBA"
                    )
                    rgba.paste(tile, (int(window.col_off), int(window.row_off)))

            rgba.save(overlay_path, format="PNG", optimize=True)
            west, south, east, north = transform_bounds(
                DISPLAY_CRS,
                "EPSG:4326",
                *rasterio.transform.array_bounds(
                    display_height, display_width, display_transform
                ),
                densify_pts=21,
            )
            return {
                "crs": DISPLAY_CRS,
                "width": display_width,
                "height": display_height,
                "transform": list(display_transform),
                "bounds": {
                    "min_latitude": south,
                    "max_latitude": north,
                    "min_longitude": west,
                    "max_longitude": east,
                },
                "indicator_resampling": "bilinear",
                "hotspot_mask_resampling": "nearest",
            }


def analyze_ci_cyano(
    source_path: Path,
    analysis_id: str,
    output_dir: Path,
    metadata: dict[str, Any],
    timeout_seconds: int = MAX_ANALYSIS_SECONDS,
) -> dict[str, Any]:
    """Create georeferenced indicator/mask rasters and a transparent map overlay."""
    succeeded = False
    try:
        result = _analyze_ci_cyano(
            source_path,
            analysis_id,
            output_dir,
            metadata,
            time.monotonic() + timeout_seconds,
        )
        succeeded = True
        return result
    finally:
        if not succeeded:
            for suffix in ("-indicator.tif", "-mask.tif", "-overlay.png"):
                (output_dir / f"{analysis_id}{suffix}").unlink(missing_ok=True)


def _analyze_ci_cyano(
    source_path: Path,
    analysis_id: str,
    output_dir: Path,
    metadata: dict[str, Any],
    deadline: float,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    indicator_path = output_dir / f"{analysis_id}-indicator.tif"
    mask_path = output_dir / f"{analysis_id}-mask.tif"
    overlay_path = output_dir / f"{analysis_id}-overlay.png"

    histogram = np.zeros(250, dtype=np.int64)
    total_pixels = 0
    valid_count = 0
    quality_counts = {value: 0 for value in RESERVED_QUALITY_VALUES}
    scale_formula = metadata.get("scale_formula")
    scale_lookup = _scale_lookup(scale_formula)

    with rasterio.open(source_path) as source:
        for window in _windows(source.width, source.height):
            if time.monotonic() > deadline:
                raise TimeoutError("Satellite screening exceeded its processing time limit.")
            values = source.read(1, window=window, masked=False)
            valid_mask = _valid_product_pixels(values, source.read_masks(1, window=window))
            total_pixels += values.size
            valid_values = values[valid_mask].astype(np.uint8, copy=False)
            valid_count += int(valid_values.size)
            if valid_values.size:
                histogram += np.bincount(valid_values, minlength=250)[:250]
            for value in quality_counts:
                quality_counts[value] += int(np.count_nonzero(values == value))

        first_quartile = _quantile_scaled(histogram, 0.25, scale_lookup)
        median = _quantile_scaled(histogram, 0.50, scale_lookup)
        third_quartile = _quantile_scaled(histogram, 0.75, scale_lookup)
        percentiles = {
            f"p{percentile}": _quantile_scaled(histogram, percentile / 100, scale_lookup)
            for percentile in (25, 50, 75, 90, 95, 99)
        }
        occupied = np.flatnonzero(histogram)
        minimum = float(scale_lookup[occupied[0]]) if occupied.size else None
        maximum = float(scale_lookup[occupied[-1]]) if occupied.size else None
        valid_percentage = (
            valid_count * 100.0 / total_pixels if total_pixels else None
        )
        if valid_count == 0:
            coverage_category = "NO_VALID_PIXELS"
        elif valid_percentage < MIN_SCREENING_COVERAGE_PERCENT:
            coverage_category = "INSUFFICIENT_COVERAGE"
        elif valid_percentage < 25.0:
            coverage_category = "LOW_COVERAGE"
        elif valid_percentage < 50.0:
            coverage_category = "MODERATE_COVERAGE"
        else:
            coverage_category = "BETTER_COVERAGE"
        screening_permitted = (
            valid_count > 0
            and valid_percentage >= MIN_SCREENING_COVERAGE_PERCENT
        )
        if valid_count:
            scaled_counts = histogram.astype(np.float64)
            value_sum = float(np.dot(scaled_counts, scale_lookup))
            mean = value_sum / valid_count
            variance = max(
                float(np.dot(scaled_counts, np.square(scale_lookup)) / valid_count)
                - mean * mean,
                0.0,
            )
            standard_deviation = float(np.sqrt(variance))
            threshold = (
                third_quartile + 1.5 * (third_quartile - first_quartile)
                if screening_permitted
                and first_quartile is not None
                and third_quartile is not None
                else None
            )
        else:
            mean = median = standard_deviation = threshold = None

        profile = source.profile.copy()
        profile.update(
            driver="GTiff",
            count=1,
            compress="deflate",
            tiled=True,
            blockxsize=256,
            blockysize=256,
            nodata=NODATA_FLOAT,
            dtype="float32",
        )
        mask_profile = profile.copy()
        mask_profile.update(dtype="uint8", nodata=NODATA_MASK)

        high_pixels = 0
        with rasterio.open(indicator_path, "w", **profile) as indicator_dst, rasterio.open(
            mask_path, "w", **mask_profile
        ) as mask_dst:
            indicator_dst.update_tags(
                product="Sentinel-3 OLCI CIcyano",
                indicator_units=metadata["indicator_units"],
                scale_formula=scale_formula,
                source_values="scaled from stored uint8 digital numbers",
            )
            mask_dst.update_tags(
                product="Sentinel-3 OLCI CIcyano",
                mask_values="0=below relative threshold, 1=above relative threshold, 255=invalid or screening not performed",
                threshold_source=(
                    "Scene-specific Tukey upper fence; not a biological HAB threshold."
                    if screening_permitted
                    else "Not calculated because valid-pixel coverage was below 10%."
                ),
            )
            for window in _windows(source.width, source.height):
                if time.monotonic() > deadline:
                    raise TimeoutError("Satellite screening exceeded its processing time limit.")
                values = source.read(1, window=window, masked=False)
                valid_mask = _valid_product_pixels(values, source.read_masks(1, window=window))
                valid_values = _scaled_ci(values, scale_lookup).astype(np.float32)
                indicator_values = np.where(valid_mask, valid_values, NODATA_FLOAT).astype(np.float32)
                if screening_permitted and threshold is not None:
                    high_mask = valid_mask & (valid_values > threshold)
                    mask_values = np.where(
                        valid_mask, high_mask.astype(np.uint8), NODATA_MASK
                    ).astype(np.uint8)
                else:
                    high_mask = np.zeros_like(valid_mask)
                    mask_values = np.full(values.shape, NODATA_MASK, dtype=np.uint8)
                indicator_dst.write(indicator_values, 1, window=window)
                mask_dst.write(mask_values, 1, window=window)
                high_pixels += int(np.count_nonzero(high_mask))
        display = _create_display_overlay(
            indicator_path,
            mask_path,
            overlay_path,
            minimum,
            maximum,
            deadline,
        )
        high_percentage = (
            high_pixels * 100.0 / valid_count
            if screening_permitted and valid_count
            else None
        )
        invalid_count = total_pixels - valid_count
        cloud_percentage = quality_counts[253] * 100.0 / total_pixels if total_pixels else None

    warnings = list(metadata.get("warnings", []))
    if not valid_count:
        screening_status = "NO_VALID_PIXELS"
        warnings.append(
            "No valid pixels remained after quality masking; hotspot screening was not performed "
            "and indicator statistics are unavailable."
        )
    elif not screening_permitted:
        screening_status = "INSUFFICIENT_COVERAGE"
        warnings.append(
            "Hotspot screening was not performed because fewer than 10% of image pixels "
            "are valid. This is an engineering safeguard, not a scientific confidence threshold."
        )
    elif coverage_category == "LOW_COVERAGE":
        screening_status = (
            "NO_RELATIVE_HOTSPOTS" if high_pixels == 0 else "RELATIVE_HOTSPOTS_DETECTED"
        )
        warnings.append(
            "Low valid-pixel coverage (10% to below 25%): relative screening may be unstable "
            "or unrepresentative because much of the image is invalid. This category is an "
            "engineering safeguard, not a biological confidence level."
        )
    elif high_pixels == 0:
        screening_status = "NO_RELATIVE_HOTSPOTS"
        warnings.append("No pixels exceeded the scene-relative Tukey upper fence; this does not establish that the waterbody is HAB-free.")
    else:
        screening_status = "RELATIVE_HOTSPOTS_DETECTED"

    return {
        "status": "success",
        "analysis_id": analysis_id,
        "filename": metadata["filename"],
        "sensor": metadata["sensor"],
        "product_type": metadata["product_type"],
        "product_version": metadata["product_version"],
        "acquisition_date": metadata["acquisition_date"],
        "crs": metadata["crs"],
        "bounds": metadata["bounds"],
        "display": display,
        "spatial_resolution": metadata["spatial_resolution"],
        "band_count": metadata["band_count"],
        "band_descriptions": metadata["band_descriptions"],
        "quality": {
            "valid_pixel_percentage": valid_percentage,
            "coverage_category": coverage_category,
            "valid_pixel_count": valid_count,
            "invalid_pixel_count": invalid_count,
            "cloud_percentage": cloud_percentage,
            "quality_pixel_counts": {
                RESERVED_QUALITY_VALUES[value]: count
                for value, count in quality_counts.items()
            },
            "warnings": warnings,
        },
        "analysis": {
            "method": "Sentinel-3 OLCI CIcyano scene-relative hotspot screening",
            "indicator_units": metadata["indicator_units"],
            "screening_status": screening_status,
            "coverage_category": coverage_category,
            "indicator_hotspots_found": (
                high_pixels > 0 if screening_permitted else None
            ),
            "possible_hab_indicator": None,
            "mean_indicator": mean,
            "median_indicator": median,
            "standard_deviation_indicator": standard_deviation,
            "maximum_indicator": maximum,
            "minimum_indicator": minimum,
            "percentiles": percentiles,
            "threshold": threshold,
            "hotspot_pixel_count": high_pixels if screening_permitted else None,
            "hotspot_pixel_percentage": high_percentage,
            "threshold_source": (
                "Scene-specific Tukey upper fence (Q3 + 1.5 × IQR); relative outlier "
                "screen, not a biological HAB threshold."
                if screening_permitted
                else (
                    "Not calculated because no valid pixels remained."
                    if not valid_count
                    else "Not calculated because valid-pixel coverage was below the 10% engineering safeguard."
                )
            ),
            "high_indicator_pixel_percentage": high_percentage,
            "valid_pixel_count": valid_count,
            "invalid_pixel_count": invalid_count,
            "total_pixel_count": total_pixels,
            "cloud_percentage": cloud_percentage,
        },
        "result_type": "experimental_screening",
        "model_accuracy": None,
        "outputs": {
            "overlay_url": f"/api/satellite-detection/result/{analysis_id}/overlay",
            "indicator_raster_url": f"/api/satellite-detection/result/{analysis_id}/indicator",
            "mask_raster_url": f"/api/satellite-detection/result/{analysis_id}/mask",
        },
        "disclaimer": (
            "This result is an experimental satellite-based screening output. A detected spectral "
            "indicator does not confirm toxic HAB presence or identify the responsible species. "
            "Field sampling and laboratory verification may be required."
        ),
    }
