"""Planform and airfoil geometry of the equivalent unswept wing (reader App. A.3).

Coordinate system used throughout WP4 (README sec. 3):
    y : spanwise, from the root (y = 0, centreline) to the tip (y = b/2)
    x : chordwise, from the local leading edge, positive aft
    z : normal to the chord plane, positive up
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.interpolate import interp1d

from .config import Planform, WingBoxLayout


class Airfoil:
    """Selig/Lednicer-agnostic .dat reader that exposes thickness t(x/c)."""

    def __init__(self, path: Path):
        pts = []
        for line in Path(path).read_text().splitlines():
            parts = line.split()
            if len(parts) != 2:
                continue
            try:
                pts.append((float(parts[0]), float(parts[1])))
            except ValueError:
                continue  # header line
        xy = np.array(pts)
        i_le = int(np.argmin(xy[:, 0]))
        a, b = xy[: i_le + 1], xy[i_le:]
        upper, lower = (a, b) if a[:, 1].mean() > b[:, 1].mean() else (b, a)
        upper = upper[np.argsort(upper[:, 0])]
        lower = lower[np.argsort(lower[:, 0])]
        self.name = Path(path).stem
        self._zu = interp1d(upper[:, 0], upper[:, 1], kind="linear")
        self._zl = interp1d(lower[:, 0], lower[:, 1], kind="linear")
        self.upper, self.lower = upper, lower

    def thickness(self, x_c):
        """Local thickness / chord at chord fraction x_c."""
        return self._zu(x_c) - self._zl(x_c)

    @property
    def t_c_max(self) -> float:
        x = np.linspace(0.01, 0.99, 981)
        return float(self.thickness(x).max())


@dataclass(frozen=True)
class WingGeometry:
    planform: Planform
    layout: WingBoxLayout
    airfoil: Airfoil

    # --- planform ---------------------------------------------------------
    def chord(self, y):
        p = self.planform
        return p.c_root + (p.c_tip - p.c_root) * np.asarray(y) / p.half_span

    @property
    def y_MAC(self) -> float:
        p = self.planform
        lam = p.taper
        return p.half_span / 3 * (1 + 2 * lam) / (1 + lam)

    @property
    def x_LEMAC(self) -> float:
        """x of the MAC leading edge, aircraft frame with root LE at 0 [m]."""
        return float(self.x_LE_swept(self.y_MAC))

    def x_from_LEMAC_to_local(self, dx_LEMAC: float, y: float) -> float:
        """Convert an x measured from LEMAC (+ aft) to x measured from the local LE at span y."""
        return float(self.x_LEMAC + dx_LEMAC - self.x_LE_swept(y))

    def x_LE_swept(self, y):
        """Leading-edge x of the REAL swept wing (aircraft frame, root LE = 0)."""
        return np.asarray(y) * np.tan(np.radians(self.planform.sweep_LE_deg))

    # --- wing box outline (reader Fig. 1, symmetric trapezoid) ------------
    def spar_height(self, y, x_c):
        """Height of a spar at chord fraction x_c (straight skins between front and rear spar)."""
        lay = self.layout
        h_f = self.airfoil.thickness(lay.x_front_spar)
        h_r = self.airfoil.thickness(lay.x_rear_spar)
        frac = (np.asarray(x_c) - lay.x_front_spar) / (lay.x_rear_spar - lay.x_front_spar)
        return (h_f + (h_r - h_f) * frac) * self.chord(y)

    def box_width(self, y):
        lay = self.layout
        return (lay.x_rear_spar - lay.x_front_spar) * self.chord(y)
