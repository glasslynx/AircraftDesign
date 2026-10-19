"""
Class II component weight estimation (ADSEE-I), three methods side by side:
Torenbeek, Roskam (GD method) and Raymer (cargo/transport).

All inputs are metric (kg, m, m^2, m^3, N, m/s). Each formula converts to the
imperial units it was fitted in and converts the result back to kg.

Geometry comes from the other WP3 scripts, which must sit in the same folder:
  drag_geometry_inputs.py   wing, tails, nacelle, fuselage, masses, CG
  drag_estimator.py         ISA atmosphere, cruise Mach
  three_view_drawing.py     wing/HT root positions, strut lengths, pilot's eye
Values that are still assumed are in the INPUT block, marked ASSUMED, and
explained in notes/class2_weight_assumptions.md. FIXED_EQUIPMENT_MODE switches the
systems/furnishings between a reference-aircraft fraction and the per-system
relations (fill FE_INPUTS first). The engines (TCDS mass) are always included.
Run:  python class2_weight_estimation.py
"""
import math

import drag_geometry_inputs as G
import drag_estimator as DE
import three_view_drawing as TV

geo = G.compute()
tv = TV.build()

# ============================================================================
# INPUT BLOCK (everything not available from the other scripts)
# ============================================================================
# --- Masses --------------------------------------------------------------------
W_TO = G.MTOM                                   # kg
M_OE = G.OEM_FRAC * G.MTOM                      # kg, Class I OEM (replaced by Class II later)
W_MZF = M_OE + G.M_PAYLOAD_MAX                  # kg, maximum zero-fuel mass
RESERVE_FRAC = 0.045    # ASSUMED, reserve fuel / MTOM (WP1 reserves: 1.2 x 370 km + 30 min)
W_L = W_MZF + RESERVE_FRAC * W_TO               # kg, landing design mass: MLM >= MZFM + reserves
M_ENGINE = 1428.0       # kg, CF34-8E5 dry mass per engine (EASA TCDS IM.E.053)
N_E = G.N_ENG
T_TO_TOTAL = G.N_ENG * G.T_TO_ENG               # N, installed take-off thrust (all engines)

# --- Loads and speeds ------------------------------------------------------------
N_GEAR = 3.0            # ASSUMED, gear load factor (Raymer: commercial 2.7-3.0)
V_C_TAS = 228.3         # m/s TAS, design cruise speed V_C from the group's V-n diagram
V_D_TAS = 284.9         # m/s TAS, design dive speed V_D from the group's V-n diagram
H_VN = DE.h_cruise      # m, altitude these TAS values refer to (FL350, V_C = M 0.77 there)
# the weight formulas want equivalent airspeed: V_EAS = V_TAS sqrt(rho/rho0)
_SIGMA_VN = DE.isa(H_VN)[1] / DE.isa(0.0)[1]
V_C_EAS = V_C_TAS * math.sqrt(_SIGMA_VN)        # m/s EAS (127.1 m/s = 247 KEAS)
V_D_EAS = V_D_TAS * math.sqrt(_SIGMA_VN)        # m/s EAS (158.6 m/s = 308 KEAS)
CLMAX_LANDING = 2.93    # landing C_Lmax, group WP2 report (Akos 2026-10-14; gives V_stall for Raymer)

# --- Wing control surfaces (WP2 HLD/aileron layout, fractions of semi-span) --------
FLAP_ETA = (1.75 / 13.356, 9.62 / 13.356)   # Fowler flap, both wings
FLAP_CF_C = 0.25
AIL_ETA = (0.72, 0.95)
AIL_CA_C = 0.25

# --- Tail control surfaces ----------------------------------------------------------
SE_SH = 0.30            # ASSUMED, elevator area / HT area
SR_SV = 0.30            # ASSUMED, rudder area / VT area

# --- Fuselage ------------------------------------------------------------------------
PRESSURISED = True
L_RADOME = 0.80         # m, up to the front pressure bulkhead (three-view)
L_TAILCAP = 0.50        # ASSUMED m, tail cap excluded from Raymer's structural length
K_DOOR = 1.06           # Raymer: one side cargo door
K_LG = 1.0              # Raymer: main gear on the wing, not the fuselage

# --- Nacelle / propulsion ------------------------------------------------------------
K_NG = 1.017            # Raymer: pylon-mounted nacelle
K_TR = 1.18             # Raymer: jet with thrust reverser (W_ec = engine + contents)
K_EC = 0.686            # Roskam: non-afterburning engines

# --- Fuel system -----------------------------------------------------------------------
RHO_FUEL = 800.0        # kg/m^3, Jet A
V_FUEL = G.M_FUEL_MAX / RHO_FUEL               # m^3, largest fuel load
N_TANKS = 3             # ASSUMED, 2 wing tanks + centre tank
V_INTEGRAL = V_FUEL     # m^3, all tanks integral
V_PROTECTED = 0.0       # m^3, no self-sealing tanks

