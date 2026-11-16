"""
WP4.1 - Importing the Flow5 operating-point exports into Python  (reader Appendix B.3)

Flow5's export differs from the XFLR5 file described in the reader:
  - the spanwise table header starts with  y(m)  instead of  y-span
  - the columns are:  y(m) Re Ai Cd_i Cd_v Cl CP.x(%) Trans.top Trans.bot
                      Cm_i Cm_v Bending.mom Vd.x Vd.y Vd.z F.x F.y F.z gamma
  - there is NO chord column -> the chord is computed from the planform, c(y)
  - inviscid run -> use Cd_i (induced drag) and Cm_i (inviscid pitching moment)

What this file does:
  1. Reads ONE exported file (alpha = 0 deg or alpha = 10 deg).
  2. Takes the spanwise table under "Main wing" and keeps the positive-y half.
  3. Computes the wing CL by integrating the local Cl over the span, using
     S = 61.20 m^2, so CL0/CL10 use the same reference area as CL_d = nW/(qS).
  4. Makes cubic interpolants Cl(y), Cd(y), Cm(y) (reader B.3).
  5. Plots them so you can check.

Learning example: understand every line and adapt it yourselves. The reader
makes you responsible for verifying any generated code.
"""

import numpy as np
import scipy as sp
from scipy import interpolate, integrate
import matplotlib.pyplot as plt

# ---- planform (project data sheet, WP3 final) --------------------------------
HALF_SPAN = 12.74   # m
C_ROOT = 3.652      # m
C_TIP = 1.154       # m
S_REF = 61.20       # m^2


def chord(y):
    """Linear taper: c(y) = c_r - (c_r - c_t) * y / (b/2)"""
    return C_ROOT - (C_ROOT - C_TIP) * y / HALF_SPAN


# -----------------------------------------------------------------------------
# 1. Read one exported Flow5 file
# -----------------------------------------------------------------------------
def read_flow5_file(path):
    """Returns a dictionary of numpy arrays: 'y', 'Cl', 'Cd', 'Cm', 'CPx'
    (positive-y half only)."""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    # --- (a) find the "Main wing" block, then the y(m) header under it -------
    header_index = None
    in_main_wing = False
    for i, line in enumerate(lines):
        text = line.strip()
        if text.lower().startswith("main wing"):
            in_main_wing = True
        if in_main_wing and text.startswith("y(m)"):
            header_index = i
            break
    if header_index is None:
        raise ValueError("Could not find the 'y(m)' header under 'Main wing'.")

    column_names = lines[header_index].split()

    # --- (b) count the numeric rows that follow ------------------------------
    n_rows = 0
    for line in lines[header_index + 1:]:
        parts = line.split()
        if len(parts) == 0:
            break
        try:
            float(parts[0])
        except ValueError:
            break  # next section reached
        n_rows += 1

    # --- (c) read exactly that block ------------------------------------------
    table = np.genfromtxt(path, skip_header=header_index + 1, max_rows=n_rows)
    if table.shape[1] != len(column_names):
        raise ValueError(f"Table has {table.shape[1]} columns but the header has "
                         f"{len(column_names)} names. Check the file.")

    # --- (d) pick the columns by name ----------------------------------------
    def column(name):
        if name not in column_names:
            raise ValueError(f"Column '{name}' not found. Columns are: {column_names}")
        return table[:, column_names.index(name)]

    data = {
        "y":   column("y(m)"),
        "Cl":  column("Cl"),
        "Cd":  column("Cd_i"),      # induced drag (inviscid run)
        "Cm":  column("Cm_i"),      # inviscid pitching moment - check its reference point!
        "CPx": column("CP.x(%)"),   # centre of pressure, used only as a check
    }

    # --- (e) keep the positive-y half, sorted root -> tip ---------------------
    keep = data["y"] > 0
    order = np.argsort(data["y"][keep])
    for key in data:
        data[key] = data[key][keep][order]

    return data


# -----------------------------------------------------------------------------
# 2. Interpolants and total CL
# -----------------------------------------------------------------------------
def make_functions(data):
    """Cubic interpolants of Cl, Cd, Cm as functions of y. fill_value='extrapolate'
    because the strips stop just short of the root and the tip (reader B.3)."""
    f = {}
    for key in ["Cl", "Cd", "Cm"]:
        f[key] = sp.interpolate.interp1d(data["y"], data[key], kind="cubic",
                                         fill_value="extrapolate")
    return f


def wing_CL(f):
    """CL = (2 / S) * integral_0^(b/2) Cl(y) c(y) dy   (both wing halves)."""
    integral, error = sp.integrate.quad(lambda y: f["Cl"](y) * chord(y),
                                        0, HALF_SPAN, limit=200)
    return 2 * integral / S_REF


# -----------------------------------------------------------------------------
# 3. Run: read both files, print CL, plot to check
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Change these to your file names / paths
    FILE_0 = "Planename_a=0.00_v=10.00ms.txt"
    FILE_10 = "Planename_a=10.00_v=10.00ms.txt"

    data0, data10 = read_flow5_file(FILE_0), read_flow5_file(FILE_10)
    f0, f10 = make_functions(data0), make_functions(data10)
    CL0, CL10 = wing_CL(f0), wing_CL(f10)

    print("Spanwise strips per half wing:", len(data0["y"]))
    print(f"CL at alpha = 0 deg : {CL0:.4f}   (compare with the CL in the file header)")
    print(f"CL at alpha = 10 deg: {CL10:.4f}")

    # Check of the Cm reference point (see notes in the chat):
    # a moment about the aerodynamic centre (about c/4) hardly changes with alpha.
    print("\nCm_i at a few stations (alpha 0 vs 10) - should be nearly equal if about c/4:")
    for yi in [1.0, 4.0, 8.0, 11.0]:
        print(f"  y = {yi:5.1f} m:  {float(f0['Cm'](yi)):+.4f}   {float(f10['Cm'](yi)):+.4f}")

    y_fine = np.linspace(0, HALF_SPAN, 300)
    fig, ax = plt.subplots(1, 3, figsize=(14, 4))
    for f, data, label in [(f0, data0, "alpha = 0"), (f10, data10, "alpha = 10")]:
        for a, key in zip(ax, ["Cl", "Cd", "Cm"]):
            a.plot(y_fine, f[key](y_fine), label=label)
            a.plot(data["y"], data[key], "k.", markersize=3)
    for a, name in zip(ax, ["Cl (local lift coeff.)", "Cd_i (induced drag coeff.)",
                            "Cm_i (pitching moment coeff.)"]):
        a.set_xlabel("y [m]")
        a.set_ylabel(name)
        a.grid(True)
        a.legend()
    plt.tight_layout()
    plt.show()
