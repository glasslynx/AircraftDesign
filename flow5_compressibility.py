#!/usr/bin/env python3
"""
flow5 / XFLR5 compressibility correction for foil (2D) and plane (3D) polars
==============================================================================

Takes incompressible polars exported from flow5 (or XFLR5 / XFoil text format),
applies compressibility corrections for a swept wing at the cruise Mach number,
and writes files that can be loaded back into flow5.

Usage (Windows, in a Command Prompt / PowerShell):
    py flow5_compressibility.py "C:\path\to\exports"    <- a whole folder
                                                        (sub-folders too)
    py flow5_compressibility.py polar1.txt polar2.txt   <- single files
    add --no-wave if the 3D analysis already used the *_for3D foil polars
    py flow5_compressibility.py                         <- or just double-click:
                                     every .txt/.csv in the script's folder
Output goes to a "corrected" folder next to each input file.
The airfoil thickness is taken from the name (SC(2)-0612 -> t/c = 0.12).

Easiest way to get the input files out of flow5:
  2D: Foil module > Polars menu > "Export all polars" (one sub-folder per foil)
  3D: Plane module, right-click the polar graph > All polars > Export

Only dependency: numpy  (py -m pip install numpy)

------------------------------------------------------------------------------
METHOD
------------------------------------------------------------------------------
Simple sweep theory: the sections see the normal Mach number
    M_n = M_inf * cos(Lambda_c/4)

Lift / moment (Karman-Tsien, default)
    Karman-Tsien corrects pressure coefficients:  Cp = Cp0 / (beta + c*Cp0),
    c = M^2 / (2(1+beta)).  A polar only holds integrated coefficients, so the
    load is split as in thin-airfoil theory: upper surface Cp0 = -Cl0/2 and
    lower surface Cp0 = +Cl0/2. Correcting each surface and adding them gives
        F(Cl0) = beta / (beta^2 - c^2 (Cl0/2)^2),   Cl = F * Cl0
    For small Cl this is exactly Prandtl-Glauert (1/beta) and it grows with Cl
    as Karman-Tsien should. Suction peaks are stronger than this average
    pressure, so treat this as a lower bound on the Karman-Tsien effect.
    'pg' and 'laitone' can be selected instead (METHOD below).

    2D polars: linear part = 1/beta_n
    3D polars: linear part = CLa(M)/CLa(0) from the DATCOM / Roskam lift-curve
               slope, which includes finite span and sweep. The nonlinear
               Karman-Tsien term above is multiplied on top.

Wave drag (Korn equation extended with simple sweep theory, Mason):
    M_dd   = kA/cos L - (t/c)/cos^2 L - |Cl|/(10 cos^3 L)
    M_crit = M_dd - (0.1/80)^(1/3)
    CD_w   = 20 (M - M_crit)^4        for M > M_crit   (Lock)

Induced drag (3D): CDi = CL^2/(pi A e)   (or CDi_flow5 * F^2, see below)

------------------------------------------------------------------------------
HOW flow5 USES THE FOIL POLARS (this matters!)
------------------------------------------------------------------------------
flow5's 3D panel/VLM solvers are incompressible. In a viscous analysis
(From_CL = true) each strip computes its own incompressible Cl and then reads
the profile drag at that Cl from the foil polar. flow5 picks foil polars by
Reynolds number only and ignores their Mach number.

So there are two 2D output files:
  *_for3D.txt : Cl, Cm and alpha stay incompressible. Cd and Cdp include the
                wave drag at the compressible strip Cl (Cl * wing factor).
                Import THIS one before running the 3D wing analysis, and
                delete the original M=0 polar of the same Re, otherwise flow5
                may use either one. Then correct the exported 3D polar with
                WAVE_DRAG_3D = False / --no-wave (the wave drag is already
                in CD_viscous).
  *_full.txt  : the fully corrected section polar (Cl, Cm, Cd, Cpmin), for
                plots/reporting. Do NOT use it for the 3D analysis: flow5
                would read it at the incompressible Cl. Both files get the
                same polar name in flow5 (T1_Re.._M0.77_N..), so importing one
                replaces the other.

Alternative route: run the 3D analysis with the original polars and correct
the exported 3D polar with WAVE_DRAG_3D = True (the default).

------------------------------------------------------------------------------
IMPORTING INTO flow5
------------------------------------------------------------------------------
2D: Foil analysis module > Polars menu > "Import XFoil polar(s)" >
    pick *_for3D.txt.
    The foil named in the file must exist in the project.
3D: 1. Export the polar results as .txt (All polars > Export, or
       right-click > Active polar > Export data > to file). The .xml
       "analysis" files only hold the settings, not the results.
    2. Run this script on that .txt.
    3. Plane module: Active plane (or Polars) menu > "Import external
       polar". In the dialog, tick ALL variables on the right (flow5
       skips hidden columns when pasting),
       use "Resize data" to create at least one row, click the first cell
       (Ctrl column, row 1), open *_paste.txt in Notepad, copy everything,
       press Ctrl+V in the table and choose the "WhiteSpace" separator.
       Use the _paste file, not the other one: flow5's paste also splits
       on '+', which breaks numbers like 3.47e+05.
"""

