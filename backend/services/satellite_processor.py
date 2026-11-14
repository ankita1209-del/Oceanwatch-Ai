
"""Product-aware Sentinel-3 previews and CIcyano-only screening."""

from __future__ import annotations

import re
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from PIL import Image
from rasterio.enums import Resampling
from rasterio.transform import array_bounds
from rasterio.warp import (
    calculate_default_transform,
    reproject,
    transform_bounds,
)
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
MAX_PREVIEW_SIDE = 2048
MIN_SCREENING_COVERAGE_PERCENT = 10.0


def _windows(width: int, height: int):
    """Yield bounded raster windows."""
    for row in range(0, height, TILE_SIZE):
        for col in range(0, width, TILE_SIZE):
            yield Window(
                col,
                row,
                min(TILE_SIZE, width - col),
                min(TILE_SIZE, height - row),
            )


def _check_deadline(deadline: float, message: str) -> None:
    if time.monotonic() > deadline:
        raise TimeoutError(message)


def _scale_lookup(formula: str | None) -> np.ndarray:
    """Build the verified CIcyano DN-to-indicator lookup table."""
    normalize = lambda value: re.sub(
        r"\s+", "", value or ""
    ).lower()

    if normalize(formula) != normalize(SUPPORTED_SCALE_FORMULA):
        raise ValueError(
            "A supported CIcyano scale formula is required for analysis."
        )

    values = np.arange(250, dtype=np.float64)
    scaled = np.power(
        10.0,
        (3.0 / 250.0 * values) - 4.2,
    )
    scaled[0] = 0.0
    return scaled


def _quantile_scaled(
    histogram: np.ndarray,
    quantile: float,
    scale_lookup: np.ndarray,
) -> float | None:
    """Calculate a quantile from a histogram using zero-based ranks."""
    total = int(histogram.sum())

    if total == 0:
        return None

    occupied_bins = np.flatnonzero(histogram)
    cumulative = np.cumsum(histogram[occupied_bins])

    position = (total - 1) * quantile
    lower_rank = int(np.floor(position))
    upper_rank = int(np.ceil(position))

    lower_index = np.searchsorted(
        cumulative, lower_rank + 1, side="left"
    )
    upper_index = np.searchsorted(
        cumulative, upper_rank + 1, side="left"
    )

    lower_value = scale_lookup[occupied_bins[lower_index]]
    upper_value = scale_lookup[occupied_bins[upper_index]]

    fraction = position - lower_rank

    return float(
        lower_value + fraction * (upper_value - lower_value)
    )


def _scaled_ci(
    values: np.ndarray,
    scale_lookup: np.ndarray,
) -> np.ndarray:
    stored_values = np.clip(
        values.astype(np.uint8, copy=False),
        0,
        249,
    )
    return scale_lookup[stored_values]


def _source_display_info(
    source: rasterio.io.DatasetReader,
) -> dict[str, Any]:
    if source.crs is None:
        raise ValueError(
            "A valid coordinate reference system is required for map display."
        )

    west, south, east, north = transform_bounds(
        source.crs,
        "EPSG:4326",
        *source.bounds,
        densify_pts=21,
    )

    return {
        "crs": source.crs.to_string(),
        "bounds": {
            "min_latitude": south,
            "max_latitude": north,
            "min_longitude": west,
            "max_longitude": east,
        },
    }


