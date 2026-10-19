"""
First-pass geometry for the Class II drag build-up (WP3.4, Group A11).

The ADSEE-II component build-up (lecture "Estimation of Lift & Drag", slides 55-65)
needs, besides the fuselage:
  * wing exposed area                      -> S_wet,w = 1.07*2*S_exp,w
  * horizontal / vertical tail areas       -> S_wet = 1.05*2*S_exp, FF needs t/c, (x/c)_m, sweep
  * nacelle length and max. diameter       -> S_wet, fineness f = l/d, FF = 1 + 0.35/f
These are not known yet, so this script produces them with the ADSEE-I method of
R. Vos, "Airplane Design and Analysis" (course textbook):
  1. nacelle size from the engine mass flow            (Sec. 8.3.1, eqs 8.22-8.35)
  2. engine position on the wing                       (Sec. 8.3.2, Example 8.15)
  3. group mass fractions -> X_LEMAC -> loading diagram (Sec. 9.1, eqs 9.1-9.13)
  4. tail areas from tail-volume coefficients          (Sec. 9.3, eqs 9.33-9.43)
  5. exposed and wetted areas for the drag build-up    (lecture slide 57)

Everything that is a choice or a placeholder sits in the INPUT block. Replace the
FUSELAGE block with the group's own fuselage data. Run:  python drag_geometry_inputs.py
"""
import math

# ============================================================================
# INPUT BLOCK
# ============================================================================
# --- Mass basis: Class II loop (class2_iteration.py, Torenbeek) at W/S 4,800 N/m^2 ---
# (was the WP3.1 re-sizing at W/S 4,202: MTOM 30,845, OEM 0.6256, fuel 5,042, S 72.0)
MTOM = 31633.0          # kg
OEM_FRAC = 0.6149       # OEM/MTOM, Torenbeek Class II OEM (per-system fixed equipment)
M_PAYLOAD_MAX = 9302.0  # kg, maximum structural payload (harmonic point)
M_FUEL_MAX = 5778.0     # kg, largest fuel load over the missions (MTOM + full fuel)

# --- Wing (WP2 planform, scaled to S) ----------------------------------------
S_W = 64.63             # m^2 (MTOM g / 4,800)
AR_W = 10.5
TAPER_W = 0.316
SWEEP_LE_W = 26.34      # deg
SWEEP_C4_W = 24.02      # deg
FRONT_SPAR = 0.20       # x/c of front spar (Vos Example 8.15)

# --- Fuselage: group preliminary sizing (Akos, 2026-10-14) -----------------------
L_FUS = 34.00           # m, total length
D_FUS = 2.926           # m, outer diameter (inner 2.72, wall 0.103)
L_NOSE = 4.97           # m, nose cone l_nc (fineness 1.7) = L1 in slide 57
L_TAIL = 8.78           # m, tail cone l_tc (fineness 3.0) = L3 in slide 57
X_CABIN_CENTRE = (3.50 + 25.10) / 2   # m from nose, payload CG = cabin centre
D_TAILCONE_AT_HT = 1.13 # m, cone diameter at 0.9 l_fus (cone from 25.22 m, linear taper)
UPSWEEP_DEG = 6.0       # ASSUMED deg, aft-fuselage (tail-cone) upsweep; used by the drag
                        # estimator (upsweep drag) and the three-view (Vos: 4-5 deg)

# --- Engine: GE CF34-8E5 -------------------------------------------------------
N_ENG = 2
T_TO_ENG = 59.70e3      # N, normal take-off thrust per engine (EASA TCDS IM.E.053)
BPR = 5.0
TT4 = 1500.0            # K, turbine inlet temperature (choice; see note in output)
ETA_NOZ = 0.97          # Vos: 0.97-0.99
ETA_TF = 0.75           # Vos: typical
NACELLE_TYPE = "C"      # "B" (long duct, mixed) or "C" (short fan cowl)
PHI = 0.75              # fan-cowl fraction l_f/l_n (Type C, 0.5-0.8)
ENG_SPAN_FRAC = 0.35    # 2*y_e/b, one engine per wing half (Vos 8.3.2)