import csv
import math
import re
import sys
from pathlib import Path

import numpy as np

# =============================================================================
# CONFIGURATION
# =============================================================================
MACH = 0.77                      # cruise Mach number [-]
GAMMA = 1.4

# Wing (ADSEE / Roskam sizing)
SPAN = 27.82                     # b      [m]
AREA = 70.35                     # S      [m^2]
OSWALD_E = 0.95                  # e      [-]
SWEEP_C4_DEG = 25.9125            # quarter-chord sweep [deg] (was 24.0225)
TAPER = 0.3161457369885578       # lambda [-]
ROOT_CHORD = 3.842669119947949   # [m]
TIP_CHORD = 1.214843460929117    # [m]
MAC = 2.756320980384732          # [m]
MAC_Y_FRAC = 0.4134019073277612  # spanwise MAC position [-]
XLEMAC = 5.7504205309291585      # [m]
DIHEDRAL_DEG = 2.597752317632196 # [deg]

# Airfoil: NACA SC(2)-0610
THICKNESS_RATIO = 0.10           # default t/c (streamwise) if not found below
# t/c is read from the airfoil / plane name: "SC(2)-0612" -> 0.12.
# Names with an extra suffix (e.g. "SC(2)-0614-10") or non-standard names
# should be listed here explicitly (any part of the name, case-insensitive):
THICKNESS_OVERRIDES = {
    "SC(2)-0614-10": 0.10,       # SC(2)-0614 scaled to 10 % thickness
    "SC(2)-0514-10": 0.10,       # SC(2)-0514 scaled to 10 % thickness
}
KORN_KAPPA = 0.935               # technology factor: 0.935 (ADSEE/Torenbeek
                                 # supercritical), 0.95 (Mason supercritical),
                                 # 0.87 (NACA 6-series)
KORN_SWEEP = "half"              # sweep line used in Korn: "half" or "quarter"
AIRFOIL_EFFICIENCY = 0.95        # eta = cl_alpha / 2pi, for DATCOM slope

METHOD = "kt"                    # "kt" (Karman-Tsien), "pg", "laitone"

# 2D foil polar output
FOIL_NAME = "NACA SC(2)-0610"    # only used for 2D files WITHOUT a header
                                 # (graph "export data" layout). Files from
                                 # Polars > "Export all polars" carry the name.
DEFAULT_NCRIT = 9.0              # used if not found in file name/header
XTR_TOP = 1.0                    # forced transition used in the analysis
XTR_BOT = 1.0
INPUT_MACH_2D = 0.0              # Mach of the flow5 2D export (not in file)

# 3D plane polar correction
WAVE_DRAG_3D = True              # True : the 3D analysis used the original
                                 #        (M=0) foil polars -> add wave drag
                                 # False: the *_for3D foil polars were used,
                                 #        wave drag is already in CD_viscous
                                 # (command line: --wave / --no-wave)
INDUCED_DRAG = "oswald"          # "oswald": CDi = CL^2/(pi A e)
                                 # "scale" : CDi = CDi_flow5 * F^2

OUT_DIR_NAME = "corrected"

# =============================================================================
# DERIVED GEOMETRY
# =============================================================================
ASPECT = SPAN ** 2 / AREA
SWEEP_C4 = math.radians(SWEEP_C4_DEG)


def sweep_at(x_c):
    """Sweep of the x/c chord line from the quarter-chord sweep."""
    return math.atan(math.tan(SWEEP_C4)
                     - 4.0 / ASPECT * (x_c - 0.25) * (1 - TAPER) / (1 + TAPER))


