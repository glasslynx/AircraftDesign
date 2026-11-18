import numpy as np
import scipy as sp
from scipy import interpolate
from scipy.interpolate import PchipInterpolator
import matplotlib.pyplot as plt


class WingAerodynamicsInterpolator:
    """
    AE2111-I Aerodynamic Interpolation Tool (Sections B.3.1 - B.3.3).
    Allows evaluating spanwise non-dimensional and dimensional properties
    by specifying EITHER a desired lift coefficient (CL_d) OR a desired
    angle of attack (alpha_d in degrees).

    Corrected version (2026-11-18). Same functions and arguments as before, plus:
      1. Lift equilibrium: the Cl distributions at alpha = 0 and 10 deg are scaled so
         that int_0^{b/2} Cl c dy = CL * S/2 exactly (normalise=True). Then
         int L' dy = CL q S/2 = n W/2 for every load case.
      2. Interpolation: monotone PCHIP instead of cubic interp1d with extrapolation.
         The strips are mirrored about y = 0 (smooth root) and Cl, Cd_i = 0 at the
         tip (y = b/2); Cm is held at its last strip value outboard of the last strip.
      3. Compressibility: every function that needs alpha (or converts alpha <-> CL)
         takes an optional Mach number M (default 0 = old behaviour). Prandtl-Glauert:
         CL = (CL0 + CLa*alpha) / beta,  beta = sqrt(1 - M^2).
      4. Strip table: the old reader dropped the 5 outermost strips (y > 11.42 m);
         all 25 strips per half wing are read now.
      5. Induced drag: Cd_i(y) = Cd_i,10(y) * (CL/CL10)^2 (induced drag is quadratic in
         CL; the linear interpolation went negative at negative CL). drag_model="linear"
         restores the reader's linear interpolation.
    """

    def __init__(self, file_a0, file_a10, b=None, S=None, taper_ratio=None, normalise=True,
                 drag_model="quadratic"):
        self.drag_model = drag_model
        self.file_a0 = file_a0
        self.file_a10 = file_a10

        # 1. Extract global wing CL and V_inf from the top of both files
        self.CL_0, self.V_inf_0 = self._read_header_properties(file_a0)
        self.CL_10, self.V_inf_10 = self._read_header_properties(file_a10)
        self.CLa_deg = (self.CL_10 - self.CL_0) / 10.0     # lift slope [1/deg], incompressible

        # 2. Import spanwise table for positive y-coordinates using np.genfromtxt
        data_0 = self._import_spanwise_table(file_a0)
        data_10 = self._import_spanwise_table(file_a10)

        # Store discrete spanwise lists/arrays (Section B.3.1 naming convention)
        self.ylst = data_0[:, 0]      # y(m) - positive spanwise coordinates
        self.Ailst_0 = data_0[:, 2]   # Ai [deg] at alpha = 0 deg
        self.Cdlst_0 = data_0[:, 3]   # Cd_i [-] at alpha = 0 deg
        self.Cllst_0 = data_0[:, 5]   # Cl [-] at alpha = 0 deg
        self.Cmlst_0 = data_0[:, 9]   # Cm_i [-] at alpha = 0 deg
        gamma_0 = data_0[:, 18]       # Circulation gamma [m^2/s] at alpha = 0 deg

        self.Ailst_10 = data_10[:, 2] # Ai [deg] at alpha = 10 deg
        self.Cdlst_10 = data_10[:, 3] # Cd_i [-] at alpha = 10 deg
        self.Cllst_10 = data_10[:, 5] # Cl [-] at alpha = 10 deg
        self.Cmlst_10 = data_10[:, 9] # Cm_i [-] at alpha = 10 deg

        # 3. Reconstruct chord distribution c(y)
        if b is not None and S is not None and taper_ratio is not None:
            self.b = b
            self.S = S
            self.taper_ratio = taper_ratio
            c_root = (2.0 * S) / (b * (1.0 + taper_ratio))
            self.clst = c_root * (1.0 - (1.0 - taper_ratio) * (self.ylst / (b / 2.0)))
            self._c_root, self._c_tip = c_root, taper_ratio * c_root
        else:
            self.clst = (2.0 * gamma_0) / (self.V_inf_0 * self.Cllst_0)
            dy_tip = (self.ylst[-1] - self.ylst[-2]) / 2.0
            self.b = 2.0 * (self.ylst[-1] + dy_tip)
            # straight-tapered fit through the reconstructed chords (exact for a trapezoid)
            k, c0 = np.polyfit(self.ylst, self.clst, 1)
            self._c_root, self._c_tip = c0, c0 + k * self.b / 2.0
            self.S = 0.5 * (self._c_root + self._c_tip) * self.b
            self.taper_ratio = self._c_tip / self._c_root

        # 4. Interpolants: monotone PCHIP, mirrored about the root, zero lift at the tip
        b2 = self.b / 2.0
        self.Cl_0_func = self._pchip(self.Cllst_0, tip_zero=True)
        self.Cd_0_func = self._pchip(self.Cdlst_0, tip_zero=True)
        self.Cm_0_func = self._pchip(self.Cmlst_0, tip_zero=False)
        self.Ai_0_func = self._pchip(self.Ailst_0, tip_zero=False)

        self.Cl_10_func = self._pchip(self.Cllst_10, tip_zero=True)
        self.Cd_10_func = self._pchip(self.Cdlst_10, tip_zero=True)
        self.Cm_10_func = self._pchip(self.Cmlst_10, tip_zero=False)
        self.Ai_10_func = self._pchip(self.Ailst_10, tip_zero=False)

        c_r, c_t = self._c_root, self._c_tip
        self.chord_func = lambda y: c_r - (c_r - c_t) * np.clip(np.abs(np.asarray(y, dtype=float)), 0.0, b2) / b2

        # 5. Lift equilibrium: int_0^{b/2} Cl c dy = CL S/2 at both exports
        y_int = np.linspace(0.0, b2, 4001)
        c_int = self.chord(y_int)
        if normalise:
            self.k_0 = self.CL_0 * self.S / 2.0 / np.trapezoid(self.Cl_0_func(y_int) * c_int, y_int)
            self.k_10 = self.CL_10 * self.S / 2.0 / np.trapezoid(self.Cl_10_func(y_int) * c_int, y_int)
        else:
            self.k_0 = self.k_10 = 1.0

    # =========================================================================
    # Helpers
    # =========================================================================
    def _pchip(self, values, tip_zero):
        """Monotone PCHIP through the strips, mirrored about y = 0. With tip_zero the value
        is forced to 0 at y = b/2; otherwise it is held at the last strip value outboard."""
        y = self.ylst
        yy = np.concatenate([-y[::-1], y])
        vv = np.concatenate([values[::-1], values])
        b2 = self.b / 2.0
        if tip_zero:
            yy = np.concatenate([[-b2], yy, [b2]])
            vv = np.concatenate([[0.0], vv, [0.0]])
            f = PchipInterpolator(yy, vv)
            return lambda q: f(np.clip(np.abs(np.asarray(q, dtype=float)), 0.0, b2))
        f = PchipInterpolator(yy, vv)
        return lambda q: f(np.clip(np.abs(np.asarray(q, dtype=float)), 0.0, y[-1]))

    @staticmethod
    def beta(M=0.0):
        """Prandtl-Glauert factor sqrt(1 - M^2) (1 for M = 0)."""
        if M is None or M <= 0:
            return 1.0
        if M >= 0.95:
            raise ValueError("Prandtl-Glauert is not valid for M >= 0.95")
        return float(np.sqrt(1.0 - M ** 2))

    @staticmethod
    def _read_header_properties(filepath):
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        V_inf = None
        CL_wing = None
        for i, line in enumerate(lines[:20]):
            if 'VInf(m/s)' in line:
                V_inf = float(lines[i + 1].split()[-1])
            if line.strip().startswith('CL') and 'CD_inviscid' in line:
                CL_wing = float(lines[i + 1].split()[0])
                break

        if CL_wing is None or V_inf is None:
            raise ValueError(f"Could not parse CL or VInf from header of {filepath}")
        return CL_wing, V_inf

    @staticmethod
    def _import_spanwise_table(filepath):
        """Strip table under 'Main wing': every numeric row after the 'y(m) ...' header,
        up to the first blank or text line. (The old skip_footer version cut off the
        5 outermost strips, y > 11.42 m, because the Cp block header sits a few lines
        below the table.)"""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        start = None
        for i, line in enumerate(lines):
            if line.strip() == "Main wing" and i + 1 < len(lines) and lines[i + 1].startswith("y(m)"):
                start = i + 2
                break
        if start is None:
            raise ValueError(f"No 'Main wing' strip table found in {filepath}")
        n_col = len(lines[start - 1].split())
        rows = []
        for line in lines[start:]:
            try:
                vals = [float(t) for t in line.split()]
            except ValueError:
                break
            if len(vals) != n_col:
                break
            rows.append(vals)
        full_table = np.array(rows)
        table = full_table[full_table[:, 0] > 0]
        return table[np.argsort(table[:, 0])]

    # =========================================================================
    # SECTION B.3.3: Flight Condition & Scaling Helpers (CL_d <-> alpha_d)
    # =========================================================================

    def _resolve_scaling_factor(self, CL_d=None, alpha_d=None, M=0.0):
        """
        Resolves the linear interpolation factor (CL_d - CL0)/(CL10 - CL0)
        from either CL_d or alpha_d [deg]. Raises an error if neither or both are given.
        With alpha_d and a Mach number, alpha_d is first converted to CL_d (Prandtl-Glauert).
        """
        if (CL_d is None) == (alpha_d is None):
            raise ValueError("Specify exactly one of 'CL_d' or 'alpha_d' (in degrees).")
        if alpha_d is not None:
            CL_d = self.CL_from_alpha(alpha_d, M=M)
        return (CL_d - self.CL_0) / (self.CL_10 - self.CL_0)

    def CL_from_alpha(self, alpha_d, M=0.0):
        """Returns the total wing lift coefficient CL_d [-] for a given angle of attack alpha_d [deg]."""
        return (self.CL_0 + self.CLa_deg * alpha_d) / self.beta(M)

    def alpha_from_CL(self, CL_d, degrees=True, M=0.0):
        """Returns the angle of attack alpha_d [deg] or [rad] for a desired wing lift coefficient CL_d.
        M > 0 applies Prandtl-Glauert: alpha = (CL_d*beta - CL0) / CLa."""
        alpha_deg = (CL_d * self.beta(M) - self.CL_0) / self.CLa_deg
        return alpha_deg if degrees else np.radians(alpha_deg)

    def required_CL(self, n, W, V, rho, S=None):
        """Computes required wing lift coefficient CL_d from flight load case parameters.
        Use V = V_EAS with rho = 1.225, or V = V_TAS with the local density."""
        S_wing = S if S is not None else self.S
        q = 0.5 * rho * V**2
        return (n * W) / (q * S_wing)

    # =========================================================================
    # SECTION B.3.3: Non-Dimensional Spanwise Properties
    # =========================================================================

    def chord(self, y):
        """Returns local chord length c(y) [m]."""
        return self.chord_func(y)

    def CL_d(self, y, CL_d=None, alpha_d=None, M=0.0):
        """Returns local lift coefficient CL_d(y) [-] at y for given CL_d or alpha_d [deg]."""
        factor = self._resolve_scaling_factor(CL_d=CL_d, alpha_d=alpha_d, M=M)
        cl0 = self.k_0 * self.Cl_0_func(y)
        cl10 = self.k_10 * self.Cl_10_func(y)
        return cl0 + factor * (cl10 - cl0)

    def CD_d(self, y, CL_d=None, alpha_d=None, M=0.0):
        """Returns local induced drag coefficient CD_d(y) [-] at y for given CL_d or alpha_d [deg]."""
        factor = self._resolve_scaling_factor(CL_d=CL_d, alpha_d=alpha_d, M=M)
        if self.drag_model == "quadratic":
            CL = self.CL_0 + factor * (self.CL_10 - self.CL_0)
            return self.Cd_10_func(y) * (CL / self.CL_10) ** 2
        return self.Cd_0_func(y) + factor * (self.Cd_10_func(y) - self.Cd_0_func(y))

    def CM_d(self, y, CL_d=None, alpha_d=None, M=0.0):
        """Returns local pitching moment coefficient CM_d(y) [-] (about c/4) for given CL_d or alpha_d [deg]."""
        factor = self._resolve_scaling_factor(CL_d=CL_d, alpha_d=alpha_d, M=M)
        return self.Cm_0_func(y) + factor * (self.Cm_10_func(y) - self.Cm_0_func(y))

    # =========================================================================
    # SECTION B.3.2: Dimensional Distributions [N/m] and [N*m/m]
    # =========================================================================

    def lift_per_unit_span(self, y, q, CL_d=None, alpha_d=None, M=0.0):
        """Returns dimensional lift distribution L'(y) = CL_d(y) * q * c(y) [N/m]."""
        return self.CL_d(y, CL_d=CL_d, alpha_d=alpha_d, M=M) * q * self.chord(y)

    def drag_per_unit_span(self, y, q, CL_d=None, alpha_d=None, M=0.0):
        """Returns dimensional drag distribution D'(y) = CD_d(y) * q * c(y) [N/m]."""
        return self.CD_d(y, CL_d=CL_d, alpha_d=alpha_d, M=M) * q * self.chord(y)

    def moment_per_unit_span(self, y, q, CL_d=None, alpha_d=None, M=0.0):
        """Returns dimensional pitching moment distribution M'(y) = CM_d(y) * q * c(y)^2 [N*m/m]."""
        return self.CM_d(y, CL_d=CL_d, alpha_d=alpha_d, M=M) * q * (self.chord(y) ** 2)

    def normal_force_per_unit_span(self, y, q, CL_d=None, alpha_d=None, M=0.0):
        """Transforms L'(y) and D'(y) into normal force per unit span N'(y) [N/m].
        Pass the load case's Mach number M so that alpha includes Prandtl-Glauert."""
        if alpha_d is not None:
            alpha_rad = np.radians(alpha_d)
        else:
            alpha_rad = self.alpha_from_CL(CL_d, degrees=False, M=M)

        L_prime = self.lift_per_unit_span(y, q, CL_d=CL_d, alpha_d=alpha_d, M=M)
        D_prime = self.drag_per_unit_span(y, q, CL_d=CL_d, alpha_d=alpha_d, M=M)
        return L_prime * np.cos(alpha_rad) + D_prime * np.sin(alpha_rad)