# --- Method-specific knobs -------------------------------------------------------------
K_H_TOR = 1.0           # Torenbeek: fixed stabiliser (1.1 variable incidence)
K_V_TOR = 1.0           # Torenbeek: fuselage-mounted horizontal tail
K_UC = 1.0              # Torenbeek/Roskam gear: low wing (1.08 high wing)
K_INL = 1.0             # Roskam fuselage: engines not buried in the fuselage
K_UHT = 1.0             # Raymer: not an all-moving tail
K_MP, K_NP = 1.0, 1.0   # Raymer: no kneeling gear

# --- Fixed equipment (systems, furnishings) and operational items ---------------------
# "fraction": the same reference-aircraft fraction of MTOM for all three methods.
# "formulas": each method's own per-system relations, using FE_INPUTS below. A method
#             with any FE_INPUTS value it needs still set to None falls back to the
#             fraction, and the missing inputs are listed in the output.
FIXED_EQUIPMENT_MODE = "formulas"        # "fraction" or "formulas" (Akos 2026-10-14: Torenbeek build-up)
FE_FRACTION = 0.162     # m_fe/MTOM, Vos Example 9.1 average (DC-9-30, MD-80, B737-200)
                        # (not the 0.1833 in drag_geometry_inputs.py, which is scaled to Class I)
M_OPERATIONAL = 0.0     # kg, operational items (crew, trapped fuel/oil) if not in the payload

FE_INPUTS = {
    # crew and cabin (filled from WP1 / CS-25)
    "N_PILOTS": 2,
    "N_CABIN_CREW": 2,          # CS 25 / EU-OPS: 1 per 50 seats -> 2 for 80 seats
    "N_PAX": 80,                # WP1 design-mission seats
    "DESIGN_RANGE_KM": 2019.0,  # WP1 design range (Torenbeek instruments/avionics)
    # Torenbeek flight controls: W = k_sc * W_TO^(2/3) [lb]
    "K_SC": 0.64,               # transport with powered controls and TE high-lift devices
    "K_LE_DEVICES": 1.20,       # +20 % for leading-edge devices (slats)
    # shared
    "HYD_FRAC": 0.006,          # ASSUMED (Akos). Torenbeek/Roskam: hydraulics+pneumatics / MTOM (0.006-0.012)
    "W_APU_UNINSTALLED": 130.0, # ASSUMED (Akos). kg, APU dry mass (installed = 2.2x, Raymer); e.g. APS 2300
    "W_UAV": None,              # kg, uninstalled avionics (Raymer: 360-640 kg for transports)
    # Raymer
    "N_F": None,                # number of functions performed by the controls (4-7)
    "N_M": None,                # number of those that are mechanical (0-2)
    "R_KVA": None,              # electrical system rating, kVA (transports 40-60)
    "L_A": None,                # m, electrical routing distance, generators to avionics to cockpit
    "N_GEN": N_E,               # one generator per engine
    "W_CARGO": None,            # kg, maximum cargo mass (furnishings)
    # Roskam (GD furnishings)
    "K_LAV": None,              # lavatory coefficient
    "K_BUF": None,              # buffet/galley coefficient
    "P_C": None,                # psi, design cabin pressure differential
    "PAINT_FRAC": None,         # paint / MTOM (0.003-0.006)
}

# ============================================================================
# Derived inputs from the geometry scripts
# ============================================================================
_, rho0, a0, _ = DE.isa(0.0)
b, cr, ct, mac = geo["b"], geo["cr"], geo["ct"], geo["mac"]
S_w, A_w, lam_w = G.S_W, G.AR_W, G.TAPER_W
tc_w = DE.t_to_c_w
sweep_c4 = math.radians(G.SWEEP_C4_W)
sweep_c2 = math.radians(G.sweep_at(G.SWEEP_LE_W, 0.0, 0.5, A_w, lam_w))
t_root = tc_w * cr                                 # m, max root thickness
b_s = b / math.cos(sweep_c2)                       # m, structural span (formula sheet)

# load factors (CS 25.337, W in lb)
W_lb = W_TO * 2.20462
n_lim = min(max(2.1 + 24000 / (W_lb + 10000), 2.5), 3.8)
n_ult = 1.5 * n_lim
N_l = 1.5 * N_GEAR

# speeds
V_D_kt = V_D_EAS / 0.514444
q_D = 0.5 * rho0 * V_D_EAS ** 2                    # Pa
M_H = V_C_EAS / a0                                 # max Mach at sea level (V_MO at SL)
V_stall = math.sqrt(2 * W_L * 9.80665 / (rho0 * S_w * CLMAX_LANDING))


def _strip_area(eta0, eta1, frac):
    """Both wings: chord fraction 'frac' between semi-span fractions eta0..eta1."""
    y0, y1 = eta0 * b / 2, eta1 * b / 2
    c0, c1 = G.chord_at(y0, b, cr, ct), G.chord_at(y1, b, cr, ct)
    return 2 * frac * (y1 - y0) * (c0 + c1) / 2


