"""
Vertical CG of the loading cases, as used for the landing-gear layout of the three-view.

The calculation itself lives in three_view_drawing.vertical_cg() (Torenbeek Class II
masses at their heights in the drawing); the drawing uses the highest case unless
three_view_drawing.Z_CG is set to a number. This script prints the breakdown.

Run:  python cg_height_estimate.py      (same folder as the other WP3 scripts)
"""
import class2_weight_estimation  # noqa: F401  (Class II masses must exist before build())
import three_view_drawing as TV


def estimate(verbose=True):
    o = TV.build()
    cases, items = o["z_cg_cases"], o["z_cg_items"]
    if verbose:
        print("Vertical CG estimate (z from the fuselage centreline, + up)")
        for k, (m, z) in items.items():
            print(f"  {k:<32} {'' if m is None else f'{m:8,.0f} kg'}{'':>3} z {z:+.2f} m")
        for k, (m, z) in cases.items():
            print(f"  {k:<32} {m:8,.0f} kg   z_CG {z:+.2f} m")
        print(f"used for the gear layout: z_CG {o['z_cg']:+.2f} m, h_CG {o['h_cg']:.2f} m above the ground; "
              f"scrape angle {o['scrape_angle']:.1f} deg")
    return cases


if __name__ == "__main__":
    estimate()
