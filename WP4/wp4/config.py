"""Input handling: reads config/aircraft.toml and config/designs.toml into typed objects.

No aircraft number is hard-coded in the analysis modules; every value arrives through
these objects (reader WP4.2: "avoid hard-coding these variables and always pass them as
arguments to a function").
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

WP4_DIR = Path(__file__).resolve().parent.parent      # the WP4 folder (contains run_wp4.py)
DEFAULT_AIRCRAFT = WP4_DIR / "config" / "aircraft.toml"
DEFAULT_DESIGNS = WP4_DIR / "config" / "designs.toml"
G0 = 9.80665  # [m/s2]


def _path(p: str) -> Path:
    return (WP4_DIR / p).resolve()


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
    follow_camber: bool = False


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
    x_cg_rel_LEMAC: float
    z_thrust_below: float
    T0_per_engine: float
    thrust_lapse_exp: float
    thrust_mode: str


@dataclass(frozen=True)
class MainGear:
    include: bool
    m_total: float
    y: float
    x_rel_LEMAC: float

    @property
    def m_per_side(self) -> float:
        return self.m_total / 2


@dataclass(frozen=True)
class FuelSettings:
    tank_eta_start: float
    tank_eta_end: float
    density: float
    usable_factor: float


@dataclass(frozen=True)
class AeroSettings:
    spanwise_file_0: Path
    spanwise_file_10: Path
    prandtl_glauert: bool = True


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
class LoadSettings:
    dihedral_on_inertia: bool = False


@dataclass(frozen=True)
class Numerics:
    n_stations: int = 401
    deflection_method: str = "quad"


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
    loads: LoadSettings
    numerics: Numerics
    source: Path = field(default=DEFAULT_AIRCRAFT)

    def validate(self) -> None:
        p, wb = self.planform, self.wingbox
        if not (0 < wb.x_front_spar < wb.x_rear_spar < 1):
            raise ValueError("spar positions must satisfy 0 < x_front < x_rear < 1")
        if not 0 <= p.y_root < p.half_span:
            raise ValueError("y_root must lie in [0, b/2)")
        if not 0 < self.engine.y_engine < p.half_span:
            raise ValueError("engine must be on the half wing")
        if self.engine.thrust_mode not in {"max_lapsed", "zero"}:
            raise ValueError(f"unknown thrust_mode {self.engine.thrust_mode!r}")
        if not 0 <= self.fuel.tank_eta_start < self.fuel.tank_eta_end <= 1:
            raise ValueError("tank_eta_start/end must satisfy 0 <= start < end <= 1")
        if self.numerics.deflection_method not in {"quad", "trapezoid"}:
            raise ValueError("deflection_method must be 'quad' or 'trapezoid'")
        for f in (p.airfoil_file, self.aero.spanwise_file_0, self.aero.spanwise_file_10):
            if not f.exists():
                raise FileNotFoundError(f)


def load_aircraft(path: Path | str = DEFAULT_AIRCRAFT) -> Aircraft:
    path = Path(path)
    with open(path, "rb") as fh:
        d = tomllib.load(fh)
    pl = dict(d["planform"])
    pl["airfoil_file"] = _path(pl["airfoil_file"])
    ae = dict(d["aero"])
    ae["spanwise_file_0"] = _path(ae["spanwise_file_0"])
    ae["spanwise_file_10"] = _path(ae["spanwise_file_10"])
    vn = dict(d["vn"])
    vn["altitudes_m"] = tuple(vn["altitudes_m"])
    ac = Aircraft(
        planform=Planform(**pl),
        wingbox=WingBoxLayout(**d["wingbox"]),
        material=Material(**d["material"]),
        masses=Masses(**d["masses"]),
        engine=Engine(**d["engine"]),
        gear=MainGear(**d["main_gear"]),
        fuel=FuelSettings(**d["fuel"]),
        aero=AeroSettings(**ae),
        vn=VnSettings(**vn),
        req=Requirements(**d["requirements"]),
        loads=LoadSettings(**d.get("loads", {})),
        numerics=Numerics(**d.get("numerics", {})),
        source=path,
    )
    ac.validate()
    return ac