S_flap = _strip_area(*FLAP_ETA, FLAP_CF_C)
S_ail = _strip_area(*AIL_ETA, AIL_CA_C)
S_csw = S_flap + S_ail                             # m^2, wing-mounted control surfaces

# tails
S_h, b_h, cr_h, mac_h = geo["S_h"], geo["b_h"], geo["cr_h"], geo["mac_h"]
S_v, b_v, cr_v, mac_v = geo["S_v"], geo["b_v"], geo["cr_v"], geo["mac_v"]
A_h, lam_h, A_v, lam_v = G.AR_H, G.TAPER_H, G.AR_V, G.TAPER_V
sweep_c4_h = math.radians(G.SWEEP_C4_H)
sweep_c4_v = math.radians(G.sweep_at(G.SWEEP_LE_V, 0.0, 0.25, 2 * A_v, lam_v))
t_root_h = G.TC_H * cr_h
S_e, S_r = SE_SH * S_h, SR_SV * S_v

# tail arms
x_wing_c4_root = tv["x_le_root"] + 0.25 * cr
x_ht_c4_root = tv["x_le_root_h"] + 0.25 * cr_h
l_t_root = x_ht_c4_root - x_wing_c4_root           # Torenbeek: root c/4 to root c/4
x_wing_c4_mac = geo["X_LEMAC"] + 0.25 * mac
l_h = geo["X_ac_t"] - x_wing_c4_mac                # Roskam/Raymer: c/4 MAC to c/4 MAC
l_v = l_h                                          # tail ACs at the same station (0.9 l_fus)

# fuselage
L_f, D_f = G.L_FUS, G.D_FUS
S_fus = geo["swet"]["fuselage"]
L_struct = L_f - L_RADOME - L_TAILCAP
K_ws = 0.75 * (1 + 2 * lam_w) / (1 + lam_w) * b * math.tan(sweep_c4) / L_struct
k_wf = 1.08 if PRESSURISED else 1.0

# cabin (three-view fuselage layout)
_r_in = TV.D_INNER / 2
_d_floor = math.sqrt(_r_in ** 2 - (TV.FLOOR_TOP_CHORD / 2) ** 2)      # floor below the centre
_A_below = _r_in ** 2 * math.acos(_d_floor / _r_in) - _d_floor * math.sqrt(_r_in ** 2 - _d_floor ** 2)
L_cabin = TV.X_CABIN_END - TV.X_CABIN_START                            # m, passenger cabin length
V_pax = (math.pi * _r_in ** 2 - _A_below) * L_cabin                    # m^3, cabin volume above the floor
V_pr = math.pi * _r_in ** 2 * (TV.X_AFT_BULKHEAD - TV.X_FRONT_BULKHEAD)  # m^3, pressurised volume
I_y = W_TO * (0.3 * l_h) ** 2                      # kg m^2, pitch inertia from Raymer's K_y = 0.3 L_t

# landing gear (three-view, fully extended struts)
L_mlg, L_nlg = tv["l_mlg"][1], tv["l_nlg"][1]
N_MW = 2 * TV.MLG_WHEELS_PER_STRUT
N_MSS = 2
N_NW = TV.NLG_WHEELS

# nacelle
nac = geo["nac"]
A_inl = math.pi / 4 * nac["Di"] ** 2               # m^2, inlet capture area per engine
P_2 = (101325 + q_D * (1 + M_H ** 2 / 4)) / 6894.76  # psi, fan-face static pressure, SL dive
W_ec_lb = 2.331 * (M_ENGINE * 2.20462) ** 0.901 * 1.0 * K_TR   # Raymer, per nacelle, lb
W_ec = W_ec_lb / 2.20462                           # kg
x_engine_front = geo["X_LEMAC"] + geo["x_highlight"]
L_ec = N_E * ((x_engine_front - tv["eye"][0]) + geo["y_e"])   # m, cable run, all engines

# ============================================================================
# Unit conversion
# ============================================================================
LB, FT, IN, KT, GAL, LBF, PSF = 2.20462, 3.28084, 39.3701, 1.94384, 264.172, 0.224809, 0.0208854


def lb2kg(w):
    return w / LB