SWEEP_C2 = sweep_at(0.5)
SWEEP_KORN = SWEEP_C2 if KORN_SWEEP == "half" else SWEEP_C4
MACH_N = MACH * math.cos(SWEEP_C4)
BETA_N = math.sqrt(1 - MACH_N ** 2)


# =============================================================================
# AERODYNAMICS
# =============================================================================
def cp_coeff(M, method):
    """c in Cp = Cp0 / (beta + c*Cp0)."""
    b = math.sqrt(1 - M * M)
    if method == "kt":
        return M * M / (2 * (1 + b))
    if method == "laitone":
        return M * M * (1 + 0.5 * (GAMMA - 1) * M * M) / (2 * b)
    if method == "pg":
        return 0.0
    raise ValueError(f"unknown METHOD '{method}'")


def nonlinear_factor(cl0, M, method):
    """F(Cl0) for the upper/lower surface split (see docstring)."""
    b = math.sqrt(1 - M * M)
    c = cp_coeff(M, method)
    q = 0.5 * np.abs(cl0)
    den = b * b - (c * q) ** 2
    den = np.where(den > 0.05 * b * b, den, 0.05 * b * b)   # guard
    return b / den


def cla_datcom(M):
    """DATCOM / Roskam wing lift-curve slope [1/rad]."""
    b2 = 1 - M * M
    t2 = math.tan(SWEEP_C2) ** 2
    return 2 * math.pi * ASPECT / (
        2 + math.sqrt(4 + (ASPECT ** 2 * b2 / AIRFOIL_EFFICIENCY ** 2)
                      * (1 + t2 / b2)))


def factor_2d(cl0):
    return nonlinear_factor(cl0, MACH_N, METHOD)


DATCOM_RATIO = cla_datcom(MACH) / cla_datcom(0.0)


def factor_3d(cl0):
    # DATCOM linear part x nonlinear (KT/PG) part normalised to 1 at Cl=0
    return DATCOM_RATIO * nonlinear_factor(cl0, MACH_N, METHOD) * BETA_N


def korn(cl, tc):
    """Returns (M_dd, M_crit, CD_wave) for lift coefficient(s) cl."""
    c = math.cos(SWEEP_KORN)
    mdd = (KORN_KAPPA / c - tc / c ** 2
           - np.abs(cl) / (10 * c ** 3))
    mcr = mdd - (0.1 / 80) ** (1 / 3)
    cdw = np.where(MACH > mcr, 20 * (MACH - mcr) ** 4, 0.0)
    return mdd, mcr, cdw


def cl_at_mdd(tc):
    ck = math.cos(SWEEP_KORN)
    return 10 * ck ** 3 * (KORN_KAPPA / ck - tc / ck ** 2 - MACH)


def thickness_for(name):
    """t/c from THICKNESS_OVERRIDES or the 4-digit SC(2) designation."""
    low = (name or "").lower()
    for key, tc in THICKNESS_OVERRIDES.items():
        if key.lower() in low:
            return tc, f"override '{key}'"
    m = re.search(r"sc\(2\)[-_ ]?(\d{2})(\d{2})(\S*)", low)
    if m:
        note = f"from name '{name.strip()}'"
        if m.group(3):
            note += (f"  !! suffix '{m.group(3)}' ignored - add the name to "
                     "THICKNESS_OVERRIDES if the thickness differs")
        return int(m.group(2)) / 100, note
    return THICKNESS_RATIO, f"default (no SC(2) designation in '{name}')"


def cp_crit(M):
    return 2 / (GAMMA * M * M) * (
        ((2 + (GAMMA - 1) * M * M) / (GAMMA + 1)) ** (GAMMA / (GAMMA - 1)) - 1)


def kt_cp(cp0, M):
    b = math.sqrt(1 - M * M)
    den = b + M * M / (1 + b) * cp0 / 2
    cp_vac = -2 / (GAMMA * M * M)
    with np.errstate(divide="ignore", invalid="ignore"):
        cp = np.where(den > 0.02, cp0 / den, cp_vac)
    return np.maximum(cp, cp_vac)


# =============================================================================
# FILE PARSING
# =============================================================================
def read_lines(path):
    return Path(path).read_text(encoding="utf-8", errors="replace").splitlines()


