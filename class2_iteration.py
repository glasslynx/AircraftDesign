"""
Class I <-> Class II iteration (ADSEE-I Lecture 5 / Vos): the Class II OEM replaces
the Class I OEM regression, and MTOM, wing area, drag, fuel and tank volume are
re-sized until the OEM changes by less than TOL.

One iteration:
  1. S = MTOM g / (W/S)                      (W/S fixed: 4,800 N/m^2, Akos 2026-10-14)
  2. geometry (wing, tails, nacelles, CG)    drag_geometry_inputs.py
  3. C_D0 component build-up + wave drag     drag_estimator.py
     -> mid-cruise L/D = C_L / (C_D0 + C_L^2 / (pi A e))
  4. Class II OEM (OEM_METHOD switch)       class2_weight_estimation.py
  5. Class I mission fuel (WP1 equivalent-range Breguet, CF34-8E5 TSFC, real L/D):
     MTOM = (OEM + payload) / (1 - M_f) for each WP1 mission, the largest wins
  6. fuel capacity = largest fuel load of the design, MTOM+full-fuel and ferry
     missions; wing tanks hold 5.49 (S/67.91)^1.5 m^3, the rest is the centre tank

All scripts must sit in the same folder as wp1_sizing.py (WP1 mission definitions).
Run:  python class2_iteration.py
"""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "..", "knowledge")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import drag_geometry_inputs as G  # noqa: E402
import numpy as np                 # noqa: E402
import wp1_sizing as W1           # noqa: E402

# ============================================================================
# INPUT BLOCK
# ============================================================================
OEM_METHOD = "Torenbeek"   # Class II method carried into the loop: "Torenbeek", "Roskam", "Raymer"
                           # (or "mean" of the three)
WS = 4800.0             # N/m^2, design wing loading (Akos 2026-10-14, ws_sweep_class2.py;
                        # was 4,202 from the WP2 report)
TW = 0.345              # design T/W (WP2)
TSFC = 0.68 * 2.8325e-5 # kg/(N s), CF34-8E5 cruise TSFC 0.68 lb/(lbf h)
OSWALD_E = 0.7623       # agreed WP2 cruise value
RHO_FUEL = 800.0        # kg/m^3
V_WING_REF, S_WING_REF = 5.49, 67.91   # m^3 wing-tank capacity at S_ref (WP2 integrated wing box)
# integral tanks in the wing box (front spar 0.20c to rear spar 0.70c, SC(2)-0612)
TANK_USABLE = 0.85      # usable fraction (structure, systems, unusable fuel; WP2 report)
TANK_ETA = (0.17, 0.83) # WP2 wing-tank span, fraction of b/2
AIRFOIL_FILE = os.path.join(HERE, "NASA SC2-0612 AIRFOIL.dat")   # same folder, else the WP2-final copy
if not os.path.isfile(AIRFOIL_FILE):
    AIRFOIL_FILE = os.path.join(HERE, "..", "wp2-final", "code", "NASA SC2-0612 AIRFOIL.dat")
MTOM_START = G.MTOM     # kg, WP3.1 value (30,845)
TOL = 0.001             # relative OEM change for convergence (Lecture 5: < 1 %)
MAX_IT = 30

INP = W1.Inputs()       # WP1 missions: design 2,019 km / 7,200 kg, 2,574 km / 6,355 kg,
                        # ferry 2,963 km, harmonic 9,302 kg; reserves and contingency
G0 = 9.80665


# ============================================================================
def _mission_model(LD, V, h_cr):
    """WP1 equivalent-range Breguet with the CF34-8E5 TSFC and the real L/D."""
    eta_j = V / (TSFC * INP.e_fuel)
    H = eta_j * LD * INP.e_fuel / G0
    R_lost = (1.0 / 0.7) * LD * (h_cr + V ** 2 / (2 * G0))

    def R_eq(R):
        return (R + R_lost) * (1 + INP.f_contingency) + 1.2 * INP.R_diversion + INP.t_loiter * V

    def M_f(R):
        return 1 - math.exp(-R_eq(R) / H)

    def fuel_for_range(R, m_end):
        return m_end * (math.exp(R_eq(R) / H) - 1)

    return M_f, fuel_for_range


