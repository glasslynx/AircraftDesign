"""WP4.3: manoeuvre (V_EAS - n) diagrams, CS-25 as summarised in reader App. E.

(from V-n_diagrams.py; now reads aircraft.toml, no astropy, no settings .txt file)

All speeds are equivalent airspeeds [m/s]. One diagram per (altitude, weight configuration).
    n_max = 2.1 + 24000 / (W + 10000), W = MTOW in lb, clamped to [2.5, 3.8]  (CS 25.337(b))
    n_min = -1 up to V_C, linear to 0 at V_D
    V_S1 = sqrt(2 W / (rho0 S C_Lmax,clean)),  V_S0 with C_Lmax,landing
    V_A  = V_S1 sqrt(n_max)
    V_C  = design cruise speed (constant EAS, capped at M_C at altitude)
    V_D  = min(V_C / 0.8, (M_C + dM) a sqrt(sigma))   (CS 25.335(b); compressibility margin dM)
    V_H  = V_S1,neg sqrt(|n_min|)   with C_N,min = -C_Lmax (reader App. E)
    V_F  = max(1.6 V_S1(MTOW, TO flaps), 1.8 V_S1(MLW, approach ~ TO flaps), 1.8 V_S0(MLW, landing))
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .atmosphere import RHO0, isa
from .config import G0, Aircraft

LB_PER_KG = 1.0 / 0.45359237


def n_max_cs25(mtom_kg: float) -> float:
    n = 2.1 + 24000.0 / (mtom_kg * LB_PER_KG + 10000.0)
    return float(min(max(n, 2.5), 3.8))


def stall_speed(mass: float, S: float, CN: float) -> float:
    return math.sqrt(2.0 * mass * G0 / (S * RHO0 * abs(CN)))


@dataclass(frozen=True)
class WeightConfig:
    name: str            # short id used in load-case names
    label: str
    mass: float          # aircraft mass [kg]
    fuel: float          # total fuel on board [kg]
    payload: float       # [kg]


def weight_configs(ac: Aircraft) -> list[WeightConfig]:
    """The three configurations required by WP4.3 (reader p. 10)."""
    m = ac.masses
    fuel_mtow = m.MTOM - m.OEM - m.payload_max
    if fuel_mtow < 0:
        raise ValueError("OEM + MPW exceeds MTOM")
    return [
        WeightConfig("OEW", "OEW", m.OEM, 0.0, 0.0),
        WeightConfig("MTOW", "OEW + MPW + fuel = MTOW", m.MTOM, fuel_mtow, m.payload_max),
        WeightConfig("ZFW", "OEW + MPW (zero fuel)", m.OEM + m.payload_max, 0.0, m.payload_max),
    ]


@dataclass
class VnDiagram:
    ac: Aircraft
    altitude: float
    wc: WeightConfig
    VS1: float = field(init=False)
    VS1_neg: float = field(init=False)
    VS0: float = field(init=False)
    VA: float = field(init=False)
    VC: float = field(init=False)
    VD: float = field(init=False)
    VF: float = field(init=False)
    VH: float = field(init=False)
    n_max: float = field(init=False)
    n_min: float = field(init=False)

    def __post_init__(self):
        v, p, m = self.ac.vn, self.ac.planform, self.ac.masses
        st = isa(self.altitude)
        self.n_max = n_max_cs25(m.MTOM)
        self.n_min = -1.0
        self.VS1 = stall_speed(self.wc.mass, p.S, v.CL_max_clean)
        self.VS1_neg = stall_speed(self.wc.mass, p.S, v.CN_min)
        self.VS0 = stall_speed(self.wc.mass, p.S, v.CL_max_land)
        self.VC = min(v.V_C_EAS, v.M_C * st.a * math.sqrt(st.sigma))
        self.VD = min(v.VD_VC_ratio * self.VC, (v.M_C + v.dM_dive) * st.a * math.sqrt(st.sigma))
        self.VA = min(self.VS1 * math.sqrt(self.n_max), self.VD)
        self.VH = min(self.VS1_neg * math.sqrt(abs(self.n_min)), self.VC)
        mlw = m.MLM_fraction * m.MTOM
        self.VF = max(1.6 * stall_speed(m.MTOM, p.S, v.CL_max_TO),
                      1.8 * stall_speed(mlw, p.S, v.CL_max_TO),
                      1.8 * stall_speed(mlw, p.S, v.CL_max_land))

    @property
    def name(self) -> str:
        return f"{self.wc.name}@{self.altitude / 1000:.1f}km"

    def speeds(self) -> dict:
        return dict(diagram=self.name, weight=self.wc.name, mass_kg=self.wc.mass, altitude_m=self.altitude,
                    n_max=self.n_max, n_min=self.n_min, VS1=self.VS1, VS1_neg=self.VS1_neg, VS0=self.VS0,
                    VA=self.VA, VC=self.VC, VD=self.VD, VH=self.VH, VF=self.VF)

    def envelope(self, n_pts: int = 200):
        """Flaps-up envelope polyline (V, n) and flaps-down polyline."""
        V1 = np.linspace(0, self.VA, n_pts)
        up = np.column_stack([V1, np.minimum((V1 / self.VS1) ** 2, self.n_max)])
        top = np.array([[self.VA, self.n_max], [self.VD, self.n_max], [self.VD, 0.0], [self.VC, self.n_min]])
        V2 = np.linspace(self.VH, 0, n_pts)
        low = np.column_stack([V2, -(V2 / self.VS1_neg) ** 2])
        flaps_up = np.vstack([up, top, [[self.VH, self.n_min]], low])
        V_n2 = self.VS0 * math.sqrt(self.ac.vn.n_flaps_max)
        Vf = np.linspace(0, V_n2, n_pts)
        flaps = np.vstack([np.column_stack([Vf, (Vf / self.VS0) ** 2]),
                           [[max(self.VF, V_n2), self.ac.vn.n_flaps_max]]])
        return flaps_up, flaps

    def corner_points(self) -> dict[str, tuple[float, float]]:
        """Load-case candidates on the flaps-up envelope boundary (V_EAS, n)."""
        return {
            "A": (self.VA, self.n_max),     # max positive n at the lowest speed (highest CL)
            "D": (self.VD, self.n_max),     # max positive n at the highest q
            "E": (self.VD, 0.0),            # dive, zero lift: pitching-moment torque only
            "F": (self.VC, self.n_min),     # max negative n at the highest q
            "H": (self.VH, self.n_min),     # max negative n at the lowest speed
        }


def build_vn_diagrams(ac: Aircraft) -> list[VnDiagram]:
    return [VnDiagram(ac, h, wc) for h in ac.vn.altitudes_m for wc in weight_configs(ac)]
