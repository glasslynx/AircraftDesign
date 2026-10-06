#!/usr/bin/env python3
"""
hld_aileron_sizing.py
=====================
Conceptual sizing of high-lift devices (HLDs) and ailerons, following the
AE2111-II ADSEE Lecture 3 method and the aircraft formula sheet.

CLEAN WING (Lecture 2, DATCOM high-aspect-ratio method; formula sheet)
  CLa      = C_la * AR / (2 + sqrt(4 + (AR beta/eta)^2 (1 + tan^2 L_c/2 / beta^2)))
  CLmax    = (CLmax/clmax)_Fig.2(Delta Y, L_LE) * clmax         (valid if AR > 4 / ((C1 + 1) cos L_LE))
  alpha_s  = CLmax / CLa + alpha0L + d_alpha_CLmax_Fig.3(Delta Y, L_LE)
  Delta Y  = y_upper(0.06 c) - y_upper(0.0015 c) in % chord, computed from the airfoil .dat file.
  CLmax, d_alpha_CLmax and CLa can each be overridden by a manual input.

HIGH-LIFT DEVICES (Lecture 3, slides 37-46)
  Step 1  dCLmax_TE   = 0.9 * dClmax * (Swf/S) * cos(Lambda_hinge)
  Step 2  dalpha0L    = dalpha0l_airfoil * (Swf/S) * cos(Lambda_hinge)      (TE devices only)
                        dalpha0l_airfoil = -15 deg landing, -10 deg take-off
  Step 3  CLa_flapped = (S'/S) * CLa_clean,  S' = S + Swf * (c'/c - 1)      (chord-extending TE devices)
  Step 4  dCLmax_LE   = same relation as step 1, with Swf_LE
  Step 5  sanity check: alpha at CLmax vs tail-strike angle, span left for the ailerons
  The dClmax table is for full deployment; use 60-80 % of it at take-off.
  c'/c = 1 + (dc/c_f) * (c_f/c), dc/c_f from the Torenbeek graph vs flap deflection (slide 40).
  dClmax uses the full-deployment (landing) c'/c; the take-off S'/S uses the take-off deflection.
  CLa_clean: DATCOM, formula-sheet form  C_la * AR / (2 + sqrt(4 + (AR beta/eta)^2 (1 + tan^2 L_c/2 / beta^2))).
  Swf = part of the reference (trapezoidal) area spanned by the device, both wings,
        full local chord. It is NOT the area of the device itself.

AILERONS (Lecture 3, slides 54-63; formula sheet)
  Cl_da = 2 * cla * tau / (S * b) * integral_{b1}^{b2} c(y) * y dy
  Cl_p  = -4 * (cla + cd0) / (S * b^2) * integral_0^{b/2} c(y) * y^2 dy
  P     = -(Cl_da / Cl_p) * da * (2V / b)          steady-state roll rate
  dt    = dphi / P                                 time to reach the required bank angle
  Differential ailerons: da = (da_up + da_down) / 2
  Roll requirement from MIL-F-8785B by aircraft class (Lecture 3, slide 61).

The spanwise integrals are evaluated analytically for the straight-tapered
planform c(y) = c_r + (c_t - c_r) * y / (b/2).

Flap and ailerons share the trailing edge: the flap runs from the HLD inboard
station to the aileron inboard station (minus an optional gap). Any change to
the aileron span therefore changes the flap span and dCLmax as well.

Only the Python standard library is needed. matplotlib is optional (lift-curve plot).
"""

import math
import os

# =============================================================================
# 1. INPUTS  --  edit this block
# =============================================================================

# --- Wing planform (current iteration) ---------------------------------------
b        = 26.71095280966218     # wingspan [m]
S        = 67.95                 # reference (trapezoidal) wing area [m^2]
c_root   = 3.865676845690211     # root chord [m]
c_tip    = 1.2221236894835386    # tip chord [m]
sweep_c4 = 24.022                # quarter-chord sweep [deg]; every other sweep is derived from this one
sweep_LE_reported = 28.371339765533104   # LE sweep from the sizing output, used only for a consistency check (None = skip)

# --- Clean-wing aerodynamics -------------------------------------------------
# The DATCOM values (CLmax, d_alpha_CLmax, CLa) are ALWAYS calculated and printed.
# Each manual input below overrides its DATCOM value when it is a number; None = use DATCOM.
CLmax_clean        = None   # clean-wing CLmax [-].                 None = DATCOM (Lecture 2, formula-sheet Fig. 2)
dalpha_CLmax_clean = None   # clean-wing d_alpha_CLmax [deg].       None = DATCOM (formula-sheet Fig. 3)
CLa_clean_user     = None   # clean CLa [1/rad].  None = DATCOM lift-curve slope
alpha0L_clean  = -3.5    # clean-wing zero-lift angle [deg] (untwisted wing: = airfoil alpha0l). None = no absolute angles/plot
M_low          = 0.2     # Mach number for the low-speed DATCOM CLa
eta_airfoil    = 0.95    # airfoil efficiency factor in DATCOM (Lecture 2: 0.95)
tailstrike_deg = 16.7      # tail-strike angle [deg] for the step-5 check. None = skip

# DATCOM inputs for the clean CLmax (high-aspect-ratio method, Lecture 2 slides 29-33)
clmax_airfoil = 2.28     # 2D airfoil c_lmax at M ~ 0.2 and the stall-speed Re (~11e6 on the MAC) [-]
                         #   2.28 = XFOIL-type estimate (NeuralFoil) for SC(2)-0612 at Re 11e6.
                         #   REPLACE with your own flow5 2D polar value.
airfoil_dat   = "NASA SC2-0612 AIRFOIL.dat"   # coordinate file for Delta Y (path relative to this script, or absolute)
DeltaY_user   = None     # LE sharpness parameter [% chord]. None = compute it from airfoil_dat
# Note: Fig. 2 is for untwisted, constant-section wings; the 2 deg twist of the wing is neglected.

# --- Required CLmax (matching diagram). None = skip the "required flap span" sizing
CLmax_req_landing = 2.6
CLmax_req_takeoff = 2.1

# --- Fuselage / layout -------------------------------------------------------
d_fus          = 3.0                          # A-HLD-01: fuselage diameter [m]
root_clearance = 0.25                         # A-HLD-02: wing-root fairing + clearance [m]
y_hld_in       = d_fus / 2 + root_clearance   # A-HLD-02: HLD inboard end [m] (= 1.75 m)
gap_flap_ail   = 0.0                          # spanwise gap between flap end and aileron start [m]

# --- Trailing-edge device ----------------------------------------------------
TE_type  = "fowler"   # plain | split | slotted | fowler | double_slotted | triple_slotted
TE_c_ext = None       # A-HLD-03: extended chord ratio c'/c at the landing deflection [-]
                      #   None = compute it from TE_cf_c with the Torenbeek graph (slide 40)
TE_cf_c  = 0.25       # flap chord ratio c_f/c; the hinge line is at x/c = 1 - c_f/c [-]
                      #   None = derive it from TE_c_ext with the Torenbeek graph (slide 40)
