"""
WP3.4 report values: every number quoted in the WP3.4 chapter (report/chapters/
wp3_4_final_concept.tex), written to report/generated/:

  wp3_4_values.tex        \\newcommand for each number used in the text
  wp3_4_iteration.tex     Class I <-> Class II iteration history (WP3.1 point -> final)
  wp3_4_params.tex        parameter table (WP2.4 table extended with the WP3.1 systems):
                          before the iteration vs final concept
  wp3_4_engine_req.tex    REQ-ENG-01..08 thrust per engine at the final point
  wp3_4_margins.tex       margins of the final point to every constraint
  wp3_4_per_ar.tex        constraint-bound optimum per aspect ratio
  wp3_4_compliance.tex    compliance matrix, WP1 + WP2 + WP3 requirements

and copies the optimiser and three-view figures to report/figures/.

"Before iteration" is the WP3.1 engine-selection point: W/S 4,202 N/m^2 (group WP2
report), MTOM 30,845 kg re-sized for the CF34-8E5 (Class I), with the Torenbeek Class II
masses and the Class II drag evaluated once at that geometry. "Final" is the selected
point of wp3_4_optimiser.py (SELECTED).

Run:  python wp3_4_report_values.py      (same folder as the other WP3 scripts)
"""
import math
import os
import shutil
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "..", "knowledge")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import wp3_4_optimiser as O            # noqa: E402
import three_view_drawing as TV        # noqa: E402

I, G, WC, W1 = O.I, O.G, O.WC, O.W1
H = WC.H
G0 = 9.80665
OUT = os.path.join(HERE, "report", "generated")
FIG = os.path.join(HERE, "report", "figures")

# WP3.1 engine-selection point (report Table 2.5): before the WP3.4 iteration
WS_B, MTOM_B, OEMF_B, FUEL_B = 4202.0, 30845.0, 0.6256, 5042.0
AR_B = 10.5                             # WP2 / WP3.1 aspect ratio
WS_F, AR = O.SELECTED["WS"], O.SELECTED["AR"]
T_ENG = O.T_AVAIL
LBF = 4.44822


def n(x, d=0):
    """Number with the LaTeX thousands separator."""
    s = f"{x:,.{d}f}"
    return s.replace(",", "{,}")


# ============================================================================
# Snapshot of every module at the current state
# ============================================================================
def snapshot(WS, MTOM, OEM, fuel, r):
    C2 = sys.modules["class2_weight_estimation"]
    DE = sys.modules["drag_estimator"]
    g = G.compute()
    S = G.S_W
    wc = WC.check(S, G.AR_W, WS, C2.W_L / G.MTOM)
    tv = TV.build()
    pf = WC.planform(S, G.AR_W)
    cap = I.tank_capacity(S)
    tor = {k: v[0] for k, v in C2.results.items()}
    fe_tot, fe_items, _ = C2.fixed_eq[0]
    half = g["b"] / 2
    y_flap_out = wc["y_flap_out"]
    y_slat_out = H.LE_eta_out * half
    S_wf_flap = 2 * pf.area(wc["y_in"], y_flap_out)
    S_wf_slat = 2 * pf.area(wc["y_in"], y_slat_out)
    W_mid = r["C_L"] * DE.q_cruise * S
    return dict(
        WS=WS, MTOM=MTOM, OEM=OEM, fuel=fuel, MZFM=OEM + G.M_PAYLOAD_MAX, MLM=OEM + G.M_PAYLOAD_MAX + C2.RESERVE_FRAC * MTOM,
        TW=G.N_ENG * T_ENG / (MTOM * G0), S=S, b=g["b"], cr=g["cr"], ct=g["ct"], mac=g["mac"],
        ymac=g["y_mac"] / half, X_LEMAC=g["X_LEMAC"], LLE=G.SWEEP_LE_W, Lc4=pf.sweep(0.25),
        Lc2=pf.sweep(0.5), LTE=pf.sweep(1.0), t_root=C2.t_root,
        y_hld_in=wc["y_in"] / half, y_flap_out=y_flap_out / half, S_wf_flap=S_wf_flap,
        S_wf_slat=S_wf_slat, ail_span=(H.ail_eta_out - H.ail_eta_in) * half,
        Cl_da=wc["Cl_da"], Cl_p=wc["Cl_p"], helix=wc["helix"], t20=wc["t20"], da02=wc["da_req02"],
        CLmax_c=wc["CLmax_clean"], CLmax_TO=wc["CLmax_TO"], CLmax_L=wc["CLmax_L"],
        alpha_L=wc["alpha_L"], CL_req=wc["CL_req"], eta_flap_req=wc["eta_flap_req"],
        unused=wc["unused"], V_SR0=wc["V_SR0"],
        CD0=r["CD0"], CD0_nw=DE.CD0_no_wave, e=I.OSWALD_E, C_L=r["C_L"], LD=r["LD"],
        M_DD=DE.M_DD, M_cr=DE.M_cr, sar=DE.v_cruise * r["LD"] / (I.TSFC * W_mid),
        Swet=sum(g["swet"].values()), Swet_S=sum(g["swet"].values()) / S,
        # empennage
        S_h=g["S_h"], b_h=g["b_h"], cr_h=g["cr_h"], ct_h=g["ct_h"], mac_h=g["mac_h"],
        S_v=g["S_v"], b_v=g["b_v"], cr_v=g["cr_v"], ct_v=g["ct_v"], mac_v=g["mac_v"],
        l_h=g["l_h"], X_ac_t=g["X_ac_t"],
        # nacelle and engine position
        nac=g["nac"], y_e=g["y_e"], x_eng_cg=g["x_eng_cg"],
        # CG
        X_fwd=g["X_fwd"], X_aft=g["X_aft"], X_OEM=g["X_OEM"],
        cg_fwd_mac=(g["X_fwd"] - g["X_LEMAC"]) / g["mac"], cg_aft_mac=(g["X_aft"] - g["X_LEMAC"]) / g["mac"],
        # gear (three-view, Vos Sec. 9.2)
        x_mlg=tv["x_mlg"], x_nlg=tv["x_nlg"], y_mlg=tv["y_mlg"], h_cg=tv["h_cg"],
        f_nlg_aft=tv["f_nlg"][0], f_nlg_fwd=tv["f_nlg"][1], psi=tv["psi"], phi_nac=tv["phi_nac"],
        phi_tip=tv["phi_tip"], h_nac=tv["h_nac"], height=tv["height"], l_mlg=tv["l_mlg"],
        l_nlg=tv["l_nlg"], mlg_xc=tv["mlg_xc"], scrape=tv["scrape_achieved"],
        belly_start=tv["x_belly_start"], scrape_angle=tv["scrape_angle"], alpha_LOF=tv["alpha_LOF"], scrape_det=tv["scrape_det"],
        gear_outer=tv["y_mlg"] + TV.WHEEL_SPACING / 2 + TV.MLG_TYRE_W / 2,
        # fuel volume
        # V_box: integral wing-box tanks; V_aux: auxiliary fuselage tank (V4); V_tot: both
        V_fuel=fuel / I.RHO_FUEL, cap=cap, V_box=sum(cap.values()),
        V_aux=O.AUX_TANK, V_tot=sum(cap.values()) + O.AUX_TANK,
        # masses
        tor=tor, fe_items=fe_items, fe_tot=fe_tot, m_eng=C2.M_ENGINES,
    )


def set_start(MTOM, oem_frac, fuel):
    I.MTOM_START, G.OEM_FRAC, G.M_FUEL_MAX = MTOM, oem_frac, fuel


