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
Objective (OBJECTIVE): minimum design-mission fuel (default, Akos 2026-10-19: fuel burn
is what the operator pays for), or minimum MTOM. They pull AR in opposite directions
(a lower AR gives a lighter wing but more induced drag): the fuel optimum is the highest
AR (10.6) at the fuel-volume limit, the MTOM optimum the lowest AR (9.5).

The optimum is refined by bisection on the active constraint (fuel and MTOM fall with
W/S) or by a bounded scalar minimisation if the objective has an interior minimum.

Selected design point (SELECTED): the final design is taken at the min-fuel optimum
itself, W/S 4,989 N/m^2 at AR 10.6 (Akos, agreed with the TA, 2026-11-09; it was
4,900 / AR 10.5 with margin before). It is evaluated with the same checks, shown in
every figure, and the summary lists its margin to every constraint.

Specific air range at the mid-cruise mass (WP2 convention, sar-assessment.tex):
  SAR = V (L/D) / (c_T W_mid)   [m/kg],  W_mid = (1 - 0.5 M_f) MTOM g = C_L q S
with the CF34-8E5 c_T (class2_iteration.TSFC, constant with altitude) and the Class II
drag. Also SAR against cruise altitude at M 0.77 for the optimum and selected wings,
with the CF34-8E5 thrust limit (Mattingly lapse, BPR 5).

Outputs: console table, wp3/optimiser/ figures (mtom_vs_ws, aero_vs_ws, sar,
fuel_volume_vs_ws, matching_diagram_optimum, matching_diagram_selected) and
optimum_summary.txt.
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
AUX_TANK = 0.15                         # m^3, usable auxiliary fuselage tank (V4, 2026-11-10):
                                        # sized so the fuel volume no longer limits W/S; the
                                        # landing C_Lmax / REQ-RCS-01 limit needs 0.13 m^3, rounded up.
                                        # Its system mass is in class2_weight_estimation (N_TANKS 4).
INCLUDE_INBOARD_STRIP = True            # use the box between fuselage side and eta 0.17
E_WP2, AR_WP2 = 0.7623, 10.5            # Oswald factor of the WP2 wing at its AR
# matching-diagram inputs: group WP2 report (C_Lmax 1.85 / 2.61 / 2.93), BPR 5
CLMAX_FROM_HLD = True                   # matching diagram uses the HLD C_Lmax of each wing
MATCHING = dict(CLmax_clean=1.85, CLmax_takeoff=2.61, CLmax_landing=2.93,
                d_flap_landing=40.0, design_TW=0.345, oem_method="regression", BPR=5.0)
OBJECTIVE = "fuel"                      # "fuel" (design-mission fuel) or "MTOM"
# Selected (final) design point. Akos + TA 2026-11-09: the min-fuel optimum itself
# (bisection boundary 4,989.x rounded down, so it stays feasible). Was 4,900 / 10.5.
# None = report the optimum only.
# V4 2026-11-10: with the 0.15 m^3 auxiliary fuselage tank the fuel volume no longer limits
# W/S; the optimum moves to the landing C_Lmax / REQ-RCS-01 limit, 5,046.9 rounded down.
SELECTED = dict(WS=5046.0, AR=10.6)
H_SAR = np.arange(8000.0, 13501.0, 100.0)   # m, altitudes for the SAR-altitude curve
OUT_DIR = os.path.join(HERE, "optimiser")


# ============================================================================
# Matching diagram (WP1 tool) with Class II polar and landing mass
# ============================================================================
def _matching(AR):
    inp = W1.Inputs()
    for k, v in MATCHING.items():
        setattr(inp, k, v)
    inp.A = AR
    inp.design_WS = SELECTED["WS"] if SELECTED else 4900.0
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
    sar_block = I.INP.R_design / fuel_des   # m/kg, design-mission block average (incl. reserves)
    W_mid = r["C_L"] * DE.q_cruise * S      # N, mid-cruise weight (1 - 0.5 M_f) MTOM g
    sar = DE.v_cruise * r["LD"] / (I.TSFC * W_mid)   # m/kg, mid-cruise SAR

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
                margin=tw_avail / tw[drv] - 1, ws_max=ws_max, f_L=f_L, sar=sar,
                sar_block=sar_block, W_mid=W_mid, wc=wc,
                fails=fails, ok=not fails, hist=hist, r=r)


