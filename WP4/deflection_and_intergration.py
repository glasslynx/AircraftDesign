"""
WP4.2 - Bending deflection and twist distribution of the wing box.

Governing equations (Appendix D):
    d2v/dy2   = -M_x(y) / (E * I_xx(y))
    dtheta/dy =  T(y)   / (G * J(y))

Boundary conditions (wing is a cantilever, clamped at the root y = 0):
    v(0) = 0,  dv/dy(0) = 0,  theta(0) = 0

Solution steps (Appendix D.2):
    dv/dy(y) = - integral_0^y  M_x / (E I_xx) dy
    v(y)     =   integral_0^y  dv/dy dy
    theta(y) =   integral_0^y  T / (G J) dy
Integrals: scipy.integrate.quad (Appendix C.1).
Callable functions from point data: scipy.interpolate.interp1d, kind="cubic" (Appendix B.3).

Conventions (agree these with the WP4.1 group):
    y      spanwise coordinate from root (0) to tip (b/2) of the equivalent
           unswept wing (Appendix A.3) [m]
    v      displacement in z, normal to the wing box symmetry axis,
           positive upwards [m]
    theta  rotation (twist), positive nose-up [rad]
    M_x, T from WP4.1, with the reader's sign convention (Appendix C):
           an upward lift load gives a NEGATIVE M_x.

Stiffness requirements (WP4.2):
    - tip displacement shall not exceed 15% of the total span b
    - tip rotation shall stay within +/- 10 degrees
"""

import numpy as np
import matplotlib.pyplot as plt
import scipy as sp
from scipy import integrate, interpolate

# Material: AL2024-T81 for all structural elements (reader, WP4.2).
# Source: Aerospace metals.
E = 72.4e9   # Young's modulus [Pa]
G = 28.0e9   # Shear modulus   [Pa]


def integral_from_root(f, y_points):
    """Integral of f from 0 to each point in y_points, using scipy.integrate.quad.

    integral_0^y_i f dy is built as the sum of quad integrals over the
    intervals [y_0, y_1], [y_1, y_2], ..., [y_(i-1), y_i]. This gives the same
    result as integrating from 0 every time, but each part of the span is
    integrated only once, which keeps the nested integrals fast.
    Tip: include any spanwise positions where the stiffness jumps (e.g. a
    change in stringer number) in y_points, so quad never has to integrate
    across a discontinuity.
    """
    if y_points[0] != 0.0:
        raise ValueError("y_points must start at the root, y = 0")
    result = np.zeros(len(y_points))
    for i in range(1, len(y_points)):
        piece, _error = sp.integrate.quad(f, y_points[i - 1], y_points[i])
        result[i] = result[i - 1] + piece      # result[0] = 0 applies the root boundary condition
    return result


def make_function(y_points, values):
    """Turn point data into a callable function (Appendix B.3: interp1d, cubic)."""
    return sp.interpolate.interp1d(y_points, values, kind="cubic", fill_value="extrapolate")


def bending_deflection(y_points, M, Ixx, E=E):
    """Bending slope and displacement, Appendix D.2.

    y_points : spanwise stations, from 0 (root) to b/2 (tip)
    M        : callable M_x(y) [Nm], from WP4.1
    Ixx      : callable I_xx(y) [m^4], from the section-property module
    Returns two callables: slope dv/dy(y) and displacement v(y).
    """
    # Step 1: dv/dy(y) = - integral_0^y M_x / (E I_xx) dy      (dv/dy(0) = 0)
    slope_values = -integral_from_root(lambda y: M(y) / (E * Ixx(y)), y_points)
    slope = make_function(y_points, slope_values)

    # Step 2: v(y) = integral_0^y dv/dy dy                    (v(0) = 0)
    v_values = integral_from_root(slope, y_points)
    v = make_function(y_points, v_values)
    return slope, v


def twist(y_points, T, J, G=G):
    """Twist distribution, Appendix D.2.

    T : callable T(y) [Nm], from WP4.1
    J : callable J(y) [m^4], from the section-property module
    Returns a callable theta(y) [rad].
    """
    # theta(y) = integral_0^y T / (G J) dy                     (theta(0) = 0)
    theta_values = integral_from_root(lambda y: T(y) / (G * J(y)), y_points)
    return make_function(y_points, theta_values)


def check_requirements(v, theta, b):
    """Check the two WP4.2 stiffness requirements at the wing tip (y = b/2)."""
    v_tip = float(v(b / 2))
    theta_tip_deg = float(np.degrees(theta(b / 2)))
    return {
        "tip displacement [m]": v_tip,
        "limit, 15% of span [m]": 0.15 * b,
        "displacement OK": abs(v_tip) <= 0.15 * b,
        "tip rotation [deg]": theta_tip_deg,
        "rotation OK (+/-10 deg)": abs(theta_tip_deg) <= 10.0,
    }


def plot_results(cases, b, n_plot=500):
    """Displacement and twist plots for the report (deliverable WP4.2 d).

    cases : list of (label, v, theta) tuples, e.g. one per load case
            for one design option, so each figure shows several load cases.
    """
    y = np.linspace(0.0, b / 2, n_plot)
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(7, 6))

    for label, v, theta in cases:
        ax1.plot(y, v(y), label=label)
        ax2.plot(y, np.degrees(theta(y)), label=label)

    ax1.axhline(0.15 * b, ls="--", c="r", label="Limit: 15% of span")
    ax1.axhline(-0.15 * b, ls="--", c="r")
    ax1.set_ylabel("Displacement v [m]")
    ax1.grid(True)
    ax1.legend()

    ax2.axhline(10, ls="--", c="r", label="Limit: ±10°")
    ax2.axhline(-10, ls="--", c="r")
    ax2.set_ylabel("Rotation θ [deg]")
    ax2.set_xlabel("Spanwise position y [m]")
    ax2.grid(True)
    ax2.legend()

    fig.tight_layout()
    return fig