def split_nums(line):
    parts = [p for p in re.split(r"[\s,;]+", line.strip()) if p]
    try:
        return [float(p) for p in parts]
    except ValueError:
        return None


def detect(lines):
    text = "\n".join(lines[:15])
    if "<xflPlanePolar" in text or "<?xml" in text:
        return "xml"
    if "CD_induced" in text:
        return "3d"
    if "Calculated polar for" in text:
        return "2d_xfoil"
    for ln in lines[:5]:
        low = ln.lower()
        if "alpha" in low and "cdp" in low:
            return "2d_flow5"
    return None


def parse_2d_flow5(lines, path):
    hdr_i = next(i for i, l in enumerate(lines)
                 if "alpha" in l.lower() and "cdp" in l.lower())
    names = [n.strip() for n in re.split(r"[\s,;]+", lines[hdr_i].strip()) if n]
    rows = [r for r in (split_nums(l) for l in lines[hdr_i + 1:])
            if r and len(r) == len(names)]
    data = np.array(rows)
    col = {n.lower(): data[:, i] for i, n in enumerate(names)}
    n = len(data)
    get = lambda k, d=0.0: col.get(k, np.full(n, d))

    stem = Path(path).stem
    m = re.search(r"Re(\d+(?:\.\d+)?)", stem)
    re_file = float(m.group(1)) * 1e6 if m else None
    m = re.search(r"N(\d+(?:\.\d+)?)", stem)
    ncrit = float(m.group(1)) if m else DEFAULT_NCRIT
    reynolds = float(np.median(col["re"])) if "re" in col else re_file

    return dict(foil=FOIL_NAME, mach=INPUT_MACH_2D, re=reynolds, ncrit=ncrit,
                xtr_top=XTR_TOP, xtr_bot=XTR_BOT,
                alpha=col["alpha"], cl=col["cl"], cd=col["cd"],
                cdp=col["cdp"], cm=col["cm"],
                xtrtop=get("xtrtop", 1.0), xtrbot=get("xtrbot", 1.0),
                cpmin=get("cpmn"), hmom=get("hmom"), xcp=get("xcp"))


def parse_2d_xfoil(lines, path):
    foil = FOIL_NAME
    mach, reynolds, ncrit = 0.0, None, DEFAULT_NCRIT
    xt, xb = XTR_TOP, XTR_BOT
    for l in lines:
        if "Calculated polar for" in l:
            foil = l.split(":", 1)[1].strip()
        if "Mach" in l and "Re" in l and "=" in l:
            m = re.search(r"Mach\s*=\s*([-\d.]+)", l)
            mach = float(m.group(1))
            m = re.search(r"Re\s*=\s*([\d.]+)\s*e\s*(\d+)", l)
            reynolds = float(m.group(1)) * 10 ** int(m.group(2))
            m = re.search(r"Ncrit\s*=\s*([\d.]+)", l)
            if m:
                ncrit = float(m.group(1))
        if l.strip().startswith("xtrf"):
            v = re.findall(r"[\d.]+", l)
            xt, xb = float(v[0]), float(v[1])
    dash = next(i for i, l in enumerate(lines) if l.strip().startswith("---"))
    rows = [r for r in (split_nums(l) for l in lines[dash + 1:]) if r and len(r) >= 5]
    w = max(len(r) for r in rows)
    data = np.array([r + [0.0] * (w - len(r)) for r in rows])
    c = lambda i, d=0.0: data[:, i] if w > i else np.full(len(data), d)
    return dict(foil=foil, mach=mach, re=reynolds, ncrit=ncrit,
                xtr_top=xt, xtr_bot=xb,
                alpha=c(0), cl=c(1), cd=c(2), cdp=c(3), cm=c(4),
                xtrtop=c(5, 1.0), xtrbot=c(6, 1.0),
                cpmin=c(7), hmom=c(8), xcp=c(9))


# flow5 PlanePolar variable order (planepolar.cpp, 57 variables)
V = dict(ctrl=0, alpha=1, beta=2, phi=3, CL=4, CD=5, CDv=6, CDi=7, CY=8,
         Cm=9, Cmv=10, Cmp=11, Cl=12, Cn=13, Cnv=14, Cnp=15, CLCD=16,
         CL32CD=17, isqrtCL=18, Lift=19, Drag=20, FxFF=21, FyFF=22, FzFF=23,
         FxSum=24, FySum=25, FzSum=26, Extra=27, Fuse=28, CfFuse=29,
         Vx=30, Vz=31, V=32, Gamma=33, L=34, M=35, N=36, CPx=37, CPy=38,
         CPz=39, BM=40, mgVz=41, DragV=42, Eff=43, XCpCl=44, XNP=45,
         Mass=54, CoGx=55, CoGz=56)