# ============================================================================
# Wing aerodynamic optimum and SAR at the design point: cruise C_L and altitude
# ============================================================================
def _cd(d, CL):
    """Cruise drag coefficient of design d at M 0.77 with the wave drag at this C_L.
    Uses the drag_estimator state of d, so call design(d) first."""
    DE = sys.modules["drag_estimator"]
    cs = math.cos(DE.sweep_half)
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


def cruise_optimum(d):
    """C_L of maximum L/D at M 0.77 (with wave drag) and the altitude that would put
    the mid-cruise C_L there, for the converged design d (call design(d) first)."""
    DE = sys.modules["drag_estimator"]
    res = minimize_scalar(lambda CL: -CL / _cd(d, CL), bounds=(0.2, 0.8), method="bounded")
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
    return dict(CL_opt=CL_opt, LD_opt=-res.fun, h_opt=h, LD_now=d["C_L"] / _cd(d, d["C_L"]))


def sar_altitude(d):
    """Mid-cruise SAR against altitude at M 0.77 for design d (same mass and wing,
    c_T constant), and whether the two CF34-8E5 can give the cruise thrust there
    (Mattingly lapse, BPR 5). Call design(d) first."""
    DE = sys.modules["drag_estimator"]
    inp = _MATCH[d["AR"]][0]
    h_out, cl_out, sar_out, ok_out = [], [], [], []
    for h in H_SAR:
        T, rho, a, _ = DE.isa(h)
        V = DE.M_cruise * a
        q = 0.5 * rho * V ** 2
        CL = d["W_mid"] / (q * d["S"])
        cd = _cd(d, CL)
        T_av = N_ENG * T_AVAIL * float(W1.thrust_lapse(V, h, 0.0, inp))
        h_out.append(h); cl_out.append(CL)
        sar_out.append(V * (CL / cd) / (I.TSFC * d["W_mid"]))
        ok_out.append(q * d["S"] * cd <= T_av)
    h, sar, ok = np.array(h_out), np.array(sar_out), np.array(ok_out)
    i_best = int(np.argmax(sar))
    i_ok = int(np.argmax(np.where(ok, sar, -1.0)))
    ceiling = h[ok].max() if ok.any() else float("nan")
    i_cr = int(np.argmin(abs(h - DE.h_cruise)))
    return dict(h=h, CL=np.array(cl_out), sar=sar, ok=ok, h_best=h[i_best], sar_best=sar[i_best],
                h_best_thrust=h[i_ok], sar_best_thrust=sar[i_ok], ceiling=ceiling,
                sar_cruise=sar[i_cr])


def matching_curves(d):
    """Matching-diagram curves of design d (Class II polar, its MLM and C_Lmax).
    Call design(d) first."""
    inp, con = _MATCH[d["AR"]]
    WSr = np.linspace(3000, 6500, 300)
    ev = con.evaluate(WSr)
    lims = {k: float(ev[k]) for k in ("Landing field length", "Minimum speed")}
    tw = {k: np.atleast_1d(v).copy() for k, v in ev.items() if k not in lims and k != "Cruise speed"}
    # cruise curve with the Class II drag incl. wave drag (scaled to d's cruise point)
    tw["Cruise speed (Class II drag)"] = np.atleast_1d(ev["Cruise speed"]) * d["tw"]["Cruise speed"] / float(
        np.atleast_1d(con.evaluate(np.array([d["WS"]]))["Cruise speed"])[0])
    return dict(WS=WSr, tw=tw, lims=lims)


def evaluate_point(WS, AR):
    """Converged design plus its cruise optimum, SAR-altitude curve and matching curves."""
    d = design(WS, AR)
    d["co"] = cruise_optimum(d)
    d["alt"] = sar_altitude(d)
    d["mc"] = matching_curves(d)
    return d