# --- Group mass fractions (Vos Example 9.1: DC-9-30, MD-80, B737-200) -----------
# Replace with regional-jet references (Roskam Part V) for Assignment 9.1.
GROUPS_REF = {          # mass / MTOM of the reference aircraft
    "eng":  0.075, "fe": 0.162, "wing": 0.103, "tail": 0.025,
    "fus":  0.108, "nac": 0.013, "lg": 0.038,
}
OEM_FRAC_REF = 0.553    # OEM/MTOM of the same references (average)

# --- CG choices (Vos Sec. 9.1) -----------------------------------------------
X_OEM_CG_MAC = 0.25     # chosen OEM CG, fraction of MAC (typical 0.15-0.30)
X_FUEL_CG_MAC = 0.15    # fuel CG, fraction of MAC (Vos Example 9.3; check with tank layout)

# --- Tails (Vos Sec. 9.3), conventional low tail ------------------------------
X_AC_TAIL_FRAC = 0.90   # tail aerodynamic centres at 0.9 l_fus (Vos Examples 9.8/9.9)
VBAR_H = 1.00           # jet transports 0.54-1.48 (Vos eq 9.40)
VBAR_V = 0.085          # jet transports 0.038-0.120 (Vos eq 9.35)
AR_H, TAPER_H, SWEEP_C4_H = 4.0, 0.40, 30.0   # 3-5, 0.3-1, >= wing sweep
AR_V, TAPER_V, SWEEP_LE_V = 1.6, 0.35, 40.0   # 1-2, 0.3-0.7, wing LE sweep - 50 deg
TC_H, TC_V = 0.10, 0.10  # assumed symmetric sections (NACA 0010), (x/c)_m = 0.30
XC_M_TAIL = 0.30

# ============================================================================
RHO0, A0, G = 1.225, 340.3, 9.80665


def trapezoid(S, A, taper):
    b = math.sqrt(S * A)
    cr = 2 * S / (b * (1 + taper))
    ct = taper * cr
    mac = 2 / 3 * cr * (1 + taper + taper ** 2) / (1 + taper)
    y_mac = b / 6 * (1 + 2 * taper) / (1 + taper)
    return b, cr, ct, mac, y_mac


def chord_at(y, b, cr, ct):
    return cr - (cr - ct) * y / (b / 2)


def sweep_at(sweep_ref_deg, x_ref, x_new, A, taper):
    """Sweep at chord fraction x_new from sweep at x_ref (straight-tapered)."""
    t = math.tan(math.radians(sweep_ref_deg)) - 4 / A * (x_new - x_ref) * (1 - taper) / (1 + taper)
    return math.degrees(math.atan(t))