N_VARS_3D = 57


def parse_3d(lines):
    hdr_i = next(i for i, l in enumerate(lines) if "CD_induced" in l)
    rows = [r for r in (split_nums(l) for l in lines[hdr_i + 1:])
            if r and len(r) == N_VARS_3D]
    if not rows:
        raise ValueError("no 57-column data rows found")
    return lines[:hdr_i + 1], np.array(rows)


# =============================================================================
# CORRECTIONS
# =============================================================================
def correct_2d(p):
    if p["mach"] > 0.01:
        print(f"   ! input polar already has Mach = {p['mach']:.3f}; this script "
              "expects incompressible (M=0) polars. Skipping.")
        return None
    cl0 = p["cl"]
    F = factor_2d(cl0)
    cl = F * cl0
    mdd, mcr, cdw = korn(cl, p["tc"])
    cpmin = kt_cp(p["cpmin"], MACH_N)
    supercrit = cpmin < cp_crit(MACH_N)
    return dict(F=F, cl=cl, cm=F * p["cm"], hmom=F * p["hmom"],
                cdw=cdw, mdd=mdd, mcr=mcr, cpmin=cpmin,
                supercrit=supercrit, past_mdd=MACH > mdd)


def write_xfoil_polar(path, p, alpha, cl, cd, cdp, cm, cpmin, hmom):
    """flow5's own XFoil-format writer (Polar::exportToString), which its
    'Import XFoil polar' reader parses by fixed character positions."""
    out = ["flow5 compressibility-corrected polar", "",
           f" Calculated polar for: {p['foil']}", "",
           " 1 1 Reynolds number fixed          Mach number fixed         ", "",
           f" xtrf =   {p['xtr_top']:.3f} (top)        {p['xtr_bot']:.3f} (bottom)",
           f" Mach = {MACH:7.3f}     Re = {p['re'] / 1e6:9.3f} e 6     Ncrit = {p['ncrit']:7.3f}",
           "",
           "  alpha     CL        CD       CDp       Cm    Top Xtr Bot Xtr   Cpmin    Chinge    XCp    ",
           " ------- -------- --------- --------- -------- ------- ------- -------- --------- ---------"]
    for j in range(len(alpha)):
        out.append(f" {alpha[j]:7.3f}  {cl[j]:7.4f}  {cd[j]:8.5f}  {cdp[j]:8.5f}  {cm[j]:7.4f}"
                   f"  {p['xtrtop'][j]:6.4f}  {p['xtrbot'][j]:6.4f}"
                   f"  {cpmin[j]:7.4f}  {hmom[j]:7.4f}  {p['xcp'][j]:7.4f}")
    Path(path).write_text("\n".join(out) + "\n\n", encoding="utf-8")