def _box_area():
    """Wing-box cross-section between the spars per c^2 (as in WP2-final)."""
    pts = []
    for line in open(AIRFOIL_FILE):
        p = line.split()
        try:
            pts.append((float(p[0]), float(p[1])))
        except (ValueError, IndexError):
            pass
    pts = np.array(pts)
    i0 = int(np.argmin(pts[:, 0]))
    a, b_ = pts[:i0 + 1][::-1], pts[i0:]
    up, lo = (a, b_) if a[:, 1].mean() > b_[:, 1].mean() else (b_, a)
    up, lo = up[np.argsort(up[:, 0])], lo[np.argsort(lo[:, 0])]
    x = np.linspace(0.20, 0.70, 2001)
    t = np.interp(x, up[:, 0], up[:, 1]) - np.interp(x, lo[:, 0], lo[:, 1])
    return float(np.trapezoid(t, x))


def tank_capacity(S):
    """Usable integral-tank volumes [m^3] of the trapezoidal wing box at area S:
    wing tanks (TANK_ETA), centre box (carry-through across the fuselage width) and the
    inboard strip between the fuselage side and TANK_ETA[0] (both wings)."""
    box = _box_area()
    b = math.sqrt(G.AR_W * S)
    half = b / 2
    cr = 2 * S / (b * (1 + G.TAPER_W))
    ct = G.TAPER_W * cr

    def vol(y0, y1):
        y = np.linspace(y0, y1, 2001)
        c = cr - (cr - ct) * np.abs(y) / half
        return TANK_USABLE * box * float(np.trapezoid(c ** 2, y))

    r_f = G.D_FUS / 2
    return dict(wing=2 * vol(TANK_ETA[0] * half, TANK_ETA[1] * half),
                centre_box=vol(-r_f, r_f),
                inboard=2 * vol(r_f, TANK_ETA[0] * half))


def evaluate(MTOM, oem_frac, fuel_max):
    """Run geometry, drag and Class II at this MTOM; return the re-sized design."""
    G.MTOM = MTOM
    G.S_W = MTOM * G0 / WS
    G.OEM_FRAC = oem_frac          # MZFM, CG and fuel-system inputs use the latest OEM
    G.M_FUEL_MAX = fuel_max
    DE = importlib.reload(sys.modules["drag_estimator"]) if "drag_estimator" in sys.modules \
        else importlib.import_module("drag_estimator")
    C2 = importlib.reload(sys.modules["class2_weight_estimation"]) \
        if "class2_weight_estimation" in sys.modules else importlib.import_module("class2_weight_estimation")

    oems = [o[3] for o in C2.oem]
    methods = ("Torenbeek", "Roskam", "Raymer")
    if OEM_METHOD not in methods + ("mean",):
        raise ValueError(f"OEM_METHOD must be one of {methods + ('mean',)}, not {OEM_METHOD!r}")
    OEM = sum(oems) / 3 if OEM_METHOD == "mean" else oems[methods.index(OEM_METHOD)]

    # mid-cruise L/D (WP1 convention: mid-cruise mass = 1 - 0.5 M_f of the design mission)
    V, q = DE.v_cruise, DE.q_cruise
    LD = 15.0
    for _ in range(20):                      # L/D <-> M_f fixed point
        M_f, fuel_for_range = _mission_model(LD, V, DE.h_cruise)
        C_L = (1 - 0.5 * M_f(INP.R_design)) * WS / q
        LD_new = C_L / (DE.CD0 + C_L ** 2 / (math.pi * G.AR_W * OSWALD_E))
        if abs(LD_new - LD) < 1e-6:
            break
        LD = LD_new
    M_f, fuel_for_range = _mission_model(LD, V, DE.h_cruise)

    missions = {
        "Design mission": (OEM + INP.payload_design) / (1 - M_f(INP.R_design)),
        "MTOM + full fuel": (OEM + INP.payload_maxfuel) / (1 - M_f(INP.R_maxfuel)),
        "Harmonic": (OEM + INP.payload_max) / (1 - M_f(0.0)),
    }
    crit = max(missions, key=missions.get)
    MTOM_new = missions[crit]
    fuels = {
        "Design mission": MTOM_new * M_f(INP.R_design),
        "MTOM + full fuel": MTOM_new * M_f(INP.R_maxfuel),
        "Ferry": fuel_for_range(INP.R_ferry, OEM),
    }
    fcase = max(fuels, key=fuels.get)
    return dict(MTOM_in=MTOM, S=G.S_W, OEM=OEM, oems=oems, CD0=DE.CD0, C_L=C_L, LD=LD,
                MTOM=MTOM_new, critical=crit, missions=missions, fuels=fuels, fuel_case=fcase,
                fuel=fuels[fcase], b=C2.b, S_h=C2.S_h, S_v=C2.S_v)


