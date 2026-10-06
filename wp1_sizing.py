"""
================================================================================
 AE2111-I  System Design - Design for Aircraft
 Work Package 1: Aircraft initial sizing
 Aircraft 2 - small passenger aircraft            Group A011

Produces:

     - the drag polar for all six flight configurations   (WP1.3)
     - the Class I weight estimation                      (WP1.2d)
     - the payload-range diagram                          (WP1.2d/e)
     - the ten-constraint matching diagram                (WP1.3a)
     - the design point and the resulting S, b, T_TO      (WP1.3b)

 Method reference: Roskam, "Airplane Design Part I - Preliminary Sizing of
 Airplanes"; Ruijgrok, "Elements of Airplane Performance"; and the ADSEE-I
 lecture notes.  Thrust lapse follows Mattingly, "Aircraft Engine Design".

================================================================================
"""

from __future__ import annotations

import argparse
import math
import os
from dataclasses import dataclass, field

import numpy as np

# ==============================================================================
#                                   INPUTS
# ==============================================================================


@dataclass
class Inputs:
    """Every design input.  Edit values here only."""

    # --------------------------------------------------------------------
    # 0.  Identification
    # --------------------------------------------------------------------
    name: str = "Aircraft 2 - small passenger aircraft"
    group: str = "A011"

    # --------------------------------------------------------------------
    # 1.  TOP-LEVEL REQUIREMENTS  
    # --------------------------------------------------------------------
    payload_max: float = 9302.0        # maximum structural payload        [kg]
    M_cruise: float = 0.77             # cruise Mach number                [-]
    h_cruise: float = 35000 * 0.3048   # cruise altitude  (35 000 ft)      [m]
    s_takeoff: float = 1296.0          # take-off field length, AEO, ISA SL[m]
    s_landing: float = 1210.0          # landing field length, ISA SL      [m]

    R_design: float = 2019e3           # design mission range     2019         [m]
    payload_design: float = 7200.0     # payload on the design mission     [kg]
    R_maxfuel: float = 2574e3          # range at MTOM and full fuel 2574      [m]
    payload_maxfuel: float = 6355.0    # payload at that point             [kg]
    R_ferry: float = 2963e3            # ferry range, zero payload     2963    [m]

    # --------------------------------------------------------------------
    # 2.  CABIN / PAYLOAD BREAKDOWN                                     
    # --------------------------------------------------------------------
    n_pax: int = 80                    # design-mission seats              [-]
    mass_per_pax: float = 90.0         # pax + baggage allowance           [kg]
    seats_abreast: int = 4             # cabin cross-section               [-]
    seat_pitch: float = 0.79           # seat pitch                        [m]
    d_fuselage: float = 2.90           # external fuselage diameter        [m]
    l_fuselage: float = 30.50          # fuselage length                   [m]

    # --------------------------------------------------------------------
    # 3.  CONFIGURATION
    # --------------------------------------------------------------------
    n_engines: int = 2                 # number of engines                 [-]
    engine_type: str = "jet"           # "jet" or "propeller"

    # --------------------------------------------------------------------
    # 4.  WING / AERODYNAMICS                                        
    # --------------------------------------------------------------------
    A: float = 10.5                    # aspect ratio                      [-]
    # S_wet/S:  "auto"   - component build-up, iterated with the wing area
    #           "manual" - use Swet_over_S below unchanged
    swet_mode: str = "auto"
    Swet_over_S: float = 6.3           # used if swet_mode == "manual"     [-]
    Cfe: float = 0.0030                # equivalent skin-friction coeff.   [-]
    phi: float = 0.0075                # parasite-drag parameter (Oswald)  [-]
    e_span: float = 0.95               # span efficiency factor            [-]

    d_flap_takeoff: float = 15.0       # take-off flap deflection        [deg]
    d_flap_landing: float = 35.0       # landing  flap deflection        [deg]

    # Maximum lift coefficients                                        
    CLmax_clean: float = 1.50
    CLmax_takeoff: float = 2.10
    CLmax_landing: float = 2.60

    # --------------------------------------------------------------------
    # 5.  PROPULSION                                                    
    # --------------------------------------------------------------------
    BPR: float = 9.0                   # by-pass ratio                     [-]
    theta_break: float = 1.07          # Mattingly throttle-break ratio    [-]
    e_fuel: float = 44e6               # specific energy, kerosene      [J/kg]

    # --------------------------------------------------------------------
    # 6.  MISSION / RESERVES                                            
    # --------------------------------------------------------------------
    f_contingency: float = 0.05        # contingency fuel fraction         [-]
    R_diversion: float = 370e3         # diversion range                   [m]
    t_loiter: float = 30 * 60.0        # loiter time                       [s]

    # Mass fractions used in the constraints                            
    f_takeoff: float = 1.00            # W/W_TO at take-off                [-]
    f_climb: float = 1.00              # W/W_TO for the climb-rate case    [-]
    f_landing: float = 0.92            # MLM/MTOM                          [-]
    f_approach: float = 0.92           # W/W_TO on approach                [-]
    # f_cruise is derived as 1 - 0.5*M_f (mid-cruise) unless overridden:
    f_cruise_override: float | None = None

    # --------------------------------------------------------------------
    # 7.  DERIVED PERFORMANCE REQUIREMENTS
    # --------------------------------------------------------------------
    V_approach: float = 64.0           # max approach speed  (REQ-APP-01) [m/s]
    h_approach: float = 0.0
    dT_approach: float = 0.0           # ISA temperature offset            [K]

    climb_rate: float = 15.0           # min rate of climb   (REQ-CLB-01) [m/s]
    h_climb: float = 0.0
    dT_climb: float = 0.0

    h_takeoff: float = 0.0             # airport altitude                  [m]
    dT_takeoff: float = 0.0
    h_landing: float = 0.0
    dT_landing: float = 0.0

    # --------------------------------------------------------------------
    # 8.  CS-25 CLIMB-GRADIENT CASES
    #     (label, gradient [%], n_operating_engines, mass fraction,
    #      flap setting, gear position, altitude [m], dT [K])
    #     flap: "clean" | "takeoff" | "landing"      gear: "up" | "down"
    # --------------------------------------------------------------------
    climb_gradients: tuple = (
        ("CS 25.119",    3.2, 0, 0.92, "landing", "down", 0.0, 0.0),
        ("CS 25.121(a)", 0.0, 1, 1.00, "takeoff", "down", 0.0, 0.0),
        ("CS 25.121(b)", 2.4, 1, 1.00, "takeoff", "up",   0.0, 0.0),
        ("CS 25.121(c)", 1.2, 1, 1.00, "clean",   "up",   0.0, 0.0),
        ("CS 25.121(d)", 2.1, 1, 0.92, "landing", "up",   0.0, 0.0),
    )
    # n_operating_engines = 0 means "all engines operating" (AEO)

    # --------------------------------------------------------------------
    # 9.  CLASS I MASS ESTIMATION
    #     "regression" - Roskam log-log OEM = a * MTOM**b from the database
    #                    (self-consistent: OEM/MTOM re-evaluated at the
    #                     converged MTOM)                        <- primary
    #     "fixed"      - flat fleet-average fraction, as the workbook does
    #     "payload"    - OEM = k * (maximum structural payload), k the fleet
    #                    mean.  ADOPTED: operating empty mass is driven by
    #                    cabin size, not by take-off mass, and this needs no
    #                    extrapolation below the lightest reference aircraft.
    # --------------------------------------------------------------------
    oem_method: str = "regression"
    oem_fraction_fixed: float = 0.5633   # used only if oem_method == "fixed"

    # --------------------------------------------------------------------
    # 10. DESIGN POINT  (set after inspecting the matching diagram)
    # --------------------------------------------------------------------
    design_WS: float = 4400.0          # wing loading   W_TO/S            [N/m2]
    design_TW: float = 0.345           # thrust loading T_TO/W_TO         [-]

    # --------------------------------------------------------------------
    # 11. PLOTTING
    # --------------------------------------------------------------------
    WS_max_plot: float = 6000.0        # x-axis upper limit              [N/m2]
    WS_step: float = 25.0              # x-axis resolution               [N/m2]
    TW_max_plot: float = 0.65          # y-axis upper limit                 [-]


