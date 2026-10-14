"""Tests for real-source dataset preparation without synthetic labels."""

import csv
from datetime import datetime, timezone

import pandas as pd
from PIL import Image

from data.prepare_features import prepare_table
from scripts.prepare_hab_observations import observation_date
from scripts.prepare_hab_dataset import prepare_dataset


def test_preparation_validates_coordinates_and_preserves_missing_values():
    source = pd.DataFrame(
        {
            "SAMPLE_DATE": ["2026-01-01", "invalid", "2026-01-03"],
            "LATITUDE": [27.5, 28.0, 91.0],
            "LONGITUDE": [-83.0, -82.0, -83.0],
            "CELLCOUNT": [1200, 0, 50],
            "WATER_TEMP": [None, 24.0, 25.0],
        }
    )
    prepared, rejected = prepare_table(source)
    assert rejected == 2
    assert len(prepared) == 1
    assert "hab_label" not in prepared.columns
    assert pd.isna(prepared.loc[0, "water_temperature"])


def test_cell_count_does_not_create_a_hab_label():
    source = pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-02"],
            "lat": [27.5, 27.6],
            "lon": [-83.0, -83.1],
            "cell_count": [None, 0],
        }
    )
    prepared, _ = prepare_table(source)
    assert "hab_label" not in prepared.columns


def test_image_manifest_preserves_metadata_without_inventing_labels(tmp_path):
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    image_path = images_dir / "sentinel-3.2026242.fixture.truecolor.tif"
    Image.new("RGB", (12, 8), color=(10, 20, 30)).save(image_path, format="TIFF")

    summary = prepare_dataset(images_dir, tmp_path / "processed", tmp_path)
    with (tmp_path / "processed" / "hab_image_manifest.csv").open(encoding="utf-8") as manifest_file:
        row = next(csv.DictReader(manifest_file))

    assert summary["valid_images"] == 1
    assert summary["trainable_records"] == 0
    assert row["filename_date"] == "2026-08-30"
    assert row["date_semantics"] == "filename product date only; not an HAB observation date"
    assert row["hab_label"] == ""
    assert row["label_status"] == "unlabeled_no_verified_image_link"


def test_habsos_sample_date_remains_date_only():
    source_timestamp = int(datetime(2026, 9, 12, tzinfo=timezone.utc).timestamp() * 1000)

    assert observation_date(source_timestamp) == "2026-09-12"