# =========================================================================
    # SECTION B.3.2: Callable Distribution Functions f(y) [N/m] and [N*m/m]
    # =========================================================================

    def lift_per_unit_span_func(self, q, CL_d=None, alpha_d=None, M=0.0):
        """Returns a callable function L'(y) = CL_d(y) * q * c(y) [N/m]."""
        # Validate CL_d / alpha_d immediately when creating the function
        self._resolve_scaling_factor(CL_d=CL_d, alpha_d=alpha_d, M=M)
        return lambda y: self.lift_per_unit_span(y, q, CL_d=CL_d, alpha_d=alpha_d, M=M)

    def drag_per_unit_span_func(self, q, CL_d=None, alpha_d=None, M=0.0):
        """Returns a callable function D'(y) = CD_d(y) * q * c(y) [N/m]."""
        self._resolve_scaling_factor(CL_d=CL_d, alpha_d=alpha_d, M=M)
        return lambda y: self.drag_per_unit_span(y, q, CL_d=CL_d, alpha_d=alpha_d, M=M)

    def moment_per_unit_span_func(self, q, CL_d=None, alpha_d=None, M=0.0):
        """Returns a callable function M'(y) = CM_d(y) * q * c(y)^2 [N*m/m]."""
        self._resolve_scaling_factor(CL_d=CL_d, alpha_d=alpha_d, M=M)
        return lambda y: self.moment_per_unit_span(y, q, CL_d=CL_d, alpha_d=alpha_d, M=M)

    def normal_force_per_unit_span_func(self, q, CL_d=None, alpha_d=None, M=0.0):
        """Returns a callable function N'(y) [N/m] transforming L'(y) and D'(y) by alpha_d."""
        self._resolve_scaling_factor(CL_d=CL_d, alpha_d=alpha_d, M=M)
        return lambda y: self.normal_force_per_unit_span(y, q, CL_d=CL_d, alpha_d=alpha_d, M=M)