def nacelle():
    """Vos Sec. 8.3.1, eqs 8.22-8.35 (after Torenbeek & Berenschot)."""
    Gf = TT4 / 600 - 1.25                                              # (8.23)
    mdot = (N_ENG * T_TO_ENG) / (N_ENG * A0) * (1 + BPR) / math.sqrt(
        5 * ETA_NOZ * Gf * (1 + ETA_TF * BPR))                         # (8.22), per engine
    q = mdot / (RHO0 * A0)
    ds_di = 0.05 * (1 + 0.1 * RHO0 * A0 / mdot + 3 * BPR / (1 + BPR))  # (8.24)
    Di = 1.65 * math.sqrt((q + 0.005) / (1 - ds_di ** 2))              # (8.25)
    Cl, dl = (9.8, 0.05) if NACELLE_TYPE == "B" else (7.8, 0.10)
    phi = 1.0 if NACELLE_TYPE == "B" else PHI
    ln = Cl * (math.sqrt(q * (1 + 0.2 * BPR) / (1 + BPR)) + dl)        # (8.27)
    lf = phi * ln                                                      # (8.28)
    Dn = Di + 0.06 * phi * ln + 0.03                                   # (8.29)
    Def = Dn * (1 - phi ** 2 / 3)                                      # (8.30)
    out = dict(mdot=mdot, Di=Di, ln=ln, lf=lf, Dn=Dn, Def=Def)
    if NACELLE_TYPE == "C":
        lg = (1 - phi) * ln                                            # (8.31)
        Dg = Def * ((0.089 * q * BPR + 4.5) / (0.067 * q * BPR + 5.8)) ** 2  # (8.32)
        Deg = 0.55 * Dg                                                # (8.33)
        Dc = 0.55 * Deg                                                # (8.34)
        lc = 1.5 * Dc                                                  # (8.35)
        out.update(lg=lg, Dg=Dg, Deg=Deg, Dc=Dc, lc=lc)
        # wetted area: fan cowl (inlet->max->exit) + exposed core cowl + plug, as frustums
        swet = (math.pi * lf * (Di + 2 * Dn + Def) / 4      # fan cowl, approx. mean diameter
                + math.pi * lg * (Dg + Deg) / 2             # core cowl
                + math.pi * Dc / 2 * math.hypot(lc, Dc / 2))  # cone
    else:
        swet = math.pi * ln * (Di + 2 * Dn + Def) / 4
    out["swet"] = swet
    out["f"] = ln / Dn
    return out


def fuselage_swet(D, L1, L2, L3):
    """Lecture slide 57."""
    return math.pi * D / 4 * (1 / (3 * L1 ** 2) * ((4 * L1 ** 2 + D ** 2 / 4) ** 1.5 - D ** 3 / 8)
                              - D + 4 * L2 + 2 * math.sqrt(L3 ** 2 + D ** 2 / 4))


def exposed_area(S, b, cr, ct, d):
    """Planform area outboard of a body of width d (both halves)."""
    c_side = chord_at(d / 2, b, cr, ct)
    return 2 * (b / 2 - d / 2) * (c_side + ct) / 2


