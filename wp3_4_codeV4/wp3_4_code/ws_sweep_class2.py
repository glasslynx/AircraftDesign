"""
Wing-loading sweep through the Class I <-> Class II loop (class2_iteration.py).

For each W/S the loop re-sizes MTOM, wing, tails, drag and fuel, then this script
checks the constraints that bound the design point:
  - thrust: every T/W curve of the matching diagram (group WP2 inputs, BPR 5,
    knowledge/wp1_sizing.py); the cruise-speed curve is redone with the Class II
    C_D0 and e 0.7623. Margin = CF34-8E5 59.7 kN vs the driving constraint.
  - landing field length / minimum speed: maximum W/S, evaluated at the Class II
    landing mass MLM = MZFM + reserves (class2_weight_estimation.W_L) of each design;
    wp1_sizing.py's default MLM/MTOM of 0.80 is below MZFM and over-predicts the limit
  - fuel volume: centre tank = fuel capacity - wing tanks <= CENTRE_TANK_MAX
Objective columns: MTOM and design-mission fuel.

All WP3 scripts and wp1_sizing.py must be importable (same folder, or ../knowledge).
Run:  python ws_sweep_class2.py
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "..", "knowledge")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import class2_iteration as I  # noqa: E402
import wp1_sizing as W1       # noqa: E402

# ============================================================================
WS_LIST = [4202, 4400, 4600, 4800, 5000, 5200, 5400, 5600, 5800]   # N/m^2
CENTRE_TANK_MAX = 2.5   # m^3, usable centre-tank volume the fuselage allows (group: 2-3)
T_AVAIL = 59.7e3        # N per engine, CF34-8E5 take-off thrust
N_ENG = 2
# matching-diagram inputs of the group's WP2 report (as in wp3_engine_selection.py)
MATCHING = dict(A=10.5, CLmax_clean=1.85, CLmax_takeoff=2.61, CLmax_landing=2.93,
                d_flap_landing=40.0, design_WS=4202.0, design_TW=0.345,
                oem_method="regression", BPR=5.0)
# C_Lmax landing: 2.93 = group's WP2 report (WP3.1 basis); 2.756 = WP2-final iteration
G0 = 9.80665


def constraints():
    inp = W1.Inputs()
    for k, v in MATCHING.items():
        setattr(inp, k, v)
    res, _ = W1.run_converged(inp)
    return inp, res["con"]


def main():
    inp, con = constraints()
    _, _, rho, a = W1.isa(inp.h_cruise)
    V = inp.M_cruise * a
    q = 0.5 * rho * V ** 2
    alpha = float(W1.thrust_lapse(V, inp.h_cruise, 0.0, inp))
    print(f"OEM method {I.OEM_METHOD}, fixed equipment "
          f"{sys.modules['class2_weight_estimation'].FIXED_EQUIPMENT_MODE if 'class2_weight_estimation' in sys.modules else ''}; "
          f"C_Lmax landing {inp.CLmax_landing}; centre tank limit {CENTRE_TANK_MAX} m^3\n")
    print(f"{'W/S':>5} {'MTOM':>7} {'OEM':>7} {'S':>6} {'b':>6} {'C_D0':>8} {'C_L':>6} {'L/D':>6} "
          f"{'fuel des':>8} {'V_fuel':>6} {'V_wing':>6} {'centre':>6}  {'driving T/W':<14} "
          f"{'T/W':>6} {'T req':>6} {'margin':>6} {'MLM/MTOM':>8} {'W/S max':>7}")
    for WS in WS_LIST:
        I.WS = WS
        r, _ = I.iterate(verbose=False)
        S = r["MTOM"] * G0 / WS
        V_fuel = r["fuel"] / I.RHO_FUEL
        V_wing = I.V_WING_REF * (S / I.S_WING_REF) ** 1.5
        V_ctr = max(V_fuel - V_wing, 0.0)

        f_L = sys.modules["class2_weight_estimation"].W_L / r["MTOM_in"]   # MLM / MTOM
        inp.f_landing = inp.f_approach = f_L
        inp.climb_gradients = tuple(c[:3] + (f_L,) + c[4:] if c[4] == "landing" else c
                                    for c in inp.climb_gradients)
        ev = con.evaluate(np.array([float(WS)]))
        ws_max = min(float(ev["Minimum speed"]), float(ev["Landing field length"]))
        tw = {k: float(np.atleast_1d(v)[0]) for k, v in ev.items()
              if k not in ("Minimum speed", "Landing field length")}
        f = r["C_L"] * q / WS                       # mid-cruise mass fraction
        tw["Cruise speed"] = (f / alpha) * (r["CD0"] * q / (WS * f)
                                            + WS * f / (q * math.pi * I.G.AR_W * I.OSWALD_E))
        drv = max(tw, key=tw.get)
        T_req = tw[drv] * r["MTOM"] * G0 / N_ENG
        ok = V_ctr <= CENTRE_TANK_MAX and WS <= ws_max and T_req <= T_AVAIL
        print(f"{WS:5d} {r['MTOM']:7,.0f} {r['OEM']:7,.0f} {S:6.1f} {math.sqrt(I.G.AR_W * S):6.2f} "
              f"{r['CD0']:8.5f} {r['C_L']:6.3f} {r['LD']:6.2f} {r['fuels']['Design mission']:8,.0f} "
              f"{V_fuel:6.2f} {V_wing:6.2f} {V_ctr:6.2f}  {drv:<14} {tw[drv]:6.3f} "
              f"{T_req / 1e3:6.1f} {100 * (T_AVAIL / T_req - 1):+5.0f}% {f_L:8.3f} {ws_max:7,.0f}"
              f"{'' if ok else '  x'}")
    print("\nx = violates the centre-tank, landing or thrust limit")


if __name__ == "__main__":
    main()
