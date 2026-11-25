"""WP4.2: bending deflection and twist distribution of the wing box (reader App. D).

(from deflection_and_intergration.py)

Governing equations, reader sign convention (App. C: an upward load gives a NEGATIVE M):
    d2v/dy2   = -M(y) / (E I_xx(y))
    dtheta/dy =  T(y) / (G J(y))
Cantilever clamped at the root y = 0:  v(0) = 0, dv/dy(0) = 0, theta(0) = 0

    dv/dy(y) = - int_0^y M / (E I_xx) dy
    v(y)     =   int_0^y dv/dy dy
    theta(y) =   int_0^y T / (G J) dy

v      displacement normal to the chord plane, + up [m]
theta  twist about the y axis, + nose-up [rad]
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import integrate


def make_function(y_points, values):
    """Point data -> callable f(y) (piecewise linear, so property steps stay sharp)."""
    y_points, values = np.asarray(y_points, float), np.asarray(values, float)
    return lambda y: np.interp(y, y_points, values)


def integral_from_root(f, y_points, method: str = "quad") -> np.ndarray:
    """int_0^{y_i} f dy for every y_i in y_points (y_points[0] must be the root).

    "quad": scipy.integrate.quad over each grid interval [y_(i-1), y_i] and a running sum,
            so each part of the span is integrated once and quad never crosses a grid point
            (where the stiffness may jump).
    "trapezoid": cumulative trapezoid of f evaluated on the grid.
    """
    y_points = np.asarray(y_points, float)
    if method == "trapezoid":
        return integrate.cumulative_trapezoid(f(y_points), y_points, initial=0.0)
    result = np.zeros(len(y_points))
    for i in range(1, len(y_points)):
        piece, _err = integrate.quad(f, y_points[i - 1], y_points[i])
        result[i] = result[i - 1] + piece
    return result


@dataclass
class Deflection:
    y: np.ndarray
    slope: np.ndarray     # dv/dy [-]
    v: np.ndarray         # displacement, + up [m]
    theta: np.ndarray     # twist, + nose-up [rad]

    @property
    def v_tip(self) -> float:
        return float(self.v[-1])

    @property
    def theta_tip_deg(self) -> float:
        return float(np.degrees(self.theta[-1]))


def bending_deflection(y, M, EI, method="quad"):
    """Slope and displacement from M(y) (reader sign) and EI(y), arrays on the grid y."""
    f = make_function(y, -np.asarray(M) / np.asarray(EI))
    slope = integral_from_root(f, y, method)
    v = integral_from_root(make_function(y, slope), y, method)
    return slope, v


def twist(y, T, GJ, method="quad"):
    """Twist theta(y) [rad] from T(y) and GJ(y), arrays on the grid y."""
    return integral_from_root(make_function(y, np.asarray(T) / np.asarray(GJ)), y, method)


def deflection(y, M, T, EI, GJ, method="quad") -> Deflection:
    slope, v = bending_deflection(y, M, EI, method)
    return Deflection(y=np.asarray(y), slope=slope, v=v, theta=twist(y, T, GJ, method))