def compute():
    """All derived geometry, returned as a dict (used by three_view_drawing.py)."""
    b, cr, ct, mac, y_mac = trapezoid(S_W, AR_W, TAPER_W)
    tanLE = math.tan(math.radians(SWEEP_LE_W))
    nac = nacelle()

    # ---- engine position on the wing (Vos Example 8.15) ----
    y_e = ENG_SPAN_FRAC * b / 2
    x_le_eng = (y_e - y_mac) * tanLE                  # local LE relative to LEMAC
    x_fs = x_le_eng + FRONT_SPAR * chord_at(y_e, b, cr, ct)
    x_highlight = x_fs - 0.9 * nac["ln"]              # inlet 0.9 l_n ahead of front spar
    x_eng_cg = x_highlight + 0.4 * nac["ln"]          # engine+nacelle CG at 0.4 l_n

    # ---- group masses (Vos eqs 9.1-9.3) ----
    avg = {k: OEM_FRAC * v / OEM_FRAC_REF for k, v in GROUPS_REF.items()}  # (9.1), one ref set
    m = avg  # unaccounted fraction is zero after normalisation (9.2-9.4)
    # fuselage assembly: fus + fixed equipment + tail (landing gear neglected, Vos p. 234)
    mFA = m["fus"] + m["fe"] + m["tail"]
    X_FA = (0.4 * L_FUS * (m["fus"] + m["fe"]) + 0.9 * L_FUS * m["tail"]) / mFA      # (9.6)
    # wing assembly: wing + engines + nacelles (under-wing engines)
    mWA = m["wing"] + m["eng"] + m["nac"]
    x_WA = (0.4 * mac * m["wing"] + x_eng_cg * (m["eng"] + m["nac"])) / mWA         # (9.8)
    X_LEMAC = X_FA + mac * ((x_WA / mac) * mWA / mFA
                            - X_OEM_CG_MAC * (1 + mWA / mFA))                       # (9.9)
    X_OEM = X_LEMAC + mac * X_OEM_CG_MAC                                            # (9.10)

    # ---- loading diagram (Vos eqs 9.12-9.13) ----
    X_F = X_LEMAC + mac * X_FUEL_CG_MAC
    items = {"OEM": (OEM_FRAC * MTOM, X_OEM), "pl": (M_PAYLOAD_MAX, X_CABIN_CENTRE),
             "f": (M_FUEL_MAX, X_F)}

    def cg(*keys):
        ms = sum(items[k][0] for k in keys)
        return sum(items[k][0] * items[k][1] for k in keys) / ms

    cases = {"OEM": cg("OEM"), "OEM+pl": cg("OEM", "pl"),
             "OEM+pl+f": cg("OEM", "pl", "f"), "OEM+f": cg("OEM", "f")}
    X_aft = max(cases.values())
    X_fwd = min(cases.values())

    # ---- tails (Vos eqs 9.33-9.43) ----
    X_ac_t = X_AC_TAIL_FRAC * L_FUS
    l_h = l_v = X_ac_t - X_aft
    S_h = VBAR_H * S_W * mac / l_h                                                  # (9.39)
    S_v = VBAR_V * S_W * b / l_v                                                    # (9.34)
    b_h, cr_h, ct_h, mac_h, _ = trapezoid(S_h, AR_H, TAPER_H)
    # vertical tail: one surface, "span" = height, A_v = b_v^2/S_v
    b_v = math.sqrt(AR_V * S_v)
    cr_v = 2 * S_v / (b_v * (1 + TAPER_V))
    ct_v = TAPER_V * cr_v
    mac_v = 2 / 3 * cr_v * (1 + TAPER_V + TAPER_V ** 2) / (1 + TAPER_V)

    # ---- exposed and wetted areas (slide 57) ----
    S_exp_w = exposed_area(S_W, b, cr, ct, D_FUS)
    S_exp_h = exposed_area(S_h, b_h, cr_h, ct_h, D_TAILCONE_AT_HT)
    S_exp_v = S_v                       # area defined above the tail-cone curve (Vos Fig 9.11)
    L2 = L_FUS - L_NOSE - L_TAIL
    swet = {"wing": 1.07 * 2 * S_exp_w, "HT": 1.05 * 2 * S_exp_h, "VT": 1.05 * 2 * S_exp_v,
            "fuselage": fuselage_swet(D_FUS, L_NOSE, L2, L_TAIL),
            "nacelles (2)": N_ENG * nac["swet"]}

    # max-thickness-line sweeps for the form factor
    sw_m_w = sweep_at(SWEEP_LE_W, 0.0, 0.37, AR_W, TAPER_W)   # SC(2)-0612 max t at ~37 % c
    sw_m_h = sweep_at(SWEEP_C4_H, 0.25, XC_M_TAIL, AR_H, TAPER_H)
    sw_m_v = sweep_at(SWEEP_LE_V, 0.0, XC_M_TAIL, 2 * AR_V, TAPER_V)  # full-span equivalent

    return {k: v for k, v in locals().items() if k != 'cg'}


