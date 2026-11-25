"""Fuel mass distribution in the wet wing box (analytic box, the WP3 method).

The tank is the real airfoil section between the spars, from tank_eta_start to
tank_eta_end. Its cross-section area is k_box c(y)^2 (k_box = int t(x/c) d(x/c) between
the spars), so with the fuel spread uniformly over the volume

    m_f'(y) = m_half / int(c^2 dy) * c(y)^2      for y inside the tank, 0 outside.

The chordwise fuel centroid is the area centroid of the same airfoil section.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.integrate import trapezoid

from .geometry import WingGeometry


def box_section(geom: WingGeometry, n: int = 2001) -> tuple[float, float]:
    """Area per c^2 and x-centroid (chord fraction) of the airfoil between the spars."""
    lay = geom.layout
    x = np.linspace(lay.x_front_spar, lay.x_rear_spar, n)
    t = geom.airfoil.thickness(x)
    k = float(trapezoid(t, x))
    return k, float(trapezoid(t * x, x) / k)


@dataclass
class FuelTank:
    geom: WingGeometry
    eta_start: float
    eta_end: float
    density: float
    usable_factor: float
    k_box: float = field(init=False)
    x_c_frac: float = field(init=False)

    def __post_init__(self):
        b2 = self.geom.planform.half_span
        self.k_box, self.x_c_frac = box_section(self.geom)
        self.y_start, self.y_end = self.eta_start * b2, self.eta_end * b2
        y = np.linspace(self.y_start, self.y_end, 2001)
        self._c2_int = float(trapezoid(self.geom.chord(y) ** 2, y))      # int c^2 dy over the tank
        self.volume_half = self.k_box * self._c2_int                     # [m3], one half wing

    @property
    def capacity_half(self) -> float:
        """Usable fuel mass one half wing can hold [kg]."""
        return self.density * self.usable_factor * self.volume_half

    def split(self, m_fuel_total: float) -> tuple[float, float]:
        """(fuel in ONE half wing, fuel left for a fuselage tank) for a total fuel mass [kg]."""
        m_half = min(m_fuel_total / 2.0, self.capacity_half)
        return m_half, m_fuel_total - 2.0 * m_half

    def mass_per_span(self, y, m_half: float) -> np.ndarray:
        """Fuel mass per unit span [kg/m] for m_half kg in this half wing."""
        y = np.asarray(y, dtype=float)
        inside = (y >= self.y_start - 1e-12) & (y <= self.y_end + 1e-12)
        return np.where(inside, m_half * self.geom.chord(y) ** 2 / self._c2_int, 0.0)