def process_2d(path, p, outdir):
    p["tc"], note = thickness_for(p["foil"])
    print(f"   t/c = {p['tc']:.3f} ({note})")
    c = correct_2d(p)
    if c is None:
        return
    base = Path(path).stem
    if re.search(r"[_-]M\d+(?:\.\d+)?", base):          # T1_Re10.00_M0.00_N9.0
        base = re.sub(r"([_-])M\d+(?:\.\d+)?", rf"\g<1>M{MACH:.2f}", base, count=1)
    elif "Re" in base:                                     # T1-Re10.000-N9.0
        base = re.sub(r"(Re[\d.]+)", rf"\1-M{MACH:.2f}", base, count=1)
    else:
        base = f"{base}-M{MACH:.2f}"
    safe_foil = re.sub(r'[\\/:*?"<>|]', "_", p["foil"]).strip()
    if safe_foil and safe_foil.lower() not in base.lower():
        base = f"{safe_foil}_{base}"

    # a) for the 3D analysis: incompressible Cl axis + wave drag. The strip's
    #    compressible Cl follows the wing's factor (DATCOM), not the 2D one.
    _, _, cdw3 = korn(factor_3d(p["cl"]) * p["cl"], p["tc"])
    write_xfoil_polar(outdir / f"{base}_for3D.txt", p, p["alpha"], p["cl"],
                      p["cd"] + cdw3, p["cdp"] + cdw3, p["cm"],
                      p["cpmin"], p["hmom"])
    # b) fully corrected section polar
    write_xfoil_polar(outdir / f"{base}_full.txt", p, p["alpha"], c["cl"],
                      p["cd"] + c["cdw"], p["cdp"] + c["cdw"], c["cm"],
                      c["cpmin"], c["hmom"])
    # c) details
    with open(outdir / f"{base}_details.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["alpha", "Cl_inc", "F", "Cl_comp", "Cd_inc", "Cd_wave",
                    "Cd_comp", "Cdp_comp", "Cm_inc", "Cm_comp", "M_dd", "M_crit",
                    "Cpmin_inc", "Cpmin_comp", "local_supersonic", "M_above_Mdd"])
        for j in range(len(p["alpha"])):
            w.writerow([f"{p['alpha'][j]:.3f}", f"{p['cl'][j]:.5f}", f"{c['F'][j]:.5f}",
                        f"{c['cl'][j]:.5f}", f"{p['cd'][j]:.6f}", f"{c['cdw'][j]:.6f}",
                        f"{p['cd'][j] + c['cdw'][j]:.6f}", f"{p['cdp'][j] + c['cdw'][j]:.6f}",
                        f"{p['cm'][j]:.5f}", f"{c['cm'][j]:.5f}", f"{c['mdd'][j]:.4f}",
                        f"{c['mcr'][j]:.4f}", f"{p['cpmin'][j]:.4f}", f"{c['cpmin'][j]:.4f}",
                        int(c["supercrit"][j]), int(c["past_mdd"][j])])

    print(f"   foil '{p['foil']}', Re = {p['re']:.3g}, Ncrit = {p['ncrit']}, "
          f"{len(p['alpha'])} points")
    print(f"   {'alpha':>6} {'Cl_inc':>7} {'Cl_M':>7} {'Cd_inc':>8} {'Cd_wave':>8} "
          f"{'Cd_M':>8} {'M_crit':>7}")
    for a in (-2, 0, 1, 2, 3, 4):
        j = int(np.argmin(np.abs(p["alpha"] - a)))
        print(f"   {p['alpha'][j]:6.2f} {p['cl'][j]:7.4f} {c['cl'][j]:7.4f} "
              f"{p['cd'][j]:8.5f} {c['cdw'][j]:8.5f} {p['cd'][j] + c['cdw'][j]:8.5f} "
              f"{c['mcr'][j]:7.4f}")
    npast = int(c["past_mdd"].sum())
    print(f"   Korn: M_dd = M at |Cl| = {cl_at_mdd(p['tc']):.3f}; {npast} of "
          f"{len(p['alpha'])} points lie beyond that (wave drag extrapolated)")
    print(f"   -> {base}_for3D.txt, {base}_full.txt, {base}_details.csv")


def fmt_paste(v):
    """Positional notation only: flow5's paste splitter treats '+' as a
    separator, so '1.2e+05' would break the columns."""
    if not np.isfinite(v) or abs(v) < 1e-12:     # round-off noise -> 0
        v = 0.0
    return np.format_float_positional(v, precision=8, unique=False,
                                      fractional=False, trim="-")