def conservative_variant() -> "Inputs":
    i = Inputs()
    i.A, i.Cfe, i.BPR = 9.5, 0.0033, 12.0
    i.oem_method = "regression"
    i.design_WS, i.design_TW = 4500.0, 0.430
    return i

# ------------------------------------------------------------------------------
#  REFERENCE AIRCRAFT DATABASE  (WP1.2c) - 10 aircraft, 5 families
#  name, family, EIS, pax, max payload [kg], range [km], MTOM [kg], OEM [kg],
#  S [m2], b [m], total take-off thrust [kN], cruise Mach,
#  fuselage diameter [m], fuselage length [m]
# ------------------------------------------------------------------------------
REFERENCE_AIRCRAFT = [
    ("Embraer E170",      "Embraer E-Jet",  2004,  78,  9000, 3700, 36000, 21140,  72.72, 26.01, 126.0, 0.75, 3.01, 29.90),
    ("Embraer E175",      "Embraer E-Jet",  2005,  88, 10110, 3700, 37500, 21670,  72.72, 26.01, 126.0, 0.78, 3.01, 31.68),
    ("Bombardier CRJ700", "Bombardier CRJ", 2001,  78,  8530, 2650, 33000, 19730,  70.61, 23.24, 112.7, 0.78, 2.69, 32.51),
    ("Bombardier CRJ900", "Bombardier CRJ", 2003,  90, 10320, 2500, 36500, 21430,  71.10, 24.85, 127.0, 0.78, 2.69, 36.40),
    ("Fokker 70",         "Fokker",         1995,  85,  9265, 3410, 41730, 22673,  93.50, 28.08, 123.2, 0.77, 3.30, 30.91),
    ("Fokker 100",        "Fokker",         1988, 109, 11242, 3167, 45810, 24375,  93.50, 28.08, 134.4, 0.77, 3.30, 35.53),
    ("BAe 146-100",       "BAe 146",        1983,  82,  7600, 3000, 38100, 23300,  77.30, 26.34, 124.0, 0.65, 3.56, 26.16),
    ("BAe 146-200",       "BAe 146",        1983, 100, 11830, 3330, 42184, 23880,  77.30, 26.34, 124.0, 0.65, 3.56, 28.55),
]


def reference_swet_ratio(row) -> float:
    """S_wet/S of a reference aircraft, from the same component build-up."""
    _n, _f, _e, _p, _pl, _r, _m, _o, S, b, T, _M, d, l = row
    return wetted_area(S, b, d, l, T / 2.0, 2)["total"] / S

# ==============================================================================
#                              END OF INPUTS
# ==============================================================================

G0 = 9.80665          # standard gravity                                 [m/s2]
R_AIR = 287.0         # specific gas constant of air (workbook value) [J/kg/K]
GAMMA = 1.4
T0_ISA, P0_ISA, RHO0_ISA = 288.15, 101325.0, 1.225
LAPSE = -0.0065       # tropospheric temperature gradient                [K/m]
H_TROPOPAUSE = 11000.0


# ------------------------------------------------------------------------------
#  International Standard Atmosphere
# ------------------------------------------------------------------------------
def isa(h: float, dT: float = 0.0):
    """Return (T, p, rho, a) at geopotential altitude h with ISA offset dT."""
    if h <= H_TROPOPAUSE:
        T_isa = T0_ISA + LAPSE * h
        p = P0_ISA * (T_isa / T0_ISA) ** (-G0 / (LAPSE * R_AIR))
    else:
        T_isa = T0_ISA + LAPSE * H_TROPOPAUSE
        p11 = P0_ISA * (T_isa / T0_ISA) ** (-G0 / (LAPSE * R_AIR))
        p = p11 * math.exp(-G0 * (h - H_TROPOPAUSE) / (R_AIR * T_isa))
    T = T_isa + dT
    rho = p / (R_AIR * T)
    a = math.sqrt(GAMMA * R_AIR * T)
    return T, p, rho, a


# ------------------------------------------------------------------------------
#  Wetted area - component build-up  (Roskam Part I / Torenbeek App. B)
# ------------------------------------------------------------------------------
def wetted_area(S: float, b: float, d_fus: float, l_fus: float,
                T_engine_kN: float, n_engines: int,
                Sh_over_S: float = 0.25, Sv_over_S: float = 0.18,
                taper: float = 0.25) -> dict:
    """Component wetted areas [m2].  Same formula for the reference fleet and
    for the design, so the ratio S_wet/S is internally consistent."""
    c_root = 2.0 * S / (b * (1.0 + taper))
    S_exposed = S - d_fus * c_root
    parts = {
        "fuselage": 0.85 * math.pi * d_fus * l_fus,      # 0.85 for nose/tail taper
        "wing": 2.07 * S_exposed,                        # 2 x (1 + 0.035 t/c)
        "tail": 2.10 * (Sh_over_S + Sv_over_S) * S,
        "nacelles": n_engines * 2.30 * math.sqrt(T_engine_kN),
    }
    parts["total"] = sum(parts.values())
    return parts


# ------------------------------------------------------------------------------
#  Drag polar  (ADSEE-I / Roskam class I)
# ------------------------------------------------------------------------------
class DragPolar:
    """Zero-lift drag coefficient and Oswald factor per flight configuration."""

    def __init__(self, inp: Inputs, Swet_over_S: float | None = None):
        self.inp = inp
        self.Swet_over_S = (Swet_over_S if Swet_over_S is not None
                            else inp.Swet_over_S)
        self.CD0_clean = inp.Cfe * self.Swet_over_S
        self.e_clean = 1.0 / (math.pi * inp.A * inp.phi + 1.0 / inp.e_span)
        self.LD_max = 0.5 * math.sqrt(math.pi * inp.A * self.e_clean / self.CD0_clean)
        self.CL_LDmax = math.sqrt(math.pi * inp.A * self.e_clean * self.CD0_clean)

    def get(self, flap: str, gear: str):
        """(CD0, e) for flap in {clean, takeoff, landing}, gear in {up, down}."""
        i = self.inp
        d = {"clean": 0.0, "takeoff": i.d_flap_takeoff, "landing": i.d_flap_landing}[flap]
        CD0 = self.CD0_clean + 0.0013 * d + (0.02 if gear == "down" else 0.0)
        e = self.e_clean + 0.0026 * d
        return CD0, e

    def table(self):
        rows = []
        for flap in ("clean", "takeoff", "landing"):
            for gear in ("up", "down"):
                CD0, e = self.get(flap, gear)
                rows.append((flap, gear, CD0, e))
        return rows


