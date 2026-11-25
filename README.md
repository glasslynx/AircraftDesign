# AircraftDesign

AE2111-I aircraft design project, group A11.

## Layout

| Folder | Contents |
|---|---|
| `WP1/` | `wp1_sizing.py`: Class I weight estimate and matching diagram |
| `WP2/` | Wing planform (`Wing_planform_design_INITIAL.py`), airfoil tools (`airfoil_properties.py`, `flow5_compressibility.py`) and the NASA SC(2)-0612 coordinates |
| `WP3/` | Drag, Class II weights, HLD/aileron sizing, wing checks, fuselage cross-section, three-view drawing, W/S sweep and WP3.4 optimiser |
| `WP3/wp3_4_codeV4/` | Final self-contained WP3.4 code bundle (V4) with its figures and generated report tables |
| `WP4/` | WP4 structures work (in progress) |

Scripts in `WP3/` import `wp1_sizing` from `../WP1` and read the airfoil file from `../WP2`, so run them from inside the repo. `WP3/wp3_4_codeV4/` has its own copies and runs on its own.