# ============================================================================
def sweep():
    rows = []
    hdr = (f"{'AR':>5} {'W/S':>5} {'MTOM':>7} {'OEM':>7} {'S':>5} {'b':>5} {'C_D0':>7} {'e':>5} "
           f"{'C_L':>5} {'L/D':>5} {'SAR':>5} {'M_DD':>5} {'fuel':>5} {'V_f':>5} {'V_box':>5} "
           f"{'T/W req':>7} {'avail':>5} {'W/S max':>7} {'CLmaxL':>6} {'t20':>4}  status")
    print(hdr)
    for AR in AR_GRID:
        for WS in WS_GRID:
            d = design(WS, AR)
            rows.append(d)
            print(f"{AR:5.1f} {WS:5.0f} {d['MTOM']:7,.0f} {d['OEM']:7,.0f} {d['S']:5.1f} {d['b']:5.2f} "
                  f"{d['CD0']:7.5f} {d['e']:5.3f} {d['C_L']:5.3f} {d['LD']:5.2f} {d['sar']:5.0f} "
                  f"{d['M_DD']:5.3f} {d['fuel_des']:5.0f} {d['V_fuel']:5.2f} {d['V_box']:5.2f} "
                  f"{d['tw_req']:7.3f} {d['tw_avail']:5.3f} {d['ws_max']:7,.0f} {d['wc']['CLmax_L']:6.3f} "
                  f"{d['wc']['t20']:4.2f}  {'ok' if d['ok'] else ', '.join(d['fails'])}", flush=True)
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
# Figures: optimum (red star) and selected point (green diamond) on every plot
# ============================================================================
OPT_KW = dict(marker="*", ms=16, color="#d62728", mec="k", mew=0.5, ls="none", zorder=6)
SEL_KW = dict(marker="D", ms=8, color="#2ca02c", mec="k", mew=0.8, ls="none", zorder=6)


def _line(rows, AR):
    return sorted([d for d in rows if d["AR"] == AR], key=lambda d: d["WS"])


_MERGED = False   # True when the selected point is the optimum itself (one marker per plot)


def _same(opt, sel):
    return sel is not None and sel["AR"] == opt["AR"] and abs(sel["WS"] - opt["WS"]) < 2.0


def _lab(d, what):
    if what == "optimum":
        what = "min-fuel optimum" if OBJECTIVE == "fuel" else "min-MTOM optimum"
        if _MERGED:
            what = "final design = " + what
    return f"{what} (W/S {d['WS']:,.0f}, AR {d['AR']})"


def _points(ax, opt, sel, ykey, scale=1.0):
    ax.plot(opt["WS"], opt[ykey] * scale, label=_lab(opt, "optimum"), **OPT_KW)
    if sel is not None and not _MERGED:
        ax.plot(sel["WS"], sel[ykey] * scale, label=_lab(sel, "selected"), **SEL_KW)


def _boundary(ax, per_ar, AR, label=True):
    """Vertical line at the feasibility boundary (the constraint optimum) of this AR."""
    d, act = per_ar.get(AR, (None, ""))
    if d is not None:
        ax.axvline(d["WS"], c="#2ca02c", ls=":", lw=1.1,
                   label=f"constraint limit AR {AR}: W/S {d['WS']:,.0f} ({act})" if label else None)


def plot_matching(d, points, fname, title):
    """Matching diagram with the curves of design d; points = [(design, kind)] with
    kind "optimum" or "selected", each plotted at its installed T/W."""
    mc = d["mc"]
    WSr = mc["WS"]
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    env = np.zeros_like(WSr)
    for k, v in mc["tw"].items():
        cls = k.startswith("Cruise speed")
        ax.plot(WSr, v, lw=1.8 if cls else 1, c="k" if cls else None, label=k)
        env = np.maximum(env, v)
    ws_lim = min(mc["lims"].values())
    for k, v in mc["lims"].items():
        ax.axvline(v, ls="--", lw=1, c="0.35" if k == "Minimum speed" else "0.1", label=f"{k} ({v:,.0f})")
    ax.fill_between(WSr, env, 0.5, where=WSr <= ws_lim, color="#2ca02c", alpha=0.08,
                    label="feasible region")
    ax.axhline(d["tw_avail"], c="#d62728", ls=":", lw=1.2,
               label=f"2 × CF34-8E5 T/W available ({d['tw_avail']:.3f})")
    for p, kind in points:
        if p is not None and not (_MERGED and kind == "selected"):
            ax.plot(p["WS"], p["tw_avail"], label=_lab(p, kind),
                    **(OPT_KW if kind == "optimum" else SEL_KW))
    ax.set_xlim(3000, 6500); ax.set_ylim(0, 0.5)
    ax.set_xlabel("W/S [N/m²]"); ax.set_ylabel("T/W [-]"); ax.grid(alpha=0.3)
    ax.legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    ax.set_title(title, fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, fname), dpi=200); plt.close(fig)


