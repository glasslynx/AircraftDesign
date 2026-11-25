"""International Standard Atmosphere (troposphere + lower stratosphere, h <= 20 km)."""
from __future__ import annotations

import math
from dataclasses import dataclass

T0, P0, RHO0 = 288.15, 101325.0, 1.225
LAPSE, R_AIR, GAMMA, G0 = -0.0065, 287.05287, 1.4, 9.80665
H_TROPO = 11000.0


@dataclass(frozen=True)
class AtmosphereState:
    h: float      # geopotential altitude [m]
    T: float      # [K]
    p: float      # [Pa]
    rho: float    # [kg/m3]
    a: float      # speed of sound [m/s]

    @property
    def sigma(self) -> float:
        return self.rho / RHO0


def isa(h: float) -> AtmosphereState:
    if not 0.0 <= h <= 20000.0:
        raise ValueError("ISA model valid for 0 <= h <= 20 000 m")
    if h <= H_TROPO:
        T = T0 + LAPSE * h
        p = P0 * (T / T0) ** (-G0 / (LAPSE * R_AIR))
    else:
        T11 = T0 + LAPSE * H_TROPO
        p11 = P0 * (T11 / T0) ** (-G0 / (LAPSE * R_AIR))
        T = T11
        p = p11 * math.exp(-G0 * (h - H_TROPO) / (R_AIR * T11))
    rho = p / (R_AIR * T)
    return AtmosphereState(h, T, p, rho, math.sqrt(GAMMA * R_AIR * T))


def eas_to_tas(v_eas: float, h: float) -> float:
    return v_eas / math.sqrt(isa(h).sigma)


def mach_from_eas(v_eas: float, h: float) -> float:
    st = isa(h)
    return v_eas / math.sqrt(st.sigma) / st.a