# ============================================================================
# 1. Before the iteration: WP3.1 point with one Class II pass
# ============================================================================
G.AR_W = AR_B
I.OSWALD_E = O.oswald(AR_B, W1.Inputs())
I.WS = WS_B
rB = I.evaluate(MTOM_B, OEMF_B, FUEL_B)
B = snapshot(WS_B, MTOM_B, rB["OEM"], FUEL_B, rB)
B["OEM_classI"] = OEMF_B * MTOM_B
B["MTOM_classII"] = rB["MTOM"]

# Class II loop closed at the old wing loading and AR (to separate the two effects)
set_start(MTOM_B, OEMF_B, FUEL_B)
I.WS = WS_B
r42, h42 = I.iterate(verbose=False)

# ============================================================================
# 2. Iteration history from the WP3.1 point at the final wing loading
# ============================================================================
set_start(MTOM_B, OEMF_B, FUEL_B)
G.AR_W = AR
I.OSWALD_E = O.oswald(AR, W1.Inputs())
I.WS = WS_F
r_it, hist = I.iterate(verbose=False)

# ============================================================================
# 3. Optimiser: sweep, constraint-bound optimum per AR, final point
# ============================================================================
set_start(r_it["MTOM"], r_it["OEM"] / r_it["MTOM"], r_it["fuel"])
rows = O.sweep()
per_ar = {A: O.refine(rows, A) for A in O.AR_GRID}
opt, active = min(((d, a) for d, a in per_ar.values() if d is not None), key=lambda t: O._obj(t[0]))
light = min((d_ for d_, a_ in per_ar.values() if d_ is not None), key=lambda d_: d_["MTOM"])
opt = O.evaluate_point(opt["WS"], opt["AR"])
d = O.evaluate_point(WS_F, AR)          # leaves every module at the final point
assert d["ok"], f"final point infeasible: {d['fails']}"
if O._same(opt, d):                     # final point = optimum: quote one set of numbers
    opt = d
    per_ar[AR] = (d, per_ar[AR][1])
alt = O.design(4900.0, 10.5)             # earlier margin point (2026-10-19), for comparison only


def fuel_boundary(lo=4600.0, hi=5000.0):
    """W/S where the fuel volume becomes active at the final AR (current inputs)."""
    for _ in range(10):
        m = 0.5 * (lo + hi)
        dd = O.design(m, AR)
        lo, hi = (m, hi) if dd["V_box"] + O.AUX_TANK >= dd["V_fuel"] else (lo, m)
    return lo


# sensitivity of the fuel-volume boundary to the inputs that set it (final AR)
T0 = I.TSFC
I.TSFC = 1.03 * T0
sens_tsfc3 = fuel_boundary()
def3 = O.design(WS_F, AR)
I.TSFC = 1.05 * T0
sens_tsfc5 = fuel_boundary()
I.TSFC = T0
U0 = I.TANK_USABLE
I.TANK_USABLE = 0.825
sens_use = fuel_boundary()
I.TANK_USABLE = U0
d = O.evaluate_point(WS_F, AR)          # back to the final point (leaves every module there)
O.figures(rows, per_ar, opt, d)
F = snapshot(WS_F, d["MTOM"], d["OEM"], d["fuel_cap"], d["r"])
inp, con = O._MATCH[AR]

# ============================================================================
# 4. Performance checks at the final point (installed T/W, Class II polar, MLM)
# ============================================================================
TWa = d["tw_avail"]
f_L = d["f_L"]
pol = con.polar


def lapse(V, h, dT=0.0):
    return float(W1.thrust_lapse(V, h, dT, inp))


climb = {}
for case in inp.climb_gradients:
    label, grad, n_op, f, flap, gear, h, dT = case
    n_op = inp.n_engines if n_op == 0 else n_op
    _, _, rho, a = W1.isa(h, dT)
    CD0, e = pol.get(flap, gear)
    CL = math.sqrt(e * math.pi * AR * CD0)
    V = math.sqrt(WS_F * f * 2 / rho / CL)
    aT = lapse(V, h, dT)
    gam = (n_op / inp.n_engines) * aT * TWa / f - 2 * math.sqrt(CD0 / (math.pi * AR * e))
    T_req = aT * d["tw"][label] * d["MTOM"] * G0 / inp.n_engines
    climb[label] = dict(req=grad, gamma=100 * gam, CD0=CD0, e=e, V=V, M=V / a, aT=aT, n_op=n_op,
                        T_req=T_req, T_av=aT * T_ENG, h=h)

CD0c, ec = pol.get("clean", "up")
CLrc = math.sqrt(math.pi * AR * ec * CD0c)
_, _, rho0, a0 = W1.isa(inp.h_climb, inp.dT_climb)
V_rc = math.sqrt(WS_F * inp.f_climb * 2 / rho0 / CLrc)
aT_rc = lapse(V_rc, inp.h_climb, inp.dT_climb)
RC = V_rc * (aT_rc * TWa / inp.f_climb - 2 * math.sqrt(CD0c / (math.pi * AR * ec)))
rc = dict(V=V_rc, M=V_rc / a0, aT=aT_rc, RC=RC,
          T_req=aT_rc * d["tw"]["Climb rate"] * d["MTOM"] * G0 / inp.n_engines, T_av=aT_rc * T_ENG)

_, _, rho_to, a_to = W1.isa(inp.h_takeoff, inp.dT_takeoff)
V_to = math.sqrt(WS_F * 2 / rho_to / (inp.CLmax_takeoff / 1.13 ** 2))
aT_to = lapse(V_to, inp.h_takeoff, inp.dT_takeoff)
to = dict(V=V_to, M=V_to / a_to, aT=aT_to, TW_req=d["tw"]["Take-off field length"],
          T_req=aT_to * d["tw"]["Take-off field length"] * d["MTOM"] * G0 / inp.n_engines, T_av=aT_to * T_ENG)

DE = sys.modules["drag_estimator"]
_, _, rho_c, a_c = W1.isa(inp.h_cruise)
aT_cr = lapse(inp.M_cruise * a_c, inp.h_cruise)
cr = dict(M=inp.M_cruise, aT=aT_cr, TW_req=d["tw"]["Cruise speed"],
          T_req=aT_cr * d["tw"]["Cruise speed"] * d["MTOM"] * G0 / inp.n_engines, T_av=aT_cr * T_ENG)

V_app = 1.23 * math.sqrt(2 * f_L * WS_F / (1.225 * F["CLmax_L"]))
s_land = 0.45 * 2 * f_L * WS_F / (1.225 * F["CLmax_L"])

# ranges: design mission sizes MTOM, MTOM + full fuel sizes the tanks, ferry
r = d["r"]
LD = r["LD"]
M_f, fuel_for_range = I._mission_model(LD, DE.v_cruise, DE.h_cruise)


def range_for(fuel, TOM):
    lo, hi = 0.0, 8.0e6
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if M_f(mid) * TOM < fuel else (lo, mid)
    return 0.5 * (lo + hi)


R1 = range_for(r["fuels"]["Design mission"], d["MTOM"])
pl_B = d["MTOM"] - d["OEM"] - d["fuel_cap"]
R2 = range_for(d["fuel_cap"], d["OEM"] + I.INP.payload_maxfuel + d["fuel_cap"])
R3 = range_for(d["fuel_cap"], d["OEM"] + d["fuel_cap"])
harm_MTOM = r["missions"]["Harmonic"]
L_cr = d["MTOM"] * G0 * 0.9375
CL_lft = L_cr / (DE.q_cruise * F["S"])

# tyre loads (draft Sec. 3.2.3: f_mlg 0.9 over 4 wheels, f_nlg 0.1 x 1.07 over 2)
F_mlg = 0.9 * d["MTOM"] * G0 / 4
F_nlg = 0.1 * 1.07 * d["MTOM"] * G0 / 2
RATED_MLG, RATED_NLG = 77e3, 24e3

