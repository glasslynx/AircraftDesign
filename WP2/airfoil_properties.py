"""
Tools for estimating the critical Mach number of an airfoil, plus a
helper for design lift coefficient.

Equations implemented (numbering matches Anderson's Fundamentals of
Aerodynamics):
    (11.55) Laitone's rule:      Cp = f(Cp0, M_inf, gamma)
    (11.60) Critical Cp:         Cp_cr = f(M_cr, gamma)
    q_inf = 0.5 * rho_inf * V_inf^2   (dynamic pressure, confirmed correct)
    C_L,des = 1.1 * (1/q) * [ 0.5*(W/S)_start_cruise + (W/S)_end_cruise ]
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import brentq
from dataclasses import dataclass


def mach_dd(ka, t_c_streamwise, CL, sweep_deg):
    """
    Drag-divergence Mach number estimate (Mason's method).

    M_DD = ka/cos(sweep) - (t/c)_streamwise/cos^2(sweep)
           - CL/(10*cos^3(sweep))

    Parameters
    ----------
    ka : float
        Airfoil technology factor. Constant for a given airfoil family
        (differing only in thickness). ka = 0.87 for NACA 6-series
        airfoils, ka = 0.935 for supercritical airfoils.
    t_c_streamwise : float
        Streamwise thickness-to-chord ratio (t/c), as a fraction (e.g.
        0.12 for 12%)
    CL : float
        Design lift coefficient (e.g. from cl_design())
    sweep_deg : float
        Wing quarter-chord sweep angle [degrees]

    Returns
    -------
    M_DD : float
        Estimated drag-divergence Mach number
    """
    sweep_rad = np.radians(sweep_deg)
    cos_sweep = np.cos(sweep_rad)
    return ((ka / cos_sweep)
            - (t_c_streamwise / cos_sweep**2)
            - (CL / (10 * cos_sweep**3)))


def dynamic_pressure(rho_inf, V_inf):
    """
    Freestream dynamic pressure.

    q_inf = 0.5 * rho_inf * V_inf^2

    Parameters
    ----------
    rho_inf : float
        Freestream density [kg/m^3]
    V_inf : float
        Freestream velocity [m/s]

    Returns
    -------
    q_inf : float
        Dynamic pressure [Pa]
    """
    return 0.5 * rho_inf * V_inf**2


def cp_laitone(Cp0, M_inf, gamma=1.4):
    """
    Laitone's rule (Eq. 11.55) — compressibility-corrected pressure
    coefficient at freestream Mach number M_inf, given the
    incompressible pressure coefficient Cp0.

    Cp = Cp0 / ( sqrt(1 - M_inf^2)
                 + ( M_inf^2 * (1 + [(gamma-1)/2]*M_inf^2)
                     / (2*sqrt(1 - M_inf^2)) ) * Cp0 )

    Parameters
    ----------
    Cp0 : float
        Incompressible pressure coefficient (e.g. the min Cp on the airfoil)
    M_inf : float
        Freestream Mach number
    gamma : float, optional
        Ratio of specific heats (default 1.4 for air)

    Returns
    -------
    Cp : float
        Compressible pressure coefficient at M_inf
    """
    denom = (np.sqrt(1 - M_inf**2)
             + (M_inf**2 * (1 + (gamma - 1) / 2 * M_inf**2)
                / (2 * np.sqrt(1 - M_inf**2))) * Cp0)
    return Cp0 / denom


def cp_critical(M_cr, gamma=1.4):
    """
    Critical pressure coefficient (Eq. 11.60) — the Cp at which the
    local flow first reaches Mach 1, as a function of the freestream
    Mach number M_cr.

    Cp,cr = (2 / (gamma * M_cr^2)) *
            [ ( (1 + [(gamma-1)/2]*M_cr^2) / (1 + (gamma-1)/2) )^(gamma/(gamma-1)) - 1 ]

    Parameters
    ----------
    M_cr : float
        Freestream Mach number (the value being tested as M_critical)
    gamma : float, optional
        Ratio of specific heats (default 1.4 for air)

    Returns
    -------
    Cp_cr : float
        Critical pressure coefficient at M_cr
    """
    term = (1 + (gamma - 1) / 2 * M_cr**2) / (1 + (gamma - 1) / 2)
    return (2 / (gamma * M_cr**2)) * (term ** (gamma / (gamma - 1)) - 1)


def find_critical_mach(Cp0, gamma=1.4, M_bounds=(0.1, 0.8)):
    """
    Solve for the critical Mach number: the M_inf at which the
    Laitone-corrected Cp (Eq. 11.55) equals the critical Cp (Eq. 11.60).

    This finds the root of:  cp_laitone(Cp0, M) - cp_critical(M) = 0

    Parameters
    ----------
    Cp0 : float
        Incompressible pressure coefficient (minimum Cp on the airfoil)
    gamma : float, optional
        Ratio of specific heats (default 1.4)
    M_bounds : tuple, optional
        Search bracket for the Mach number root (default (0.3, 0.8)).
        Note: the residual (Cp_laitone - Cp_cr) is not monotonic and
        can turn positive again as M -> 1, so a bracket that's too
        wide (e.g. extending past ~0.85-0.9) can pick up a spurious
        sign flip. If brentq raises a sign-mismatch error for your
        Cp0, first scan the residual over M to locate the true
        bracket, then narrow M_bounds accordingly.

    Returns
    -------
    M_cr : float
        Critical Mach number
    """

    def residual(M):
        return cp_laitone(Cp0, M, gamma) - cp_critical(M, gamma)

    # Scan through Mach numbers to find where the residual changes sign
    M_values = np.linspace(0.1, 0.85, 1000)

    for M1, M2 in zip(M_values[:-1], M_values[1:]):
        if residual(M1) * residual(M2) < 0:
            return brentq(residual, M1, M2)

    raise ValueError("No critical Mach number found in the range 0.1–0.65")


def plot_critical_mach(Cp0, gamma=1.4, M_bounds=(0.1, 0.8),
                        M_range=(0.1, 0.8), ylim=None,
                        save_path=None, show=True):
    """
    Plot Cp (Laitone's rule, Eq. 11.55) and Cp,cr (Eq. 11.60) vs. M_inf
    on the same axes, mark their intersection, and return the critical
    Mach number found there.

    This reproduces the classic "Cp vs M_inf" chart: the Laitone curve
    is the actual (compressibility-corrected) pressure coefficient on
    the airfoil as M_inf increases, and the Cp,cr curve is the value
    Cp would need to reach for sonic flow to appear locally at that
    M_inf. Where the two curves cross is M_critical.

    Parameters
    ----------
    Cp0 : float
        Incompressible pressure coefficient (minimum Cp on the airfoil)
    gamma : float, optional
        Ratio of specific heats (default 1.4)
    M_bounds : tuple, optional
        Bracket passed to find_critical_mach() for the root search
        (default (0.3, 0.8) — see note in find_critical_mach)
    M_range : tuple, optional
        Mach number range to plot over (default (0.1, 0.9))
    ylim : tuple, optional
        Explicit (ymin, ymax) for the Cp axis. If None (default), the
        y-range is auto-scaled around the intersection point, since
        Laitone's rule has an asymptote (denominator -> 0) at some M
        below 1 that would otherwise dwarf the interesting region.
    save_path : str, optional
        If given, saves the figure to this path (e.g. "cp_plot.png")
    show : bool, optional
        If True (default), calls plt.show(). Set False when embedding
        in another script/notebook that handles display itself.

    Returns
    -------
    M_cr : float
        Critical Mach number (intersection point)
    Cp_at_cr : float
        Cp value at the intersection (equal for both curves)
    fig, ax : matplotlib Figure, Axes
        The plot objects, in case you want to customize further
    """
    M_cr = find_critical_mach(Cp0, gamma, M_bounds)
    Cp_at_cr = cp_laitone(Cp0, M_cr, gamma)

    # Plot only the range relevant to finding M_cr
    M_vals = np.linspace(M_range[0], M_range[1], 600)

    Cp_vals = cp_laitone(Cp0, M_vals, gamma)
    Cp_cr_vals = cp_critical(M_vals, gamma)

    # Hide values near the asymptote
    Cp_vals = np.where(
        np.isfinite(Cp_vals) & (np.abs(Cp_vals) < 50),
        Cp_vals,
        np.nan
    )

    fig, ax = plt.subplots(figsize=(8, 6))

    # Laitone's rule
    ax.plot(
        M_vals,
        Cp_vals,
        label=r"$C_p$ (Laitone's rule, Eq. 11.55)",
        color="tab:blue"
    )

    # Critical pressure coefficient
    ax.plot(
        M_vals,
        Cp_cr_vals,
        label=r"$C_{p,cr}=f(M_\infty)$ (Eq. 11.60)",
        color="tab:orange"
    )

    # Critical point
    ax.plot(
        M_cr,
        Cp_at_cr,
        "ko",
        zorder=5
    )

    # Annotation
    # Placed in axes-fraction coordinates (upper-right corner by
    # default) with a readable background box, rather than a fixed
    # pixel offset from the point — a fixed offset pushes the text
    # into the tick labels/plot edge whenever M_cr lands near the
    # right or bottom of the plot (exactly what was happening before,
    # since M_cr is usually in the right half of M_range and the
    # y-axis here is inverted). The arrow still points at the actual
    # intersection point, wherever it is.
    ax.annotate(
        f"$M_{{cr}}$ = {M_cr:.4f}\n$C_p$ = {Cp_at_cr:.4f}",
        xy=(M_cr, Cp_at_cr),
        xycoords="data",
        xytext=(0.05, 0.08),
        textcoords="axes fraction",
        ha="left",
        va="bottom",
        fontsize=10,
        arrowprops=dict(
            arrowstyle="->",
            color="black",
            shrinkA=0,
            shrinkB=5,
            connectionstyle="arc3,rad=0.15"
        ),
        bbox=dict(
            boxstyle="round,pad=0.35",
            fc="white",
            ec="gray",
            alpha=0.9
        ),
        zorder=6
    )

    # Vertical line showing M_cr
    ax.axvline(
        M_cr,
        color="gray",
        linestyle="--",
        linewidth=0.8
    )

    # Axis labels
    ax.set_xlabel(r"$M_\infty$")
    ax.set_ylabel(r"$C_p$")

    # Title
    ax.set_title(
        f"Critical Mach Number Determination ($C_{{p,0}}$ = {Cp0})"
    )

    # Grid and legend
    ax.grid(True, alpha=0.3)
    ax.legend()

    # Match the textbook convention:
    # Cp = 0 at the bottom
    # Cp = -10 at the top
    ax.set_ylim(-10, 0)
    ax.invert_yaxis()


    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()

    return M_cr, Cp_at_cr, fig, ax


def cl_design(q, f_cruise, M_TOM, S):
    """
    Design lift coefficient.

    C_L,des = 1.1 * (1/q) * [ 0.5*(W/S)_start_cruise + (W/S)_end_cruise ]

    Parameters
    ----------
    q : float
        Dynamic pressure [Pa] (e.g. from dynamic_pressure())
    W_S_start_cruise : float
        Wing loading at start of cruise [N/m^2 or matching units]
    W_S_end_cruise : float
        Wing loading at end of cruise [same units as above]

    Returns
    -------
    C_L_des : float
        Design lift coefficient
    """
    return 1.1 * 9.80665 * (1/S) * M_TOM * (1 / q) * ((f_cruise))


# ============================================================
# Sweep-angle design chart (Korn-equation form), from your notes
# ============================================================
#
# NOTE ON VERIFICATION: the two arccos-based formulas below were
# checked against the exact numeric outputs in your screenshots and
# match to 6+ decimal places. The Korn-equation branch (tc_from_korn
# / sweep_from_korn) is transcribed exactly as written in your notes,
# but your screenshots did not show a solved numeric x for f(x)=0, so
# I could not independently verify it the same way. When I scanned it
# for M=0.77, Cl=0.4536 the root came out around 67-68 deg, which is
# unrealistically high for a swept transport wing (compare to your
# other two curves, both ~24 deg at the same M) — please cross-check
# this against what your own Desmos/GeoGebra tool actually reports
# for f(x)=0 before trusting sweep_from_korn() for real design
# decisions. If your tool gives a different root, tell me the value
# and I'll help track down where the transcription or formula
# structure diverges.

def tc_from_korn(sweep_deg, M, Cl, kappa_A=0.935,
                 z_offset=0.04723, cl_coeff=0.115):
    """
    Korn-equation-based thickness-to-chord ratio.

    Calculates t/c directly as a function of sweep angle.
    """

    x = np.radians(sweep_deg)
    z = np.tan(x) - z_offset

    return (
        kappa_A / np.sqrt(1 + z**2)
        - (M + 0.03) / (1 + z**2)
        - cl_coeff * Cl**1.5 * (1 + z**2)
    )


def sweep_from_korn(M, Cl, kappa_A=0.935, z_offset=0.04723, cl_coeff=0.115,
                     scan_range=(0.0, 89.0), scan_points=900):
    """
    Solve the Korn-equation-style formula (tc_from_korn) for the
    sweep angle x where f(x) = 0, auto-detecting the bracket the same
    way find_critical_mach() does (so you don't need to hand-pick a
    search window).

    Parameters
    ----------
    M : float
        Freestream/design Mach number
    Cl : float
        Design lift coefficient
    kappa_A, z_offset, cl_coeff : float, optional
        Passed through to tc_from_korn()
    scan_range : tuple, optional
        Sweep angle range to scan for a sign change (default (0, 89) deg)
    scan_points : int, optional
        Number of scan points (default 900)

    Returns
    -------
    sweep_deg : float
        Sweep angle [degrees] where f(x) = 0

    Raises
    ------
    ValueError
        If no sign change is found in scan_range
    """
    def residual(s):
        return tc_from_korn(s, M, Cl, kappa_A, z_offset, cl_coeff)

    s_scan = np.linspace(scan_range[0], scan_range[1], scan_points)
    r_scan = np.array([residual(s) for s in s_scan])
    sign_changes = np.where(np.diff(np.sign(r_scan)) != 0)[0]

    if len(sign_changes) == 0:
        raise ValueError(
            f"No sweep solution found for M={M}, Cl={Cl} in "
            f"{scan_range} deg."
        )

    i = sign_changes[0]
    return brentq(residual, s_scan[i], s_scan[i + 1])



def tc_from_mach_dd(M_DD, ka, CL, sweep_deg):
    """
    Streamwise thickness-to-chord ratio required to achieve a
    target drag-divergence Mach number M_DD.
    """
    sweep_rad = np.radians(sweep_deg)
    cos_sweep = np.cos(sweep_rad)

    return cos_sweep**2 * (
        ka / cos_sweep
        - CL / (10 * cos_sweep**3)
        - M_DD
    )

def sweep_structural_deg(M, coeff=1.16, offset=0.5):
    # Wing planform
    c_r = 3.842669119947949
    c_t = 1.214843460929117
    span = 27.82

    # Taper ratio
    taper_ratio = c_t / c_r

    # arccos gives QUARTER-CHORD sweep
    sweep_quarter_rad = np.arccos(
        coeff / (M + offset)
    )

    # Convert QUARTER-CHORD sweep -> HALF-CHORD sweep
    sweep_half_rad = np.arctan(
        np.tan(sweep_quarter_rad)
        - c_r * (1 - taper_ratio) / (4 * span)
    )

    return np.degrees(sweep_half_rad)

def sweep_from_mcrest_deg(M, M_crest):
    """
    Calculate the HALF-CHORD sweep angle corresponding to
    a given crest Mach number.

    First, the quarter-chord sweep is calculated from:

        M_crest = M * cos(Lambda_c/4)

    Then the quarter-chord sweep is converted to
    half-chord sweep using the wing planform.

    Parameters
    ----------
    M : float
        Freestream/cruise Mach number.

    M_crest : float
        Target crest Mach number.

    Returns
    -------
    sweep_half_deg : float
        HALF-CHORD sweep angle [degrees]
    """

    # Wing planform
    c_r = 3.842669119947949
    c_t = 1.214843460929117
    span = 27.82

    # arccos gives QUARTER-CHORD sweep
    sweep_quarter_rad = np.arccos(
        M_crest / M
    )

    # Convert QUARTER-CHORD sweep -> HALF-CHORD sweep
    sweep_half_rad = np.arctan(
        np.tan(sweep_quarter_rad)
        - (c_r - c_t) / (4 * span)
    )

    return np.degrees(sweep_half_rad)

def plot_sweep_tc_chart(CL, M_DD, ka,
                        sweep_range_deg=(0, 45),
                        M_cruise=0.77,
                        M_crest=None,
                        structural_coeff=1.16,
                        structural_offset=0.5,
                        t_c_horizontal=None,
                        save_path=None,
                        show=True):

    fig, ax = plt.subplots(figsize=(9, 6.5))

    constraints = {
        "structural": None,
        "M_crest": None,
        "drag_divergence_intersection": None,
        "structural_tc_intersection": None,
        "M_crest_tc_intersection": None
    }

    # ==================================================
    # Drag-divergence constraint
    # ==================================================

    sweep_values = np.linspace(
        sweep_range_deg[0],
        sweep_range_deg[1],
        500
    )

    tc_drag_divergence = tc_from_mach_dd(
        M_DD,
        ka,
        CL,
        sweep_values
    )

    ax.plot(
        sweep_values,
        tc_drag_divergence,
        color="blue",
        linewidth=1.8,
        label=fr"Drag divergence ($M_{{DD}}={M_DD}$)"
    )

    # ==================================================
    # Structural Mach constraint
    # ==================================================

    if M_cruise is not None:

        if (structural_coeff / (M_cruise + structural_offset)) <= 1.0:

            sweep_struct = sweep_structural_deg(
                M_cruise,
                structural_coeff,
                structural_offset
            )

            constraints["structural"] = sweep_struct

            ax.axvline(
                sweep_struct,
                color="red",
                linestyle="-.",
                linewidth=1.3,
                label=fr"Structural constraint ($\Lambda={sweep_struct:.2f}^\circ$)"
            )

    # ==================================================
    # Mach crest constraint
    # ==================================================

    if M_crest is not None and M_cruise is not None:

        if M_cruise > M_crest:

            sweep_mcrest = sweep_from_mcrest_deg(
                M_cruise,
                M_crest
            )

            constraints["M_crest"] = sweep_mcrest

            ax.axvline(
                sweep_mcrest,
                color="green",
                linestyle=":",
                linewidth=1.5,
                label=fr"$M_{{crest}}$ constraint ($\Lambda={sweep_mcrest:.2f}^\circ$)"
            )

    # ==================================================
    # Actual t/c
    # ==================================================

    if t_c_horizontal is not None:

        ax.axhline(
            t_c_horizontal,
            color="black",
            linestyle="--",
            linewidth=1.3,
            label=fr"Actual $t/c={t_c_horizontal:.3f}$"
        )

        # --------------------------------------------------
        # Drag-divergence × actual t/c intersection
        # --------------------------------------------------

        tc_difference = tc_drag_divergence - t_c_horizontal

        for i in range(len(sweep_values) - 1):

            if tc_difference[i] * tc_difference[i + 1] <= 0:

                # Linear interpolation between the two points
                sweep_dd = (
                    sweep_values[i]
                    + (
                        -tc_difference[i]
                        / (tc_difference[i + 1] - tc_difference[i])
                    )
                    * (sweep_values[i + 1] - sweep_values[i])
                )

                constraints["drag_divergence_intersection"] = (
                    sweep_dd,
                    t_c_horizontal
                )

                # Intersection point
                ax.plot(
                    sweep_dd,
                    t_c_horizontal,
                    marker="o",
                    markersize=7,
                    color="blue",
                    zorder=5,
                    label=fr"Drag divergence: $\Lambda={sweep_dd:.2f}^\circ$"
                )

                break

        # --------------------------------------------------
        # Structural × actual t/c intersection
        # --------------------------------------------------

        if constraints["structural"] is not None:

            sweep_struct = constraints["structural"]

            constraints["structural_tc_intersection"] = (
                sweep_struct,
                t_c_horizontal
            )

            ax.plot(
                sweep_struct,
                t_c_horizontal,
                marker="o",
                markersize=7,
                color="red",
                zorder=5
            )

        # --------------------------------------------------
        # M_crest × actual t/c intersection
        # --------------------------------------------------

        if constraints["M_crest"] is not None:

            sweep_mcrest = constraints["M_crest"]

            constraints["M_crest_tc_intersection"] = (
                sweep_mcrest,
                t_c_horizontal
            )

            ax.plot(
                sweep_mcrest,
                t_c_horizontal,
                marker="o",
                markersize=7,
                color="green",
                zorder=5
            )

    # ==================================================
    # Plot formatting
    # ==================================================

    ax.set_xlim(sweep_range_deg)

    if t_c_horizontal is not None:

        curve_max = np.nanmax(tc_drag_divergence)

        ax.set_ylim(
            0,
            max(
                0.2,
                t_c_horizontal * 1.6,
                curve_max * 1.1
            )
        )

    ax.set_xlabel("Half-chord sweep angle, $\\lambda$ [deg]")
    ax.set_ylabel("Thickness-to-chord ratio, $t/c$")

    ax.set_title(
        f"Sweep Design Constraints "
        f"($M_\\infty={M_cruise}$, $C_L={CL}$)"
    )

    ax.grid(
        True,
        alpha=0.25
    )

    # Legend outside plot
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(1.02, 1),
        fontsize=8,
        handlelength=1.5,
        handletextpad=0.5,
        borderpad=0.4,
        labelspacing=0.4
    )

    # Make room for the legend
    fig.subplots_adjust(
        right=0.75
    )

    if save_path:
        fig.savefig(
            save_path,
            dpi=150,
            bbox_inches="tight"
        )

    if show:
        plt.show()

    return constraints, fig, ax
# ============================================================
# Wing area iteration
# ============================================================

def solve_wing_area(CL_target, q, f_cruise, M_TOM, S_guess=50.0,
                     tol=1e-6, max_iter=100):
    """
    Iteratively solve for the wing area S such that cl_design(q,
    f_cruise, M_TOM, S) equals a target design CL.

    Note: as currently written, cl_design(...) is directly invertible
    in S (CL_des is proportional to 1/S), so this converges in a
    single step. It's written as an explicit fixed-point iteration
    (rather than one-line algebra) so it matches the "iterate the
    wing loading" process from your coursework, and so it's ready to
    extend later if you add a feedback dependency (e.g. M_TOM or q
    depending on S).

    Parameters
    ----------
    CL_target : float
        Target design lift coefficient
    q : float
        Dynamic pressure [Pa]
    f_cruise : float
        Cruise mass fraction (as used in cl_design)
    M_TOM : float
        Take-off mass [kg]
    S_guess : float, optional
        Initial guess for wing area [m^2] (default 50.0)
    tol : float, optional
        Convergence tolerance on S [m^2] (default 1e-6)
    max_iter : int, optional
        Maximum number of iterations (default 100)

    Returns
    -------
    S : float
        Converged wing area [m^2]
    n_iter : int
        Number of iterations used
    """
    S = S_guess
    for i in range(max_iter):
        CL_current = cl_design(q, f_cruise, M_TOM, S)
        S_new = S * (CL_current / CL_target)
        if abs(S_new - S) < tol:
            return S_new, i + 1
        S = S_new
    raise RuntimeError("Wing area iteration did not converge")


# ============================================================
# Generalized per-airfoil container, for comparing airfoils
# ============================================================

@dataclass
class Airfoil:
    """
    Holds all the per-airfoil inputs this module needs, so the same
    pipeline (M_cr via Laitone's rule, M_DD via Mason's method) can be
    run for any airfoil and results compared side by side.

    Attributes
    ----------
    name : str
        Airfoil name/label, e.g. "SC(2)-0610"
    Cp0 : float
        Incompressible minimum Cp (suction peak) at the design/cruise
        condition — used for M_cr via find_critical_mach()
    ka : float
        Technology factor for Mason's M_DD formula (0.87 for NACA
        6-series, 0.935 for supercritical airfoils)
    t_c_streamwise : float
        Streamwise thickness-to-chord ratio, used in mach_dd()
    M_crest : float, optional
        Known/target crest critical Mach number for this airfoil, if
        you have one (e.g. from a published source), for comparison
        against the computed M_cr and M_DD
    gamma : float, optional
        Ratio of specific heats (default 1.4)
    """
    name: str
    Cp0: float
    ka: float
    t_c_streamwise: float
    M_crest: float = None
    gamma: float = 1.4


def analyze_airfoil(airfoil: Airfoil, Cl_cruise, sweep_deg):
    """
    Run the M_cr (Laitone) and M_DD (Mason) pipeline for one Airfoil,
    at a given cruise CL and sweep angle, and return a dict of results
    — so you can loop this over several Airfoil objects and directly
    compare M_cr, M_DD, and M_crest across airfoil families.

    Parameters
    ----------
    airfoil : Airfoil
        The airfoil to analyze
    Cl_cruise : float
        Cruise lift coefficient (used in mach_dd())
    sweep_deg : float
        Wing quarter-chord sweep angle [degrees] (used in mach_dd())

    Returns
    -------
    dict
        Keys: name, Cp0, M_cr, M_DD, M_crest (M_crest is whatever was
        stored on the Airfoil, possibly None)
    """
    M_cr = find_critical_mach(airfoil.Cp0, airfoil.gamma)
    M_DD = mach_dd(airfoil.ka, airfoil.t_c_streamwise, Cl_cruise, sweep_deg)
    return {
        "name": airfoil.name,
        "Cp0": airfoil.Cp0,
        "M_cr": M_cr,
        "M_DD": M_DD,
        "M_crest": airfoil.M_crest,
    }


if __name__ == "__main__":

    # ============================================================
    # GENERAL FLIGHT CONDITION INPUTS
    # ============================================================

    gamma = 1.4

    altitude_m = 10000.0
    M_cruise = 0.77
    rho_inf = 0.37957
    V_inf = 228.3112
    q = dynamic_pressure(rho_inf, V_inf)

    mass_fraction_cruise = 0.9375
    S_initial = 70.35
    M_TOM = 32211
    sweep_deg = 28.371339765533104 

    CL_target = 0.453561059164
    Cl_cruise = 0.4257

    # ============================================================
    # WING AREA / DESIGN CL
    # ============================================================

    CL_des = cl_design(
        q,
        mass_fraction_cruise,
        M_TOM,
        S_initial
    )

    print(f"C_L,des (at S_initial = {S_initial}) = {CL_des:.4f}")

    S_converged, n_iter = solve_wing_area(
        CL_target,
        q,
        mass_fraction_cruise,
        M_TOM,
        S_guess=S_initial
    )

    print(
        f"Converged wing area S = {S_converged:.4f} m^2 "
        f"(from S_initial = {S_initial}, {n_iter} iteration(s))"
    )


    # ============================================================
    # AIRFOIL 1
    # ============================================================

    airfoil_name = "SC(2)-0612"

    Cp0 = -0.41
    ka = 0.935
    t_c_streamwise = 0.12
    M_crest = 0.71

    print("\n========================================")
    print(f"Airfoil: {airfoil_name}")
    print("========================================")

    # Critical Mach
    M_cr = find_critical_mach(Cp0, gamma)

    print(f"Cp0       = {Cp0:.4f}")
    print(f"M_cr      = {M_cr:.4f}")
    print(f"M_crest   = {M_crest:.4f}")

    print(
        f"Cp at M_cr (Laitone) = "
        f"{cp_laitone(Cp0, M_cr, gamma):.4f}"
    )

    print(
        f"Cp_cr at M_cr        = "
        f"{cp_critical(M_cr, gamma):.4f}"
    )

    # Critical Mach plot
    plot_critical_mach(
        Cp0,
        gamma,
        save_path=f"{airfoil_name}_cp_vs_mach.png",
        show=False
    )

    # Drag divergence Mach
    M_drag_divergence = mach_dd(
        ka,
        t_c_streamwise,
        Cl_cruise,
        sweep_deg
    )

    print(f"M_DD      = {M_drag_divergence:.4f}")

    # Sweep vs t/c plot
    plot_sweep_tc_chart(
        CL=CL_target,
        M_DD=M_drag_divergence,
        ka=ka,
        t_c_horizontal=t_c_streamwise,
        M_cruise=M_cruise,
        M_crest=M_crest,
        save_path=f"{airfoil_name}_sweep_tc_chart.png",
        show=False
    )