# ============================================================================
# TORENBEEK (Synthesis of Subsonic Airplane Design, Ch. 8)
# ============================================================================
class Torenbeek:
    @staticmethod
    def wing(W_MZF, b_s, n_ult, t_r, S):
        # formula sheet: k_w 6.67e-3 (SI) = 1.70e-3 (lb, ft), b_ref 1.905 m, b_s = b/cos(sweep c/2)
        W, bs, tr, Sft = W_MZF * LB, b_s * FT, t_r * FT, S * FT ** 2
        b_ref = 6.25
        return lb2kg(1.70e-3 * W * bs ** 0.75 * (1 + math.sqrt(b_ref / bs)) * n_ult ** 0.55
                     * ((bs / tr) / (W / Sft)) ** 0.30)

    @staticmethod
    def _tail(k, S, V_D_eas, sweep):
        # Torenbeek Fig 8-5 linear fit (as given in Roskam Part V): W/S [lb/ft^2]
        # = 3.81 * S^0.2 V_D / (1000 sqrt(cos sweep)) - 0.287, S in ft^2, V_D in KEAS
        Sft, VD = S * FT ** 2, V_D_eas * KT
        x = Sft ** 0.2 * VD / (1000 * math.sqrt(math.cos(sweep)))
        return lb2kg(k * Sft * (3.81 * x - 0.287))

    @classmethod
    def horizontal_tail(cls, S_h, V_D, sweep_h):
        return cls._tail(K_H_TOR, S_h, V_D, sweep_h)

    @classmethod
    def vertical_tail(cls, S_v, V_D, sweep_v):
        return cls._tail(K_V_TOR, S_v, V_D, sweep_v)

    @staticmethod
    def fuselage(V_D, l_t, b_f, h_f, S_G):
        # Eq 8-16: 0.021 k_wf sqrt(V_D l_t/(b_f+h_f)) S_G^1.2 (lb, KEAS, ft)
        return lb2kg(0.021 * k_wf * math.sqrt(V_D * KT * l_t * FT / ((b_f + h_f) * FT))
                     * (S_G * FT ** 2) ** 1.2)

    @staticmethod
    def _gear(W_to, A, B, C, D):
        W = W_to * LB
        return lb2kg(K_UC * (A + B * W ** 0.75 + C * W + D * W ** 1.5))

    @classmethod
    def main_gear(cls, W_to):           # Table 8-6, jet transport, main retractable
        return cls._gear(W_to, 40.0, 0.16, 0.019, 1.5e-5)

    @classmethod
    def nose_gear(cls, W_to):           # Table 8-6, jet transport, nose retractable
        return cls._gear(W_to, 20.0, 0.10, 0.0, 2.0e-6)

    @staticmethod
    def nacelle(T_to_total):
        # pod-mounted high-bypass turbofan nacelles: 0.065 lb per lbf of total T_TO
        return lb2kg(0.065 * T_to_total * LBF)

    @staticmethod
    def engine_controls(W_to):
        # AS SUPPLIED, NOT A SOURCE FORMULA: 10 % of Torenbeek's surface-control weight
        return lb2kg(0.64 * (W_to * LB) ** 0.666 * 0.10)

    @staticmethod
    def starter(N_e, W_e):
        # AS SUPPLIED, NOT VERIFIED ("generalised fit for Table 8-9")
        return lb2kg(11.45 * N_e * (W_e * LB / 1000) ** 0.5)

    @staticmethod
    def fuel_system(V_ft, N_ft, N_e):
        # AS SUPPLIED, NOT VERIFIED ("integral tanks approximation")
        return lb2kg(80.0 * (N_e + N_ft - 1) + 4.3 * (V_ft * GAL) ** 0.60)


# ============================================================================
# ROSKAM, Part V (General Dynamics method, commercial transports)
# ============================================================================
class Roskam:
    @staticmethod
    def wing(W_TO, n_ult, S, A, M_H, lam, tc, sweep_c2):
        W, Sft = W_TO * LB, S * FT ** 2
        return lb2kg(0.00428 * Sft ** 0.48 * A * M_H ** 0.43 * (W * n_ult) ** 0.84 * lam ** 0.14
                     / ((100 * tc) ** 0.76 * math.cos(sweep_c2) ** 1.54))

    @staticmethod
    def horizontal_tail(W_TO, n_ult, S_h, b_h, t_rh, c_bar, l_h):
        return lb2kg(0.0034 * ((W_TO * LB * n_ult) ** 0.813 * (S_h * FT ** 2) ** 0.584
                               * (b_h / t_rh) ** 0.033 * (c_bar / l_h) ** 0.28) ** 0.915)

    @staticmethod
    def vertical_tail(z_h, b_v, W_TO, n_ult, S_v, M_H, l_v, S_r, A_v, lam_v, sweep_c4_v):
        Sv, Sr = S_v * FT ** 2, S_r * FT ** 2
        return lb2kg(0.19 * ((1 + z_h / b_v) ** 0.5 * (W_TO * LB * n_ult) ** 0.363
                             * Sv ** 1.089 * M_H ** 0.601 * (l_v * FT) ** -0.726
                             * (1 + Sr / Sv) ** 0.217 * A_v ** 0.337 * (1 + lam_v) ** 0.363
                             * math.cos(sweep_c4_v) ** -0.484) ** 1.014)

    @staticmethod
    def fuselage(q_D, W_TO, l_f, h_f):
        return lb2kg(2 * 10.43 * K_INL ** 1.42 * (q_D * PSF / 100) ** 0.283
                     * (W_TO * LB / 1000) ** 0.95 * (l_f / h_f) ** 0.71)

    main_gear = staticmethod(lambda W_TO: Torenbeek._gear(W_TO, 40.0, 0.16, 0.019, 1.5e-5))
    nose_gear = staticmethod(lambda W_TO: Torenbeek._gear(W_TO, 20.0, 0.10, 0.0, 2.0e-6))

    @staticmethod
    def nacelle(N_inl, A_inl, l_n, P_2):
        # GD, turbofan: 7.435 N_inl (l_n A_inl^0.5 P_2)^0.731 (ft, ft^2, psi)
        return lb2kg(7.435 * N_inl * (l_n * FT * (A_inl * FT ** 2) ** 0.5 * P_2) ** 0.731)

    @staticmethod
    def engine_controls(l_f, b, N_e):
        # GD, wing-mounted jet engines: 88.46 ((l_f + b) N_e / 100)^0.294 (ft)
        return lb2kg(88.46 * ((l_f + b) * FT * N_e / 100) ** 0.294)

    @staticmethod
    def starter(N_e, W_e):
        # GD, pneumatic starting: 9.33 (W_E/1000)^1.078, W_E = all engines
        return lb2kg(9.33 * (N_e * W_e * LB / 1000) ** 1.078)

    @staticmethod
    def fuel_system(N_e, N_t, W_F, K_fsp):
        # Torenbeek method for integral tanks, as given by Roskam
        return lb2kg(80 * (N_e + N_t - 1) + 15 * N_t ** 0.5 * (W_F * LB / K_fsp) ** 0.333)


