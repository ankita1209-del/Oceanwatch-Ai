
"""Secure upload and product-aware analysis endpoints for Sentinel-3 GeoTIFFs."""

from __future__ import annotations

import json
import logging
import re
import tempfile
import uuid

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy
import pyproj
import rasterio

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import __version__ as pillow_version
from starlette.concurrency import run_in_threadpool

from backend.config import get_settings

from backend.services.satellite_processor import (
    MAX_ANALYSIS_SECONDS,
    analyze_satellite_product,
)

from backend.services.satellite_hab_results import (
    build_satellite_hab_results,
)

from backend.services.satellite_validator import (
    SatelliteValidationError,
    inspect_satellite_raster,
)


logger = logging.getLogger("oceanwatch.satellite_detection")

router = APIRouter()

MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_MULTIPART_OVERHEAD_BYTES = 1024 * 1024

MAX_CONCURRENT_UPLOADS = 2
MAX_CONCURRENT_ANALYSES = 1

ANALYSIS_TIMEOUT_SECONDS = MAX_ANALYSIS_SECONDS

UPLOAD_TTL = timedelta(hours=24)

UPLOAD_DIRECTORY = (
    Path(tempfile.gettempdir())
    / "oceanwatch-satellite-detection"
)

ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")

SUPPORTED_PRODUCTS = [
    "CIcyano",
    "CI-CIcyano",
    "CI",
    "CInonfluor",
    "Kd_Rhos",
    "truecolor",
    "landwatercolor",
    "rbd_rhos",
    "rrs665",
    "chloc4_global",
    "chl_switch",
]


def _directory() -> Path:
    UPLOAD_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    return UPLOAD_DIRECTORY


def _file_id(value: str) -> str:
    if not ID_PATTERN.fullmatch(value):
        raise HTTPException(
            status_code=404,
            detail="Uploaded satellite image was not found.",
        )

    return value


def _paths(file_id: str) -> tuple[Path, Path]:
    base = _directory()

    return (
        base / f"{file_id}.tif",
        base / f"{file_id}.json",
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(
            path.read_text(encoding="utf-8")
        )

    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=404,
            detail="Satellite analysis was not found or has expired.",
        ) from exc


def _write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    temporary_path = path.with_suffix(".json.tmp")

    temporary_path.write_text(
        json.dumps(
            payload,
            allow_nan=False,
        ),
        encoding="utf-8",
    )

    temporary_path.replace(path)


def _cleanup_expired_uploads() -> None:
    cutoff = (
        datetime.now(timezone.utc)
        - UPLOAD_TTL
    )

    directory = _directory()

    for manifest_path in directory.glob(
        "[0-9a-f]" * 32 + ".json"
    ):
        try:
            modified_at = datetime.fromtimestamp(
                manifest_path.stat().st_mtime,
                timezone.utc,
            )

            if modified_at >= cutoff:
                continue

            file_id = manifest_path.stem

            if not ID_PATTERN.fullmatch(file_id):
                continue

            try:
                manifest = _read_json(manifest_path)

            except HTTPException:
                logger.warning(
                    "Could not read an expired satellite upload manifest."
                )
                continue

            for suffix in (".json", ".tif"):
                target = directory / f"{file_id}{suffix}"

                if target.is_file():
                    target.unlink()

            for analysis_id in manifest.get(
                "analysis_ids",
                [],
            ):
                if (
                    not isinstance(analysis_id, str)
                    or not ID_PATTERN.fullmatch(analysis_id)
                ):
                    continue

                for suffix in (
                    "-result.json",
                    "-indicator.tif",
                    "-mask.tif",
                    "-overlay.png",
                ):
                    target = (
                        directory
                        / f"{analysis_id}{suffix}"
                    )

                    if target.is_file():
                        target.unlink()

        except OSError:
            logger.warning(
                "Could not clean an expired satellite upload artifact."
            )


def cleanup_expired_satellite_uploads() -> None:
    """Remove expired uploads and their generated analysis artifacts."""

    _cleanup_expired_uploads()