def figures(rows, per_ar, opt, sel):
    global _MERGED
    _MERGED = _same(opt, sel)
    os.makedirs(OUT_DIR, exist_ok=True)
    all_ars = sorted({d["AR"] for d in rows})
    cols = dict(zip(all_ars, plt.cm.viridis(np.linspace(0.1, 0.85, len(all_ars)))))
    AR_main = sel["AR"] if sel is not None else opt["AR"]
    ARs = [opt["AR"]] + ([sel["AR"]] if sel is not None and sel["AR"] != opt["AR"] else [])

    # 1. MTOM vs W/S per AR, infeasible points hollow
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    for AR in all_ars:
        L, c = _line(rows, AR), cols[AR]
        ax.plot([d["WS"] for d in L], [d["MTOM"] for d in L], "-", color=c, lw=1.2, label=f"AR {AR}")
        ax.plot([d["WS"] for d in L if d["ok"]], [d["MTOM"] for d in L if d["ok"]], "o", color=c, ms=4)
        ax.plot([d["WS"] for d in L if not d["ok"]], [d["MTOM"] for d in L if not d["ok"]], "o",
                mfc="none", color=c, ms=4)
    _boundary(ax, per_ar, AR_main)
    _points(ax, opt, sel, "MTOM")
    ax.set_xlabel("W/S [N/m²]"); ax.set_ylabel("MTOM [kg]")
    ax.set_title("Converged MTOM (filled = feasible, hollow = violates a constraint)", fontsize=10)
    ax.grid(alpha=0.3); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "mtom_vs_ws.png"), dpi=200); plt.close(fig)

    # 2. L/D, C_L and design fuel vs W/S at the optimum and selected AR
    fig, axs = plt.subplots(1, 3, figsize=(13, 4.6))
    for AR in ARs:
        L = _line(rows, AR)
        ws = [d["WS"] for d in L]
        for a, key in zip(axs, ("LD", "C_L", "fuel_des")):
            a.plot(ws, [d[key] for d in L], "o-", ms=3, color=cols[AR], label=f"AR {AR}")
    axs[0].axhline(LD_MIN, ls="--", c="k", lw=0.8, label="REQ-WNG-EFF-02 (15.4)")
    for a, key, yl, t in zip(axs, ("LD", "C_L", "fuel_des"),
                             ("mid-cruise L/D", "mid-cruise C_L", "design-mission fuel [kg]"),
                             ("L/D", "Cruise lift coefficient", "Fuel burn")):
        _boundary(a, per_ar, AR_main, label=a is axs[0])
        _points(a, opt, sel, key)
        a.set_xlabel("W/S [N/m²]"); a.set_ylabel(yl); a.set_title(t); a.grid(alpha=0.3)
    fig.legend(*axs[0].get_legend_handles_labels(), loc="lower center", ncol=3, fontsize=7.5)
    fig.tight_layout(rect=(0, 0.13, 1, 1)); fig.savefig(os.path.join(OUT_DIR, "aero_vs_ws.png"), dpi=200); plt.close(fig)

    # 3. SAR vs W/S (all AR) and SAR vs cruise altitude (optimum and selected wings)
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.6))
    ax = axs[0]
    for AR in all_ars:
        L, c = _line(rows, AR), cols[AR]
        ax.plot([d["WS"] for d in L], [d["sar"] for d in L], "-", color=c, lw=1.2, label=f"AR {AR}")
        ax.plot([d["WS"] for d in L if d["ok"]], [d["sar"] for d in L if d["ok"]], "o", color=c, ms=4)
        ax.plot([d["WS"] for d in L if not d["ok"]], [d["sar"] for d in L if not d["ok"]], "o",
                mfc="none", color=c, ms=4)
    _boundary(ax, per_ar, AR_main)
    _points(ax, opt, sel, "sar")
    ax.set_xlabel("W/S [N/m²]"); ax.set_ylabel("mid-cruise SAR [m/kg]")
    ax.set_title("SAR at M 0.77, FL350 (hollow = violates a constraint)", fontsize=10)
    ax.grid(alpha=0.3); ax.legend(fontsize=7)
    ax = axs[1]
    for p, kw, what in ((opt, OPT_KW, "optimum"), (sel, SEL_KW, "selected")):
        if p is None or (_MERGED and what == "selected"):
            continue
        al = p["alt"]
        fl = al["h"] / 0.3048 / 100
        ax.plot(fl, np.where(al["ok"], al["sar"], np.nan), "-", color=kw["color"], lw=1.6,
                label=_lab(p, what))
        ax.plot(fl, np.where(al["ok"], np.nan, al["sar"]), ":", color=kw["color"], lw=1.4)
        ax.plot(fl[al["h"] == al["h_best_thrust"]], al["sar_best_thrust"], "o", color=kw["color"], ms=5)
        ax.plot(10668 / 0.3048 / 100, p["sar"], **kw)
    ax.axvline(350, c="k", ls="--", lw=0.8, label="cruise requirement FL350")
    ax.plot([], [], ":", c="0.4", label="dotted: CF34-8E5 thrust too low")
    ax.plot([], [], "o", c="0.4", ms=5, label="best SAR with thrust available")
    ax.set_xlabel("cruise altitude [FL]"); ax.set_ylabel("mid-cruise SAR [m/kg]")
    ax.set_title("SAR against cruise altitude, M 0.77, mid-cruise mass", fontsize=10)
    ax.grid(alpha=0.3); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "sar.png"), dpi=200); plt.close(fig)

    # 4. fuel volume needed vs available, at the selected AR
    L = _line(rows, AR_main)
    ws = [d["WS"] for d in L]
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    ax.plot(ws, [d["V_fuel"] for d in L], "o-", ms=3, c="k", label=f"fuel volume needed, AR {AR_main}")
    ax.plot(ws, [d["cap"]["wing"] for d in L], "--", label="wing tanks η 0.17–0.83")
    ax.plot(ws, [d["cap"]["wing"] + d["cap"]["centre_box"] for d in L], "-.", label="+ centre box")
    ax.plot(ws, [d["V_box"] + AUX_TANK for d in L], "-", label="+ inboard strip (+ aux)")
    if opt["AR"] != AR_main:
        Lo = _line(rows, opt["AR"])
        ax.plot([d["WS"] for d in Lo], [d["V_fuel"] for d in Lo], "-", c="0.6", lw=0.9,
                label=f"needed, AR {opt['AR']}")
        ax.plot([d["WS"] for d in Lo], [d["V_box"] + AUX_TANK for d in Lo], "-", c="0.6", lw=0.9, alpha=0.5,
                label=f"available, AR {opt['AR']}")
    _boundary(ax, per_ar, AR_main)
    _points(ax, opt, sel, "V_fuel")
    ax.set_xlabel("W/S [N/m²]"); ax.set_ylabel("usable volume [m³]"); ax.grid(alpha=0.3)
    ax.legend(fontsize=7); ax.set_title(f"Fuel volume, AR {AR_main}", fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "fuel_volume_vs_ws.png"), dpi=200); plt.close(fig)

    # 5. matching diagrams (Class II polar, MLM and HLD C_Lmax of each design)
    pts = [(opt, "optimum"), (sel, "selected")]
    plot_matching(opt, pts, "matching_diagram_optimum.png",
                  f"Matching diagram, curves of the optimum (AR {opt['AR']}, MLM/MTOM {opt['f_L']:.3f})")
    if sel is not None:
        plot_matching(sel, pts, "matching_diagram_selected.png",
                      f"Matching diagram, curves of the selected point (AR {sel['AR']}, "
                      f"MLM/MTOM {sel['f_L']:.3f})")


