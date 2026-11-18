"""Input handling: reads the TOML input files into typed, immutable dataclasses.

Nothing in the analysis modules is hard-coded; every aircraft number arrives
through these objects (reader sec. WP4.2: "always pass them as arguments").
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

WP4_DIR = Path(__file__).resolve().parent.parent
DEFAULT_AIRCRAFT = WP4_DIR / "config" / "aircraft.toml"
DEFAULT_DESIGNS = WP4_DIR / "config" / "designs.toml"
G0 = 9.80665  # [m/s2]


def _path(p: str) -> Path:
    return (WP4_DIR / p).resolve()


def _opt_path(p: str | None) -> Path | None:
    """Optional input file: an empty string means 'not supplied'."""
    return _path(p) if p else None


@dataclass(frozen=True)
class Planform:
    S: float
    b: float
    c_root: float
    c_tip: float
    sweep_c4_deg: float
    sweep_LE_deg: float
    dihedral_deg: float
    t_c: float
    airfoil_file: Path
    y_root: float = 0.0

    @property
    def half_span(self) -> float:
        return 0.5 * self.b

    @property
    def taper(self) -> float:
        return self.c_tip / self.c_root


@dataclass(frozen=True)
class WingBoxLayout:
    x_front_spar: float
    x_rear_spar: float


@dataclass(frozen=True)
class Material:
    name: str
    E: float
    G: float
    nu: float
    rho: float
    sigma_y: float
    sigma_u: float


@dataclass(frozen=True)
class Masses:
    MTOM: float
    OEM: float
    payload_max: float
    payload_des: float
    MLM_fraction: float
    m_wing_total: float
    x_wing_cg_frac: float


@dataclass(frozen=True)
class Engine:
    n_engines: int
    m_engine: float
    y_engine: float
    x_cg_rel_LEMAC: float          # engine CG x relative to LEMAC (+ aft) [m]
    z_thrust_below: float
    T0_per_engine: float
    thrust_lapse_exp: float
    thrust_mode: str


@dataclass(frozen=True)
class MainGear:
    include: bool
    m_total: float       # both main gear legs [kg]
    y: float             # lateral position [m]
    x_rel_LEMAC: float   # CG x relative to LEMAC (+ aft) [m]

    @property
    def m_per_side(self) -> float:
        return self.m_total / 2


@dataclass(frozen=True)
class FuelSettings:
    stl_file: Path | None          # None -> analytic wing box (A11 addition)
    density: float
    usable_factor: float
    fill_strategy: str
    tank_eta_start: float = 0.0    # analytic box only
    tank_eta_end: float = 0.85     # analytic box only


@dataclass(frozen=True)
class AeroSettings:
    spanwise_file_0: Path          # flow5 strip export at alpha = 0 deg (reader App. B)
    spanwise_file_10: Path         # flow5 strip export at alpha = 10 deg
    polar_file: Path | None        # optional, plot only
    prandtl_glauert: bool
    cm_prandtl_glauert: bool = False


@dataclass(frozen=True)
class VnSettings:
    CL_max_clean: float
    CL_max_TO: float
    CL_max_land: float
    CN_min: float
    V_C_EAS: float
    M_C: float
    dM_dive: float
    VD_VC_ratio: float
    n_flaps_max: float
    altitudes_m: tuple[float, ...]
    safety_factor: float


@dataclass(frozen=True)
class Requirements:
    tip_deflection_frac_span: float
    tip_twist_deg: float
    stiffness_at_ultimate: bool
    strength_check: bool
    k_shear: float


@dataclass(frozen=True)
class Numerics:
    n_stations: int
    n_stations_opt: int


@dataclass(frozen=True)
class Aircraft:
    """Complete, validated input set for one aircraft."""
    planform: Planform
    wingbox: WingBoxLayout
    material: Material
    masses: Masses
    engine: Engine
    gear: MainGear
    fuel: FuelSettings
    aero: AeroSettings
    vn: VnSettings
    req: Requirements
    numerics: Numerics
    source: Path = field(default=DEFAULT_AIRCRAFT)

    def validate(self) -> None:
        p, wb = self.planform, self.wingbox
        if not (0 < wb.x_front_spar < wb.x_rear_spar < 1):
            raise ValueError("spar positions must satisfy 0 < x_front < x_rear < 1")
        if not (0 < p.y_root < p.half_span or p.y_root == 0):
            raise ValueError("y_root must lie in [0, b/2)")
        if not 0 < self.engine.y_engine < p.half_span:
            raise ValueError("engine must be on the half wing")
        if self.fuel.fill_strategy not in {"uniform", "inboard_first", "outboard_first"}:
            raise ValueError(f"unknown fill_strategy {self.fuel.fill_strategy!r}")
        if self.engine.thrust_mode not in {"max_lapsed", "zero"}:
            raise ValueError(f"unknown thrust_mode {self.engine.thrust_mode!r}")
        if not 0 <= self.fuel.tank_eta_start < self.fuel.tank_eta_end <= 1:
            raise ValueError("tank_eta_start/end must satisfy 0 <= start < end <= 1")
        for f in (p.airfoil_file, self.fuel.stl_file, self.aero.spanwise_file_0,
                  self.aero.spanwise_file_10, self.aero.polar_file):
            if f is not None and not f.exists():
                raise FileNotFoundError(f)


def load_aircraft(path: Path | str = DEFAULT_AIRCRAFT) -> Aircraft:
    path = Path(path)
    with open(path, "rb") as fh:
        d = tomllib.load(fh)
    pl = dict(d["planform"])
    pl["airfoil_file"] = _path(pl["airfoil_file"])
    fu = dict(d["fuel"])
    fu["stl_file"] = _opt_path(fu.get("stl_file", ""))
    ae = dict(d["aero"])
    ae["spanwise_file_0"] = _path(ae["spanwise_file_0"])
    ae["spanwise_file_10"] = _path(ae["spanwise_file_10"])
    ae["polar_file"] = _opt_path(ae.get("polar_file", ""))
    vn = dict(d["vn"])
    vn["altitudes_m"] = tuple(vn["altitudes_m"])
    ac = Aircraft(
        planform=Planform(**pl),
        wingbox=WingBoxLayout(**d["wingbox"]),
        material=Material(**d["material"]),
        masses=Masses(**d["masses"]),
        engine=Engine(**d["engine"]),
        gear=MainGear(**d["main_gear"]),
        fuel=FuelSettings(**fu),
        aero=AeroSettings(**ae),
        vn=VnSettings(**vn),
        req=Requirements(**d["requirements"]),
        numerics=Numerics(**d["numerics"]),
        source=path,
    )
    ac.validate()
    return ac


def load_designs(path: Path | str = DEFAULT_DESIGNS) -> dict:
    with open(path, "rb") as fh:
        return tomllib.load(fh)
