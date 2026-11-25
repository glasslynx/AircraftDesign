"""WP4.2: cross-section properties of the wing box along the span.

Merged and generalised from Geometry_and_Bending.py (centroid, I_xx) and torsion.py
(torsion constant J, one or two cells).

Cross-section model (reader WP4.2, Fig. 1, App. D):
* trapezoid: front spar height h_f, rear spar height h_r, straight top and bottom skins
* thin walls; skins and spars include their own second moment of area
* stringers and spar caps are POINT AREAS (Huygens-Steiner term only)
* optional mid spar from the root to eta_end -> two-cell box inboard
* the shear centre is assumed to coincide with the centroid (reader WP4.1)
* the x-axis through the centroid is a principal axis (I_xz = 0, reader WP4.2)

Coordinates of one section: x from the local leading edge (+ aft), z from the chord line (+ up).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .design import WingBoxDesign
from .geometry import WingGeometry


# --------------------------------------------------------------------------- #
#  torsion constant (from torsion.py)                                          #
# --------------------------------------------------------------------------- #
def polygon_area(Q: np.ndarray) -> float:
    """Shoelace formula for the area of a polygon (vertices in order)."""
    x, z = Q[:, 0], Q[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(z, -1)) - np.dot(z, np.roll(x, -1)))


def torsion_constant(corners, t, t_mid=None, f_mid=None):
    """Torsion constant J of a one- or two-cell thin-walled box (Bredt-Batho).

    corners : (front-up, front-low, rear-low, rear-up), each (x, z)   [m]
    t       : wall thicknesses [top skin, rear spar, bottom skin, front spar]  [m]
    t_mid   : mid-spar web thickness (None -> single cell)                  [m]
    f_mid   : mid-spar position as a fraction of the box width (0 = front spar)

    Returns (J, q_webs): J [m4] and the shear flow per unit torque in each spar web
    [front, (mid), rear] [1/m2], used for the web shear stress.
    """
    FU, FL, RL, RU = (np.asarray(p, float) for p in corners)
    L = lambda p, q: float(np.linalg.norm(q - p))                     # wall length
    if t_mid is None:
        P = np.array([FU, RU, RL, FL])                                # going round the box
        A = polygon_area(P)
        s = L(FU, RU) / t[0] + L(RU, RL) / t[1] + L(RL, FL) / t[2] + L(FL, FU) / t[3]
        q = 1.0 / (2.0 * A)                                           # unit torque
        return 4.0 * A**2 / s, np.array([q, q])
    # two cells: split the box with the mid spar (on the straight skins)
    MT = FU + f_mid * (RU - FU)
    MB = FL + f_mid * (RL - FL)
    A1 = polygon_area(np.array([FU, MT, MB, FL]))                     # front cell
    A2 = polygon_area(np.array([MT, RU, RL, MB]))                     # rear cell
    s1 = L(FU, MT) / t[0] + L(MB, FL) / t[2] + L(FL, FU) / t[3]       # front cell walls, no mid spar
    s2 = L(MT, RU) / t[0] + L(RU, RL) / t[1] + L(RL, MB) / t[2]       # rear cell walls, no mid spar
    sm = L(MT, MB) / t_mid                                            # mid spar, shared
    # unknowns q1, q2, G dtheta/dy for a unit torque
    M = np.array([[s1 + sm, -sm, -2 * A1],     # front cell: twist-rate compatibility
                  [-sm, s2 + sm, -2 * A2],     # rear cell: twist-rate compatibility
                  [2 * A1, 2 * A2, 0.0]])      # torque balance 2 A1 q1 + 2 A2 q2 = 1
    q1, q2, k = np.linalg.solve(M, np.array([0.0, 0.0, 1.0]))
    return 1.0 / k, np.array([q1, q2 - q1, q2])


# --------------------------------------------------------------------------- #
#  one section (from Geometry_and_Bending.compute_section)                     #
# --------------------------------------------------------------------------- #
def stringer_x(x_front: float, x_rear: float, n: int) -> np.ndarray:
    """n stringers spaced evenly between the spars (none on the spars themselves)."""
    k = np.arange(1, n + 1)
    return x_front + (x_rear - x_front) * k / (n + 1)


def compute_section(y: float, design: WingBoxDesign, geom: WingGeometry) -> dict:
    """All section properties at one spanwise station y [m]."""
    lay = geom.layout
    eta = y / geom.planform.half_span
    c = float(geom.chord(y))
    xf, xr = lay.x_front_spar * c, lay.x_rear_spar * c
    hf, hr = float(geom.spar_height(y, lay.x_front_spar)), float(geom.spar_height(y, lay.x_rear_spar))
    zf, zr = float(geom.spar_mid_z(y, lay.x_front_spar)), float(geom.spar_mid_z(y, lay.x_rear_spar))

    t_top, t_bot = float(design.t_skin_top(eta)), float(design.t_skin_bot(eta))
    t_fs, t_rs = float(design.t_front_spar(eta)), float(design.t_rear_spar(eta))
    n_top = int(np.floor(design.n_str_top(eta) + 1e-9))
    n_bot = int(np.floor(design.n_str_bot(eta) + 1e-9))
    A_st, A_sb = float(design.A_str_top(eta)), float(design.A_str_bot(eta))
    A_cap = float(design.A_cap(eta))
    ms = design.mid_spar
    has_mid = ms is not None and eta <= ms.eta_end + 1e-9

    # corners (front-up, front-low, rear-low, rear-up)
    FU, FL = (xf, zf + hf / 2), (xf, zf - hf / 2)
    RL, RU = (xr, zr - hr / 2), (xr, zr + hr / 2)
    z_top = lambda x: FU[1] + (RU[1] - FU[1]) * (x - xf) / (xr - xf)
    z_bot = lambda x: FL[1] + (RL[1] - FL[1]) * (x - xf) / (xr - xf)

    # elements: (area, x, z, own second moment about its own centroid, parallel to x)
    el = []
    for t, P, Q in ((t_top, FU, RU), (t_bot, FL, RL)):                       # skins
        Ls = float(np.hypot(Q[0] - P[0], Q[1] - P[1]))
        dz = Q[1] - P[1]
        el.append((t * Ls, (P[0] + Q[0]) / 2, (P[1] + Q[1]) / 2, t * Ls * dz**2 / 12))
    el.append((t_fs * hf, xf, zf, t_fs * hf**3 / 12))                       # front spar
    el.append((t_rs * hr, xr, zr, t_rs * hr**3 / 12))                       # rear spar
    t_mid = h_mid = None
    if has_mid:
        x_m = ms.x_c * c
        t_mid = float(ms.t(eta))
        h_mid = z_top(x_m) - z_bot(x_m)
        el.append((t_mid * h_mid, x_m, (z_top(x_m) + z_bot(x_m)) / 2, t_mid * h_mid**3 / 12))
    xs_top, xs_bot = stringer_x(xf, xr, n_top), stringer_x(xf, xr, n_bot)
    el += [(A_st, x, z_top(x), 0.0) for x in xs_top]                         # stringers (point areas)
    el += [(A_sb, x, z_bot(x), 0.0) for x in xs_bot]
    if A_cap > 0:
        el += [(A_cap, p[0], p[1], 0.0) for p in (FU, FL, RL, RU)]           # spar caps (point areas)

    e = np.array(el)
    A = e[:, 0].sum()
    x_c = float((e[:, 0] * e[:, 1]).sum() / A)
    z_c = float((e[:, 0] * e[:, 2]).sum() / A)
    I_xx = float((e[:, 3] + e[:, 0] * (e[:, 2] - z_c) ** 2).sum())

    corners = [FU, FL, RL, RU]
    f_mid = (ms.x_c - lay.x_front_spar) / (lay.x_rear_spar - lay.x_front_spar) if has_mid else None
    J, q_webs = torsion_constant(corners, [t_top, t_rs, t_bot, t_fs], t_mid, f_mid)
    t_webs = np.array([t_fs, t_mid, t_rs]) if has_mid else np.array([t_fs, t_rs])
    sum_ht = t_fs * hf + t_rs * hr + (t_mid * h_mid if has_mid else 0.0)
    return dict(
        y=y, chord=c, area=A, x_c=x_c, z_c=z_c, I_xx=I_xx, J=J,
        h_f=hf, h_r=hr, h_mid=h_mid or 0.0, width=xr - xf,
        t_skin_top=t_top, t_skin_bot=t_bot, t_front_spar=t_fs, t_rear_spar=t_rs, t_mid_spar=t_mid or 0.0,
        n_str_top=n_top, n_str_bot=n_bot, A_str_top=A_st, A_str_bot=A_sb, A_cap=A_cap,
        n_cells=2 if has_mid else 1,
        z_extreme=max(abs(p[1] - z_c) for p in corners),
        sum_ht_spars=sum_ht,
        tau_web_per_T=float(np.max(np.abs(q_webs) / t_webs)),
        corners=np.array(corners), stringers_top=np.column_stack([xs_top, [z_top(x) for x in xs_top]]),
        stringers_bot=np.column_stack([xs_bot, [z_bot(x) for x in xs_bot]]),
    )


# --------------------------------------------------------------------------- #
#  spanwise distribution                                                       #
# --------------------------------------------------------------------------- #
_ARRAYS = ("chord", "area", "x_c", "z_c", "I_xx", "J", "h_f", "h_r", "h_mid", "width",
           "t_skin_top", "t_skin_bot", "t_front_spar", "t_rear_spar", "t_mid_spar",
           "n_str_top", "n_str_bot", "A_str_top", "A_str_bot", "A_cap", "n_cells",
           "z_extreme", "sum_ht_spars", "tau_web_per_T")


@dataclass
class SectionProps:
    """Section properties of one design on a spanwise grid (arrays over y)."""
    design: WingBoxDesign
    y: np.ndarray
    data: dict

    def __getattr__(self, k):
        try:
            return self.__dict__["data"][k]
        except KeyError:
            raise AttributeError(k) from None

    def mass_half(self, rho: float) -> float:
        """Mass of ONE half-wing box (skins, spars, stringers, caps; no ribs) [kg]."""
        return float(np.trapezoid(rho * self.area, self.y))


def section_properties(design: WingBoxDesign, geom: WingGeometry, y: np.ndarray) -> SectionProps:
    rows = [compute_section(float(yi), design, geom) for yi in y]
    data = {k: np.array([r[k] for r in rows]) for k in _ARRAYS}
    return SectionProps(design, np.asarray(y, float), data)
