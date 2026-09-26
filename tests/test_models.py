"""Model training guard tests; these do not create scientific observations."""

import pandas as pd
import pytest

from src.hab_model import FEATURES, train_model


def test_training_rejects_feature_table_without_source_labels(tmp_path):
    input_path = tmp_path / "feature_schema.csv"
    pd.DataFrame(columns=[*FEATURES, "source"]).to_csv(input_path, index=False)

    with pytest.raises(ValueError, match="verified HAB labels"):
        train_model(
            input_path,
            "NOAA HABSOS and environmental product",
            tmp_path / "model.pkl",
            tmp_path / "model_metadata.json",
        )