# ============================================================================
# RAYMER, Aircraft Design: A Conceptual Approach (cargo/transport equations)
# ============================================================================
class Raymer:
    @staticmethod
    def wing(W_dg, N_z, S, A, tc, lam, sweep_c4, S_csw):
        return lb2kg(0.0051 * (W_dg * LB * N_z) ** 0.557 * (S * FT ** 2) ** 0.649 * A ** 0.5
                     * tc ** -0.4 * (1 + lam) ** 0.1 / math.cos(sweep_c4) * (S_csw * FT ** 2) ** 0.1)

    @staticmethod
    def horizontal_tail(F_w, B_h, W_dg, N_z, S_ht, L_t, K_y, sweep_ht, A_h, S_e):
        return lb2kg(0.0379 * K_UHT * (1 + F_w / B_h) ** -0.25 * (W_dg * LB) ** 0.639 * N_z ** 0.10
                     * (S_ht * FT ** 2) ** 0.75 / (L_t * FT) * (K_y * FT) ** 0.704
                     / math.cos(sweep_ht) * A_h ** 0.166 * (1 + S_e / S_ht) ** 0.1)

    @staticmethod
    def vertical_tail(Ht_Hv, W_dg, N_z, L_t, S_vt, K_z, sweep_vt, A_v, tc_v):
        return lb2kg(0.0026 * (1 + Ht_Hv) ** 0.225 * (W_dg * LB) ** 0.556 * N_z ** 0.536
                     * (L_t * FT) ** -0.5 * (S_vt * FT ** 2) ** 0.5 * (K_z * FT) ** 0.875
                     / math.cos(sweep_vt) * A_v ** 0.35 * tc_v ** -0.5)

    @staticmethod
    def fuselage(W_dg, N_z, L, S_f, K_ws, D):
        return lb2kg(0.3280 * K_DOOR * K_LG * (W_dg * LB * N_z) ** 0.5 * (L * FT) ** 0.25
                     * (S_f * FT ** 2) ** 0.302 * (1 + K_ws) ** 0.04 * (L / D) ** 0.10)

    @staticmethod
    def main_gear(W_l, N_l, L_m, N_mw, N_mss, V_stall):
        return lb2kg(0.0106 * K_MP * (W_l * LB) ** 0.888 * N_l ** 0.25 * (L_m * IN) ** 0.4
                     * N_mw ** 0.321 * N_mss ** -0.5 * (V_stall * KT) ** 0.1)

    @staticmethod
    def nose_gear(W_l, N_l, L_n, N_nw):
        return lb2kg(0.032 * K_NP * (W_l * LB) ** 0.646 * N_l ** 0.2 * (L_n * IN) ** 0.5 * N_nw ** 0.45)

    @staticmethod
    def nacelle(N_Lt, N_w, N_z, W_ec, N_en, S_n):
        return lb2kg(0.6724 * K_NG * (N_Lt * FT) ** 0.10 * (N_w * FT) ** 0.294 * N_z ** 0.119
                     * (W_ec * LB) ** 0.611 * N_en ** 0.984 * (S_n * FT ** 2) ** 0.224)

    @staticmethod
    def engine_controls(N_en, L_ec):
        return lb2kg(5.0 * N_en + 0.80 * L_ec * FT)

    @staticmethod
    def starter(N_en, W_en):
        return lb2kg(49.19 * (N_en * W_en * LB / 1000) ** 0.541)

    @staticmethod
    def fuel_system(V_t, V_i, V_p, N_t):
        Vt, Vi, Vp = V_t * GAL, V_i * GAL, V_p * GAL
        return lb2kg(2.405 * Vt ** 0.606 * (1 + Vi / Vt) ** -1.0 * (1 + Vp / Vt) * N_t ** 0.5)


