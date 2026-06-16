import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from run_effectiveness_tests import generate_report, REPORT_PATH

with open(Path(__file__).parent / "test_results.json", "r", encoding="utf-8") as f:
    results = json.load(f)

# Add missing throughput per second fields for backward compatibility
scheduling = results["scheduling"]
for algo in ["density_based", "fixed_time"]:
    if "throughput_per_second" not in scheduling[algo]:
        t = scheduling[algo]["total_time"]
        tp = scheduling[algo]["total_throughput"]
        scheduling[algo]["throughput_per_second"] = round(tp / t, 2) if t > 0 else 0

if "throughput_efficiency_pct" not in scheduling["improvements"]:
    density_tps = scheduling["density_based"]["throughput_per_second"]
    fixed_tps = scheduling["fixed_time"]["throughput_per_second"]
    scheduling["improvements"]["throughput_efficiency_pct"] = round((density_tps - fixed_tps) / fixed_tps * 100, 2) if fixed_tps > 0 else 0

report = generate_report(results["detection"], scheduling)
with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write(report)

print(f"Report regenerated at {REPORT_PATH}")
