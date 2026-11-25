"""WP4.1: distributed loads and the shear force, bending moment and torque diagrams (reader App. C).

(from shear_moment_diagrams.py; torque part added)

Loads on one half wing, normal to the chord plane, per unit span (+ up) [N/m]:
    aerodynamic   N'(y) = L'(y) cos(alpha) + D'(y) sin(alpha)       (wingcoefficients.py, reader C.2)
    wing weight   -n g m_w'(y),   m_w' ~ c(y)  (Class II wing mass, CG at x_wing_cg_frac c)
    fuel          -n g m_f'(y),   m_f' ~ c(y)^2 inside the tank (fuel.py)
point loads:
    engine        -n g m_eng at y_e, CG at x_e (from LEMAC); thrust T below the chord plane
                  gives a nose-up couple T cos(sweep) z_t and an axial force T sin(sweep)
    main gear     -n g m_gear/2 at y_gear (retracted in flight, carried by the wing)

Sign convention (reader App. C):
    S(y) =  int_y^{b/2} w dy' + sum P_i H(y_i - y)        + = net upward load outboard of y
    M(y) = -int_y^{b/2} S dy'                             upward load -> NEGATIVE M (tip up)
    T(y) =  int_y^{b/2} t dy' + sum T_i H(y_i - y)        + = nose-up, about the shear centre
with the distributed torque about the shear centre x_sc(y) (= centroid, from section.py)
    t(y) = sum_i w_i(y) (x_sc - x_i) + m'(y)               (m' = aero moment about c/4, + nose-up)

The torque depends on x_sc, a design output (WP4.2). Since t is linear in x_sc,
t = w x_sc + t0, the design-independent parts are stored once per load case.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import cumulative_trapezoid

from .config import G0, Aircraft
from .fuel import FuelTank
from .geometry import WingGeometry
from .loadcases import LoadCase
from .wingcoefficients import WingAerodynamicsInterpolator


def integrate_from_tip(f: np.ndarray, y: np.ndarray) -> np.ndarray:
    """F(y) = int_y^{b/2} f dy' on the grid (trapezoidal rule)."""
    return -cumulative_trapezoid(f[::-1], y[::-1], initial=0.0)[::-1]


@dataclass(frozen=True)
class PointLoad:
    name: str
    y: float          # span station [m]
    P: float          # force normal to the chord plane, + up [N]
    x: float          # point of application from the local LE (+ aft) [m]
    couple: float = 0.0   # extra nose-up couple [Nm] (thrust below the chord plane)


@dataclass
class CaseLoads:
    """Design-independent loading of one load case on a spanwise grid."""
    case: LoadCase
    y: np.ndarray
    chord: np.ndarray
    alpha_deg: float
    w_aero: np.ndarray      # N' [N/m]
    w_wing: np.ndarray      # wing-structure inertia [N/m]
    w_fuel: np.ndarray      # fuel inertia [N/m]
    m_ac: np.ndarray        # aero pitching moment about c/4 [Nm/m]
    t0: np.ndarray          # torque part independent of x_sc [Nm/m]
    points: tuple[PointLoad, ...]
    F_axial: float          # thrust component along the box axis [N]
    y_engine: float

    @property
    def w(self) -> np.ndarray:
        return self.w_aero + self.w_wing + self.w_fuel

    def shear(self) -> np.ndarray:
        S = integrate_from_tip(self.w, self.y)
        for p in self.points:
            S = S + p.P * (self.y < p.y)
        return S

    def bending(self) -> np.ndarray:
        """Reader sign: negative when the wing bends up."""
        return -integrate_from_tip(self.shear(), self.y)

    def axial(self) -> np.ndarray:
        """Axial force, + tension: thrust pushes the box inboard of the engine (compression)."""
        return -self.F_axial * (self.y < self.y_engine)

    def torque(self, x_sc: np.ndarray) -> np.ndarray:
        """Internal torque about the shear centre x_sc(y) [m aft of the local LE]."""
        x_sc = np.broadcast_to(x_sc, self.y.shape)
        T = integrate_from_tip(self.w * x_sc + self.t0, self.y)
        for p in self.points:
            x_sc_p = float(np.interp(p.y, self.y, x_sc))
            T = T + (p.P * (x_sc_p - p.x) + p.couple) * (self.y < p.y)
        return T