# =============================================================================
# EXAMPLE USAGE & VERIFICATION PLOTS
# =============================================================================

if __name__ == "__main__":
    from pathlib import Path

    # Always look in the same folder where wingcoefficients.py is saved
    script_dir = Path(__file__).resolve().parent

    # Handle both possible spellings (with or without space after NASA)
    file_0 = script_dir / "Final_Wing-(NASASC(2)-0612)_a=0.00_v=10.00ms.txt"
    file_10 = script_dir / "Final_Wing-(NASASC(2)-0612)_a=10.00_v=10.00ms.txt"

    if not file_0.exists():
        file_0 = script_dir / "Final_Wing-(NASA SC(2)-0612)_a=0.00_v=10.00ms.txt"
        file_10 = script_dir / "Final_Wing-(NASA SC(2)-0612)_a=10.00_v=10.00ms.txt"

    # Final WP3 wing (W/S 5,046, AR 10.6): b 25.47 m, S 61.20 m^2, taper 0.316
    wing = WingAerodynamicsInterpolator(file_0, file_10, b=25.47, S=61.20, taper_ratio=0.316)

    # Set your desired angle of attack directly as a parameter (in degrees)
    alpha_target = 4.0   # [deg]
    y_eval = 5.0         # [m]
    q_example = 12000.0  # [Pa]
    CL_equiv = wing.CL_from_alpha(alpha_target)

    print(f"--- Sample Evaluation at alpha = {alpha_target} deg (CL_d = {CL_equiv:.4f}), y = {y_eval} m ---")
    print(f"  Local Chord c(y)       = {wing.chord(y_eval):.4f} m")
    print(f"  Local CL_d(y)          = {wing.CL_d(y_eval, alpha_d=alpha_target):.4f} [-]")
    print(f"  Local CD_d(y)          = {wing.CD_d(y_eval, alpha_d=alpha_target):.5f} [-]")
    print(f"  Local CM_d(y)          = {wing.CM_d(y_eval, alpha_d=alpha_target):.4f} [-]")
    print(f"  Lift L'(y)             = {wing.lift_per_unit_span(y_eval, q_example, alpha_d=alpha_target):.2f} N/m")
    print(f"  Drag D'(y)             = {wing.drag_per_unit_span(y_eval, q_example, alpha_d=alpha_target):.2f} N/m")
    print(f"  Moment M'(y)           = {wing.moment_per_unit_span(y_eval, q_example, alpha_d=alpha_target):.2f} N*m/m")

    # Checks of the three corrections
    y_fine = np.linspace(0, wing.b / 2, 4001)
    print("\n--- Checks ---")
    print(f"  normalisation factors k_0 / k_10   = {wing.k_0:.4f} / {wing.k_10:.4f}")
    for CL in (0.5, 1.0, 1.852):
        L = wing.lift_per_unit_span(y_fine, 1.0, CL_d=CL)
        print(f"  CL = {CL:5.3f}: int L' dy / (CL q S/2) = {np.trapezoid(L, y_fine) / (CL * wing.S / 2):.5f}")
    print(f"  Cl at the tip (alpha 10)           = {float(wing.CL_d(wing.b / 2, alpha_d=10)):.4f}")
    print(f"  alpha for CL 1.071: M 0 -> {wing.alpha_from_CL(1.071):.2f} deg, "
          f"M 0.84 -> {wing.alpha_from_CL(1.071, M=0.84):.2f} deg")

    # Plot verification parameterized by alpha_target
    y_fine = np.linspace(0, wing.b / 2, 200)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    axes[0].plot(y_fine, wing.CL_d(y_fine, alpha_d=alpha_target), 'g-', lw=2)
    axes[0].set_title(rf'Local Lift Coefficient $CL_d(y)$ at $\alpha = {alpha_target}^\circ$')
    axes[0].set_xlabel(r'$y$ [m]')
    axes[0].grid(True)

    axes[1].plot(y_fine, wing.CD_d(y_fine, alpha_d=alpha_target), 'r-', lw=2)
    axes[1].set_title(rf'Local Drag Coefficient $CD_d(y)$ at $\alpha = {alpha_target}^\circ$')
    axes[1].set_xlabel(r'$y$ [m]')
    axes[1].grid(True)

    axes[2].plot(y_fine, wing.CM_d(y_fine, alpha_d=alpha_target), 'b-', lw=2)
    axes[2].set_title(rf'Local Moment Coefficient $CM_d(y)$ at $\alpha = {alpha_target}^\circ$')
    axes[2].set_xlabel(r'$y$ [m]')
    axes[2].grid(True)

    plt.tight_layout()
    plt.show()
