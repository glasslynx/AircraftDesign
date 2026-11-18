code_content = r""

import os
import re
import numpy as np
import matplotlib.pyplot as plt
import astropy.units as u


def parse_vn_settings(settings_filepath):
    """
    Parses the 'V-n diagram settings.txt' file and returns a dictionary of parameters.
    Supports lines formatted like:
        OEW  = 19347 [kg]
        compressibility_limited = True
    """
    params = {}
    with open(settings_filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val_part = line.split("=", 1)
            key = key.strip()
            # Remove unit brackets like [kg], [m^2], [-], [1/rad] and inline comments
            val_clean = re.sub(r"\[.*?\]", "", val_part).split("#")[0].strip()
            if val_clean.lower() == "true":
                params[key] = True
            elif val_clean.lower() == "false":
                params[key] = False
            else:
                params[key] = float(val_clean)
    return params


def get_isa_properties(alt, rho_0, g_0):
    """Calculates ISA temperature, density, and speed of sound at altitude."""
    T_0 = 288.15 * u.K
    L_rate = -0.0065 * u.K / u.m
    R_gas = 287.058 * u.J / (u.kg * u.K)
    gamma = 1.4
    if alt <= 11000 * u.m:
        T = T_0 + L_rate * alt
        rho = rho_0 * (T / T_0)**((-g_0 / (L_rate * R_gas)).decompose().value - 1.0)
    else:
        T = 216.65 * u.K
        rho_11 = rho_0 * (216.65 / 288.15)**((-g_0 / (L_rate * R_gas)).decompose().value - 1.0)
        rho = rho_11 * np.exp((-g_0 * (alt - 11000 * u.m) / (R_gas * T)).decompose().value)
    a = np.sqrt(gamma * R_gas * T).to(u.m / u.s)
    return rho.to(u.kg / u.m**3), a.to(u.m / u.s)


def generate_vn_diagrams(settings_filename="V-n diagram settings.txt"):
    """
    Main function that reads input data from 'V-n diagram settings.txt' in the
    script's directory, generates the 6 V-n diagrams inside the 'V-n diagrams'
    subfolder, writes 'V-n diagram output.txt' (only inside 'V-n diagrams' without
    raw NumPy arrays at the bottom), and outputs the NumPy arrays to the terminal.
    """
    # ==========================================================================
    # 0. DIRECTORY & INPUT FILE SETUP
    # ==========================================================================
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    
    if os.path.isabs(settings_filename):
        settings_path = settings_filename
    else:
        settings_path = os.path.join(script_dir, settings_filename)

    output_folder = os.path.join(script_dir, "V-n diagrams")
    os.makedirs(output_folder, exist_ok=True)
    txt_output_path = os.path.join(output_folder, "V-n diagram output.txt")

    # ==========================================================================
    # 1. READ INPUT PARAMETERS FROM TXT FILE (WITH ASTROPY SI UNITS)
    # ==========================================================================
    raw_params = parse_vn_settings(settings_path)

    # Weights
    OEW  = (raw_params["OEW"] * u.kg).to(u.kg)
    MPW  = (raw_params["MPW"] * u.kg).to(u.kg)
    MTOW = (raw_params["MTOW"] * u.kg).to(u.kg)
    MLW  = (raw_params["MLW"] * u.kg).to(u.kg)

    # Altitudes
    h_SL     = (raw_params["h_SL"] * u.m).to(u.m)
    h_cruise = (raw_params["h_cruise"] * u.m).to(u.m)

    # Standard Atmosphere Constants
    g_0   = (9.80665 * u.m / u.s**2).to(u.m / u.s**2)
    rho_0 = (1.225 * u.kg / u.m**3).to(u.kg / u.m**3)

    # Aerodynamic & Flight Parameters
    S               = (raw_params["S"] * u.m**2).to(u.m**2)
    C_L_max_clean   = raw_params["C_L_max_clean"] * u.dimensionless_unscaled
    C_L_max_takeoff = raw_params["C_L_max_takeoff"] * u.dimensionless_unscaled
    C_L_max_landing = raw_params["C_L_max_landing"] * u.dimensionless_unscaled

    V_C = (raw_params["V_C"] * u.m / u.s).to(u.m / u.s)
    M_C = raw_params["M_C"] * u.dimensionless_unscaled
    compressibility_limited = bool(raw_params["compressibility_limited"])
    C_L_alpha_0 = (raw_params["C_L_alpha_0"] / u.rad).to(1 / u.rad)

    # ==========================================================================
    # 2. CONSTANT PARAMETER CALCULATIONS (Independent of active W and h)
    # ==========================================================================
    # Limit Manoeuvring Load Factors based on MTOW (CS25.337)
    W_MTOW_lb = (MTOW / (0.454 * u.kg)).decompose().value
    n_max = np.clip(2.1 + (24000.0 / (W_MTOW_lb + 10000.0)), 2.5, 3.8) * u.dimensionless_unscaled
    n_min = -1.0 * u.dimensionless_unscaled
    n_flaps_max = 2.0 * u.dimensionless_unscaled

    # Design Wing-Flap Speed V_F based on MTOW and MLW (CS25.335(e)(3))
    V_S1_MTOW_TO   = np.sqrt((2.0 * MTOW * g_0) / (rho_0 * S * C_L_max_takeoff)).to(u.m / u.s)
    V_S1_MLW_clean = np.sqrt((2.0 * MLW * g_0) / (rho_0 * S * C_L_max_clean)).to(u.m / u.s)
    V_S0_MLW_land  = np.sqrt((2.0 * MLW * g_0) / (rho_0 * S * C_L_max_landing)).to(u.m / u.s)
    V_F = max(1.6 * V_S1_MTOW_TO, 1.8 * V_S1_MLW_clean, 1.8 * V_S0_MLW_land).to(u.m / u.s)

    # ==========================================================================
    # 3. SETTINGS FOR BATCH GENERATION & DATABASE INITIALIZATION
    # ==========================================================================
    weight_configs = [
        ("OEW", "OEW", OEW),
        ("MZFW (OEW + MPW)", "MZFW", OEW + MPW),
        ("MTOW", "MTOW", MTOW)
    ]

    alt_configs = [
        ("Sea-Level", "SEA_LEVEL", h_SL),
        ("Cruise Altitude (FL350)", "CRUISE_ALT", h_cruise)
    ]

    db_dtype = np.dtype([
        ('case_id', 'U25'),
        ('weight_config', 'U20'),
        ('altitude_config', 'U25'),
        ('W_kg', 'f8'),
        ('h_m', 'f8'),
        ('V_S1_ms', 'f8'),
        ('V_S0_ms', 'f8'),
        ('V_A_ms', 'f8'),
        ('V_C_ms', 'f8'),
        ('V_D_ms', 'f8'),
        ('V_F_ms', 'f8'),
        ('n_max', 'f8'),
        ('n_min', 'f8')
    ])

    database_records = []
    txt_blocks = []

    # ==========================================================================
    # 4. DIAGRAM GENERATION LOOP
    # ==========================================================================
    plot_index = 1
    total_plots = len(weight_configs) * len(alt_configs)

    for w_name, w_tag, W in weight_configs:
        for h_name, h_tag, h in alt_configs:
            case_label = f"{h_tag}-{w_tag}"
            print(f"Generating & Saving Diagram {plot_index}/{total_plots}: {case_label}...")

            # --- Update Atmosphere and Speeds ---
            rho_h, a_h = get_isa_properties(h, rho_0, g_0)

            V_S0 = np.sqrt((2.0 * W * g_0) / (rho_0 * S * C_L_max_landing)).to(u.m / u.s)
            V_S1 = np.sqrt((2.0 * W * g_0) / (rho_0 * S * C_L_max_clean)).to(u.m / u.s)
            V_A  = (V_S1 * np.sqrt(n_max)).to(u.m / u.s)

            V_D_subsonic = (V_C / 0.8).to(u.m / u.s)
            if compressibility_limited and h > 0 * u.m:
                M_D = M_C + 0.05 * u.dimensionless_unscaled
                V_D_mach_TAS = (M_D * a_h).to(u.m / u.s)
                V_D_mach_EAS = (V_D_mach_TAS * np.sqrt(rho_h / rho_0)).to(u.m / u.s)
                V_D = min(V_D_subsonic, V_D_mach_EAS).to(u.m / u.s)
            else:
                V_D = V_D_subsonic

            # --- Store Record for NumPy Database ---
            database_records.append((
                case_label,
                w_name,
                h_name,
                float(W.value),
                float(h.value),
                float(np.round(V_S1.value, 2)),
                float(np.round(V_S0.value, 2)),
                float(np.round(V_A.value, 2)),
                float(np.round(V_C.value, 2)),
                float(np.round(V_D.value, 2)),
                float(np.round(V_F.value, 2)),
                float(np.round(n_max.value, 3)),
                float(np.round(n_min.value, 3))
            ))

            # --- Format Text Block for 'V-n diagram output.txt' ---
            block_str = (
                f"============================================================\n"
                f"CASE {plot_index}: {case_label}\n"
                f"============================================================\n"
                f"DIAGRAM SPECIFICATIONS\n"
                f"------------------------------------------------------------\n"
                f"Weight Config:                 {w_name} [-]\n"
                f"Weight (W):                    {W.value:,.1f} [kg]\n"
                f"Altitude Config:               {h_name} [-]\n"
                f"Altitude (h):                  {h.value:,.1f} [m]\n"
                f"Positive Limit Load (n_max):   {n_max.value:.3f} [-]\n"
                f"Negative Limit Load (n_min):   {n_min.value:.3f} [-]\n"
                f"Flap Max Load (n_flaps_max):   {n_flaps_max.value:.3f} [-]\n\n"
                f"KEY SPEEDS (Equivalent Airspeed - EAS)\n"
                f"------------------------------------------------------------\n"
                f"V_S1 (Stall, Clean):           {V_S1.value:.2f} [m/s]\n"
                f"V_S0 (Stall, Landing):         {V_S0.value:.2f} [m/s]\n"
                f"V_A  (Design Manoeuvre):       {V_A.value:.2f} [m/s]\n"
                f"V_C  (Design Cruise):          {V_C.value:.2f} [m/s]\n"
                f"V_D  (Design Dive):            {V_D.value:.2f} [m/s]\n"
                f"V_F  (Max Flap):               {V_F.value:.2f} [m/s]\n"
            )
            txt_blocks.append(block_str)

            # --- Calculate Line Segments ---
            # Line Segment 1: Positive Stall Curve (Flaps Up, 0 to Point A)
            V_seg_OA = np.linspace(0 * u.m / u.s, V_A, 200)
            n_seg_OA = (V_seg_OA / V_S1).decompose()**2

            # Line Segment 2: Flaps Down Envelope (0 to n = 2.0, then horizontal to V_F or clean curve)
            V_flap_reach_2 = (V_S0 * np.sqrt(n_flaps_max)).to(u.m / u.s)
            V_seg_flap_curve = np.linspace(0 * u.m / u.s, V_flap_reach_2, 100)
            n_seg_flap_curve = (V_seg_flap_curve / V_S0).decompose()**2

            V_clean_at_n2 = (V_S1 * np.sqrt(n_flaps_max)).to(u.m / u.s)
            V_flap_end = min(V_F, V_clean_at_n2)
            V_seg_flap_flat = np.linspace(V_flap_reach_2, V_flap_end, 50)
            n_seg_flap_flat = np.full(V_seg_flap_flat.shape, n_flaps_max.value) * u.dimensionless_unscaled

            # Line Segment 3: Positive Limit Load Factor Line (Point A to Point D)
            V_seg_AD = np.linspace(V_A, V_D, 100)
            n_seg_AD = np.full(V_seg_AD.shape, n_max.value) * u.dimensionless_unscaled

            # Line Segment 4: Dive Speed Vertical Boundary (Point D to V_D at n = 0)
            V_seg_D0 = np.array([V_D.value, V_D.value]) * (u.m / u.s)
            n_seg_D0 = np.array([n_max.value, 0.0]) * u.dimensionless_unscaled

            # Line Segment 5: High-Speed Negative Recovery Line (V_D at n = 0 to Point F at V_C, n = n_min)
            V_seg_FD = np.linspace(V_C, V_D, 100)
            denom = (V_D - V_C).decompose()
            if abs(denom.value) > 1e-9:
                n_seg_FD = n_min * ((V_D - V_seg_FD) / denom).decompose()
            else:
                n_seg_FD = np.linspace(n_min.value, 0.0, 100) * u.dimensionless_unscaled

            # Line Segment 6: Negative Limit Load Factor Line (Point H to Point F)
            V_H = (V_S1 * np.sqrt(abs(n_min))).to(u.m / u.s)
            V_seg_HF = np.linspace(V_H, V_C, 100)
            n_seg_HF = np.full(V_seg_HF.shape, n_min.value) * u.dimensionless_unscaled

            # Line Segment 7: Negative Stall Curve (0 to Point H)
            V_seg_OH = np.linspace(0 * u.m / u.s, V_H, 150)
            n_seg_OH = -((V_seg_OH / V_S1).decompose()**2)

            # --- Plotting ---
            fig, ax = plt.subplots(figsize=(11, 7), dpi=150)

            ax.plot(V_seg_OA.value, n_seg_OA.value, 'k-', lw=2.2, label=r'Clean Stall Curve ($0 \rightarrow A$)')
            ax.plot(V_seg_AD.value, n_seg_AD.value, 'k-', lw=2.2, label=r'Positive Limit ($A \rightarrow D$)')
            ax.plot(V_seg_D0.value, n_seg_D0.value, 'k-', lw=2.2, label=r'Dive Speed Limit ($V_D$)')
            ax.plot(V_seg_FD.value, n_seg_FD.value, 'k-', lw=2.2, label=r'Negative Linear Variation ($F \rightarrow V_D$)')
            ax.plot(V_seg_HF.value, n_seg_HF.value, 'k-', lw=2.2, label=r'Negative Limit ($H \rightarrow F$)')
            ax.plot(V_seg_OH.value, n_seg_OH.value, 'k-', lw=2.2, label=r'Negative Stall Curve ($0 \rightarrow H$)')

            ax.plot(V_seg_flap_curve.value, n_seg_flap_curve.value, 'b--', lw=1.8, label='Flaps Down Envelope')
            ax.plot(V_seg_flap_flat.value, n_seg_flap_flat.value, 'b--', lw=1.8)
            if V_F < V_clean_at_n2:
                n_clean_at_VF = ((V_F / V_S1).decompose()**2).value
                ax.plot([V_F.value, V_F.value], [n_flaps_max.value, n_clean_at_VF], 'b:', lw=1.5)

            ax.axhline(0, color='black', lw=1.0)
            ax.axhline(1, color='gray', ls='--', lw=1.0)
            ax.axhline(-1, color='gray', ls='--', lw=1.0)

            ax.plot([V_S1.value, V_S1.value], [0, 1], 'k--', lw=1.0, alpha=0.5)
            ax.plot([V_A.value, V_A.value], [0, n_max.value], 'k--', lw=1.0, alpha=0.5)
            ax.plot([V_C.value, V_C.value], [n_min.value, n_max.value], 'k--', lw=1.0, alpha=0.5)

            # Annotate Key Points
            ax.scatter([V_A.value, V_D.value, V_C.value, V_H.value],
                        [n_max.value, n_max.value, n_min.value, n_min.value], color='red', zorder=5)
            ax.annotate('A', (V_A.value, n_max.value), xytext=(-10, 8), textcoords='offset points', fontweight='bold')
            ax.annotate('D', (V_D.value, n_max.value), xytext=(6, 8), textcoords='offset points', fontweight='bold')
            ax.annotate('F', (V_C.value, n_min.value), xytext=(6, -15), textcoords='offset points', fontweight='bold')
            ax.annotate('H', (V_H.value, n_min.value), xytext=(-14, -15), textcoords='offset points', fontweight='bold')

            # Add Titles and Labels
            ax.set_title(
                f'$(V_{{EAS}} - n)$ Manoeuvre Loading Diagram [{plot_index}/{total_plots}]\n'
                f'Configuration: {w_name} | Altitude: {h_name}',
                fontsize=14, pad=15, fontweight='bold'
            )

            ax.set_xlabel(r'Equivalent Airspeed $V_{EAS}$ [m/s]', fontsize=11)
            ax.set_ylabel(r'Load Factor $n$ [-]', fontsize=11)

            # Description Box on Plot (Moved slightly to ensure no overlap)
            description_text = (
                f"DIAGRAM SPECIFICATIONS\n"
                f"----------------------------------------\n"
                f"Weight Config:  {w_name}\n"
                f"Weight ($W$):   {W.value:,.0f} kg\n"
                f"Altitude ($h$): {h.value:,.0f} m\n\n"
                f"KEY SPEEDS (EAS)\n"
                f"----------------------------------------\n"
                f"$V_{{S1}}$ (Stall, Clean):    {V_S1.value:.1f} m/s\n"
                f"$V_{{S0}}$ (Stall, Landing):  {V_S0.value:.1f} m/s\n"
                f"$V_A$  (Manoeuvre):      {V_A.value:.1f} m/s\n"
                f"$V_C$  (Design Cruise):  {V_C.value:.1f} m/s\n"
                f"$V_D$  (Design Dive):    {V_D.value:.1f} m/s\n"
                f"$V_F$  (Max Flap):       {V_F.value:.1f} m/s"
            )

            # To avoid the description box hitting the top border, we adjust the coordinates
            ax.text(0.02, 0.95, description_text, transform=ax.transAxes,
                     fontsize=9, va='top', ha='left', family='monospace',
                     bbox=dict(boxstyle='round,pad=0.6', facecolor='whitesmoke', edgecolor='gray', alpha=0.95))

            ax.set_xlim(0, max(V_D.value, V_C.value) * 1.15)
            # Increase top padding slightly so the description box doesn't hit the top spine
            ax.set_ylim(n_min.value - 0.8, n_max.value + 1.2)
            
            # Use bbox_to_anchor to position the legend well below the x-axis
            # Using shrink to give room for legend
            box = ax.get_position()
            ax.set_position([box.x0, box.y0 + box.height * 0.15,
                             box.width, box.height * 0.85])

            ax.grid(True, linestyle=':', alpha=0.6)
            ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=3, fontsize=9)
            
            # Save figure into 'V-n diagrams' folder
            figure_filepath = os.path.join(output_folder, f"{case_label}.png")
            # bbox_inches='tight' will perfectly crop the figure including the newly placed legend
            plt.savefig(figure_filepath, dpi=150, bbox_inches='tight')
            plt.close(fig)

            plot_index += 1

    # ==========================================================================
    # 5. BUILD NUMPY ARRAYS, SAVE TXT FILE (ONLY IN FOLDER) & PRINT TO TERMINAL
    # ==========================================================================
    # 1. Structured NumPy Database Array
    vn_database_structured = np.array(database_records, dtype=db_dtype)

    # 2. Pure Numeric 2D NumPy Array (rows = 6 cases, cols = [W, h, V_S1, V_S0, V_A, V_C, V_D, V_F, n_max, n_min])
    vn_database_numeric = np.array([
        [r['W_kg'], r['h_m'], r['V_S1_ms'], r['V_S0_ms'], r['V_A_ms'], r['V_C_ms'], r['V_D_ms'], r['V_F_ms'], r['n_max'], r['n_min']]
        for r in vn_database_structured
    ])

    # Write formatted output ONLY to 'V-n diagrams/V-n diagram output.txt'
    # (Without the raw NumPy array representations at the bottom)
    header_summary = (
        "====================================================================================================\n"
        "AE2111-I WORK PACKAGE 4.3: V-n MANOEUVRE DIAGRAM SPECIFICATIONS DATABASE\n"
        "====================================================================================================\n"
        "SUMMARY TABLE (SI UNITS):\n"
        f"{'Case ID':<18} | {'W [kg]':>9} | {'h [m]':>8} | {'V_S1 [m/s]':>10} | {'V_S0 [m/s]':>10} | "
        f"{'V_A [m/s]':>9} | {'V_C [m/s]':>9} | {'V_D [m/s]':>9} | {'V_F [m/s]':>9} | {'n_max [-]':>9} | {'n_min [-]':>9}\n"
        "----------------------------------------------------------------------------------------------------\n"
    )

    table_rows = ""
    for r in vn_database_structured:
        table_rows += (
            f"{r['case_id']:<18} | {r['W_kg']:>9.1f} | {r['h_m']:>8.1f} | {r['V_S1_ms']:>10.2f} | {r['V_S0_ms']:>10.2f} | "
            f"{r['V_A_ms']:>9.2f} | {r['V_C_ms']:>9.2f} | {r['V_D_ms']:>9.2f} | {r['V_F_ms']:>9.2f} | {r['n_max']:>9.3f} | {r['n_min']:>9.3f}\n"
        )

    full_txt_content = (
        header_summary + table_rows +
        "====================================================================================================\n\n" +
        "\n".join(txt_blocks)
    )

    with open(txt_output_path, "w", encoding="utf-8") as f_out:
        f_out.write(full_txt_content)

    # Print raw NumPy arrays and summary to the Python terminal
    print("\n" + "="*80)
    print("RAW STRUCTURED NUMPY DATABASE ARRAY (vn_database_structured):")
    print("="*80)
    print(repr(vn_database_structured))

    print("\n" + "="*80)
    print("RAW 2D NUMERIC NUMPY ARRAY (vn_database_numeric):")
    print("Columns: [W_kg, h_m, V_S1_ms, V_S0_ms, V_A_ms, V_C_ms, V_D_ms, V_F_ms, n_max, n_min]")
    print("="*80)
    print(repr(vn_database_numeric))

    print("\n" + "="*80)
    print(f"All 6 figures saved to: {output_folder}")
    print(f"Specifications text file saved to: {txt_output_path}")
    print("="*80)

    return vn_database_structured, vn_database_numeric


if __name__ == "__main__":
    vn_database_structured, vn_database_numeric = generate_vn_diagrams("V-n diagram settings.txt")

with open('V-n_diagrams-v5.py', 'w', encoding='utf-8') as f:
    f.write(code_content)

exec(code_content)