# ------------------------------------------------------------------------------
#  Engine thrust lapse  (Mattingly, high-BPR turbofan)
# ------------------------------------------------------------------------------
def thrust_lapse(V: float | np.ndarray, h: float, dT: float, inp: Inputs):
    """alpha_T = T_available(h, M) / T_TO,static  for a high-bypass turbofan."""
    T, p, _, a = isa(h, dT)
    M = np.asarray(V, dtype=float) / a
    ratio = 1.0 + 0.2 * M ** 2
    theta_t = (T / T0_ISA) * ratio
    delta_t = (p / P0_ISA) * ratio ** 3.5
    k = 0.43 + 0.014 * inp.BPR
    alpha = delta_t * (1.0 - k * np.sqrt(M))
    hot = theta_t > inp.theta_break
    alpha = np.where(
        hot,
        delta_t * (1.0 - k * np.sqrt(M) - 3.0 * (theta_t - inp.theta_break) / (1.5 + M)),
        alpha,
    )
    return alpha


# ------------------------------------------------------------------------------
#  Class I weight estimation
# ------------------------------------------------------------------------------
def oem_regression(db=REFERENCE_AIRCRAFT):
    """Roskam log-log fit  OEM = 10**a * MTOM**b  over the reference database."""
    x = np.log10([r[6] for r in db])       # log MTOM
    y = np.log10([r[7] for r in db])       # log OEM
    b, a = np.polyfit(x, y, 1)
    r = np.corrcoef(x, y)[0, 1]
    return 10.0 ** a, b, r ** 2


@dataclass
class MassResult:
    R_design: float
    payload: float
    R_eq: float
    M_f: float
    MTOM: float
    OEM: float
    oem_fraction: float
    label: str = ""


class ClassI:
    """Equivalent-range Breguet mass estimation (ADSEE-I / Roskam class I)."""

    def __init__(self, inp: Inputs, polar: DragPolar):
        self.inp, self.polar = inp, polar
        _, _, self.rho_cr, self.a_cr = isa(inp.h_cruise)
        self.V_cr = inp.M_cruise * self.a_cr
        # overall propulsive+thermal efficiency of a turbofan (ADSEE-I 5.4)
        self.eta_j = self.V_cr / (22.0 * inp.BPR ** -0.19 * (inp.e_fuel / 1e6))
        self.LD = polar.LD_max
        # range parameter  H = eta * (L/D) * e_f / g            [m]
        self.H = self.eta_j * self.LD * inp.e_fuel / G0
        self.R_lost = (1.0 / 0.7) * self.LD * (
            inp.h_cruise + self.V_cr ** 2 / (2.0 * G0)
        )
        self.a_reg, self.b_reg, self.r2_reg = oem_regression()

    # ---- range <-> fuel-fraction ------------------------------------------
    def R_equivalent(self, R: float) -> float:
        i = self.inp
        return ((R + self.R_lost) * (1.0 + i.f_contingency)
                + 1.2 * i.R_diversion + i.t_loiter * self.V_cr)

    def fuel_fraction(self, R: float) -> float:
        return 1.0 - math.exp(-self.R_equivalent(R) / self.H)

    def range_from_masses(self, m_start: float, m_end: float) -> float:
        """Exact inversion of the equivalent-range relation for a mass ratio.

        R_eq = (R + R_lost)(1 + f_con) + 1.2 R_div + t_loiter V  and
        R_eq = H ln(m_start/m_end)   ->  solve for the still-air range R.
        """
        i = self.inp
        R_eq = self.H * math.log(m_start / m_end)
        return ((R_eq - 1.2 * i.R_diversion - i.t_loiter * self.V_cr)
                / (1.0 + i.f_contingency)) - self.R_lost

    def fuel_for_range(self, R: float, m_end: float) -> float:
        """Fuel mass needed to fly range R ending at mass m_end."""
        return m_end * (math.exp(self.R_equivalent(R) / self.H) - 1.0)

    def oem_fraction(self, MTOM: float) -> float:
        if self.inp.oem_method == "fixed":
            return self.inp.oem_fraction_fixed
        if self.inp.oem_method == "payload":
            return self.k_payload * self.inp.payload_max / MTOM
        return self.a_reg * MTOM ** (self.b_reg - 1.0)

    @property
    def k_payload(self) -> float:
        """Fleet-mean ratio of operating empty mass to maximum payload."""
        return float(np.mean([r[7] / r[4] for r in REFERENCE_AIRCRAFT]))

    # ---- the mass loop ----------------------------------------------------
    def size(self, R: float, payload: float, label: str = "") -> MassResult:
        M_f = self.fuel_fraction(R)
        MTOM = 30000.0
        for _ in range(200):
            frac = self.oem_fraction(MTOM)
            denom = 1.0 - M_f - frac
            if denom <= 0.0:
                return MassResult(R, payload, self.R_equivalent(R), M_f,
                                  float("inf"), float("inf"), frac, label)
            new = payload / denom
            if abs(new - MTOM) < 1e-6:
                MTOM = new
                break
            MTOM += 0.5 * (new - MTOM)          # damped fixed point
        frac = self.oem_fraction(MTOM)
        return MassResult(R, payload, self.R_equivalent(R), M_f,
                          MTOM, frac * MTOM, frac, label)

    def size_harmonic(self, payload_max: float) -> MassResult:
        """Smallest MTOM that can lift the maximum structural payload with
        reserves only (i.e. the harmonic point at zero mission range)."""
        M_f = self.fuel_fraction(0.0)
        MTOM = 30000.0
        for _ in range(200):
            frac = self.oem_fraction(MTOM)
            new = payload_max / (1.0 - M_f - frac)
            if abs(new - MTOM) < 1e-6:
                MTOM = new
                break
            MTOM += 0.5 * (new - MTOM)
        frac = self.oem_fraction(MTOM)
        return MassResult(0.0, payload_max, self.R_equivalent(0.0), M_f,
                          MTOM, frac * MTOM, frac, "Harmonic (max payload)")


