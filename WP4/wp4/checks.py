"""Model verification checks, run with every analysis and listed in WP4_results.md.

Each check compares the code with an independent closed-form or balance result.
"""
from __future__ import annotations

import numpy as np
from scipy.integrate import quad

from .config import G0
from .deflection import deflection
from .section import polygon_area, torsion_constant


def run_checks(model, case_loads, drs) -> list[dict]:
    ac, rows = model.ac, []

    def add(name, value, reference, tol):
        err = abs(value - reference) / max(abs(reference), 1e-12)
        rows.append(dict(check=name, value=value, reference=reference, rel_error=err, ok=err <= tol))

    # 1. lift equilibrium: 2 int L' dy = n W for every case with n != 0
    worst = 0.0
    for c in case_loads:
        if c.case.n == 0:
            continue
        L = model.aero.lift_per_unit_span(c.y, c.case.q, CL_d=c.case.CL,
                                          M=c.case.mach if ac.aero.prandtl_glauert else 0.0)
        ratio = 2 * np.trapezoid(L, c.y) / (c.case.n * c.case.mass * G0)
        worst = max(worst, abs(ratio - 1))
    add("lift equilibrium 2 int L' dy / (n W), worst case", 1 + worst, 1.0, 1e-3)

    # 2. root shear = sum of all loads on the half wing (vertical force balance)
    c = case_loads[0]
    total = np.trapezoid(c.w, c.y) + sum(p.P for p in c.points)
    add(f"root shear S(0) = total load on the half wing ({c.case.id})", c.shear()[0], total, 1e-9)

    # 3. wing and fuel mass are distributed without losing mass
    mw = np.trapezoid(model.loads.wing_mass_per_span(c.y), c.y)
    add("wing mass per half wing [kg]", mw, ac.masses.m_wing_total / 2, 1e-6)
    cm = next(x for x in case_loads if x.case.fuel_wing_half > 0)
    mf = np.trapezoid(model.tank.mass_per_span(cm.y, cm.case.fuel_wing_half), cm.y)
    add("fuel mass per half wing at MTOW [kg]", mf, cm.case.fuel_wing_half, 5e-3)
    add("usable wing-tank volume, both wings [m3] (WP3: 7.05)",
        2 * model.tank.volume_half * ac.fuel.usable_factor, 7.05, 5e-3)

    # 4. deflection integration vs cantilever closed forms (uniform load w, constant EI / GJ)
    L, w, EI, T, GJ = 12.735, 1e4, 72.4e9 * 1e-3, 1e4, 28e9 * 1e-3
    y = np.linspace(0, L, 201)
    d = deflection(y, -w * (L - y) ** 2 / 2, np.full_like(y, T), np.full_like(y, EI), np.full_like(y, GJ),
                   ac.numerics.deflection_method)
    add("cantilever tip deflection w L^4 / (8 EI) [m]", d.v_tip, w * L**4 / (8 * EI), 1e-3)
    add("constant-torque tip twist T L / (G J) [rad]", float(d.theta[-1]), T * L / GJ, 1e-6)
    # tapered EI(y) = EI0 (1 - 0.6 y/L): reference by Mohr's theorem v_tip = int (L - y) (-M / EI) dy (quad)
    EIy = lambda s: EI * (1 - 0.6 * s / L)
    Mf = lambda s: -w * (L - s) ** 2 / 2
    ref = quad(lambda s: (L - s) * (-Mf(s) / EIy(s)), 0, L)[0]
    y = np.linspace(0, L, ac.numerics.n_stations)
    d = deflection(y, Mf(y), np.zeros_like(y), EIy(y), np.ones_like(y), ac.numerics.deflection_method)
    add("tapered-EI tip deflection vs Mohr integral [m] (grid convergence)", d.v_tip, ref, 1e-3)

    # 5. torsion constant: one cell vs Bredt 4 A^2 / (sum s / t); two cells with a zero-thickness mid spar
    corners = [(0, 0.5), (0, -0.5), (1, -0.4), (1, 0.4)]
    t = [0.004, 0.006, 0.004, 0.006]
    P = np.array([corners[0], corners[3], corners[2], corners[1]], float)
    s = sum(np.linalg.norm(P[(i + 1) % 4] - P[i]) / ti for i, ti in enumerate(t))
    add("one-cell J vs 4 A^2 / (sum s/t) [m4]", torsion_constant(corners, t)[0], 4 * polygon_area(P) ** 2 / s, 1e-12)
    add("two-cell J with a very thin mid spar = one-cell J [m4]",
        torsion_constant(corners, t, 1e-9, 0.5)[0], torsion_constant(corners, t)[0], 1e-4)

    return rows
