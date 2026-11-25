"""Results output: output/WP4_results.md (everything, human readable) and output/tables/*.csv."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import numpy as np

from .config import G0


def _csv(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return path


def _fmt(v):
    if isinstance(v, (bool, np.bool_)):
        return "yes" if v else "NO"
    if isinstance(v, (int, np.integer)):
        return f"{v:d}"
    if isinstance(v, (float, np.floating)):
        a = abs(v)
        if a == 0:
            return "0"
        if a >= 1e5 or a < 1e-3:
            return f"{v:.4g}"
        if a >= 1000:
            return f"{v:,.0f}"
        return f"{v:.4g}"
    return str(v)


def _md(rows: list[dict], cols: list[str] | None = None) -> str:
    cols = cols or list(rows[0])
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(_fmt(r[c]) for c in cols) + " |" for r in rows]
    return "\n".join(out)


def design_rows(drs) -> list[dict]:
    rows = []
    for dr in drs:
        p, u = dr.props, dr.utilisation()
        v, rv = dr.worst("v_tip")
        th, rt = dr.worst("theta_tip")
        s, rs = dr.worst("sigma")
        ta, rta = dr.worst("tau")
        rows.append(dict(
            design=dr.design.name, label=dr.design.label, box_mass_both_wings_kg=dr.mass_total,
            t_skin_root_mm=p.t_skin_top[0] * 1e3, t_skin_tip_mm=p.t_skin_top[-1] * 1e3,
            t_spar_root_mm=p.t_front_spar[0] * 1e3, t_spar_tip_mm=p.t_front_spar[-1] * 1e3,
            n_str_root=int(p.n_str_top[0]), n_str_tip=int(p.n_str_top[-1]),
            A_str_root_mm2=p.A_str_top[0] * 1e6, A_cap_root_mm2=p.A_cap[0] * 1e6,
            n_cells_root=int(p.n_cells[0]), Ixx_root_m4=p.I_xx[0], J_root_m4=p.J[0],
            max_v_tip_m=v, case_v=rv.case.id, max_theta_tip_deg=th, case_theta=rt.case.id,
            max_sigma_ult_MPa=s / 1e6, case_sigma=rs.case.id, max_tau_ult_MPa=ta / 1e6, case_tau=rta.case.id,
            **{f"util_{k}": x for k, x in u.items()}, compliant=dr.compliant))
    return rows


def load_case_rows(case_loads, drs) -> list[dict]:
    rows = []
    for i, c in enumerate(case_loads):
        lc = c.case
        row = dict(id=lc.id, description=lc.description, weight=lc.weight, mass_kg=lc.mass,
                   fuel_wing_half_kg=lc.fuel_wing_half, fuel_fuselage_kg=lc.fuel_fuselage,
                   altitude_m=lc.altitude, V_EAS=lc.V_EAS, n=lc.n, Mach=lc.mach, CL=lc.CL,
                   alpha_deg=c.alpha_deg, q_Pa=lc.q, thrust_per_engine_kN=lc.thrust / 1e3,
                   S_root_kN=c.shear()[0] / 1e3, M_root_kNm=c.bending()[0] / 1e3)
        for dr in drs:
            r = dr.cases[i]
            row[f"T_root_kNm_{dr.design.name}"] = r.T[0] / 1e3
            row[f"v_tip_m_{dr.design.name}"] = r.defl.v_tip
            row[f"theta_tip_deg_{dr.design.name}"] = r.defl.theta_tip_deg
        rows.append(row)
    return rows


def matrix_rows(drs) -> list[dict]:
    """Every design x every load case: tip values, peak stresses and utilisations."""
    rows = []
    for dr in drs:
        lim = dr.limits
        for r in dr.cases:
            rows.append(dict(design=dr.design.name, case=r.case.id, description=r.case.description,
                             weight=r.case.weight, altitude_m=r.case.altitude, n=r.case.n,
                             v_tip_m=r.defl.v_tip, util_v=abs(r.defl.v_tip) / lim["v_tip"],
                             theta_tip_deg=r.defl.theta_tip_deg,
                             util_theta=abs(r.defl.theta_tip_deg) / lim["theta_tip"],
                             sigma_max_ult_MPa=r.sigma.max() / 1e6, util_sigma=r.sigma.max() / lim["sigma"],
                             tau_max_ult_MPa=r.tau.max() / 1e6, util_tau=r.tau.max() / lim["tau"],
                             S_root_kN=r.S[0] / 1e3, M_root_kNm=r.M[0] / 1e3, T_root_kNm=r.T[0] / 1e3))
    return rows


def spanwise_rows(dr, crit_ids, every: int = 1) -> list[dict]:
    p = dr.props
    rows = []
    for j in range(0, len(p.y), every):
        row = dict(y_m=p.y[j], eta=p.y[j] / p.y[-1], chord_m=p.chord[j], area_m2=p.area[j],
                   x_sc_m=p.x_c[j], z_c_m=p.z_c[j], Ixx_m4=p.I_xx[j], J_m4=p.J[j], n_cells=int(p.n_cells[j]),
                   h_front_mm=p.h_f[j] * 1e3, h_rear_mm=p.h_r[j] * 1e3,
                   t_skin_top_mm=p.t_skin_top[j] * 1e3, t_skin_bot_mm=p.t_skin_bot[j] * 1e3,
                   t_front_spar_mm=p.t_front_spar[j] * 1e3, t_rear_spar_mm=p.t_rear_spar[j] * 1e3,
                   t_mid_spar_mm=p.t_mid_spar[j] * 1e3, n_str_top=int(p.n_str_top[j]),
                   n_str_bot=int(p.n_str_bot[j]), A_str_top_mm2=p.A_str_top[j] * 1e6,
                   A_str_bot_mm2=p.A_str_bot[j] * 1e6, A_cap_mm2=p.A_cap[j] * 1e6)
        for cid in crit_ids.values():
            r = dr.result(cid)
            row.update({f"{cid}_S_N": r.S[j], f"{cid}_M_Nm": r.M[j], f"{cid}_T_Nm": r.T[j],
                        f"{cid}_N_N": r.N[j], f"{cid}_v_m": r.defl.v[j],
                        f"{cid}_theta_deg": np.degrees(r.defl.theta[j]),
                        f"{cid}_sigma_ult_MPa": r.sigma[j] / 1e6, f"{cid}_tau_ult_MPa": r.tau[j] / 1e6})
        rows.append(row)
    return rows


def write_all(out: Path, model, case_loads, crit, drs, checks, figures) -> dict[str, Path]:
    ac = model.ac
    tab = out / "tables"
    crit_ids = {k: v.case.id for k, v in crit.items()}
    vn_rows = [d.speeds() for d in model.diagrams]
    lc_rows = load_case_rows(case_loads, drs)
    d_rows = design_rows(drs)
    m_rows = matrix_rows(drs)
    paths = {
        "vn": _csv(tab / "vn_speeds.csv", vn_rows),
        "load_cases": _csv(tab / "load_cases.csv", lc_rows),
        "designs": _csv(tab / "designs.csv", d_rows),
        "matrix": _csv(tab / "design_x_loadcase.csv", m_rows),
        "checks": _csv(tab / "model_checks.csv", checks),
    }
    for dr in drs:
        paths[f"spanwise_{dr.design.name}"] = _csv(tab / f"spanwise_{dr.design.name}.csv",
                                                   spanwise_rows(dr, crit_ids))

    p, m, e, gr = ac.planform, ac.masses, ac.engine, ac.gear
    L = []
    L.append("# WP4 results, group A11 (generated by run_wp4.py)\n")
    L.append(f"Generated {datetime.now():%Y-%m-%d %H:%M}. Inputs: `config/aircraft.toml`, `config/designs.toml`. "
             "All loads are LIMIT loads unless marked ultimate (x1.5). Sign convention (reader App. C): "
             "S + = net upward load outboard, M negative when the wing bends up, T + nose-up, "
             "v + up, theta + nose-up. Full-precision numbers are in `output/tables/*.csv`.\n")

    L.append("## 1. Summary\n")
    L.append(f"* Critical positive case: **{crit['positive'].case.id}** ({crit['positive'].case.description}, "
             f"{crit['positive'].case.weight}, h = {crit['positive'].case.altitude:.0f} m, n = "
             f"{crit['positive'].case.n:+.2f}, M_root = {crit['positive'].bending()[0] / 1e3:,.0f} kNm)")
    L.append(f"* Critical negative case: **{crit['negative'].case.id}** ({crit['negative'].case.description}, "
             f"{crit['negative'].case.weight}, h = {crit['negative'].case.altitude:.0f} m, n = "
             f"{crit['negative'].case.n:+.2f}, M_root = {crit['negative'].bending()[0] / 1e3:,.0f} kNm)")
    for r in d_rows:
        L.append(f"* Design **{r['label']}**: box mass {r['box_mass_both_wings_kg']:,.0f} kg (both wings), "
                 f"max tip deflection {r['max_v_tip_m']:.3f} m ({r['case_v']}), max tip twist "
                 f"{r['max_theta_tip_deg']:.2f} deg ({r['case_theta']}), "
                 f"{'meets all requirements' if r['compliant'] else '**DOES NOT meet every requirement**'}.")
    L.append("")
    L.append("## 2. Requirement compliance (worst load case per requirement)\n")
    lim = drs[0].limits
    req = [("REQ-WB-STIFF-01: tip displacement <= 0.15 b", "v_tip", f"{lim['v_tip']:.3f} m", "max_v_tip_m", "m"),
           ("REQ-WB-STIFF-02: tip rotation <= 10 deg", "theta_tip", f"{lim['theta_tip']:.1f} deg",
            "max_theta_tip_deg", "deg")]
    if lim["strength"]:
        req += [("(info) normal stress at ultimate <= yield", "sigma", f"{lim['sigma'] / 1e6:.0f} MPa",
                 "max_sigma_ult_MPa", "MPa"),
                ("(info) web shear at ultimate <= yield/sqrt(3)", "tau", f"{lim['tau'] / 1e6:.0f} MPa",
                 "max_tau_ult_MPa", "MPa")]
    hdr = "| requirement | limit | " + " | ".join(f"design {r['design']}" for r in d_rows) + " |"
    L += [hdr, "|" + "---|" * (2 + len(d_rows))]
    for text, k, limtxt, col, unit in req:
        cells = []
        for r in d_rows:
            u = r[f"util_{k}"]
            cells.append(f"{r[col]:.3g} {unit} (util {u:.2f}, {'OK' if u <= 1 + 1e-9 else 'FAIL'})")
        L.append(f"| {text} | {limtxt} | " + " | ".join(cells) + " |")
    L.append("\nThe strength rows are informative: WP4 only requires stiffness (reader WP4.2); "
             "`requirements.strength_check` decides whether they count for 'compliant'.\n")

    L.append("## 3. Inputs used\n")
    inp = [
        ("S, b, AR", f"{p.S} m2, {p.b} m, {p.b ** 2 / p.S:.2f}"),
        ("W/S at MTOM", f"{m.MTOM * G0 / p.S:,.0f} N/m2"),
        ("c_root, c_tip, taper", f"{p.c_root} m, {p.c_tip} m, {p.taper:.3f}"),
        ("sweep LE / c/4, dihedral", f"{p.sweep_LE_deg} / {p.sweep_c4_deg} deg, {p.dihedral_deg} deg"),
        ("airfoil, spars", f"{model.geom.airfoil.name} (t/c {model.geom.airfoil.t_c_max:.3f}), "
                           f"{ac.wingbox.x_front_spar}c / {ac.wingbox.x_rear_spar}c, "
                           f"h_f {model.geom.airfoil.thickness(ac.wingbox.x_front_spar):.4f}c, "
                           f"h_r {model.geom.airfoil.thickness(ac.wingbox.x_rear_spar):.4f}c"),
        ("MTOM / OEM / MPW", f"{m.MTOM:,.0f} / {m.OEM:,.0f} / {m.payload_max:,.0f} kg"),
        ("wing mass (both wings), CG", f"{m.m_wing_total:,.0f} kg, {m.x_wing_cg_frac}c"),
        ("engine per side", f"{e.m_engine:,.1f} kg at y = {e.y_engine} m, CG {e.x_cg_rel_LEMAC} m from LEMAC "
                            f"(= {model.geom.x_from_LEMAC_to_local(e.x_cg_rel_LEMAC, e.y_engine):.3f} m from local LE)"),
        ("thrust", f"{e.T0_per_engine / 1e3:.1f} kN x sigma^{e.thrust_lapse_exp}, line {e.z_thrust_below} m "
                   f"below the chord plane ({e.thrust_mode})"),
        ("main gear", (f"{gr.m_total:,.0f} kg (both legs) at y = {gr.y} m, {gr.x_rel_LEMAC} m aft of LEMAC"
                       if gr.include else "not on the wing")),
        ("fuel tank", f"eta {ac.fuel.tank_eta_start}-{ac.fuel.tank_eta_end}, usable capacity "
                      f"{2 * model.tank.capacity_half:,.0f} kg (both wings), centroid {model.tank.x_c_frac:.3f}c"),
        ("material", f"{ac.material.name}: E {ac.material.E / 1e9:.1f} GPa, G {ac.material.G / 1e9:.1f} GPa, "
                     f"rho {ac.material.rho:.0f} kg/m3, yield {ac.material.sigma_y / 1e6:.0f} MPa"),
        ("aero", f"flow5 alpha 0/10 deg: CL0 {model.aero.CL_0:.4f}, CL_alpha {model.aero.CLa_deg:.5f} /deg, "
                 f"lift normalisation {model.aero.k_0:.4f} / {model.aero.k_10:.4f}, "
                 f"Prandtl-Glauert {ac.aero.prandtl_glauert}"),
        ("grid", f"{len(case_loads[0].y)} spanwise stations, deflection integration: "
                 f"{ac.numerics.deflection_method}"),
    ]
    L += ["| quantity | value |", "|---|---|"] + [f"| {a} | {b} |" for a, b in inp]
    L.append("")

    L.append("## 4. V-n diagrams (WP4.3.b), speeds in m/s EAS\n")
    L.append(_md(vn_rows))
    L.append("")
    L.append("## 5. Load cases (WP4.3.c) and root loads (WP4.1)\n")
    cols = ["id", "description", "weight", "altitude_m", "V_EAS", "n", "Mach", "CL", "alpha_deg",
            "fuel_wing_half_kg", "S_root_kN", "M_root_kNm"] + [f"T_root_kNm_{d.design.name}" for d in drs]
    L.append(_md(lc_rows, cols))
    L.append("\nTip deflection and twist per case and design:\n")
    cols = ["id"] + [f"{q}_{d.design.name}" for d in drs for q in ("v_tip_m", "theta_tip_deg")]
    L.append(_md(lc_rows, cols))
    L.append("")

    L.append("## 6. Design options (WP4.3.e)\n")
    for dr in drs:
        d = dr.design
        L.append(f"### {d.label}\n")
        L.append(f"{d.philosophy}\n")
        spec = [("top skin t [mm]", d.t_skin_top, 1e3), ("bottom skin t [mm]", d.t_skin_bot, 1e3),
                ("front spar t [mm]", d.t_front_spar, 1e3), ("rear spar t [mm]", d.t_rear_spar, 1e3),
                ("stringers per top skin", d.n_str_top, 1), ("stringers per bottom skin", d.n_str_bot, 1),
                ("top stringer area [mm2]", d.A_str_top, 1e6), ("bottom stringer area [mm2]", d.A_str_bot, 1e6),
                ("corner cap area, each [mm2]", d.A_cap, 1e6)]
        L += ["| quantity | eta breakpoints | values | interpolation |", "|---|---|---|---|"]
        for name, v, k in spec:
            L.append(f"| {name} | {', '.join(f'{x:g}' for x in v.eta)} | "
                     f"{', '.join(f'{x * k:g}' for x in v.val)} | {v.kind} |")
        if d.mid_spar:
            L.append(f"| mid spar | x/c = {d.mid_spar.x_c}, root to eta = {d.mid_spar.eta_end} | "
                     f"t: {', '.join(f'{x * 1e3:g}' for x in d.mid_spar.t.val)} mm | {d.mid_spar.t.kind} |")
        L.append("")
        pr = dr.props
        idx = [int(np.argmin(abs(pr.y / pr.y[-1] - e))) for e in (0, 0.2, 0.35, 0.4, 0.6, 0.8, 1.0)]
        rows = [dict(y_m=pr.y[j], chord_m=pr.chord[j], t_skin_mm=pr.t_skin_top[j] * 1e3,
                     t_spar_mm=pr.t_front_spar[j] * 1e3, n_str=int(pr.n_str_top[j]), cells=int(pr.n_cells[j]),
                     area_cm2=pr.area[j] * 1e4, x_sc_over_c=pr.x_c[j] / pr.chord[j], Ixx_m4=pr.I_xx[j],
                     J_m4=pr.J[j]) for j in idx]
        L.append(_md(rows))
        L.append(f"\nBox mass {dr.mass_total:,.1f} kg (both wings, skins + spars + stringers + caps, no ribs).\n")
    L.append("### Comparison\n")
    L.append(_md(d_rows, [k for k in d_rows[0] if k != "label"]))
    L.append("")

    L.append("## 7. Model verification\n")
    L.append(_md(checks))
    L.append("")
    L.append("## 8. Files\n")
    L.append("Tables (`output/tables/`): " + ", ".join(f"`{q.name}`" for q in paths.values()) + ".\n")
    L.append("Figures (`output/figures/`): " + ", ".join(f"`{f.name}`" for f in figures) + ".\n")
    summary = out / "WP4_results.md"
    summary.write_text("\n".join(L), encoding="utf-8")
    paths["summary"] = summary
    return paths