# ------------------------------------------------------------------------------
#  Matching-diagram constraints
# ------------------------------------------------------------------------------
class Constraints:
    def __init__(self, inp: Inputs, polar: DragPolar, mass: ClassI, M_f: float):
        self.inp, self.polar, self.mass = inp, polar, mass
        self.f_cruise = (inp.f_cruise_override if inp.f_cruise_override
                         else 1.0 - 0.5 * M_f)

    # ---- 1. minimum (approach) speed  -> vertical W/S limit ---------------
    def wing_loading_minimum_speed(self) -> float:
        i = self.inp
        _, _, rho, _ = isa(i.h_approach, i.dT_approach)
        return (1.0 / i.f_approach) * 0.5 * rho * (i.V_approach / 1.23) ** 2 * i.CLmax_landing

    # ---- 2. landing field length     -> vertical W/S limit ---------------
    def wing_loading_landing(self) -> float:
        i = self.inp
        _, _, rho, _ = isa(i.h_landing, i.dT_landing)
        return (1.0 / i.f_landing) * (rho / 2.0) * (i.s_landing / 0.45) * i.CLmax_landing

    # ---- 3. cruise speed --------------------------------------------------
    def cruise(self, WS: np.ndarray) -> np.ndarray:
        i = self.inp
        _, _, rho, a = isa(i.h_cruise)
        V = i.M_cruise * a
        q = 0.5 * rho * V ** 2
        alpha = float(thrust_lapse(V, i.h_cruise, 0.0, i))
        CD0, e = self.polar.get("clean", "up")
        WSc = WS * self.f_cruise
        with np.errstate(divide="ignore", invalid="ignore"):
            tw = (self.f_cruise / alpha) * (
                CD0 * q / WSc + WSc / (q * math.pi * i.A * e)
            )
        self.alpha_cruise, self.q_cruise, self.V_cruise = alpha, q, V
        return tw

    # ---- 4. rate of climb -------------------------------------------------
    def climb_rate(self, WS: np.ndarray) -> np.ndarray:
        i = self.inp
        _, _, rho, _ = isa(i.h_climb, i.dT_climb)
        CD0, e = self.polar.get("clean", "up")
        CL = math.sqrt(math.pi * i.A * e * CD0)          # CL for (L/D)max
        with np.errstate(divide="ignore", invalid="ignore"):
            V = np.sqrt(WS * i.f_climb * 2.0 / rho / CL)
            alpha = thrust_lapse(V, i.h_climb, i.dT_climb, i)
            tw = (i.f_climb / alpha) * (
                i.climb_rate / V + 2.0 * math.sqrt(CD0 / (math.pi * i.A * e))
            )
        return tw

    # ---- 5..9  CS-25 climb gradients -------------------------------------
    def climb_gradient(self, WS: np.ndarray, case) -> np.ndarray:
        i = self.inp
        label, grad, n_op, f, flap, gear, h, dT = case
        n_op = i.n_engines if n_op == 0 else n_op
        _, _, rho, _ = isa(h, dT)
        CD0, e = self.polar.get(flap, gear)
        CL = math.sqrt(e * math.pi * i.A * CD0)
        with np.errstate(divide="ignore", invalid="ignore"):
            V = np.sqrt(WS * f * 2.0 / rho / CL)
            alpha = thrust_lapse(V, h, dT, i)
            tw = (i.n_engines / n_op) * (f / alpha) * (
                grad / 100.0 + 2.0 * math.sqrt(CD0 / (math.pi * i.A * e))
            )
        return tw

    # ---- 10. take-off field length ---------------------------------------
    def takeoff(self, WS: np.ndarray) -> np.ndarray:
        i = self.inp
        T, p, rho, _ = isa(i.h_takeoff, i.dT_takeoff)
        CD0_to, e_to = self.polar.get("takeoff", "up")
        CL2 = i.CLmax_takeoff / 1.13 ** 2
        with np.errstate(divide="ignore", invalid="ignore"):
            V = np.sqrt(WS * 2.0 / rho / CL2)
            alpha = thrust_lapse(V, i.h_takeoff, i.dT_takeoff, i)
            tw = (1.0 / alpha) * (
                1.15 * np.sqrt(WS / (i.s_takeoff * 0.85 * rho * G0 * math.pi * i.A * e_to))
                + 4.0 * 11.0 / i.s_takeoff
            )
        return tw

    # ---- everything at once ----------------------------------------------
    def evaluate(self, WS: np.ndarray) -> dict:
        out = {
            "Minimum speed": self.wing_loading_minimum_speed(),
            "Landing field length": self.wing_loading_landing(),
            "Cruise speed": self.cruise(WS),
            "Climb rate": self.climb_rate(WS),
        }
        for case in self.inp.climb_gradients:
            out[case[0]] = self.climb_gradient(WS, case)
        out["Take-off field length"] = self.takeoff(WS)
        return out


# ------------------------------------------------------------------------------
#  Driver
# ------------------------------------------------------------------------------
def run(inp: Inputs, Swet_over_S: float | None = None, _outer: bool = True):
    """One pass of the sizing chain.  With swet_mode == 'auto' the caller
    (`run_converged`) iterates S_wet/S against the wing area that comes out."""
    polar = DragPolar(inp, Swet_over_S)
    mass = ClassI(inp, polar)

    # ---- Step 1: which mission demands the largest MTOM? ------------------
    missions = [
        mass.size(inp.R_design, inp.payload_design, "Design mission"),
        mass.size(inp.R_maxfuel, inp.payload_maxfuel, "MTOM and full fuel"),
        mass.size_harmonic(inp.payload_max),
    ]
    critical = max(missions, key=lambda m: m.MTOM)
    MTOM, OEM = critical.MTOM, critical.OEM

    # ---- Step 2: the fuel *capacity* is sized by a different mission ------
    # Each range requirement implies a usable-fuel mass; the tank must hold
    # the largest of them.
    # The design mission and the maximum-fuel mission both take off at MTOM,
    # so their fuel is M_f(R) * MTOM.  The ferry mission takes off at
    # OEM + fuel, so its fuel is found from the end mass instead.
    fuel_cases = [
        ("Design mission", MTOM * mass.fuel_fraction(inp.R_design)),
        ("MTOM and full fuel", MTOM * mass.fuel_fraction(inp.R_maxfuel)),
        ("Ferry", mass.fuel_for_range(inp.R_ferry, OEM)),
    ]
    fuel_max = max(f for _, f in fuel_cases)
    fuel_case = max(fuel_cases, key=lambda t: t[1])[0]
    M_f_tank = fuel_max / MTOM

    # ---- Step 3: constraints, using the tank fuel fraction for mid-cruise --
    con = Constraints(inp, polar, mass, M_f_tank)
    WS = np.arange(0.0, inp.WS_max_plot + inp.WS_step, inp.WS_step)
    curves = con.evaluate(WS)

    # ---- Step 4: payload-range envelope -----------------------------------
    R_harmonic = mass.range_from_masses(MTOM, OEM + inp.payload_max)
    payload_B = MTOM - OEM - fuel_max
    R_B = mass.range_from_masses(MTOM, MTOM - fuel_max)
    R_C = mass.range_from_masses(OEM + fuel_max, OEM)

    def range_at_payload(pl: float) -> float:
        """Range available at a given payload, on whichever segment applies."""
        if pl >= payload_B:                       # segment A-B: MTOM limited
            return mass.range_from_masses(MTOM, OEM + pl)
        return mass.range_from_masses(OEM + fuel_max + pl, OEM + pl)  # B-C

    checks = [
        ("REQ-RAN-01 design mission", inp.R_design, inp.payload_design,
         range_at_payload(inp.payload_design)),
        ("REQ-RAN-02 MTOM + full fuel", inp.R_maxfuel, inp.payload_maxfuel,
         range_at_payload(inp.payload_maxfuel)),
        ("REQ-RAN-03 ferry", inp.R_ferry, 0.0, R_C),
    ]

    # ---- Step 5: design point --------------------------------------------
    S = MTOM * G0 / inp.design_WS
    b = math.sqrt(S * inp.A)
    T_TO = inp.design_TW * MTOM * G0

    swet = wetted_area(S, b, inp.d_fuselage, inp.l_fuselage,
                       T_TO / 1e3 / inp.n_engines, inp.n_engines)

    return dict(inp=inp, polar=polar, mass=mass, con=con, WS=WS, curves=curves,
                missions=missions, critical=critical, MTOM=MTOM, OEM=OEM,
                M_f=M_f_tank, fuel_max=fuel_max, fuel_cases=fuel_cases,
                fuel_case=fuel_case, R_harmonic=R_harmonic, R_B=R_B,
                payload_B=payload_B, R_C=R_C, checks=checks, S=S, b=b, T_TO=T_TO,
                swet=swet, Swet_over_S=polar.Swet_over_S)


