import numpy as np
import scipy as sp
import math

# --- Design Inputs ---
y_span =          # half-span [m] (adjust to your wing half-span b/2)
y_third_spar =       # y position at which the third spar stops [m]

# Thicknesses of spars and skins [m]
t_frontspar =
t_rearspar =
t_thirdspar =
t_upskin =
t_lowskin =

# Stringer areas [m^2] and counts (even numbers)
A_stringer_up =
A_stringer_low =
n_stringer_up =
n_stringer_low =


def make_function(y_points, values):
    """Turn point data into a callable function."""
    return sp.interpolate.interp1d(y_points, values, kind="linear", fill_value="extrapolate")


def wingboxdimension(zref_frontspar, zref_rearspar, h_frontspar, h_rearspar):
    zref_f_up = zref_frontspar + 0.5 * h_frontspar
    zref_f_low = zref_frontspar - 0.5 * h_frontspar
    zref_r_up = zref_rearspar + 0.5 * h_rearspar
    zref_r_low = zref_rearspar - 0.5 * h_rearspar
    return [zref_f_up, zref_f_low, zref_r_up, zref_r_low]


def positionUPstringers(xref_frontspar, xref_rearspar, xref_thirdspar, wingbox_zref_dimension, y_third_spar, n_stringer_up, y):
    xref_UPstringer = []
    zref_UPstringer = []
    zref_f_up = wingbox_zref_dimension[0]
    zref_r_up = wingbox_zref_dimension[2]
    
    if y <= y_third_spar:
        n_half = n_stringer_up // 2
        for i in range(1, n_half + 1):
            x = xref_frontspar + (xref_thirdspar - xref_frontspar) / (n_half + 1) * i
            xref_UPstringer.append(x)
            z = zref_f_up + (zref_r_up - zref_f_up) / (xref_rearspar - xref_frontspar) * (x - xref_frontspar)
            zref_UPstringer.append(z)
        for i in range(1, n_half + 1):
            x = xref_thirdspar + (xref_rearspar - xref_thirdspar) / (n_half + 1) * i
            xref_UPstringer.append(x)
            z = zref_f_up + (zref_r_up - zref_f_up) / (xref_rearspar - xref_frontspar) * (x - xref_frontspar)
            zref_UPstringer.append(z)
    else:
        n_total = n_stringer_up + 1
        for i in range(1, n_total + 1):
            x = xref_frontspar + (xref_rearspar - xref_frontspar) / (n_total + 1) * i
            xref_UPstringer.append(x)
            z = zref_f_up + (zref_r_up - zref_f_up) / (xref_rearspar - xref_frontspar) * (x - xref_frontspar)
            zref_UPstringer.append(z)
            
    return (xref_UPstringer, zref_UPstringer)


def positionLOWstringers(xref_frontspar, xref_rearspar, xref_thirdspar, wingbox_zref_dimension, y_third_spar, n_stringer_low, y):
    xref_LOWstringer = []
    zref_LOWstringer = []
    zref_f_low = wingbox_zref_dimension[1]
    zref_r_low = wingbox_zref_dimension[3]
    
    if y <= y_third_spar:
        n_half = n_stringer_low // 2
        for i in range(1, n_half + 1):
            x = xref_frontspar + (xref_thirdspar - xref_frontspar) / (n_half + 1) * i
            xref_LOWstringer.append(x)
            z = zref_f_low + (zref_r_low - zref_f_low) / (xref_rearspar - xref_frontspar) * (x - xref_frontspar)
            zref_LOWstringer.append(z)
        for i in range(1, n_half + 1):
            x = xref_thirdspar + (xref_rearspar - xref_thirdspar) / (n_half + 1) * i
            xref_LOWstringer.append(x)
            z = zref_f_low + (zref_r_low - zref_f_low) / (xref_rearspar - xref_frontspar) * (x - xref_frontspar)
            zref_LOWstringer.append(z)
    else:
        n_total = n_stringer_low + 1
        for i in range(1, n_total + 1):
            x = xref_frontspar + (xref_rearspar - xref_frontspar) / (n_total + 1) * i
            xref_LOWstringer.append(x)
            z = zref_f_low + (zref_r_low - zref_f_low) / (xref_rearspar - xref_frontspar) * (x - xref_frontspar)
            zref_LOWstringer.append(z)
            
    return (xref_LOWstringer, zref_LOWstringer)