# ============================================================================
def _describe(d, title):
    co, al, wc = d["co"], d["alt"], d["wc"]
    return [
        f"{title}: W/S {d['WS']:,.0f} N/m^2, AR {d['AR']}",
        f"  MTOM {d['MTOM']:,.0f} kg, OEM {d['OEM']:,.0f} kg, S {d['S']:.2f} m^2, b {d['b']:.2f} m",
        f"  C_D0 {d['CD0']:.5f} (no wave {d['CD0_nw']:.5f}), e {d['e']:.4f}, mid-cruise C_L "
        f"{d['C_L']:.3f}, L/D {d['LD']:.2f}, M_DD {d['M_DD']:.3f}",
        f"  design-mission fuel {d['fuel_des']:,.0f} kg ({d['sar_block']:.0f} m/kg block, incl. reserves); "
        f"fuel capacity {d['fuel_cap']:,.0f} kg = {d['V_fuel']:.2f} m^3 vs wing box {d['V_box']:.2f} m^3 "
        f"(wing {d['cap']['wing']:.2f}, centre {d['cap']['centre_box']:.2f}, inboard {d['cap']['inboard']:.2f})",
        f"  SAR (mid-cruise, M 0.77, FL350) {d['sar']:.0f} m/kg at {d['W_mid'] / G0:,.0f} kg; best at "
        f"FL{al['h_best_thrust'] / 0.3048 / 100:.0f} with thrust available {al['sar_best_thrust']:.0f} m/kg "
        f"(thrust ceiling FL{al['ceiling'] / 0.3048 / 100:.0f}; unconstrained best "
        f"FL{al['h_best'] / 0.3048 / 100:.0f}, {al['sar_best']:.0f} m/kg)",
        f"  driving T/W {d['drv']} {d['tw_req']:.3f} vs available {d['tw_avail']:.3f} "
        f"({100 * d['margin']:+.0f} %); W/S limit {d['ws_max']:,.0f} (MLM/MTOM {d['f_L']:.3f})",
        f"  cruise optimum of this wing at M 0.77: C_L {co['CL_opt']:.3f} (L/D {co['LD_opt']:.2f}) vs "
        f"{d['C_L']:.3f} flown (L/D {co['LD_now']:.2f}); best mid-cruise altitude "
        f"{co['h_opt']:,.0f} m (FL{co['h_opt'] / 0.3048 / 100:.0f}) vs FL350",
        f"  WP2 wing: C_Lmax {wc['CLmax_clean']:.3f} / {wc['CLmax_TO']:.3f} / {wc['CLmax_L']:.3f} "
        f"(needed {wc['CL_req']:.3f}); flap for it to {wc['eta_flap_req']:.3f} b/2 (ailerons from "
        f"{WC.H.ail_eta_in} b/2); 20 deg roll in {wc['t20']:.2f} s at V_SR0 {wc['V_SR0']:.1f} m/s "
        f"({100 * wc['unused']:.0f} % travel unused); pb/2V {wc['helix']:.4f}; alpha at C_Lmax "
        f"{wc['alpha_max']:.1f} deg vs tail strike {WC.TAILSTRIKE:.0f} "
        f"({'OK' if wc['tailstrike_ok'] else 'exceeds, as in WP2'})",
        f"  status: {'all constraints met' if d['ok'] else 'FAILS ' + ', '.join(d['fails'])}",
    ]