# ============================================================================
# FIXED EQUIPMENT per method (used when FIXED_EQUIPMENT_MODE = "formulas").
# Relations as given in Torenbeek Ch. 8, Roskam Part V Ch. 7 (GD) and Raymer
# Ch. 15 (cargo/transport); check them against your copies before reporting.
# Each returns ({item: kg}, [missing inputs]).
# ============================================================================
FE = FE_INPUTS


def _need(keys):
    return [k for k in keys if FE[k] is None]


def _n_crew():
    return FE["N_PILOTS"] + FE["N_CABIN_CREW"]


def _apu():
    return 2.2 * FE["W_APU_UNINSTALLED"]


def _avionics_raymer():
    return lb2kg(1.73 * (FE["W_UAV"] * LB) ** 0.983)


def fe_torenbeek():
    miss = _need(["HYD_FRAC", "W_APU_UNINSTALLED"])
    if miss:
        return None, miss
    W = W_TO * LB
    vpax = V_pax * FT ** 3
    return {
        "Flight controls": lb2kg(FE["K_SC"] * FE["K_LE_DEVICES"] * W ** (2 / 3)),
        "Hydraulics/pneumatics": FE["HYD_FRAC"] * W_TO,
        "Instruments + avionics": lb2kg(0.575 * (M_OE * LB) ** 0.556
                                        * (FE["DESIGN_RANGE_KM"] / 1.852) ** 0.25),
        "Electrical": lb2kg(10.8 * vpax ** 0.7 * (1 - 0.018 * vpax ** 0.35)),
        "Air cond./press./anti-ice": lb2kg(14 * (L_cabin * FT) ** 1.28),
        "APU": _apu(),
        "Furnishings": lb2kg(0.211 * (W_MZF * LB) ** 0.91),
    }, []


def fe_roskam():
    miss = _need(["HYD_FRAC", "W_APU_UNINSTALLED", "W_UAV", "K_LAV", "K_BUF", "P_C", "PAINT_FRAC"])
    if miss:
        return None, miss
    W = W_TO * LB
    n_pax, n_cr = FE["N_PAX"], _n_crew()
    instr = (FE["N_PILOTS"] * (15 + 0.032 * W / 1000) + N_E * (5 + 0.006 * W / 1000)
             + 0.15 * W / 1000 + 0.012 * W)                                   # lb
    iae = lb2kg(instr) + _avionics_raymer()
    w_fs = Roskam.fuel_system(N_E, N_TANKS, G.M_FUEL_MAX, K_FSP)
    furn = (55 * FE["N_PILOTS"] + 32 * n_pax + 15 * FE["N_CABIN_CREW"]
            + FE["K_LAV"] * n_pax ** 1.33 + FE["K_BUF"] * n_pax ** 1.12
            + 109 * (n_pax * (1 + FE["P_C"]) / 100) ** 0.505 + 0.771 * W / 1000)  # lb
    return {
        "Flight controls": lb2kg(56.01 * (W * q_D * PSF / 100000) ** 0.576),
        "Hydraulics/pneumatics": FE["HYD_FRAC"] * W_TO,
        "Instruments + avionics": iae,
        "Electrical": lb2kg(1163 * ((w_fs + iae) * LB / 1000) ** 0.506),
        "Air cond./press./anti-ice": lb2kg(469 * (V_pax * FT ** 3 * (n_cr + n_pax) / 10000) ** 0.419),
        "Oxygen": lb2kg(7 * (n_cr + n_pax) ** 0.702),
        "APU": _apu(),
        "Furnishings": lb2kg(furn),
        "Paint": FE["PAINT_FRAC"] * W_TO,
    }, []


def fe_raymer():
    miss = _need(["N_F", "N_M", "R_KVA", "L_A", "W_APU_UNINSTALLED", "W_UAV", "W_CARGO"])
    if miss:
        return None, miss
    W = W_TO * LB
    n_c = _n_crew()
    S_cs = (S_csw + S_e + S_r) * FT ** 2
    Iy = I_y * LB * FT ** 2
    lfb = (L_f + b) * FT
    return {
        "Flight controls": lb2kg(145.9 * FE["N_F"] ** 0.554 * (1 + FE["N_M"] / FE["N_F"]) ** -1.0
                                 * S_cs ** 0.20 * (Iy * 1e-6) ** 0.07),
        "Hydraulics": lb2kg(0.2673 * FE["N_F"] * lfb ** 0.937),
        "Instruments": lb2kg(4.509 * 1.0 * 1.0 * n_c ** 0.541 * N_E * lfb ** 0.5),
        "Avionics": _avionics_raymer(),
        "Electrical": lb2kg(7.291 * FE["R_KVA"] ** 0.782 * (FE["L_A"] * FT) ** 0.346
                            * FE["N_GEN"] ** 0.10),
        "Air conditioning": lb2kg(62.36 * (FE["N_PAX"] + n_c) ** 0.25 * (V_pr * FT ** 3 / 1000) ** 0.604
                                  * (FE["W_UAV"] * LB) ** 0.10),
        "Anti-ice": 0.002 * W_TO,
        "Handling gear": 3.0e-4 * W_TO,
        "APU": _apu(),
        "Furnishings": lb2kg(0.0577 * n_c ** 0.1 * (FE["W_CARGO"] * LB) ** 0.393 * (S_fus * FT ** 2) ** 0.75),
    }, []


