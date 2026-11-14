from backend.services.satellite_hab_results import (
    build_satellite_hab_results,
)


def build_result(product_name, capability, coverage=None):
    return build_satellite_hab_results(
        "unused-image.tif",
        {
            "product_name": product_name,
            "analysis_capability": capability,
        },
        {"quality": {"coverage_category": coverage}},
        "unused-model.pkl",
        "unused-metadata.json",
    )


def test_model_inference_is_not_claimed_for_supported_products():
    for product_name in [
        "CIcyano",
        "truecolor",
        "landwatercolor",
        "CI",
        "Kd_Rhos",
    ]:
        result = build_result(
            product_name,
            "ci_cyano_screening"
            if product_name == "CIcyano"
            else "metadata_preview",
            "BETTER_COVERAGE",
        )

        assert result["experimental_model_score"] is None
        assert result["hab_probability"] is None
        assert result["risk_score"] is None
        assert result["risk_level"] is None
        assert result["model"]["inference_ran"] is False
        assert result["model"]["status"] == "not_run"
        assert result["model"]["name"] is None
        assert result["model"]["version"] is None


def test_insufficient_ci_cyano_coverage_is_explained():
    result = build_result(
        "CIcyano",
        "ci_cyano_screening",
        "INSUFFICIENT_COVERAGE",
    )

    assert result["model"]["inference_ran"] is False
    assert "insufficient" in result["model"]["reason"].lower()
    assert result["hab_probability"] is None


def test_generic_product_does_not_claim_hab_inference():
    result = build_result("truecolor", "rgb_preview")

    assert result["model"]["status"] == "not_run"
    assert result["model"]["inference_ran"] is False
    assert result["risk_score"] is None