def _margins(d, per_ar):
    """Margin of design d to every constraint (positive = inside)."""
    wc = d["wc"]
    DE = sys.modules["drag_estimator"]
    eta_flap_avail = wc["y_flap_out"] / (wc["b"] / 2)
    rows = [
        ("thrust (T/W available vs driving)", f"{d['tw_avail']:.3f} vs {d['tw_req']:.3f}", f"{100 * d['margin']:+.1f} %"),
        ("landing / minimum-speed W/S", f"{d['WS']:,.0f} vs {d['ws_max']:,.0f}", f"{100 * (d['ws_max'] / d['WS'] - 1):+.1f} %"),
        ("fuel volume [m^3]", f"{d['V_fuel']:.2f} vs {d['V_box'] + AUX_TANK:.2f}",
         f"{d['V_box'] + AUX_TANK - d['V_fuel']:+.2f} m^3"),
        ("L/D (REQ-WNG-EFF-02)", f"{d['LD']:.2f} vs {LD_MIN}", f"{d['LD'] - LD_MIN:+.2f}"),
        ("M_DD vs M_cruise", f"{d['M_DD']:.3f} vs {DE.M_cruise}", f"{d['M_DD'] - DE.M_cruise:+.3f}"),
        ("span [m]", f"{d['b']:.2f} vs {SPAN_MAX}", f"{SPAN_MAX - d['b']:+.2f} m"),
        ("REQ-HLD-01 C_Lmax landing", f"{wc['CLmax_L']:.3f} vs {max(wc['CL_req'], WC.CLMAX_L_MIN):.3f}",
         f"{wc['CLmax_L'] - wc['CL_req']:+.3f}"),
        ("REQ-HLD-02 C_Lmax take-off", f"{wc['CLmax_TO']:.3f} vs {WC.CLMAX_TO_MIN}",
         f"{wc['CLmax_TO'] - WC.CLMAX_TO_MIN:+.3f}"),
        ("REQ-RCS-01 flap span needed [b/2]", f"{wc['eta_flap_req']:.3f} vs {eta_flap_avail:.3f}",
         f"{eta_flap_avail - wc['eta_flap_req']:+.3f}"),
        ("REQ-RCS-02 20 deg roll time [s]", f"{wc['t20']:.2f} vs {WC.T_RCS02}", f"{WC.T_RCS02 - wc['t20']:+.2f} s"),
        ("REQ-RCS-03 aileron travel unused", f"{100 * wc['unused']:.0f} % vs 25 %", f"{100 * (wc['unused'] - 0.25):+.0f} %"),
        ("REQ-RCS-04 pb/2V", f"{wc['helix']:.4f} vs {WC.H.helix_req}", f"{wc['helix'] - WC.H.helix_req:+.4f}"),
    ]
    b, act = per_ar.get(d["AR"], (None, ""))
    lines = [f"  {'constraint':<36} {'value vs limit':>22} {'margin':>12}"]
    lines += [f"  {n:<36} {v:>22} {m:>12}" for n, v, m in rows]
    if b is not None:
        lines.append(f"  distance to the feasibility boundary at AR {d['AR']}: W/S {b['WS']:,.0f} "
                     f"({b['WS'] - d['WS']:+,.0f} N/m^2, first constraint hit: {act})")
    return lines


