"""
WP2 wing checks (high-lift devices and ailerons) for any wing size and aspect ratio,
using the group's hld_aileron_sizing.py (Lecture 2 DATCOM, Lecture 3 HLD and aileron
method) with its inputs unchanged: same airfoil, device types, chord ratios and
spanwise fractions. The HLD inboard end stays at fuselage radius + root clearance.

check(S, AR, WS, f_L) returns the C_Lmax values (clean / take-off / landing), the
angles at C_Lmax and the WP2 requirements:
  REQ-HLD-01/02  C_Lmax landing >= 2.60, take-off >= 2.10 (WP1 values); the landing
                 C_Lmax the matching diagram needs at this W/S is reported as well
  REQ-RCS-01     flap ends inboard of the aileron and the flap span needed for
                 C_Lmax,L,req fits there
  REQ-RCS-02     CS 25.149(h)(4): 20 deg roll in <= 5 s at V_MCL, checked at the lower
                 bound V_SR0 (landing config, MLM), first-order response tau_R = 1.4 s
                 (WP2-final form)
  REQ-RCS-03     >= 25 % of the effective aileron travel unused at the RCS-02 condition
  REQ-RCS-04     steady roll helix pb/(2V) >= 0.07
  tail strike    angle at C_Lmax (linear estimate) vs 16 deg -- reported, not a
                 constraint (it already exceeded 16 deg in WP2: 17.7 deg)
  info           group WP2 claim 30 deg in 1.5 s at V_roll of hld_aileron_sizing.py

Run:  python wing_checks.py   (prints the checks at the current design point)
"""
import math
import os

import drag_geometry_inputs as G
import hld_aileron_sizing as H

HERE = os.path.dirname(os.path.abspath(__file__))
RHO0 = 1.225
S_LANDING, V_APPROACH = 1210.0, 64.0   # WP1 requirements (m, m/s)
CLMAX_L_MIN, CLMAX_TO_MIN = 2.60, 2.10 # REQ-HLD-01 / 02
TAU_R = 1.4                            # s, roll-mode time constant (MIL-F-8785C Level 1, Class II-L)
PHI_RCS02, T_RCS02 = 20.0, 5.0         # deg, s (CS 25.149(h)(4))
UNUSED_RCS03 = 0.25                    # fraction of effective aileron travel left unused
TAILSTRIKE = H.tailstrike_deg

_DY = None


def _delta_y():
    global _DY
    if _DY is None:
        path = H.airfoil_dat if os.path.isabs(H.airfoil_dat) else os.path.join(HERE, H.airfoil_dat)
        if not os.path.isfile(path):
            path = os.path.join(HERE, "..", "wp2-final", "code", "NASA SC2-0612 AIRFOIL.dat")
        _DY = H.delta_y_from_dat(path)
    return _DY


def planform(S, AR, taper=None, sweep_LE=None):
    taper = G.TAPER_W if taper is None else taper
    sweep_LE = G.SWEEP_LE_W if sweep_LE is None else sweep_LE
    b = math.sqrt(AR * S)
    cr = 2 * S / (b * (1 + taper))
    sweep_c4 = G.sweep_at(sweep_LE, 0.0, 0.25, AR, taper)
    return H.Planform(b, S, cr, taper * cr, sweep_c4)


