"""
Parametric three-view drawing (WP3, Group A11), following R. Vos, "Airplane Design and
Analysis" (ADSEE-I textbook):
  * layout: American projection (Fig. 6.15): front view rotated 90 deg clockwise to the left
    of the top view (Y aligned), side view below the top view (X aligned); one common scale;
    port wing and port HT trimmed in the top and front views
  * fuselage side view: flight deck, pilot's eye, over-nose / upward view angles,
    windshield grazing angle, tail-cone upsweep (Sec. 6.5, Example 6.8)
  * nacelle outline (Sec. 8.3.1, Fig. 8.20) and engine position on the wing (Example 8.15)
  * landing gear: tip-over, scrape and engine ground-clearance constraints in side view,
    nose-gear load limits (eq. 9.24), lateral turnover and clearance angles (eqs 9.25-9.31)
  * tail surfaces placed per Examples 9.8/9.9; drawing content per Sec. 9.4 / Assignment
    9.11 (reference areas shaded, MACs, CG range, scale, axes, ground plane, length,
    height, semi-span, over-nose / scrape / clearance angles, bulkheads, floor, exits)

Wing, tail, nacelle and CG values come from drag_geometry_inputs.py (same folder), so a
change there flows into the drawing. Inputs that only the drawing needs are in the INPUT
block below. Every value marked "ASSUMED" is a placeholder the group still has to choose
or justify; the script prints that list when it runs.

Run:  python three_view_drawing.py    ->  drawings/three_view.pdf and .png
"""
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Rectangle, Arc

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import drag_geometry_inputs as G  # noqa: E402

# ============================================================================
# INPUT BLOCK (drawing-only inputs; wing/tail/nacelle/CG inputs live in
# drag_geometry_inputs.py)
# ============================================================================
# --- Fuselage cross-section and side view (group fuselage sizing, 2026-10-14) ------
D_INNER = 2.72            # m
FLOOR_TOP_CHORD = 2.49    # m, chord of the inner circle at the floor top
FLOOR_UNDERSIDE_DEPTH = 0.58  # m, keel (inner) to floor underside
X_CABIN_START, X_CABIN_END = 3.50, 25.10   # m
X_TAILCONE_START = 25.22  # m
# ASSUMED: cockpit and nose shape (Vos Example 6.8 values unless noted)
L_FLIGHT_DECK = 2.30      # ASSUMED m, flight deck ends where the cabin starts
FD_RAISE = 0.0            # ASSUMED m, flight-deck floor above cabin floor (Vos used 0.25)
DX_PILOT_EYE = 1.00       # m behind flight-deck start (Vos Example 6.8)
H_PILOT_EYE = 1.10        # m above flight-deck floor (Vos Example 6.8)
OVERNOSE_ANGLE = 20.0     # ASSUMED deg (Vos Example 6.8; re-check after HLD/attitude)
UPWARD_VIEW_ANGLE = 25.0  # ASSUMED deg (Vos Example 6.8)
GRAZING_ANGLE = 25.0      # ASSUMED deg, windshield to over-nose sight line (< 30 deg)
DX_WINDSHIELD = 0.60      # ASSUMED m, lower windshield corner ahead of the eye
Z_NOSE_TIP_FRAC = 0.5     # ASSUMED, nose tip between keel (0) and flight-deck floor (1)
UPSWEEP_ANGLE = G.UPSWEEP_DEG  # ASSUMED deg, tail-cone upsweep; set in drag_geometry_inputs.py
X_BELLY_UPSWEEP = 25.22   # ASSUMED m, where the belly starts to rise (default: tail-cone start;
                          # moving it forward under the aft hold shortens the main gear)
H_TAIL_END = 0.30         # ASSUMED m, height (and width) of the fuselage end cap
X_FRONT_BULKHEAD = 0.80   # ASSUMED m, front pressure bulkhead (behind radome)
X_AFT_BULKHEAD = 25.40    # ASSUMED m, aft pressure bulkhead (just behind cabin end)
# Emergency exits: 76 pax -> two pairs of Type I (45 pax per pair, CS 25.807)
EXITS = [                 # ASSUMED positions: (X of exit centre [m], type, width, height)
    (X_CABIN_START + 0.45, "Type I", 0.61, 1.22),
    (X_CABIN_END - 0.45, "Type I", 0.61, 1.22),
]

# --- Wing vertical position -------------------------------------------------------
WING_ROOT_Z = None        # m, root-chord plane at the centreline; None -> low wing,
                          # lower surface 0.10 m above the keel (ASSUMED)
DIHEDRAL_W = 2.60         # deg (WP2 final)
TC_ROOT_W, TC_TIP_W = 0.12, 0.12   # SC(2)-0612
REAR_SPAR = 0.70          # x/c of the rear spar (WP2; front spar 0.20 in drag_geometry_inputs)
AIRFOIL_FILE = os.path.join(HERE, "NASA SC2-0612 AIRFOIL.dat")   # same folder, else the WP2-final copy
if not os.path.isfile(AIRFOIL_FILE):
    AIRFOIL_FILE = os.path.join(HERE, "..", "wp2-final", "code", "NASA SC2-0612 AIRFOIL.dat")

# --- Nacelle vertical position -----------------------------------------------------
NAC_GAP = 0.15            # ASSUMED m, nacelle top below the local wing lower surface
PYLON_FRAC = 0.75         # ASSUMED, pylon chord as fraction of nacelle length (drawing only)

# --- Tails -------------------------------------------------------------------------
DIHEDRAL_H = 3.0          # ASSUMED deg, low tail (Vos Sec. 9.4 suggests a small dihedral)
HT_Z_OFFSET = 0.0         # ASSUMED m, HT root plane relative to tail-cone mid-height

# --- Landing gear (Vos Sec. 9.2) ----------------------------------------------------
TIPOVER_ANGLE = 15.0      # deg (Vos typical)
SCRAPE_ANGLE = 12.0       # ASSUMED deg at MTOM, 1 g (Vos Example 9.6; check V_LOF attitude)
ENGINE_GROUND_CLEARANCE = 0.45   # m, FOD (Vos: h_g > 45 cm)
F_NLG_MIN, F_NLG_MAX = 0.06, 0.15  # steering (aft CG) / max nose-gear load (fwd CG)
X_NLG_FWD_LIMIT = 2.0     # ASSUMED m, most forward nose-gear axle (behind radome/bulkhead)
PSI_MAX = 55.0            # deg, lateral turnover
PHI_MIN = 8.0             # deg, bank-angle ground clearance
Z_CG = 0.0                # ASSUMED m, CG height on the fuselage centreline (Vos p. 240)
STROKE = 0.40             # ASSUMED m, shock-absorber stroke (Vos: 0.30-0.50)
STROKE_FRAC_1G = 2 / 3    # Vos: two-thirds compressed in the static case
# Tyres from the group's selection (Vos Fig. 3.2), sizes in inches: D x W - rim
IN = 0.0254
MLG_TYRE_D, MLG_TYRE_W, MLG_RIM_D = 34 * IN, 9.25 * IN, 16 * IN   # 34x9.25-16
NLG_TYRE_D, NLG_TYRE_W, NLG_RIM_D = 22 * IN, 6.75 * IN, 10 * IN   # 22x6.75-10
MLG_WHEELS_PER_STRUT, NLG_WHEELS = 2, 2
WHEEL_SPACING = 0.55      # ASSUMED m, centre-to-centre of a twin-wheel pair

# --- Sheet ---------------------------------------------------------------------------
SCALE = None              # 1:SCALE; None -> largest Vos Table 6.4 scale that fits the sheet
SHEET_MM = (594, 420)     # A2 landscape -> 1:100 (A3 (420, 297) -> 1:200)
TRIM_PORT = 2.0           # m of port wing shown outboard of the fuselage (top and front views)
TRIM_PORT_HT = 0.8        # m of port HT shown outboard of the tail cone
OUT_DIR = os.path.join(HERE, "drawings")
# ============================================================================