# ============================================================================
# 5. Write the LaTeX
# ============================================================================
os.makedirs(OUT, exist_ok=True)
os.makedirs(FIG, exist_ok=True)


def write(name, body):
    with open(os.path.join(OUT, name), "w") as f:
        f.write("% generated by wp3_4_report_values.py -- do not edit\n" + body)


opt_ar = per_ar[AR][0]
V = {}
V.update(
    WSB=n(WS_B), MTOMB=n(MTOM_B), OEMBI=n(B["OEM_classI"]), OEMB=n(B["OEM"]),
    MTOMBII=n(B["MTOM_classII"]), SB=f"{B['S']:.1f}", LDB=f"{B['LD']:.2f}", CDzB=f"{B['CD0']:.4f}",
    MTOMfourtwo=n(r42["MTOM"]), Sfourtwo=f"{r42['MTOM'] * G0 / WS_B:.1f}", fuelfourtwo=n(r42["fuels"]["Design mission"]),
    NIT=str(len(hist)),
    WSF=n(WS_F), ARF=f"{AR}", MTOMF=n(d["MTOM"]), OEMF=n(d["OEM"]), OEMfracF=f"{d['OEM'] / d['MTOM']:.4f}",
    MZFMF=n(F["MZFM"]), MLMF=n(F["MLM"]), fLF=f"{f_L:.3f}",
    SF=f"{d['S']:.2f}", bF=f"{d['b']:.2f}", CDzF=f"{d['CD0']:.5f}", CDznwF=f"{d['CD0_nw']:.5f}",
    eF=f"{d['e']:.4f}", CLF=f"{d['C_L']:.3f}", LDF=f"{d['LD']:.2f}", MDDF=f"{d['M_DD']:.3f}",
    fueldesF=n(d["fuel_des"]), fuelcapF=n(d["fuel_cap"]), VfuelF=f"{d['V_fuel']:.2f}",
    VboxF=f"{d['V_box']:.2f}", VwingF=f"{d['cap']['wing']:.2f}", VctrF=f"{d['cap']['centre_box']:.2f}",
    VinbF=f"{d['cap']['inboard']:.2f}", VmargF=f"{d['V_box'] + O.AUX_TANK - d['V_fuel']:.2f}",
    VauxF=f"{O.AUX_TANK:.2f}", VtotF=f"{d['V_box'] + O.AUX_TANK:.2f}",
    VauxNeedF=f"{max(d['V_fuel'] - d['V_box'], 0.0):.2f}",
    mauxF=n(O.AUX_TANK * I.RHO_FUEL),
    VcentreNeedF=f"{d['V_fuel'] - d['cap']['wing']:.2f}",
    TWavF=f"{TWa:.3f}", TWreqF=f"{d['tw_req']:.3f}", TWmargF=f"{100 * d['margin']:.0f}",
    WSmaxF=n(d["ws_max"]), WSmargF=f"{100 * (d['ws_max'] / WS_F - 1):.1f}",
    WSlandF=n(d["mc"]["lims"]["Landing field length"]), WSminspF=n(d["mc"]["lims"]["Minimum speed"]),
    CLmaxcF=f"{F['CLmax_c']:.3f}", CLmaxTOF=f"{F['CLmax_TO']:.3f}", CLmaxLF=f"{F['CLmax_L']:.3f}",
    CLreqF=f"{F['CL_req']:.3f}", etaflapF=f"{F['eta_flap_req']:.3f}", tzwF=f"{F['t20']:.2f}",
    unusedF=f"{100 * F['unused']:.0f}", helixF=f"{F['helix']:.4f}", VSRF=f"{F['V_SR0']:.1f}",
    alphaLF=f"{F['alpha_L']:.1f}",
    sarF=f"{d['sar']:.0f}", sarB=f"{B['sar']:.0f}", sarOpt=f"{opt['sar']:.0f}",
    sarBestF=f"{d['alt']['sar_best_thrust']:.0f}", hBestF=f"{d['alt']['h_best_thrust'] / 0.3048 / 100:.0f}",
    sarGainAlt=f"{100 * (d['alt']['sar_best_thrust'] / d['sar'] - 1):.0f}",
    CLoptF=f"{d['co']['CL_opt']:.2f}", LDoptF=f"{d['co']['LD_opt']:.1f}",
    # optimum
    WSopt=n(opt["WS"]), ARopt=f"{opt['AR']}", MTOMopt=n(opt["MTOM"]), fuelopt=n(opt["fuel_des"]),
    Sopt=f"{opt['S']:.2f}", LDopt=f"{opt['LD']:.2f}", actopt=active.split(";")[0],
    WSbound=n(opt_ar["WS"]), MTOMbound=n(opt_ar["MTOM"]), fuelbound=n(opt_ar["fuel_des"]),
    sarbound=f"{opt_ar['sar']:.0f}", actbound=per_ar[AR][1],
    VmargFthree=f"{d['V_box'] + O.AUX_TANK - d['V_fuel']:.3f}",
    WSmargFabs=n(d["ws_max"] - WS_F), WSboundexact=f"{opt_ar['WS']:,.1f}".replace(",", "{,}"),
    CLmargF=f"{F['CLmax_L'] - F['CL_req']:.3f}", flapmargF=f"{0.72 - F['eta_flap_req']:.3f}",
    helixmargF=f"{F['helix'] - 0.07:.4f}",
    dWSbound=n(opt_ar["WS"] - WS_F), dMTOMbound=n(d["MTOM"] - opt_ar["MTOM"]),
    dfuelbound=n(d["fuel_des"] - opt_ar["fuel_des"]),
    dMTOMopt=n(d["MTOM"] - opt["MTOM"]), dfuelopt=n(d["fuel_des"] - opt["fuel_des"]),
    dsaropt=f"{opt['sar'] - d['sar']:.0f}", dWSopt=n(opt["WS"] - WS_F), dLDopt=f"{opt['LD'] - d['LD']:.2f}",
    pfuelopt=f"{100 * (d['fuel_des'] / opt['fuel_des'] - 1):.1f}",
    pMTOMopt=f"{100 * (d['MTOM'] / opt['MTOM'] - 1):.1f}",
    # lightest design (MTOM objective): lowest AR at its boundary
    WSlight=n(light["WS"]), ARlight=f"{light['AR']}", MTOMlight=n(light["MTOM"]),
    fuellight=n(light["fuel_des"]), LDlight=f"{light['LD']:.2f}", sarlight=f"{light['sar']:.0f}",
    actlight=per_ar[light["AR"]][1], dMTOMlight=n(d["MTOM"] - light["MTOM"]),
    dfuellight=n(light["fuel_des"] - d["fuel_des"]),
    # earlier margin point W/S 4,900 / AR 10.5 (not selected)
    MTOMalt=n(alt["MTOM"]), fuelalt=n(alt["fuel_des"]), dfuelalt=n(alt["fuel_des"] - d["fuel_des"]),
    dMTOMalt=n(alt["MTOM"] - d["MTOM"]), Vmargalt=f"{alt['V_box'] - alt['V_fuel']:.2f}",
    WSmargalt=f"{100 * (alt['ws_max'] / 4900.0 - 1):.1f}", sarAlt=f"{alt['sar']:.0f}", LDalt=f"{alt['LD']:.2f}",
    WSboundtenfive=n(per_ar[10.5][0]["WS"]), fueltenfive=n(per_ar[10.5][0]["fuel_des"]),
    senstsfcthree=n(sens_tsfc3), senstsfcfive=n(sens_tsfc5), sensuse=n(sens_use),
    defthree=f"{def3['V_fuel'] - def3['V_box']:.2f}", dfuelthree=n(def3["fuel_des"] - d["fuel_des"]),
    dMTOMthree=n(def3["MTOM"] - d["MTOM"]),
    dMTOMfourtwo=n(r42["MTOM"] - d["MTOM"]), dSfourtwo=f"{r42['MTOM'] * G0 / WS_B - d['S']:.1f}",
    dfuelfourtwo=n(r42["fuels"]["Design mission"] - d["fuel_des"]),
    # performance checks
    Vapp=f"{V_app:.1f}", sland=n(s_land), RCF=f"{RC:.1f}", TWtoF=f"{to['TW_req']:.3f}",
    TWcrF=f"{cr['TW_req']:.3f}", Rone=n(R1 / 1e3), Rtwo=n(R2 / 1e3), Rthree=n(R3 / 1e3),
    plB=n(pl_B), harmMTOM=n(harm_MTOM), Lcr=n(L_cr), CLlft=f"{CL_lft:.3f}",
    xmlgF=f"{F['x_mlg']:.2f}", xnlgF=f"{F['x_nlg']:.2f}", hcgF=f"{F['h_cg']:.2f}", ZCG=f"{TV.build()['z_cg']:.2f}", scrapeAng=f"{F['scrape_angle']:.1f}",
    alphaLOFtv=f"{F['alpha_LOF']:.1f}" if F['alpha_LOF'] is not None else "--",
    incW=f"{F['scrape_det']['i_w']:.2f}", scrMarg=f"{TV.SCRAPE_MARGIN:.0f}",
    attLOF=f"{F['scrape_det']['att_LOF']:.1f}", attTD=f"{F['scrape_det']['att_TD']:.1f}",
    alphaTD=f"{F['scrape_det']['alpha_TD']:.1f}",
    lmlgF=f"{F['l_mlg'][0]:.2f}", mlgxcF=f"{F['mlg_xc']:.2f}", trackF=f"{2 * F['y_mlg']:.2f}",
    hnacF=f"{F['h_nac']:.2f}", scrapeF=f"{F['scrape']:.1f}", bellyX=f"{F['belly_start']:.1f}", upsweep=f"{G.UPSWEEP_DEG:.0f}",
    alphaLOF=f"{d['wc']['alpha_LOF']:.1f}",
    Fmlg=f"{F_mlg / 1e3:.1f}", Fnlg=f"{F_nlg / 1e3:.1f}",
)
V["TSFCmg"] = f"{I.TSFC * 1e6:.1f}"
write("wp3_4_values.tex", "".join(f"\\newcommand{{\\wpv{k}}}{{{v}}}\n" for k, v in V.items()))

