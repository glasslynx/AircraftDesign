"""
Fuselage cross-section drawing, built the way the reader builds it:
stacked boxes around the passengers, then a circle around the box corners,
a floor, and the hold below the floor. Group A011 (80 passengers, 2-2 single aisle).

Run:    python fuselage_cross_section.py
Needs:  numpy, matplotlib
Output: fuselage_cross_section.png

Change the numbers in the INPUTS block and run again; everything else is calculated.
All lengths in metres. Heights are measured above the TOP of the passenger floor.
"""
from math import acos, sqrt, pi
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Polygon

# ----------------------------------------------------------------------------
# INPUTS
# ----------------------------------------------------------------------------
n_SA, n_aisle = 4, 1
w_seat, w_armrest, w_clear, w_aisle = 0.43, 0.05, 0.02, 0.41

h_armrest, h_shoulder, h_headroom, h_aisle = 0.64, 1.05, 1.40, 1.90

d_inner = 2.72        # inner diameter (from the drawing)
t_floor = 0.15        # floor thickness
h_hold = 0.58         # hold height below the floor (from the drawing)

# "measured": circle placed so the hold is exactly h_hold deep (the numbers used in the report)
# "tight"   : circle placed as low as the box corners allow (hold depth then follows from it)
CENTRE_MODE = "measured"

OUTFILE = "fuselage_cross_section.png"

# ----------------------------------------------------------------------------
# CALCULATIONS (the reader's cross-section method)
# ----------------------------------------------------------------------------
w_cabin = n_SA * w_seat + (n_SA + n_aisle + 1) * w_armrest + n_aisle * w_aisle + 2 * w_clear
w_floor = w_cabin - 2 * (w_armrest + w_clear)
w_headroom = w_floor - w_seat

R = d_inner / 2
d_outer = 1.045 * d_inner + 0.084
R_out = d_outer / 2
t_wall = (d_outer - d_inner) / 2

# corner points the circle has to enclose (right-hand side; the left side is mirrored)
corners = [(w_floor / 2, 0.0), (w_cabin / 2, h_armrest), (w_cabin / 2, h_shoulder),
           (w_headroom / 2, h_headroom), (w_aisle / 2, h_aisle)]

# allowed range of the circle centre height: every corner must lie inside the circle
lo = max(y - sqrt(R**2 - x**2) for x, y in corners)
hi = min(y + sqrt(R**2 - x**2) for x, y in corners)
if CENTRE_MODE == "tight":
    c = lo
    h_hold = R - c - t_floor
else:
    c = R - h_hold - t_floor
if not (lo - 1e-9 <= c <= hi + 1e-9):
    print(f"WARNING: with c = {c:.3f} m some box corners lie outside the circle "
          f"(allowed c from {lo:.3f} to {hi:.3f} m)")


def segment_area(radius, depth):
    """Area of the circular segment of height `depth`, measured from the bottom of the circle."""
    dd = radius - depth
    return radius**2 * acos(dd / radius) - dd * sqrt(radius**2 - dd**2)


A_hold = segment_area(R, h_hold)
A_cabin = pi * R**2 - segment_area(R, R - c)
x_max = sqrt(R**2 - (h_headroom - c) ** 2)
xs = np.linspace(w_aisle / 2, x_max, 20001)
A_bin = float(np.trapezoid(np.clip(c + np.sqrt(R**2 - xs**2) - h_headroom, 0, None), xs))

print(f"w_cabin = {w_cabin:.3f}  w_floor = {w_floor:.3f}  w_headroom = {w_headroom:.3f}  w_aisle = {w_aisle:.3f} m")
print(f"d_inner = {d_inner:.3f}  d_outer = {d_outer:.3f}  t_wall = {t_wall:.3f} m")
print(f"circle centre above floor top c = {c:.3f} m (allowed {lo:.3f} to {hi:.3f})")
print(f"hold depth = {h_hold:.3f} m   A_hold = {A_hold:.3f} m^2   A_cabin = {A_cabin:.3f} m^2   A_bin = {A_bin:.3f} m^2/side")
for x, y in corners:
    print(f"  corner ({x:.3f}, {y:.2f}): distance to centre {sqrt(x**2 + (y - c)**2):.3f} m (R = {R:.3f})")

# ----------------------------------------------------------------------------
# DRAWING
# ----------------------------------------------------------------------------
BOX = "#1f3f73"
fig, ax = plt.subplots(figsize=(11, 11))

# circles
ax.add_patch(Circle((0, c), R_out, fill=False, ec="#888888", lw=1.0))
ax.add_patch(Circle((0, c), R, fill=False, ec="k", lw=2.2))

# hold (below the floor underside) and floor
th = np.linspace(0, 2 * np.pi, 4000)
X, Y = R * np.cos(th), c + R * np.sin(th)
m = Y <= -t_floor
ax.fill(X[m], Y[m], color="#dce9f5", zorder=0)
xf = sqrt(R**2 - (0 - c) ** 2)               # half chord at the floor top
xu = sqrt(R**2 - (-t_floor - c) ** 2)        # half chord at the floor underside
ax.add_patch(Polygon([(-xf, 0), (xf, 0), (xu, -t_floor), (-xu, -t_floor)], closed=True,
                     fc="#b9bec5", ec="k", lw=1.0, hatch="////"))