def _create_display_overlay(
    indicator_path: Path,
    mask_path: Path,
    overlay_path: Path,
    minimum: float | None,
    maximum: float | None,
    deadline: float,
) -> dict[str, Any]:
    """Create the georeferenced CIcyano relative-hotspot overlay."""
    with rasterio.open(indicator_path) as indicator, rasterio.open(
        mask_path
    ) as mask:
        if indicator.crs is None:
            raise ValueError("CIcyano indicator raster has no CRS.")

        display_transform, display_width, display_height = (
            calculate_default_transform(
                indicator.crs,
                DISPLAY_CRS,
                indicator.width,
                indicator.height,
                *indicator.bounds,
            )
        )

        if (
            display_width <= 0
            or display_height <= 0
            or display_width > 20_000
            or display_height > 20_000
            or display_width * display_height > MAX_DISPLAY_PIXELS
        ):
            raise ValueError(
                "The raster cannot be safely reprojected to the map display grid."
            )

        with tempfile.TemporaryDirectory(
            prefix=f"{indicator_path.stem}-display-",
            dir=indicator_path.parent,
        ) as temporary_directory:
            temporary = Path(temporary_directory)
            display_indicator_path = temporary / "indicator.tif"
            display_mask_path = temporary / "mask.tif"

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

            mask_profile = display_profile.copy()
            mask_profile.update(
                dtype="uint8",
                nodata=NODATA_MASK,
            )

            with rasterio.open(
                display_indicator_path,
                "w",
                **display_profile,
            ) as destination:
                reproject(
                    source=rasterio.band(indicator, 1),
                    destination=rasterio.band(destination, 1),
                    src_transform=indicator.transform,
                    src_crs=indicator.crs,
                    src_nodata=NODATA_FLOAT,
                    dst_transform=display_transform,
                    dst_crs=DISPLAY_CRS,
                    dst_nodata=NODATA_FLOAT,
                    resampling=Resampling.bilinear,
                    init_dest_nodata=True,
                )

            with rasterio.open(
                display_mask_path,
                "w",
                **mask_profile,
            ) as destination:
                reproject(
                    source=rasterio.band(mask, 1),
                    destination=rasterio.band(destination, 1),
                    src_transform=mask.transform,
                    src_crs=mask.crs,
                    src_nodata=NODATA_MASK,
                    dst_transform=display_transform,
                    dst_crs=DISPLAY_CRS,
                    dst_nodata=NODATA_MASK,
                    resampling=Resampling.nearest,
                    init_dest_nodata=True,
                )

            rgba = Image.new(
                "RGBA",
                (display_width, display_height),
                (0, 0, 0, 0),
            )

            with rasterio.open(
                display_indicator_path
            ) as display_indicator, rasterio.open(
                display_mask_path
            ) as display_mask:
                for window in _windows(
                    display_width,
                    display_height,
                ):
                    _check_deadline(
                        deadline,
                        "Satellite screening exceeded its processing time limit.",
                    )

                    values = display_indicator.read(
                        1, window=window
                    )
                    mask_values = display_mask.read(
                        1, window=window
                    )

                    valid = (
                        np.isfinite(values)
                        & (values != NODATA_FLOAT)
                    )
                    hotspots = valid & (mask_values == 1)

                    if (
                        minimum is None
                        or maximum is None
                        or maximum <= minimum
                    ):
                        normalized = np.zeros(
                            values.shape,
                            dtype=np.float32,
                        )
                    else:
                        normalized = np.clip(
                            (values - minimum) / (maximum - minimum),
                            0.0,
                            1.0,
                        )

                    red = (30 + 70 * normalized).astype(np.uint8)
                    green = (135 + 100 * normalized).astype(np.uint8)
                    blue = (205 + 20 * normalized).astype(np.uint8)

                    red[hotspots] = 255
                    green[hotspots] = 184
                    blue[hotspots] = 61

                    alpha = np.where(
                        hotspots,
                        245,
                        np.where(valid, 155, 0),
                    ).astype(np.uint8)

                    tile = Image.fromarray(
                        np.dstack((red, green, blue, alpha)),
                        mode="RGBA",
                    )

                    rgba.paste(
                        tile,
                        (
                            int(window.col_off),
                            int(window.row_off),
                        ),
                    )

            rgba.save(
                overlay_path,
                format="PNG",
                optimize=True,
            )

            west, south, east, north = transform_bounds(
                DISPLAY_CRS,
                "EPSG:4326",
                *array_bounds(
                    display_height,
                    display_width,
                    display_transform,
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


def _create_generic_preview(
    source_path: Path,
    preview_path: Path,
    product_capability: str,
    deadline: float,
) -> dict[str, Any]:
    """
    Create a visual preview without applying scientific product scaling.

    Only products explicitly identified as RGB use three-band display.
    Other products use their first band as grayscale.
    """
    with rasterio.open(source_path) as source:
        if source.count < 1:
            raise ValueError("The uploaded raster contains no readable bands.")

        display_scale = min(
            1.0,
            MAX_PREVIEW_SIDE / max(source.width, source.height),
        )

        display_width = max(
            1,
            int(round(source.width * display_scale)),
        )
        display_height = max(
            1,
            int(round(source.height * display_scale)),
        )

        preview_bands = (
            3 if product_capability == "rgb_preview" else 1
        )

        if preview_bands == 3 and source.count != 3:
            raise ValueError(
                "An RGB preview requires exactly three raster bands."
            )

        preview = source.read(
            indexes=list(range(1, preview_bands + 1)),
            out_shape=(
                preview_bands,
                display_height,
                display_width,
            ),
            resampling=Resampling.bilinear,
        ).astype(np.float64)

        preview_mask = (
            source.dataset_mask(
                out_shape=(display_height, display_width),
                resampling=Resampling.nearest,
            )
            > 0
        )

        _check_deadline(
            deadline,
            "Satellite preview exceeded its processing time limit.",
        )

        if not np.any(preview_mask):
            raise ValueError(
                "No displayable pixels remain after the raster dataset mask."
            )

        stretch_details = []

        if preview_bands == 3:
            rgb = np.zeros(
                (display_height, display_width, 3),
                dtype=np.uint8,
            )

            for band_index in range(3):
                values = preview[band_index]
                valid = preview_mask & np.isfinite(values)
                valid_values = values[valid]

                if valid_values.size == 0:
                    low, high = 0.0, 1.0
                else:
                    low, high = np.percentile(
                        valid_values,
                        [2, 98],
                    ).tolist()

                    if high <= low:
                        high = low + 1.0

                normalized = np.clip(
                    (values - low) / (high - low),
                    0.0,
                    1.0,
                )

                rgb[:, :, band_index] = (
                    normalized * 255
                ).astype(np.uint8)

                stretch_details.append({
                    "band": band_index + 1,
                    "display_minimum": float(low),
                    "display_maximum": float(high),
                    "method": "2nd–98th percentile display stretch",
                })

            image = Image.fromarray(
                rgb,
                mode="RGB",
            ).convert("RGBA")

        else:
            values = preview[0]
            valid = preview_mask & np.isfinite(values)
            valid_values = values[valid]

            if valid_values.size == 0:
                low, high = 0.0, 1.0
            else:
                low, high = np.percentile(
                    valid_values,
                    [2, 98],
                ).tolist()

                if high <= low:
                    high = low + 1.0

            normalized = np.clip(
                (values - low) / (high - low),
                0.0,
                1.0,
            )

            grayscale = (
                normalized * 255
            ).astype(np.uint8)

            image = Image.fromarray(
                grayscale,
                mode="L",
            ).convert("RGBA")

            stretch_details.append({
                "band": 1,
                "display_minimum": float(low),
                "display_maximum": float(high),
                "method": "2nd–98th percentile grayscale display stretch",
            })

        alpha = np.where(
            preview_mask,
            220,
            0,
        ).astype(np.uint8)

        image.putalpha(Image.fromarray(alpha, mode="L"))
        image.save(
            preview_path,
            format="PNG",
            optimize=True,
        )

        display_info = _source_display_info(source)

        display_info.update({
            "width": display_width,
            "height": display_height,
            "preview_type": (
                "rgb" if preview_bands == 3 else "grayscale"
            ),
            "display_stretch": stretch_details,
            "display_only": True,
        })

        return display_info


def _generic_band_statistics(
    source_path: Path,
    deadline: float,
) -> tuple[int, int, list[dict[str, Any]]]:
    """
    Calculate raw-DN statistics for each band.

    Each band's statistics use its own finite, dataset-mask-valid pixel
    count. No CIcyano quality flags or product scaling are applied.
    """
    with rasterio.open(source_path) as source:
        count = source.count

        sums = np.zeros(count, dtype=np.float64)
        sums_squared = np.zeros(count, dtype=np.float64)
        valid_counts = np.zeros(count, dtype=np.int64)

        minima = np.full(count, np.inf, dtype=np.float64)
        maxima = np.full(count, -np.inf, dtype=np.float64)

        total_pixel_count = source.width * source.height
        dataset_valid_count = 0

        for window in _windows(source.width, source.height):
            _check_deadline(
                deadline,
                "Satellite statistics exceeded the processing time limit.",
            )

            dataset_mask = (
                source.dataset_mask(window=window) > 0
            )
            dataset_valid_count += int(
                np.count_nonzero(dataset_mask)
            )

            for band_index in range(1, count + 1):
                values = source.read(
                    band_index,
                    window=window,
                ).astype(np.float64)

                valid = dataset_mask & np.isfinite(values)
                selected = values[valid]

                if selected.size == 0:
                    continue

                index = band_index - 1

                valid_counts[index] += selected.size
                sums[index] += float(
                    np.sum(selected, dtype=np.float64)
                )
                sums_squared[index] += float(
                    np.sum(
                        np.square(selected),
                        dtype=np.float64,
                    )
                )

                minima[index] = min(
                    minima[index],
                    float(np.min(selected)),
                )
                maxima[index] = max(
                    maxima[index],
                    float(np.max(selected)),
                )

        statistics = []

        for index in range(count):
            band_count = int(valid_counts[index])

            if band_count == 0:
                mean = standard_deviation = None
                minimum = maximum = None
            else:
                mean = float(sums[index] / band_count)

                variance = max(
                    float(
                        sums_squared[index] / band_count
                        - mean * mean
                    ),
                    0.0,
                )

                standard_deviation = float(np.sqrt(variance))
                minimum = float(minima[index])
                maximum = float(maxima[index])

            statistics.append({
                "band": index + 1,
                "description": (
                    source.descriptions[index]
                    or f"Band {index + 1}"
                ),
                "valid_pixel_count": band_count,
                "minimum_raw_dn": minimum,
                "maximum_raw_dn": maximum,
                "mean_raw_dn": mean,
                "standard_deviation_raw_dn": standard_deviation,
                "units": (
                    "raw digital numbers (DN); "
                    "product scaling not applied"
                ),
            })

    return (
        dataset_valid_count,
        total_pixel_count,
        statistics,
    )



def _product_specific_band_statistics(
    source_path: Path,
    metadata: dict[str, Any],
    deadline: float,
) -> dict[str, Any] | None:
    """
    Calculate product-specific scaled statistics only when the exact
    product and reverse-scaling formula match the supported registry.

    Product flags are read from that TIFF's own metadata. This helper
    is deliberately separate from the CIcyano screening pipeline.
    """
    products = {
        "ci": {
            "formula": "10**(3.0 / 250.0 * DN - 4.2)",
            "units": "dimensionless index",
            "label": "Chlorophyll Index",
            "scale": lambda dn: np.power(
                10.0, (3.0 / 250.0 * dn) - 4.2
            ),
        },
        "ci-cicyano": {
            "formula": "10**(3.0 / 250.0 * DN - 4.2)",
            "units": "dimensionless index",
            "label": "CI-CIcyano composite index",
            "scale": lambda dn: np.power(
                10.0, (3.0 / 250.0 * dn) - 4.2
            ),
        },
        "cinonfluor": {
            "formula": "10**(3.0 / 250.0 * DN - 4.2)",
            "units": "dimensionless index",
            "label": "Non-fluorescing cyanobacteria index",
            "scale": lambda dn: np.power(
                10.0, (3.0 / 250.0 * dn) - 4.2
            ),
        },
        "kd_rhos": {
            "formula": "2.71828 / ((325.0 / DN) - 1)",
            "units": "m-1",
            "label": "Diffuse attenuation coefficient",
            "scale": lambda dn: 2.71828 / ((325.0 / dn) - 1.0),
        },
        "rbd_rhos": {
            "formula": "10**(DN / 150. - 4)",
            "units": "dimensionless reflectance",
            "label": "Remote-sensing reflectance",
            "scale": lambda dn: np.power(10.0, dn / 150.0 - 4.0),
        },
        "rrs665": {
            "formula": "0.00609675 / ((270.0 / DN) - 1)",
            "units": "sr-1",
            "label": "Remote-sensing reflectance at 665 nm",
            "scale": lambda dn: 0.00609675 / ((270.0 / dn) - 1.0),
        },
        "chloc4_global": {
            "formula": "10**(0.012 * DN - 1.3)",
            "units": "mg m-3",
            "label": "Global chlorophyll concentration",
            "scale": lambda dn: np.power(10.0, 0.012 * dn - 1.3),
        },
        "chl_switch": {
            "formula": "13.46374 / ((275.0 / DN) - 1)",
            "units": "mg m-3",
            "label": "Switched chlorophyll concentration",
            "scale": lambda dn: 13.46374 / ((275.0 / dn) - 1.0),
        },
    }

    product_name = str(metadata.get("product_name") or "").strip().lower()
    config = products.get(product_name)

    if config is None:
        return None

    supplied_formula = metadata.get("scale_formula_metadata")
    normalize = lambda value: re.sub(
        r"[\s\"']", "", str(value or "")
    ).lower()

    if normalize(supplied_formula) != normalize(config["formula"]):
        return None

    with rasterio.open(source_path) as src:
        if src.count != 1 or src.dtypes[0] != "uint8":
            return None

        tags = src.tags()
        documented_flags = set()

        for key, value in tags.items():
            if not key.lower().startswith("saps_product_flag_"):
                continue
            try:
                documented_flags.add(int(float(str(value).strip())))
            except (TypeError, ValueError):
                continue

        if src.nodata is not None:
            try:
                documented_flags.add(int(src.nodata))
            except (TypeError, ValueError, OverflowError):
                pass

        total_pixels = src.width * src.height
        dataset_valid_count = 0
        valid_count = 0

        raw_sum = 0.0
        raw_sum_sq = 0.0
        raw_min = np.inf
        raw_max = -np.inf

        scaled_sum = 0.0
        scaled_sum_sq = 0.0
        scaled_min = np.inf
        scaled_max = -np.inf

        for window in _windows(src.width, src.height):
            _check_deadline(
                deadline,
                "Product-specific statistics exceeded the processing time limit.",
            )

            values = src.read(1, window=window).astype(np.float64)
            mask = src.read_masks(1, window=window) > 0

            dataset_valid_count += int(np.count_nonzero(mask))

            valid = mask & np.isfinite(values) & (values > 0)

            for flag in documented_flags:
                valid &= values != flag

            selected = values[valid]
            if selected.size == 0:
                continue

            # These uint8 product formulas have positive physical
            # denominators over their supported stored-value domain.
            with np.errstate(
                divide="ignore",
                invalid="ignore",
                over="ignore",
            ):
                scaled = config["scale"](selected)

            physical = np.isfinite(scaled) & (scaled > 0)
            selected = selected[physical]
            scaled = scaled[physical]

            if selected.size == 0:
                continue

            valid_count += int(selected.size)

            raw_sum += float(np.sum(selected, dtype=np.float64))
            raw_sum_sq += float(np.sum(selected * selected, dtype=np.float64))
            raw_min = min(raw_min, float(np.min(selected)))
            raw_max = max(raw_max, float(np.max(selected)))

            scaled_sum += float(np.sum(scaled, dtype=np.float64))
            scaled_sum_sq += float(np.sum(scaled * scaled, dtype=np.float64))
            scaled_min = min(scaled_min, float(np.min(scaled)))
            scaled_max = max(scaled_max, float(np.max(scaled)))

        if valid_count == 0:
            return {
                "valid_pixel_count": 0,
                "total_pixel_count": total_pixels,
                "dataset_valid_pixel_count": dataset_valid_count,
                "statistics": [{
                    "band": 1,
                    "description": src.descriptions[0] or "Band 1",
                    "valid_pixel_count": 0,
                    "units": config["units"],
                    "minimum_scaled": None,
                    "maximum_scaled": None,
                    "mean_scaled": None,
                    "standard_deviation_scaled": None,
                }],
                "units": config["units"],
                "label": config["label"],
            }

        raw_mean = raw_sum / valid_count
        scaled_mean = scaled_sum / valid_count

        raw_variance = max(
            raw_sum_sq / valid_count - raw_mean * raw_mean, 0.0
        )
        scaled_variance = max(
            scaled_sum_sq / valid_count - scaled_mean * scaled_mean, 0.0
        )

        statistics = [{
            "band": 1,
            "description": src.descriptions[0] or "Band 1",
            "valid_pixel_count": valid_count,
            "minimum_raw_dn": raw_min,
            "maximum_raw_dn": raw_max,
            "mean_raw_dn": raw_mean,
            "standard_deviation_raw_dn": float(np.sqrt(raw_variance)),
            "minimum_scaled": scaled_min,
            "maximum_scaled": scaled_max,
            "mean_scaled": scaled_mean,
            "standard_deviation_scaled": float(np.sqrt(scaled_variance)),
            "units": config["units"],
        }]

    return {
        "valid_pixel_count": valid_count,
        "total_pixel_count": total_pixels,
        "dataset_valid_pixel_count": dataset_valid_count,
        "statistics": statistics,
        "units": config["units"],
        "label": config["label"],
    }


def analyze_generic_satellite_product(
    source_path: Path,
    analysis_id: str,
    output_dir: Path,
    metadata: dict[str, Any],
    timeout_seconds: int = MAX_ANALYSIS_SECONDS,
) -> dict[str, Any]:
    """
    Produce a preview and product-specific statistics where supported.

    No CIcyano scaling, quality flags, HAB threshold, or hotspot
    algorithm is applied.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    preview_path = output_dir / f"{analysis_id}-overlay.png"
    deadline = time.monotonic() + timeout_seconds
    succeeded = False

    try:
        capability = metadata.get(
            "analysis_capability",
            "metadata_preview",
        )

        preview = _create_generic_preview(
            source_path,
            preview_path,
            capability,
            deadline,
        )

        product_statistics = _product_specific_band_statistics(
            source_path,
            metadata,
            deadline,
        )

        if product_statistics is not None:
            valid_count = product_statistics["valid_pixel_count"]
            total_count = product_statistics["total_pixel_count"]
            band_statistics = product_statistics["statistics"]
            scaled_analysis = True
            indicator_units = product_statistics["units"]
            analysis_method = (
                "Metadata-checked product-specific scaling and "
                "tiled descriptive statistics"
            )
            analysis_status = "PRODUCT_SPECIFIC_SCALED_STATISTICS"
            product_analysis_label = product_statistics["label"]
        else:
            valid_count, total_count, band_statistics = (
                _generic_band_statistics(
                    source_path,
                    deadline,
                )
            )
            scaled_analysis = False
            indicator_units = "raw digital numbers (DN)"
            analysis_method = (
                "Display preview and raw-DN descriptive statistics"
            )
            analysis_status = "PREVIEW_ONLY"
            product_analysis_label = None

        valid_percentage = (
            valid_count * 100.0 / total_count
            if total_count
            else None
        )

        warnings = list(metadata.get("warnings", []))

        warnings.append(
            "This is a product preview, not a CIcyano screening result. "
            "No CIcyano quality flags, scale formula, HAB threshold, "
            "or hotspot algorithm was applied."
        )

        if scaled_analysis:
            warnings.append(
                "Scaled statistics use a product-specific formula found in "
                "the GeoTIFF metadata and checked against the application's "
                "formula registry. Metadata provenance is not independently "
                "authenticated; results are not HAB detection or prediction."
            )
        elif capability in {
            "metadata_preview",
            "indicator_preview",
        }:
            warnings.append(
                "The product formula did not pass the application's exact "
                "formula check, or this product is not supported for scaled "
                "statistics. Raw-DN statistics are shown instead."
            )

        if capability == "rgb_preview":
            warnings.append(
                "The RGB preview uses a display stretch for visibility. "
                "Display values are not calibrated scientific measurements."
            )

        result = {
            "status": "success",
            "analysis_id": analysis_id,
            "filename": metadata.get("filename"),
            "sensor": metadata.get("sensor"),
            "product_name": metadata.get("product_name"),
            "product_type": metadata.get("product_type"),
            "product_family": metadata.get("product_family"),
            "analysis_capability": capability,
            "product_version": metadata.get("product_version"),
            "acquisition_date": metadata.get("acquisition_date"),
            "crs": metadata.get("crs"),
            "bounds": metadata.get("bounds"),
            "display": preview,
            "spatial_resolution": metadata.get("spatial_resolution"),
            "band_count": metadata.get("band_count"),
            "band_descriptions": metadata.get("band_descriptions"),
            "quality": {
                "valid_pixel_percentage": valid_percentage,
                "valid_pixel_count": valid_count,
                "invalid_pixel_count": total_count - valid_count,
                "coverage_description": (
                    "Product-specific valid-pixel coverage after "
                    "dataset-mask, reserved-flag, and value-domain checks."
                ),
                "warnings": warnings,
            },
            "analysis": {
                "method": analysis_method,
                "analysis_status": analysis_status,
                "product_analysis_label": product_analysis_label,
                "indicator_units": indicator_units,
                "band_statistics": band_statistics,
                "hotspot_screening_performed": False,
                "indicator_hotspots_found": None,
                "possible_hab_indicator": None,
                "hotspot_pixel_count": None,
                "threshold": None,
            },
            "result_type": "product_preview",
            "model_accuracy": None,
            "outputs": {
                "overlay_url": (
                    f"/api/satellite-detection/result/{analysis_id}/overlay"
                ),
                "preview_url": (
                    f"/api/satellite-detection/result/{analysis_id}/overlay"
                ),
                "indicator_raster_url": None,
                "mask_raster_url": None,
            },
            "disclaimer": (
                "This output contains a product preview and, where supported, "
                "metadata-checked product-specific statistics. Product "
                "metadata is not independently authenticated. It is not "
                "HAB prediction or confirmation of harmful algae."
            ),
        }

        succeeded = True
        return result

    finally:
        if not succeeded:
            preview_path.unlink(missing_ok=True)


def analyze_ci_cyano(
    source_path: Path,
    analysis_id: str,
    output_dir: Path,
    metadata: dict[str, Any],
    timeout_seconds: int = MAX_ANALYSIS_SECONDS,
) -> dict[str, Any]:
    """Create CIcyano indicator/mask rasters and map overlay."""
    output_dir.mkdir(parents=True, exist_ok=True)
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
            for suffix in (
                "-indicator.tif",
                "-mask.tif",
                "-overlay.png",
            ):
                (
                    output_dir / f"{analysis_id}{suffix}"
                ).unlink(missing_ok=True)


def _analyze_ci_cyano(
    source_path: Path,
    analysis_id: str,
    output_dir: Path,
    metadata: dict[str, Any],
    deadline: float,
) -> dict[str, Any]:
    indicator_path = output_dir / f"{analysis_id}-indicator.tif"
    mask_path = output_dir / f"{analysis_id}-mask.tif"
    overlay_path = output_dir / f"{analysis_id}-overlay.png"

    histogram = np.zeros(250, dtype=np.int64)
    total_pixels = 0
    valid_count = 0

    quality_counts = {
        value: 0 for value in RESERVED_QUALITY_VALUES
    }

    scale_formula = metadata.get("scale_formula")
    scale_lookup = _scale_lookup(scale_formula)

    with rasterio.open(source_path) as source:
        if source.count != 1:
            raise ValueError(
                "CIcyano screening requires a single-band raster."
            )

        for window in _windows(source.width, source.height):
            _check_deadline(
                deadline,
                "Satellite screening exceeded its processing time limit.",
            )

            values = source.read(
                1,
                window=window,
                masked=False,
            )

            valid_mask = _valid_product_pixels(
                values,
                source.read_masks(1, window=window),
            )

            total_pixels += values.size

            valid_values = values[valid_mask].astype(
                np.uint8,
                copy=False,
            )

            valid_count += int(valid_values.size)

            if valid_values.size:
                histogram += np.bincount(
                    valid_values,
                    minlength=250,
                )[:250]

            for value in quality_counts:
                quality_counts[value] += int(
                    np.count_nonzero(values == value)
                )

        first_quartile = _quantile_scaled(
            histogram, 0.25, scale_lookup
        )
        median = _quantile_scaled(
            histogram, 0.50, scale_lookup
        )
        third_quartile = _quantile_scaled(
            histogram, 0.75, scale_lookup
        )

        percentiles = {
            f"p{percentile}": _quantile_scaled(
                histogram,
                percentile / 100,
                scale_lookup,
            )
            for percentile in (25, 50, 75, 90, 95, 99)
        }

        occupied = np.flatnonzero(histogram)

        minimum = (
            float(scale_lookup[occupied[0]])
            if occupied.size
            else None
        )
        maximum = (
            float(scale_lookup[occupied[-1]])
            if occupied.size
            else None
        )

        valid_percentage = (
            valid_count * 100.0 / total_pixels
            if total_pixels
            else None
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
            counts = histogram.astype(np.float64)

            mean = float(
                np.dot(counts, scale_lookup) / valid_count
            )

            variance = max(
                float(
                    np.dot(counts, np.square(scale_lookup))
                    / valid_count
                )
                - mean * mean,
                0.0,
            )

            standard_deviation = float(np.sqrt(variance))

            threshold = (
                third_quartile
                + 1.5 * (third_quartile - first_quartile)
                if (
                    screening_permitted
                    and first_quartile is not None
                    and third_quartile is not None
                )
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
        mask_profile.update(
            dtype="uint8",
            nodata=NODATA_MASK,
        )

        high_pixels = 0

        with rasterio.open(
            indicator_path,
            "w",
            **profile,
        ) as indicator_dst, rasterio.open(
            mask_path,
            "w",
            **mask_profile,
        ) as mask_dst:

            indicator_dst.update_tags(
                product="Sentinel-3 OLCI CIcyano",
                indicator_units=metadata["indicator_units"],
                scale_formula=scale_formula,
                source_values=(
                    "scaled from stored uint8 digital numbers"
                ),
            )

            mask_dst.update_tags(
                product="Sentinel-3 OLCI CIcyano",
                mask_values=(
                    "0=below relative threshold, "
                    "1=above relative threshold, "
                    "255=invalid or screening not performed"
                ),
                threshold_source=(
                    "Scene-specific Tukey upper fence; "
                    "not a biological HAB threshold."
                    if screening_permitted
                    else "Not calculated because valid-pixel coverage was below 10%."
                ),
            )

            for window in _windows(source.width, source.height):
                _check_deadline(
                    deadline,
                    "Satellite screening exceeded its processing time limit.",
                )

                values = source.read(
                    1,
                    window=window,
                    masked=False,
                )

                valid_mask = _valid_product_pixels(
                    values,
                    source.read_masks(1, window=window),
                )

                valid_values = _scaled_ci(
                    values,
                    scale_lookup,
                ).astype(np.float32)

                indicator_values = np.where(
                    valid_mask,
                    valid_values,
                    NODATA_FLOAT,
                ).astype(np.float32)

                if screening_permitted and threshold is not None:
                    high_mask = (
                        valid_mask & (valid_values > threshold)
                    )

                    mask_values = np.where(
                        valid_mask,
                        high_mask.astype(np.uint8),
                        NODATA_MASK,
                    ).astype(np.uint8)

                else:
                    high_mask = np.zeros_like(valid_mask)

                    mask_values = np.full(
                        values.shape,
                        NODATA_MASK,
                        dtype=np.uint8,
                    )

                indicator_dst.write(
                    indicator_values,
                    1,
                    window=window,
                )

                mask_dst.write(
                    mask_values,
                    1,
                    window=window,
                )

                high_pixels += int(
                    np.count_nonzero(high_mask)
                )

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

        cloud_percentage = (
            quality_counts[253] * 100.0 / total_pixels
            if total_pixels
            else None
        )

    warnings = list(metadata.get("warnings", []))

    if not valid_count:
        screening_status = "NO_VALID_PIXELS"
        warnings.append(
            "No valid pixels remained after quality masking. "
            "Hotspot screening was not performed."
        )

    elif not screening_permitted:
        screening_status = "INSUFFICIENT_COVERAGE"
        warnings.append(
            "Hotspot screening was not performed because fewer than "
            "10% of image pixels are valid. This is an engineering "
            "safeguard, not a scientific confidence threshold."
        )

    elif coverage_category == "LOW_COVERAGE":
        screening_status = (
            "NO_RELATIVE_HOTSPOTS"
            if high_pixels == 0
            else "RELATIVE_HOTSPOTS_DETECTED"
        )

        warnings.append(
            "Low valid-pixel coverage (10% to below 25%): relative "
            "screening may be unstable or unrepresentative."
        )

    elif high_pixels == 0:
        screening_status = "NO_RELATIVE_HOTSPOTS"
        warnings.append(
            "No pixels exceeded the scene-relative Tukey upper fence. "
            "This does not establish that the waterbody is HAB-free."
        )

    else:
        screening_status = "RELATIVE_HOTSPOTS_DETECTED"

    return {
        "status": "success",
        "analysis_id": analysis_id,
        "filename": metadata["filename"],
        "sensor": metadata["sensor"],
        "product_name": metadata.get("product_name"),
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
            "method": (
                "Sentinel-3 OLCI CIcyano scene-relative hotspot screening"
            ),
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
            "hotspot_pixel_count": (
                high_pixels if screening_permitted else None
            ),
            "hotspot_pixel_percentage": high_percentage,
            "threshold_source": (
                "Scene-specific Tukey upper fence (Q3 + 1.5 × IQR); "
                "relative outlier screen, not a biological HAB threshold."
                if screening_permitted
                else (
                    "Not calculated because no valid pixels remained."
                    if not valid_count
                    else (
                        "Not calculated because valid-pixel coverage "
                        "was below the 10% engineering safeguard."
                    )
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
            "overlay_url": (
                f"/api/satellite-detection/result/{analysis_id}/overlay"
            ),
            "indicator_raster_url": (
                f"/api/satellite-detection/result/{analysis_id}/indicator"
            ),
            "mask_raster_url": (
                f"/api/satellite-detection/result/{analysis_id}/mask"
            ),
        },
        "disclaimer": (
            "This result is an experimental satellite-based screening "
            "output. A detected spectral indicator does not confirm toxic "
            "HAB presence or identify the responsible species. Field "
            "sampling and laboratory verification may be required."
        ),
    }


def analyze_satellite_product(
    source_path: Path,
    analysis_id: str,
    output_dir: Path,
    metadata: dict[str, Any],
    timeout_seconds: int = MAX_ANALYSIS_SECONDS,
) -> dict[str, Any]:
    """
    Dispatch according to the identified product capability.

    Only verified CIcyano products enter CIcyano screening.
    All other recognized products receive a generic preview.
    """
    capability = metadata.get("analysis_capability")

    if capability == "ci_cyano_screening":
        return analyze_ci_cyano(
            source_path=source_path,

            analysis_id=analysis_id,
            output_dir=output_dir,
            metadata=metadata,
            timeout_seconds=timeout_seconds,
        )

    return analyze_generic_satellite_product(
        source_path=source_path,
        analysis_id=analysis_id,
        output_dir=output_dir,
        metadata=metadata,
        timeout_seconds=timeout_seconds,
    )
