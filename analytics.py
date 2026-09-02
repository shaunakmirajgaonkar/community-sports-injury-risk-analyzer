
from __future__ import annotations
import numpy as np
import pandas as pd


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    seen: dict[str, int] = {}
    names: list[str] = []
    for raw in out.columns:
        name = str(raw).strip().lower().replace("-", "_").replace(" ", "_") or "unnamed"
        seen[name] = seen.get(name, 0) + 1
        names.append(name if seen[name] == 1 else f"{name}__{seen[name]}")
    out.columns = names
    return out


def numeric(series: pd.Series, default: float = 0.0) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(default)


def unit(series: pd.Series) -> pd.Series:
    return numeric(series).clip(0, 1)


def safe_size(df: pd.DataFrame, source: str, target: str = "plot_size") -> pd.DataFrame:
    out = df.copy()
    values = (
        numeric(out[source], 1.0)
        .replace([np.inf, -np.inf], np.nan)
        .fillna(1.0)
        .abs()
        .clip(lower=1.0)
    )
    out[target] = values
    return out


def classify(score: pd.Series) -> pd.Series:
    return pd.cut(
        numeric(score),
        [-0.1, 24.9, 49.9, 74.9, 100.1],
        labels=["Low", "Moderate", "High", "Critical"],
    )


