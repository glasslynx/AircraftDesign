"""WP4.3: verify one hand-chosen wing-box design against every load case.

(replaces the empty loop in design_calculator.py)

Requirements (reader WP4.2), checked at LIMIT load:
    |v_tip|     <= 0.15 b          (tip displacement, full span b)
    |theta_tip| <= 10 deg          (tip rotation)
Optional, if requirements.strength_check = true (not a WP4 requirement; WP5 adds buckling):
    sigma = 1.5 (|M| z_max / I_xx + |N| / A)                  <= sigma_yield
    tau   = 1.5 (k_v |S| / sum(h t)_webs + |T| q_web,max / t)  <= sigma_yield / sqrt(3)
Utilisation = applied / allowed; a design is compliant when every utilisation <= 1.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .config import Aircraft
from .deflection import Deflection, deflection
from .design import WingBoxDesign
from .loads import CaseLoads
from .section import SectionProps, section_properties


@dataclass
class CaseResult:
    loads: CaseLoads
    S: np.ndarray
    M: np.ndarray
    T: np.ndarray
    N: np.ndarray
    defl: Deflection
    sigma: np.ndarray      # max |normal stress| at ULTIMATE load [Pa]
    tau: np.ndarray        # max spar-web shear stress at ULTIMATE load [Pa]

    @property
    def case(self):
        return self.loads.case


@dataclass
class DesignResult:
    design: WingBoxDesign
    props: SectionProps
    cases: list[CaseResult]
    mass_half: float
    limits: dict = field(default_factory=dict)

    @property
    def mass_total(self) -> float:
        return 2 * self.mass_half

    _KEYS = {
        "v_tip": lambda r: abs(r.defl.v_tip),
        "theta_tip": lambda r: abs(r.defl.theta_tip_deg),
        "sigma": lambda r: float(r.sigma.max()),
        "tau": lambda r: float(r.tau.max()),
    }

    def worst(self, key: str) -> tuple[float, CaseResult]:
        f = self._KEYS[key]
        r = max(self.cases, key=f)
        return f(r), r

    def utilisation(self) -> dict[str, float]:
        lim = self.limits
        out = {"v_tip": self.worst("v_tip")[0] / lim["v_tip"],
               "theta_tip": self.worst("theta_tip")[0] / lim["theta_tip"]}
        if lim["strength"]:
            out["sigma"] = self.worst("sigma")[0] / lim["sigma"]
            out["tau"] = self.worst("tau")[0] / lim["tau"]
        return out

    @property
    def compliant(self) -> bool:
        return all(u <= 1.0 + 1e-9 for u in self.utilisation().values())

    def result(self, case_id: str) -> CaseResult:
        return next(r for r in self.cases if r.case.id == case_id)


def requirement_limits(ac: Aircraft) -> dict:
    r, m = ac.req, ac.material
    return {"v_tip": r.tip_deflection_frac_span * ac.planform.b, "theta_tip": r.tip_twist_deg,
            "strength": r.strength_check, "sigma": m.sigma_y, "tau": m.sigma_y / np.sqrt(3.0)}


def evaluate_design(ac: Aircraft, design: WingBoxDesign, geom, case_loads: list[CaseLoads]) -> DesignResult:
    y = case_loads[0].y
    props = section_properties(design, geom, y)
    E, G, sf = ac.material.E, ac.material.G, ac.vn.safety_factor
    k = sf if ac.req.stiffness_at_ultimate else 1.0
    EI, GJ = E * props.I_xx, G * props.J
    results = []
    for cl in case_loads:
        S, M, N = cl.shear(), cl.bending(), cl.axial()
        T = cl.torque(props.x_c)
        d = deflection(y, k * M, k * T, EI, GJ, ac.numerics.deflection_method)
        sigma = sf * (np.abs(M) * props.z_extreme / props.I_xx + np.abs(N) / props.area)
        tau = sf * (ac.req.k_shear * np.abs(S) / props.sum_ht_spars + np.abs(T) * props.tau_web_per_T)
        results.append(CaseResult(cl, S, M, T, N, d, sigma, tau))
    return DesignResult(design, props, results, props.mass_half(ac.material.rho), requirement_limits(ac))


def critical_cases(case_loads: list[CaseLoads]) -> dict[str, CaseLoads]:
    """Most critical positive / negative cases = extreme ROOT bending moment.

    Root bending dominates the tip deflection (v ~ double integral of M/EI) and the skin
    stresses, and it does not depend on the wing-box design (the inertial loads use the
    Class II wing mass). With the reader sign, the positive case has the most NEGATIVE M_root.
    """
    pos = [c for c in case_loads if c.case.n > 0]
    neg = [c for c in case_loads if c.case.n < 0]
    return {"positive": min(pos, key=lambda c: c.bending()[0]),
            "negative": max(neg, key=lambda c: c.bending()[0])}