# ---- iteration history ------------------------------------------------------
it_rows = []
for k, h in enumerate(hist):
    it_rows.append(f"{k} & {n(h['MTOM_in'])} & {h['MTOM_in'] * G0 / WS_F:.2f} & {h['CD0']:.5f} & "
                   f"{h['LD']:.2f} & {n(h['OEM'])} & {n(h['MTOM'])} & {n(h['fuel'])} \\\\")
write("wp3_4_iteration.tex", "\n".join(it_rows) + "\n")

# ---- constraint-bound optimum per AR ----------------------------------------
pa = []
for A, (dd, act) in per_ar.items():
    cells = [f"{A}", n(dd['WS']), n(dd['MTOM']), n(dd['fuel_des']), f"{dd['S']:.2f}",
             f"{dd['b']:.2f}", f"{dd['LD']:.2f}", f"{dd['sar']:.0f}", act]
    if A == opt["AR"]:          # overall optimum: shaded and bold (needs xcolor[table])
        pa.append("\\rowcolor{green!12} " + " & ".join(f"\\textbf{{{c}}}" for c in cells) + " \\\\")
    else:
        pa.append(" & ".join(cells) + " \\\\")
write("wp3_4_per_ar.tex", "\n".join(pa) + "\n")

# ---- margins of the final point ---------------------------------------------
wc = d["wc"]
eta_flap_av = wc["y_flap_out"] / (wc["b"] / 2)
mg = [
    ("Thrust (driving constraint: cruise speed)", f"$T/W \\leq {TWa:.3f}$", f"{d['tw_req']:.3f}",
     f"$+{100 * d['margin']:.0f}\\,\\%$ thrust"),
    ("Landing field length / minimum speed", f"$W/S \\leq {n(d['ws_max'])}$", n(WS_F),
     f"$+{100 * (d['ws_max'] / WS_F - 1):.1f}\\,\\%$"),
    ("Fuel volume (REQ-WNG-FUEL-01), wing box + aux tank", f"$V \\leq {d['V_box'] + O.AUX_TANK:.2f}$~m$^3$",
     f"{d['V_fuel']:.2f}~m$^3$",
     f"${d['V_box'] + O.AUX_TANK - d['V_fuel']:+.3f}$~m$^3$ (active)" if d['V_box'] + O.AUX_TANK - d['V_fuel'] < 0.01 else
     f"$+{d['V_box'] + O.AUX_TANK - d['V_fuel']:.2f}$~m$^3$ ($+{100 * ((d['V_box'] + O.AUX_TANK) / d['V_fuel'] - 1):.1f}\\,\\%$)"),
    ("Cruise $L/D$ (REQ-WNG-EFF-02)", "$\\geq 15.4$", f"{d['LD']:.2f}", f"$+{d['LD'] - 15.4:.2f}$"),
    ("$M_{dd}$ at MTOM $C_L$", f"$\\geq {DE.M_cruise}$", f"{d['M_DD']:.3f}", f"$+{d['M_DD'] - DE.M_cruise:.3f}$"),
    ("$C_{L,\\max}$ landing (matching diagram)", f"$\\geq {wc['CL_req']:.3f}$", f"{wc['CLmax_L']:.3f}",
     f"$+{wc['CLmax_L'] - wc['CL_req']:.3f}$"),
    ("Flap span needed (REQ-RCS-01)", f"$\\leq {eta_flap_av:.2f}\\,b/2$", f"{wc['eta_flap_req']:.3f}\\,$b/2$",
     f"$+{eta_flap_av - wc['eta_flap_req']:.3f}\\,b/2$"),
    ("Roll $20^\\circ$ at $V_{SR0}$ (REQ-RCS-02)", "$\\leq 5$~s", f"{wc['t20']:.2f}~s", f"$+{5 - wc['t20']:.2f}$~s"),
    ("Aileron travel unused (REQ-RCS-03)", "$\\geq 25\\,\\%$", f"{100 * wc['unused']:.0f}\\,\\%",
     f"$+{100 * (wc['unused'] - 0.25):.0f}$ points"),
    ("Roll helix $pb/2V$ (REQ-RCS-04)", "$\\geq 0.07$", f"{wc['helix']:.4f}", f"$+{wc['helix'] - 0.07:.4f}$"),
    ("Aspect ratio (ADSEE limit)", "$\\leq 10.6$", f"{AR}", f"${O.AR_MAX - AR:+.1f}$ (at the limit)" if AR >= O.AR_MAX else f"${O.AR_MAX - AR:+.1f}$"),
    ("Wingspan (REQ-WNG-SPAN-01)", "$\\leq 36$~m", f"{d['b']:.2f}~m", f"$+{36 - d['b']:.2f}$~m"),
]
write("wp3_4_margins.tex", "\n".join(" & ".join(m) + " \\\\" for m in mg) + "\n")