def run_converged(inp: Inputs, verbose: bool = False):
    """Outer loop: S_wet/S depends on the wing area, which depends on MTOM,
    which depends on the drag polar built from S_wet/S.  Iterate to a fixed
    point.  With swet_mode == 'manual' this returns after a single pass."""
    if inp.swet_mode != "auto":
        return run(inp), []
    ratio, history = inp.Swet_over_S, []
    res = None
    for it in range(60):
        res = run(inp, Swet_over_S=ratio)
        new = res["swet"]["total"] / res["S"]
        history.append((it + 1, ratio, res["S"], res["MTOM"], new))
        if abs(new - ratio) < 1e-6:
            ratio = new
            break
        ratio += 0.5 * (new - ratio)          # damped, always converges here
    res = run(inp, Swet_over_S=ratio)
    if verbose:
        for it, r, S, M, n in history:
            print(f"   iter {it:2d}  Swet/S in {r:6.3f}  ->  S {S:6.2f} m2, "
                  f"MTOM {M:8,.0f} kg,  Swet/S out {n:6.3f}")
    return res, history


# ------------------------------------------------------------------------------
#  Reporting
# ------------------------------------------------------------------------------
def report(res: dict):
    inp, polar, mass, con = res["inp"], res["polar"], res["mass"], res["con"]
    WS, curves = res["WS"], res["curves"]

    def hdr(t):
        print("\n" + "=" * 78 + f"\n {t}\n" + "=" * 78)

    hdr(f"AE2111-I WP1 - {inp.name}  (group {inp.group})")

    hdr("1. Reference aircraft database (WP1.2c)")
    print(f"{'Aircraft':<20}{'EIS':>6}{'MTOM':>9}{'OEM':>9}{'OEM/MTOM':>10}"
          f"{'A':>7}{'W/S':>9}{'T/W':>7}{'Swet/S':>8}")
    print(f"{'':<20}{'':>6}{'[kg]':>9}{'[kg]':>9}{'[-]':>10}{'[-]':>7}"
          f"{'[N/m2]':>9}{'[-]':>7}{'[-]':>8}")
    ar, ws, tw, of, sw = [], [], [], [], []
    for row in REFERENCE_AIRCRAFT:
        n, fam, eis, pax, pl, rng, mtom, oem, S, bb, T, Mc, dfus, lfus = row
        A_i, ws_i = bb ** 2 / S, mtom * G0 / S
        tw_i, of_i = T * 1e3 / (mtom * G0), oem / mtom
        sw_i = reference_swet_ratio(row)
        ar.append(A_i); ws.append(ws_i); tw.append(tw_i); of.append(of_i)
        sw.append(sw_i)
        print(f"{n:<20}{eis:>6}{mtom:>9,.0f}{oem:>9,.0f}{of_i:>10.3f}"
              f"{A_i:>7.2f}{ws_i:>9,.0f}{tw_i:>7.3f}{sw_i:>8.2f}")
    print("-" * 78)
    print(f"{'mean':<20}{'':>6}{np.mean([r[6] for r in REFERENCE_AIRCRAFT]):>9,.0f}"
          f"{np.mean([r[7] for r in REFERENCE_AIRCRAFT]):>9,.0f}"
          f"{np.mean(of):>10.3f}{np.mean(ar):>7.2f}{np.mean(ws):>9,.0f}"
          f"{np.mean(tw):>7.3f}{np.mean(sw):>8.2f}")
    print(f"{'min':<20}{'':>6}{'':>9}{'':>9}{min(of):>10.3f}{min(ar):>7.2f}"
          f"{min(ws):>9,.0f}{min(tw):>7.3f}{min(sw):>8.2f}")
    print(f"{'max':<20}{'':>6}{'':>9}{'':>9}{max(of):>10.3f}{max(ar):>7.2f}"
          f"{max(ws):>9,.0f}{max(tw):>7.3f}{max(sw):>8.2f}")
    print(f"\nRoskam log-log fit:  OEM = {mass.a_reg:.4f} * MTOM^{mass.b_reg:.4f}"
          f"   (R^2 = {mass.r2_reg:.4f})")

    hdr("2. Drag polar (WP1.3 / ADSEE 5.1-5.3, 7.7)")
    print(f"  aspect ratio A                 = {inp.A:.2f}")
    print(f"  S_wet/S                        = {res['Swet_over_S']:.3f}"
          f"   ({inp.swet_mode})")
    for k in ("fuselage", "wing", "tail", "nacelles", "total"):
        print(f"    S_wet {k:<24}= {res['swet'][k]:8.1f} m2")
    print(f"  C_fe                           = {inp.Cfe:.4f}")
    print(f"  C_D0 (clean)                   = {polar.CD0_clean:.5f}")
    print(f"  Oswald factor e (clean)        = {polar.e_clean:.4f}")
    print(f"  (L/D)_max                      = {polar.LD_max:.2f}")
    print(f"  C_L at (L/D)_max               = {polar.CL_LDmax:.4f}")
    print(f"\n  {'configuration':<22}{'C_D0':>10}{'e':>10}")
    for flap, gear, CD0, e in polar.table():
        print(f"  {flap + ', gear ' + gear:<22}{CD0:>10.5f}{e:>10.4f}")

    hdr("3. Class I weight estimation (WP1.2d)")
    print(f"  cruise altitude                = {inp.h_cruise:,.0f} m "
          f"({inp.h_cruise / 0.3048:,.0f} ft)")
    print(f"  cruise TAS V_cr                = {mass.V_cr:.2f} m/s  (M {inp.M_cruise})")
    print(f"  cruise density                 = {mass.rho_cr:.5f} kg/m3")
    print(f"  by-pass ratio                  = {inp.BPR:.1f}")
    print(f"  overall efficiency eta_j       = {mass.eta_j:.4f}")
    print(f"  range parameter H = eta*L/D*e_f/g = {mass.H / 1e3:,.0f} km")
    print(f"  lost range R_lost              = {mass.R_lost / 1e3:,.1f} km")
    print(f"\n  {'mission':<24}{'R [km]':>9}{'payload':>9}{'R_eq [km]':>11}"
          f"{'M_f':>8}{'OEM/MTOM':>10}{'MTOM [kg]':>12}")
    for m in res["missions"]:
        print(f"  {m.label:<24}{m.R_design / 1e3:>9,.0f}{m.payload:>9,.0f}"
              f"{m.R_eq / 1e3:>11,.0f}{m.M_f:>8.4f}{m.oem_fraction:>10.4f}{m.MTOM:>12,.0f}")
    print(f"\n  CRITICAL MISSION PROFILE:  {res['critical'].label}")
    print(f"  MTOM = {res['MTOM']:,.0f} kg    OEM = {res['OEM']:,.0f} kg"
          f"    OEM/MTOM = {res['critical'].oem_fraction:.4f}")
    print(f"\n  fuel capacity sizing")
    for lbl, f in res["fuel_cases"]:
        print(f"    {lbl:<24}{f:>9,.0f} kg" + ("   <- sizes the tank"
                                               if lbl == res["fuel_case"] else ""))
    print(f"    usable fuel capacity  = {res['fuel_max']:,.0f} kg"
          f"  ({res['M_f']:.4f} of MTOM, {res['fuel_max']/0.80/1e3:.1f} m3 at 0.80 kg/l)")

    hdr("3b. Sensitivity of the mass loop to the empty-mass model")

    import copy
    print(f"  {'OEM model':<42}{'MTOM [kg]':>11}{'OEM [kg]':>10}"
          f"{'Swet/S':>8}{'cruise T/W':>12}{'critical':>24}")
    for meth, desc in (("regression", "Roskam log-log OEM = a*MTOM^b  (primary)"),
                       ("fixed", f"flat fleet mean OEM/MTOM = {inp.oem_fraction_fixed:.4f}"),
                       ("payload", "OEM = k * max payload  (cross-check)")):
        j = copy.deepcopy(inp)
        j.oem_method = meth
        r2, _ = run_converged(j)
        cr2 = r2["critical"]
        k2 = int(np.argmin(np.abs(r2["WS"] - j.design_WS)))
        print(f"  {desc:<42}{cr2.MTOM:>11,.0f}{cr2.OEM:>10,.0f}"
              f"{r2['Swet_over_S']:>8.3f}{float(r2['curves']['Cruise speed'][k2]):>12.4f}"
              f"{cr2.label:>24}")
    kp = [r[7] / r[4] for r in REFERENCE_AIRCRAFT]
    of = [r[7] / r[6] for r in REFERENCE_AIRCRAFT]
    cov_kp = 100 * np.std(kp, ddof=1) / np.mean(kp)
    cov_of = 100 * np.std(of, ddof=1) / np.mean(of)
    print(f"\n  fleet mean OEM / max structural payload = {np.mean(kp):.3f}"
          f"   (coefficient of variation {cov_kp:.1f}%)")
    print(f"  fleet mean OEM / MTOM                  = {np.mean(of):.3f}"
          f"   (coefficient of variation {cov_of:.1f}%)")

    hdr("4. Payload-range diagram")
    print(f"  A  harmonic  : {res['R_harmonic'] / 1e3:>8,.0f} km at "
          f"{inp.payload_max:>7,.0f} kg  (max structural payload)")
    print(f"  B  MTOM+full : {res['R_B'] / 1e3:>8,.0f} km at "
          f"{res['payload_B']:>7,.0f} kg")
    print(f"  C  ferry     : {res['R_C'] / 1e3:>8,.0f} km at "
          f"{0:>7,.0f} kg")
    print(f"\n  {'requirement':<30}{'required':>22}{'achieved':>12}{'margin':>10}")
    for lbl, Rr, pl, Ra in res["checks"]:
        print(f"  {lbl:<30}{f'{Rr/1e3:,.0f} km @ {pl:,.0f} kg':>22}"
              f"{Ra/1e3:>9,.0f} km{100*(Ra/Rr-1):>9.1f}%")

    hdr("5. Matching diagram (WP1.3a)")
    ws_lim = min(curves["Minimum speed"], curves["Landing field length"])
    idx = int(np.argmin(np.abs(WS - inp.design_WS)))
    print(f"  {'constraint':<26}{'type':<12}{'value at design W/S':>22}")
    print(f"  {'Minimum speed':<26}{'W/S limit':<12}{curves['Minimum speed']:>16,.0f} N/m2")
    print(f"  {'Landing field length':<26}{'W/S limit':<12}{curves['Landing field length']:>16,.0f} N/m2")
    order = ["Cruise speed", "Climb rate"] + [c[0] for c in inp.climb_gradients] + \
            ["Take-off field length"]
    tw_at = {}
    for k in order:
        tw_at[k] = float(curves[k][idx])
        print(f"  {k:<26}{'T/W curve':<12}{tw_at[k]:>16.4f}")
    driving = max(tw_at, key=tw_at.get)
    print(f"\n  binding W/S limit        = {ws_lim:,.0f} N/m2 "
          f"({'minimum speed' if curves['Minimum speed'] < curves['Landing field length'] else 'landing field length'})")
    print(f"  driving T/W constraint   = {driving} ({tw_at[driving]:.4f}) at "
          f"W/S = {inp.design_WS:,.0f} N/m2")
    print(f"  second most demanding    = "
          f"{sorted(tw_at, key=tw_at.get)[-2]} ({sorted(tw_at.values())[-2]:.4f})")

    hdr("6. Design point and resulting geometry (WP1.3b)")
    print(f"  W_TO/S                         = {inp.design_WS:,.0f} N/m2"
          f"   (limit {ws_lim:,.0f}, margin {100*(ws_lim/inp.design_WS-1):.1f}%)")
    print(f"  T_TO/W_TO                      = {inp.design_TW:.4f}"
          f"   (required {tw_at[driving]:.4f}, margin {100*(inp.design_TW/tw_at[driving]-1):.1f}%)")
    print(f"  wing area S                    = {res['S']:.2f} m2")
    print(f"  wing span b                    = {res['b']:.2f} m")
    print(f"  total take-off thrust T_TO     = {res['T_TO']/1e3:.1f} kN")
    print(f"  thrust per engine              = {res['T_TO']/1e3/inp.n_engines:.1f} kN")
    print(f"  cruise C_L at design point     = "
          f"{inp.design_WS*con.f_cruise/con.q_cruise:.4f}")
    CLc = inp.design_WS * con.f_cruise / con.q_cruise
    CD0, e = polar.get("clean", "up")
    print(f"  cruise L/D at design point     = "
          f"{CLc/(CD0+CLc**2/(math.pi*inp.A*e)):.2f}   ((L/D)max = {polar.LD_max:.2f})")
    print(f"  cruise thrust lapse alpha      = {con.alpha_cruise:.5f}"
          f"   (Mattingly, BPR {inp.BPR:.0f})")
    for a_alt in (0.18, 0.20, 0.22):
        print(f"    cruise T/W if alpha were {a_alt:.2f}   = "
              f"{tw_at['Cruise speed'] * con.alpha_cruise / a_alt:.4f}")
    print(f"  mid-cruise mass fraction       = {con.f_cruise:.4f}")

    # --- is the stored design point still feasible? -----------------------
    need_tw = tw_at[driving]
    infeasible = (inp.design_TW < need_tw) or (inp.design_WS > ws_lim)
    if infeasible:
        print("\n" + "!" * 78)
        print(" WARNING: the design point in Inputs is NO LONGER FEASIBLE")
        print("!" * 78)
        if inp.design_TW < need_tw:
            print(f"   T/W = {inp.design_TW:.3f} is BELOW the {driving.lower()} "
                  f"constraint of {need_tw:.4f}")
        if inp.design_WS > ws_lim:
            print(f"   W/S = {inp.design_WS:,.0f} exceeds the limit of {ws_lim:,.0f} N/m2")
        print("   The design point is an INPUT; it does not move when you change an")
        print("   assumption.  Set these in Inputs and re-run:")
        print(f"       design_WS = {round(0.965 * ws_lim, -1):.0f}")
        print(f"       design_TW = {round(1.022 * need_tw, 3):.3f}")
        print("!" * 78)
    print()
    return tw_at, ws_lim