TE_delta_f_landing = 40.0   # flap deflection at landing [deg] (slide 15, Fowler: 40 deg)
TE_delta_f_takeoff = 15.0   # flap deflection at take-off [deg] (slide 15, Fowler: 15 deg); used only for
                            #   the take-off S'/S. None = use the landing c'/c at take-off as well
# The flap outboard end is set automatically to (aileron inboard station - gap_flap_ail).

# --- Leading-edge device -----------------------------------------------------
LE_type     = "slat"    # fixed_slot | le_flap | kruger | slat
LE_c_ext    = 1.10      # A-HLD-04: slat c'/c [-]
LE_y_in     = y_hld_in  # A-HLD-04: slat inboard end [m]
LE_eta_out  = 0.90      # A-HLD-04: slat outboard end as a fraction of b/2 [-]
LE_hinge_xc = 0.0       # x/c of the LE-device "hinge line" (0 = leading edge) [-]

# --- Phase settings (Lecture 3) ----------------------------------------------
TO_fraction_TE   = 0.70   # take-off dClmax as a fraction of the full value (60-80 %): devices are only
TO_fraction_LE   = 0.70   #   partially deployed at take-off (slide 39)
dalpha0l_landing = -15.0  # [deg] AIRFOIL zero-lift angle shift with the TE flap deployed, landing (slide 41)
dalpha0l_takeoff = -10.0  # [deg] same at take-off (smaller deflection). The WING shift is this value
                          #   x (Swf/S) x cos(Lambda_hinge), because only the flapped part of the span has it
slat_in_slope    = True   # True = also count the slat chord extension in S'/S (slide 32: slats raise CLa)

# --- Ailerons ----------------------------------------------------------------
ail_eta_in    = 0.72      # inboard station as a fraction of b/2 [-] (REQ-RCS-04 needs <= 0.741 with tau = 0.471)
ail_eta_out   = 0.95      # outboard station as a fraction of b/2 [-]
ca_c          = 0.25      # aileron chord ratio [-]
da_up_max     = 25.0      # maximum up deflection [deg]
up_down_ratio = 2.0       # differential ratio da_up : da_down (2 -> 25 deg up / 12.5 deg down)
cla_airfoil   = 2 * math.pi   # airfoil lift-curve slope [1/rad]
cd0_airfoil   = 0.0193    # airfoil zero-lift drag coefficient [-]
tau_user      = None      # aileron effectiveness tau [-]. None = use tau_method
tau_method    = "graph"   # "graph": Sadraey graph (Lecture 3 slide 56); already includes real-flow losses
                          # "theory_eta": eta_flap * thin-airfoil value (Roskam/DATCOM style, report A6)
eta_flap      = 0.85      # real-to-theoretical flap effectiveness, only for tau_method = "theory_eta"
roll_class    = "CS25.147f"      # MIL-F-8785B class: I, II, III, IVA, IVB, IVC
V_roll        = 70.0      # [m/s] speed for the roll check. PLACEHOLDER: set your approach speed
helix_req     = 0.07      # REQ-RCS-04: minimum steady roll helix angle pb/(2V) [rad]. None = skip

MAKE_PLOT = True          # lift-curve plot (needs matplotlib and alpha0L_clean)


# =============================================================================
# 2. COURSE DATA
# =============================================================================

# Lecture 3, slide 39: dClmax at full deployment
#  key               name                     dClmax  x c'/c  side  extends chord (-> S'/S)
HLD_TYPES = {
    "plain":          ("Plain flap",            0.9,  False, "TE", False),
    "split":          ("Split flap",            0.9,  False, "TE", False),
    "slotted":        ("Single-slotted flap",   1.3,  False, "TE", False),
    "fowler":         ("Fowler flap",           1.3,  True,  "TE", True),
    "double_slotted": ("Double-slotted flap",   1.6,  True,  "TE", True),
    "triple_slotted": ("Triple-slotted flap",   1.9,  True,  "TE", True),
    "fixed_slot":     ("Fixed slot",            0.2,  False, "LE", False),
    "le_flap":        ("Leading-edge flap",     0.3,  False, "LE", False),
    "kruger":         ("Krueger flap",          0.3,  False, "LE", False),
    "slat":           ("Slat",                  0.4,  True,  "LE", True),
}

# Aileron effectiveness tau vs c_a/c (Sadraey graph, Lecture 3 slide 56), digitised from the
# slide against its grid lines (read-off accuracy about +-0.01).
TAU_GRAPH = [(0.00, 0.000), (0.05, 0.153), (0.10, 0.264), (0.15, 0.344), (0.20, 0.410),
             (0.25, 0.471), (0.30, 0.521), (0.35, 0.560), (0.40, 0.598), (0.45, 0.635),
             (0.50, 0.671), (0.60, 0.741), (0.70, 0.796)]

# Flap chord extension dc/c_f vs flap deflection [deg] (Torenbeek graph, Lecture 3 slide 40),
# digitised from the slide (read-off accuracy about +-0.01). c'/c = 1 + (dc/c_f) * (c_f/c).
#   IVa: Fowler, single slotted (and double slotted with fixed vane)
#   IVb: double and triple slotted with flap extension
_IVa = [(0, 0.0), (7.5, 0.45), (10, 0.47), (15, 0.50), (20, 0.53), (25, 0.56),
        (30, 0.585), (35, 0.61), (40, 0.64), (44, 0.66)]
_IVb = [(0, 0.0), (7.5, 0.46), (10, 0.50), (15, 0.55), (20, 0.60), (25, 0.65),
        (30, 0.70), (35, 0.75), (40, 0.80), (50, 0.89), (58, 0.97)]
TORENBEEK = {"fowler": ("IVa", _IVa), "double_slotted": ("IVb", _IVb), "triple_slotted": ("IVb", _IVb)}

# DATCOM high-aspect-ratio CLmax method (Lecture 2 slides 29-33, formula-sheet Figures 2 and 3).
# All curves digitised from the slide images (read-off accuracy about +-0.01 / +-0.1 deg).
# C1 vs taper ratio (slide 29): high-AR method valid if AR > 4 / ((C1 + 1) cos L_LE)
C1_GRAPH = [(0.00, 0.00), (0.05, 0.10), (0.10, 0.23), (0.15, 0.38), (0.20, 0.46), (0.25, 0.50),
            (0.30, 0.49), (0.35, 0.46), (0.40, 0.415), (0.45, 0.37), (0.50, 0.31), (0.55, 0.255),
            (0.60, 0.21), (0.65, 0.165), (0.70, 0.13), (0.75, 0.10), (0.80, 0.075), (0.85, 0.05),
            (0.90, 0.03), (1.00, 0.00)]
# Figure 2: CLmax/clmax vs Lambda_LE [deg] for Delta Y = 1.4 (<=1.4) ... 2.5 (>=2.5), M ~ 0.2
FIG2_LLE = [0, 10, 20, 25, 30, 40, 50, 60]
FIG2 = {1.4: [0.90, 0.920, 0.962, 0.995, 1.028, 1.105, 1.198, 1.30],
        1.6: [0.90, 0.918, 0.955, 0.975, 1.000, 1.054, 1.120, 1.19],
        1.8: [0.90, 0.912, 0.932, 0.940, 0.950, 0.970, 1.000, 1.03],
        2.0: [0.90, 0.900, 0.900, 0.895, 0.893, 0.890, 0.880, 0.875],
        2.2: [0.90, 0.885, 0.867, 0.857, 0.846, 0.818, 0.780, 0.74],
        2.4: [0.90, 0.875, 0.848, 0.830, 0.800, 0.760, 0.690, 0.60],
        2.5: [0.90, 0.868, 0.834, 0.817, 0.800, 0.735, 0.655, 0.53]}