# ---- REQ-ENG-01..08 at the final point -------------------------------------
eng = [
    ("REQ-ENG-01", "Cruise, $M$ 0.77, FL350", "AEO", cr, "REQ-CRUISE-01"),
    ("REQ-ENG-02", "Climb rate 15 m/s, SL", "AEO", rc, "REQ-CLIMB-01"),
    ("REQ-ENG-03", "CS 25.119 landing climb", "AEO", climb["CS 25.119"], "REQ-CLIMB-06"),
    ("REQ-ENG-04", "CS 25.121(a) gear down", "OEI", climb["CS 25.121(a)"], "REQ-CLIMB-02"),
    ("REQ-ENG-05", "CS 25.121(b) 2nd segment", "OEI", climb["CS 25.121(b)"], "REQ-CLIMB-03"),
    ("REQ-ENG-06", "CS 25.121(c) en-route", "OEI", climb["CS 25.121(c)"], "REQ-CLIMB-04"),
    ("REQ-ENG-07", "CS 25.121(d) approach", "OEI", climb["CS 25.121(d)"], "REQ-CLIMB-05"),
    ("REQ-ENG-08", "Take-off 1,296 m, SL", "AEO", to, "REQ-TAKE-02"),
]
OLD_ENG = {"REQ-ENG-01": 8.80, "REQ-ENG-02": 29.18, "REQ-ENG-03": 16.80, "REQ-ENG-04": 27.33,
           "REQ-ENG-05": 29.19, "REQ-ENG-06": 19.62, "REQ-ENG-07": 35.03, "REQ-ENG-08": 23.13}
er = []
for rid, cond, mode, c, src in eng:
    er.append(f"{rid} & {cond} & {mode} & {c['M']:.3f} & {OLD_ENG[rid]:.2f} & {c['T_req'] / 1e3:.2f} & "
              f"{c['T_av'] / 1e3:.2f} & $+{100 * (c['T_av'] / c['T_req'] - 1):.0f}\\,\\%$ \\\\")
write("wp3_4_engine_req.tex", "\n".join(er) + "\n")
ENG = {rid: c for rid, _, _, c, _ in eng}

# ---- parameter table --------------------------------------------------------
def rowp(group, name, b, f, unit):
    return f"{group} & {name} & {b} & {f} & {unit} \\\\"