def build_scores(
    surfaces: pd.DataFrame,
    weather: pd.DataFrame,
    usage: pd.DataFrame,
    equipment: pd.DataFrame,
    incidents: pd.DataFrame,
) -> pd.DataFrame:
    s = normalize_columns(surfaces)
    w = normalize_columns(weather)
    u = normalize_columns(usage)
    e = normalize_columns(equipment)
    i = normalize_columns(incidents)

    incident_agg = i.groupby("facility_id", as_index=False).agg(
        incident_count_30d=("incident_count_30d", "max"),
        total_incident_records=("incident_id", "count"),
        high_critical_share=("severity", lambda x: x.astype(str).str.lower().isin(["high", "critical"]).mean()),
        injury_report_share=("reported_injury", lambda x: x.astype(str).str.lower().eq("yes").mean()),
        near_miss_share=("near_miss", lambda x: x.astype(str).str.lower().eq("yes").mean()),
    )

    equip = e.copy()
    equip["check_completion_rate"] = (
        numeric(equip["checks_completed"])
        / numeric(equip["checks_due"]).clip(lower=1)
    ).clip(0, 1)

    base = (
        s.merge(w, on="facility_id", how="left")
         .merge(u, on="facility_id", how="left")
         .merge(equip, on="facility_id", how="left")
         .merge(incident_agg, on="facility_id", how="left")
    )

    for col in base.columns:
        if pd.api.types.is_numeric_dtype(base[col]):
            base[col] = base[col].fillna(0)

    surface_pressure = (
        0.36 * (1 - unit(base["surface_condition_score"]))
        + 0.18 * (numeric(base["worn_area_pct"]) / 50).clip(0, 1)
        + 0.16 * unit(base["puddle_pressure_index"])
        + 0.12 * (numeric(base["maintenance_overdue_days"]) / 45).clip(0, 1)
        + 0.10 * (numeric(base["last_inspection_days"]) / 60).clip(0, 1)
        + 0.08 * (1 - unit(base["surface_cleanliness_index"]))
    ).clip(0, 1)

    weather_pressure = (
        0.42 * unit(base["heat_exposure_index"])
        + 0.22 * unit(base["weather_variability_index"])
        + 0.18 * unit(base["wind_exposure_index"])
        + 0.18 * (numeric(base["rainfall_mm"]) / 50).clip(0, 1)
    ).clip(0, 1)

    usage_pressure = (
        0.38 * unit(base["utilization_index"])
        + 0.22 * unit(base["capacity_pressure_index"])
        + 0.18 * (numeric(base["daily_users"]) / max(float(base["daily_users"].quantile(0.9)), 1)).clip(0, 1)
        + 0.12 * (numeric(base["session_duration_min"]) / 120).clip(0, 1)
        + 0.10 * (numeric(base["weekly_sessions"]) / 35).clip(0, 1)
    ).clip(0, 1)

    equipment_pressure = (
        0.28 * unit(base["equipment_issue_index"])
        + 0.20 * (1 - unit(base["protective_equipment_readiness"]))
        + 0.16 * (1 - unit(base["goal_post_check_index"]))
        + 0.12 * (1 - unit(base["lighting_equipment_index"]))
        + 0.14 * unit(base["maintenance_backlog_index"])
        + 0.10 * (1 - unit(base["check_completion_rate"]))
    ).clip(0, 1)

    incident_pressure = (
        0.36 * (numeric(base["incident_count_30d"]) / max(float(base["incident_count_30d"].max()), 1)).clip(0, 1)
        + 0.25 * unit(base["high_critical_share"])
        + 0.19 * unit(base["injury_report_share"])
        + 0.10 * unit(base["near_miss_share"])
        + 0.10 * (numeric(base["total_incident_records"]) / 10).clip(0, 1)
    ).clip(0, 1)

    base["injury_risk_score"] = (
        100 * (
            0.25 * surface_pressure
            + 0.17 * weather_pressure
            + 0.20 * usage_pressure
            + 0.18 * equipment_pressure
            + 0.20 * incident_pressure
        )
    ).clip(0, 100).round(1)

    base["risk_band"] = classify(base["injury_risk_score"])

    base["primary_driver"] = np.select(
        [
            surface_pressure >= 0.70,
            incident_pressure >= 0.70,
            equipment_pressure >= 0.70,
            usage_pressure >= 0.70,
            weather_pressure >= 0.70,
        ],
        [
            "Surface-condition pressure",
            "Incident-history pressure",
            "Equipment-control gaps",
            "Usage and capacity pressure",
            "Weather exposure pressure",
        ],
        default="Mixed facility risk factors",
    )

    base["review_action_count"] = (
        (surface_pressure >= 0.60).astype(int)
        + (weather_pressure >= 0.60).astype(int)
        + (usage_pressure >= 0.60).astype(int)
        + (equipment_pressure >= 0.60).astype(int)
        + (incident_pressure >= 0.60).astype(int)
    )

    base["review_priority_rank"] = (
        base["injury_risk_score"]
        .rank(method="dense", ascending=False)
        .astype(int)
    )

    base["surface_pressure"] = surface_pressure.round(3)
    base["weather_pressure"] = weather_pressure.round(3)
    base["usage_pressure"] = usage_pressure.round(3)
    base["equipment_pressure"] = equipment_pressure.round(3)
    base["incident_pressure"] = incident_pressure.round(3)
    return base


def build_sport_summary(scored: pd.DataFrame) -> pd.DataFrame:
    return (
        scored.groupby("sport_type", as_index=False)
        .agg(
            avg_risk=("injury_risk_score", "mean"),
            peak_risk=("injury_risk_score", "max"),
            facilities=("facility_id", "nunique"),
            avg_usage=("utilization_index", "mean"),
            avg_incidents=("incident_count_30d", "mean"),
        )
        .sort_values("avg_risk", ascending=False)
    )


def build_incident_summary(incidents: pd.DataFrame) -> pd.DataFrame:
    i = normalize_columns(incidents).copy()
    out = (
        i.groupby("risk_factor", as_index=False)
        .agg(
            incidents=("incident_id", "count"),
            max_30d_count=("incident_count_30d", "max"),
            injury_reports=("reported_injury", lambda x: x.astype(str).str.lower().eq("yes").sum()),
            near_misses=("near_miss", lambda x: x.astype(str).str.lower().eq("yes").sum()),
        )
        .sort_values("incidents", ascending=False)
    )
    return out
