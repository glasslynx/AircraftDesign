"""
Class II zero-lift drag estimate, component build-up (ADSEE-II lecture
"Estimation of Lift & Drag", slides 57-70; Raymer Ch. 12):

    C_D0 = 1/S_ref * sum(C_f * FF * IF * S_wet) + C_D,misc

Geometry (wetted areas, lengths, sweeps, t/c, fineness) is read directly from
drag_geometry_inputs.py, so both files must sit in the same folder.
Run:  python drag_estimator.py
"""
import math

import drag_geometry_inputs as G

geo = G.compute()

# ============================================================================
# INPUT BLOCK (flight condition and drag-method choices)
# ============================================================================
# --- Cruise condition (WP2: FL350, M 0.77) -----------------------------------
h_cruise = 10668.0      # m (35,000 ft)
M_cruise = 0.77
m_cruise_frac = 1.0     # cruise mass / MTOM for C_L in the wave drag (1.0 = conservative)

# --- Skin friction (slides 60-61) ---------------------------------------------
k_surface = 0.634e-5    # m, smooth paint (slide 61)
# laminar flow fraction, civil jet with classic production metal (slide 60)
lam_frac = {"wing": 0.10, "fuselage": 0.05, "VT": 0.10, "HT": 0.10, "nacelle": 0.05}
#   nacelle is not in the table: taken as the fuselage value

# --- Interference factors (slide 63) ------------------------------------------
IF = {
    "wing": 1.0,        # low wing WITH a wing-body fairing (un-filleted low wing: 1.1-1.4)
    "fuselage": 1.0,
    "VT": 1.045,        # conventional tail 1.04-1.05
    "HT": 1.045,
    "nacelle": 1.3,     # pylon-mounted less than ~1 nacelle diameter from the wing
}

# --- Wing airfoil (NASA SC(2)-0612) and tail sections -------------------------
t_to_c_w = 0.12
max_t_loc_w = 0.37      # (x/c)_m of the SC(2)-0612
k_a = 0.935             # Mason technology factor, supercritical (slide 64)

# --- Miscellaneous ---------------------------------------------------------------
leakage_frac = 0.035    # excrescence and leakage, jet transport 2-5 % of total C_D0 (slide 70)

# ============================================================================
# ISA atmosphere (troposphere / lower stratosphere) and Sutherland viscosity
# ============================================================================
def isa(h):
    T0, p0, R, g0, L = 288.15, 101325.0, 287.05, 9.80665, -0.0065
    if h <= 11000:
        T = T0 + L * h
        p = p0 * (T / T0) ** (-g0 / (L * R))
    else:
        T11 = T0 + L * 11000
        p11 = p0 * (T11 / T0) ** (-g0 / (L * R))
        T = T11
        p = p11 * math.exp(-g0 * (h - 11000) / (R * T11))
    rho = p / (R * T)
    a = math.sqrt(1.4 * R * T)
    mu = 1.458e-6 * T ** 1.5 / (T + 110.4)
    return T, rho, a, mu


T, air_density, a_sound, viscosity = isa(h_cruise)
v_cruise = M_cruise * a_sound
q_cruise = 0.5 * air_density * v_cruise ** 2
S_ref = G.S_W

# ============================================================================
# Component data from the geometry code
# ============================================================================
nac = geo["nac"]
A_max_f = math.pi / 4 * G.D_FUS ** 2           # fuselage max. frontal area
A_max_nac = math.pi / 4 * nac["Dn"] ** 2       # nacelle max. frontal area

components = {
    #             length l [m]   S_wet [m^2] (per aircraft)
    "wing":     (geo["mac"],    geo["swet"]["wing"]),
    "fuselage": (G.L_FUS,       geo["swet"]["fuselage"]),
    "VT":       (geo["mac_v"],  geo["swet"]["VT"]),
    "HT":       (geo["mac_h"],  geo["swet"]["HT"]),
    "nacelle":  (nac["ln"],     geo["swet"]["nacelles (2)"]),
}

# ============================================================================
# 1. Skin friction coefficient C_f (slide 61)
# ============================================================================
def reynolds(length):
    re_actual = air_density * v_cruise * length / viscosity
    # cutoff Re (surface roughness); transonic form since M > ~0.7
    re_cutoff = 44.62 * (length / k_surface) ** 1.053 * M_cruise ** 1.16
    return min(re_actual, re_cutoff), re_actual, re_cutoff


def skin_friction(re, laminar):
    c_f_l = 1.328 / math.sqrt(re)
    c_f_t = 0.455 / (math.log10(re) ** 2.58 * (1 + 0.144 * M_cruise ** 2) ** 0.65)
    return laminar * c_f_l + (1 - laminar) * c_f_t


# ============================================================================
# 2. Form factor FF (slide 62)
# ============================================================================
def ff_lifting(t_c, xc_m, sweep_m_deg):
    """Wing, tail, strut and pylon; sweep of the maximum-thickness line."""
    return ((1 + 0.6 / xc_m * t_c + 100 * t_c ** 4)
            * 1.34 * M_cruise ** 0.18 * math.cos(math.radians(sweep_m_deg)) ** 0.28)