# ============================================================================
# Run all three
# ============================================================================
K_FSP = RHO_FUEL / 119.826          # lb/gal (1 kg/m^3 = 1/119.826 lb/gal)

results = {
    "Wing": (Torenbeek.wing(W_MZF, b_s, n_ult, t_root, S_w),
             Roskam.wing(W_TO, n_ult, S_w, A_w, M_H, lam_w, tc_w, sweep_c2),
             Raymer.wing(W_TO, n_ult, S_w, A_w, tc_w, lam_w, sweep_c4, S_csw)),
    "Horizontal tail": (Torenbeek.horizontal_tail(S_h, V_D_EAS, sweep_c4_h),
                        Roskam.horizontal_tail(W_TO, n_ult, S_h, b_h, t_root_h, mac, l_h),
                        Raymer.horizontal_tail(G.D_TAILCONE_AT_HT, b_h, W_TO, n_ult, S_h, l_h,
                                               0.3 * l_h, sweep_c4_h, A_h, S_e)),
    "Vertical tail": (Torenbeek.vertical_tail(S_v, V_D_EAS, sweep_c4_v),
                      Roskam.vertical_tail(0.0, b_v, W_TO, n_ult, S_v, M_H, l_v, S_r, A_v, lam_v,
                                           sweep_c4_v),
                      Raymer.vertical_tail(0.0, W_TO, n_ult, l_v, S_v, l_v, sweep_c4_v, A_v, G.TC_V)),
    "Fuselage": (Torenbeek.fuselage(V_D_EAS, l_t_root, D_f, D_f, S_fus),
                 Roskam.fuselage(q_D, W_TO, L_f, D_f),
                 Raymer.fuselage(W_TO, n_ult, L_struct, S_fus, K_ws, D_f)),
    "Main landing gear": (Torenbeek.main_gear(W_TO), Roskam.main_gear(W_TO),
                          Raymer.main_gear(W_L, N_l, L_mlg, N_MW, N_MSS, V_stall)),
    "Nose landing gear": (Torenbeek.nose_gear(W_TO), Roskam.nose_gear(W_TO),
                          Raymer.nose_gear(W_L, N_l, L_nlg, N_NW)),
    "Nacelle group": (Torenbeek.nacelle(T_TO_TOTAL),
                      Roskam.nacelle(N_E, A_inl, nac["ln"], P_2),
                      Raymer.nacelle(nac["ln"], nac["Dn"], n_ult, W_ec, N_E, nac["swet"])),
    "Engine controls": (Torenbeek.engine_controls(W_TO),
                        Roskam.engine_controls(L_f, b, N_E),
                        Raymer.engine_controls(N_E, L_ec)),
    "Starter (pneumatic)": (Torenbeek.starter(N_E, M_ENGINE),
                            Roskam.starter(N_E, M_ENGINE),
                            Raymer.starter(N_E, M_ENGINE)),
    "Fuel system": (Torenbeek.fuel_system(V_FUEL, N_TANKS, N_E),
                    Roskam.fuel_system(N_E, N_TANKS, G.M_FUEL_MAX, K_FSP),
                    Raymer.fuel_system(V_FUEL, V_INTEGRAL, V_PROTECTED, N_TANKS)),
}
UNVERIFIED = {("Engine controls", 0), ("Starter (pneumatic)", 0), ("Fuel system", 0)}

STRUCTURE = ["Wing", "Horizontal tail", "Vertical tail", "Fuselage", "Main landing gear",
             "Nose landing gear", "Nacelle group"]
PROPULSION = ["Engine controls", "Starter (pneumatic)", "Fuel system"]
M_ENGINES = N_E * M_ENGINE

fixed_eq = []          # per method: (total kg, {item: kg} or None, missing inputs)
for fn in (fe_torenbeek, fe_roskam, fe_raymer):
    items, miss = fn() if FIXED_EQUIPMENT_MODE == "formulas" else (None, [])
    total = sum(items.values()) if items else FE_FRACTION * W_TO
    fixed_eq.append((total, items, miss))

oem = []
for i in range(3):
    m_str = sum(results[k][i] for k in STRUCTURE)
    m_prop = M_ENGINES + sum(results[k][i] for k in PROPULSION)
    oem.append((m_str, m_prop, fixed_eq[i][0], m_str + m_prop + fixed_eq[i][0] + M_OPERATIONAL))