def check(S, AR, WS, f_L, d_fus=None):
    """WP2 wing checks for wing area S, aspect ratio AR, wing loading WS (MTOM) and
    landing mass fraction f_L = MLM/MTOM."""
    d_fus = G.D_FUS if d_fus is None else d_fus
    pf = planform(S, AR)

    # ---- clean wing (DATCOM) ----
    CLa = H.CLa_datcom(H.cla_airfoil, pf.AR, H.M_low, H.eta_airfoil, pf.sweep(0.5))
    dat = H.datcom_clean(pf, H.clmax_airfoil, _delta_y(), CLa, H.alpha0L_clean)
    CLmax_c = dat["CLmax"]

    # ---- HLDs (same logic as hld_aileron_sizing.main) ----
    name, curve = H.TORENBEEK[H.TE_type]
    cf_c = H.TE_cf_c
    c_ext_L = 1 + H.interp_table(curve, H.TE_delta_f_landing, "landing deflection") * cf_c
    c_ext_TO = 1 + H.interp_table(curve, H.TE_delta_f_takeoff, "take-off deflection") * cf_c
    y_in = d_fus / 2 + H.root_clearance
    y1_ail, y2_ail = H.ail_eta_in * pf.half, H.ail_eta_out * pf.half
    y_flap_out = y1_ail - H.gap_flap_ail
    te = H.HLD(H.TE_type, y_in, y_flap_out, c_ext_L, 1 - cf_c, H.TO_fraction_TE)
    le = H.HLD(H.LE_type, y_in, H.LE_eta_out * pf.half, H.LE_c_ext, H.LE_hinge_xc, H.TO_fraction_LE)
    ph = {}
    for phase, da0l, c_s in (("landing", H.dalpha0l_landing, None),
                             ("takeoff", H.dalpha0l_takeoff, c_ext_TO)):
        rt = te.evaluate(pf, phase, da0l, c_s)
        rl = le.evaluate(pf, phase, da0l)
        S_ratio = (pf.S + rt["dS"] + (rl["dS"] if H.slat_in_slope else 0.0)) / pf.S
        CLmax = CLmax_c + rt["dCLmax"] + rl["dCLmax"]
        alpha = H.alpha0L_clean + rt["dalpha0L"] + math.degrees(CLmax / (S_ratio * CLa))
        ph[phase] = dict(CLmax=CLmax, alpha=alpha, dCL_LE=rl["dCLmax"])
    CLmax_L, CLmax_TO = ph["landing"]["CLmax"], ph["takeoff"]["CLmax"]

    # C_Lmax the matching diagram needs at this W/S (landing field length, approach speed)
    CL_req_land = f_L * WS / (RHO0 / 2 * S_LANDING / 0.45)
    CL_req_app = f_L * WS / (0.5 * RHO0 * (V_APPROACH / 1.23) ** 2)
    CL_req = max(CL_req_land, CL_req_app, CLMAX_L_MIN)
    _, _, y_req = H.required_te_span(pf, te, CL_req, CLmax_c, ph["landing"]["dCL_LE"], "landing")

    # ---- ailerons ----
    tau = H.tau_user if H.tau_user is not None else H.tau_from_graph(H.ca_c)
    da_eff = 0.5 * (H.da_up_max + H.da_up_max / H.up_down_ratio)            # deg
    Cl_da, Cl_p = H.aileron_derivatives(pf, y1_ail, y2_ail, tau, H.cla_airfoil, H.cd0_airfoil)
    helix_per_rad = -Cl_da / Cl_p                                            # pb/2V per rad aileron
    helix = helix_per_rad * math.radians(da_eff)
    V_SR0 = math.sqrt(2 * f_L * WS / (RHO0 * CLmax_L))
    p_req = math.radians(PHI_RCS02) / (T_RCS02 - TAU_R)                      # rad/s
    helix_req02 = p_req * pf.b / (2 * V_SR0)
    da_req02 = math.degrees(helix_req02 / helix_per_rad)
    p_max = helix * 2 * V_SR0 / pf.b
    t20 = TAU_R + math.radians(PHI_RCS02) / p_max
    unused = 1 - da_req02 / da_eff
    phi30, t30req = H.ROLL_REQ[H.roll_class]
    t30, *_ = H.roll_time(pf, y1_ail, y2_ail, tau, H.cla_airfoil, H.cd0_airfoil,
                          math.radians(da_eff), H.V_roll, phi30)

    alpha_max = max(p["alpha"] for p in ph.values())
    fails = []
    if CLmax_L < CLMAX_L_MIN:
        fails.append("HLD-01")
    if CLmax_TO < CLMAX_TO_MIN:
        fails.append("HLD-02")
    if y_flap_out <= y_in or y_req is None or y_req > y_flap_out:
        fails.append("RCS-01")
    if t20 > T_RCS02:
        fails.append("RCS-02")
    if unused < UNUSED_RCS03:
        fails.append("RCS-03")
    if helix < H.helix_req:
        fails.append("RCS-04")
    return dict(b=pf.b, cr=pf.cr, ct=pf.ct, sweep_c4=pf.sweep(0.25), CLa=CLa,
                CLmax_clean=CLmax_c, CLmax_TO=CLmax_TO, CLmax_L=CLmax_L,
                alpha_TO=ph["takeoff"]["alpha"], alpha_L=ph["landing"]["alpha"], alpha_max=alpha_max,
                tailstrike_ok=alpha_max < TAILSTRIKE,
                CL_req=CL_req, CL_req_land=CL_req_land, CL_req_app=CL_req_app,
                y_in=y_in, y_flap_out=y_flap_out, y_flap_req=y_req, eta_flap_req=(y_req or 0) / pf.half,
                tau=tau, Cl_da=Cl_da, Cl_p=Cl_p, helix=helix, V_SR0=V_SR0, t20=t20,
                da_req02=da_req02, da_eff=da_eff, unused=unused, t30=t30, t30_req=t30req,
                V_roll=H.V_roll, fails=fails, ok=not fails)