tB, tF = B["tor"], F["tor"]
fB, fF = B["fe_items"] or {}, F["fe_items"] or {}
P = [
    rowp("Design point", "Wing loading, $W_\\mathrm{TO}/S$", n(WS_B), n(WS_F), "N/m$^2$"),
    rowp("", "Thrust loading (installed, $2\\times$CF34-8E5), $T_\\mathrm{TO}/W_\\mathrm{TO}$", f"{B['TW']:.3f}", f"{F['TW']:.3f}", "--"),
    rowp("", "Take-off thrust, $T_\\mathrm{TO}$", "$2\\times 59.7$", "$2\\times 59.7$", "kN"),
    "\\midrule",
    rowp("Masses", "Maximum take-off mass, MTOM", n(MTOM_B), n(F["MTOM"]), "kg"),
    rowp("", "Operating empty mass, OEM (Torenbeek Class II)", n(B["OEM"]), n(F["OEM"]), "kg"),
    rowp("", "OEM / MTOM", f"{B['OEM'] / MTOM_B:.4f}", f"{F['OEM'] / F['MTOM']:.4f}", "--"),
    rowp("", "Maximum zero-fuel mass, MZFM", n(B["MZFM"]), n(F["MZFM"]), "kg"),
    rowp("", "Maximum landing mass, MLM (MZFM + reserves)", n(B["MLM"]), n(F["MLM"]), "kg"),
    rowp("", "Maximum structural payload", n(G.M_PAYLOAD_MAX), n(G.M_PAYLOAD_MAX), "kg"),
    rowp("", "Maximum fuel mass (MTOM + full fuel mission)", n(B["fuel"]), n(F["fuel"]), "kg"),
    rowp("", "Design-mission fuel (2,019 km, 7,200 kg)", "--", n(d["fuel_des"]), "kg"),
    "\\midrule",
    rowp("Wing sizing", "Wing area, $S$", f"{B['S']:.2f}", f"{d['S']:.2f}", "m$^2$"),
    rowp("", "Aspect ratio, $AR$", f"{AR_B}", f"{AR}", "--"),
    rowp("", "Wingspan, $b$", f"{B['b']:.2f}", f"{d['b']:.2f}", "m"),
    rowp("Planform", "Root chord, $c_r$", f"{B['cr']:.3f}", f"{F['cr']:.3f}", "m"),
    rowp("", "Tip chord, $c_t$", f"{B['ct']:.3f}", f"{F['ct']:.3f}", "m"),
    rowp("", "Taper ratio, $\\lambda$", f"{G.TAPER_W}", f"{G.TAPER_W}", "--"),
    rowp("", "Mean aerodynamic chord, $\\bar c$", f"{B['mac']:.3f}", f"{F['mac']:.3f}", "m"),
    rowp("", "Spanwise position of MAC, $y_\\mathrm{MAC}/(b/2)$", f"{B['ymac']:.3f}", f"{F['ymac']:.3f}", "--"),
    rowp("", "LEMAC from the nose, $X_\\mathrm{LEMAC}$", f"{B['X_LEMAC']:.2f}", f"{F['X_LEMAC']:.2f}", "m"),
    rowp("", "Sweep $\\Lambda_\\mathrm{LE}$ / $\\Lambda_{c/4}$ / $\\Lambda_{c/2}$",
         f"{B['LLE']:.2f} / {B['Lc4']:.2f} / {B['Lc2']:.2f}", f"{F['LLE']:.2f} / {F['Lc4']:.2f} / {F['Lc2']:.2f}", "deg"),
    rowp("", "Dihedral, $\\Gamma$ / tip twist", "2.60 / $-2.0$", "2.60 / $-2.0$", "deg"),
    rowp("Airfoil", "Airfoil, $t/c$", "SC(2)-0612, 0.12", "SC(2)-0612, 0.12", "--"),
    rowp("", "Front / rear spar", "0.20 / 0.70", "0.20 / 0.70", "$x/c$"),
    rowp("Roll control", "Aileron inboard / outboard position", f"{H.ail_eta_in} / {H.ail_eta_out}",
         f"{H.ail_eta_in} / {H.ail_eta_out}", "$y/(b/2)$"),
    rowp("", "Aileron span per wing, $c_a/c$ = 0.25", f"{B['ail_span']:.2f}", f"{F['ail_span']:.2f}", "m"),
    rowp("", "Roll derivatives $C_{l_{\\delta_a}}$ / $C_{l_p}$", f"{B['Cl_da']:.4f} / ${B['Cl_p']:.4f}$",
         f"{F['Cl_da']:.4f} / ${F['Cl_p']:.4f}$", "rad$^{-1}$"),
    rowp("", "Roll helix $pb/(2V)$ / time to $20^\\circ$ at $V_{SR0}$", f"{B['helix']:.4f} / {B['t20']:.2f}",
         f"{F['helix']:.4f} / {F['t20']:.2f}", "rad / s"),
    rowp("High-lift devices", "Slat + single-slotted Fowler flap, $c_f/c$", "0.25", "0.25", "--"),
    rowp("", "HLD inboard position (fuselage side + 0.25 m)", f"{B['y_hld_in']:.3f}", f"{F['y_hld_in']:.3f}", "$y/(b/2)$"),
    rowp("", "Flap / slat outboard position", f"{B['y_flap_out']:.2f} / {H.LE_eta_out:.2f}",
         f"{F['y_flap_out']:.2f} / {H.LE_eta_out:.2f}", "$y/(b/2)$"),
    rowp("", "Flapped wing area $S_{wf}$, flap / slat", f"{B['S_wf_flap']:.1f} / {B['S_wf_slat']:.1f}",
         f"{F['S_wf_flap']:.1f} / {F['S_wf_slat']:.1f}", "m$^2$"),
    rowp("", "Flap take-off / landing deflection", "15 / 40", "15 / 40", "deg"),
    "\\midrule",
    rowp("Fuselage", "Length / outer diameter", "34.00 / 2.926", "34.00 / 2.926", "m"),
    rowp("", "Nose cone / tail cone length", "4.97 / 8.78", "4.97 / 8.78", "m"),
    rowp("", "Tail-cone upsweep", f"{G.UPSWEEP_DEG:.0f}", f"{G.UPSWEEP_DEG:.0f}", "deg"),
    "\\midrule",
    rowp("Propulsion", "Engine (2, under the wing)", "GE CF34-8E5", "GE CF34-8E5", "--"),
    rowp("", "Dry mass per engine / cruise TSFC", "1,428 / 0.68", "1,428 / 0.68", "kg / lb/(lbf\\,h)"),
    rowp("", "Nacelle length / max. diameter / inlet diameter",
         f"{B['nac']['ln']:.2f} / {B['nac']['Dn']:.2f} / {B['nac']['Di']:.2f}",
         f"{F['nac']['ln']:.2f} / {F['nac']['Dn']:.2f} / {F['nac']['Di']:.2f}", "m"),
    rowp("", "Engine spanwise position, $y_e$ (0.35 $b/2$)", f"{B['y_e']:.2f}", f"{F['y_e']:.2f}", "m"),
    "\\midrule",
    rowp("Horizontal tail", "Area $S_h$ ($\\bar V_h = 1.0$)", f"{B['S_h']:.2f}", f"{F['S_h']:.2f}", "m$^2$"),
    rowp("", "Span / root chord / tip chord", f"{B['b_h']:.2f} / {B['cr_h']:.2f} / {B['ct_h']:.2f}",
         f"{F['b_h']:.2f} / {F['cr_h']:.2f} / {F['ct_h']:.2f}", "m"),
    rowp("", "$AR_h$ / $\\lambda_h$ / $\\Lambda_{c/4,h}$ / $t/c$", "4.0 / 0.40 / 30 / 0.10", "4.0 / 0.40 / 30 / 0.10", "-- / -- / deg / --"),
    rowp("Vertical tail", "Area $S_v$ ($\\bar V_v = 0.085$)", f"{B['S_v']:.2f}", f"{F['S_v']:.2f}", "m$^2$"),
    rowp("", "Height / root chord / tip chord", f"{B['b_v']:.2f} / {B['cr_v']:.2f} / {B['ct_v']:.2f}",
         f"{F['b_v']:.2f} / {F['cr_v']:.2f} / {F['ct_v']:.2f}", "m"),
    rowp("", "$AR_v$ / $\\lambda_v$ / $\\Lambda_{\\mathrm{LE},v}$ / $t/c$", "1.6 / 0.35 / 40 / 0.10", "1.6 / 0.35 / 40 / 0.10", "-- / -- / deg / --"),
    rowp("", "Tail arm $l_h = l_v$ (aft CG to tail AC at 0.9 $l_f$)", f"{B['l_h']:.2f}", f"{F['l_h']:.2f}", "m"),
    "\\midrule",
    rowp("Centre of gravity", "Forward / aft CG from the nose", f"{B['X_fwd']:.2f} / {B['X_aft']:.2f}",
         f"{F['X_fwd']:.2f} / {F['X_aft']:.2f}", "m"),
    rowp("", "Forward / aft CG", f"{100 * B['cg_fwd_mac']:.1f} / {100 * B['cg_aft_mac']:.1f}",
         f"{100 * F['cg_fwd_mac']:.1f} / {100 * F['cg_aft_mac']:.1f}", "\\% MAC"),
    "\\midrule",
    rowp("Landing gear", "Tyres main / nose (2 + 2 main, 2 nose)", "34$\\times$9.25-16 / 22$\\times$6.75-10",
         "34$\\times$9.25-16 / 22$\\times$6.75-10", "in"),
    rowp("", "Main / nose gear position from the nose", f"{B['x_mlg']:.2f} / {B['x_nlg']:.2f}",
         f"{F['x_mlg']:.2f} / {F['x_nlg']:.2f}", "m"),
    rowp("", "Main gear track, $2y_\\mathrm{MLG}$", f"{2 * B['y_mlg']:.2f}", f"{2 * F['y_mlg']:.2f}", "m"),
    rowp("", "CG height above ground, $h_\\mathrm{CG}$", f"{B['h_cg']:.2f}", f"{F['h_cg']:.2f}", "m"),
    rowp("", "Nose-gear load, aft / forward CG", f"{100 * B['f_nlg_aft']:.1f} / {100 * B['f_nlg_fwd']:.1f}",
         f"{100 * F['f_nlg_aft']:.1f} / {100 * F['f_nlg_fwd']:.1f}", "\\% $W$"),
    "\\midrule",
    rowp("Fuel system", "Usable integral-tank volume (wing + centre + inboard)", f"{B['V_box']:.2f}", f"{F['V_box']:.2f}", "m$^3$"),
    rowp("", "Auxiliary fuselage tank, usable (ahead of the centre box)", "--", f"{F['V_aux']:.2f}", "m$^3$"),
    rowp("", "Fuel volume needed", f"{B['V_fuel']:.2f}", f"{F['V_fuel']:.2f}", "m$^3$"),
    rowp("", "Fuel outside the $\\eta$ 0.17--0.83 wing tanks (centre tank)",
         f"{max(B['V_fuel'] - B['cap']['wing'], 0):.2f}", f"{max(F['V_fuel'] - F['cap']['wing'], 0):.2f}", "m$^3$"),
    "\\midrule",
    rowp("Performance", "$C_{L,\\max}$ clean / take-off / landing (DATCOM + HLD)",
         f"{B['CLmax_c']:.3f} / {B['CLmax_TO']:.3f} / {B['CLmax_L']:.3f}",
         f"{F['CLmax_c']:.3f} / {F['CLmax_TO']:.3f} / {F['CLmax_L']:.3f}", "--"),
    rowp("", "Zero-lift drag $C_{D_0}$ (Class II, incl. wave drag)", f"{B['CD0']:.5f}", f"{F['CD0']:.5f}", "--"),
    rowp("", "Wetted area ratio, $S_\\mathrm{wet}/S$", f"{B['Swet_S']:.2f}", f"{F['Swet_S']:.2f}", "--"),
    rowp("", "Oswald factor, $e$", f"{B['e']:.4f}", f"{F['e']:.4f}", "--"),
    rowp("", "Mid-cruise $C_L$ / $L/D$", f"{B['C_L']:.3f} / {B['LD']:.2f}", f"{F['C_L']:.3f} / {F['LD']:.2f}", "--"),
    rowp("", "Drag-divergence Mach number (MTOM $C_L$, Korn)", f"{B['M_DD']:.3f}", f"{F['M_DD']:.3f}", "--"),
    rowp("", "Specific air range (mid-cruise, FL350)", f"{B['sar']:.0f}", f"{F['sar']:.0f}", "m/kg"),
]
write("wp3_4_params.tex", "\n".join(P) + "\n")

# ---- Class II mass breakdown, before vs final -------------------------------
MB = []
for k in ["Wing", "Horizontal tail", "Vertical tail", "Fuselage", "Main landing gear", "Nose landing gear",
          "Nacelle group"]:
    MB.append(f"{k} & {n(tB[k])} & {n(tF[k])} \\\\")
MB.append(f"Engines (2 $\\times$ 1,428 kg) & {n(B['m_eng'])} & {n(F['m_eng'])} \\\\")
for k in ["Engine controls", "Starter (pneumatic)", "Fuel system"]:
    MB.append(f"{k} & {n(tB[k])} & {n(tF[k])} \\\\")
for k in fF:
    MB.append(f"{k} & {n(fB.get(k, 0))} & {n(fF[k])} \\\\")