ASSUMED = [
    ("Flight-deck length", L_FLIGHT_DECK, "m"), ("Over-nose angle", OVERNOSE_ANGLE, "deg"),
    ("Upward view angle", UPWARD_VIEW_ANGLE, "deg"), ("Windshield grazing angle", GRAZING_ANGLE, "deg"),
    ("Tail-cone upsweep", UPSWEEP_ANGLE, "deg"), ("Belly upsweep start X", X_BELLY_UPSWEEP, "m"), ("Front / aft pressure bulkhead X",
                                                   f"{X_FRONT_BULKHEAD} / {X_AFT_BULKHEAD}", "m"),
    ("Exit positions (2 pairs Type I)", ", ".join(f"{e[0]:.2f}" for e in EXITS), "m"),
    ("Wing vertical position", "low wing, 0.10 m above keel", ""),
("Nacelle gap below wing", NAC_GAP, "m"),
    ("HT dihedral", DIHEDRAL_H, "deg"), ("Scrape angle", SCRAPE_ANGLE, "deg"),
    ("CG height", Z_CG, "m"), ("Stroke", STROKE, "m"),
    ("Wheels: 2 per main strut, 2 nose", "", ""),
    ("Nose-gear forward limit", X_NLG_FWD_LIMIT, "m"),
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def hermite(x0, z0, k0, x1, z1, k1, n=60):
    """Cubic Hermite curve z(x) with end slopes k0, k1."""
    t = np.linspace(0, 1, n)
    h = x1 - x0
    h00, h10 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t
    h01, h11 = -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
    return x0 + h * t, h00 * z0 + h10 * h * k0 + h01 * z1 + h11 * h * k1


def naca00(tc, n=60):
    x = (1 - np.cos(np.linspace(0, math.pi, n))) / 2
    yt = 5 * tc * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x ** 2 + 0.2843 * x ** 3 - 0.1036 * x ** 4)
    return np.r_[x[::-1], x[1:]], np.r_[yt[::-1], -yt[1:]]


def load_airfoil(path):
    try:
        pts = np.loadtxt(path, skiprows=1)
        return pts[:, 0], pts[:, 1]
    except OSError:
        return naca00(0.12)


def dim(ax, p1, p2, off, text, fs=6.5, ext=True):
    """Linear dimension between p1 and p2, offset perpendicular by 'off'."""
    p1, p2 = np.array(p1, float), np.array(p2, float)
    d = p2 - p1
    L = np.hypot(*d)
    nrm = np.array([-d[1], d[0]]) / L
    a, b = p1 + nrm * off, p2 + nrm * off
    if ext:
        for p, q in ((p1, a), (p2, b)):
            ax.plot([p[0], q[0] + nrm[0] * 0.25 * np.sign(off)], [p[1], q[1] + nrm[1] * 0.25 * np.sign(off)],
                    lw=0.35, color="0.35")
    ax.annotate("", a, b, arrowprops=dict(arrowstyle="<|-|>", lw=0.5, color="k",
                                          shrinkA=0, shrinkB=0, mutation_scale=5))
    m = (a + b) / 2 + nrm * 0.35 * np.sign(off if off else 1)
    ang = math.degrees(math.atan2(d[1], d[0]))
    if ang > 90 or ang < -90:
        ang += 180
    ax.text(m[0], m[1], text, fontsize=fs, ha="center", va="center", rotation=ang,
            bbox=dict(fc="white", ec="none", pad=0.3))


def angle_mark(ax, c, r, a0, a1, text, fs=6.5):
    ax.add_patch(Arc(c, 2 * r, 2 * r, theta1=min(a0, a1), theta2=max(a0, a1), lw=0.6, color="k"))
    am = math.radians((a0 + a1) / 2)
    ax.text(c[0] + 1.25 * r * math.cos(am), c[1] + 1.25 * r * math.sin(am), text, fontsize=fs,
            ha="center", va="center")