@router.post("/satellite-detection/upload")
async def upload_satellite_image(
    file: UploadFile = File(...),
):
    """Store an upload and validate its product metadata."""

    original_filename = Path(
        file.filename or ""
    ).name

    if Path(original_filename).suffix.lower() not in {
        ".tif",
        ".tiff",
    }:
        raise HTTPException(
            status_code=415,
            detail=(
                "Only GeoTIFF files with a .tif or .tiff "
                "extension are accepted."
            ),
        )

    _cleanup_expired_uploads()

    file_id = uuid.uuid4().hex

    path, manifest_path = _paths(file_id)

    size = 0

    try:
        with path.open("xb") as destination:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)

                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "Upload exceeds the 100 MiB size limit."
                        ),
                    )

                destination.write(chunk)

        if size == 0:
            raise HTTPException(
                status_code=422,
                detail="The uploaded file is empty.",
            )

        metadata = await run_in_threadpool(
            inspect_satellite_raster,
            path,
            original_filename,
        )

        metadata["filename"] = original_filename
        metadata["file_size_bytes"] = size

        _write_json(
            manifest_path,
            {
                "metadata": metadata,
                "uploaded_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "analysis_ids": [],
            },
        )

        return {
            "file_id": file_id,
            "filename": original_filename,
            "file_size_bytes": size,
            "validation": metadata,
        }

    except SatelliteValidationError as exc:
        path.unlink(missing_ok=True)

        status_code = (
            504
            if exc.status == "PROCESSING_TIMEOUT"
            else 422
        )

        raise HTTPException(
            status_code=status_code,
            detail={
                "status": exc.status,
                "message": exc.message,
            },
        ) from exc

    except HTTPException:
        path.unlink(missing_ok=True)
        raise

    except OSError as exc:
        path.unlink(missing_ok=True)

        logger.exception(
            "Could not store satellite upload."
        )

        raise HTTPException(
            status_code=500,
            detail="The satellite image could not be stored.",
        ) from exc

    finally:
        await file.close()


@router.get("/satellite-detection/validate/{file_id}")
async def validate_satellite_image(file_id: str):
    """Return the validation metadata for an uploaded image."""

    file_id = _file_id(file_id)

    _, manifest_path = _paths(file_id)

    manifest = _read_json(manifest_path)

    return manifest["metadata"]


@router.post("/satellite-detection/analyze/{file_id}")
async def analyze_satellite_image(file_id: str):
    """Run product analysis and experimental CIcyano model inference."""

    file_id = _file_id(file_id)

    raster_path, manifest_path = _paths(file_id)

    manifest = _read_json(manifest_path)

    if not raster_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=(
                "Uploaded satellite image was not found or has expired."
            ),
        )

    metadata = manifest.get("metadata")

    if not isinstance(metadata, dict):
        raise HTTPException(
            status_code=422,
            detail=(
                "Satellite upload metadata is missing or invalid."
            ),
        )

    capability = metadata.get("analysis_capability")

    if not capability:
        raise HTTPException(
            status_code=422,
            detail=(
                "The uploaded product has no recognized analysis capability."
            ),
        )

    analysis_id = uuid.uuid4().hex

    try:
        # Run the existing product-specific raster analysis.
        result = await run_in_threadpool(
            analyze_satellite_product,
            raster_path,
            analysis_id,
            _directory(),
            metadata,
            ANALYSIS_TIMEOUT_SECONDS,
        )

    except TimeoutError as exc:
        logger.warning(
            "Satellite product analysis exceeded its processing time limit."
        )

        raise HTTPException(
            status_code=504,
            detail=(
                f"Satellite analysis exceeded the "
                f"{ANALYSIS_TIMEOUT_SECONDS}-second processing limit."
            ),
        ) from exc

    except (
        OSError,
        ValueError,
        rasterio.errors.RasterioError,
    ) as exc:
        logger.exception(
            "Satellite product analysis failed for capability %s.",
            capability,
        )

        raise HTTPException(
            status_code=422,
            detail=(
                "The uploaded satellite product could not be processed. "
                "Check its product metadata and raster structure."
            ),
        ) from exc

    # Load the correct ResNet-18 detection model settings.
    settings = get_settings()

    # Run experimental inference only for supported CIcyano images.
    # Other products remain preview-only.
    result["hab_detection"] = await run_in_threadpool(
        build_satellite_hab_results,
        raster_path,
        metadata,
        result,
        settings.DETECTION_MODEL_PATH,
        settings.DETECTION_MODEL_METADATA_PATH,
    )

    # Save the complete analysis result.
    _write_json(
        _directory() / f"{analysis_id}-result.json",
        result,
    )

    # Preserve the existing upload-to-analysis relationship.
    analysis_ids = manifest.get(
        "analysis_ids",
        [],
    )

    if not isinstance(analysis_ids, list):
        analysis_ids = []

    analysis_ids.append(analysis_id)

    manifest["analysis_ids"] = analysis_ids

    _write_json(
        manifest_path,
        manifest,
    )

    return result


