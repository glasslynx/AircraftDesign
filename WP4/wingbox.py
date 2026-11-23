"""WP4.2: wing-box design description and cross-section properties.

Cross-section model (reader Fig. 1 + Appendix D):
* symmetric trapezoid: front spar height h_f, rear spar height h_r, straight skins
* thin walls; skins and spars have their own second moment of area
* stringers and spar caps are POINT AREAS (Steiner term only, reader WP4.2)
* optional extra (mid) spars, each running from the root to eta_end -> multi-cell
* shear centre assumed at the centroid (reader WP4.1)

All properties are evaluated vectorised over a spanwise grid.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

from .geometry import WingGeometry


# --------------------------------------------------------------------------- #
#  spanwise parameter description                                             #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SpanwiseVar:
    """Value defined at breakpoints eta = y/(b/2), linear or stepwise in between."""
    eta: tuple[float, ...]
    val: tuple[float, ...]
    kind: str = "linear"          # "linear" | "previous" (step, value holds until next breakpoint)

    def __call__(self, eta) -> np.ndarray:
        eta = np.asarray(eta, dtype=float)
        e, v = np.asarray(self.eta), np.asarray(self.val)
        if self.kind == "linear":
            return np.interp(eta, e, v)
        idx = np.clip(np.searchsorted(e, eta, side="right") - 1, 0, len(v) - 1)
        return v[idx]

    @staticmethod
    def const(v: float) -> "SpanwiseVar":
        return SpanwiseVar((0.0, 1.0), (v, v))


@dataclass(frozen=True)
class MidSpar:
    x_c: float           # chord position
    eta_end: float       # spar ends (merges / terminates at a rib) at this eta
    t_factor: float = 1.0  # web thickness relative to the main spars


@dataclass(frozen=True)
class WingBoxDesign:
    name: str
    label: str
    t_skin: SpanwiseVar              # top and bottom skin thickness [m]
    t_spar: SpanwiseVar              # spar web thickness [m]
    n_str: SpanwiseVar               # stringers per skin (top = bottom), stepwise
    A_str: SpanwiseVar               # area of one stringer [m2]
    A_cap: SpanwiseVar = field(default_factory=lambda: SpanwiseVar.const(0.0))  # each of 4 corner caps [m2]
    mid_spars: tuple[MidSpar, ...] = ()
    philosophy: str = ""

    def with_(self, **kw) -> "WingBoxDesign":
        return replace(self, **kw)


# --------------------------------------------------------------------------- #
#  section properties                                                         #
# --------------------------------------------------------------------------- #
@dataclass
class SectionProps:
    y: np.ndarray
    area: np.ndarray          # structural area [m2]
    x_c: np.ndarray           # centroid / shear centre, aft of LOCAL LE [m]
    z_c: np.ndarray           # centroid height above box mid-plane [m]
    Ixx: np.ndarray           # about centroidal axis parallel to chord [m4]
    J: np.ndarray             # torsional constant [m4]
    A_enc: np.ndarray         # total enclosed area [m2]
    h_f: np.ndarray
    h_r: np.ndarray
    width: np.ndarray
    t_skin: np.ndarray
    t_spar: np.ndarray
    n_str: np.ndarray
    sum_ht_spars: np.ndarray  # sum of spar web areas h*t [m2]
    tau_t_per_T: np.ndarray   # max spar shear stress per unit torque [1/m3]
    n_cells: np.ndarray

    def z_extreme(self) -> np.ndarray:
        """Largest distance from the neutral axis to the outer fibre (front spar corners)."""
        return np.maximum(self.h_f / 2 - self.z_c, self.h_f / 2 + self.z_c)


def _torsion(widths, heights, t_walls, t_top, t_bot):
    """Multi-cell torsional constant per unit G (reader App. D.1, generalised).

    widths : (N, nc) cell widths;  heights : (N, nc+1) wall heights;
    t_walls: (N, nc+1) wall thicknesses.  Returns J (N,), spar shear flows per
    unit torque (N, nc+1), enclosed area (N,).
    """
    N, nc = widths.shape
    A = widths * (heights[:, :-1] + heights[:, 1:]) / 2.0
    L = np.sqrt(widths**2 + ((heights[:, 1:] - heights[:, :-1]) / 2.0) ** 2)
    d_wall = heights / t_walls                                   # ds/t of each spar web
    d_cell = L / t_top[:, None] + L / t_bot[:, None] + d_wall[:, :-1] + d_wall[:, 1:]
    # unknowns: q_1..q_nc, k = G dtheta/dz ; equations per cell + torque equation
    M = np.zeros((N, nc + 1, nc + 1))
    rhs = np.zeros((N, nc + 1))
    for i in range(nc):
        M[:, i, i] = d_cell[:, i]
        if i > 0:
            M[:, i, i - 1] = -d_wall[:, i]
        if i < nc - 1:
            M[:, i, i + 1] = -d_wall[:, i + 1]
        M[:, i, nc] = -2.0 * A[:, i]
        M[:, nc, i] = 2.0 * A[:, i]
    rhs[:, nc] = 1.0                                             # unit torque
    sol = np.linalg.solve(M, rhs[..., None])[..., 0]
    q, k = sol[:, :nc], sol[:, nc]
    J = 1.0 / k
    q_pad = np.concatenate([np.zeros((N, 1)), q, np.zeros((N, 1))], axis=1)
    q_wall = q_pad[:, 1:] - q_pad[:, :-1]                        # net flow in each spar web
    return J, q_wall, A.sum(axis=1)


def section_properties(design: WingBoxDesign, geom: WingGeometry, y: np.ndarray) -> SectionProps:
    y = np.asarray(y, dtype=float)
    eta = y / geom.planform.half_span
    lay = geom.layout
    c = geom.chord(y)
    w = geom.box_width(y)
    hf = geom.spar_height(y, lay.x_front_spar)
    hr = geom.spar_height(y, lay.x_rear_spar)
    tsk = design.t_skin(eta)
    tsp = design.t_spar(eta)
    nst = np.floor(design.n_str(eta) + 1e-9)
    Ast = design.A_str(eta)
    Acap = design.A_cap(eta)
    x0 = lay.x_front_spar * c                     # front-spar x from LE

    zf, dz = hf / 2, (hr - hf) / 2                # top skin: z = zf + dz*s, s in [0,1]
    L = np.sqrt(w**2 + dz**2)

    # --- area, first and second moments (about box mid-plane z=0, x from front spar)
    A_list, Ax, Az, Azz = [], [], [], []

    def add(A, x, z, I_own):
        A_list.append(A); Ax.append(A * x); Az.append(A * z); Azz.append(I_own + A * z**2)

    for sgn in (+1, -1):                          # top / bottom skin
        add(tsk * L, w / 2, sgn * (zf + dz / 2), tsk * L * dz**2 / 12)
        # n stringers at s_k = k/(n+1)
        s1 = nst / 2
        s2 = nst * (2 * nst + 1) / (6 * (nst + 1))
        A_s = nst * Ast
        A_list.append(A_s)
        Ax.append(Ast * w * s1)
        Az.append(sgn * Ast * (nst * zf + dz * s1))
        Azz.append(Ast * (nst * zf**2 + 2 * zf * dz * s1 + dz**2 * s2))
        # corner caps
        add(Acap, 0.0, sgn * zf, 0.0)
        add(Acap, w, sgn * (zf + dz), 0.0)
    add(tsp * hf, 0.0, 0.0, tsp * hf**3 / 12)     # front spar
    add(tsp * hr, w, 0.0, tsp * hr**3 / 12)       # rear spar
    sum_ht = tsp * (hf + hr)

    # --- mid spars and torsion cells
    active = [eta <= ms.eta_end + 1e-12 for ms in design.mid_spars]
    for ms, act in zip(design.mid_spars, active):
        xm = (ms.x_c - lay.x_front_spar) * c
        hm = geom.spar_height(y, ms.x_c)
        tm = tsp * ms.t_factor * act
        add(tm * hm, xm, 0.0, tm * hm**3 / 12)
        sum_ht = sum_ht + tm * hm

    A = np.sum(A_list, axis=0)
    xbar = np.sum(Ax, axis=0) / A
    zbar = np.sum(Az, axis=0) / A
    Ixx = np.sum(Azz, axis=0) - A * zbar**2

    J = np.empty_like(y)
    tau_per_T = np.empty_like(y)
    A_enc = np.empty_like(y)
    ncell = np.ones_like(y, dtype=int)
    # group stations by the set of active mid spars (piecewise-constant topology)
    keys = np.array([sum(int(a[i]) << k for k, a in enumerate(active)) for i in range(len(y))]) \
        if active else np.zeros(len(y), dtype=int)
    for key in np.unique(keys):
        sel = keys == key
        mids = [ms for k, ms in enumerate(design.mid_spars) if key >> k & 1]
        mids = sorted(mids, key=lambda m: m.x_c)
        xs = [lay.x_front_spar] + [m.x_c for m in mids] + [lay.x_rear_spar]
        tf = [1.0] + [m.t_factor for m in mids] + [1.0]
        cs = c[sel][:, None]
        xpos = np.array(xs)[None, :] * cs
        heights = np.column_stack([geom.spar_height(y[sel], xc) for xc in xs])
        twall = tsp[sel][:, None] * np.array(tf)[None, :]
        Jk, qw, Ae = _torsion(np.diff(xpos, axis=1), heights, twall, tsk[sel], tsk[sel])
        J[sel], A_enc[sel], ncell[sel] = Jk, Ae, len(xs) - 1
        tau_per_T[sel] = np.max(np.abs(qw) / twall, axis=1)

    return SectionProps(y=y, area=A, x_c=x0 + xbar, z_c=zbar, Ixx=Ixx, J=J, A_enc=A_enc,
                        h_f=hf, h_r=hr, width=w, t_skin=tsk, t_spar=tsp, n_str=nst,
                        sum_ht_spars=sum_ht, tau_t_per_T=tau_per_T, n_cells=ncell)


def box_mass(props: SectionProps, rho: float) -> float:
    """Mass of ONE half-wing box (skins, spars, stringers, caps; no ribs) [kg]."""
    return float(np.trapezoid(rho * props.area, props.y))