def lengthSkinWingbox(wingbox_zref_dimension, xref_frontspar, xref_rearspar):
    L_upskin = math.sqrt((xref_rearspar - xref_frontspar)**2 + (wingbox_zref_dimension[2] - wingbox_zref_dimension[0])**2)
    L_lowskin = math.sqrt((xref_rearspar - xref_frontspar)**2 + (wingbox_zref_dimension[3] - wingbox_zref_dimension[1])**2)
    return [L_upskin, L_lowskin]


def HeightThirdSpar(wingbox_zref_dimension, xref_thirdspar, xref_rearspar, xref_frontspar):
    zref_r_up = wingbox_zref_dimension[2]
    zref_f_up = wingbox_zref_dimension[0]
    zref_r_low = wingbox_zref_dimension[3]
    zref_f_low = wingbox_zref_dimension[1]
    zref_third_up = zref_f_up + (zref_r_up - zref_f_up) / (xref_rearspar - xref_frontspar) * (xref_thirdspar - xref_frontspar)
    zref_third_low = zref_f_low + (zref_r_low - zref_f_low) / (xref_rearspar - xref_frontspar) * (xref_thirdspar - xref_frontspar)
    h_thirdspar = zref_third_up - zref_third_low
    zref_third = (zref_third_up + zref_third_low) / 2
    return [h_thirdspar, zref_third]


def centroid_corners(wingbox_zref_dimension, xref_frontspar, xref_rearspar, x_c, z_c):
    """Returns the 4 corners of the wing box in the centroidal (x, z) coordinate system."""
    zref_f_up, zref_f_low, zref_r_up, zref_r_low = wingbox_zref_dimension
    return [
        (xref_frontspar - x_c, zref_f_up - z_c),   # Front-up corner
        (xref_frontspar - x_c, zref_f_low - z_c),  # Front-low corner
        (xref_rearspar - x_c,  zref_r_low - z_c),  # Rear-low corner
        (xref_rearspar - x_c,  zref_r_up - z_c),   # Rear-up corner
    ]


