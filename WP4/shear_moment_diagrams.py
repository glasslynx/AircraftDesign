

import numpy as np
import tomllib
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import integrate

from wingcoefficients import WingAerodynamicsInterpolator



# 1. READ THE AIRCRAFT DATA FROM aircraft.toml

folder = Path(__file__).resolve().parent
with open(folder / "aircraft.toml", "rb") as f:
    cfg = tomllib.load(f)

g = 9.80665                                         # [m/s2]

# [planform]
S            = cfg["planform"]["S"]                 # wing area [m2]
b            = cfg["planform"]["b"]                 # span [m]
c_root       = cfg["planform"]["c_root"]            # [m]
c_tip        = cfg["planform"]["c_tip"]             # [m]
dihedral_deg = cfg["planform"]["dihedral_deg"]      # [deg]

# [masses]
MTOM         = cfg["masses"]["MTOM"]                # [kg]
m_wing_total = cfg["masses"]["m_wing_total"]        # both wings [kg]

# [engine]
m_engine     = cfg["engine"]["m_engine"]            # per side, engine + nacelle [kg]
y_engine     = cfg["engine"]["y_engine"]            # [m]

# [main_gear]
if cfg["main_gear"]["include"]:
    m_gear = cfg["main_gear"]["m_total"] / 2        # one leg per side [kg]
else:
    m_gear = 0.0
y_gear       = cfg["main_gear"]["y"]                # [m]

# [fuel]
tank_eta_start = cfg["fuel"]["tank_eta_start"]      # fraction of b/2
tank_eta_end   = cfg["fuel"]["tank_eta_end"]        # fraction of b/2

# [aero] - only the file name is used, the files sit next to this script
file_0  = folder / Path(cfg["aero"]["spanwise_file_0"]).name
file_10 = folder / Path(cfg["aero"]["spanwise_file_10"]).name


half_span    = b / 2
cos_dihedral = np.cos(np.radians(dihedral_deg))
y_tank_start = tank_eta_start * half_span
y_tank_end   = tank_eta_end * half_span



# AERODYNAMIC MODEL (wingcoefficients.py)

wing = WingAerodynamicsInterpolator(file_0, file_10, b=b, S=S, taper_ratio=c_tip / c_root)


def chord(y):
    """Local chord c(y) [m]."""
    return float(wing.chord(y))



#  INERTIAL LOADS 

def wing_weight_per_span(y):
    
    return m_wing_total * g * chord(y) / S


# fuel is spread in proportion to c(y)^2 (the wing-box area scales with c^2)
c2_integral, _ = integrate.quad(lambda y: chord(y) ** 2, y_tank_start, y_tank_end)


def fuel_weight_per_span(y, m_fuel):

    if y < y_tank_start or y > y_tank_end:
        return 0.0
    return (m_fuel / 2) * g * chord(y) ** 2 / c2_integral



# NET LOAD FOR ONE LOAD CASE

def make_load_case(n, rho, V, m_aircraft, m_fuel):
   
    q = 0.5 * rho * V**2                                       
    CL_d = wing.required_CL(n, m_aircraft * g, V, rho)         
    N_prime = wing.normal_force_per_unit_span_func(q, CL_d=CL_d)

    def w(y):
        aero = float(N_prime(y))                             
        weight = wing_weight_per_span(y) + fuel_weight_per_span(y, m_fuel)
        return aero - n * cos_dihedral * weight                

    point_loads = [
        (y_engine, n * cos_dihedral * m_engine * g),
        (y_gear,   n * cos_dihedral * m_gear * g),
    ]
    return w, point_loads, CL_d



#  SHEAR FORCe and moment diagram

def shear_and_moment(w, point_loads, y_values):
   
    S_values = np.zeros(len(y_values))
    M_values = np.zeros(len(y_values))

    for i, y in enumerate(y_values):
        jumps = [p for p in (y_tank_start, y_tank_end) if y < p < half_span]

        S_dist, _ = integrate.quad(w, y, half_span, points=jumps or None, limit=100)
        M_dist, _ = integrate.quad(lambda yy: w(yy) * (yy - y), y, half_span,
                                   points=jumps or None, limit=100)

        S_values[i] = S_dist
        M_values[i] = M_dist
        for y_p, P in point_loads:
            if y_p > y:
                S_values[i] -= P
                M_values[i] -= P * (y_p - y)

    return S_values, M_values



#LOAD CASES 

load_cases = [
    # name,               n,    rho [kg/m3], V [m/s], aircraft mass [kg], fuel mass [kg]
    ("LC-22 , n = 2.5",  2.5,  0.380,       228.3,   MTOM,               2841.0),
    ("LC-23 , n = -1.0", -1.0, 0.380,       228.3,   MTOM,               2841.0),
]

y_values = np.linspace(0, half_span, 101)        # stations from root to tip [m]

y_values = np.sort(np.concatenate([y_values, [y_engine - 1e-6, y_engine + 1e-6,
                                              y_gear - 1e-6, y_gear + 1e-6]]))

fig, axes = plt.subplots(len(load_cases), 2, figsize=(12, 4 * len(load_cases)))

for row, (name, n, rho, V, m_aircraft, m_fuel) in enumerate(load_cases):
    w, point_loads, CL_d = make_load_case(n, rho, V, m_aircraft, m_fuel)
    S_values, M_values = shear_and_moment(w, point_loads, y_values)

    
    lift_half, _ = integrate.quad(lambda y: w(y) + n * cos_dihedral *
                                  (wing_weight_per_span(y) + fuel_weight_per_span(y, m_fuel)),
                                  0, half_span, points=[y_tank_end], limit=100)

    print(f"--- {name} ---")
    print(f"  CL_d = {CL_d:.3f}, alpha = {wing.alpha_from_CL(CL_d):.2f} deg")
    print(f"  lift on half-wing = {lift_half / 1e3:.1f} kN   (n W / 2 = {n * m_aircraft * g / 2 / 1e3:.1f} kN)")
    print(f"  root shear  S(0) = {S_values[0] / 1e3:.1f} kN")
    print(f"  root moment M(0) = {M_values[0] / 1e3:.1f} kN m")
    print(f"  (root reactions on the wing: R_z = {-S_values[0] / 1e3:.1f} kN, M_x = {-M_values[0] / 1e3:.1f} kN m)")

    ax = axes[row, 0]
    ax.plot(y_values, S_values / 1e3)
    ax.set_title(f"Shear force, {name}")
    ax.set_xlabel("y [m]")
    ax.set_ylabel("S [kN]")
    ax.grid(True)

    ax = axes[row, 1]
    ax.plot(y_values, M_values / 1e3)
    ax.set_title(f"Bending moment, {name}")
    ax.set_xlabel("y [m]")
    ax.set_ylabel("M [kN m]")
    ax.grid(True)

plt.tight_layout()
plt.savefig(folder / "shear_moment_diagrams.png", dpi=150)
plt.show()