def label(ax, x, y, text, fs=6.0, **kw):
    ax.text(x, y, text, fontsize=fs, **kw)


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------
def build():
    g = G.compute()
    R, Rin = G.D_FUS / 2, D_INNER / 2
    L = G.L_FUS
    out = dict(g=g, R=R, L=L)

    # ---------------- fuselage side view (Vos Sec. 6.5) ----------------
    z_floor = -math.sqrt(Rin ** 2 - (FLOOR_TOP_CHORD / 2) ** 2)
    z_floor_under = -Rin + FLOOR_UNDERSIDE_DEPTH
    z_fd = z_floor + FD_RAISE
    x_fd0 = X_CABIN_START - L_FLIGHT_DECK
    x_eye, z_eye = x_fd0 + DX_PILOT_EYE, z_fd + H_PILOT_EYE
    t_on, t_up = math.tan(math.radians(OVERNOSE_ANGLE)), math.tan(math.radians(UPWARD_VIEW_ANGLE))
    # lower windshield corner on the over-nose sight line
    x_lc, z_lc = x_eye - DX_WINDSHIELD, z_eye - DX_WINDSHIELD * t_on
    # windshield pane: angle GRAZING to the sight line -> inclination (over-nose + grazing)
    inc = math.radians(OVERNOSE_ANGLE + GRAZING_ANGLE)
    # intersect pane (from lower corner, aft-up) with upward sight line (forward-up from eye)
    s = (z_eye + (x_eye - x_lc) * t_up - z_lc) / (math.sin(inc) + math.cos(inc) * t_up)
    x_uc, z_uc = x_lc + s * math.cos(inc), z_lc + s * math.sin(inc)
    z_tip = -R + Z_NOSE_TIP_FRAC * (z_fd + R)
    lnc = G.L_NOSE
    # crown: tip -> lower corner (below the sight line), pane, upper corner -> R at l_nc
    xa, za = hermite(0, z_tip, 4.0, x_lc, z_lc, 1.4 * t_on, 40)
    za = np.minimum(za, z_eye - (x_eye - xa) * t_on - 0.01 * (xa < x_lc - 1e-9))  # stay below sight line
    xb, zb = np.array([x_lc, x_uc]), np.array([z_lc, z_uc])
    xc, zc = hermite(x_uc, z_uc, math.tan(inc) * 0.6, lnc, R, 0.0, 40)
    # belly: quarter ellipse tip -> keel
    t = np.linspace(0, 1, 50)
    xbel = lnc * (1 - np.cos(t * math.pi / 2))
    zbel = z_tip - (z_tip + R) * np.sin(t * math.pi / 2)
    # tail cone with upsweep (straight line from the start of the cone on the centreline)
    xt0, ltc = X_TAILCONE_START, L - X_TAILCONE_START
    z_end = ltc * math.tan(math.radians(UPSWEEP_ANGLE))
    xct, zct = hermite(xt0, R, 0.0, L, z_end + H_TAIL_END / 2, -0.15, 50)
    xbt, zbt = hermite(min(X_BELLY_UPSWEEP, xt0), -R, 0.0, L, z_end - H_TAIL_END / 2,
                       2.2 * math.tan(math.radians(UPSWEEP_ANGLE)), 50)
    top_x = np.r_[xa, xb[1:], xc[1:], xt0, xct]
    top_z = np.r_[za, zb[1:], zc[1:], R, zct]
    bot_x = np.r_[xbel, xbt[0], xbt]
    bot_z = np.r_[zbel, -R, zbt]
    out.update(top=(top_x, top_z), bot=(bot_x, bot_z), z_floor=z_floor, z_floor_under=z_floor_under,
               z_fd=z_fd, x_fd0=x_fd0, eye=(x_eye, z_eye), lc=(x_lc, z_lc), uc=(x_uc, z_uc),
               z_tip=z_tip, z_end=z_end)
    # achieved over-nose angle: steepest sight line from the eye that clears the crown ahead
    ahead = top_x < x_eye - 0.05
    ang = np.degrees(np.arctan2(z_eye - top_z[ahead], x_eye - top_x[ahead]))
    sel = top_x[ahead] <= x_lc + 1e-6
    out["overnose_achieved"] = float(ang[sel].min())

    def ztop(x):
        return float(np.interp(x, top_x, top_z))

    def zbot(x):
        return float(np.interp(x, bot_x, bot_z))

    out["ztop"], out["zbot"] = ztop, zbot
    # top-view half width
    xh = np.r_[lnc * (1 - np.cos(t * math.pi / 2)), xt0]
    yh = np.r_[R * np.sin(t * math.pi / 2), R]
    xht, yht = hermite(xt0, R, 0.0, L, H_TAIL_END / 2, -0.12, 50)
    out["half_w"] = (np.r_[xh, xht], np.r_[yh, yht])

    # ---------------- wing ----------------
    b, cr, ct, mac, y_mac = g["b"], g["cr"], g["ct"], g["mac"], g["y_mac"]
    tanLE = math.tan(math.radians(G.SWEEP_LE_W))
    x_le_root = g["X_LEMAC"] - y_mac * tanLE      # LE of the root chord on the centreline
    zw = WING_ROOT_Z if WING_ROOT_Z is not None else -R + 0.10 + 0.5 * TC_ROOT_W * cr
    tanG = math.tan(math.radians(DIHEDRAL_W))

    def wing_le(y):
        return x_le_root + y * tanLE

    def wing_c(y):
        return G.chord_at(y, b, cr, ct)

    def wing_z(y):
        return zw + y * tanG

    out.update(x_le_root=x_le_root, zw=zw, wing_le=wing_le, wing_c=wing_c, wing_z=wing_z,
               tanLE=tanLE)

    # ---------------- nacelle (Vos Fig. 8.20) ----------------
    n = g["nac"]
    phi = 1.0 if G.NACELLE_TYPE == "B" else G.PHI
    beta = 0.35 if G.NACELLE_TYPE == "B" else 0.21 + 0.12 / math.sqrt(phi - 0.3)
    y_e = g["y_e"]
    x_hl = g["X_LEMAC"] + g["x_highlight"]
    # profile (x from highlight, radius)
    xs = [0.0, 0.08 * n["lf"], beta * n["lf"], n["lf"]]
    rs = [n["Di"] / 2, (n["Di"] + 0.6 * (n["Dn"] - n["Di"])) / 2, n["Dn"] / 2, n["Def"] / 2]
    if G.NACELLE_TYPE == "C":
        xs += [n["lf"], n["ln"], n["ln"], n["ln"] + n["lc"]]
        rs += [n["Dg"] / 2, n["Deg"] / 2, n["Dc"] / 2, 0.0]
    z_wing_lower_e = wing_z(y_e) - 0.5 * TC_ROOT_W * wing_c(y_e)
    z_nac = z_wing_lower_e - NAC_GAP - n["Dn"] / 2
    out.update(nac_x=np.array(xs) + x_hl, nac_r=np.array(rs), x_hl=x_hl, z_nac=z_nac, y_e=y_e,
               nac=n, beta=beta)
    z_nac_bottom = z_nac - n["Dn"] / 2

    # ---------------- tails ----------------
    X_ac = g["X_ac_t"]
    # HT
    b_h, cr_h, ct_h, mac_h = g["b_h"], g["cr_h"], g["ct_h"], g["mac_h"]
    tanLE_h = math.tan(math.radians(G.SWEEP_C4_H)) + (1 - G.TAPER_H) / (G.AR_H * (1 + G.TAPER_H))
    y_mac_h = b_h / 6 * (1 + 2 * G.TAPER_H) / (1 + G.TAPER_H)
    x_le_root_h = X_ac - 0.25 * mac_h - y_mac_h * tanLE_h
    z_h = 0.5 * (ztop(X_ac) + zbot(X_ac)) + HT_Z_OFFSET
    # VT: midpoint of the root chord on the upper tail-cone curve (Vos Fig. 9.11)
    b_v, cr_v, ct_v, mac_v = g["b_v"], g["cr_v"], g["ct_v"], g["mac_v"]
    tanLE_v = math.tan(math.radians(G.SWEEP_LE_V))
    z_mac_v = b_v / 3 * (1 + 2 * G.TAPER_V) / (1 + G.TAPER_V)
    x_le_root_v = X_ac - 0.25 * mac_v - z_mac_v * tanLE_v
    for _ in range(3):
        z_v0 = ztop(x_le_root_v + cr_v / 2)
    out.update(tanLE_h=tanLE_h, y_mac_h=y_mac_h, x_le_root_h=x_le_root_h, z_h=z_h,
               tanLE_v=tanLE_v, z_mac_v=z_mac_v, x_le_root_v=x_le_root_v, z_v0=z_v0)

    # ---------------- landing gear, side view (Vos Sec. 9.2) ----------------
    X_aft, X_fwd = g["X_aft"], g["X_fwd"]
    t_tip = math.tan(math.radians(TIPOVER_ANGLE))
    t_scr = math.tan(math.radians(SCRAPE_ANGLE))

    def place(zg):
        z_axle = zg + MLG_TYRE_D / 2
        x_m = X_aft + (Z_CG - z_axle) * t_tip            # tip-over line through the aft CG
        # scrape: line from the tyre contact point at SCRAPE_ANGLE must stay below the belly
        xs_ = bot_x[bot_x > x_m]
        clear = bot_z[bot_x > x_m] - (zg + (xs_ - x_m) * t_scr)
        return x_m, float(clear.min()) if clear.size else 1.0

    zg_hi = min(z_nac_bottom - ENGINE_GROUND_CLEARANCE, -R - 0.30)
    zg = zg_hi
    for _ in range(200):          # lengthen the gear until the scrape line clears the fuselage
        x_m, clr = place(zg)
        if clr >= 0:
            break
        zg -= 0.01
    x_mlg, _ = place(zg)
    out["scrape_active"] = zg < zg_hi - 1e-9
    # tail-strike angle actually available
    xs_ = bot_x[bot_x > x_mlg]
    out["scrape_achieved"] = float(np.degrees(np.arctan2(bot_z[bot_x > x_mlg] - zg, xs_ - x_mlg)).min())
    # nose gear (eq. 9.24)
    l_m_aft, l_m_fwd = x_mlg - X_aft, x_mlg - X_fwd
    x_nlg_min = X_aft - (1 / F_NLG_MIN - 1) * l_m_aft      # steering at aft CG
    x_nlg_max = X_fwd - (1 / F_NLG_MAX - 1) * l_m_fwd      # max load at fwd CG
    x_nlg = max(x_nlg_min, X_NLG_FWD_LIMIT)
    out["nlg_feasible"] = x_nlg <= x_nlg_max
    f_nlg_aft = l_m_aft / (x_mlg - x_nlg)
    f_nlg_fwd = l_m_fwd / (x_mlg - x_nlg)
    # lateral position (eqs 9.25-9.31)
    h_cg = Z_CG - zg
    l_n, l_m = X_fwd - x_nlg, x_mlg - X_fwd
    arg = l_n ** 2 * math.tan(math.radians(PSI_MAX)) ** 2 / h_cg ** 2 - 1
    y_turn = (l_m + l_n) / math.sqrt(arg) if arg > 0 else float("inf")
    h_nac = z_nac_bottom - zg
    y_clr = y_e - h_nac / math.tan(math.radians(PHI_MIN))
    x_tip_te = wing_le(b / 2) + ct
    h_tip = wing_z(b / 2) - 0.5 * TC_TIP_W * ct - zg
    y_tip = b / 2 - (h_tip + (x_mlg - x_tip_te) * math.sin(math.radians(SCRAPE_ANGLE))) / math.tan(
        math.radians(PHI_MIN))
    dh = (1 - STROKE_FRAC_1G) * STROKE + (MLG_TYRE_D - MLG_RIM_D) / 2
    y_cmp = dh / (2 * h_nac - dh) * y_e
    y_reqs = dict(turnover=y_turn, nacelle_clearance=y_clr, tip_clearance=y_tip, compressed=y_cmp)
    y_mlg = max(max(y_reqs.values()), R * 0.5)
    out.update(zg=zg, x_mlg=x_mlg, x_nlg=x_nlg, x_nlg_range=(x_nlg_min, x_nlg_max), y_mlg=y_mlg,
               y_reqs=y_reqs, f_nlg=(f_nlg_aft, f_nlg_fwd), h_cg=h_cg, h_nac=h_nac, h_tip=h_tip,
               x_tip_te=x_tip_te)
    out["phi_nac"] = math.degrees(math.atan2(h_nac, y_e - y_mlg))
    out["phi_tip"] = math.degrees(math.atan2(h_tip, b / 2 - y_mlg))
    out["psi"] = math.degrees(math.atan(h_cg * (l_m + l_n) / (l_n * y_mlg) *
                                        math.sqrt(1 + (y_mlg / (l_m + l_n)) ** 2)))
    out["height"] = (z_v0 + b_v) - zg
    # strut lengths, wheel axle to attachment (static, 1 g) and fully extended (+ the
    # compressed part of the stroke); MLG attaches at the wing lower surface, NLG at the keel
    l_mlg_static = wing_z(y_mlg) - 0.5 * TC_ROOT_W * wing_c(y_mlg) - (zg + MLG_TYRE_D / 2)
    l_nlg_static = -R - (zg + NLG_TYRE_D / 2)
    out["l_mlg"] = (l_mlg_static, l_mlg_static + STROKE_FRAC_1G * STROKE)
    out["l_nlg"] = (l_nlg_static, l_nlg_static + STROKE_FRAC_1G * STROKE)
    # MLG chordwise position at y_mlg
    out["mlg_xc"] = (x_mlg - wing_le(y_mlg)) / wing_c(y_mlg)
    return out


# ---------------------------------------------------------------------------
# drawing
# ---------------------------------------------------------------------------
LW, LW_T = 0.8, 0.45
HATCH = dict(fill=False, hatch="////", lw=0, ec="0.65")


