"""
WP3.4 design-point optimiser: Class I <-> Class II iteration over wing loading and
aspect ratio, with the WP1 (matching diagram), WP2 (wing) and WP3 (engine, fuel
volume) constraints checked at every converged design.

Design variables
  W/S   wing loading [N/m^2]          (WS_GRID)
  AR    aspect ratio, <= 10.6 (ADSEE) (AR_GRID)
Fixed: fuselage, CF34-8E5 engines, planform shape (taper, LE sweep, SC(2)-0612),
cruise M 0.77 at FL350, all WP1 missions and requirements.

For each (W/S, AR):  class2_iteration.iterate() closes MTOM <-> S <-> geometry <->
Class II drag <-> mid-cruise L/D <-> Class II OEM (OEM_METHOD and fixed-equipment
mode as set in class2_iteration.py / class2_weight_estimation.py).

Constraints (feasible if all hold)
  1 thrust      every matching-diagram T/W curve <= CF34-8E5 T/W available; climb and
                cruise curves use the Class II polar, landing cases the Class II MLM
  2 landing     W/S <= landing-field-length and minimum-speed limits (C_Lmax 2.93,
                MLM = MZFM + reserves)
  3 fuel        fuel volume <= integral wing-box tanks (wing + centre box + inboard
                strip) + AUX_TANK
  4 L/D         mid-cruise L/D >= 15.4 (REQ-WNG-EFF-02)
  5 M_DD        drag-divergence Mach at the start-of-cruise C_L >= cruise Mach
  6 AR          <= 10.6
  7 span        <= 36 m (ICAO code C)
  8 WP2 wing    wing_checks.py (group's hld_aileron_sizing.py at this S and AR):
                REQ-HLD-01/02 C_Lmax, REQ-RCS-01 flap span inboard of the ailerons,
                REQ-RCS-02 CS 25.149(h)(4) roll at V_SR0, REQ-RCS-03 25 % aileron travel
                unused, REQ-RCS-04 pb/2V >= 0.07. With CLMAX_FROM_HLD the matching
                diagram uses the C_Lmax (clean / take-off / landing) of this wing.
                The angle at C_Lmax vs the 16 deg tail-strike angle is reported only
                (it already exceeded it in WP2).
Objective (OBJECTIVE): minimum MTOM, or minimum design-mission fuel. Both are reported
for the optimum of every AR, because they pull AR in opposite directions (a lower AR
gives a lighter wing but more induced drag).

The optimum is refined by bisection on the active constraint (MTOM falls with W/S)
or by a bounded scalar minimisation if MTOM has an interior minimum.

Outputs: console table, wp3/optimiser/ figures and optimum_summary.txt.
All WP3 scripts and wp1_sizing.py must be importable (same folder or ../knowledge).
Run:  python wp3_4_optimiser.py
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "..", "knowledge")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import matplotlib                      # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt        # noqa: E402
from scipy.optimize import minimize_scalar  # noqa: E402

import class2_iteration as I           # noqa: E402
import wing_checks as WC               # noqa: E402
import wp1_sizing as W1                # noqa: E402

G = I.G
G0 = 9.80665

# ============================================================================
# INPUT BLOCK
# ============================================================================
WS_GRID = np.arange(4000, 5401, 100.0)  # N/m^2
AR_GRID = [9.5, 10.0, 10.5, 10.6]       # 10.6 = ADSEE upper limit
AR_MAX = 10.6
SPAN_MAX = 36.0                         # m, ICAO aerodrome code C
LD_MIN = 15.4                           # REQ-WNG-EFF-02
T_AVAIL = 59.7e3                        # N per engine, CF34-8E5 take-off thrust
N_ENG = 2
AUX_TANK = 0.0                          # m^3, extra usable fuselage tank outside the wing box
INCLUDE_INBOARD_STRIP = True            # use the box between fuselage side and eta 0.17
E_WP2, AR_WP2 = 0.7623, 10.5            # Oswald factor of the WP2 wing at its AR
# matching-diagram inputs: group WP2 report (C_Lmax 1.85 / 2.61 / 2.93), BPR 5
CLMAX_FROM_HLD = True                   # matching diagram uses the HLD C_Lmax of each wing
MATCHING = dict(CLmax_clean=1.85, CLmax_takeoff=2.61, CLmax_landing=2.93,
                d_flap_landing=40.0, design_TW=0.345, oem_method="regression", BPR=5.0)
OBJECTIVE = "MTOM"                      # "MTOM" or "fuel" (design-mission fuel)
OUT_DIR = os.path.join(HERE, "optimiser")


# ============================================================================
# Matching diagram (WP1 tool) with Class II polar and landing mass
# ============================================================================
def _matching(AR):
    inp = W1.Inputs()
    for k, v in MATCHING.items():
        setattr(inp, k, v)
    inp.A = AR
    inp.design_WS = 4800.0
    res, _ = W1.run_converged(inp)
    return inp, res["con"]


_MATCH = {}


def oswald(AR, inp):
    """WP1 Oswald model (phi, e_span) scaled to the agreed WP2 value at AR 10.5."""
    def f(A):
        return 1.0 / (math.pi * A * inp.phi + 1.0 / inp.e_span)
    return E_WP2 * f(AR) / f(AR_WP2)


def constraints_at(WS, AR, r, C2, DE, wc=None):
    """T/W curves and W/S limits at a converged design r (wc: wing checks for C_Lmax)."""
    if AR not in _MATCH:
        _MATCH[AR] = _matching(AR)
    inp, con = _MATCH[AR]
    f_L = C2.W_L / r["MTOM_in"]                              # MLM / MTOM
    if wc is not None and CLMAX_FROM_HLD:
        inp.CLmax_clean, inp.CLmax_takeoff, inp.CLmax_landing = \
            wc["CLmax_clean"], wc["CLmax_TO"], wc["CLmax_L"]
    inp.f_landing = inp.f_approach = f_L
    inp.climb_gradients = tuple(c[:3] + (f_L,) + c[4:] if c[4] == "landing" else c
                                for c in W1.Inputs().climb_gradients)
    con.polar.CD0_clean = DE.CD0_no_wave                     # Class II low-speed C_D0
    con.polar.e_clean = I.OSWALD_E
    ev = con.evaluate(np.array([float(WS)]))
    ws_lim = {k: float(ev[k]) for k in ("Landing field length", "Minimum speed")}
    tw = {k: float(np.atleast_1d(v)[0]) for k, v in ev.items() if k not in ws_lim}
    # cruise with the Class II drag including wave drag, at the mid-cruise mass
    _, _, rho, a = W1.isa(inp.h_cruise)
    V = inp.M_cruise * a
    q = 0.5 * rho * V ** 2
    alpha = float(W1.thrust_lapse(V, inp.h_cruise, 0.0, inp))
    fm = r["C_L"] * q / WS
    tw["Cruise speed"] = (fm / alpha) * (r["CD0"] * q / (WS * fm)
                                         + WS * fm / (q * math.pi * AR * I.OSWALD_E))
    return tw, ws_lim, f_L


# ============================================================================
# One converged design
# ============================================================================
def design(WS, AR):
    G.AR_W = AR
    I.WS = WS
    I.OSWALD_E = oswald(AR, W1.Inputs())
    r, hist = I.iterate(verbose=False)
    C2 = sys.modules["class2_weight_estimation"]
    DE = sys.modules["drag_estimator"]
    converged = len(hist) < I.MAX_IT
    S = r["MTOM"] * G0 / WS
    b = math.sqrt(AR * S)
    cap = I.tank_capacity(S)
    V_box = cap["wing"] + cap["centre_box"] + (cap["inboard"] if INCLUDE_INBOARD_STRIP else 0.0)
    V_fuel = r["fuel"] / I.RHO_FUEL
    f_L = C2.W_L / r["MTOM_in"]
    wc = WC.check(S, AR, WS, f_L)
    tw, ws_lim, f_L = constraints_at(WS, AR, r, C2, DE, wc)
    drv = max(tw, key=tw.get)
    tw_avail = N_ENG * T_AVAIL / (r["MTOM"] * G0)
    ws_max = min(ws_lim.values())
    fuel_des = r["fuels"]["Design mission"]
    sar = I.INP.R_design / fuel_des   # m/kg, design-mission block average (incl. reserves)

    fails = []
    if tw[drv] > tw_avail:
        fails.append("thrust")
    if WS > ws_max:
        fails.append("landing")
    if V_fuel > V_box + AUX_TANK:
        fails.append("fuel volume")
    if r["LD"] < LD_MIN:
        fails.append("L/D")
    if DE.M_DD < DE.M_cruise:
        fails.append("M_DD")
    if AR > AR_MAX + 1e-9:
        fails.append("AR")
    if b > SPAN_MAX:
        fails.append("span")
    if not converged:
        fails.append("not converged")
    fails += wc["fails"]
    return dict(WS=WS, AR=AR, MTOM=r["MTOM"], OEM=r["OEM"], S=S, b=b, CD0=r["CD0"],
                CD0_nw=DE.CD0_no_wave, e=I.OSWALD_E, C_L=r["C_L"], LD=r["LD"], M_DD=DE.M_DD,
                fuel_des=fuel_des, fuel_cap=r["fuel"], V_fuel=V_fuel, V_box=V_box, cap=cap,
                tw=tw, drv=drv, tw_req=tw[drv], tw_avail=tw_avail,
                margin=tw_avail / tw[drv] - 1, ws_max=ws_max, f_L=f_L, sar=sar, wc=wc,
                fails=fails, ok=not fails, hist=hist, r=r)


# ============================================================================
# Wing aerodynamic optimum at the design point: best cruise C_L and altitude
# ============================================================================
def cruise_optimum(d):
    """C_L of maximum L/D at M 0.77 (with wave drag) and the altitude that would put
    the mid-cruise C_L there, for the converged design d."""
    DE = sys.modules["drag_estimator"]
    cs = math.cos(DE.sweep_half)

    def cd(CL):
        mdd = DE.k_a / cs - DE.t_to_c_w / cs ** 2 - CL / (10 * cs ** 3)
        mcr = mdd - (0.1 / 80) ** (1 / 3)
        M = DE.M_cruise
        if M <= mcr:
            w = 0.0
        elif M <= mdd:
            w = 0.002 * (1 + 2.5 * (mdd - M) / 0.05) ** -1
        else:
            w = 0.002 * (1 + (M - mdd) / 0.05) ** 2.5
        return d["CD0_nw"] + w / (1 - DE.leakage_frac) + CL ** 2 / (math.pi * d["AR"] * d["e"])

    res = minimize_scalar(lambda CL: -CL / cd(CL), bounds=(0.2, 0.8), method="bounded")
    CL_opt = res.x
    # altitude at which mid-cruise C_L = CL_opt at M 0.77: q = W/S_mid / CL_opt
    ws_mid = d["C_L"] * DE.q_cruise
    q_opt = ws_mid / CL_opt
    h_lo, h_hi = 6000.0, 14000.0
    for _ in range(60):
        h = 0.5 * (h_lo + h_hi)
        T, rho, a, _ = DE.isa(h)
        q = 0.5 * rho * (DE.M_cruise * a) ** 2
        h_lo, h_hi = (h, h_hi) if q > q_opt else (h_lo, h)
    return dict(CL_opt=CL_opt, LD_opt=-res.fun, h_opt=h, LD_now=d["C_L"] / cd(d["C_L"]))


# ============================================================================
def sweep():
    rows = []
    hdr = (f"{'AR':>5} {'W/S':>5} {'MTOM':>7} {'OEM':>7} {'S':>5} {'b':>5} {'C_D0':>7} {'e':>5} "
           f"{'C_L':>5} {'L/D':>5} {'M_DD':>5} {'fuel':>5} {'V_f':>5} {'V_box':>5} "
           f"{'T/W req':>7} {'avail':>5} {'W/S max':>7} {'CLmaxL':>6} {'t20':>4}  status")
    print(hdr)
    for AR in AR_GRID:
        for WS in WS_GRID:
            d = design(WS, AR)
            rows.append(d)
            print(f"{AR:5.1f} {WS:5.0f} {d['MTOM']:7,.0f} {d['OEM']:7,.0f} {d['S']:5.1f} {d['b']:5.2f} "
                  f"{d['CD0']:7.5f} {d['e']:5.3f} {d['C_L']:5.3f} {d['LD']:5.2f} {d['M_DD']:5.3f} "
                  f"{d['fuel_des']:5.0f} {d['V_fuel']:5.2f} {d['V_box']:5.2f} {d['tw_req']:7.3f} "
                  f"{d['tw_avail']:5.3f} {d['ws_max']:7,.0f} {d['wc']['CLmax_L']:6.3f} {d['wc']['t20']:4.2f}  "
                  f"{'ok' if d['ok'] else ', '.join(d['fails'])}", flush=True)
    return rows


def _obj(d):
    return d["MTOM"] if OBJECTIVE == "MTOM" else d["fuel_des"]


def refine(rows, AR):
    """Best feasible grid point at this AR, refined along W/S."""
    line = sorted([d for d in rows if d["AR"] == AR], key=lambda d: d["WS"])
    feas = [d for d in line if d["ok"]]
    if not feas:
        return None, "no feasible W/S"
    best = min(feas, key=_obj)
    k = line.index(best)
    if k + 1 < len(line) and not line[k + 1]["ok"]:
        # constraint-bound: bisect the feasibility boundary between the two grid points
        lo, hi = best, line[k + 1]
        while hi["WS"] - lo["WS"] > 2.0:
            mid = design(0.5 * (lo["WS"] + hi["WS"]), AR)
            lo, hi = (mid, hi) if mid["ok"] else (lo, mid)
        return lo, ", ".join(hi["fails"])
    if k == len(line) - 1:
        return best, "end of W/S grid"
    a = line[max(k - 1, 0)]["WS"]
    b = line[k + 1]["WS"]
    res = minimize_scalar(lambda ws: _obj(design(ws, AR)), bounds=(a, b),
                          method="bounded", options={"xatol": 2.0})
    return design(res.x, AR), f"none (interior minimum of {OBJECTIVE})"


# ============================================================================
def figures(rows, opt):
    os.makedirs(OUT_DIR, exist_ok=True)
    cols = plt.cm.viridis(np.linspace(0.1, 0.85, len(AR_GRID)))

    # 1. MTOM vs W/S per AR, infeasible points hollow
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for AR, c in zip(AR_GRID, cols):
        L = sorted([d for d in rows if d["AR"] == AR], key=lambda d: d["WS"])
        ax.plot([d["WS"] for d in L], [d["MTOM"] for d in L], "-", color=c, lw=1.2, label=f"AR {AR}")
        ax.plot([d["WS"] for d in L if d["ok"]], [d["MTOM"] for d in L if d["ok"]], "o", color=c, ms=4)
        ax.plot([d["WS"] for d in L if not d["ok"]], [d["MTOM"] for d in L if not d["ok"]], "o",
                mfc="none", color=c, ms=4)
    ax.plot(opt["WS"], opt["MTOM"], "*", ms=15, color="#d62728", label="optimum", zorder=5)
    ax.set_xlabel("W/S [N/m²]"); ax.set_ylabel("MTOM [kg]")
    ax.set_title("Converged MTOM (filled = feasible, hollow = violates a constraint)")
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "mtom_vs_ws.png"), dpi=200); plt.close(fig)

    # 2. L/D, C_L and design fuel vs W/S at the optimum AR
    L = sorted([d for d in rows if d["AR"] == opt["AR"]], key=lambda d: d["WS"])
    ws = [d["WS"] for d in L]
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.8))
    axs[0].plot(ws, [d["LD"] for d in L], "o-", ms=3); axs[0].axhline(LD_MIN, ls="--", c="k", lw=0.8)
    axs[0].set_ylabel("mid-cruise L/D"); axs[0].set_title("L/D (dashed: REQ-WNG-EFF-02)")
    axs[1].plot(ws, [d["C_L"] for d in L], "o-", ms=3); axs[1].set_ylabel("mid-cruise C_L")
    axs[1].set_title("Cruise lift coefficient")
    axs[2].plot(ws, [d["fuel_des"] for d in L], "o-", ms=3); axs[2].set_ylabel("design-mission fuel [kg]")
    axs[2].set_title("Fuel burn")
    for a in axs:
        a.axvline(opt["WS"], c="#d62728", lw=0.8); a.set_xlabel("W/S [N/m²]"); a.grid(alpha=0.3)
    fig.suptitle(f"AR {opt['AR']}"); fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "aero_vs_ws.png"), dpi=200); plt.close(fig)

    # 3. fuel volume needed vs available
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(ws, [d["V_fuel"] for d in L], "o-", ms=3, label="fuel volume needed")
    ax.plot(ws, [d["cap"]["wing"] for d in L], "--", label="wing tanks η 0.17–0.83")
    ax.plot(ws, [d["cap"]["wing"] + d["cap"]["centre_box"] for d in L], "-.", label="+ centre box")
    ax.plot(ws, [d["V_box"] + AUX_TANK for d in L], "-", label="+ inboard strip (+ aux)")
    ax.axvline(opt["WS"], c="#d62728", lw=0.8)
    ax.set_xlabel("W/S [N/m²]"); ax.set_ylabel("usable volume [m³]"); ax.grid(alpha=0.3)
    ax.legend(fontsize=8); ax.set_title(f"Fuel volume, AR {opt['AR']}")
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "fuel_volume_vs_ws.png"), dpi=200); plt.close(fig)

    # 4. matching diagram at the optimum (Class II polar and MLM)
    inp, con = _MATCH[opt["AR"]]
    WSr = np.linspace(3000, 6500, 300)
    ev = con.evaluate(WSr)
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for k, v in ev.items():
        if k in ("Landing field length", "Minimum speed"):
            ax.axvline(float(v), ls="--", lw=1, label=k)
        elif k != "Cruise speed":
            ax.plot(WSr, np.atleast_1d(v), lw=1, label=k)
    # cruise curve with the Class II drag at the optimum (scaled from the optimum point)
    cr = np.atleast_1d(ev["Cruise speed"]) * opt["tw"]["Cruise speed"] / float(
        np.atleast_1d(con.evaluate(np.array([opt["WS"]]))["Cruise speed"])[0])
    ax.plot(WSr, cr, lw=1.6, c="k", label="Cruise speed (Class II drag)")
    ax.axhline(opt["tw_avail"], c="#d62728", ls=":", lw=1.2, label="CF34-8E5 T/W available")
    ax.plot(opt["WS"], opt["tw_avail"], "*", ms=15, c="#d62728", label="optimum")
    ax.set_xlim(3000, 6500); ax.set_ylim(0, 0.5)
    ax.set_xlabel("W/S [N/m²]"); ax.set_ylabel("T/W [-]"); ax.grid(alpha=0.3)
    ax.legend(fontsize=6.5, ncol=2, loc="upper left")
    ax.set_title(f"Matching diagram at the optimum (AR {opt['AR']}, MLM/MTOM {opt['f_L']:.3f})")
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "matching_diagram_optimum.png"), dpi=200)
    plt.close(fig)


def summary(opt, active, co):
    ref = design(4202.0, 10.5)
    lines = [
        "WP3.4 optimum (Class I <-> Class II, OEM method %s, fixed equipment %s)"
        % (I.OEM_METHOD, sys.modules["class2_weight_estimation"].FIXED_EQUIPMENT_MODE),
        f"  W/S {opt['WS']:,.0f} N/m^2, AR {opt['AR']}, active constraint: {active}",
        f"  MTOM {opt['MTOM']:,.0f} kg, OEM {opt['OEM']:,.0f} kg, S {opt['S']:.2f} m^2, b {opt['b']:.2f} m",
        f"  C_D0 {opt['CD0']:.5f} (no wave {opt['CD0_nw']:.5f}), e {opt['e']:.4f}, mid-cruise C_L "
        f"{opt['C_L']:.3f}, L/D {opt['LD']:.2f}, M_DD {opt['M_DD']:.3f}",
        f"  design-mission fuel {opt['fuel_des']:,.0f} kg ({opt['sar']:.0f} m/kg incl. reserves); fuel "
        f"capacity {opt['fuel_cap']:,.0f} kg = {opt['V_fuel']:.2f} m^3 vs wing box {opt['V_box']:.2f} m^3 "
        f"(wing {opt['cap']['wing']:.2f}, centre {opt['cap']['centre_box']:.2f}, inboard "
        f"{opt['cap']['inboard']:.2f})",
        f"  driving T/W {opt['drv']} {opt['tw_req']:.3f} vs available {opt['tw_avail']:.3f} "
        f"({100 * opt['margin']:+.0f} %); W/S limit {opt['ws_max']:,.0f} (MLM/MTOM {opt['f_L']:.3f})",
        f"  cruise optimum of this wing at M 0.77: C_L {co['CL_opt']:.3f} (L/D {co['LD_opt']:.2f}) vs "
        f"{opt['C_L']:.3f} flown (L/D {co['LD_now']:.2f}); best mid-cruise altitude "
        f"{co['h_opt']:,.0f} m (FL{co['h_opt'] / 0.3048 / 100:.0f}) vs FL350",
        f"  WP2 wing: C_Lmax {opt['wc']['CLmax_clean']:.3f} / {opt['wc']['CLmax_TO']:.3f} / "
        f"{opt['wc']['CLmax_L']:.3f} (needed {opt['wc']['CL_req']:.3f}); flap for it to "
        f"{opt['wc']['eta_flap_req']:.3f} b/2 (ailerons from {WC.H.ail_eta_in} b/2); 20 deg roll in "
        f"{opt['wc']['t20']:.2f} s at V_SR0 {opt['wc']['V_SR0']:.1f} m/s ({100 * opt['wc']['unused']:.0f} % "
        f"travel unused); pb/2V {opt['wc']['helix']:.4f}; alpha at C_Lmax {opt['wc']['alpha_max']:.1f} deg "
        f"vs tail strike {WC.TAILSTRIKE:.0f} ({'OK' if opt['wc']['tailstrike_ok'] else 'exceeds, as in WP2'})",
        f"  vs W/S 4,202 / AR 10.5 (same settings): MTOM {ref['MTOM']:,.0f} kg "
        f"({opt['MTOM'] - ref['MTOM']:+,.0f}), fuel {ref['fuel_des']:,.0f} kg "
        f"({opt['fuel_des'] - ref['fuel_des']:+,.0f}), S {ref['S']:.1f} m^2",
    ]
    txt = "\n".join(lines)
    print("\n" + txt)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "optimum_summary.txt"), "w") as f:
        f.write(txt + "\n")


def main():
    rows = sweep()
    per_ar = {AR: refine(rows, AR) for AR in AR_GRID}
    print(f"\nOptimum W/S per AR (objective {OBJECTIVE}):")
    print(f"{'AR':>5} {'W/S':>6} {'MTOM':>7} {'fuel':>6} {'S':>6} {'L/D':>6}  active constraint")
    for AR, (d, act) in per_ar.items():
        if d is None:
            print(f"{AR:5.1f}  {act}")
            continue
        print(f"{AR:5.1f} {d['WS']:6,.0f} {d['MTOM']:7,.0f} {d['fuel_des']:6,.0f} {d['S']:6.2f} "
              f"{d['LD']:6.2f}  {act}")
    opt, active = min(((d, a) for d, a in per_ar.values() if d is not None), key=lambda t: _obj(t[0]))
    if AR_GRID.index(opt["AR"]) in (0, len(AR_GRID) - 1):
        active += f"; AR at the edge of AR_GRID ({opt['AR']})"
    design(opt["WS"], opt["AR"])          # leave the modules at the optimum for cruise_optimum
    co = cruise_optimum(opt)
    figures(rows, opt)
    summary(opt, active, co)


if __name__ == "__main__":
    main()
