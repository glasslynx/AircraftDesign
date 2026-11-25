"""WP4.3.c: table of load cases = every V-n corner point for every altitude x weight.

The 1 g stall point is dominated by corner A (same C_L, higher n) and is discarded a priori;
flaps-down cases (n <= 2) are below the flaps-up n_max = 2.5 and are discarded as well.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from .atmosphere import RHO0, isa
from .config import G0, Aircraft
from .vn import VnDiagram, WeightConfig

STRUCTURAL_CORNERS = ("A", "D", "E", "F", "H")
CORNER_TEXT = {
    "A": "pos. manoeuvre at V_A",
    "D": "pos. manoeuvre at V_D",
    "E": "dive, n = 0 at V_D",
    "F": "neg. manoeuvre at V_C",
    "H": "neg. manoeuvre at V_H",
}


@dataclass(frozen=True)
class LoadCase:
    id: str
    description: str
    corner: str
    weight: str
    altitude: float        # [m]
    V_EAS: float           # [m/s]
    n: float               # limit load factor [-]
    mass: float            # aircraft mass [kg]
    fuel_total: float      # fuel on board [kg]
    fuel_wing_half: float  # fuel in ONE half wing [kg]
    fuel_fuselage: float   # fuel that did not fit in the wings [kg]
    q: float               # dynamic pressure 0.5 rho0 V_EAS^2 [Pa]
    mach: float            # [-]
    CL: float              # wing C_L = n W / (q S) [-]
    thrust: float          # per engine [N]

    def as_row(self) -> dict:
        return asdict(self)


def thrust_per_engine(ac: Aircraft, altitude: float) -> float:
    e = ac.engine
    if e.thrust_mode == "zero":
        return 0.0
    return e.T0_per_engine * isa(altitude).sigma ** e.thrust_lapse_exp


def make_case(ac: Aircraft, tank, wc: WeightConfig, altitude: float, V: float, n: float,
              corner: str = "X", case_id: str | None = None) -> LoadCase:
    st = isa(altitude)
    q = 0.5 * RHO0 * V**2
    m_half, m_fus = tank.split(wc.fuel)
    CL = n * wc.mass * G0 / (q * ac.planform.S) if q > 0 else 0.0
    return LoadCase(
        id=case_id or f"{corner}-{wc.name}-{altitude / 1000:.1f}km",
        description=CORNER_TEXT.get(corner, "user-defined"),
        corner=corner, weight=wc.name, altitude=altitude, V_EAS=V, n=n,
        mass=wc.mass, fuel_total=wc.fuel, fuel_wing_half=m_half, fuel_fuselage=m_fus,
        q=q, mach=V / math.sqrt(st.sigma) / st.a, CL=CL, thrust=thrust_per_engine(ac, altitude),
    )


def build_load_cases(ac: Aircraft, tank, diagrams: list[VnDiagram]) -> list[LoadCase]:
    cases, k = [], 1
    for d in diagrams:
        pts = d.corner_points()
        for c in STRUCTURAL_CORNERS:
            V, n = pts[c]
            cases.append(make_case(ac, tank, d.wc, d.altitude, V, n, corner=c, case_id=f"LC-{k:02d}"))
            k += 1
    return cases