def iterate(verbose=True):
    MTOM, oem_frac, fuel = MTOM_START, G.OEM_FRAC, G.M_FUEL_MAX
    hist, OEM_prev = [], None
    for k in range(MAX_IT):
        r = evaluate(MTOM, oem_frac, fuel)
        hist.append(r)
        if verbose:
            print(f"  it {k:2d}: MTOM in {r['MTOM_in']:8,.0f}  S {r['S']:6.2f}  C_D0 {r['CD0']:.5f}  "
                  f"L/D {r['LD']:5.2f}  OEM {r['OEM']:8,.0f}  -> MTOM {r['MTOM']:8,.0f} ({r['critical']})  "
                  f"fuel {r['fuel']:6,.0f}")
        done = OEM_prev is not None and abs(r["OEM"] / OEM_prev - 1) < TOL \
            and abs(r["MTOM"] / MTOM - 1) < TOL
        OEM_prev = r["OEM"]
        MTOM_next = r["MTOM"]
        oem_frac, fuel = r["OEM"] / MTOM_next, r["fuel"]
        MTOM = MTOM + 0.7 * (MTOM_next - MTOM)            # light damping
        if done:
            break
    return hist[-1], hist


def report(r):
    S = r["MTOM"] * G0 / WS
    V_fuel = r["fuel"] / RHO_FUEL
    V_wing = V_WING_REF * (S / S_WING_REF) ** 1.5
    T_req = TW * r["MTOM"] * G0 / G.N_ENG
    cap = tank_capacity(S)
    V_box = sum(cap.values())
    print(f"\nConverged ({OEM_METHOD} Class II OEM)")
    print(f"  MTOM {r['MTOM']:,.0f} kg (critical: {r['critical']}), OEM {r['OEM']:,.0f} kg "
          f"(OEM/MTOM {r['OEM'] / r['MTOM']:.4f})")
    print(f"  S {S:.2f} m^2, b {math.sqrt(S * G.AR_W):.2f} m at W/S {WS:.0f}; "
          f"tails S_h {r['S_h']:.2f}, S_v {r['S_v']:.2f} m^2")
    print(f"  C_D0 {r['CD0']:.5f}, mid-cruise C_L {r['C_L']:.3f}, L/D {r['LD']:.2f}")
    print("  MTOM per mission: " + ", ".join(f"{k} {v:,.0f}" for k, v in r["missions"].items()))
    print("  fuel per mission: " + ", ".join(f"{k} {v:,.0f}" for k, v in r["fuels"].items()))
    print(f"  fuel capacity {r['fuel']:,.0f} kg = {V_fuel:.2f} m^3 ({r['fuel_case']}); "
          f"wing tanks {V_wing:.2f} m^3 -> centre tank {max(V_fuel - V_wing, 0):.2f} m^3 "
          f"({max(V_fuel - V_wing, 0) * RHO_FUEL:,.0f} kg)")
    print(f"  integral wing-box tanks (usable {TANK_USABLE}): wing eta {TANK_ETA[0]}-{TANK_ETA[1]} "
          f"{cap['wing']:.2f}, centre box {cap['centre_box']:.2f}, inboard strip {cap['inboard']:.2f} "
          f"-> total {V_box:.2f} m^3 vs {V_fuel:.2f} needed ({V_box - V_fuel:+.2f} m^3)")
    print(f"  design-point T/W {TW} -> {T_req / 1e3:.1f} kN per engine vs CF34-8E5 59.7 kN "
          f"({100 * (59.7e3 / T_req - 1):+.0f} %); margin against the driving matching-diagram "
          f"constraint: see ws_sweep_class2.py")
    return dict(S=S, V_fuel=V_fuel, V_wing=V_wing, V_centre=max(V_fuel - V_wing, 0), T_req=T_req,
                tanks=cap, V_box=V_box)


def main():
    print(f"Class I <-> Class II iteration, start MTOM {MTOM_START:,.0f} kg, W/S {WS:.0f} N/m^2")
    r, _ = iterate()
    report(r)


if __name__ == "__main__":
    main()