def screen_angle_mark(ax, c, r, p_a, p_b, text, fs=6.5):
    """Arc at screen point c between the directions to screen points p_a and p_b."""
    a0 = math.degrees(math.atan2(p_a[1] - c[1], p_a[0] - c[0]))
    a1 = math.degrees(math.atan2(p_b[1] - c[1], p_b[0] - c[0]))
    if abs(a1 - a0) > 180:
        a1 += 360 if a1 < a0 else -360
    angle_mark(ax, c, r, a0, a1, text, fs)


def break_line(ax, p, q, n=4, amp=0.18, **kw):
    """Zig-zag break line between screen points p and q (trimmed geometry)."""
    p, q = np.array(p, float), np.array(q, float)
    d = q - p
    nrm = np.array([-d[1], d[0]]) / np.hypot(*d)
    t = np.linspace(0, 1, 2 * n + 1)
    off = np.array([0 if i in (0, 2 * n) else (amp if i % 2 else -amp) for i in range(2 * n + 1)])
    pts = p[None, :] + t[:, None] * d[None, :] + off[:, None] * nrm[None, :]
    ax.plot(pts[:, 0], pts[:, 1], lw=0.6, color="k", **kw)


def layout_extent(o):
    """Overall drawing size [m] for the chosen layout (used for the scale choice)."""
    g = o["g"]
    zmax = o["z_v0"] + g["b_v"]
    w = (zmax - o["zg"]) + 4.5 + o["L"] + 7.0
    h = (g["b"] / 2 + o["R"] + TRIM_PORT + 4.0) + (zmax - o["zg"]) + 9.0
    return w, h


def pick_scale(o):
    if SCALE:
        return SCALE
    w, h = layout_extent(o)
    for s in (50, 100, 200, 250, 400, 500, 1000):        # Vos Table 6.4
        if SHEET_MM[0] * s / 1000 >= w and SHEET_MM[1] * s / 1000 >= h:
            return s
    return 1000


