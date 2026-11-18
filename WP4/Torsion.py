import numpy as np
from scipy import integrate
from scipy.interpolate import interp1d

G = 28e9

def torsion_constant(corners, t):
    """J = 4 A^2 / sum(l_i / t_i)   (Bredt-Batho, single closed cell) [m^4]."""
    P = np.asarray(corners, float)
    x, z = P[:, 0], P[:, 1]
    A = 0.5 * abs(np.dot(x, np.roll(z, -1)) - np.dot(z, np.roll(x, -1)))  # shoelace
    s = sum(np.linalg.norm(P[(i + 1) % 4] - P[i]) / t[i] for i in range(4))
    return 4.0 * A ** 2 / s

def twist_function(T, J, y_max, G=G, n=400):
    """
    theta(y) = int_0^y T(s) / (G J(s)) ds, theta(0) = 0.
    T : callable y -> torque about the centroid [Nm]
    J : callable y -> torsion constant [m^4]
    Returns a callable theta(y) in radians.
    """
    y = np.linspace(0.0, y_max, n)
    f = np.array([T(yi) / (G * J(yi)) for yi in y])
    theta = integrate.cumulative_trapezoid(f, y, initial=0.0)
    return interp1d(y, theta, kind="cubic")