@router.get("/satellite-detection/result/{analysis_id}")
async def get_satellite_analysis(analysis_id: str):
    """Return a completed satellite analysis."""

    analysis_id = _file_id(analysis_id)

    return _read_json(
        _directory() / f"{analysis_id}-result.json"
    )


@router.get("/satellite-detection/result/{analysis_id}/overlay")
async def get_satellite_overlay(analysis_id: str):
    """Return the generated visual preview or CIcyano map overlay."""

    analysis_id = _file_id(analysis_id)

    path = (
        _directory()
        / f"{analysis_id}-overlay.png"
    )

    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail=(
                "Satellite preview was not found or has expired."
            ),
        )

    return FileResponse(
        path,
        media_type="image/png",
        filename=f"{analysis_id}-overlay.png",
    )


@router.get(
    "/satellite-detection/result/{analysis_id}/{output_kind}"
)
async def get_satellite_raster(
    analysis_id: str,
    output_kind: str,
):
    """Return generated CIcyano indicator or mask rasters."""

    analysis_id = _file_id(analysis_id)

    names = {
        "indicator": f"{analysis_id}-indicator.tif",
        "mask": f"{analysis_id}-mask.tif",
    }

    filename = names.get(output_kind)

    if not filename:
        raise HTTPException(
            status_code=404,
            detail="Satellite output was not found.",
        )

    path = _directory() / filename

    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail=(
                "Satellite output was not found or has expired."
            ),
        )

    return FileResponse(
        path,
        media_type="image/tiff",
        filename=filename,
    )


@router.get("/satellite-detection/health")
async def satellite_detection_health():
    """Report the supported products and processing capabilities."""

    return {
        "status": "available",
        "rasterio": True,
        "numpy": True,
        "supported_sensor": "Sentinel-3 OLCI",
        "supported_products": SUPPORTED_PRODUCTS,

        "analysis_capabilities": {
            "ci_cyano_screening": (
                "CIcyano only; scene-relative experimental screening"
            ),
            "rgb_preview": (
                "Three-band visual preview; not scientific interpretation"
            ),
            "indicator_preview": (
                "Single-band preview and raw-DN statistics"
            ),
            "metadata_preview": (
                "Generic preview and raw-DN statistics"
            ),
        },

        "dependencies": {
            "rasterio": rasterio.__version__,
            "numpy": numpy.__version__,
            "pyproj": pyproj.__version__,
            "pillow": pillow_version,
        },

        "temporary_storage_ttl_hours": (
            UPLOAD_TTL.total_seconds() / 3600
        ),

        "max_upload_bytes": MAX_UPLOAD_BYTES,
        "max_concurrent_uploads": MAX_CONCURRENT_UPLOADS,
        "max_concurrent_analyses": MAX_CONCURRENT_ANALYSES,
        "analysis_timeout_seconds": ANALYSIS_TIMEOUT_SECONDS,
        "display_crs": "EPSG:3857",
    }