MB.append("\\midrule")
MB.append(f"\\textbf{{OEM}} & \\textbf{{{n(B['OEM'])}}} & \\textbf{{{n(F['OEM'])}}} \\\\")
write("wp3_4_masses.tex", "\n".join(MB) + "\n")
# the same breakdown split in two halves for a side-by-side layout (OEM total in the right half)
_rows = MB[:MB.index("\\midrule")]
_half = (len(_rows) + 1) // 2
write("wp3_4_masses_a.tex", "\n".join(_rows[:_half]) + "\n")
write("wp3_4_masses_b.tex", "\n".join(_rows[_half:] + MB[MB.index("\\midrule"):]) + "\n")

# ---- compliance matrix ------------------------------------------------------
Y, NO, NV, GRP = "\\yes{}", "\\no{}", "\\nv{}", "\\grp{}"
c = climb
cm = []


def req(rid, text, required, value, ok):
    cm.append(f"{rid} & {text} & {required} & {value} & {ok} \\\\")


def head(t):
    cm.append(f"\\multicolumn{{5}}{{l}}{{\\textbf{{{t}}}}} \\\\")


head("WP1: top-level requirements")
req("REQ-PAY-02", "Maximum structural payload", "9,302~kg",
    f"Harmonic mission needs MTOM {n(harm_MTOM)}~kg $\\leq$ {n(d['MTOM'])}~kg", Y)
req("REQ-PAS-01, PAY-01", "Passenger cabin and payload layout", "WP1", "Unchanged by the iteration (fuselage fixed)", Y)
req("REQ-SPAN-01", "Wingspan; landing gear span", "$\\leq 36$~m; $\\leq 9$~m",
    f"$b = {d['b']:.2f}$~m; gear {2 * F['gear_outer']:.2f}~m", Y)
req("REQ-CLIMB-01", "Climb rate, MTOM, SL", "$\\geq 15$~m/s", f"{RC:.1f}~m/s", Y)
req("REQ-CLIMB-02", "OEI, gear down, TO flaps (CS 25.121(a))", "$> 0\\,\\%$", f"{c['CS 25.121(a)']['gamma']:.1f}\\,\\%", Y)
req("REQ-CLIMB-03", "OEI, gear up, TO flaps (CS 25.121(b))", "$\\geq 2.4\\,\\%$", f"{c['CS 25.121(b)']['gamma']:.1f}\\,\\%", Y)
req("REQ-CLIMB-04", "OEI, clean (CS 25.121(c))", "$\\geq 1.2\\,\\%$", f"{c['CS 25.121(c)']['gamma']:.1f}\\,\\%", Y)
req("REQ-CLIMB-05", "OEI, approach (CS 25.121(d)), MLM", "$\\geq 2.1\\,\\%$", f"{c['CS 25.121(d)']['gamma']:.1f}\\,\\%", Y)
req("REQ-CLIMB-06", "AEO, landing (CS 25.119), MLM", "$\\geq 3.2\\,\\%$", f"{c['CS 25.119']['gamma']:.1f}\\,\\%", Y)
req("REQ-TAKE-01", "$V_2 = 1.13\\,V_\\mathrm{SR}$", "--", "Built into the take-off constraint", Y)
req("REQ-TAKE-02", "Take-off distance, MTOM, SL", "$\\leq 1{,}296$~m",
    f"Needs $T/W = {to['TW_req']:.3f} \\leq {TWa:.3f}$", Y)
req("REQ-CRUISE-01", "Cruise $M \\geq 0.77$ at FL350", "$T/W$ available",
    f"Needs $T/W = {cr['TW_req']:.3f} \\leq {TWa:.3f}$", Y)
req("REQ-RAN-01", "Range at 7,200~kg payload", "$\\geq 2{,}019$~km", f"{n(R1 / 1e3)}~km (sizes the MTOM)", Y)
req("REQ-RAN-02", "Range at MTOM, full fuel, 6,355~kg", "$\\geq 2{,}574$~km",
    f"{n(R2 / 1e3)}~km (sizes the fuel volume)", Y)
req("REQ-RAN-03", "Ferry range", "$\\geq 2{,}963$~km", f"{n(R3 / 1e3)}~km", Y)
req("REQ-FUEL-01 to 03", "Fuel reserve policy", "WP1", "Built into the equivalent range", Y)
req("REQ-APA-01", "Approach speed, MLM, SL", "$\\leq 64$~m/s", f"{V_app:.1f}~m/s", Y)
req("REQ-APA-02", "Landing distance, MLM, SL", "$\\leq 1{,}210$~m", f"{n(s_land)}~m", Y)
cm.append("\\midrule")
head("WP2: wing")
req("REQ-WNG-LFT-01", "Lift at the start of cruise (MTOM $g\\cdot 0.9375$)",
    f"{n(L_cr)}~N (was 267,850)", f"$C_L = {CL_lft:.3f}$ at FL350", Y)
req("REQ-WNG-LFT-02", "$C_{L,\\max}$ take-off", "$\\geq 2.10$", f"{F['CLmax_TO']:.2f}", Y)
req("REQ-WNG-LFT-03", "$C_{L,\\max}$ landing", f"$\\geq 2.60$ ({F['CL_req']:.2f} for the field)", f"{F['CLmax_L']:.2f}", Y)
req("REQ-WNG-EFF-01", "Drag-divergence Mach number", "$\\geq 0.79$", f"{d['M_DD']:.3f}", Y)
req("REQ-WNG-EFF-02", "Cruise $L/D$ ($0.866\\,(L/D)_{\\max}$)", "$\\geq 15.4$", f"{d['LD']:.2f}", Y)
req("REQ-WNG-FUEL-01", "Usable internal fuel volume", f"$\\geq {d['V_fuel']:.2f}$~m$^3$ (was 5.0)",
    f"{d['V_box'] + O.AUX_TANK:.2f}~m$^3$ (wing box {d['V_box']:.2f} + aux tank {O.AUX_TANK:.2f})", Y)
req("REQ-WNG-SPAN-01", "Wingspan", "$\\leq 36$~m", f"{d['b']:.2f}~m", Y)
req("REQ-RCS-01", "Ailerons outboard of the TE HLDs", "No overlap",
    f"Flap needed to {F['eta_flap_req']:.3f}, aileron from 0.72 $b/2$", Y)
req("REQ-RCS-02", "OEI roll $20^\\circ$ (CS 25.149(h)(4))", "$\\leq 5$~s", f"{F['t20']:.2f}~s at $V_{{SR0}}$", Y)
req("REQ-RCS-03", "Remaining aileron deflection", "$\\geq 6.25^\\circ$",
    f"$6.25^\\circ$; {100 * F['unused']:.0f}\\,\\% unused at REQ-RCS-02", Y)
req("REQ-RCS-04", "Steady roll helix angle", "$pb/2V \\geq 0.07$", f"{F['helix']:.4f}", Y)
req("REQ-HLD-01", "$C_{L,\\max}$ landing", "$\\geq 2.60$", f"{F['CLmax_L']:.2f}", Y)
req("REQ-HLD-02", "$C_{L,\\max}$ take-off", "$\\geq 2.10$", f"{F['CLmax_TO']:.2f}", Y)
req("REQ-HLD-03", "Climb gradient, approach config.", "$\\geq 2.1\\,\\%$", f"{c['CS 25.121(d)']['gamma']:.1f}\\,\\%", Y)
req("REQ-HLD-04", "Climb gradient, landing config.", "$\\geq 3.2\\,\\%$", f"{c['CS 25.119']['gamma']:.1f}\\,\\%", Y)
req("REQ-HLD-05", "Retraction from full extension", "Below $V_F + 9$~kt", "Actuation not yet sized", NV)
req("REQ-HLD-06", "Fuel volume after HLD integration", f"$\\geq {d['V_fuel'] - O.AUX_TANK:.2f}$~m$^3$ in the wing box",
    f"{d['V_box']:.2f}~m$^3$ (box 0.20--0.70$c$, clear of the devices)", Y)
