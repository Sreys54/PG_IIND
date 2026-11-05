"""
Week 8 advisor review, A8 (facts for the text): what Week 2 produced, and
every remaining "60 kWh" in the repository (code, configs, chapters, docs,
including the text of .docx files). Outputs:
  experiments/phase4_review/A/A8_week2_outputs.csv
  experiments/phase4_review/A/A8_60kwh.csv
"""
import glob
import os
import re
import zipfile

import pandas as pd

D = "experiments/phase4_review/A"


def week2_outputs():
    deg = pd.read_csv("results/degradation_by_ambient.csv")
    g = deg.groupby(["algorithm", "ambient_scenario"]).sum_d_cal.mean().unstack()
    rows = []
    for a in g.index:
        for sc in ("bogota_outdoor", "bogota_outdoor_plus5", "bogota_underground"):
            rows.append({"file": "results/degradation_by_ambient.csv", "what": f"calendar degradation, {a}, {sc} vs 25 C default (100 rows: 50 seeds x 2 days)",
                         "number": f"{100 * (g.loc[a, sc] / g.loc[a, 'default'] - 1):+.2f}% (mean per case)"})
    m = pd.read_csv("results/master_results.csv", low_memory=False)
    x = m[m.config_name.str.startswith("station_n")]
    for (cfg, alg), s in x.groupby(["config_name", "algorithm"]):
        rows.append({"file": "results/master_results.csv (Week 2 size sensitivity)", "what": f"{cfg}, {alg}, {len(s)} rows",
                     "number": f"energy {s.total_energy_charged.mean():.2f} kWh/day, overload {s.total_transformer_overload.mean():.2f} kWh/day, EVs {s.total_ev_served.mean():.2f}/day"})
    rows += [
        {"file": "ev2gym_thesis/ambient_bogota.py", "what": "Bogota ambient profiles (IDEAM station 21205791, El Dorado, 1981-2010 normals)",
         "number": "annual mean 13.68 C, mean daily max 19.31 C, mean daily min 7.88 C"},
        {"file": "ev2gym_thesis/degradation_bogota.py", "what": "calendar-ageing recomputation at Bogota temperatures, outside the library (theta = 298.15 K hard-coded in ev2gym/models/ev.py line 480)",
         "number": "total battery_degradation change vs 25 C: -26.13% outdoor, -24.37% outdoor +5 C, -32.49% underground (02_model_validation.md)"},
        {"file": "thesis_docs/chapters/02_model_validation.md", "what": "10-row realism table (validated / empirically set / declared limitation)", "number": "-"}]
    return pd.DataFrame(rows)


def sixty_kwh():
    pat = re.compile(r"\b60\s?-?kWh", re.I)
    rows = []
    for f in glob.glob("**/*", recursive=True):
        if any(p in f for p in (".git", "_tmp_", "node_modules", "__pycache__")) or os.path.isdir(f):
            continue
        if f.endswith((".py", ".md", ".yaml", ".yml", ".json", ".tex", ".txt", ".csv")):
            try:
                for i, line in enumerate(open(f, encoding="utf-8", errors="ignore"), start=1):
                    if pat.search(line):
                        rows.append({"file": f, "line": i, "text": line.strip()[:200]})
            except OSError:
                pass
        elif f.endswith(".docx"):
            try:
                t = re.sub(r"<[^>]+>", " ", zipfile.ZipFile(f).read("word/document.xml").decode("utf8"))
            except (KeyError, zipfile.BadZipFile):
                continue
            for mm in pat.finditer(t):
                rows.append({"file": f, "line": -1, "text": re.sub(r"\s+", " ", t[max(0, mm.start() - 90):mm.end() + 60])})
    df = pd.DataFrame(rows)
    # Text files only quote the old wording to record or audit the 70 kWh correction (checked line by
    # line, 2026-11-03); a .docx deliverable that contains it states it.
    df["status"] = df.file.str.endswith(".docx").map(
        {True: "STATES 60 kWh: to correct to 70 kWh", False: "quotes it to record or audit the correction (no action)"})
    return df


if __name__ == "__main__":
    week2_outputs().to_csv(f"{D}/A8_week2_outputs.csv", index=False)
    s = sixty_kwh()
    s.to_csv(f"{D}/A8_60kwh.csv", index=False)
    print(s.status.value_counts().to_string())
    print(s[s.status.str.startswith("STATES")][["file", "line"]].to_string())
