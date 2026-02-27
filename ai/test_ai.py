from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.engine import (
    build_engine_summary,
    build_peak_contributors,
    call_ai_intelligence,
    generate_plan_with_ai,
    simulate_shift,
    strategy_simulation,
)
from parser.syllabus_parser import parse_syllabi
from planner.weekly_planner import generate_weekly_plan
from datetime import date

# ---- LOAD SYLLABI ----
with open("data/mock_syllabi/cse2331.txt") as f:
    cse_text = f.read()

with open("data/mock_syllabi/econ1011.txt") as f:
    econ_text = f.read()

# ---- PARSE ----
parsed = parse_syllabi([cse_text, econ_text])

# ---- DRAFT PLAN ----
draft_plan = generate_weekly_plan(parsed)

# ---- DETERMINISTIC + AI LAYER ----
result = generate_plan_with_ai(
    parsed_syllabi=parsed,
    weekly_plan=draft_plan,
    anchor_date=date.today()
)

# ---- ENGINE METRICS ----
summary = build_engine_summary(result)

print("===== ENGINE SUMMARY =====")
print(summary)

contributors = build_peak_contributors(result, limit=5)
print("===== PEAK CONTRIBUTORS =====")
for item in contributors:
    print(item)

shift_out = {"error": "task_not_found"}
if contributors:
    shift_title = contributors[0].get("task")
    shift_out = simulate_shift(result, shift_title, 4)

strategy_out = strategy_simulation(
    result,
    {"exam_prep": 40, "projects": 35, "homework": 25},
)

# ---- RISK INTELLIGENCE ----
ai_output = call_ai_intelligence(
    summary,
    metrics=result,
    simulation_results={"shift": shift_out, "strategy": strategy_out},
)

print("===== AI OUTPUT =====")
print(ai_output)

print("===== CHECKPOINTS =====")
print("peak_week:", summary.get("peak_week"))
print("high_pressure_weeks:", summary.get("high_pressure_weeks"))
print("shift_delta_percent:", shift_out.get("delta_percent"))

kpis = ai_output.get("kpis", {}) if isinstance(ai_output, dict) else {}
why_risky = ai_output.get("why_risky", {}) if isinstance(ai_output, dict) else {}
simulation_impact = ai_output.get("simulation_impact", {}) if isinstance(ai_output, dict) else {}
allocation = ai_output.get("time_allocation_strategy", {}) if isinstance(ai_output, dict) else {}

assert isinstance(kpis, dict), "kpis must be a dict"
assert isinstance(why_risky, dict), "why_risky must be a dict"
assert isinstance(simulation_impact, dict), "simulation_impact must be a dict"
assert isinstance(allocation, dict), "time_allocation_strategy must be a dict"

for key in (
    "peak_stress_score",
    "volatility_index",
    "risk_week_ratio",
    "burnout_probability_percent",
    "acceleration_index",
    "compression_risk",
    "peak_delta_percent",
):
    assert key in kpis, f"missing KPI: {key}"
for key in (
    "peak_week",
    "exam_count",
    "milestone_count",
    "weekly_weight_sum",
    "compression_weight_percent",
    "compression_window_days",
    "stress_acceleration_percent",
    "detail",
):
    assert key in why_risky, f"missing why_risky field: {key}"
for key in ("peak_delta_percent", "week_shift_detected", "driver_task", "explanation"):
    assert key in simulation_impact, f"missing simulation_impact field: {key}"
for key in ("exam_prep", "projects", "homework"):
    assert key in allocation, f"missing allocation field: {key}"

allocation_total = (
    float(allocation.get("exam_prep") or 0.0)
    + float(allocation.get("projects") or 0.0)
    + float(allocation.get("homework") or 0.0)
)
assert abs(allocation_total - 100.0) <= 1.5, "allocation must sum to ~100"

simulation_narrative = str(ai_output.get("simulation_narrative") or "")
for token in ("peak change", "week shift", "acceleration change", "compression change"):
    assert token in simulation_narrative.lower(), f"simulation_narrative must include '{token}'"

print("===== AI KPIS =====")
print(kpis)
print("===== WHY RISKY =====")
print(why_risky)
print("===== SIMULATION IMPACT =====")
print(simulation_impact)