def report(c, label=""):
    print(f"WP2 wing checks {label}")
    print(f"  planform b {c['b']:.2f} m, c_r {c['cr']:.3f}, c_t {c['ct']:.3f}, sweep c/4 {c['sweep_c4']:.2f} deg, "
          f"HLD inboard end {c['y_in']:.3f} m")
    print(f"  C_Lmax clean {c['CLmax_clean']:.3f}, take-off {c['CLmax_TO']:.3f} (REQ-HLD-02 >= {CLMAX_TO_MIN}), "
          f"landing {c['CLmax_L']:.3f} (REQ-HLD-01 >= {CLMAX_L_MIN}; matching diagram needs "
          f"{c['CL_req']:.3f} at this W/S)")
    print(f"  RCS-01: flap {c['y_in']:.2f}-{c['y_flap_out']:.2f} m, span needed for C_L {c['CL_req']:.3f} ends at "
          f"{(c['y_flap_req'] or float('nan')):.2f} m ({c['eta_flap_req']:.3f} b/2)")
    print(f"  RCS-02: V_SR0 {c['V_SR0']:.1f} m/s, 20 deg in {c['t20']:.2f} s (<= 5 s), needs "
          f"{c['da_req02']:.1f} of {c['da_eff']:.2f} deg; RCS-03: {100 * c['unused']:.0f} % travel unused (>= 25 %)")
    print(f"  RCS-04: pb/2V {c['helix']:.4f} (>= {H.helix_req}); info: 30 deg in {c['t30']:.2f} s at "
          f"V_roll {c['V_roll']:.0f} m/s ({c['t30_req']} s, group WP2 claim)")
    print(f"  alpha at C_Lmax (linear): take-off {c['alpha_TO']:.1f}, landing {c['alpha_L']:.1f} deg vs tail strike "
          f"{TAILSTRIKE:.0f} deg -> {'OK' if c['tailstrike_ok'] else 'exceeds (as in WP2)'}")
    print(f"  -> {'all WP2 wing requirements met' if c['ok'] else 'FAILS ' + ', '.join(c['fails'])}")


if __name__ == "__main__":
    import class2_weight_estimation as C2
    f_L = C2.W_L / G.MTOM
    WS = G.MTOM * G.G / G.S_W
    report(check(67.95, 10.5, 4202.0, f_L, d_fus=3.0), "(WP2 report wing: S 67.95, d_fus 3.0, W/S 4,202)")
    print()
    report(check(G.S_W, G.AR_W, WS, f_L), f"(current design: S {G.S_W:.2f}, AR {G.AR_W}, W/S {WS:,.0f})")