def main():
    p = print
    p("Inputs derived from the WP3 scripts")
    p(f"  MTOM {W_TO:,.0f} kg, MZFM {W_MZF:,.0f} kg, MLM {W_L:,.0f} kg; n_lim {n_lim:.2f}, n_ult {n_ult:.2f}")
    p(f"  V_C {V_C_EAS / 0.514444:.0f} KEAS, V_D {V_D_kt:.0f} KEAS (q_D {q_D * PSF:.0f} psf), "
      f"M_H {M_H:.3f}, V_stall {V_stall * KT:.1f} kt")
    p(f"  wing: b {b:.2f}, b_s {b_s:.2f}, t_root {t_root:.3f} m, sweep c/4 {math.degrees(sweep_c4):.1f}, "
      f"c/2 {math.degrees(sweep_c2):.1f} deg, S_csw {S_csw:.2f} m^2 (flaps {S_flap:.2f}, ailerons {S_ail:.2f})")
    p(f"  tails: l_t (root c/4) {l_t_root:.2f} m, l_h = l_v (MAC c/4) {l_h:.2f} m, "
      f"VT sweep c/4 {math.degrees(sweep_c4_v):.1f} deg")
    p(f"  fuselage: L {L_f:.2f}, L_struct {L_struct:.2f}, D {D_f:.3f} m, S_wet {S_fus:.1f} m^2, K_ws {K_ws:.3f}")
    p(f"  gear struts (extended): main {L_mlg:.2f} m, nose {L_nlg:.2f} m; wheels {N_MW} main, {N_NW} nose")
    p(f"  nacelle: A_inl {A_inl:.3f} m^2, P_2 {P_2:.1f} psi, W_ec {W_ec:,.0f} kg each; L_ec {L_ec:.1f} m")
    p(f"  fuel: {G.M_FUEL_MAX:,.0f} kg = {V_FUEL:.2f} m^3 in {N_TANKS} integral tanks\n")

    p(f"{'Component [kg]':<22}{'Torenbeek':>11}{'Roskam':>11}{'Raymer':>11}{'Mean':>11}{'% MTOM':>8}")
    tot = [0.0, 0.0, 0.0]
    for name, vals in results.items():
        cells = []
        for i, v in enumerate(vals):
            tot[i] += v
            cells.append(f"{v:>10,.0f}{'*' if (name, i) in UNVERIFIED else ' '}")
        mean = sum(vals) / 3
        p(f"{name:<22}{''.join(cells)}{mean:>11,.0f}{100 * mean / W_TO:>7.2f}%")
    mean_tot = sum(tot) / 3
    p(f"{'Sum':<22}" + "".join(f"{t:>10,.0f} " for t in tot) + f"{mean_tot:>11,.0f}{100 * mean_tot / W_TO:>7.2f}%")
    p("* formula as supplied by the group; not checked against Torenbeek (see the assumptions note)")

    # fixed equipment detail
    p(f"\nFixed equipment: mode '{FIXED_EQUIPMENT_MODE}'")
    for name, (tot_fe, items, miss) in zip(("Torenbeek", "Roskam", "Raymer"), fixed_eq):
        if items:
            p(f"  {name}: " + ", ".join(f"{k} {v:,.0f}" for k, v in items.items()) + f"  -> {tot_fe:,.0f} kg")
        elif miss:
            p(f"  {name}: missing FE_INPUTS {', '.join(miss)} -> fraction {FE_FRACTION} MTOM used")
        else:
            p(f"  {name}: {FE_FRACTION} x MTOM = {tot_fe:,.0f} kg")

    # full OEM
    names = ("Torenbeek", "Roskam", "Raymer")
    p(f"\n{'Class II OEM [kg]':<26}" + "".join(f"{n:>11}" for n in names) + f"{'Mean':>11}")
    rows = [("Structure (incl. nacelles)", 0), ("Propulsion (incl. engines)", 1),
            ("Fixed equipment", 2), ("OEM", 3)]
    for label_, j in rows:
        vals = [o[j] for o in oem]
        p(f"{label_:<26}" + "".join(f"{v:>11,.0f}" for v in vals) + f"{sum(vals) / 3:>11,.0f}")
    p(f"{'  of which engines':<26}" + f"{M_ENGINES:>11,.0f}" * 3 + f"{M_ENGINES:>11,.0f}")
    if M_OPERATIONAL:
        p(f"{'  of which operational':<26}" + f"{M_OPERATIONAL:>11,.0f}" * 4)
    vals = [o[3] / W_TO for o in oem]
    p(f"{'OEM / MTOM':<26}" + "".join(f"{v:>11.4f}" for v in vals) + f"{sum(vals) / 3:>11.4f}")
    vals = [100 * (o[3] / M_OE - 1) for o in oem]
    p(f"{f'vs Class I OEM {M_OE:,.0f} kg':<26}" + "".join(f"{v:>+10.1f}%" for v in vals)
      + f"{sum(vals) / 3:>+10.1f}%")


if __name__ == "__main__":
    main()