def _report(nac, b, cr, ct, mac, y_mac, y_e, x_highlight, x_eng_cg, m, mFA, X_FA, mWA, x_WA, X_LEMAC, X_OEM, cases, X_fwd, X_aft, l_h, X_ac_t, S_h, b_h, cr_h, ct_h, mac_h, S_v, b_v, cr_v, ct_v, mac_v, S_exp_w, S_exp_h, S_exp_v, swet, sw_m_w, sw_m_h, sw_m_v, **_):
    p = print
    p("=== 1. Nacelle, CF34-8E5 (Vos 8.3.1, Type %s, phi %.2f, Tt4 %.0f K) ===" % (NACELLE_TYPE, PHI, TT4))
    p("  mass flow per engine        %7.1f kg/s" % nac["mdot"])
    p("  inlet/highlight diameter Di %7.2f m   (real CF34-8E fan: 1.17 m)" % nac["Di"])
    p("  nacelle length l_n          %7.2f m   fan cowl l_f %.2f m" % (nac["ln"], nac["lf"]))
    p("  max diameter D_n            %7.2f m   fineness l_n/D_n %.2f" % (nac["Dn"], nac["f"]))
    if NACELLE_TYPE == "C":
        p("  core cowl l_g %.2f m, D_g %.2f m, D_eg %.2f m; plug D_c %.2f m, l_c %.2f m"
          % (nac["lg"], nac["Dg"], nac["Deg"], nac["Dc"], nac["lc"]))
    p("  wetted area per nacelle     %7.2f m^2" % nac["swet"])
    p("\n=== 2. Wing and engine position ===")
    p("  b %.2f m, c_r %.3f m, c_t %.3f m, MAC %.3f m at y %.2f m" % (b, cr, ct, mac, y_mac))
    p("  engine at y %.2f m; highlight %.2f m, engine CG %.2f m from LEMAC" % (y_e, x_highlight, x_eng_cg))
    p("\n=== 3. CG and wing position (Vos 9.1) ===")
    for k in ("eng", "fe", "wing", "tail", "fus", "nac", "lg"):
        p("  m_%-5s/MTOM %.4f" % (k, m[k]))
    p("  fuselage assembly %.3f MTOM, X_FACG %.2f m" % (mFA, X_FA))
    p("  wing assembly     %.3f MTOM, x_WACG %.2f m from LEMAC" % (mWA, x_WA))
    p("  X_LEMAC %.2f m (%.2f l_fus), X_OEM %.2f m" % (X_LEMAC, X_LEMAC / L_FUS, X_OEM))
    for k, v in cases.items():
        p("  %-9s X %.2f m  = %.2f MAC" % (k, v, (v - X_LEMAC) / mac))
    p("  forward CG %.2f MAC, aft CG %.2f MAC" % ((X_fwd - X_LEMAC) / mac, (X_aft - X_LEMAC) / mac))
    p("\n=== 4. Tails (Vos 9.3) ===")
    p("  tail arm l_h = l_v = %.2f m (tail AC at %.2f m)" % (l_h, X_ac_t))
    p("  HT: S_h %.2f m^2, b %.2f, c_r %.2f, c_t %.2f, MAC %.2f m, sweep c/4 %.0f deg, t/c %.2f"
      % (S_h, b_h, cr_h, ct_h, mac_h, SWEEP_C4_H, TC_H))
    p("  VT: S_v %.2f m^2, h %.2f, c_r %.2f, c_t %.2f, MAC %.2f m, sweep LE %.0f deg, t/c %.2f"
      % (S_v, b_v, cr_v, ct_v, mac_v, SWEEP_LE_V, TC_V))
    p("\n=== 5. Inputs for the drag build-up ===")
    p("  S_exp wing %.2f, HT %.2f, VT %.2f m^2" % (S_exp_w, S_exp_h, S_exp_v))
    for k, v in swet.items():
        p("  S_wet %-13s %7.2f m^2" % (k, v))
    p("  total S_wet %.1f m^2, S_wet/S %.2f" % (sum(swet.values()), sum(swet.values()) / S_W))
    p("  sweep of max-thickness line: wing %.1f, HT %.1f, VT %.1f deg" % (sw_m_w, sw_m_h, sw_m_v))
    p("  characteristic lengths for Re: wing MAC %.2f, HT MAC %.2f, VT MAC %.2f, "
      "fuselage %.2f, nacelle %.2f m" % (mac, mac_h, mac_v, L_FUS, nac["ln"]))


def main():
    _report(**compute())


if __name__ == "__main__":
    main()