def process_3d(path, lines, outdir):
    header, d = parse_3d(lines)
    plane = next((l for l in header if l.strip()), "")
    tc, note = thickness_for(plane)
    print(f"   plane '{plane.strip()}', t/c = {tc:.3f} ({note})")
    o = d.copy()
    CL0, CDi0 = d[:, V["CL"]], d[:, V["CDi"]]
    F = factor_3d(CL0)
    CL = F * CL0

    if INDUCED_DRAG == "oswald":
        CDi = CL ** 2 / (math.pi * ASPECT * OSWALD_E)
    else:
        CDi = CDi0 * F ** 2
    mdd, mcr, cdw = korn(CL, tc)
    if not WAVE_DRAG_3D:
        cdw = np.zeros_like(cdw)
    CDv = d[:, V["CDv"]] + cdw
    CD = CDi + CDv

    # q*S, q*S*c, q*S*b from the flow5 columns themselves
    def ratio(num, den):
        m = np.abs(den) > 1e-6 * max(np.abs(den).max(), 1e-30)
        return float(np.median(num[m] / den[m])) if m.any() else 0.0
    qS = ratio(d[:, V["Lift"]], CL0)
    with np.errstate(divide="ignore", invalid="ignore"):
        ri = np.where(np.abs(CDi0) > 1e-12, CDi / CDi0, F ** 2)

    o[:, V["CL"]] = CL
    o[:, V["CD"]] = CD
    o[:, V["CDv"]] = CDv
    o[:, V["CDi"]] = CDi
    for k in ("CY", "Cl", "Cmp", "Cnp", "Lift", "FyFF", "FzFF",
              "FySum", "FzSum", "L", "BM", "XCpCl"):
        o[:, V[k]] = d[:, V[k]] * F
    o[:, V["Cm"]] = o[:, V["Cmv"]] + o[:, V["Cmp"]]
    o[:, V["Cn"]] = o[:, V["Cnv"]] + o[:, V["Cnp"]]
    o[:, V["M"]] = d[:, V["M"]] + (F - 1) * d[:, V["Cmp"]] * ratio(d[:, V["M"]], d[:, V["Cm"]])
    o[:, V["N"]] = d[:, V["N"]] + (F - 1) * d[:, V["Cnp"]] * ratio(d[:, V["N"]], d[:, V["Cn"]])
    o[:, V["FxFF"]] = CDi * qS
    o[:, V["FxSum"]] = d[:, V["FxSum"]] * ri
    o[:, V["Drag"]] = CD * qS
    o[:, V["DragV"]] = CD * qS * d[:, V["V"]]
    with np.errstate(divide="ignore", invalid="ignore"):
        o[:, V["CLCD"]] = np.where(np.abs(CD) > 1e-9, CL / CD, 0)
        o[:, V["CL32CD"]] = np.where(np.abs(CD) > 1e-9,
                                     np.sign(CL) * np.abs(CL) ** 1.5 / CD, 0)
        o[:, V["isqrtCL"]] = np.where(CL > 1e-9, 1 / np.sqrt(np.abs(CL)), 0)
        o[:, V["Gamma"]] = np.where(np.abs(CL) > 1e-9, np.degrees(np.arctan(CD / CL)), 0)
        o[:, V["Eff"]] = np.where(np.abs(CDi) > 1e-12,
                                  d[:, V["Eff"]] * ri ** -1 * F ** 2, 0)
        gam_old = np.arctan(d[:, V["CD"]] / CL0)
        gam_new = np.arctan(CD / CL)
        o[:, V["Vx"]] = np.where(np.abs(np.cos(gam_old)) > 0,
                                 d[:, V["Vx"]] * np.cos(gam_new) / np.cos(gam_old),
                                 d[:, V["Vx"]])
        # non-glide polars: Vz = sqrt(2mg/(rho S)) / (CL^1.5/CD)
        vz_ratio = np.where(np.abs(o[:, V["CL32CD"]]) > 1e-9,
                            d[:, V["CL32CD"]] / o[:, V["CL32CD"]], 1.0)
        o[:, V["Vz"]] = d[:, V["Vz"]] * vz_ratio
        o[:, V["mgVz"]] = d[:, V["mgVz"]] * vz_ratio
    o = np.nan_to_num(o)

    stem = Path(path).stem
    base = f"{stem}_M{MACH:.2f}"
    # a) flow5 export layout
    sep = ", " if Path(path).suffix.lower() == ".csv" else "  "
    body = [sep.join(f"{v:11.5g}" for v in row) for row in o]
    header = list(header)
    header[1] = header[1] + f"  [compressibility corrected, M = {MACH}]"
    (outdir / f"{base}.txt").write_text("\n".join(header + body) + "\n",
                                        encoding="utf-8")
    # b) paste-ready block for 'Import external polar'
    (outdir / f"{base}_paste.txt").write_text(
        "\n".join(" ".join(fmt_paste(v) for v in row) for row in o) + "\n",
        encoding="utf-8")
    # c) details
    with open(outdir / f"{base}_details.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["alpha", "CL_inc", "F", "CL_comp", "CDi_inc", "CDi_comp",
                    "CDv_inc", "CD_wave", "CD_inc", "CD_comp", "Cm_inc", "Cm_comp",
                    "M_dd", "M_crit", "L/D_inc", "L/D_comp"])
        for j in range(len(d)):
            w.writerow([f"{d[j, V['alpha']]:.3f}", f"{CL0[j]:.5f}", f"{F[j]:.5f}",
                        f"{CL[j]:.5f}", f"{CDi0[j]:.6f}", f"{CDi[j]:.6f}",
                        f"{d[j, V['CDv']]:.6f}", f"{cdw[j]:.6f}",
                        f"{d[j, V['CD']]:.6f}", f"{CD[j]:.6f}",
                        f"{d[j, V['Cm']]:.5f}", f"{o[j, V['Cm']]:.5f}",
                        f"{mdd[j]:.4f}", f"{mcr[j]:.4f}",
                        f"{d[j, V['CLCD']]:.3f}", f"{o[j, V['CLCD']]:.3f}"])

    print(f"   {len(d)} points, DATCOM CLa ratio = {DATCOM_RATIO:.4f}, "
          f"wave drag {'ADDED' if WAVE_DRAG_3D else 'NOT added (assumed in CDv)'}, "
          f"CDi = {INDUCED_DRAG}")
    print(f"   {'alpha':>6} {'CL_inc':>7} {'CL_M':>7} {'CDi_M':>8} {'CDw':>8} "
          f"{'CD_M':>8} {'L/D_M':>6}")
    shown = sorted({int(np.argmin(np.abs(d[:, V["alpha"]] - a))) for a in range(-2, 7)})
    for j in shown:
        print(f"   {d[j, V['alpha']]:6.2f} {CL0[j]:7.4f} {CL[j]:7.4f} {CDi[j]:8.5f} "
              f"{cdw[j]:8.5f} {CD[j]:8.5f} {o[j, V['CLCD']]:6.2f}")
    print(f"   -> {base}.txt, {base}_paste.txt, {base}_details.csv")


