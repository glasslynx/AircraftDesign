"""Wing-box design description (WP4.3 design options), read from config/designs.toml.

A design is chosen BY HAND (no optimiser in WP4): the layout (spars, stringers) follows
the design philosophy, and the thicknesses / areas are picked and then verified against
the requirements with the WP4.1 and WP4.2 tools (run_wp4.py).

Every sizing quantity is a spanwise distribution given at breakpoints eta = y / (b/2):
    linear   : linear interpolation between breakpoints (thicknesses, areas)
    previous : step function, the value holds until the next breakpoint (stringer counts)
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import DEFAULT_DESIGNS

MM, MM2 = 1e-3, 1e-6


@dataclass(frozen=True)
class SpanwiseVar:
    """Value defined at breakpoints eta = y/(b/2), linear or stepwise in between."""
    eta: tuple[float, ...]
    val: tuple[float, ...]
    kind: str = "linear"          # "linear" | "previous"

    def __call__(self, eta) -> np.ndarray:
        eta = np.asarray(eta, dtype=float)
        e, v = np.asarray(self.eta), np.asarray(self.val)
        if self.kind == "linear":
            return np.interp(eta, e, v)
        idx = np.clip(np.searchsorted(e, eta + 1e-9, side="right") - 1, 0, len(v) - 1)  # a station on a break takes the outboard value
        return v[idx]

    @property
    def breaks(self) -> tuple[float, ...]:
        """Breakpoints where a stepwise variable jumps (interior only)."""
        return tuple(e for e in self.eta[1:]) if self.kind == "previous" else ()

    def scaled(self, k: float) -> "SpanwiseVar":
        return SpanwiseVar(self.eta, tuple(k * x for x in self.val), self.kind)

    @staticmethod
    def const(v: float) -> "SpanwiseVar":
        return SpanwiseVar((0.0, 1.0), (v, v))


@dataclass(frozen=True)
class MidSpar:
    x_c: float            # chord position of the extra spar
    eta_end: float        # it ends (at a reinforced rib) at this eta
    t: SpanwiseVar        # web thickness [m]


@dataclass(frozen=True)
class WingBoxDesign:
    name: str
    label: str
    philosophy: str
    t_skin_top: SpanwiseVar       # [m]
    t_skin_bot: SpanwiseVar       # [m]
    t_front_spar: SpanwiseVar     # [m]
    t_rear_spar: SpanwiseVar      # [m]
    n_str_top: SpanwiseVar        # stringers on the top skin [-], stepwise
    n_str_bot: SpanwiseVar        # stringers on the bottom skin [-], stepwise
    A_str_top: SpanwiseVar        # area of ONE top stringer [m2]
    A_str_bot: SpanwiseVar        # area of ONE bottom stringer [m2]
    A_cap: SpanwiseVar            # area of EACH of the 4 corner spar caps [m2]
    mid_spar: MidSpar | None = None

    def eta_breaks(self) -> tuple[float, ...]:
        """Spanwise stations where a property jumps (stringer count steps, mid-spar end)."""
        b = set(self.n_str_top.breaks) | set(self.n_str_bot.breaks)
        if self.mid_spar is not None:
            b.add(self.mid_spar.eta_end)
        return tuple(sorted(x for x in b if 0 < x < 1))


def _var(d: dict, scale: float, kind: str) -> SpanwiseVar:
    if isinstance(d, (int, float)):
        return SpanwiseVar.const(float(d) * scale)
    return SpanwiseVar(tuple(float(e) for e in d["eta"]), tuple(float(v) * scale for v in d["val"]),
                       d.get("kind", kind))


def design_from_dict(d: dict) -> WingBoxDesign:
    """Build a design from one [[design]] table. Bottom values default to the top values,
    the rear spar to the front spar, the mid spar web to the front spar."""
    t_top = _var(d["t_skin_top_mm"], MM, "linear")
    t_fs = _var(d["t_front_spar_mm"], MM, "linear")
    n_top = _var(d["n_stringers_top"], 1.0, "previous")
    A_top = _var(d["A_stringer_top_mm2"], MM2, "linear")
    ms = None
    if "mid_spar" in d:
        m = d["mid_spar"]
        ms = MidSpar(float(m["x_c"]), float(m["eta_end"]),
                     _var(m["t_mm"], MM, "linear") if "t_mm" in m else t_fs)
    return WingBoxDesign(
        name=d["name"], label=d.get("label", d["name"]), philosophy=" ".join(d.get("philosophy", "").split()),
        t_skin_top=t_top,
        t_skin_bot=_var(d["t_skin_bottom_mm"], MM, "linear") if "t_skin_bottom_mm" in d else t_top,
        t_front_spar=t_fs,
        t_rear_spar=_var(d["t_rear_spar_mm"], MM, "linear") if "t_rear_spar_mm" in d else t_fs,
        n_str_top=n_top,
        n_str_bot=_var(d["n_stringers_bottom"], 1.0, "previous") if "n_stringers_bottom" in d else n_top,
        A_str_top=A_top,
        A_str_bot=_var(d["A_stringer_bottom_mm2"], MM2, "linear") if "A_stringer_bottom_mm2" in d else A_top,
        A_cap=_var(d.get("A_cap_mm2", 0.0), MM2, "linear"),
        mid_spar=ms,
    )


def load_designs(path: Path | str = DEFAULT_DESIGNS) -> list[WingBoxDesign]:
    with open(path, "rb") as fh:
        d = tomllib.load(fh)
    return [design_from_dict(x) for x in d["design"]]