def summary(per_ar, opt, active, sel):
    ref = design(4202.0, 10.5)
    lines = [
        "WP3.4 optimiser (Class I <-> Class II, OEM method %s, fixed equipment %s, objective %s)"
        % (I.OEM_METHOD, sys.modules["class2_weight_estimation"].FIXED_EQUIPMENT_MODE, OBJECTIVE),
        "",
        "Optimum W/S per AR (feasibility boundary):",
        f"  {'AR':>5} {'W/S':>6} {'MTOM':>7} {'fuel':>6} {'S':>6} {'L/D':>6} {'SAR':>5}  active constraint",
    ]
    for AR, (d, act) in per_ar.items():
        lines.append(f"  {AR:5.1f}  {act}" if d is None else
                     f"  {AR:5.1f} {d['WS']:6,.0f} {d['MTOM']:7,.0f} {d['fuel_des']:6,.0f} {d['S']:6.2f} "
                     f"{d['LD']:6.2f} {d['sar']:5.0f}  {act}")
    lines += ["", *_describe(opt, f"OPTIMUM (active constraint: {active})")]
    if sel is not None:
        lines += ["", *_describe(sel, "SELECTED DESIGN POINT"), "  margins:", *_margins(sel, per_ar),
                  f"  cost of the margin vs the optimum: MTOM {sel['MTOM'] - opt['MTOM']:+,.0f} kg "
                  f"({100 * (sel['MTOM'] / opt['MTOM'] - 1):+.1f} %), design fuel "
                  f"{sel['fuel_des'] - opt['fuel_des']:+,.0f} kg ({100 * (sel['fuel_des'] / opt['fuel_des'] - 1):+.1f} %), "
                  f"SAR {sel['sar'] - opt['sar']:+.0f} m/kg ({100 * (sel['sar'] / opt['sar'] - 1):+.1f} %), "
                  f"S {sel['S'] - opt['S']:+.1f} m^2"]
    lines += ["", f"Reference W/S 4,202 / AR 10.5 (same settings): MTOM {ref['MTOM']:,.0f} kg, fuel "
                  f"{ref['fuel_des']:,.0f} kg, SAR {ref['sar']:.0f} m/kg, S {ref['S']:.1f} m^2"]
    txt = "\n".join(lines)
    print("\n" + txt)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "optimum_summary.txt"), "w") as f:
        f.write(txt + "\n")


def main():
    rows = sweep()
    ars = list(AR_GRID)
    if SELECTED is not None and SELECTED["AR"] not in ars:
        ars.append(SELECTED["AR"])       # boundary of the selected AR is needed for its margins
        rows += [design(WS, SELECTED["AR"]) for WS in WS_GRID]
    per_ar = {AR: refine(rows, AR) for AR in ars}
    opt, active = min(((d, a) for d, a in per_ar.values() if d is not None), key=lambda t: _obj(t[0]))
    if opt["AR"] in (min(AR_GRID), max(AR_GRID)):
        active += f"; AR at the edge of AR_GRID ({opt['AR']}{', the AR limit' if opt['AR'] >= AR_MAX else ''})"
    opt = evaluate_point(opt["WS"], opt["AR"])
    sel = evaluate_point(SELECTED["WS"], SELECTED["AR"]) if SELECTED is not None else None
    figures(rows, per_ar, opt, sel)
    summary(per_ar, opt, active, sel)


if __name__ == "__main__":
    main()