f_fus = G.L_FUS / math.sqrt(4 / math.pi * A_max_f)
f_nac = nac["ln"] / math.sqrt(4 / math.pi * A_max_nac)

FF = {
    "wing": ff_lifting(t_to_c_w, max_t_loc_w, geo["sw_m_w"]),
    "fuselage": 1 + 60 / f_fus ** 3 + f_fus / 400,
    "VT": ff_lifting(G.TC_V, G.XC_M_TAIL, geo["sw_m_v"]),
    "HT": ff_lifting(G.TC_H, G.XC_M_TAIL, geo["sw_m_h"]),
    "nacelle": 1 + 0.35 / f_nac,
}

# ============================================================================
# 3. Build-up
# ============================================================================
rows = {}
CD_comp_sum = 0.0
for name, (length, S_wet) in components.items():
    re, re_actual, re_cutoff = reynolds(length)
    c_f = skin_friction(re, lam_frac[name])
    cd = c_f * FF[name] * IF[name] * S_wet / S_ref
    rows[name] = dict(l=length, Re=re, Re_cut=re_cutoff, Cf=c_f, FF=FF[name], IF=IF[name],
                      S_wet=S_wet, CD=cd)
    CD_comp_sum += cd

# ============================================================================
# 4. Miscellaneous drag
# ============================================================================
# 4a. aft-fuselage upsweep (Raymer eq 12.36): D/q = 3.83 u^2.5 A_max, u in rad
u = math.radians(G.UPSWEEP_DEG)
CD_upsweep = 3.83 * u ** 2.5 * A_max_f / S_ref

# 4b. wave drag (slides 64-65): Mason M_DD with the half-chord sweep (as in WP2)
sweep_half = math.radians(G.sweep_at(G.SWEEP_LE_W, 0.0, 0.5, G.AR_W, G.TAPER_W))
C_L_cruise = m_cruise_frac * G.MTOM * G.G / (q_cruise * S_ref)
cs = math.cos(sweep_half)
M_DD = k_a / cs - t_to_c_w / cs ** 2 - C_L_cruise / (10 * cs ** 3)
M_cr = M_DD - (0.1 / 80) ** (1 / 3)
if M_cruise <= M_cr:
    CD_wave = 0.0
elif M_cruise <= M_DD:
    CD_wave = 0.002 * (1 + 2.5 * (M_DD - M_cruise) / 0.05) ** -1
else:
    CD_wave = 0.002 * (1 + (M_cruise - M_DD) / 0.05) ** 2.5

# 4c. excrescence and leakage: a fraction of the TOTAL C_D0 -> divide by (1 - frac)
CD0_no_wave = (CD_comp_sum + CD_upsweep) / (1 - leakage_frac)
CD0 = (CD_comp_sum + CD_upsweep + CD_wave) / (1 - leakage_frac)
CD_leakage = CD0 - (CD_comp_sum + CD_upsweep + CD_wave)


def main():
    print("Cruise: h %.0f m, M %.2f, V %.1f m/s, rho %.4f kg/m^3, mu %.3e Pa s, q %.0f Pa"
          % (h_cruise, M_cruise, v_cruise, air_density, viscosity, q_cruise))
    print("S_ref %.2f m^2\n" % S_ref)
    print("%-9s %6s %9s %8s %6s %6s %8s %9s %6s"
          % ("comp.", "l [m]", "Re", "C_f", "FF", "IF", "S_wet", "C_D", "share"))
    for name, r in rows.items():
        print("%-9s %6.2f %9.3e %8.5f %6.3f %6.3f %8.2f %9.5f %5.1f%%"
              % (name, r["l"], r["Re"], r["Cf"], r["FF"], r["IF"], r["S_wet"], r["CD"],
                 100 * r["CD"] / CD0))
    print("%-9s %70.5f %5.1f%%" % ("upsweep", CD_upsweep, 100 * CD_upsweep / CD0))
    print("%-9s %70.5f %5.1f%%" % ("wave", CD_wave, 100 * CD_wave / CD0))
    print("%-9s %70.5f %5.1f%%" % ("leakage", CD_leakage, 100 * CD_leakage / CD0))
    print()
    print("fineness: fuselage %.2f, nacelle %.2f" % (f_fus, f_nac))
    print("upsweep %.1f deg; wave drag: C_L %.3f, sweep c/2 %.1f deg, M_DD %.3f, M_cr %.3f"
          % (G.UPSWEEP_DEG, C_L_cruise, math.degrees(sweep_half), M_DD, M_cr))
    print("Re cutoff active for: %s"
          % (", ".join(n for n, r in rows.items() if r["Re"] == r["Re_cut"]) or "none"))
    print()
    print("C_D0 without wave drag  %.5f" % CD0_no_wave)
    print("C_D0 with wave drag     %.5f" % CD0)


if __name__ == "__main__":
    main()
