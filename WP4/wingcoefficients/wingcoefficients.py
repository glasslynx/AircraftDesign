import numpy as np
import scipy as sp
from scipy import interpolate
import matplotlib.pyplot as plt


class WingAerodynamicsInterpolator:
    """
    AE2111-I Aerodynamic Interpolation Tool (Sections B.3.1 - B.3.3).
    Allows evaluating spanwise non-dimensional and dimensional properties
    by specifying EITHER a desired lift coefficient (CL_d) OR a desired
    angle of attack (alpha_d in degrees).
    """

    def __init__(self, file_a0, file_a10, b=None, S=None, taper_ratio=None):
        self.file_a0 = file_a0
        self.file_a10 = file_a10

        # 1. Extract global wing CL and V_inf from the top of both files
        self.CL_0, self.V_inf_0 = self._read_header_properties(file_a0)
        self.CL_10, self.V_inf_10 = self._read_header_properties(file_a10)

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
        else:
            self.clst = (2.0 * gamma_0) / (self.V_inf_0 * self.Cllst_0)
            dy_tip = (self.ylst[-1] - self.ylst[-2]) / 2.0
            self.b = 2.0 * (self.ylst[-1] + dy_tip)

        # 4. Construct SciPy Cubic Spline Interpolants (Section B.3.1)
        self.Cl_0_func = sp.interpolate.interp1d(
            self.ylst, self.Cllst_0, kind='cubic', fill_value="extrapolate"
        )
        self.Cd_0_func = sp.interpolate.interp1d(
            self.ylst, self.Cdlst_0, kind='cubic', fill_value="extrapolate"
        )
        self.Cm_0_func = sp.interpolate.interp1d(
            self.ylst, self.Cmlst_0, kind='cubic', fill_value="extrapolate"
        )
        self.Ai_0_func = sp.interpolate.interp1d(
            self.ylst, self.Ailst_0, kind='cubic', fill_value="extrapolate"
        )

        self.Cl_10_func = sp.interpolate.interp1d(
            self.ylst, self.Cllst_10, kind='cubic', fill_value="extrapolate"
        )
        self.Cd_10_func = sp.interpolate.interp1d(
            self.ylst, self.Cdlst_10, kind='cubic', fill_value="extrapolate"
        )
        self.Cm_10_func = sp.interpolate.interp1d(
            self.ylst, self.Cmlst_10, kind='cubic', fill_value="extrapolate"
        )
        self.Ai_10_func = sp.interpolate.interp1d(
            self.ylst, self.Ailst_10, kind='cubic', fill_value="extrapolate"
        )

        self.chord_func = sp.interpolate.interp1d(
            self.ylst, self.clst, kind='linear', fill_value="extrapolate"
        )

        if S is None:
            c_r = float(self.chord_func(0.0))
            c_t = float(self.chord_func(self.b / 2.0))
            self.S = 0.5 * (c_r + c_t) * self.b
            self.taper_ratio = c_t / c_r

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
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        total_lines = len(lines)
        start_idx = None
        end_idx = None

        for i, line in enumerate(lines):
            if line.strip() == "Main wing":
                start_idx = i + 2
            elif "Main wing - Cp Coefficients" in line and start_idx is not None:
                end_idx = i - 2
                break

        full_table = np.genfromtxt(
            filepath,
            skip_header=start_idx,
            skip_footer=total_lines - end_idx
        )
        return full_table[full_table[:, 0] > 0]

    # =========================================================================
    # SECTION B.3.3: Flight Condition & Scaling Helpers (CL_d <-> alpha_d)
    # =========================================================================

    def _resolve_scaling_factor(self, CL_d=None, alpha_d=None):
        """
        Resolves the linear interpolation factor (0 at alpha=0 deg, 1 at alpha=10 deg)
        from either CL_d or alpha_d [deg]. Raises an error if neither or both are given.
        """
        if (CL_d is None) == (alpha_d is None):
            raise ValueError("Specify exactly one of 'CL_d' or 'alpha_d' (in degrees).")
        if alpha_d is not None:
            return alpha_d / 10.0
        return (CL_d - self.CL_0) / (self.CL_10 - self.CL_0)

    def CL_from_alpha(self, alpha_d):
        """Returns the total wing lift coefficient CL_d [-] for a given angle of attack alpha_d [deg]."""
        return self.CL_0 + (alpha_d / 10.0) * (self.CL_10 - self.CL_0)

    def alpha_from_CL(self, CL_d, degrees=True):
        """Returns the angle of attack alpha_d [deg] or [rad] for a desired wing lift coefficient CL_d."""
        alpha_deg = ((CL_d - self.CL_0) / (self.CL_10 - self.CL_0)) * 10.0
        return alpha_deg if degrees else np.radians(alpha_deg)

    def required_CL(self, n, W, V, rho, S=None):
        """Computes required wing lift coefficient CL_d from flight load case parameters."""
        S_wing = S if S is not None else self.S
        q = 0.5 * rho * V**2
        return (n * W) / (q * S_wing)

    # =========================================================================
    # SECTION B.3.3: Non-Dimensional Spanwise Properties
    # =========================================================================

    def chord(self, y):
        """Returns local chord length c(y) [m]."""
        return self.chord_func(y)

    def CL_d(self, y, CL_d=None, alpha_d=None):
        """Returns local lift coefficient CL_d(y) [-] at y for given CL_d or alpha_d [deg]."""
        factor = self._resolve_scaling_factor(CL_d=CL_d, alpha_d=alpha_d)
        return self.Cl_0_func(y) + factor * (self.Cl_10_func(y) - self.Cl_0_func(y))

    def CD_d(self, y, CL_d=None, alpha_d=None):
        """Returns local induced drag coefficient CD_d(y) [-] at y for given CL_d or alpha_d [deg]."""
        factor = self._resolve_scaling_factor(CL_d=CL_d, alpha_d=alpha_d)
        return self.Cd_0_func(y) + factor * (self.Cd_10_func(y) - self.Cd_0_func(y))

    def CM_d(self, y, CL_d=None, alpha_d=None):
        """Returns local pitching moment coefficient CM_d(y) [-] at y for given CL_d or alpha_d [deg]."""
        factor = self._resolve_scaling_factor(CL_d=CL_d, alpha_d=alpha_d)
        return self.Cm_0_func(y) + factor * (self.Cm_10_func(y) - self.Cm_0_func(y))

    # =========================================================================
    # SECTION B.3.2: Dimensional Distributions [N/m] and [N*m/m]
    # =========================================================================

    def lift_per_unit_span(self, y, q, CL_d=None, alpha_d=None):
        """Returns dimensional lift distribution L'(y) = CL_d(y) * q * c(y) [N/m]."""
        return self.CL_d(y, CL_d=CL_d, alpha_d=alpha_d) * q * self.chord(y)

    def drag_per_unit_span(self, y, q, CL_d=None, alpha_d=None):
        """Returns dimensional drag distribution D'(y) = CD_d(y) * q * c(y) [N/m]."""
        return self.CD_d(y, CL_d=CL_d, alpha_d=alpha_d) * q * self.chord(y)

    def moment_per_unit_span(self, y, q, CL_d=None, alpha_d=None):
        """Returns dimensional pitching moment distribution M'(y) = CM_d(y) * q * c(y)^2 [N*m/m]."""
        return self.CM_d(y, CL_d=CL_d, alpha_d=alpha_d) * q * (self.chord(y) ** 2)

    def normal_force_per_unit_span(self, y, q, CL_d=None, alpha_d=None):
        """Transforms L'(y) and D'(y) into normal force per unit span N'(y) [N/m]."""
        if alpha_d is not None:
            alpha_rad = np.radians(alpha_d)
        else:
            alpha_rad = self.alpha_from_CL(CL_d, degrees=False)

        L_prime = self.lift_per_unit_span(y, q, CL_d=CL_d, alpha_d=alpha_d)
        D_prime = self.drag_per_unit_span(y, q, CL_d=CL_d, alpha_d=alpha_d)
        return L_prime * np.cos(alpha_rad) + D_prime * np.sin(alpha_rad)


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

    wing = WingAerodynamicsInterpolator(file_0, file_10)

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