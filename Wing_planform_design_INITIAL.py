#THIS PYTHON FILE WILL BE USED TO CALCULATE ALL NECESSARY PARAMETERS FOR THE INITIAL WING PLANFORM DESIGN

#THE PROCESS FOLLOWS THE ADSEE-1 BOOK (CHAPTER_8)

import math
import matplotlib.pyplot as plt

#BASIC DATA:

#constants:
g = 9.80665 #[m/s^2] - gravitational constant

#Work_package_1:
W_MTOM_per_S = 4490 #[N/kg] - Ratio of Maximum Take-off Mass and Wing surface area 
T_per_W = 0.335 #[-] - Trust to weight ratio
W_MTOM = 31_287 #[kg] - Maximum Take-off Mass
OEM = 20_712 #[kg] - Operating EMpty Mass
M_cr = 0.77 #[-] - Cruise Mach number
h_cr = 35_000 #[feet] - cruise altitude
AR = 10.5 #[-] - Aspect Ratio
e = 0.7623 #[-] - Oswald efficiency factor
S_wing = 67.95 #[m^2] - Wing surface area
b = math.sqrt(AR * S_wing) #[m] - wingspan

def initial_wing_planform_design(S_wing, M_cr, AR, b, e):
    #SWEEP

    sweep_angle_deg = 24.022
    sweep_angle_rad = math.pi * sweep_angle_deg / 180

    #Section 8.1.2
    #TAPER RATIO

    #based on  equation 8.3 from the book on page 190 justyfied based off the graph (the trendline) below the equation
    taper_ratio = 0.2*(2 - sweep_angle_rad)

    #Section 8.1.3
    #ROOT CHORD

    #based on equation 8.5
    root_chord = 2 * S_wing / ((1 + taper_ratio) * b)

    

    #TIP CHORD

    #based on equation 8.6
    tip_chord = root_chord * taper_ratio


    #SWEEP ANGLES FOR ANY PART OF THE ROOT CHORD:
    sweep_angle_rad_c_per_4 = sweep_angle_rad
    sweep_angle_deg_c_per_4 = sweep_angle_deg
    
    sweep_angle_rad_LE = math.tan(sweep_angle_rad_c_per_4) + 0.25 * (2 * root_chord / b) * (1 - taper_ratio)
    sweep_angle_deg_LE = 180 * sweep_angle_rad_LE / math.pi

    #MAC calculation

    #define geometry:
    point_a = (0, 0)
    point_b = (0.25 * root_chord, 0)
    point_c = (0.5 * root_chord, 0)
    point_d = (root_chord, 0)
    point_e = (root_chord + tip_chord, 0)

    point_f = (0.25 * root_chord + math.tan(sweep_angle_rad) * (b/2) - root_chord - 0.25 * tip_chord, b/2)
    point_g = (0.25 * root_chord + math.tan(sweep_angle_rad) * (b/2) - 0.25 * tip_chord, b/2)
    point_h = (0.25 * root_chord + math.tan(sweep_angle_rad) * (b/2), b/2)
    point_i = (point_h[0] + 0.25 * tip_chord, b/2)
    point_j = (point_h[0] + 0.75 * tip_chord, b/2)

    wing_points = [point_a, point_b, point_c, point_d, point_j, point_i, point_h, point_g, point_a]
    extra_points = [point_d, point_e, point_f, point_g]
    half_chord_points = [point_c, point_i]

    x_coordinates_wing = []
    y_coordinates_wing = []

    x_coordinates_extra = []
    y_coordinates_extra = []

    x_coordinates_half_chord = []
    y_coordinates_half_chord = []

    for point in wing_points:
        x_coordinates_wing.append(point[0])
        y_coordinates_wing.append(point[1])

    for point in extra_points:
        x_coordinates_extra.append(point[0])
        y_coordinates_extra.append(point[1])

    for point in half_chord_points:
        x_coordinates_half_chord.append(point[0])
        y_coordinates_half_chord.append(point[1])

    #finding the intersection for the MAC

    denominator = (point_e[0] - point_f[0]) * (point_c[1] - point_i[1]) - (point_e[1] - point_f[1]) * (point_c[0] - point_i[0])

    l_x = ((point_e[0]*point_f[1] - point_e[1]*point_f[0])*(point_c[0] - point_i[0]) - (point_e[0] - point_f[0])*(point_c[0]*point_i[1] - point_c[1]*point_i[0])) / denominator
    l_y = ((point_e[0]*point_f[1] - point_e[1]*point_f[0])*(point_c[1] - point_i[1]) - (point_e[1] - point_f[1])*(point_c[0]*point_i[1] - point_c[1]*point_i[0])) / denominator
    point_l = (l_x, l_y)
    plt.plot(l_x, l_y, marker = "o", color = "red")

    #constructing the MAC line

    point_k = (point_a[0] + (point_g[0] - point_a[0])*((l_y - point_a[1])/(point_g[1] - point_a[1])), l_y)
    point_m = (point_d[0] + (point_j[0] - point_d[0])*((l_y - point_d[1])/(point_j[1] - point_d[1])), l_y)

    mac_line_points = [point_k, point_l, point_m]

    x_coordinates_mac_line = []
    y_coordinates_mac_line = []

    for point in mac_line_points:
        x_coordinates_mac_line.append(point[0])
        y_coordinates_mac_line.append(point[1])

    plt.plot(x_coordinates_mac_line, y_coordinates_mac_line, marker='o', linestyle='-', color='red', label = "MAC")
    plt.plot(x_coordinates_extra, y_coordinates_extra, marker='o', linestyle='-', color='green', label = "Auxiliary lines")
    plt.plot(x_coordinates_half_chord, y_coordinates_half_chord, marker='o', linestyle='-', color='blue', label = "Half chord line")
    plt.plot(x_coordinates_wing, y_coordinates_wing, marker='o', linestyle='-', color='black', label = "Wing outline")
    plt.plot(point_k[0], point_k[1], marker = "X", color = "orange", label = "LEMAC")

    #calculate the rest of the calculations

    MAC_length = math.sqrt((point_k[0] - point_m[0])**2 + (point_k[1] - point_m[1])**2)
    MAC_span_pos = point_l[1] / (b/2) # % of the half span
    LEMAC_x_pos = point_k[0] #my coordinate system if different

    #Section 8.1.6
    #DIHEDRAL ANGLE

    dihedral_angle = 3 - 0.1 * sweep_angle_deg + 2
    #start from 3 degs, substract 0.1 for every degree of sweep and add/substract 2 degs for low/high wings (page 201)

    #SUMMARY
    #printing out all the values and information about the wing

    print("Aspect ratio:", AR, "[-]")
    print("Wingspan:", b, "[m]")
    print("Wing surface area:", S_wing, "[m^2]")
    print("Oswald efficiency factor:", e, "[-]")
    print("Sweep angle (quarter chord):", sweep_angle_deg_c_per_4, "[deg]")
    print("Leading edge sweep angle", sweep_angle_deg_LE, "[deg]")
    print("Taper ratio:", taper_ratio, "[-]")
    print("Root chord:", root_chord, "[m]")
    print("Tip chord:", tip_chord, "[m]")
    print("MAC length:", MAC_length, "[m]")
    print("MAC spanvise position:", MAC_span_pos, "[-]")
    print("XLEMAC:", LEMAC_x_pos, "[m]")
    print("Dihedral angle:", dihedral_angle, "[deg]")

    plt.legend()
    plt.title("MAC calculation of the wing planform")
    plt.show()

    outputs = [AR, b, S_wing, e, sweep_angle_deg_c_per_4, sweep_angle_deg_LE, taper_ratio, root_chord, tip_chord, MAC_length, MAC_span_pos, LEMAC_x_pos, dihedral_angle]
    return (outputs)

initial_wing_planform_design(S_wing, M_cr, AR, b, e)