# =============================================================================
# MAIN
# =============================================================================
def main(args):
    global WAVE_DRAG_3D
    if "--wave" in args:
        WAVE_DRAG_3D = True
    if "--no-wave" in args:
        WAVE_DRAG_3D = False
    args = [a for a in args if not a.startswith("--")]
    def collect(folder):
        return [f for f in sorted(folder.rglob("*"))
                if f.suffix.lower() in (".txt", ".csv")
                and OUT_DIR_NAME not in f.parts[len(folder.parts):]]

    targets = [Path(a) for a in args] or [Path(__file__).resolve().parent]
    files = []
    for t in targets:
        files += collect(t) if t.is_dir() else [t]

    print(f"M = {MACH}, Lambda_c/4 = {SWEEP_C4_DEG:.3f} deg, "
          f"Lambda_c/2 = {math.degrees(SWEEP_C2):.3f} deg, A = {ASPECT:.3f}")
    print(f"M_n = {MACH_N:.4f}, beta_n = {BETA_N:.4f}, 1/beta_n = {1 / BETA_N:.4f}, "
          f"method = {METHOD}")
    print(f"Korn: kappa = {KORN_KAPPA}, "
          f"sweep = {math.degrees(SWEEP_KORN):.3f} deg ({KORN_SWEEP} chord)\n")

    for f in files:
        if not f.is_file():
            print(f"{f}: not found")
            continue
        lines = read_lines(f)
        kind = detect(lines)
        print(f"{f.name}: {kind or 'unrecognised'}")
        outdir = f.parent / OUT_DIR_NAME
        try:
            if kind == "2d_flow5":
                outdir.mkdir(exist_ok=True)
                process_2d(f, parse_2d_flow5(lines, f), outdir)
            elif kind == "2d_xfoil":
                outdir.mkdir(exist_ok=True)
                process_2d(f, parse_2d_xfoil(lines, f), outdir)
            elif kind == "3d":
                outdir.mkdir(exist_ok=True)
                process_3d(f, lines, outdir)
            elif kind == "xml":
                print("   this is an analysis definition (settings only, no "
                      "results). Export the polar data instead: right-click > "
                      "Active polar > Export data > to file.")
        except Exception as exc:  # keep going with the other files
            print(f"   ERROR: {exc}")
        print()


if __name__ == "__main__":
    main(sys.argv[1:])
    if len(sys.argv) == 1 and sys.platform.startswith("win"):
        input("Press Enter to close...")
