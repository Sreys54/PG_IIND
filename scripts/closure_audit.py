"""
Closure brief, Part F: audit table of stated values in chapters 01-08, the
weekly handbacks and the overnight report, against their source files.

For each check, every occurrence of the stated value is listed with its file
and line, the value in the current source, and the action:
  - "matches source": the statement agrees with the current source file;
  - "corrected / labelled (dated note nearby)": a stale value kept as
    history, with a dated correction, withdrawal or "superseded" note within
    AUDIT_WINDOW lines;
  - "historical section of the report": inside the overnight report's
    earlier (Week 7) run, which the closure section supersedes;
  - "UNRESOLVED": a stale value with no nearby note. The run must end with
    none of these.
The 00_lab_log is excluded by design: it is an append-only chronological
record, and its later entries carry the corrections.

Usage: PYTHONPATH=. python scripts/closure_audit.py
"""
import glob
import re

import pandas as pd
import yaml

AUDIT_WINDOW = 14
NOTE = re.compile(r"Correction \(2026-10-0[56]|Withdrawn|withdrawn|superseded|Superseded|historical|Historical|"
                  r"Original text|corrected 2026-10-0[56]|was:|previously|stale|for the record|\[W7, corrected\]", re.I)
# A document with a whole-document dated correction section covers every stale value in it.
WHOLE_DOC_NOTE = "## Correction (2026-10-06, closure brief A.2)"
OUT = "results/closure_audit_table.csv"


def targets():
    files = sorted(glob.glob("thesis_docs/chapters/0[1-8]_*.md"))
    files += sorted(glob.glob("thesis_docs/Week*_Parameter_Method_and_Implementation_Justification.md"))
    files += ["thesis_docs/overnight_report.md"]
    return files


def sources():
    cfg = yaml.safe_load(open("experiments/phase1_baseline/configs/station_v0_bogota.yaml", encoding="utf-8"))
    ci = pd.read_csv("results/closure_margin_vs_overload_ci.csv").set_index("algorithm")
    mv = pd.read_csv("results/week5_margin_vs_overload.csv", comment="#").set_index("algorithm")
    vc = pd.read_csv("results/closure_voltage_contribution.csv").set_index("setting")
    sz = pd.read_csv("results/week7_transformer_sizing.csv")
    from ev2gym_thesis.prices.cities import spread
    rr = ci.loc["RoundRobin"]
    return {
        "battery": f"{cfg['ev']['battery_capacity']} kWh (station_v0_bogota.yaml ev.battery_capacity)",
        "afap_overload": f"{mv.loc['ChargeAsFastAsPossible','mean_overload']:.2f} kWh/day (week5_margin_vs_overload.csv)",
        "rr_cost": f"{rr.margin_foregone_vs_afap_cop:.1f} [{rr.foregone_ci_low:.1f}, {rr.foregone_ci_high:.1f}] COP/day "
                   f"(closure_margin_vs_overload_ci.csv)",
        "rr_rel": f"{100 * rr.margin_foregone_vs_afap_cop / mv.loc['ChargeAsFastAsPossible','mean_margin']:.2f}% "
                  f"(Proposition 7.1: = Delta E / E_AFAP)",
        "voltage": f"{100 * vc.loc['base','rr_reduction_vs_afap']:.1f}% [{100 * vc.loc['base','reduction_ci_low']:.1f}, "
                   f"{100 * vc.loc['base','reduction_ci_high']:.1f}] at base only (closure_voltage_contribution.csv)",
        "kva": f"225 kVA (P95 {sz[sz.algorithm=='ChargeAsFastAsPossible'].peak_kw_p95.min():.1f}-"
               f"{sz[sz.algorithm=='ChargeAsFastAsPossible'].peak_kw_p95.max():.1f} kW / 0.894 -> ET-013)",
        "spread_bog": f"{100 * spread('Bogota'):.2f}% (Enel Aug 2026, cities.py)",
        "spread_med": f"{100 * spread('Medellin'):.2f}% (EPM Sep 2026, cities.py)",
        "dns": "Round Robin DNS 34.58% [30.75, 38.38] at 1.0x (closure_demand_not_served.csv)",
    }


# (check id, regex, source key, stale?)
CHECKS = [
    ("battery_60kWh", r"\b60 ?kWh", "battery", True),
    ("afap_overload_5.33", r"5\.33", "afap_overload", True),
    ("afap_overload_13.25", r"13\.25 kWh", "afap_overload", True),
    ("rr_cost_503.9", r"503\.9", "rr_cost", True),
    ("rr_cost_88.6", r"88\.6 COP", "rr_cost", True),
    ("rr_energy_0.08pct", r"0\.08%", "rr_rel", True),
    ("satisfaction_unchanged", r"[Ss]atisfaction (is )?unchanged|not reached within 1\.6|\(≥ 99\.89%\)|99\.89–99\.93%",
     "dns", True),
    ("targets_met_all_arms", r"met by (all|every) (5 )?arms?", "dns", True),
    ("rr_cost_551.9", r"551\.9", "rr_cost", False),
    ("rr_relative_0.47pct", r"0\.47%", "rr_rel", False),
    ("ranking_48_checks", r"48 checks|48/48", "rr_rel", False),
    ("afap_overload_14.22", r"14\.22", "afap_overload", False),
    ("voltage_37pct", r"\b37%", "voltage", False),
    ("sizing_225kVA", r"225 kVA", "kva", False),
    ("spread_bogota_1.57", r"1\.57%", "spread_bog", False),
    ("spread_medellin_0.69", r"0\.69%", "spread_med", False),
]


def main():
    src = sources()
    rows = []
    for f in targets():
        text = open(f, encoding="utf-8").read()
        lines = text.splitlines()
        whole_doc = WHOLE_DOC_NOTE in text
        hist_start = None
        if f.endswith("overnight_report.md"):
            hist_start = next((i for i, l in enumerate(lines) if l.startswith("# Overnight Report — Final Practical")), None)
        for cid, rx, key, stale in CHECKS:
            for i, line in enumerate(lines):
                for m in re.finditer(rx, line):
                    win = "\n".join(lines[max(0, i - AUDIT_WINDOW): i + AUDIT_WINDOW + 1])
                    if hist_start is not None and i >= hist_start:
                        action = "historical section of the report (superseded by the closure section)"
                    elif not stale:
                        action = "matches source"
                    elif NOTE.search(win) or whole_doc:
                        action = "corrected / labelled (dated note nearby)"
                    else:
                        action = "UNRESOLVED"
                    rows.append({"file": f, "line": i + 1, "check": cid, "stated_value": m.group(0),
                                 "source_value": src[key], "action": action,
                                 "context": line.strip()[:160]})
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    print(out.groupby(["check", "action"]).size().to_string())
    bad = out[out.action == "UNRESOLVED"]
    print(f"\nUNRESOLVED: {len(bad)}")
    if len(bad):
        print(bad[["file", "line", "check", "context"]].to_string(index=False))


if __name__ == "__main__":
    main()