def draw(o):
    g, R, L = o["g"], o["R"], o["L"]
    b = g["b"]
    zg = o["zg"]
    scale = pick_scale(o)
    o["scale"] = scale
    W_m, H_m = SHEET_MM[0] * scale / 1000, SHEET_MM[1] * scale / 1000   # sheet in metres
    fig = plt.figure(figsize=(SHEET_MM[0] / 25.4, SHEET_MM[1] / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_m)
    ax.set_ylim(0, H_m)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((0.5, 0.5), W_m - 1, H_m - 1, fill=False, lw=1.0))

    zv0, bv = o["z_v0"], g["b_v"]
    zmax = zv0 + bv
    # ---- view origins (American projection, Vos Fig. 6.15) ----
    # top view: nose at top0, centreline horizontal, starboard (+Y) downwards
    top0 = np.array([W_m - L - 4.0, H_m - (R + TRIM_PORT + 3.0)])
    # front view rotated 90 deg clockwise: Y downwards (aligned with the top view), Z to the right
    front0 = np.array([top0[0] - 3.5 - zmax, top0[1]])
    # side view below the top view, same X
    side0 = np.array([top0[0], top0[1] - b / 2 - 5.5 - zmax])

    def T(x, y):
        return top0[0] + np.asarray(x), top0[1] - np.asarray(y)

    def S(x, z):
        return side0[0] + np.asarray(x), side0[1] + np.asarray(z)

    def F(y, z):
        return front0[0] + np.asarray(z), front0[1] - np.asarray(y)

    def poly(fn, xs, ys, **kw):
        X, Y = fn(np.asarray(xs, float), np.asarray(ys, float))
        p = Polygon(np.c_[X, Y], closed=True, **kw)
        ax.add_patch(p)
        return p

    def line(fn, xs, ys, **kw):
        X, Y = fn(np.asarray(xs, float), np.asarray(ys, float))
        kw.setdefault("lw", LW)
        kw.setdefault("color", "k")
        ax.plot(X, Y, **kw)

    def axes_sys(origin, lab_x, lab_y, dx, dy):
        ox, oy = origin
        ax.annotate("", (ox + dx[0], oy + dx[1]), (ox, oy), arrowprops=dict(arrowstyle="-|>", lw=0.7))
        ax.annotate("", (ox + dy[0], oy + dy[1]), (ox, oy), arrowprops=dict(arrowstyle="-|>", lw=0.7))
        label(ax, ox + 1.15 * dx[0] + 0.1, oy + 1.15 * dx[1], lab_x, fs=7, va="center")
        label(ax, ox + 1.15 * dy[0] - 0.2, oy + 1.15 * dy[1] - 0.2, lab_y, fs=7, va="center")

    tx, tz = o["top"]
    bx, bz = o["bot"]
    hx, hy = o["half_w"]
    wle, wc, wz = o["wing_le"], o["wing_c"], o["wing_z"]
    ct, cr = g["ct"], g["cr"]
    mac, y_mac = g["mac"], g["y_mac"]
    afx, afz = load_airfoil(AIRFOIL_FILE)
    n0x, n0z = naca00(G.TC_H)
    n = o["nac"]
    nx, nr = o["nac_x"], o["nac_r"]
    b_h, cr_h, ct_h, mac_h, y_mac_h = g["b_h"], g["cr_h"], g["ct_h"], g["mac_h"], o["y_mac_h"]
    hle = lambda y: o["x_le_root_h"] + y * o["tanLE_h"]  # noqa: E731
    hc = lambda y: G.chord_at(y, b_h, cr_h, ct_h)        # noqa: E731
    yf_h = G.D_TAILCONE_AT_HT / 2
    y_trim_w, y_trim_h = R + TRIM_PORT, yf_h + TRIM_PORT_HT

    # ============================ TOP VIEW ============================
    # starboard wing: reference area (hatched, through the fuselage) and exposed planform
    poly(T, [o["x_le_root"], wle(b / 2), wle(b / 2) + ct, o["x_le_root"] + cr], [0, b / 2, b / 2, 0],
         **HATCH, zorder=1)
    poly(T, [wle(R), wle(b / 2), wle(b / 2) + ct, wle(R) + wc(R)], [R, b / 2, b / 2, R],
         fc="none", ec="k", lw=LW, zorder=3)
    # port wing trimmed
    yy = -y_trim_w
    poly(T, [o["x_le_root"], wle(-yy), wle(-yy) + wc(-yy), o["x_le_root"] + cr], [0, yy, yy, 0], **HATCH, zorder=1)
    line(T, [wle(R), wle(-yy)], [-R, yy], zorder=3)
    line(T, [wle(R) + wc(R), wle(-yy) + wc(-yy)], [-R, yy], zorder=3)
    break_line(ax, T(wle(-yy), yy), T(wle(-yy) + wc(-yy), yy), zorder=3)
    # spars, quarter-chord line, MAC
    for f, nm in ((G.FRONT_SPAR, "fs"), (REAR_SPAR, "rs")):
        line(T, [wle(R) + f * wc(R), wle(b / 2) + f * ct], [R, b / 2], lw=LW_T, ls="--", color="0.4")
        label(ax, *T(wle(R) + f * wc(R) - 0.15, R + 0.9), f"{nm} {f:.2f}c", fs=5.5, ha="right", rotation=-60)
    line(T, [o["x_le_root"] + 0.25 * cr, wle(b / 2) + 0.25 * ct], [0, b / 2], lw=LW_T, ls="-.", color="0.4", zorder=3)
    lam_c4 = math.degrees(math.atan2((wle(b / 2) + 0.25 * ct) - (o["x_le_root"] + 0.25 * cr), b / 2))
    pc4 = T(o["x_le_root"] + 0.25 * cr, 0)
    screen_angle_mark(ax, pc4, 3.0, T(o["x_le_root"] + 0.25 * cr, 1.0),
                      T(o["x_le_root"] + 0.25 * cr + math.tan(math.radians(lam_c4)), 1.0),
                      f"Λc/4 {lam_c4:.1f}°", fs=5.5)
    line(T, [wle(y_mac), wle(y_mac) + mac], [y_mac, y_mac], lw=1.1, color="tab:blue", zorder=4)
    ax.plot(*T(wle(y_mac), y_mac), "o", ms=3, mfc="white", mec="tab:blue", zorder=5)
    label(ax, *T(wle(y_mac) - 0.3, y_mac + 0.5), "LEMAC", fs=6, color="tab:blue", ha="right")
    label(ax, *T(wle(y_mac) + mac + 0.3, y_mac), f"MAC {mac:.2f} m", fs=6, color="tab:blue", va="center")
    label(ax, *T(wle(0.62 * b / 2) + 0.4 * wc(0.62 * b / 2), 0.62 * b / 2), r"$S_w$", fs=9, color="0.3")
    # HT: starboard full, port trimmed
    poly(T, [o["x_le_root_h"], hle(b_h / 2), hle(b_h / 2) + ct_h, o["x_le_root_h"] + cr_h], [0, b_h / 2, b_h / 2, 0],
         **HATCH, zorder=1)
    poly(T, [hle(yf_h), hle(b_h / 2), hle(b_h / 2) + ct_h, hle(yf_h) + hc(yf_h)], [yf_h, b_h / 2, b_h / 2, yf_h],
         fc="none", ec="k", lw=LW, zorder=3)
    line(T, [hle(yf_h), hle(y_trim_h)], [-yf_h, -y_trim_h], zorder=3)
    line(T, [hle(yf_h) + hc(yf_h), hle(y_trim_h) + hc(y_trim_h)], [-yf_h, -y_trim_h], zorder=3)
    break_line(ax, T(hle(y_trim_h), -y_trim_h), T(hle(y_trim_h) + hc(y_trim_h), -y_trim_h), n=3, zorder=3)
    line(T, [hle(y_mac_h), hle(y_mac_h) + mac_h], [y_mac_h, y_mac_h], lw=1.0, color="tab:blue", zorder=4)
    label(ax, *T(hle(y_mac_h) + mac_h + 0.3, y_mac_h), f"MAC_h {mac_h:.2f}", fs=6, color="tab:blue", va="center")
    label(ax, *T(hle(0.55 * b_h / 2) + 0.35 * hc(0.55 * b_h / 2), 0.55 * b_h / 2), r"$S_h$", fs=8, color="0.3")
    ax.plot(*T(g["X_ac_t"], 0), "+", color="tab:blue", ms=7, zorder=7)
    # fuselage (white fill hides the wing root)
    X, Y = T(np.r_[hx, hx[::-1]], np.r_[hy, -hy[::-1]])
    ax.add_patch(Polygon(np.c_[X, Y], closed=True, fc="white", ec="k", lw=LW, zorder=2))
    line(T, [-0.8, L + 0.8], [0, 0], lw=0.35, ls=(0, (8, 2, 1, 2)), color="0.4", zorder=2.1)
    # VT seen from above
    for (xle, c) in ((o["x_le_root_v"], g["cr_v"]), (o["x_le_root_v"] + bv * o["tanLE_v"], g["ct_v"])):
        poly(T, xle + n0x * c, n0z * c / G.TC_H * G.TC_V, fc="white", ec="k", lw=LW_T, zorder=5)
    # starboard nacelle (part under the wing dashed)
    X, Y = T(np.r_[nx, nx[::-1]], o["y_e"] + np.r_[nr, -nr[::-1]])
    ax.add_patch(Polygon(np.c_[X, Y], closed=True, fc="white", ec="k", lw=LW, zorder=2.5))
    ax.plot(X, Y, lw=LW_T, ls=(0, (3, 2)), color="k", zorder=6)
    # cabin walls, flight deck, exits
    for xx in (X_CABIN_START, X_CABIN_END):
        line(T, [xx, xx], [-D_INNER / 2, D_INNER / 2], lw=LW_T, ls="-.", color="0.4", zorder=5)
    for (xe_, typ, w, h) in EXITS:
        for sgn in (1, -1):
            poly(T, [xe_ - w / 2, xe_ + w / 2, xe_ + w / 2, xe_ - w / 2],
                 sgn * np.array([R - 0.12, R - 0.12, R + 0.12, R + 0.12]), fc="k", ec="k", zorder=6)
        label(ax, *T(xe_, -R - 0.55), typ, fs=5.5, ha="center")
    label(ax, *T(o["x_fd0"] + 0.2, 0.15), "flight\ndeck", fs=5, zorder=6)
    # CG range and gear
    for xx in (g["X_fwd"], g["X_aft"]):
        line(T, [xx, xx], [-0.6, 0.6], lw=0.9, color="tab:red", zorder=7)
    label(ax, *T(g["X_fwd"] - 0.4, -0.75), "fwd/aft CG", fs=5.5, color="tab:red", ha="right", zorder=7)
    for sgn in (1, -1):
        for k in (-0.5, 0.5):
            poly(T, o["x_mlg"] + np.array([-1, 1, 1, -1]) * MLG_TYRE_D / 2,
                 sgn * o["y_mlg"] + k * WHEEL_SPACING + np.array([-1, -1, 1, 1]) * MLG_TYRE_W / 2,
                 fc="0.85", ec="k", lw=LW_T, zorder=6)
    for k in (-0.5, 0.5):
        poly(T, o["x_nlg"] + np.array([-1, 1, 1, -1]) * NLG_TYRE_D / 2,
             k * 0.45 + np.array([-1, -1, 1, 1]) * NLG_TYRE_W / 2, fc="0.85", ec="k", lw=LW_T, zorder=6)
    label(ax, *T(o["x_mlg"] + 0.6, o["y_mlg"] + 0.9), "main gear", fs=5.5, zorder=7)
    label(ax, *T(o["x_nlg"] - 0.3, -0.9), "nose gear", fs=5.5, zorder=7, ha="center")
    # dimensions
    ytop = -(y_trim_w + 0.4)
    dim(ax, T(0, ytop), T(G.L_NOSE, ytop), 0, f"l_nc {G.L_NOSE:.2f}", fs=5.5, ext=False)
    dim(ax, T(X_CABIN_START, ytop - 1.0), T(X_CABIN_END, ytop - 1.0), 0, f"l_cabin {X_CABIN_END - X_CABIN_START:.2f}",
        fs=5.5, ext=False)
    dim(ax, T(X_TAILCONE_START, ytop), T(L, ytop), 0, f"l_tc {L - X_TAILCONE_START:.2f}", fs=5.5, ext=False)
    dim(ax, T(X_CABIN_END, ytop - 1.0), T(L, ytop - 1.0), 0, f"l_t {L - X_CABIN_END:.2f}", fs=5.5, ext=False)
    dim(ax, T(X_CABIN_START + 1.0, -R), T(X_CABIN_START + 1.0, R), 0, f"w_fus {G.D_FUS:.3f}", fs=5.5, ext=False)
    dim(ax, T(o["x_le_root"], 0), T(o["x_le_root"] + cr, 0), 0, f"c_r {cr:.2f}", fs=5.5, ext=False)
    dim(ax, T(wle(b / 2), b / 2 + 0.2), T(wle(b / 2) + ct, b / 2 + 0.2), -0.5, f"c_t {ct:.2f}", fs=5.5)
    xb2 = wle(b / 2) + ct + 1.2
    dim(ax, T(xb2, 0), T(xb2, b / 2), 0, f"b/2 = {b / 2:.2f} m", ext=False)
    xe2 = o["x_hl"] - 1.0
    dim(ax, T(xe2, 0), T(xe2, o["y_e"]), 0, f"y_e {o['y_e']:.2f} (2y_e/b = {G.ENG_SPAN_FRAC})", fs=5.5, ext=False)
    dim(ax, T(o["x_hl"], o["y_e"] + n["Dn"] / 2 + 0.4), T(nx[-1], o["y_e"] + n["Dn"] / 2 + 0.4), 0,
        f"l_n + l_c {n['ln'] + n['lc']:.2f}", fs=5.5, ext=False)
    xdn = o["x_hl"] + o["beta"] * n["lf"]
    dim(ax, T(xdn, o["y_e"] - n["Dn"] / 2), T(xdn, o["y_e"] + n["Dn"] / 2), 0, f"D_n {n['Dn']:.2f}", fs=5, ext=False)
    xh2 = hle(b_h / 2) + ct_h + 1.0
    dim(ax, T(xh2, 0), T(xh2, b_h / 2), 0, f"b_h/2 {b_h / 2:.2f}", fs=5.5, ext=False)
    dim(ax, T(hle(b_h / 2), b_h / 2 + 0.2), T(hle(b_h / 2) + ct_h, b_h / 2 + 0.2), -0.5, f"c_t,h {ct_h:.2f}", fs=5.5)
    dim(ax, T(o["x_le_root_h"], 0), T(o["x_le_root_h"] + cr_h, 0), 0, f"c_r,h {cr_h:.2f}", fs=5, ext=False)
    dim(ax, T(g["X_aft"], b / 2 * 0.25), T(g["X_ac_t"], b / 2 * 0.25), 0, f"l_h = l_v {g['l_h']:.2f}", fs=5.5)
    label(ax, *T(g["X_LEMAC"], b / 2 + 1.6), f"X_LEMAC = {g['X_LEMAC']:.2f} m", fs=6)
    axes_sys(T(-2.5, -1.5), "X", "Y", (1.8, 0), (0, -1.8))
    label(ax, *T(L / 2 + 6, b / 2 + 2.6), "Top view", fs=10, weight="bold")

    # ============================ FRONT VIEW (rotated 90 deg clockwise) ============================
    # ground plane: vertical line at Z = zg
    line(F, [-y_trim_w - 1.0, b / 2 + 1.0], [zg, zg], lw=1.0)
    for yy_ in np.arange(-y_trim_w - 1.0, b / 2 + 1.0, 0.6):
        line(F, [yy_, yy_ + 0.4], [zg, zg - 0.4], lw=0.3)
    # VT
    tv = G.TC_V * g["cr_v"] / 2
    poly(F, [-tv, -G.TC_V * g["ct_v"] / 2, G.TC_V * g["ct_v"] / 2, tv], [zv0, zmax, zmax, zv0],
         fc="white", ec="k", lw=LW_T, zorder=1)
    # HT (starboard full, port trimmed)
    tgh = math.tan(math.radians(DIHEDRAL_H))
    ys = np.array([yf_h, b_h / 2, b_h / 2, yf_h])
    th = np.array([G.TC_H * hc(yf_h), G.TC_H * ct_h, -G.TC_H * ct_h, -G.TC_H * hc(yf_h)]) / 2
    poly(F, ys, o["z_h"] + ys * tgh + th, fc="white", ec="k", lw=LW_T, zorder=1.5)
    ysp = np.array([yf_h, y_trim_h])
    for sg in (1, -1):
        line(F, -ysp, o["z_h"] + ysp * tgh + sg * G.TC_H * hc(ysp) / 2, lw=LW_T, zorder=1.5)
    # wing (starboard full, port trimmed) with dihedral
    ys = np.array([R * 0.7, b / 2, b / 2, R * 0.7])
    th = np.array([TC_ROOT_W * wc(R), TC_TIP_W * ct, -TC_TIP_W * ct, -TC_ROOT_W * wc(R)]) / 2
    poly(F, ys, wz(ys) + th, fc="white", ec="k", lw=LW, zorder=2)
    ysp = np.array([R * 0.7, y_trim_w])
    for sg in (1, -1):
        line(F, -ysp, wz(ysp) + sg * TC_ROOT_W * wc(ysp) / 2, zorder=2)
    break_line(ax, F(-y_trim_w, wz(y_trim_w) - TC_ROOT_W * wc(y_trim_w) / 2 - 0.15),
               F(-y_trim_w, wz(y_trim_w) + TC_ROOT_W * wc(y_trim_w) / 2 + 0.15), n=2, zorder=2)
    # dihedral
    line(F, [R, b / 2], [wz(R), wz(R)], lw=0.35, ls=":", color="0.3")
    screen_angle_mark(ax, F(R, wz(R)), 6.0, F(b / 2, wz(R)), F(b / 2, wz(b / 2)), f"Γ {DIHEDRAL_W}°", fs=6)
    # fuselage
    ax.add_patch(Circle(F(0, 0), R, fc="white", ec="k", lw=LW, zorder=3))
    ax.add_patch(Circle(F(0, 0), D_INNER / 2, fill=False, ec="0.5", lw=0.3, ls=":", zorder=3))
    hw = FLOOR_TOP_CHORD / 2
    line(F, [-hw, hw], [o["z_floor"]] * 2, lw=LW_T, zorder=3.1)
    line(F, [-1.1, 1.1], [o["z_floor_under"]] * 2, lw=LW_T, ls=":", zorder=3.1)
    # starboard nacelle and pylon
    zpt = wz(o["y_e"]) - 0.5 * TC_ROOT_W * wc(o["y_e"])
    ax.add_patch(Circle(F(o["y_e"], o["z_nac"]), n["Dn"] / 2, fc="white", ec="k", lw=LW, zorder=4))
    ax.add_patch(Circle(F(o["y_e"], o["z_nac"]), n["Di"] / 2, fc="none", ec="k", lw=LW_T, zorder=4))
    ax.add_patch(Circle(F(o["y_e"], o["z_nac"]), 0.12, fc="0.5", ec="k", lw=0.3, zorder=4))
    poly(F, o["y_e"] + np.array([-0.08, 0.08, 0.08, -0.08]), [o["z_nac"] + n["Dn"] / 2] * 2 + [zpt] * 2,
         fc="white", ec="k", lw=LW_T, zorder=3.9)
    # landing gear
    for sgn in (1, -1):
        for k in (-0.5, 0.5):
            poly(F, sgn * o["y_mlg"] + k * WHEEL_SPACING + np.array([-1, 1, 1, -1]) * MLG_TYRE_W / 2,
                 zg + np.array([0, 0, MLG_TYRE_D, MLG_TYRE_D]), fc="0.85", ec="k", lw=LW_T, zorder=5)
        line(F, [sgn * o["y_mlg"]] * 2, [zg + MLG_TYRE_D / 2, wz(o["y_mlg"])], lw=1.3, zorder=4.9)
    for k in (-0.5, 0.5):
        poly(F, k * 0.45 + np.array([-1, 1, 1, -1]) * NLG_TYRE_W / 2, zg + np.array([0, 0, NLG_TYRE_D, NLG_TYRE_D]),
             fc="0.85", ec="k", lw=LW_T, zorder=5)
    line(F, [0, 0], [zg + NLG_TYRE_D / 2, -R], lw=1.3, zorder=4.9)
    # clearance angles from the outer main tyre contact point
    yc = o["y_mlg"] + WHEEL_SPACING / 2 + MLG_TYRE_W / 2
    z_nb = o["z_nac"] - n["Dn"] / 2
    z_tb = wz(b / 2) - TC_TIP_W * ct / 2
    line(F, [yc, o["y_e"]], [zg, z_nb], lw=0.5, ls="--", color="tab:red", zorder=6)
    line(F, [yc, b / 2], [zg, z_tb], lw=0.5, ls="--", color="tab:red", zorder=6)
    phi_n = math.degrees(math.atan2(z_nb - zg, o["y_e"] - yc))
    phi_t = math.degrees(math.atan2(z_tb - zg, b / 2 - yc))
    screen_angle_mark(ax, F(yc, zg), 7.0, F(b / 2, zg), F(b / 2, z_tb), f"φ_tip {phi_t:.1f}°", fs=6)
    screen_angle_mark(ax, F(yc, zg), 2.2, F(b / 2, zg), F(o["y_e"], z_nb), f"φ_nac {phi_n:.1f}°", fs=6)
    # dimensions
    dim(ax, F(0, zmax + 1.2), F(b / 2, zmax + 1.2), 0, f"b/2 = {b / 2:.2f} m", ext=False)
    dim(ax, F(o["y_e"], zg), F(o["y_e"], z_nb), 0, f"h_nac {o['h_nac']:.2f}", fs=5.5, ext=False)
    dz_e = wz(o["y_e"]) - o["z_nac"]
    dim(ax, F(o["y_e"] + 1.2, o["z_nac"]), F(o["y_e"] + 1.2, wz(o["y_e"])), 0, f"Δz_e {dz_e:.2f}", fs=5.5)
    dim(ax, F(-y_trim_w - 1.8, zg), F(-y_trim_w - 1.8, Z_CG), 0, f"h_CG {o['h_cg']:.2f}", fs=5.5, ext=False)
    dim(ax, F(o["y_mlg"], zg - 0.9), F(-o["y_mlg"], zg - 0.9), 0, f"track {2 * o['y_mlg']:.2f}", fs=5.5,
        ext=False)
    dim(ax, F(b / 2 + 0.6, zg), F(b / 2 + 0.6, zmax), 0, f"h = {o['height']:.2f} m", ext=False)
    label(ax, *F(-0.4, zg + 0.3), "ground plane", fs=5.5, rotation=90, va="bottom")
    axes_sys(F(b / 2 - 2.5, zmax - 2.5), "Z", "Y", (1.8, 0), (0, -1.8))
    label(ax, *F(b / 2 + 2.6, zg + 0.5), "Front view", fs=10, weight="bold")

    # ============================ SIDE VIEW ============================
    line(S, [-1.5, L + 1.5], [zg, zg], lw=1.0)
    for xx in np.arange(-1.5, L + 1.5, 0.6):
        line(S, [xx, xx - 0.4], [zg, zg - 0.4], lw=0.3)
    label(ax, *S(L - 3.5, zg - 1.0), "ground plane", fs=6)
    # VT (true shape) with reference area, MAC, dimensions
    xv0 = o["x_le_root_v"]
    vt = ([xv0, xv0 + bv * o["tanLE_v"], xv0 + bv * o["tanLE_v"] + g["ct_v"], xv0 + g["cr_v"]], [zv0, zmax, zmax, zv0])
    poly(S, *vt, fc="white", ec="k", lw=LW, zorder=2)
    poly(S, *vt, **HATCH, zorder=2.1)
    xm_v = xv0 + o["z_mac_v"] * o["tanLE_v"]
    line(S, [xm_v, xm_v + g["mac_v"]], [zv0 + o["z_mac_v"]] * 2, lw=1.0, color="tab:blue", zorder=5)
    label(ax, *S(xm_v + g["mac_v"] + 0.2, zv0 + o["z_mac_v"]), f"MAC_v {g['mac_v']:.2f}", fs=6, color="tab:blue",
          va="center")
    ax.plot(*S(g["X_ac_t"], zv0 + o["z_mac_v"]), "+", color="tab:blue", ms=7, zorder=7)
    label(ax, *S(xm_v + 0.5, zv0 + 0.35 * bv), r"$S_v$", fs=8, color="0.3", zorder=6)
    dim(ax, S(xv0 + bv * o["tanLE_v"], zmax), S(xv0 + bv * o["tanLE_v"] + g["ct_v"], zmax), 0.5,
        f"c_t,v {g['ct_v']:.2f}", fs=5.5)
    dim(ax, S(xv0 - 1.0, zv0), S(xv0 - 1.0, zmax), 0, f"b_v {bv:.2f}", fs=5.5, ext=False)
    dim(ax, S(xv0, zv0 - 0.0), S(xv0 + g["cr_v"], zv0), -0.0, "", ext=False)
    label(ax, *S(xv0 + 0.2, zv0 + 0.15), f"c_r,v {g['cr_v']:.2f}", fs=5.5, zorder=6)
    screen_angle_mark(ax, S(xv0, zv0), 1.8, S(xv0, zmax), S(xv0 + bv * o["tanLE_v"], zmax),
                      f"Λ_LE,v {G.SWEEP_LE_V:.0f}°", fs=5.5)
    # fuselage
    X, Y = S(np.r_[tx, bx[::-1]], np.r_[tz, bz[::-1]])
    ax.add_patch(Polygon(np.c_[X, Y], closed=True, fc="white", ec="k", lw=LW, zorder=3))
    line(S, [-0.8, L + 0.8], [0, 0], lw=0.35, ls=(0, (8, 2, 1, 2)), color="0.4", zorder=3.1)
    line(S, [X_CABIN_START, X_CABIN_END], [o["z_floor"]] * 2, lw=LW_T, zorder=4)
    line(S, [X_CABIN_START - 0.2, X_CABIN_END], [o["z_floor_under"]] * 2, lw=LW_T, ls=":", zorder=4)
    line(S, [o["x_fd0"], X_CABIN_START], [o["z_fd"]] * 2, lw=LW_T, zorder=4)
    label(ax, *S(X_CABIN_START + 4.0, o["z_floor"] + 0.15), "main deck", fs=5.5, zorder=4)
    label(ax, *S(X_CABIN_START + 4.0, o["z_floor_under"] - 0.45), "lower deck", fs=5.5, zorder=4)
    label(ax, *S(o["x_fd0"] + 0.1, o["z_fd"] + 0.12), "flight deck", fs=5, zorder=4)
    for xx, nm in ((X_FRONT_BULKHEAD, "front pressure bulkhead"), (X_AFT_BULKHEAD, "aft pressure bulkhead")):
        zt, zb_ = o["ztop"](xx) - 0.08, o["zbot"](xx) + 0.08
        th_ = np.linspace(-1, 1, 30)
        bulge = 0.35 if xx > L / 2 else -0.15
        line(S, xx + bulge * (1 - th_ ** 2), (zt + zb_) / 2 + th_ * (zt - zb_) / 2, lw=LW_T, color="0.3", zorder=4)
        if xx > L / 2:
            label(ax, *S(xx + 0.3, o["zbot"](xx) - 0.8), nm, fs=5.5, ha="left")
        else:
            label(ax, *S(xx, o["zbot"](xx) - 0.9), nm, fs=5.5, ha="left")
    for (xe_, typ, w, h) in EXITS:
        poly(S, [xe_ - w / 2, xe_ + w / 2, xe_ + w / 2, xe_ - w / 2],
             [o["z_floor"], o["z_floor"], o["z_floor"] + h, o["z_floor"] + h], fc="none", ec="k", lw=LW_T, zorder=4)
        label(ax, *S(xe_, o["z_floor"] + h + 0.2), typ, fs=5.5, ha="center", zorder=4)
    # pilot's eye and view angles
    xe, ze = o["eye"]
    ax.plot(*S(xe, ze), "ko", ms=2.5, zorder=6)
    label(ax, *S(xe + 0.25, ze + 0.12), "pilot's eye", fs=5, zorder=6)
    t_on = math.tan(math.radians(OVERNOSE_ANGLE))
    t_up = math.tan(math.radians(UPWARD_VIEW_ANGLE))
    line(S, [xe, xe - 3.0], [ze, ze - 3.0 * t_on], lw=0.5, ls="--", color="tab:green", zorder=6)
    line(S, [xe, xe - 2.5], [ze, ze + 2.5 * t_up], lw=0.5, ls="--", color="tab:green", zorder=6)
    line(S, [xe, xe - 3.0], [ze, ze], lw=0.4, ls=":", color="tab:green", zorder=6)
    angle_mark(ax, S(xe, ze), 2.2, 180, 180 + OVERNOSE_ANGLE, f"{OVERNOSE_ANGLE:.0f}°")
    angle_mark(ax, S(xe, ze), 1.6, 180 - UPWARD_VIEW_ANGLE, 180, f"{UPWARD_VIEW_ANGLE:.0f}°")
    # wing (starboard): exposed root and tip sections, LE/TE lines, MAC
    for y in (R, b / 2):
        c = wc(y)
        poly(S, wle(y) + afx * c, wz(y) + afz * c, fc="white", ec="k", lw=LW_T, zorder=4.5)
    line(S, [wle(R), wle(b / 2)], [wz(R), wz(b / 2)], lw=LW_T, zorder=4.5)
    line(S, [wle(R) + wc(R), wle(b / 2) + ct], [wz(R), wz(b / 2)], lw=LW_T, zorder=4.5)
    line(S, [g["X_LEMAC"], g["X_LEMAC"] + mac], [wz(y_mac)] * 2, lw=1.0, color="tab:blue", zorder=5)
    # HT tip section
    yt_h = b_h / 2
    zh_tip = o["z_h"] + yt_h * math.tan(math.radians(DIHEDRAL_H))
    poly(S, hle(yt_h) + n0x * ct_h, zh_tip + n0z * ct_h, fc="white", ec="k", lw=LW_T, zorder=4.5)
    line(S, [hle(yf_h), hle(yt_h)], [o["z_h"], zh_tip], lw=LW_T, zorder=4.5)
    line(S, [hle(yf_h) + hc(yf_h), hle(yt_h) + ct_h], [o["z_h"], zh_tip], lw=LW_T, zorder=4.5)
    # nacelle, pylon, engine offset
    X, Y = S(np.r_[nx, nx[::-1]], o["z_nac"] + np.r_[nr, -nr[::-1]])
    ax.add_patch(Polygon(np.c_[X, Y], closed=True, fc="white", ec="k", lw=LW, zorder=5.5))
    xp0 = o["x_hl"] + 0.15 * n["ln"]
    poly(S, [xp0, xp0 + PYLON_FRAC * n["ln"], wle(o["y_e"]) + 0.7 * wc(o["y_e"]), wle(o["y_e"]) + 0.05],
         [o["z_nac"] + n["Dn"] / 2 - 0.05, o["z_nac"] + n["Dg"] / 2, zpt, zpt], fc="white", ec="k", lw=LW_T,
         zorder=5.4)
    dim(ax, S(o["x_hl"] - 0.6, o["z_nac"]), S(o["x_hl"] - 0.6, wz(o["y_e"])), 0, f"Δz_e {dz_e:.2f}", fs=5.5)
    # landing gear
    za = zg + MLG_TYRE_D / 2
    ax.add_patch(Circle(S(o["x_mlg"], za), MLG_TYRE_D / 2, fc="0.85", ec="k", lw=LW, zorder=6))
    line(S, [o["x_mlg"], o["x_mlg"]], [za, wz(o["y_mlg"]) - 0.05], lw=1.4, zorder=5.9)
    zn = zg + NLG_TYRE_D / 2
    ax.add_patch(Circle(S(o["x_nlg"], zn), NLG_TYRE_D / 2, fc="0.85", ec="k", lw=LW, zorder=6))
    line(S, [o["x_nlg"], o["x_nlg"]], [zn, o["zbot"](o["x_nlg"])], lw=1.4, zorder=5.9)
    # CG range, tip-over, scrape, nose-gear load
    for xx in (g["X_fwd"], g["X_aft"]):
        ax.plot(*S(xx, Z_CG), marker="o", ms=4, mfc="white", mec="tab:red", zorder=7)
    label(ax, *S(g["X_fwd"] - 0.3, Z_CG + 0.3), "fwd/aft CG", fs=5.5, color="tab:red", ha="right", zorder=7)
    t_tip = math.tan(math.radians(TIPOVER_ANGLE))
    line(S, [g["X_aft"], g["X_aft"] + (Z_CG - zg) * t_tip], [Z_CG, zg], lw=0.6, ls="--", color="tab:red", zorder=7)
    line(S, [g["X_aft"], g["X_aft"]], [Z_CG, zg], lw=0.4, ls=":", color="tab:red", zorder=7)
    angle_mark(ax, S(g["X_aft"], Z_CG), 1.3, 270, 270 + TIPOVER_ANGLE, f"θ_tip {TIPOVER_ANGLE:.0f}°", fs=5.5)
    t_s = math.tan(math.radians(SCRAPE_ANGLE))
    line(S, [o["x_mlg"], L + 0.5], [zg, zg + (L + 0.5 - o["x_mlg"]) * t_s], lw=0.6, ls="--", color="tab:red", zorder=7)
    angle_mark(ax, S(o["x_mlg"], zg), 4.0, 0, SCRAPE_ANGLE, f"θ_scrape {SCRAPE_ANGLE:.0f}°", fs=5.5)
    label(ax, *S(o["x_nlg"] + 0.6, zg + 0.5), f"NLG load {100 * o['f_nlg'][0]:.0f}% (aft CG) / "
                                             f"{100 * o['f_nlg'][1]:.0f}% (fwd CG)", fs=5.5)
    # tail-cone upsweep
    line(S, [X_TAILCONE_START, L], [0, o["z_end"]], lw=0.4, ls="-.", color="0.4", zorder=4)
    angle_mark(ax, S(X_TAILCONE_START, 0), 5.5, 0, UPSWEEP_ANGLE, f"{UPSWEEP_ANGLE:.0f}°")
    # dimensions
    dim(ax, S(0, zg), S(L, zg), -1.9, f"l_fus = {L:.2f} m")
    dim(ax, S(L + 2.0, zg), S(L + 2.0, zmax), 0, f"h = {o['height']:.2f} m", ext=False)
    dim(ax, S(0, zmax - 0.3), S(X_CABIN_START, zmax - 0.3), 0, f"l_n {X_CABIN_START:.2f}", fs=5.5, ext=False)
    dim(ax, S(X_CABIN_START, zmax - 0.3), S(X_CABIN_END, zmax - 0.3), 0, f"l_cabin {X_CABIN_END - X_CABIN_START:.2f}",
        fs=5.5, ext=False)
    dim(ax, S(0, zmax - 1.3), S(G.L_NOSE, zmax - 1.3), 0, f"l_nc {G.L_NOSE:.2f}", fs=5.5, ext=False)
    dim(ax, S(o["x_nlg"], zg), S(o["x_mlg"], zg), -1.0, f"wheelbase {o['x_mlg'] - o['x_nlg']:.2f} m", fs=5.5)
    dim(ax, S(-1.0, -R), S(-1.0, R), 0, f"h_fus {G.D_FUS:.3f}", fs=5.5, ext=False)
    axes_sys(S(-2.5, zg + 0.5), "X", "Z", (1.8, 0), (0, 1.8))
    label(ax, *S(L / 2 - 2, zg - 3.4), "Side view", fs=10, weight="bold")

    # ============================ scale bar and data box ============================
    sx, sy = 1.5, 1.6
    for i in range(5):
        ax.add_patch(Rectangle((sx + i, sy), 1, 0.3, fc="k" if i % 2 == 0 else "white", ec="k", lw=0.4))
    for i in (0, 5):
        label(ax, sx + i, sy - 0.5, f"{i}", fs=6, ha="center")
    label(ax, sx + 5.3, sy - 0.5, "[m]", fs=6)
    label(ax, sx, sy + 0.6, f"Scale 1:{scale} on {SHEET_MM[0]}x{SHEET_MM[1]} mm", fs=7)
    box = [
        "AE2111 Group A11 regional jet, three-view (Vos, ADSEE-I, Sec. 9.4); port wing and HT trimmed",
        f"MTOM {G.MTOM:,.0f} kg   S_w {G.S_W:.1f} m²   A {G.AR_W}   b {b:.2f} m   "
        f"Λ_LE {G.SWEEP_LE_W:.1f}°   Γ {DIHEDRAL_W}°   spars {G.FRONT_SPAR:.2f}/{REAR_SPAR:.2f} c",
        f"S_h {g['S_h']:.2f} m²   S_v {g['S_v']:.2f} m²   l_h = l_v {g['l_h']:.2f} m   "
        f"V̄_h {G.VBAR_H}   V̄_v {G.VBAR_V}",
        f"CG range {(g['X_fwd'] - g['X_LEMAC']) / mac:.2f}–{(g['X_aft'] - g['X_LEMAC']) / mac:.2f} MAC   "
        f"X_LEMAC {g['X_LEMAC']:.2f} m",
        f"2× CF34-8E5: l_n {n['ln']:.2f} m, D_n {n['Dn']:.2f} m, D_i {n['Di']:.2f} m",
        f"MLG at X {o['x_mlg']:.2f} m ({o['mlg_xc']:.2f} c local), track {2 * o['y_mlg']:.2f} m; "
        f"NLG at X {o['x_nlg']:.2f} m",
        f"over-nose {o['overnose_achieved']:.1f}°, scrape {o['scrape_achieved']:.1f}°, "
        f"turnover ψ {o['psi']:.1f}°, φ_nac {phi_n:.1f}°, φ_tip {phi_t:.1f}°",
    ]
    for i, s_ in enumerate(box):
        label(ax, 1.5, sy + 1.6 + 0.7 * (len(box) - i), s_, fs=6.5)
    return fig


