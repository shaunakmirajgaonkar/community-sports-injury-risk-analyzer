
from pathlib import Path
import pandas as pd
from analytics import normalize_columns, build_scores, build_sport_summary, build_incident_summary

ROOT = Path(__file__).resolve().parent

surfaces = normalize_columns(pd.read_csv(ROOT / "data/sample_surface_conditions.csv"))
weather = normalize_columns(pd.read_csv(ROOT / "data/sample_weather_conditions.csv"))
usage = normalize_columns(pd.read_csv(ROOT / "data/sample_facility_usage.csv"))
equipment = normalize_columns(pd.read_csv(ROOT / "data/sample_equipment_checks.csv"))
incidents = normalize_columns(pd.read_csv(ROOT / "data/sample_incident_reports.csv"))

scored = build_scores(surfaces, weather, usage, equipment, incidents)
sport_summary = build_sport_summary(scored)
incident_summary = build_incident_summary(incidents)

assert len(scored) == 12
assert scored["injury_risk_score"].between(0, 100).all()
assert scored["risk_band"].notna().all()
assert scored["primary_driver"].notna().all()
assert scored["review_priority_rank"].ge(1).all()
assert scored["surface_pressure"].between(0, 1).all()
assert scored["weather_pressure"].between(0, 1).all()
assert scored["usage_pressure"].between(0, 1).all()
assert scored["equipment_pressure"].between(0, 1).all()
assert scored["incident_pressure"].between(0, 1).all()
assert len(sport_summary) == 5
assert len(incident_summary) > 0
assert len(set(scored.columns)) == len(scored.columns)

print("PASS: community sports injury-risk screening")
print("Facilities:", len(scored))
print("Score range:", float(scored["injury_risk_score"].min()), "-", float(scored["injury_risk_score"].max()))
print("Sports:", len(sport_summary))
print("Incident factor groups:", len(incident_summary))
