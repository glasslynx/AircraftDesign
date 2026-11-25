"""All WP4 figures (written to output/figures/)."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

COLORS = {"A": "#1f77b4", "B": "#d62728", "C": "#2ca02c"}


def _save(fig, out: Path, name: str) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    p = out / name
    fig.savefig(p, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return p


def _color(name: str, i: int) -> str:
    return COLORS.get(name, f"C{i}")


# --------------------------------------------------------------------------- #
#  V-n diagrams (WP4.3.b)                                                     #
# --------------------------------------------------------------------------- #
def _vn_axes(ax, d, annotate=True):
    up, flaps = d.envelope()
    ax.plot(up[:, 0], up[:, 1], "k-", lw=2, label="flaps up")
    ax.plot(flaps[:, 0], flaps[:, 1], "b--", lw=1.5, label="flaps down")
    ax.axhline(0, color="k", lw=0.8)
    for n in (1, -1):
        ax.axhline(n, color="grey", ls=":", lw=0.8)
    if annotate:
        for k, (V, n) in d.corner_points().items():
            ax.plot(V, n, "ro", ms=5)
            ax.annotate(k, (V, n), xytext=(5, 6 if n >= 0 else -14), textcoords="offset points",
                        fontweight="bold")
        for lab, V in (("$V_{S1}$", d.VS1), ("$V_A$", d.VA), ("$V_C$", d.VC), ("$V_D$", d.VD)):
            ax.axvline(V, color="grey", ls="--", lw=0.6)
            ax.text(V, d.n_min - 0.55, lab, ha="center", fontsize=8)
    ax.set_xlim(0, d.VD * 1.12)
    ax.set_ylim(d.n_min - 0.8, d.n_max + 0.8)
    ax.set_xlabel(r"$V_{EAS}$ [m/s]")
    ax.set_ylabel("n [-]")
    ax.grid(True, ls=":", alpha=0.6)


def fig_vn_all(diagrams, out: Path) -> list[Path]:
    paths = []
    for d in diagrams:
        fig, ax = plt.subplots(figsize=(8, 5))
        _vn_axes(ax, d)
        ax.set_title(f"Manoeuvre diagram, {d.wc.label}, W = {d.wc.mass:,.0f} kg, h = {d.altitude:,.0f} m")
        txt = (f"$V_{{S1}}$ {d.VS1:.1f}  $V_{{S0}}$ {d.VS0:.1f}  $V_A$ {d.VA:.1f}\n"
               f"$V_C$ {d.VC:.1f}  $V_D$ {d.VD:.1f}  $V_F$ {d.VF:.1f} m/s EAS")
        ax.text(0.02, 0.97, txt, transform=ax.transAxes, va="top", fontsize=8,
                bbox=dict(boxstyle="round", fc="whitesmoke", ec="grey"))
        ax.legend(loc="center left", fontsize=8)
        paths.append(_save(fig, out, f"vn_{d.wc.name}_{d.altitude / 1000:.1f}km.png"))
    fig, axs = plt.subplots(2, 3, figsize=(15, 8), sharey=True)
    for ax, d in zip(axs.flat, diagrams):
        _vn_axes(ax, d, annotate=False)
        ax.set_title(d.name, fontsize=10)
    fig.tight_layout()
    paths.append(_save(fig, out, "vn_overview.png"))
    return paths


# --------------------------------------------------------------------------- #
#  inputs                                                                      #
# --------------------------------------------------------------------------- #
def fig_inputs(model, out: Path) -> Path:
    aero, geom, tank, lm = model.aero, model.geom, model.tank, model.loads
    y = np.linspace(0, geom.planform.half_span, 400)
    fig, axs = plt.subplots(1, 3, figsize=(15, 4))
    for a_deg, ls in ((0, "-"), (10, "--")):
        axs[0].plot(y, aero.CL_d(y, alpha_d=a_deg), ls, label=fr"$c_l$, $\alpha$ = {a_deg}°")
        axs[1].plot(y, aero.CM_d(y, alpha_d=a_deg), ls, label=fr"$c_m$ (c/4), $\alpha$ = {a_deg}°")
    axs[0].plot(aero.ylst, aero.k_0 * aero.Cllst_0, "k.", ms=4)
    axs[0].plot(aero.ylst, aero.k_10 * aero.Cllst_10, "k.", ms=4, label="flow5 strips")
    axs[0].set_title("Section lift coefficient (flow5)")
    axs[1].set_title("Section pitching moment coefficient")
    m_fuel = max(c.fuel_wing_half for c in model.cases)
    axs[2].plot(y, lm.wing_mass_per_span(y), label="wing structure (Class II, ~ c)")
    axs[2].plot(y, tank.mass_per_span(y, m_fuel), label=f"fuel at MTOW ({m_fuel:.0f} kg per half wing, ~ c²)")
    axs[2].axvline(model.ac.engine.y_engine, color="grey", ls="--", lw=0.8)
    axs[2].text(model.ac.engine.y_engine, axs[2].get_ylim()[1] * 0.9, " engine", fontsize=8)
    axs[2].set_title("Mass per unit span [kg/m]")
    for ax in axs:
        ax.set_xlabel("y [m]")
        ax.grid(True, alpha=0.5)
        ax.legend(fontsize=8)
    fig.tight_layout()
    return _save(fig, out, "inputs_aero_mass.png")


# --------------------------------------------------------------------------- #
#  WP4.1                                                                       #
# --------------------------------------------------------------------------- #
def fig_load_case_scatter(case_loads, crit, out: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 5))
    for c in case_loads:
        S0, M0 = c.shear()[0] / 1e3, c.bending()[0] / 1e3
        ax.plot(M0, S0, "o", color="k" if c.case.n >= 0 else "grey", ms=5)
        ax.annotate(c.case.id[3:], (M0, S0), fontsize=7, xytext=(3, 2), textcoords="offset points")
    for k, c in crit.items():
        ax.plot(c.bending()[0] / 1e3, c.shear()[0] / 1e3, "r*", ms=14, label=f"critical {k}: {c.case.id}")
    ax.set_xlabel(r"root bending moment $M_x(0)$ [kNm] (reader sign: negative = tip up)")
    ax.set_ylabel("root shear force S(0) [kN]")
    ax.set_title("All load cases at the wing root (limit loads)")
    ax.grid(True, alpha=0.5)
    ax.legend()
    return _save(fig, out, "load_cases_root.png")


def fig_distributed_loads(crit, out: Path) -> Path:
    fig, axs = plt.subplots(1, len(crit), figsize=(7 * len(crit), 4.5), squeeze=False)
    for ax, (k, c) in zip(axs[0], crit.items()):
        ax.plot(c.y, c.w_aero / 1e3, label="aerodynamic N'")
        ax.plot(c.y, c.w_wing / 1e3, label="wing weight")
        ax.plot(c.y, c.w_fuel / 1e3, label="fuel weight")
        ax.plot(c.y, c.w / 1e3, "k", lw=2, label="net distributed load")
        for p in c.points:
            ax.annotate(f"{p.name}\n{p.P / 1e3:+.1f} kN", (p.y, 0), xytext=(p.y, c.w.max() / 2e3),
                        arrowprops=dict(arrowstyle="->"), fontsize=8, ha="center")
        ax.set_title(f"{k}: {c.case.id}, {c.case.description}, {c.case.weight}, "
                     f"h {c.case.altitude:.0f} m, n = {c.case.n:+.2f}", fontsize=9)
        ax.set_xlabel("y [m]")
        ax.set_ylabel("load per unit span [kN/m]")
        ax.grid(True, alpha=0.5)
        ax.legend(fontsize=8)
    fig.tight_layout()
    return _save(fig, out, "distributed_loads.png")


def fig_internal_loads(crit_ids, drs, out: Path) -> list[Path]:
    """Shear, bending and torque (and axial) diagrams of the critical cases (WP4.1.b).
    S, M and N do not depend on the design; T does (shear-centre position), so T is one line per design."""
    paths = []
    first = drs[0]
    for qty, unit, scale, name in (("S", "kN", 1e3, "shear"), ("M", "kNm", 1e3, "bending"),
                                   ("T", "kNm", 1e3, "torque"), ("N", "kN", 1e3, "axial")):
        fig, axs = plt.subplots(1, len(crit_ids), figsize=(7 * len(crit_ids), 4), squeeze=False)
        for ax, (k, cid) in zip(axs[0], crit_ids.items()):
            if qty == "T":
                for i, dr in enumerate(drs):
                    r = dr.result(cid)
                    ax.plot(r.loads.y, r.T / scale, color=_color(dr.design.name, i), label=dr.design.label)
                ax.legend(fontsize=8)
            else:
                r = first.result(cid)
                ax.plot(r.loads.y, getattr(r, qty) / scale, "k", lw=2)
            c = first.result(cid).case
            ax.set_title(f"{name}, {k} critical: {c.id} (n = {c.n:+.2f}, {c.weight}, h {c.altitude:.0f} m)",
                         fontsize=9)
            ax.set_xlabel("y [m]")
            ax.set_ylabel(f"{qty}(y) [{unit}]")
            ax.axhline(0, color="k", lw=0.6)
            ax.grid(True, alpha=0.5)
        fig.tight_layout()
        paths.append(_save(fig, out, f"diagram_{name}.png"))
    return paths


# --------------------------------------------------------------------------- #
#  WP4.2                                                                       #
# --------------------------------------------------------------------------- #
def fig_stiffness(drs, out: Path) -> Path:
    fig, axs = plt.subplots(1, 3, figsize=(16, 4))
    for i, dr in enumerate(drs):
        p, col = dr.props, _color(dr.design.name, i)
        axs[0].plot(p.y, p.I_xx * 1e6, color=col, label=dr.design.label)
        axs[1].plot(p.y, p.J * 1e6, color=col, label=dr.design.label)
        axs[2].plot(p.y, p.x_c / p.chord, color=col, label=dr.design.label)
    for ax, t in zip(axs, (r"$I_{xx}$ [$10^{-6}$ m$^4$]", r"$J$ [$10^{-6}$ m$^4$]",
                           r"centroid = shear centre $x_c / c$ [-]")):
        ax.set_title(t)
        ax.set_xlabel("y [m]")
        ax.grid(True, alpha=0.5)
        ax.legend(fontsize=8)
    fig.tight_layout()
    return _save(fig, out, "stiffness_Ixx_J.png")


def fig_deflection(dr, crit_ids, limits, out: Path) -> Path:
    fig, (a1, a2) = plt.subplots(2, 1, sharex=True, figsize=(8, 7))
    for k, cid in crit_ids.items():
        r = dr.result(cid)
        lab = f"{cid} ({k}, n = {r.case.n:+.2f})"
        a1.plot(r.defl.y, r.defl.v, label=lab)
        a2.plot(r.defl.y, np.degrees(r.defl.theta), label=lab)
    for ax, lim in ((a1, limits["v_tip"]), (a2, limits["theta_tip"])):
        ax.axhline(lim, ls="--", c="r", lw=1, label="requirement limit")
        ax.axhline(-lim, ls="--", c="r", lw=1)
        ax.grid(True, alpha=0.5)
        ax.legend(fontsize=8)
    a1.set_ylim(-1.15 * limits["v_tip"], 1.15 * limits["v_tip"])
    a1.set_ylabel("displacement v [m]")
    a2.set_ylabel(r"twist $\theta$ [deg]")
    a2.set_xlabel("y [m]")
    a1.set_title(f"Design {dr.design.label}: bending deflection and twist (limit load)")
    fig.tight_layout()
    return _save(fig, out, f"deflection_{dr.design.name}.png")


def fig_cross_sections(drs, geom, out: Path) -> Path:
    from .section import compute_section
    stations = (0.0, geom.planform.half_span * 0.35, geom.planform.half_span * 0.7)
    fig, axs = plt.subplots(len(drs), len(stations), figsize=(15, 1.9 * len(drs)), squeeze=False)
    for row, dr in zip(axs, drs):
        for ax, ys in zip(row, stations):
            s = compute_section(ys, dr.design, geom)
            C = np.vstack([s["corners"], s["corners"][:1]])
            ax.plot(C[:, 0], C[:, 1], "k-", lw=1.5)
            if s["h_mid"] > 0:
                xm = dr.design.mid_spar.x_c * s["chord"]
                zt = np.interp(xm, [C[0, 0], C[3, 0]], [C[0, 1], C[3, 1]])
                zb = np.interp(xm, [C[1, 0], C[2, 0]], [C[1, 1], C[2, 1]])
                ax.plot([xm, xm], [zt, zb], "k-", lw=1.5)
            for st in (s["stringers_top"], s["stringers_bot"]):
                if len(st):
                    ax.plot(st[:, 0], st[:, 1], "s", color=_color(dr.design.name, 0), ms=4)
            if s["A_cap"] > 0:
                ax.plot(s["corners"][:, 0], s["corners"][:, 1], "o", color="orange", ms=7)
            ax.plot(s["x_c"], s["z_c"], "r+", ms=10)
            ax.set_aspect("equal", adjustable="datalim")
            ax.set_title(f"{dr.design.name}, y = {ys:.2f} m: t_skin {s['t_skin_top'] * 1e3:.1f} mm, "
                         f"t_spar {s['t_front_spar'] * 1e3:.1f} mm, {s['n_str_top']} str/skin", fontsize=8)
            ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return _save(fig, out, "cross_sections.png")


def fig_utilisation(drs, out: Path) -> Path:
    keys = list(drs[0].utilisation())
    labels = {"v_tip": "tip deflection", "theta_tip": "tip twist", "sigma": "normal stress (yield)",
              "tau": "web shear (yield)"}
    x = np.arange(len(keys))
    w = 0.8 / len(drs)
    fig, ax = plt.subplots(figsize=(9, 4))
    for i, dr in enumerate(drs):
        u = dr.utilisation()
        ax.bar(x + (i - (len(drs) - 1) / 2) * w, [u[k] for k in keys], w,
               color=_color(dr.design.name, i), label=f"{dr.design.label} ({dr.mass_total:.0f} kg)")
    ax.axhline(1.0, color="r", ls="--", lw=1)
    ax.set_xticks(x, [labels[k] for k in keys])
    ax.set_ylabel("utilisation = applied / allowed [-]")
    ax.set_title("Requirement utilisation, worst load case per requirement")
    ax.grid(True, axis="y", alpha=0.5)
    ax.legend(fontsize=8)
    return _save(fig, out, "utilisation.png")