# Figure 3: d_alpha_CLmax [deg] vs Lambda_LE [deg] for Delta Y = 1.2 (<=1.2), 2, 3, 4; 0.2 <= M <= 0.6
FIG3 = {1.2: [(0, 1.80), (2.5, 1.84), (7.5, 2.07), (12.5, 2.43), (17.5, 3.04), (22.5, 3.73), (26.3, 4.36), (27.5, 4.55), (28.4, 4.72),
              (32.5, 5.55), (37.5, 6.68), (42.5, 7.91), (47.5, 9.42), (52.5, 10.88), (56, 12.0)],
        2.0: [(0, 0.10), (2.5, 0.32), (7.5, 0.80), (12.5, 1.35), (17.5, 2.00), (22.5, 2.70), (26.3, 3.29), (27.5, 3.47), (28.4, 3.61),
              (32.5, 4.33), (37.5, 5.22), (42.5, 6.14), (47.5, 7.15), (52.5, 8.17), (57.5, 9.28), (60, 9.80)],
        3.0: [(0, 1.20), (2.5, 1.34), (7.5, 1.60), (12.5, 1.87), (17.5, 2.20), (22.5, 2.60), (26.3, 2.89), (27.5, 3.04), (28.4, 3.09),
              (32.5, 3.46), (37.5, 3.90), (42.5, 4.42), (47.5, 4.98), (52.5, 5.56), (57.5, 6.27), (60, 6.65)],
        4.0: [(0, 2.20), (2.5, 2.15), (7.5, 2.07), (12.5, 2.06), (17.5, 2.07), (22.5, 2.09), (26.3, 2.15), (27.5, 2.18), (28.4, 2.20),
              (32.5, 2.30), (37.5, 2.43), (42.5, 2.58), (47.5, 2.75), (52.5, 2.89), (57.5, 3.10), (60, 3.20)]}

# MIL-F-8785B roll requirements (bank angle [deg], time [s]); formula-sheet values
ROLL_REQ = {"I": (60, 1.3), "II": (45, 1.4), "III": (30, 1.5),
            "IVA": (90, 1.3), "IVB": (90, 1.0), "IVC": (90, 1.7), "CS25.147f": (30, 1.5)}


# =============================================================================
# 3. PLANFORM
# =============================================================================

class Planform:
    """Straight-tapered wing. y is measured from the centreline, 0 <= y <= b/2."""

    def __init__(self, b, S, c_root, c_tip, sweep_c4_deg):
        self.b, self.S, self.cr, self.ct = b, S, c_root, c_tip
        self.half = b / 2
        self.taper = c_tip / c_root
        self.AR = b ** 2 / S
        self.k = (c_tip - c_root) / self.half                 # dc/dy [-]
        # Formula sheet: tan L_x = tan L_LE - (x/c) * (2 c_r / b) * (1 - taper)
        self._g = 2 * c_root / b * (1 - self.taper)
        self.tan_LE = math.tan(math.radians(sweep_c4_deg)) + 0.25 * self._g

    def sweep(self, xc):
        """Sweep of the constant x/c line [deg]."""
        return math.degrees(math.atan(self.tan_LE - xc * self._g))

    def chord(self, y):
        return self.cr + self.k * y

    def area(self, y1, y2):
        """Planform area between y1 and y2 on ONE wing [m^2]."""
        F = lambda y: self.cr * y + self.k * y ** 2 / 2
        return F(y2) - F(y1)

    def int_cy(self, y1, y2):
        """integral c(y) * y dy  [m^3]"""
        F = lambda y: self.cr * y ** 2 / 2 + self.k * y ** 3 / 3
        return F(y2) - F(y1)

    def int_cy2(self, y1, y2):
        """integral c(y) * y^2 dy  [m^4]"""
        F = lambda y: self.cr * y ** 3 / 3 + self.k * y ** 4 / 4
        return F(y2) - F(y1)

    def y_for_area(self, y_in, area_one_side):
        """Outboard station y such that area(y_in, y) = area_one_side (bisection)."""
        lo, hi = y_in, self.half
        if self.area(lo, hi) < area_one_side:
            return None
        for _ in range(100):
            mid = (lo + hi) / 2
            if self.area(y_in, mid) < area_one_side:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    @property
    def mac(self):
        t = self.taper
        return 2 / 3 * self.cr * (1 + t + t ** 2) / (1 + t)

    @property
    def y_mac(self):
        t = self.taper
        return self.b / 6 * (1 + 2 * t) / (1 + t)

    @property
    def x_lemac(self):
        return self.y_mac * self.tan_LE


def CLa_datcom(cla, AR, M, eta, sweep_half_deg):
    """DATCOM lift-curve slope [1/rad], formula-sheet form (numerator C_la * AR; the lecture
    slide writes 2*pi * AR, which is the same for C_la = 2*pi)."""
    beta = math.sqrt(1 - M ** 2)
    t = math.tan(math.radians(sweep_half_deg))
    return cla * AR / (2 + math.sqrt(4 + (AR * beta / eta) ** 2 * (1 + t ** 2 / beta ** 2)))


def interp_table(table, x, label):
    """Linear interpolation in [(x, y), ...]; warns outside the digitised range."""
    if x < table[0][0] or x > table[-1][0]:
        print(f"  ! {label}: {x} is outside the graph range [{table[0][0]}, {table[-1][0]}], value clamped")
        x = min(max(x, table[0][0]), table[-1][0])
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


# =============================================================================
# 3b. DATCOM CLEAN-WING CLmax (Lecture 2, high-aspect-ratio method)
# =============================================================================

def airfoil_upper_surface(path):
    """Upper-surface (x, y) of a Selig- or Lednicer-format .dat file, sorted LE -> TE, chord-normalised."""
    pts = []
    with open(path) as f:
        for line in f:
            p = line.replace(",", " ").split()
            if len(p) < 2:
                continue
            try:
                pts.append((float(p[0]), float(p[1])))
            except ValueError:
                continue                                   # header line
    if pts and pts[0][0] > 1.5:                            # Lednicer: first line holds the point counts
        n_up = int(pts[0][0])
        surf_a, surf_b = pts[1:1 + n_up], pts[1 + n_up:]
    else:                                                  # Selig: one loop through the leading edge
        i_le = min(range(len(pts)), key=lambda i: pts[i][0])
        surf_a, surf_b = pts[:i_le + 1], pts[i_le:]
    mean_y = lambda s: sum(y for _, y in s) / len(s)
    upper = sorted(surf_a if mean_y(surf_a) > mean_y(surf_b) else surf_b)
    x_le, x_te = upper[0][0], max(x for x, _ in surf_a + surf_b)
    chord = x_te - x_le
    y_le = upper[0][1]
    return [((x - x_le) / chord, (y - y_le) / chord) for x, y in upper]