def compute_section(y):
    """Computes x_c, z_c, I_xx, and corners at a single spanwise station y."""
    c = 3.652 − 0.19615 * y
    h_frontspar = 0.1092 * c
    h_rearspar = 0.0732 * c
    xref_frontspar = 0.2 * c
    zref_frontspar = -0.0001 * c
    xref_rearspar = 0.7 * c
    zref_rearspar = 0.009 * c
    xref_thirdspar = 0.45 * c

    wingbox_zref_dimension = wingboxdimension(zref_frontspar, zref_rearspar, h_frontspar, h_rearspar)
    zref_f_up, zref_f_low, zref_r_up, zref_r_low = wingbox_zref_dimension

    xref_UP, zref_UP = positionUPstringers(
        xref_frontspar, xref_rearspar, xref_thirdspar, wingbox_zref_dimension, y_third_spar, n_stringer_up, y
    )
    xref_LOW, zref_LOW = positionLOWstringers(
        xref_frontspar, xref_rearspar, xref_thirdspar, wingbox_zref_dimension, y_third_spar, n_stringer_low, y
    )

    A_f_spar = t_frontspar * h_frontspar
    A_r_spar = t_rearspar * h_rearspar
    h_third, zref_third = HeightThirdSpar(wingbox_zref_dimension, xref_thirdspar, xref_rearspar, xref_frontspar)
    A_third_spar = t_thirdspar * h_third

    Length_Skin = lengthSkinWingbox(wingbox_zref_dimension, xref_frontspar, xref_rearspar)
    A_up_skin = t_upskin * Length_Skin[0]
    A_low_skin = t_lowskin * Length_Skin[1]

    x_skin_mid = (xref_rearspar + xref_frontspar) / 2
    z_upskin_mid = (zref_r_up + zref_f_up) / 2
    z_lowskin_mid = (zref_r_low + zref_f_low) / 2

    Ax_stringers = A_stringer_up * sum(xref_UP) + A_stringer_low * sum(xref_LOW)
    Az_stringers = A_stringer_up * sum(zref_UP) + A_stringer_low * sum(zref_LOW)

    if y <= y_third_spar:
        A_total = A_up_skin + A_low_skin + A_f_spar + A_r_spar + A_third_spar + n_stringer_low * A_stringer_low + n_stringer_up * A_stringer_up
        x_c = (A_f_spar * xref_frontspar + A_r_spar * xref_rearspar + A_third_spar * xref_thirdspar + (A_up_skin + A_low_skin) * x_skin_mid + Ax_stringers) / A_total
        z_c = (A_f_spar * zref_frontspar + A_r_spar * zref_rearspar + A_third_spar * zref_third + A_up_skin * z_upskin_mid + A_low_skin * z_lowskin_mid + Az_stringers) / A_total
    else:
        A_total = A_up_skin + A_low_skin + A_f_spar + A_r_spar + (n_stringer_low + 1) * A_stringer_low + (n_stringer_up + 1) * A_stringer_up
        x_c = (A_f_spar * xref_frontspar + A_r_spar * xref_rearspar + (A_up_skin + A_low_skin) * x_skin_mid + Ax_stringers) / A_total
        z_c = (A_f_spar * zref_frontspar + A_r_spar * zref_rearspar + A_up_skin * z_upskin_mid + A_low_skin * z_lowskin_mid + Az_stringers) / A_total

    corners = centroid_corners(wingbox_zref_dimension, xref_frontspar, xref_rearspar, x_c, z_c)

    I_f_spar = (1 / 12) * t_frontspar * h_frontspar**3 + A_f_spar * (zref_frontspar - z_c)**2
    I_r_spar = (1 / 12) * t_rearspar * h_rearspar**3 + A_r_spar * (zref_rearspar - z_c)**2
    I_up_skin = (1 / 12) * t_upskin * Length_Skin[0] * (zref_r_up - zref_f_up)**2 + A_up_skin * (z_upskin_mid - z_c)**2
    I_low_skin = (1 / 12) * t_lowskin * Length_Skin[1] * (zref_r_low - zref_f_low)**2 + A_low_skin * (z_lowskin_mid - z_c)**2
    I_stringers = (
        sum(A_stringer_up * (z - z_c)**2 for z in zref_UP)
        + sum(A_stringer_low * (z - z_c)**2 for z in zref_LOW)
    )

    if y <= y_third_spar:
        I_third_spar = (1 / 12) * t_thirdspar * h_third**3 + A_third_spar * (zref_third - z_c)**2
        I_xx = I_f_spar + I_r_spar + I_third_spar + I_up_skin + I_low_skin + I_stringers
    else:
        I_xx = I_f_spar + I_r_spar + I_up_skin + I_low_skin + I_stringers

    return x_c, z_c, I_xx, corners


# --- Build Spanwise Grid & Callable Interpolated Functions ---
# Include points right before and after y_third_spar to capture the exact step change cleanly
y_points = np.unique(np.concatenate([
    np.linspace(0.0, y_span, 200),
    [y_third_spar - 1e-6, y_third_spar, y_third_spar + 1e-6]
]))

x_c_vals = []
z_c_vals = []
I_xx_vals = []
corners_vals = []  # shape will be (len(y_points), 4, 2)

for y_val in y_points:
    xc, zc, ixx, crn = compute_section(y_val)
    x_c_vals.append(xc)
    z_c_vals.append(zc)
    I_xx_vals.append(ixx)
    corners_vals.append(crn)

# Callable functions of y (ready for integration with scipy.integrate.quad)
x_c_func = make_function(y_points, x_c_vals)
z_c_func = make_function(y_points, z_c_vals)
I_xx_func = make_function(y_points, I_xx_vals)

# Interpolating corners along axis=0 returns a (4, 2) array for any scalar y
corners_interp = sp.interpolate.interp1d(y_points, np.array(corners_vals), axis=0, kind="linear", fill_value="extrapolate")

def corners_func(y):
    return [tuple(pt) for pt in corners_interp(y)]