req("REQ-RET-01", "Chord extension at full deployment", "$c'/c = 1.16$", "1.16 (unchanged)", Y)
req("REQ-RET-02", "Deflection at full deployment", "$\\geq 40^\\circ$", "$40^\\circ$ (unchanged)", Y)
cm.append("\\midrule")
head("WP3: propulsion")
for rid, cnd in (("REQ-ENG-01", "Thrust per engine, cruise M 0.77, FL350"),
                 ("REQ-ENG-02", "Thrust per engine, climb 15 m/s, SL"),
                 ("REQ-ENG-03", "Thrust per engine, CS 25.119"),
                 ("REQ-ENG-04", "Thrust, OEI, CS 25.121(a)"),
                 ("REQ-ENG-05", "Thrust, OEI, CS 25.121(b)"),
                 ("REQ-ENG-06", "Thrust, OEI, CS 25.121(c)"),
                 ("REQ-ENG-07", "Thrust, OEI, CS 25.121(d)"),
                 ("REQ-ENG-08", "Thrust per engine, take-off, SL")):
    e_ = ENG[rid]
    req(rid, cnd, f"$\\geq {e_['T_req'] / 1e3:.2f}$~kN (was {OLD_ENG[rid]:.2f})",
        f"{e_['T_av'] / 1e3:.2f}~kN", Y)
req("REQ-ENG-09", "Valid EASA certification", "--", "EASA TCDS IM.E.053", Y)
req("REQ-ENG-10", "Commercially produced", "--", "In production (E170/E175)", Y)
req("REQ-ENG-11", "Certified for M 0.77 at FL350", "--", "E175 envelope ($M_{MO}$ 0.82, FL410)", Y)
req("REQ-ENG-12", "Rotor failure no hazard to engine/tanks", "CS 25.903(d)",
    "Burst zone analysis open (engine at 0.35 $b/2$, tanks 0.17--0.83)", NV)
req("REQ-ENG-13", "Cruise TSFC at M 0.77, FL350", "$\\leq 16.20$~mg/(N\\,s)",
    f"{I.TSFC * 1e6:.1f}~mg/(N\\,s); MTOM re-sized for it", NO)
cm.append("\\midrule")
head("WP3: fuselage")
req("REQ-FUS-01", "Seating for at least 80 passengers", "80", "Cabin layout, Section 3.1", GRP)
req("REQ-FUS-02, 03", "Aisle width (CS 25.815)", "0.51 / 0.38~m", "Cross-section, Section 3.1.3", GRP)
req("REQ-FUS-04", "Evacuation in 90~s (CS 25.803(c))", "90~s", "Exits sized per CS 25.807; demonstration later", NV)
req("REQ-FUS-05", "Exits per side (CS 25.807)", "$\\geq 2$, one Type I", "2 Type I per side", Y)
req("REQ-FUS-06", "Fatigue and damage tolerance (CS 25.571)", "--", "Structural design not yet done", NV)
req("REQ-FUS-07", "Pressure loads (CS 25.365)", "--", "Structural design not yet done ($k_{wf}$ 1.08 in Class II)", NV)
cm.append("\\midrule")
head("WP3: landing gear (final MTOM)")
req("REQ-LG-01", "Tyre load within rating, main / nose", "77 / 24~kN",
    f"{F_mlg / 1e3:.1f} / {F_nlg / 1e3:.1f}~kN", Y)
req("REQ-LG-02", "Nose-gear load at aft CG", "$\\geq 6\\,\\%$", f"{100 * F['f_nlg_aft']:.1f}\\,\\%", Y)
req("REQ-LG-03", "Outer span of the main gear", "$\\leq 9$~m", f"{2 * F['gear_outer']:.2f}~m", Y)
req("REQ-LG-04", "Nacelle ground clearance at MTOM", "$\\geq 0.45$~m", f"{F['h_nac']:.2f}~m", Y)
req("REQ-LG-05", "Pitch attitude without tail strike", f"$\\geq {F['scrape_angle']:.1f}^\\circ$", f"{F['scrape']:.1f}$^\\circ$", Y)
req("REQ-LG-06", "Tip-over angle", "$\\geq 15^\\circ$", "$15^\\circ$ (gear placed on it)", Y)
req("REQ-LG-07", "Nose-gear load at forward CG", "$\\leq 20\\,\\%$", f"{100 * F['f_nlg_fwd']:.1f}\\,\\%", Y)
req("REQ-LG-08", "Turnover angle", "$\\leq 55^\\circ$", f"{F['psi']:.1f}$^\\circ$ (track set by it)", Y)
req("REQ-LG-09", "Nacelle clear of the ground at $8^\\circ$ bank", "$\\geq 8^\\circ$", f"{F['phi_nac']:.1f}$^\\circ$", Y)
req("REQ-LG-10", "Tyre inflation pressure", "$\\leq 1.25$~MPa", "1.25~MPa", Y)
cm.append("\\midrule")
head("WP3: empennage")
req("REQ-EMP-01", "Pitch control for stall recovery (CS 25.201/203)", "--",
    "Tail sized by $\\bar V_h$; control check in stability analysis", NV)
req("REQ-EMP-02", "Directional control OEI down to $1.13V_{SR}$", "--",
    "Tail sized by $\\bar V_v$; $V_{MC}$ check in stability analysis", NV)
write("wp3_4_compliance.tex", "\n".join(cm) + "\n")

# ---- figures ----------------------------------------------------------------
for f in ("mtom_vs_ws.png", "aero_vs_ws.png", "sar.png", "fuel_volume_vs_ws.png",
          "matching_diagram_selected.png", "matching_diagram_optimum.png"):
    shutil.copy(os.path.join(O.OUT_DIR, f), os.path.join(FIG, "wp3_4_" + f))
TV.main()
shutil.copy(os.path.join(HERE, "drawings", "three_view.pdf"), os.path.join(FIG, "wp3_4_three_view.pdf"))

print(f"before: MTOM {MTOM_B:,.0f} (Class II pass -> {B['MTOM_classII']:,.0f}), OEM {B['OEM']:,.0f}, S {B['S']:.2f}")
print(f"4,202 closed: MTOM {r42['MTOM']:,.0f}; history to {WS_F:.0f}: {len(hist)} iterations -> {r_it['MTOM']:,.0f}")
print(f"final: MTOM {d['MTOM']:,.0f}, OEM {d['OEM']:,.0f}, S {d['S']:.2f}, b {d['b']:.2f}, L/D {d['LD']:.2f}, SAR {d['sar']:.0f}")
print(f"climb: " + ", ".join(f"{k} {v['gamma']:.1f}%" for k, v in climb.items()) + f", RC {RC:.1f} m/s")
print(f"V_app {V_app:.1f} m/s, s_land {s_land:,.0f} m, R1 {R1 / 1e3:,.0f} R2 {R2 / 1e3:,.0f} R3 {R3 / 1e3:,.0f} km")
print(f"gear: x_mlg {F['x_mlg']:.2f} x_nlg {F['x_nlg']:.2f} track {2 * F['y_mlg']:.2f} psi {F['psi']:.1f} "
      f"phi_nac {F['phi_nac']:.1f} f_nlg {F['f_nlg_aft']:.3f}/{F['f_nlg_fwd']:.3f} h_nac {F['h_nac']:.2f}")
for rid, e_ in ENG.items():
    print(f"  {rid}: M {e_['M']:.3f} req {e_['T_req'] / 1e3:.2f} kN avail {e_['T_av'] / 1e3:.2f} kN")
print(f"written to {OUT}")