def delta_y_from_dat(path):
    """LE sharpness parameter Delta Y = y_upper(0.06c) - y_upper(0.0015c), in % chord (slide 28).
    Interpolated linearly in sqrt(x), which follows the round leading edge (y ~ sqrt(x))."""
    up = airfoil_upper_surface(path)
    table = [(math.sqrt(max(x, 0.0)), y) for x, y in up]
    y_at = lambda x: interp_table(table, math.sqrt(x), "airfoil x")
    return 100 * (y_at(0.06) - y_at(0.0015))


def interp_between_curves(curves, key, x, x_of_curve):
    """Interpolate linearly between the curves of a chart family (keyed by Delta Y), clamping the key."""
    keys = sorted(curves)
    k = min(max(key, keys[0]), keys[-1])
    for k0, k1 in zip(keys, keys[1:]):
        if k0 <= k <= k1:
            v0, v1 = x_of_curve(curves[k0], x), x_of_curve(curves[k1], x)
            return v0 + (v1 - v0) * (k - k0) / (k1 - k0)


def datcom_clean(pf, clmax2d, delta_y, cla_rad, alpha0L):
    """DATCOM high-AR CLmax and stall angle (formula sheet). Returns a dict of intermediate values."""
    L_LE = pf.sweep(0.0)
    C1 = interp_table(C1_GRAPH, pf.taper, "taper ratio for C1")
    AR_lim = 4 / ((C1 + 1) * math.cos(math.radians(L_LE)))
    fig2 = lambda vals, L: interp_table(list(zip(FIG2_LLE, vals)), L, "Lambda_LE for Fig. 2")
    fig3 = lambda pts, L: interp_table(pts, L, "Lambda_LE for Fig. 3")
    ratio = interp_between_curves(FIG2, delta_y, L_LE, fig2)
    dalpha = interp_between_curves(FIG3, delta_y, L_LE, fig3)
    CLmax = ratio * clmax2d                               # + dCLmax (Mach > 0.2 term) = 0 at low speed
    out = dict(L_LE=L_LE, C1=C1, AR_lim=AR_lim, high_AR=pf.AR > AR_lim, ratio=ratio, CLmax=CLmax, dalpha=dalpha)
    if alpha0L is not None:
        out["alpha_s"] = math.degrees(CLmax / cla_rad) + alpha0L + dalpha
    return out


# =============================================================================
# 4. HIGH-LIFT DEVICES
# =============================================================================

class HLD:
    def __init__(self, kind, y_in, y_out, c_ext=1.0, hinge_xc=0.0, to_fraction=0.7):
        if kind not in HLD_TYPES:
            raise ValueError(f"Unknown HLD type '{kind}'. Options: {list(HLD_TYPES)}")
        self.kind = kind
        self.name, self.dcl_base, self.scales, self.side, self.extends = HLD_TYPES[kind]
        if not y_in < y_out:
            raise ValueError(f"{self.name}: inboard end {y_in:.2f} m must be < outboard end {y_out:.2f} m")
        self.y_in, self.y_out = y_in, y_out
        self.c_ext = c_ext if (self.scales or self.extends) else 1.0
        if self.c_ext < 1.0:
            raise ValueError("c'/c must be >= 1")
        self.hinge_xc = hinge_xc
        self.to_fraction = to_fraction

    def dClmax(self, phase):
        val = self.dcl_base * (self.c_ext if self.scales else 1.0)
        return val * (self.to_fraction if phase == "takeoff" else 1.0)

    def evaluate(self, pf, phase, dalpha0l_airfoil, c_ext_slope=None):
        """c_ext_slope: c'/c in this phase for S'/S (None = the full-deployment c'/c).
        dClmax always uses the full-deployment c'/c; take-off is covered by to_fraction (slide 39)."""
        Swf = 2 * pf.area(self.y_in, self.y_out)          # both wings
        L_h = pf.sweep(self.hinge_xc)
        cosL = math.cos(math.radians(L_h))
        dcl = self.dClmax(phase)
        dCL = 0.9 * dcl * Swf / pf.S * cosL                # steps 1 and 4
        da0 = dalpha0l_airfoil * Swf / pf.S * cosL if self.side == "TE" else 0.0   # step 2
        c_s = self.c_ext if c_ext_slope is None else c_ext_slope
        dS = Swf * (c_s - 1) if self.extends else 0.0                              # step 3
        return dict(Swf=Swf, Swf_S=Swf / pf.S, L_hinge=L_h, dClmax=dcl,
                    dCLmax=dCL, dalpha0L=da0, dS=dS, c_ext_slope=c_s)


def required_te_span(pf, te, CLmax_req, CLmax_clean, dCL_LE, phase):
    """Outboard flap station needed to reach CLmax_req (with the LE device as specified)."""
    dCL_TE_req = CLmax_req - CLmax_clean - dCL_LE
    if dCL_TE_req <= 0:
        return dCL_TE_req, 0.0, te.y_in
    cosL = math.cos(math.radians(pf.sweep(te.hinge_xc)))
    Swf_req = dCL_TE_req * pf.S / (0.9 * te.dClmax(phase) * cosL)
    y_out = pf.y_for_area(te.y_in, Swf_req / 2)
    return dCL_TE_req, Swf_req, y_out


# =============================================================================
# 5. AILERONS
# =============================================================================

def tau_theory(ratio):
    """Thin-airfoil flap effectiveness: tau = 1 - (theta_f - sin theta_f)/pi, cos theta_f = 2 c_f/c - 1."""
    th = math.acos(2 * ratio - 1)
    return 1 - (th - math.sin(th)) / math.pi


def tau_from_graph(ratio):
    return interp_table(TAU_GRAPH, ratio, "c_a/c for the tau graph")


def aileron_derivatives(pf, y1, y2, tau, cla, cd0):
    Cl_da = 2 * cla * tau / (pf.S * pf.b) * pf.int_cy(y1, y2)
    Cl_p = -4 * (cla + cd0) / (pf.S * pf.b ** 2) * pf.int_cy2(0.0, pf.half)
    return Cl_da, Cl_p


def roll_time(pf, y1, y2, tau, cla, cd0, da_rad, V, phi_req_deg):
    Cl_da, Cl_p = aileron_derivatives(pf, y1, y2, tau, cla, cd0)
    P = -(Cl_da / Cl_p) * da_rad * 2 * V / pf.b          # [rad/s]
    return math.radians(phi_req_deg) / P, P, Cl_da, Cl_p


def size_aileron_helix(pf, y2, y_min, tau, cla, cd0, da_rad, helix_req):
    """Most outboard inboard station meeting pb/(2V) >= helix_req (outboard end fixed; independent of V)."""
    helix = lambda y1: -aileron_derivatives(pf, y1, y2, tau, cla, cd0)[0] \
        / aileron_derivatives(pf, y1, y2, tau, cla, cd0)[1] * da_rad
    if helix(y_min) < helix_req:
        return None
    lo, hi = y_min, y2 - 1e-6
    for _ in range(100):
        mid = (lo + hi) / 2
        if helix(mid) >= helix_req:
            lo = mid
        else:
            hi = mid
    return lo


