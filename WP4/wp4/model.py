"""Assembles the whole WP4 model from the input files (one call: build_model())."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import DEFAULT_AIRCRAFT, Aircraft, load_aircraft
from .design import WingBoxDesign
from .fuel import FuelTank
from .geometry import Airfoil, WingGeometry
from .loadcases import LoadCase, build_load_cases
from .loads import CaseLoads, LoadModel
from .vn import VnDiagram, build_vn_diagrams
from .wingcoefficients import WingAerodynamicsInterpolator


@dataclass
class Model:
    ac: Aircraft
    geom: WingGeometry
    aero: WingAerodynamicsInterpolator
    tank: FuelTank
    loads: LoadModel
    diagrams: list[VnDiagram]
    cases: list[LoadCase]

    def case_loads(self, designs: list[WingBoxDesign] = ()) -> list[CaseLoads]:
        """Loads of every case on one common grid that contains every design's breakpoints."""
        extra = tuple(sorted({e for d in designs for e in d.eta_breaks()}))
        y = self.loads.grid(extra)
        return [self.loads.build(c, y) for c in self.cases]


def build_model(path: Path | str = DEFAULT_AIRCRAFT) -> Model:
    ac = load_aircraft(path)
    p = ac.planform
    geom = WingGeometry(p, ac.wingbox, Airfoil(p.airfoil_file))
    aero = WingAerodynamicsInterpolator(ac.aero.spanwise_file_0, ac.aero.spanwise_file_10,
                                        b=p.b, S=p.S, taper_ratio=p.taper)
    f = ac.fuel
    tank = FuelTank(geom, f.tank_eta_start, f.tank_eta_end, f.density, f.usable_factor)
    diagrams = build_vn_diagrams(ac)
    cases = build_load_cases(ac, tank, diagrams)
    return Model(ac, geom, aero, tank, LoadModel(ac, geom, aero, tank), diagrams, cases)