class LoadModel:
    """Builds CaseLoads for any LoadCase (the WP4.1 tool)."""

    def __init__(self, ac: Aircraft, geom: WingGeometry, aero: WingAerodynamicsInterpolator, tank: FuelTank):
        self.ac, self.geom, self.aero, self.tank = ac, geom, aero, tank

    def grid(self, extra_eta: tuple[float, ...] = ()) -> np.ndarray:
        """Spanwise grid from the root to the tip, with the engine, gear, tank-end and any
        design breakpoints as nodes (so steps and point loads fall on grid points)."""
        p = self.ac.planform
        y = np.linspace(p.y_root, p.half_span, self.ac.numerics.n_stations)
        extra = [self.ac.engine.y_engine, self.tank.y_end] + [e * p.half_span for e in extra_eta]
        if self.ac.gear.include:
            extra.append(self.ac.gear.y)
        y = np.union1d(y, extra)
        return y[np.concatenate([[True], np.diff(y) > 1e-9])]   # drop near-duplicate nodes

    def wing_mass_per_span(self, y: np.ndarray) -> np.ndarray:
        """Wing structural mass per span, proportional to the local chord."""
        p = self.ac.planform
        c_int = 0.5 * (p.c_root + p.c_tip) * p.half_span       # int_0^{b/2} c dy
        return (self.ac.masses.m_wing_total / 2) * self.geom.chord(y) / c_int

    def build(self, case: LoadCase, y: np.ndarray) -> CaseLoads:
        ac, g, aero = self.ac, self.geom, self.aero
        c = g.chord(y)
        n, q = case.n, case.q
        M = case.mach if ac.aero.prandtl_glauert else 0.0
        alpha = float(aero.alpha_from_CL(case.CL, M=M))

        w_aero = aero.normal_force_per_unit_span(y, q, CL_d=case.CL, M=M)
        m_ac = aero.moment_per_unit_span(y, q, CL_d=case.CL, M=M)
        k_g = np.cos(np.radians(ac.planform.dihedral_deg)) if ac.loads.dihedral_on_inertia else 1.0
        w_wing = -n * G0 * k_g * self.wing_mass_per_span(y)
        w_fuel = -n * G0 * k_g * self.tank.mass_per_span(y, case.fuel_wing_half)

        x_ac = 0.25 * c
        x_w = ac.masses.x_wing_cg_frac * c
        x_f = self.tank.x_c_frac * c
        t0 = -(w_aero * x_ac + w_wing * x_w + w_fuel * x_f) + m_ac      # t = w x_sc + t0

        e, gr = ac.engine, ac.gear
        lam = np.radians(ac.planform.sweep_c4_deg)
        T = case.thrust
        points = [PointLoad("engine", e.y_engine, -n * G0 * k_g * e.m_engine,
                            g.x_from_LEMAC_to_local(e.x_cg_rel_LEMAC, e.y_engine),
                            couple=T * np.cos(lam) * e.z_thrust_below)]  # thrust below -> nose up
        if gr.include:
            points.append(PointLoad("main gear", gr.y, -n * G0 * k_g * gr.m_per_side,
                                    g.x_from_LEMAC_to_local(gr.x_rel_LEMAC, gr.y)))
        return CaseLoads(case=case, y=y, chord=c, alpha_deg=alpha, w_aero=w_aero, w_wing=w_wing,
                         w_fuel=w_fuel, m_ac=m_ac, t0=t0, points=tuple(points),
                         F_axial=T * np.sin(lam), y_engine=e.y_engine)