# passenger boxes (stacked as in the reader) and the aisle box
ax.add_patch(Rectangle((-w_floor / 2, 0), w_floor, h_armrest, fill=False, ec=BOX, lw=1.4))
ax.add_patch(Rectangle((-w_cabin / 2, h_armrest), w_cabin, h_shoulder - h_armrest, fill=False, ec=BOX, lw=1.4))
ax.add_patch(Rectangle((-w_headroom / 2, h_shoulder), w_headroom, h_headroom - h_shoulder, fill=False, ec=BOX, lw=1.4))
ax.add_patch(Rectangle((-w_aisle / 2, 0), w_aisle, h_aisle, fill=False, ec="#b03a2e", lw=1.4, ls="--"))
ax.plot([0, 0], [-0.9, h_aisle + 0.15], color="#999999", lw=0.8, ls="-.")

# corner points
for x, y in corners:
    ax.plot([x, -x], [y, y], "o", color="#b03a2e", ms=5, zorder=5)

# overhead bin regions (above the headroom line, outboard of the aisle)
xs = np.linspace(w_aisle / 2, x_max, 3000)
top = c + np.sqrt(np.clip(R**2 - xs**2, 0, None))
for s in (1, -1):
    ax.fill_between(s * xs, h_headroom, top, where=top > h_headroom, fc="#d6efdc", ec="#2e7d4f", lw=1.2, ls="--")
ax.annotate(f"A_bin = {A_bin:.3f} m² (each side)", xy=(0.75, 1.62), xytext=(1.12, 2.05),
            fontsize=9.5, color="#1b5e3a", arrowprops=dict(arrowstyle="-", color="#1b5e3a", lw=0.8))

# hold label
ax.text(0, -0.45, f"hold\nA_hold = {A_hold:.3f} m²", ha="center", va="center", fontsize=10.5, color="#12355b")


# ---- dimensions --------------------------------------------------------------
def hdim(y, x0, x1, label, dy=0.045, col="k", fs=9):
    ax.annotate("", (x0, y), (x1, y), arrowprops=dict(arrowstyle="<->", color=col, lw=1.0))
    ax.text((x0 + x1) / 2, y + dy, label, ha="center", va="bottom", fontsize=fs, color=col,
            bbox=dict(fc="white", ec="none", alpha=0.9, pad=0.8))


def vdim(x, y0, y1, label, side="left", col="k", fs=9):
    ax.annotate("", (x, y1), (x, y0), arrowprops=dict(arrowstyle="<->", color=col, lw=1.0))
    if side == "left":      # rotated labels, so neighbouring dimension lines do not collide
        ax.text(x - 0.04, (y0 + y1) / 2, label, ha="right", va="center", rotation=90, fontsize=fs, color=col)
    else:
        ax.text(x + 0.04, (y0 + y1) / 2, label, ha="left", va="center", fontsize=fs, color=col)


col = "#1f3f73"
hdim(0.0, -w_floor / 2, w_floor / 2, f"w_floor = {w_floor:.2f} m", col=col)
hdim(h_armrest, -w_cabin / 2, w_cabin / 2, f"w_cabin = {w_cabin:.2f} m", col=col)
hdim(h_headroom, -w_headroom / 2, w_headroom / 2, f"w_headroom = {w_headroom:.2f} m", col=col)
hdim(0.25, -w_aisle / 2, w_aisle / 2, "", col="#b03a2e")
ax.text(w_aisle / 2 + 0.03, 0.31, f"w_aisle\n{w_aisle:.2f} m", fontsize=8.5, color="#b03a2e", va="bottom")

# heights on the left, staggered, with dotted guide lines to the box corners
for xg, y, name, val in ((-1.60, h_armrest, "h_armrest", h_armrest), (-1.90, h_shoulder, "h_shoulder", h_shoulder),
                         (-2.20, h_headroom, "h_headroom", h_headroom), (-2.50, h_aisle, "h_aisle", h_aisle)):
    vdim(xg, 0, y, f"{name}\n{val:.2f} m", side="left")
    cx = {"h_armrest": w_cabin / 2, "h_shoulder": w_cabin / 2, "h_headroom": w_headroom / 2, "h_aisle": w_aisle / 2}[name]
    ax.plot([xg, -cx], [y, y], color="#777777", lw=0.7, ls=":")
ax.plot([-2.3, 2.3], [0, 0], color="#777777", lw=0.6, ls=":")

# floor and hold on the right
vdim(1.55, -t_floor, 0, f"t_floor = {t_floor:.2f} m", side="right")
vdim(1.55, -t_floor - h_hold, -t_floor, f"h_hold = {h_hold:.2f} m", side="right", col="#12355b")
ax.plot([xu, 1.6], [-t_floor, -t_floor], color="#777777", lw=0.7, ls=":")
ax.plot([0.0, 1.6], [-t_floor - h_hold, -t_floor - h_hold], color="#777777", lw=0.7, ls=":")

# diameters below the circle
yb = c - R_out - 0.12
hdim(yb, -R, R, f"d_inner = {d_inner:.2f} m", dy=-0.13)
hdim(yb - 0.30, -R_out, R_out, f"d_outer = {d_outer:.3f} m   (t_wall = {t_wall:.3f} m)", dy=-0.13)

ax.set_aspect("equal")
ax.set_xlim(-2.95, 2.25)
ax.set_ylim(yb - 0.65, 2.35)
ax.axis("off")
ax.set_title("Fuselage cross-section: design boxes (80 passengers, 2-2 single aisle)", fontsize=12.5)
plt.tight_layout()
plt.savefig(OUTFILE, dpi=150, facecolor="white")
print("saved", OUTFILE)