def size_aileron_inboard(pf, y2, y_min, tau, cla, cd0, da_rad, V, phi_req, t_req):
    """Most outboard inboard station that still meets t_req (outboard end fixed)."""
    t_full, *_ = roll_time(pf, y_min, y2, tau, cla, cd0, da_rad, V, phi_req)
    if t_full > t_req:
        return None                                       # cannot be met, even with the whole span
    lo, hi = y_min, y2 - 1e-6
    for _ in range(100):
        mid = (lo + hi) / 2
        t, *_ = roll_time(pf, mid, y2, tau, cla, cd0, da_rad, V, phi_req)
        if t <= t_req:
            lo = mid
        else:
            hi = mid
    return lo


# =============================================================================
# 6. RUN
# =============================================================================

def line(char="-", n=78):
    print(char * n)


def main():
    pf = Planform(b, S, c_root, c_tip, sweep_c4)

    # ---------------------------------------------------------------- planform
    line("=")
    print("WING PLANFORM")
    line("=")
    S_trap = (c_root + c_tip) * b / 2
    print(f"  b = {b:.3f} m   S = {S:.2f} m^2   AR = {pf.AR:.3f}   taper = {pf.taper:.4f}")
    print(f"  c_r = {c_root:.4f} m   c_t = {c_tip:.4f} m   MAC = {pf.mac:.4f} m   "
          f"y_mac = {pf.y_mac:.3f} m ({pf.y_mac / pf.half:.4f} b/2)   x_LEMAC = {pf.x_lemac:.3f} m")
    print(f"  Sweep: LE {pf.sweep(0):.3f}  c/4 {pf.sweep(0.25):.3f}  c/2 {pf.sweep(0.5):.3f}  "
          f"TE {pf.sweep(1.0):.3f}  [deg]")
    if abs(S_trap - S) / S > 0.005:
        print(f"  ! (c_r + c_t) b / 2 = {S_trap:.2f} m^2 differs from S = {S:.2f} m^2")
    if sweep_LE_reported is not None and abs(sweep_LE_reported - pf.sweep(0)) > 0.25:
        tan_c4 = math.tan(math.radians(sweep_LE_reported)) - 0.25 * pf._g
        print(f"  ! Reported LE sweep {sweep_LE_reported:.3f} deg is not consistent with c/4 sweep "
              f"{sweep_c4:.3f} deg for this planform")
        print(f"    (it corresponds to a c/4 sweep of {math.degrees(math.atan(tan_c4)):.3f} deg). "
              f"This script uses the c/4 input.")

    # ---------------------------------------------------------------- ailerons
    roll_phi, roll_t = ROLL_REQ[roll_class]
    tau_g, tau_th = tau_from_graph(ca_c), tau_theory(ca_c)
    if tau_user is not None:
        tau, tau_src = tau_user, "user input"
    elif tau_method == "graph":
        tau, tau_src = tau_g, "Sadraey graph, slide 56"
    elif tau_method == "theory_eta":
        tau, tau_src = eta_flap * tau_th, f"eta_flap {eta_flap} x thin-airfoil {tau_th:.3f}"
    else:
        raise ValueError("tau_method must be 'graph' or 'theory_eta'")
    da_down = da_up_max / up_down_ratio
    da_eff = 0.5 * (da_up_max + da_down)
    y1_ail, y2_ail = ail_eta_in * pf.half, ail_eta_out * pf.half
    t_roll, P, Cl_da, Cl_p = roll_time(pf, y1_ail, y2_ail, tau, cla_airfoil, cd0_airfoil,
                                       math.radians(da_eff), V_roll, roll_phi)

    # ---------------------------------------------------------------- HLDs
    # Flap chord ratio and extended chord, linked by the Torenbeek graph (slide 40)
    tor = TORENBEEK.get(TE_type)
    te_c_ext, te_cf_c, te_c_ext_TO, tor_lines = TE_c_ext, TE_cf_c, None, []
    if tor is not None:
        curve_name, curve = tor
        dc_L = interp_table(curve, TE_delta_f_landing, "landing flap deflection")
        if te_c_ext is None and te_cf_c is None:
            raise ValueError("Set at least one of TE_c_ext and TE_cf_c")
        if te_cf_c is None:
            te_cf_c = (te_c_ext - 1) / dc_L
            tor_lines.append(f"c_f/c = (c'/c - 1) / (dc/c_f) = ({te_c_ext:.3f} - 1) / {dc_L:.3f} = {te_cf_c:.3f}")
        elif te_c_ext is None:
            te_c_ext = 1 + dc_L * te_cf_c
            tor_lines.append(f"c'/c = 1 + (dc/c_f) * c_f/c = 1 + {dc_L:.3f} * {te_cf_c:.3f} = {te_c_ext:.3f}")
        else:
            implied = 1 + dc_L * te_cf_c
            tor_lines.append(f"input c'/c = {te_c_ext:.3f}; Torenbeek with c_f/c = {te_cf_c:.3f} gives {implied:.3f}"
                             + ("" if abs(implied - te_c_ext) < 0.02 else "  <- INCONSISTENT, check inputs"))
        tor_lines.insert(0, f"Torenbeek curve {curve_name}: dc/c_f = {dc_L:.3f} at delta_f = {TE_delta_f_landing:.0f} deg (landing)")
        if TE_delta_f_takeoff is not None:
            dc_TO = interp_table(curve, TE_delta_f_takeoff, "take-off flap deflection")
            te_c_ext_TO = 1 + dc_TO * te_cf_c
            tor_lines.append(f"take-off: dc/c_f = {dc_TO:.3f} at delta_f = {TE_delta_f_takeoff:.0f} deg -> "
                             f"c'/c = {te_c_ext_TO:.3f} (used for the take-off S'/S only)")
    else:
        if te_cf_c is None:
            raise ValueError(f"No Torenbeek curve stored for '{TE_type}': set TE_cf_c")
        if te_c_ext is None:
            te_c_ext = 1.0
    if not 0.25 - 1e-9 <= te_cf_c <= 0.40 + 1e-9:
        tor_lines.append(f"! c_f/c = {te_cf_c:.3f} is outside the slide-36 guideline (0.25 simple ... 0.35-0.40 slotted)")
    if 1 - te_cf_c < 0.60:
        tor_lines.append(f"! flap leading edge at {1 - te_cf_c:.2f} c: less than 5 % chord behind a rear spar at 55 % c (slide 36)")

    y_flap_out = y1_ail - gap_flap_ail
    te = HLD(TE_type, y_hld_in, y_flap_out, te_c_ext, 1 - te_cf_c, TO_fraction_TE)
    le = HLD(LE_type, LE_y_in, LE_eta_out * pf.half, LE_c_ext, LE_hinge_xc, TO_fraction_LE)
    if te.side != "TE" or le.side != "LE":
        raise ValueError("TE_type must be a trailing-edge device and LE_type a leading-edge device")

    # ---------------------------------------------------------------- clean wing (DATCOM)
    line("=")
    print("CLEAN WING  (Lecture 2: DATCOM lift slope, CLmax and stall angle)")
    line("=")
    CLa_dat = CLa_datcom(cla_airfoil, pf.AR, M_low, eta_airfoil, pf.sweep(0.5))
    CLa_clean = CLa_clean_user if CLa_clean_user is not None else CLa_dat
    if CLa_clean < 1.0:
        # A wing CLa is ~3-6 per rad or ~0.05-0.11 per deg: a value below 1 was given per degree
        print(f"  ! CLa_clean_user = {CLa_clean:.4f} looks like a per-DEGREE value; "
              f"converted to {math.degrees(CLa_clean):.4f} 1/rad")
        CLa_clean = math.degrees(CLa_clean)

    if DeltaY_user is not None:
        dY, dY_src = DeltaY_user, "user input"
    else:
        dat_path = airfoil_dat if os.path.isabs(airfoil_dat) else \
            os.path.join(os.path.dirname(os.path.abspath(__file__)), airfoil_dat)
        if not os.path.isfile(dat_path):
            raise FileNotFoundError(f"Airfoil file not found: {dat_path}\n"
                                    f"Put it next to this script, give an absolute path, or set DeltaY_user.")
        dY, dY_src = delta_y_from_dat(dat_path), f"from {os.path.basename(dat_path)}"
    # DATCOM evaluated with the DATCOM slope and with the slope actually used
    dat = datcom_clean(pf, clmax_airfoil, dY, CLa_dat, alpha0L_clean)
    CLmax_c = CLmax_clean if CLmax_clean is not None else dat["CLmax"]
    dalpha_c = dalpha_CLmax_clean if dalpha_CLmax_clean is not None else dat["dalpha"]

    print(f"  High-AR check (slide 29): C1 = {dat['C1']:.3f} (taper {pf.taper:.3f}) -> "
          f"4/((C1+1) cos L_LE) = {dat['AR_lim']:.2f};  AR = {pf.AR:.2f} -> "
          + ("high-AR method valid" if dat["high_AR"] else "LOW-AR wing: this method does NOT apply"))
    clamp2 = " (beyond the chart: >=2.5 curve used)" if dY > 2.5 else (" (<=1.4 curve used)" if dY < 1.4 else "")
    clamp3 = " (beyond the chart: 4 curve used)" if dY > 4 else (" (<=1.2 curve used)" if dY < 1.2 else "")
    print(f"  Delta Y = {dY:.3f} % chord ({dY_src}),  Lambda_LE = {dat['L_LE']:.2f} deg,  clmax (2D) = {clmax_airfoil:.3f}")
    print(f"  Fig. 2: CLmax/clmax = {dat['ratio']:.3f}{clamp2}")
    print(f"  Fig. 3: d_alpha_CLmax = {dat['dalpha']:.2f} deg{clamp3}")
    print()
    print(f"  {'':30s}{'DATCOM':>12s}{'USED':>12s}   source of the used value")
    line()
    print(f"  {'CLa clean [1/rad]':30s}{CLa_dat:12.4f}{CLa_clean:12.4f}   "
          + ("manual input" if CLa_clean_user is not None else f"DATCOM (M = {M_low}, eta = {eta_airfoil})"))
    print(f"  {'CLa clean [1/deg]':30s}{math.radians(CLa_dat):12.5f}{math.radians(CLa_clean):12.5f}")
    print(f"  {'CLmax clean [-]':30s}{dat['CLmax']:12.4f}{CLmax_c:12.4f}   "
          + ("manual input" if CLmax_clean is not None else "DATCOM"))
    print(f"  {'d_alpha_CLmax [deg]':30s}{dat['dalpha']:12.2f}{dalpha_c:12.2f}   "
          + ("manual input" if dalpha_CLmax_clean is not None else "DATCOM"))
    if alpha0L_clean is not None:
        a_s_used = math.degrees(CLmax_c / CLa_clean) + alpha0L_clean + dalpha_c
        print(f"  {'alpha_stall clean [deg]':30s}{dat['alpha_s']:12.2f}{a_s_used:12.2f}   "
              f"= CLmax/CLa + alpha0L ({alpha0L_clean:+.2f}) + d_alpha_CLmax")
    if not dat["high_AR"]:
        print("  ! The high-AR DATCOM method is not valid for this wing: set CLmax_clean / dalpha_CLmax_clean manually")

    line("=")
    print("HIGH-LIFT DEVICES  (Lecture 3, steps 1-5)")
    line("=")
    print(f"  HLD inboard end y = {y_hld_in:.3f} m (fuselage radius {d_fus / 2:.2f} m + {root_clearance:.2f} m)")
    for dev, extra in ((te, f"c_f/c = {te_cf_c:.3f}, hinge at {te.hinge_xc:.3f} c"),
                       (le, f"hinge line at {le.hinge_xc:.2f} c")):
        print(f"  {dev.side}: {dev.name:<20s} y = {dev.y_in:.3f} -> {dev.y_out:.3f} m "
              f"({dev.y_in / pf.half:.3f} -> {dev.y_out / pf.half:.3f} b/2),  c'/c = {dev.c_ext:.3f},  {extra}")
    for s in tor_lines:
        print(f"      {s}")

    results = {}
    for phase, da0l in (("landing", dalpha0l_landing), ("takeoff", dalpha0l_takeoff)):
        rt = te.evaluate(pf, phase, da0l, te_c_ext_TO if phase == "takeoff" else None)
        rl = le.evaluate(pf, phase, da0l)
        # Step 3: TE-only curve uses the flap extension only; the TE + LE curve also
        # counts the slat extension when slat_in_slope is True (slide 32: slats raise CLa)
        S_ratio_TE = (pf.S + rt["dS"]) / pf.S
        S_ratio_tot = (pf.S + rt["dS"] + (rl["dS"] if slat_in_slope else 0.0)) / pf.S
        results[phase] = dict(te=rt, le=rl,
                              S_ratio_TE=S_ratio_TE, S_ratio_tot=S_ratio_tot,
                              CLa_TE=S_ratio_TE * CLa_clean, CLa_tot=S_ratio_tot * CLa_clean,
                              CLmax_TE=CLmax_c + rt["dCLmax"],
                              CLmax_tot=CLmax_c + rt["dCLmax"] + rl["dCLmax"])
    two_slopes = slat_in_slope and le.extends

    def a_CLmax(r, which):
        """Linear-estimate angle at CLmax [deg]; which = 'TE' or 'tot'."""
        return alpha0L_clean + r["te"]["dalpha0L"] + math.degrees(r["CLmax_" + which] / r["CLa_" + which])

    print()
    hdr = f"  {'':34s}{'LANDING':>14s}{'TAKE-OFF':>14s}"
    print(hdr)
    line()

    def row(label, key_fn, fmt="{:14.4f}"):
        print(f"  {label:34s}" + "".join(fmt.format(key_fn(results[p])) for p in ("landing", "takeoff")))

    row(f"TE dClmax (airfoil) [-]", lambda r: r["te"]["dClmax"])
    row(f"TE Swf [m^2]", lambda r: r["te"]["Swf"], "{:14.2f}")
    row(f"TE Swf/S [-]", lambda r: r["te"]["Swf_S"])
    row(f"TE hinge-line sweep [deg]", lambda r: r["te"]["L_hinge"], "{:14.2f}")
    row(f"TE dCLmax (step 1) [-]", lambda r: r["te"]["dCLmax"])
    line()
    row(f"LE dClmax (airfoil) [-]", lambda r: r["le"]["dClmax"])
    row(f"LE Swf [m^2]", lambda r: r["le"]["Swf"], "{:14.2f}")
    row(f"LE Swf/S [-]", lambda r: r["le"]["Swf_S"])
    row(f"LE hinge-line sweep [deg]", lambda r: r["le"]["L_hinge"], "{:14.2f}")
    row(f"LE dCLmax (step 4) [-]", lambda r: r["le"]["dCLmax"])
    line()
    row(f"Total dCLmax [-]", lambda r: r["te"]["dCLmax"] + r["le"]["dCLmax"])
    row(f"CLmax clean [-]", lambda r: CLmax_c)
    row(f"CLmax with TE only [-]", lambda r: r["CLmax_TE"])
    row(f"CLmax with TE + LE [-]", lambda r: r["CLmax_tot"])
    line()
    row(f"dalpha0L (step 2) [deg]", lambda r: r["te"]["dalpha0L"], "{:14.2f}")
    row(f"CLa clean [1/rad]", lambda r: CLa_clean)
    if two_slopes:
        row(f"S'/S, TE only (step 3) [-]", lambda r: r["S_ratio_TE"])
        row(f"S'/S, TE + LE (step 3) [-]", lambda r: r["S_ratio_tot"])
        row(f"CLa flapped, TE only [1/rad]", lambda r: r["CLa_TE"])
        row(f"CLa flapped, TE + LE [1/rad]", lambda r: r["CLa_tot"])
    else:
        row(f"S'/S (step 3) [-]", lambda r: r["S_ratio_TE"])
        row(f"CLa flapped [1/rad]", lambda r: r["CLa_TE"])
    if alpha0L_clean is not None:
        row(f"alpha0L flapped [deg]", lambda r: alpha0L_clean + r["te"]["dalpha0L"], "{:14.2f}")
        a_clean = alpha0L_clean + math.degrees(CLmax_c / CLa_clean)
        row(f"alpha at CLmax TE only, lin [deg]", lambda r: a_CLmax(r, "TE"), "{:14.2f}")
        row(f"alpha at CLmax TE + LE, lin [deg]", lambda r: a_CLmax(r, "tot"), "{:14.2f}")
        print(f"  {'(clean wing, linear)':34s}{a_clean:14.2f}")
        print(f"  {'(clean wing stall, DATCOM)':34s}{a_clean + dalpha_c:14.2f}"
              f"   = CLmax/CLa + alpha0L + d_alpha_CLmax")
        print("  Flapped wing: linear estimate only. The course gives no d_alpha_CLmax for the flapped wing;")
        print("  LE devices also shift the curve slightly to higher alpha (no formula).")
        if tailstrike_deg is not None:
            worst = max(max(a_CLmax(r, "TE"), a_CLmax(r, "tot")) for r in results.values())
            ok = "OK" if worst < tailstrike_deg else "CHECK: exceeds the tail-strike angle"
            print(f"  Step 5: highest flapped alpha at CLmax {worst:.1f} deg vs tail strike {tailstrike_deg:.1f} deg -> {ok}")
    else:
        print("  (set alpha0L_clean for the absolute flapped lift curve and the plot)")
    print(f"  Take-off uses {TO_fraction_TE:.0%} (TE) and {TO_fraction_LE:.0%} (LE) of the full dClmax.")

    # ---------------------------------------------------------------- required flap span
    for phase, req in (("landing", CLmax_req_landing), ("takeoff", CLmax_req_takeoff)):
        if req is None:
            continue
        dCL_LE = results[phase]["le"]["dCLmax"]
        dCL_TE_req, Swf_req, y_req = required_te_span(pf, te, req, CLmax_c, dCL_LE, phase)
        print()
        print(f"  Required for CLmax_{phase} = {req:.3f}:  dCLmax_TE = {dCL_TE_req:.4f}")
        if dCL_TE_req <= 0:
            print("    -> already met by the clean wing + LE device; no TE device needed for this phase")
        elif y_req is None:
            print(f"    -> Swf = {Swf_req:.2f} m^2: larger than the whole span outboard of y_in. Not feasible.")
        else:
            fits = "fits inboard of the ailerons" if y_req <= y_flap_out else \
                "OVERLAPS the ailerons: pick a stronger TE device, larger c'/c, or shorter ailerons"
            print(f"    -> Swf = {Swf_req:.2f} m^2 (Swf/S = {Swf_req / pf.S:.4f}), flap from {te.y_in:.3f} to "
                  f"{y_req:.3f} m ({y_req / pf.half:.3f} b/2): {fits}")

    # ---------------------------------------------------------------- aileron report
    line("=")
    print("AILERONS  (Lecture 3, slides 54-63)")
    line("=")
    c1, c2 = pf.chord(y1_ail), pf.chord(y2_ail)
    ca1, ca2 = ca_c * c1, ca_c * c2
    lam_a = ca2 / ca1
    mac_a = 2 / 3 * ca1 * (1 + lam_a + lam_a ** 2) / (1 + lam_a)
    Sa = (ca1 + ca2) / 2 * (y2_ail - y1_ail)
    print(f"  Inboard station b1        {y1_ail:8.3f} m  ({ail_eta_in:.1%} semi-span)")
    print(f"  Outboard station b2       {y2_ail:8.3f} m  ({ail_eta_out:.1%} semi-span)")
    print(f"  Aileron span per side     {y2_ail - y1_ail:8.3f} m  ({ail_eta_out - ail_eta_in:.1%} semi-span)")
    print(f"  Aileron chord ratio       {ca_c:8.3f}")
    print(f"  Wing chord at b1 / b2     {c1:8.3f} / {c2:.3f} m")
    print(f"  Aileron chord at b1 / b2  {ca1:8.3f} / {ca2:.3f} m")
    print(f"  Aileron taper ratio       {lam_a:8.3f}")
    print(f"  Aileron MAC               {mac_a:8.3f} m")
    print(f"  Area per side / total     {Sa:8.3f} / {2 * Sa:.3f} m^2  (S_a,total/S = {2 * Sa / pf.S:.2%})")
    print(f"  Hinge line                {1 - ca_c:8.3f} x/c, sweep {pf.sweep(1 - ca_c):.2f} deg")
    print(f"  Deflection up / down      {da_up_max:8.2f} / {da_down:.2f} deg  -> average da = {da_eff:.2f} deg")
    print(f"  tau                       {tau:8.3f}  ({tau_src})")
    print(f"    (for comparison: graph {tau_g:.3f}, thin-airfoil theory {tau_th:.3f}, "
          f"graph/theory = {tau_g / tau_th:.2f}, {eta_flap} x theory = {eta_flap * tau_th:.3f})")
    line()
    print(f"  Cl_da = {Cl_da:.5f} 1/rad    Cl_p = {Cl_p:.5f} 1/rad")
    print(f"  At V = {V_roll:.1f} m/s:  P = {P:.4f} rad/s = {math.degrees(P):.2f} deg/s")
    req_txt = f"Class {roll_class}: {roll_phi} deg in {roll_t} s"
    verdict = "MEETS" if t_roll <= roll_t else "DOES NOT MEET"
    print(f"  Time to {roll_phi} deg = {t_roll:.3f} s  -> {verdict} {req_txt}")
    V_min = V_roll * t_roll / roll_t
    print(f"  Requirement met for V >= {V_min:.1f} m/s (P scales linearly with V)")
    helix = -Cl_da / Cl_p * math.radians(da_eff)
    print(f"  Steady roll helix angle pb/(2V) = -(Cl_da/Cl_p) da = {helix:.4f} rad (independent of V)")
    if helix_req is not None:
        Cl_da_target = helix_req * abs(Cl_p) / math.radians(da_eff)
        y1_hx = size_aileron_helix(pf, y2_ail, y_hld_in, tau, cla_airfoil, cd0_airfoil,
                                   math.radians(da_eff), helix_req)
        print(f"  REQ pb/(2V) >= {helix_req}: {'MET' if helix >= helix_req else 'NOT MET'} "
              f"(margin {100 * (helix / helix_req - 1):+.1f} %); target Cl_da = {Cl_da_target:.4f} 1/rad")
        if y1_hx is not None:
            print(f"    -> needs b1 <= {y1_hx:.3f} m ({y1_hx / pf.half:.3f} b/2) with b2 fixed")

    y1_min = size_aileron_inboard(pf, y2_ail, y_hld_in, tau, cla_airfoil, cd0_airfoil,
                                  math.radians(da_eff), V_roll, roll_phi, roll_t)
    print()
    if y1_min is None:
        print(f"  Sizing: even an aileron from {y_hld_in:.2f} m to b2 does not meet {req_txt} at "
              f"{V_roll:.1f} m/s. Increase c_a/c, deflection, or check V.")
    else:
        print(f"  Sizing (b2 fixed): smallest aileron meeting {req_txt} starts at b1 = {y1_min:.3f} m "
              f"({y1_min / pf.half:.3f} b/2)")
        if y1_min - gap_flap_ail <= y_hld_in:
            print("    -> no span left for the flap")
        else:
            te_alt = HLD(TE_type, y_hld_in, y1_min - gap_flap_ail, te_c_ext, 1 - te_cf_c, TO_fraction_TE)
            r_alt = te_alt.evaluate(pf, "landing", dalpha0l_landing)
            print(f"    -> the flap would then end at {y1_min - gap_flap_ail:.3f} m: Swf/S = {r_alt['Swf_S']:.4f}, "
                  f"landing dCLmax_TE = {r_alt['dCLmax']:.4f}")

    # ---------------------------------------------------------------- notes
    line("=")
    print("NOTES")
    line("=")
    if LE_y_in <= y_hld_in + 1e-9:
        print("  - Lecture 3 (slide 34): leave the LE near the fuselage unslatted so the root stalls first.")
    print(f"  - Slat outboard end = {LE_eta_out:.2f} b/2 = {LE_eta_out * pf.half:.3f} m for b = {b:.3f} m.")
    print(f"  - Flap outboard end is tied to the aileron inboard station ({y_flap_out:.3f} m).")
    print(f"  - V_roll = {V_roll} m/s is a placeholder: use the approach/landing speed of your design.")

    # ---------------------------------------------------------------- plot
    if MAKE_PLOT and alpha0L_clean is not None:
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("  (matplotlib not installed: no plot)")
            return
        fig, ax = plt.subplots(figsize=(7, 4.5))

        def a_at(a0, cla, cl):
            return a0 + math.degrees(cl / cla)

        # Clean wing: linear part, then a parabola tangent to it that peaks at (alpha_s, CLmax).
        # The tangent point lies 2*d_alpha_CLmax before alpha_s, so the extended linear curve reaches
        # CLmax exactly d_alpha_CLmax before the stall angle, as in the DATCOM figure (slide 33).
        cla_deg = math.radians(CLa_clean)
        a_s = a_at(alpha0L_clean, CLa_clean, CLmax_c) + dalpha_c
        if dalpha_c > 0:
            a_t = a_s - 2 * dalpha_c
            k = cla_deg / (4 * dalpha_c)
            n = 40
            a_par = [a_t + (a_s + 0.6 * dalpha_c - a_t) * i / n for i in range(n + 1)]
            ax.plot([alpha0L_clean] + a_par,
                    [0] + [CLmax_c - k * (a - a_s) ** 2 for a in a_par], "-", color="tab:blue")
        else:
            ax.plot([alpha0L_clean, a_s], [0, CLmax_c], "-", color="tab:blue")
        ax.plot(a_s, CLmax_c, "o", color="tab:blue",
                label=f"Clean (DATCOM stall): CLmax = {CLmax_c:.2f} at {a_s:.1f} deg")
        # Flapped wing, per phase. Hollow marker = TE only, filled = TE + LE.
        # slat_in_slope False: the LE device extends the TE line to a higher CLmax (same slope).
        # slat_in_slope True : the TE + LE line is a separate, steeper line (slat chord extension).
        for phase, col in (("takeoff", "tab:orange"), ("landing", "tab:red")):
            r = results[phase]
            a0 = alpha0L_clean + r["te"]["dalpha0L"]
            a_te = a_at(a0, r["CLa_TE"], r["CLmax_TE"])
            a_tot = a_at(a0, r["CLa_tot"], r["CLmax_tot"])
            ph = phase.capitalize()
            if two_slopes:
                ax.plot([a0, a_te], [0, r["CLmax_TE"]], "--", color=col)
                ax.plot([a0, a_tot], [0, r["CLmax_tot"]], "-", color=col)
            else:
                ax.plot([a0, a_tot], [0, r["CLmax_tot"]], "-", color=col)
            ax.plot(a_te, r["CLmax_TE"], "o", mfc="white", color=col,
                    label=f"{ph}, TE only: CLmax = {r['CLmax_TE']:.2f}"
                          + (f", CLa = {r['CLa_TE']:.2f}/rad" if two_slopes else ""))
            ax.plot(a_tot, r["CLmax_tot"], "o", color=col,
                    label=f"{ph}, TE + LE: CLmax = {r['CLmax_tot']:.2f}"
                          + (f", CLa = {r['CLa_tot']:.2f}/rad" if two_slopes else ""))
        if tailstrike_deg is not None:
            ax.axvline(tailstrike_deg, color="grey", ls=":", label="Tail strike")
        ax.axhline(0, color="black", lw=0.6)
        ax.set_xlabel("alpha [deg]")
        ax.set_ylabel("CL [-]")
        ax.set_title("Lift curves: clean wing with DATCOM stall, flapped wing linear")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
        fig.tight_layout()
        out_png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flapped_lift_curves.png")
        fig.savefig(out_png, dpi=200)
        print(f"  Plot saved to {out_png}")
        plt.show()
    elif MAKE_PLOT:
        print("  No plot: set alpha0L_clean (clean-wing zero-lift angle) in the inputs to get the lift-curve plot.")


if __name__ == "__main__":
    main()