# ------------------------------------------------------------------------------
#  Figures
# ------------------------------------------------------------------------------
# categorical palette - validated for adjacent-pair CVD separation
C_MINSPEED = "#2a78d6"   # blue
C_LANDING = "#eb6834"    # orange
C_CRUISE = "#1baf7a"     # aqua
C_CLIMBRATE = "#eda100"  # yellow
C_TAKEOFF = "#e87ba4"    # magenta
C_GRADIENT = "#008300"   # green  (all five CS-25 gradients, dashed variants)
C_INK = "#0b0b0b"
C_INK2 = "#52514e"
C_GRID = "#d9d8d3"
C_FEASIBLE = "#2a78d6"


def figures(res: dict, outdir: str = ".") -> list:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    outdir = os.path.abspath(outdir)
    os.makedirs(outdir, exist_ok=True)
    written = []

    def save(fig, stem):
        for ext, kw in ((".pdf", {}), (".png", {"dpi": 220})):
            path = os.path.join(outdir, stem + ext)
            fig.savefig(path, bbox_inches="tight", **kw)
            written.append(path)

    inp, polar, mass = res["inp"], res["polar"], res["mass"]
    WS, curves = res["WS"], res["curves"]

    plt.rcParams.update({
        "font.size": 9, "axes.edgecolor": C_INK2, "axes.labelcolor": C_INK,
        "text.color": C_INK, "xtick.color": C_INK2, "ytick.color": C_INK2,
        "axes.linewidth": 0.8, "figure.dpi": 200,
        "font.family": "DejaVu Sans",
    })

    # ================= Figure 1: matching diagram =========================
    fig, ax = plt.subplots(figsize=(7.4, 5.4))
    ws_lim = min(curves["Minimum speed"], curves["Landing field length"])

    grad_styles = [(0, (6, 2)), (0, (2, 2)), (0, (6, 2, 1, 2)),
                   (0, (1, 1.6)), (0, (5, 1.5, 1, 1.5, 1, 1.5))]
    grad_names = [c[0] for c in inp.climb_gradients]

    # feasible region: above every T/W curve, left of every W/S limit
    tw_stack = np.vstack([curves[k] for k in
                          ["Cruise speed", "Climb rate", *grad_names,
                           "Take-off field length"]])
    tw_req = np.nanmax(tw_stack, axis=0)
    mask = WS <= ws_lim
    ax.fill_between(WS[mask], tw_req[mask], inp.TW_max_plot,
                    color=C_FEASIBLE, alpha=0.07, lw=0, zorder=0)
    ax.plot(WS[mask], tw_req[mask], color=C_FEASIBLE, lw=1.2, alpha=0.55,
            zorder=1)

    # constraints
    ax.axvline(curves["Minimum speed"], color=C_MINSPEED, lw=2.0, zorder=4)
    ax.axvline(curves["Landing field length"], color=C_LANDING, lw=2.0, zorder=4)
    ax.plot(WS, curves["Cruise speed"], color=C_CRUISE, lw=2.0, zorder=5)
    ax.plot(WS, curves["Climb rate"], color=C_CLIMBRATE, lw=2.0, zorder=5)
    ax.plot(WS, curves["Take-off field length"], color=C_TAKEOFF, lw=2.0, zorder=5)
    for name, st in zip(grad_names, grad_styles):
        ax.plot(WS, curves[name], color=C_GRADIENT, lw=1.4, ls=st, zorder=3)

    # reference aircraft
    for n, fam, eis, pax, pl, rng, mtom, oem, S, bb, T, Mc, dfus, lfus in REFERENCE_AIRCRAFT:
        ax.plot(mtom * G0 / S, T * 1e3 / (mtom * G0), "o", ms=5.5,
                mfc="white", mec=C_INK2, mew=1.1, zorder=6)

    # design point
    ax.plot(inp.design_WS, inp.design_TW, "*", ms=17, color="#e34948",
            mec="white", mew=0.9, zorder=8)
    ax.annotate(f"Design point\n{inp.design_WS:,.0f} N/m$^2$,  $T/W$ = {inp.design_TW:.3f}",
                (inp.design_WS, inp.design_TW),
                textcoords="offset points", xytext=(-26, 26),
                ha="right", fontsize=8.2, color=C_INK, zorder=11,
                arrowprops=dict(arrowstyle="-", color="#e34948", lw=0.8,
                                shrinkA=2, shrinkB=6),
                bbox=dict(boxstyle="round,pad=0.28", fc="white",
                          ec="#e34948", lw=0.8, alpha=0.96))

    # direct labels (relief for the low-contrast slots)
    def lab(x, y, txt, col, ha="left", va="center", dx=0, dy=0, rot=0, fs=7.6):
        ax.annotate(txt, (x, y), textcoords="offset points", xytext=(dx, dy),
                    ha=ha, va=va, fontsize=fs, color=col, rotation=rot,
                    zorder=10,
                    bbox=dict(boxstyle="round,pad=0.16", fc="white",
                              ec="none", alpha=0.85))

    lab(curves["Minimum speed"], inp.TW_max_plot * 0.015, "Minimum speed",
        C_MINSPEED, ha="left", dx=5, rot=90, va="bottom")
    lab(curves["Landing field length"], inp.TW_max_plot * 0.015,
        "Landing field length", C_LANDING, ha="right", dx=-4, rot=90, va="bottom")
    i_e = int(0.84 * len(WS))
    lab(WS[i_e], curves["Cruise speed"][i_e], "Cruise speed", C_CRUISE, dx=2, dy=10)
    lab(WS[i_e], curves["Climb rate"][i_e], "Climb rate", C_CLIMBRATE, dx=2, dy=-10)
    lab(WS[int(0.42 * len(WS))],
        float(curves["Take-off field length"][int(0.42 * len(WS))]),
        "Take-off field length", C_TAKEOFF, dx=2, dy=-11)
    # the five gradient curves share one hue: one direct label for the band
    band = [float(curves[n][-1]) for n in grad_names]
    lab(WS[-1], 0.5 * (min(band) + max(band)), "CS-25 climb\ngradients",
        C_GRADIENT, ha="left", dx=4, fs=7.4)
    lab(ws_lim * 0.93, inp.TW_max_plot * 0.925, "Feasible\ndesign space",
        C_FEASIBLE, ha="right", fs=8.2)

    handles = [
        Line2D([], [], color=C_MINSPEED, lw=2, label="Minimum speed ($W/S$ limit)"),
        Line2D([], [], color=C_LANDING, lw=2, label="Landing field length ($W/S$ limit)"),
        Line2D([], [], color=C_CRUISE, lw=2, label="Cruise speed"),
        Line2D([], [], color=C_CLIMBRATE, lw=2, label="Climb rate"),
        Line2D([], [], color=C_TAKEOFF, lw=2, label="Take-off field length"),
    ] + [Line2D([], [], color=C_GRADIENT, lw=1.4, ls=st, label=n)
         for n, st in zip(grad_names, grad_styles)] + [
        Line2D([], [], marker="o", ls="", ms=5.5, mfc="white", mec=C_INK2,
               mew=1.1, label="Reference aircraft"),
        Line2D([], [], marker="*", ls="", ms=12, color="#e34948",
               label="Design point"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.16),
              fontsize=7.6, frameon=False, ncol=3, handlelength=2.6,
              columnspacing=1.6, labelspacing=0.4)

    ax.set_xlabel(r"Wing loading  $W_{TO}/S$   [N/m$^2$]")
    ax.set_ylabel(r"Thrust loading  $T_{TO}/W_{TO}$   [-]")
    ax.set_xlim(0, inp.WS_max_plot)
    ax.set_ylim(0, inp.TW_max_plot)
    ax.grid(True, color=C_GRID, lw=0.6, alpha=0.9)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    save(fig, "matching_diagram")
    plt.close(fig)

    # ================= Figure 2: payload-range ============================
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    R = [0, res["R_harmonic"] / 1e3, res["R_B"] / 1e3, res["R_C"] / 1e3]
    P = [inp.payload_max, inp.payload_max, res["payload_B"], 0.0]
    ax.plot(R, P, "-o", color=C_MINSPEED, lw=2.0, ms=5.5, mfc="white",
            mec=C_MINSPEED, mew=1.6, zorder=4, label="Payload-range envelope")
    for x, y, t, off in zip(R[1:], P[1:], ["A", "B", "C"],
                            [(8, 4), (9, 4), (6, 8)]):
        ax.annotate(t, (x, y), textcoords="offset points", xytext=off,
                    fontsize=9, fontweight="bold", color=C_MINSPEED)
    ax.text(0.035, 0.085,
            "A  the maximum structural payload is reached with reserve fuel\n"
            "     only, so the harmonic range is $\\approx$ 0 km.  MTOM is sized\n"
            "     by this point - it is the critical mission profile.",
            transform=ax.transAxes, fontsize=7.2, color=C_INK2, va="bottom")

    reqs = [(inp.R_design / 1e3, inp.payload_design, "Design mission", (-8, 10), "right"),
            (inp.R_maxfuel / 1e3, inp.payload_maxfuel, "MTOM + full fuel", (10, -4), "left"),
            (inp.R_ferry / 1e3, 0.0, "Ferry", (0, 12), "center")]
    for x, y, t, off, ha in reqs:
        ax.plot(x, y, "X", ms=9, color="#e34948", mec="white", mew=0.8, zorder=5)
        ax.annotate(t, (x, y), textcoords="offset points", xytext=off,
                    ha=ha, fontsize=7.6, color="#e34948", zorder=6,
                    bbox=dict(boxstyle="round,pad=0.16", fc="white",
                              ec="none", alpha=0.85))
    ax.plot([], [], "X", ms=9, color="#e34948", label="Top-level requirement")

    ax.set_xlabel("Range  [km]")
    ax.set_ylabel("Payload  [kg]")
    ax.set_xlim(0, max(R + [r[0] for r in reqs]) * 1.12)
    ax.set_ylim(0, inp.payload_max * 1.20)
    ax.grid(True, color=C_GRID, lw=0.6, alpha=0.9)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(loc="upper right", fontsize=8, frameon=True, framealpha=0.94,
              edgecolor=C_GRID)
    fig.tight_layout()
    save(fig, "payload_range")
    plt.close(fig)

    # ================= Figure 3: OEM vs MTOM regression ===================
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    x = np.array([r[6] for r in REFERENCE_AIRCRAFT]) / 1e3
    y = np.array([r[7] for r in REFERENCE_AIRCRAFT]) / 1e3
    xs = np.linspace(min(x.min(), res["MTOM"] / 1e3) * 0.85, x.max() * 1.08, 200)
    ax.plot(xs, mass.a_reg * (xs * 1e3) ** mass.b_reg / 1e3, "-",
            color=C_INK2, lw=1.4, zorder=2,
            label=rf"$OEM = {mass.a_reg:.3f}\,MTOM^{{{mass.b_reg:.4f}}}$"
                  f"   ($R^2$ = {mass.r2_reg:.3f})")
    fams = {}
    cols = [C_MINSPEED, C_LANDING, C_CRUISE, C_CLIMBRATE]
    short = {"Embraer E170": ("E170", (-8, -13)), "Embraer E175": ("E175", (6, 6)),
             "Bombardier CRJ700": ("CRJ700", (-6, -14)),
             "Bombardier CRJ900": ("CRJ900", (7, -2)),
             "BAe 146-100": ("BAe 146", (8, -3)),
             "BAe 146-200": ("BAe 146", (-8, 7)),
             "Fokker 70": ("F70", (2, 8)), "Fokker 100": ("F100", (8, -3))}
    for (n, fam, *_rest), xi, yi in zip(REFERENCE_AIRCRAFT, x, y):
        if fam not in fams:
            fams[fam] = cols[len(fams) % len(cols)]
        ax.plot(xi, yi, "o", ms=7, color=fams[fam], mec="white", mew=1.0,
                zorder=4)
        lbl, off = short[n]
        ax.annotate(lbl, (xi, yi), textcoords="offset points", xytext=off,
                    fontsize=7, color=C_INK2, zorder=5)
    for fam, c in fams.items():
        ax.plot([], [], "o", ms=7, color=c, label=fam)
    ax.plot(res["MTOM"] / 1e3, res["OEM"] / 1e3, "*", ms=18, color="#e34948",
            mec="white", mew=0.9, zorder=6, label="Class I design point")
    ax.set_xlabel("Maximum take-off mass  [t]")
    ax.set_ylabel("Operating empty mass  [t]")
    ax.grid(True, color=C_GRID, lw=0.6, alpha=0.9)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(loc="upper left", fontsize=7.6, frameon=True, framealpha=0.94,
              edgecolor=C_GRID)
    fig.tight_layout()
    save(fig, "oem_mtom")
    plt.close(fig)

    return written


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--no-plot", action="store_true",
                    help="skip the figures, print numbers only")
    ap.add_argument("--outdir", default=here,
                    help="where to write the figures (default: next to this script)")
    ap.add_argument("--no-report-figs", action="store_true",
                    help="do not also refresh report/figures/")
    args = ap.parse_args()

    inp = Inputs()
    res, history = run_converged(inp)
    if history:
        print("\nS_wet/S outer iteration:")
        for it, r, S, M, n in history:
            print(f"   {it:2d}  in {r:6.3f}  ->  S {S:6.2f} m2, "
                  f"MTOM {M:8,.0f} kg,  out {n:6.3f}")
    report(res)
    if not args.no_plot:
        written = figures(res, args.outdir)
        report_figs = os.path.join(here, "report", "figures")
        if os.path.isdir(report_figs) and not args.no_report_figs \
                and os.path.abspath(args.outdir) != report_figs:
            written += figures(res, report_figs)
        print("figures written:")
        for path in written:
            print("   " + path)


if __name__ == "__main__":
    main()
