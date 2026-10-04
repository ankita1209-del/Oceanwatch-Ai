"""Tests for real-source dataset preparation without synthetic labels."""

import pandas as pd

from data.prepare_features import prepare_table


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
