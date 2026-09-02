
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analytics import normalize_columns, safe_size, build_scores


def load():
    return (
        pd.read_csv(ROOT / "data/sample_surface_conditions.csv"),
        pd.read_csv(ROOT / "data/sample_weather_conditions.csv"),
        pd.read_csv(ROOT / "data/sample_facility_usage.csv"),
        pd.read_csv(ROOT / "data/sample_equipment_checks.csv"),
        pd.read_csv(ROOT / "data/sample_incident_reports.csv"),
    )


def test_duplicate_headers_are_safe():
    df = pd.DataFrame([[1, 2]], columns=["Zone", "Zone"])
    assert list(normalize_columns(df).columns) == ["zone", "zone__2"]


def test_plot_size_is_always_positive():
    df = pd.DataFrame({"x": [0, None, -2, 3]})
    out = safe_size(df, "x")
    assert (out["plot_size"] >= 1).all()


def test_scores_bounded_and_ranked():
    s, w, u, e, i = load()
    out = build_scores(s, w, u, e, i)
    assert len(out) == 12
    assert out["injury_risk_score"].between(0, 100).all()
    assert out["risk_band"].notna().all()
    assert out["review_priority_rank"].ge(1).all()


def test_all_explainable_components_exist():
    s, w, u, e, i = load()
    out = build_scores(s, w, u, e, i)
    required = {
        "surface_pressure", "weather_pressure", "usage_pressure",
        "equipment_pressure", "incident_pressure",
        "primary_driver", "review_action_count",
    }
    assert required.issubset(out.columns)
