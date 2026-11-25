"""WP4 run file, group A11 (AE2111-I). Everything is started from here.

    python run_wp4.py              # full analysis: V-n, load cases, loads, all designs, figures, results
    python run_wp4.py vn           # only the V-n diagrams and the speeds table
    python run_wp4.py loads        # V-n + load-case table + S/M diagrams (no designs)

Options:
    --aircraft PATH   aircraft input file   (default config/aircraft.toml)
    --designs  PATH   design options file   (default config/designs.toml)
    --out      DIR    output folder         (default output/)

Workflow (WP4.3, no optimiser): edit the thicknesses / stringers in config/designs.toml,
run this file, read output/WP4_results.md (section 2 says whether every requirement is met),
adjust and repeat.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from wp4 import plots as P
from wp4 import report
from wp4.checks import run_checks
from wp4.config import DEFAULT_AIRCRAFT, DEFAULT_DESIGNS, WP4_DIR
from wp4.design import load_designs
from wp4.model import build_model
from wp4.verify import critical_cases, evaluate_design


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("task", nargs="?", default="all", choices=["all", "vn", "loads"])
    ap.add_argument("--aircraft", default=DEFAULT_AIRCRAFT)
    ap.add_argument("--designs", default=DEFAULT_DESIGNS)
    ap.add_argument("--out", default=WP4_DIR / "output")
    a = ap.parse_args(argv)
    out = Path(a.out)
    figs = out / "figures"
    t0 = time.time()
    log = lambda msg: print(f"[{time.time() - t0:5.1f} s] {msg}", flush=True)

    model = build_model(a.aircraft)
    log(f"model built: {len(model.diagrams)} V-n diagrams, {len(model.cases)} load cases")
    figures = P.fig_vn_all(model.diagrams, figs) + [P.fig_inputs(model, figs)]
    log("V-n and input figures written")
    if a.task == "vn":
        return

    designs = load_designs(a.designs)
    case_loads = model.case_loads(designs)
    crit = critical_cases(case_loads)
    log("critical cases: " + ", ".join(f"{k} = {v.case.id}" for k, v in crit.items()))
    figures += [P.fig_load_case_scatter(case_loads, crit, figs), P.fig_distributed_loads(crit, figs)]
    if a.task == "loads":
        return

    drs = []
    for d in designs:
        dr = evaluate_design(model.ac, d, model.geom, case_loads)
        u = dr.utilisation()
        log(f"design {d.name}: {dr.mass_total:,.0f} kg, compliant = {dr.compliant} ("
            + ", ".join(f"{k} {v:.2f}" for k, v in u.items()) + ")")
        drs.append(dr)

    crit_ids = {k: v.case.id for k, v in crit.items()}
    figures += P.fig_internal_loads(crit_ids, drs, figs)
    figures += [P.fig_stiffness(drs, figs), P.fig_cross_sections(drs, model.geom, figs),
                P.fig_utilisation(drs, figs)]
    figures += [P.fig_deflection(dr, crit_ids, dr.limits, figs) for dr in drs]
    checks = run_checks(model, case_loads, drs)
    bad = [c["check"] for c in checks if not c["ok"]]
    log("model checks: " + ("all passed" if not bad else "FAILED: " + "; ".join(bad)))
    paths = report.write_all(out, model, case_loads, crit, drs, checks, figures)
    log(f"done: {len(figures)} figures, results in {paths['summary']}")


if __name__ == "__main__":
    main()