def main():
    o = build()
    g = o["g"]
    os.makedirs(OUT_DIR, exist_ok=True)
    fig = draw(o)
    fig.savefig(os.path.join(OUT_DIR, "three_view.pdf"))
    fig.savefig(os.path.join(OUT_DIR, "three_view.png"), dpi=150)
    p = print
    p(f"Three-view written to {OUT_DIR} (scale 1:{o['scale']})")
    p(f"  pilot's eye X {o['eye'][0]:.2f} Z {o['eye'][1]:.2f} m; over-nose achieved {o['overnose_achieved']:.1f}° "
      f"(target {OVERNOSE_ANGLE})")
    p(f"  ground plane Z {o['zg']:.2f} m (h_CG {o['h_cg']:.2f} m); scrape constraint "
      f"{'active' if o['scrape_active'] else 'not active (engine clearance sets the gear height)'}; "
      f"tail-strike angle {o['scrape_achieved']:.1f}°")
    p(f"  MLG X {o['x_mlg']:.2f} m = {o['mlg_xc']:.2f} local chord at y {o['y_mlg']:.2f} m; "
      f"lateral requirements: " + ", ".join(f"{k} {v:.2f}" for k, v in o['y_reqs'].items()))
    p(f"  NLG X {o['x_nlg']:.2f} m; feasible range {o['x_nlg_range'][0]:.2f} .. {o['x_nlg_range'][1]:.2f} m "
      f"({'OK' if o['nlg_feasible'] else 'NOT FEASIBLE: move MLG aft or widen CG range'}); "
      f"load {100 * o['f_nlg'][0]:.1f}% aft CG / {100 * o['f_nlg'][1]:.1f}% fwd CG")
    p(f"  turnover angle {o['psi']:.1f}° (max {PSI_MAX}); nacelle height {o['h_nac']:.2f} m; "
      f"aircraft height {o['height']:.2f} m")
    p(f"  strut length axle-attachment, static / extended: MLG {o['l_mlg'][0]:.2f} / {o['l_mlg'][1]:.2f} m, "
      f"NLG {o['l_nlg'][0]:.2f} / {o['l_nlg'][1]:.2f} m")
    p("\nASSUMED inputs still to be justified:")
    for nm, v, u in ASSUMED:
        p(f"  - {nm}: {v} {u}")


if __name__ == "__main__":
    main()
