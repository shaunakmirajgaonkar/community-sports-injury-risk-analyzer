
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from analytics import (
    normalize_columns,
    safe_size,
    build_scores,
    build_sport_summary,
    build_incident_summary,
)

st.set_page_config(
    page_title="Community Sports Injury Risk Analyzer",
    page_icon="🏟️",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

REQUIRED_COLUMNS = {
    "surfaces": [
        "facility_id", "surface_type", "surface_condition_score",
        "worn_area_pct", "puddle_pressure_index", "last_inspection_days",
        "maintenance_overdue_days", "surface_cleanliness_index",
    ],
    "weather": [
        "facility_id", "avg_temp_c", "humidity_pct", "rainfall_mm",
        "heat_exposure_index", "weather_variability_index", "wind_exposure_index",
    ],
    "usage": [
        "facility_id", "sport_type", "daily_users", "peak_users",
        "weekly_sessions", "utilization_index", "session_duration_min",
        "capacity_pressure_index",
    ],
    "equipment": [
        "facility_id", "check_date", "checks_due", "checks_completed",
        "equipment_issue_index", "protective_equipment_readiness",
        "goal_post_check_index", "lighting_equipment_index",
        "maintenance_backlog_index",
    ],
    "incidents": [
        "incident_id", "facility_id", "incident_date", "sport_type",
        "severity", "risk_factor", "reported_injury", "near_miss",
        "body_area", "incident_count_30d",
    ],
}

st.markdown(
    """
<style>
.stApp{
    background:linear-gradient(180deg,#f9fcff 0%,#f5f8ff 45%,#fff7ef 100%);
    color:#23384a;
}
.block-container{max-width:1680px;padding-top:1rem;padding-bottom:2rem}
[data-testid="stSidebar"]{background:#ffffff;border-right:1px solid #dde6ef}
[data-testid="stSidebar"] *{color:#2a4052!important}
.hero{
    background:linear-gradient(135deg,#eef5ff 0%,#edfaff 45%,#fff1dc 100%);
    border:1px solid #dbe5ef;border-radius:30px;padding:30px 34px;
    margin-bottom:20px;box-shadow:0 16px 44px rgba(35,57,74,.06)
}
.eyebrow{font-size:.72rem;font-weight:900;letter-spacing:.16em;color:#2b68b6;text-transform:uppercase}
.hero h1{font-size:2.48rem;line-height:1.05;color:#233b4e!important;margin:.35rem 0 .65rem}
.hero p{color:#61737f;max-width:1380px;font-size:1rem}
.pill{
    display:inline-block;background:#fff;border:1px solid #dde6ed;border-radius:999px;
    padding:7px 12px;margin:10px 6px 0 0;font-size:.82rem;font-weight:800;color:#405766
}
.card{
    background:#fff;border:1px solid #dee7ee;border-radius:18px;padding:16px;
    box-shadow:0 10px 30px rgba(35,55,68,.05)
}
.label{font-size:.71rem;text-transform:uppercase;letter-spacing:.07em;font-weight:850;color:#7a8b95}
.value{font-size:1.82rem;font-weight:900;color:#254052;margin-top:4px}
.sub{font-size:.77rem;color:#7b8d96}
.section{font-size:1.2rem;font-weight:900;color:#294556;margin:24px 0 11px}
.note{background:#f5fafc;border:1px solid #dae7ef;border-radius:15px;padding:14px 16px;color:#596d78}
.action{background:#fff7e8;border-left:5px solid #e2a23c;border-radius:10px;padding:10px 13px;margin:7px 0;color:#5b4b39}
.footer{text-align:center;color:#82929b;font-size:.75rem;margin-top:22px}
</style>
""",
    unsafe_allow_html=True,
)

st.sidebar.markdown("## 🏟️ SportShield Local")
st.sidebar.caption("Observe • Compare • Prioritize")
page = st.sidebar.radio(
    "Workspace",
    [
        "Dashboard",
        "Risk Overview",
        "Facilities",
        "Surface & Weather",
        "Usage & Load",
        "Equipment Checks",
        "Incident Analysis",
        "Sport Comparison",
        "Risk Heatmap",
        "Priority Queue",
        "Recommendations",
        "Scenario Planner",
        "Reports & Export",
    ],
    label_visibility="collapsed",
)
st.sidebar.divider()

uploads = [
    ("surfaces", "Upload authorized surface-conditions CSV", "sample_surface_conditions.csv"),
    ("weather", "Upload weather-conditions CSV", "sample_weather_conditions.csv"),
    ("usage", "Upload facility-usage CSV", "sample_facility_usage.csv"),
    ("equipment", "Upload equipment-checks CSV", "sample_equipment_checks.csv"),
    ("incidents", "Upload incident-reports CSV", "sample_incident_reports.csv"),
]

frames = {}
for key, label, default in uploads:
    uploaded = st.sidebar.file_uploader(label, type=["csv"], key=f"upload_{key}")
    try:
        frames[key] = normalize_columns(
            pd.read_csv(uploaded) if uploaded is not None else pd.read_csv(DATA / default)
        )
    except Exception as exc:
        st.error(f"Could not read {label}: {exc}")
        st.stop()

errors = []
for dataset, required in REQUIRED_COLUMNS.items():
    missing = [col for col in required if col not in frames[dataset].columns]
    if missing:
        errors.append(f"{dataset}: missing {', '.join(missing)}")

if errors:
    st.error("Input validation failed.")
    for error in errors:
        st.write("• " + error)
    st.stop()

try:
    scored = build_scores(
        frames["surfaces"],
        frames["weather"],
        frames["usage"],
        frames["equipment"],
        frames["incidents"],
    )
    sport_summary = build_sport_summary(scored)
    incident_summary = build_incident_summary(frames["incidents"])
except Exception as exc:
    st.error("The supplied records could not be processed.")
    st.exception(exc)
    st.stop()

facility_options = ["All"] + sorted(scored["facility_id"].astype(str).unique().tolist())
sport_options = ["All"] + sorted(scored["sport_type"].astype(str).unique().tolist())
band_options = ["All", "Low", "Moderate", "High", "Critical"]

selected_facility = st.sidebar.selectbox("Facility", facility_options)
selected_sport = st.sidebar.selectbox("Sport", sport_options)
selected_band = st.sidebar.selectbox("Risk band", band_options)
minimum_score = st.sidebar.slider("Minimum injury-risk score", 0, 100, 0)

view = scored.copy()
if selected_facility != "All":
    view = view[view["facility_id"].astype(str) == selected_facility]
if selected_sport != "All":
    view = view[view["sport_type"].astype(str) == selected_sport]
if selected_band != "All":
    view = view[view["risk_band"].astype(str) == selected_band]
view = view[view["injury_risk_score"] >= minimum_score]

if view.empty:
    st.warning("No facilities match the current filters.")
    st.stop()

st.markdown(
    """
<div class="hero">
<div class="eyebrow">COMMUNITY SPORTS SAFETY • FACILITY CONDITIONS • LOCAL-FIRST • EXPLAINABLE</div>
<h1>Analyze potential injury-risk patterns across sports facilities, surfaces, weather, usage, equipment checks and incident reports.</h1>
<p>Surface operational conditions that may warrant qualified sports-safety review using transparent local analytics rather than unsupported individual injury predictions.</p>
<span class="pill">🏟️ Facility Risk</span>
<span class="pill">🟩 Surface Condition</span>
<span class="pill">☀️ Weather Context</span>
<span class="pill">📈 Usage & Load</span>
<span class="pill">🧰 Equipment Checks</span>
<span class="pill">🚑 Incident History</span>
<span class="pill">🏃 Sport Comparison</span>
<span class="pill">🔒 Local Processing</span>
</div>
""",
    unsafe_allow_html=True,
)

kpis = [
    ("Facilities", int(view["facility_id"].nunique()), "In current filter"),
    ("High / Critical", int((view["injury_risk_score"] >= 50).sum()), "Review-priority facilities"),
    ("Critical", int((view["injury_risk_score"] >= 75).sum()), "Highest screening band"),
    ("Avg risk", f"{view['injury_risk_score'].mean():.1f}", "Mean screening score"),
    ("Incidents / 30d", int(view["incident_count_30d"].sum()), "Reported local signal"),
]
cols = st.columns(5)
for col, (label, value, subtitle) in zip(cols, kpis):
    col.markdown(
        f'<div class="card"><div class="label">{label}</div>'
        f'<div class="value">{value}</div><div class="sub">{subtitle}</div></div>',
        unsafe_allow_html=True,
    )

if page == "Dashboard":
    st.markdown('<div class="section">SportShield command view</div>', unsafe_allow_html=True)
    a, b, c = st.columns([1, 1.25, 1])

    dist = (
        view["risk_band"].astype(str)
        .value_counts()
        .rename_axis("band")
        .reset_index(name="count")
    )
    a.plotly_chart(
        px.pie(
            dist, names="band", values="count", hole=.62,
            title="Risk-band distribution", template="plotly_white"
        ),
        width="stretch",
    )

    bubble = safe_size(view, "capacity_pressure_index")
    b.plotly_chart(
        px.scatter(
            bubble,
            x="surface_condition_score",
            y="injury_risk_score",
            size="plot_size",
            color="sport_type",
            hover_name="facility_id",
            range_x=[0, 1],
            range_y=[0, 100],
            title="Surface condition × injury-risk score",
            template="plotly_white",
        ),
        width="stretch",
    )

    top = view.nlargest(8, "injury_risk_score").sort_values("injury_risk_score")
    c.plotly_chart(
        px.bar(
            top,
            x="injury_risk_score",
            y="facility_id",
            orientation="h",
            color="primary_driver",
            text_auto=".0f",
            range_x=[0, 100],
            title="Top review priorities",
            template="plotly_white",
        ),
        width="stretch",
    )

    d, e = st.columns(2)
    usage_bubble = safe_size(view, "daily_users")
    d.plotly_chart(
        px.scatter(
            usage_bubble,
            x="utilization_index",
            y="injury_risk_score",
            size="plot_size",
            color="sport_type",
            range_x=[0, 1],
            range_y=[0, 100],
            title="Usage intensity × injury risk",
            template="plotly_white",
        ),
        width="stretch",
    )

    eq_bubble = safe_size(view, "equipment_issue_index")
    e.plotly_chart(
        px.scatter(
            eq_bubble,
            x="protective_equipment_readiness",
            y="injury_risk_score",
            size="plot_size",
            color="sport_type",
            range_x=[0, 1],
            range_y=[0, 100],
            title="Equipment readiness × injury risk",
            template="plotly_white",
        ),
        width="stretch",
    )

    st.markdown('<div class="section">Facility register</div>', unsafe_allow_html=True)
    st.dataframe(
        view.sort_values("injury_risk_score", ascending=False),
        width="stretch",
        hide_index=True,
    )

    hero = ROOT / "assets" / "sportshield_dashboard_hero.png"
    if hero.exists():
        with st.expander("Project visual"):
            st.image(str(hero), width="stretch")

elif page == "Risk Overview":
    st.markdown('<div class="section">Risk overview</div>', unsafe_allow_html=True)
    components = view[
        [
            "facility_id", "sport_type",
            "surface_pressure", "weather_pressure", "usage_pressure",
            "equipment_pressure", "incident_pressure", "injury_risk_score",
            "risk_band", "primary_driver",
        ]
    ].copy()
    st.dataframe(
        components.sort_values("injury_risk_score", ascending=False),
        width="stretch",
        hide_index=True,
    )

elif page == "Facilities":
    st.markdown('<div class="section">Facility profile</div>', unsafe_allow_html=True)
    facility_id = st.selectbox("Select facility", view["facility_id"].astype(str).tolist())
    row = view[view["facility_id"].astype(str) == facility_id].iloc[0]

    a, b, c, d = st.columns(4)
    a.metric("Risk score", f"{row['injury_risk_score']:.1f}/100")
    b.metric("Risk band", str(row["risk_band"]))
    c.metric("Sport", row["sport_type"])
    d.metric("Primary driver", row["primary_driver"])

    profile = pd.DataFrame({
        "Signal": [
            "Surface pressure", "Weather pressure", "Usage pressure",
            "Equipment pressure", "Incident pressure",
            "Utilization", "Capacity pressure", "Incident count / 30d",
            "Equipment issue index", "Protective-equipment readiness",
        ],
        "Value": [
            f"{row['surface_pressure']:.2f}",
            f"{row['weather_pressure']:.2f}",
            f"{row['usage_pressure']:.2f}",
            f"{row['equipment_pressure']:.2f}",
            f"{row['incident_pressure']:.2f}",
            f"{row['utilization_index']:.2f}",
            f"{row['capacity_pressure_index']:.2f}",
            int(row["incident_count_30d"]),
            f"{row['equipment_issue_index']:.2f}",
            f"{row['protective_equipment_readiness']:.2f}",
        ],
    })
    st.dataframe(profile, width="stretch", hide_index=True)

elif page == "Surface & Weather":
    st.markdown('<div class="section">Surface and weather context</div>', unsafe_allow_html=True)
    a, b = st.columns(2)
    surface_df = frames["surfaces"].merge(frames["weather"], on="facility_id", how="left")
    a.plotly_chart(
        px.scatter(
            surface_df,
            x="surface_condition_score",
            y="puddle_pressure_index",
            size="worn_area_pct",
            color="surface_type",
            range_x=[0, 1],
            range_y=[0, 1],
            title="Surface condition × puddle pressure",
            template="plotly_white",
        ),
        width="stretch",
    )
    b.plotly_chart(
        px.scatter(
            surface_df,
            x="heat_exposure_index",
            y="humidity_pct",
            size="rainfall_mm",
            color="surface_type",
            range_x=[0, 1],
            title="Heat exposure × humidity",
            template="plotly_white",
        ),
        width="stretch",
    )
    st.dataframe(surface_df, width="stretch", hide_index=True)

elif page == "Usage & Load":
    st.markdown('<div class="section">Usage and workload pressure</div>', unsafe_allow_html=True)
    u = frames["usage"].copy()
    a, b = st.columns(2)
    a.plotly_chart(
        px.scatter(
            safe_size(u, "daily_users"),
            x="utilization_index",
            y="capacity_pressure_index",
            size="plot_size",
            color="sport_type",
            range_x=[0, 1],
            range_y=[0, 1],
            title="Utilization × capacity pressure",
            template="plotly_white",
        ),
        width="stretch",
    )
    b.plotly_chart(
        px.bar(
            u.groupby("sport_type", as_index=False)["daily_users"].mean()
             .sort_values("daily_users", ascending=False),
            x="sport_type",
            y="daily_users",
            color="sport_type",
            title="Average daily users by sport",
            template="plotly_white",
        ),
        width="stretch",
    )
    st.dataframe(u, width="stretch", hide_index=True)

elif page == "Equipment Checks":
    st.markdown('<div class="section">Equipment-control readiness</div>', unsafe_allow_html=True)
    e = frames["equipment"].copy()
    e["completion_rate"] = (
        pd.to_numeric(e["checks_completed"], errors="coerce").fillna(0)
        / pd.to_numeric(e["checks_due"], errors="coerce").fillna(1).clip(lower=1)
    ).clip(0, 1)
    a, b = st.columns(2)
    a.plotly_chart(
        px.scatter(
            e,
            x="completion_rate",
            y="equipment_issue_index",
            size="maintenance_backlog_index",
            color="facility_id",
            range_x=[0, 1],
            range_y=[0, 1],
            title="Check completion × equipment issues",
            template="plotly_white",
        ),
        width="stretch",
    )
    b.plotly_chart(
        px.scatter(
            e,
            x="protective_equipment_readiness",
            y="goal_post_check_index",
            size="maintenance_backlog_index",
            color="facility_id",
            range_x=[0, 1],
            range_y=[0, 1],
            title="Protective-equipment × goal-post checks",
            template="plotly_white",
        ),
        width="stretch",
    )
    st.dataframe(e, width="stretch", hide_index=True)

elif page == "Incident Analysis":
    st.markdown('<div class="section">Incident and near-miss analytics</div>', unsafe_allow_html=True)
    a, b = st.columns(2)
    a.plotly_chart(
        px.bar(
            incident_summary,
            x="risk_factor",
            y="incidents",
            color="risk_factor",
            text_auto=True,
            title="Incident records by reported factor",
            template="plotly_white",
        ),
        width="stretch",
    )
    by_severity = (
        frames["incidents"]["severity"].astype(str).value_counts()
        .rename_axis("severity").reset_index(name="count")
    )
    b.plotly_chart(
        px.pie(
            by_severity,
            names="severity",
            values="count",
            hole=.58,
            title="Incident severity distribution",
            template="plotly_white",
        ),
        width="stretch",
    )
    st.dataframe(frames["incidents"], width="stretch", hide_index=True)

elif page == "Sport Comparison":
    st.markdown('<div class="section">Sport-type comparison</div>', unsafe_allow_html=True)
    st.plotly_chart(
        px.bar(
            sport_summary,
            x="sport_type",
            y="avg_risk",
            color="sport_type",
            text_auto=".1f",
            range_y=[0, 100],
            title="Average injury-risk screening score by sport",
            template="plotly_white",
        ),
        width="stretch",
    )
    st.dataframe(sport_summary, width="stretch", hide_index=True)

elif page == "Risk Heatmap":
    st.markdown('<div class="section">Facility risk heatmap</div>', unsafe_allow_html=True)
    heat = view[
        [
            "facility_id", "surface_pressure", "weather_pressure",
            "usage_pressure", "equipment_pressure", "incident_pressure",
            "injury_risk_score",
        ]
    ].set_index("facility_id")
    st.plotly_chart(
        px.imshow(
            heat.T,
            text_auto=".2f",
            aspect="auto",
            title="Explainable facility risk-factor matrix",
            template="plotly_white",
        ),
        width="stretch",
    )

elif page == "Priority Queue":
    st.markdown('<div class="section">Safety review priority queue</div>', unsafe_allow_html=True)
    q = view.sort_values(
        ["injury_risk_score", "review_action_count"],
        ascending=False,
    )
    st.dataframe(q, width="stretch", hide_index=True)
    st.download_button(
        "⬇️ Download priority queue",
        q.to_csv(index=False).encode("utf-8"),
        file_name="community_sports_injury_priority_queue.csv",
        mime="text/csv",
    )

elif page == "Recommendations":
    st.markdown('<div class="section">Guided review actions</div>', unsafe_allow_html=True)
    facility_id = st.selectbox("Select facility", view["facility_id"].astype(str).tolist())
    row = view[view["facility_id"].astype(str) == facility_id].iloc[0]
    actions = []

    if row["surface_pressure"] >= 0.60:
        actions.append("Review surface condition, worn areas, puddle/standing-water pressure and maintenance timing.")
    if row["weather_pressure"] >= 0.60:
        actions.append("Review current local weather conditions and whether activity scheduling or recovery arrangements need attention.")
    if row["usage_pressure"] >= 0.60:
        actions.append("Review utilization, session density, capacity pressure and feasible scheduling/load controls.")
    if row["equipment_pressure"] >= 0.60:
        actions.append("Review equipment-check completion, protective equipment, lighting and maintenance backlog.")
    if row["incident_pressure"] >= 0.60:
        actions.append("Review incident and near-miss records with qualified safety personnel and identify repeat patterns.")
    if row["injury_risk_score"] >= 75:
        actions.append("Prioritize multidisciplinary safety review before making operational changes.")
    if not actions:
        actions.append("Maintain routine monitoring and continue established facility safety controls.")

    for action in actions:
        st.markdown(f'<div class="action">• {action}</div>', unsafe_allow_html=True)

elif page == "Scenario Planner":
    st.markdown('<div class="section">Sports Safety Scenario Planner</div>', unsafe_allow_html=True)
    st.caption(
        "Adjustable weights change planning emphasis only; they do not predict individual injury or establish causation."
    )
    a, b, c, d, e = st.columns(5)
    with a:
        w_surface = st.slider("Surface", 10, 40, 25)
    with b:
        w_weather = st.slider("Weather", 5, 30, 17)
    with c:
        w_usage = st.slider("Usage", 5, 30, 20)
    with d:
        w_equipment = st.slider("Equipment", 5, 30, 18)
    with e:
        w_incident = st.slider("Incidents", 5, 30, 20)

    weights = np.array([w_surface, w_weather, w_usage, w_equipment, w_incident], dtype=float)
    weights /= weights.sum()

    scenario = view.copy()
    scenario["scenario_score"] = (
        100 * (
            weights[0] * scenario["surface_pressure"]
            + weights[1] * scenario["weather_pressure"]
            + weights[2] * scenario["usage_pressure"]
            + weights[3] * scenario["equipment_pressure"]
            + weights[4] * scenario["incident_pressure"]
        )
    ).clip(0, 100).round(1)
    scenario["scenario_change"] = (
        scenario["scenario_score"] - scenario["injury_risk_score"]
    ).round(1)

    st.dataframe(
        scenario[
            [
                "facility_id", "sport_type", "injury_risk_score",
                "scenario_score", "scenario_change", "primary_driver",
            ]
        ].sort_values("scenario_score", ascending=False),
        width="stretch",
        hide_index=True,
    )

    st.download_button(
        "⬇️ Download scenario CSV",
        scenario.to_csv(index=False).encode("utf-8"),
        file_name="community_sports_injury_scenario.csv",
        mime="text/csv",
    )

else:
    st.markdown('<div class="section">Reports & export</div>', unsafe_allow_html=True)
    exports = [
        ("Scored facilities", scored, "scored_facilities.csv"),
        ("Surface conditions", frames["surfaces"], "surface_conditions.csv"),
        ("Weather conditions", frames["weather"], "weather_conditions.csv"),
        ("Facility usage", frames["usage"], "facility_usage.csv"),
        ("Equipment checks", frames["equipment"], "equipment_checks.csv"),
        ("Incident reports", frames["incidents"], "incident_reports.csv"),
        ("Sport summary", sport_summary, "sport_summary.csv"),
        ("Incident summary", incident_summary, "incident_summary.csv"),
    ]
    for label, dataframe, filename in exports:
        st.download_button(
            f"⬇️ Download {label}",
            dataframe.to_csv(index=False).encode("utf-8"),
            file_name=filename,
            mime="text/csv",
        )

st.markdown(
    """
<div class="note">
<b>Important:</b> This platform is a safety-planning screening aid. It does not
diagnose injuries, predict individual outcomes, establish causation or legal liability,
certify facility safety, or replace qualified sports-medicine, coaching, facility-management,
occupational-safety, public-health, or emergency professionals and applicable procedures.
</div>
<div class="footer">
100% local CSV processing • No external APIs • Explainable heuristics • Human-in-the-loop review • Synthetic demonstration data
</div>
""",
    unsafe_allow_html=True,
)
