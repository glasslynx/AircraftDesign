#Imports
import numpy as np
from Geometry_and_Bending import corners, y, t_upskin, t_rearspar, t_lowskin, t_frontspar, t_midspar, xref_frontspar, xref_midspar, xref_rearspar, y_mid_end

#Middle spar
f_mid = (xref_midspar - xref_frontspar) / (xref_rearspar - xref_frontspar) #Position of the middle spar between the front and rear spar

#Wall thicknesses in the order top, right, bottom, left
t = [t_upskin, t_rearspar, t_lowskin, t_frontspar] #[m]
t_mid = t_midspar #[m]

#Torsion constant calculation
#Uses corners as input for the corners and t for the thicknesses
#Example inputs:
#corners = [(-0.25,  0.05),   # upper left
#           (-0.25, -0.05),   # bottom left
#           ( 0.25,  0.05),   # upper right
#           ( 0.25, -0.05)]   # bottom right
#t = [0.003, 0.003, 0.003, 0.003]   # top, right, bottom, left
#If different corner sequence change the [[0, 2, 3, 1]]

def polygon_area(Q):
    x, z = Q[:, 0], Q[:, 1] #Splits the coordinates in two columns with either containing one of the coordinates
    return 0.5 * abs(np.dot(x, np.roll(z, -1)) - np.dot(z, np.roll(x, -1))) #Shoelace formula for the area of a polygon

def torsion_constant(corners, t, t_mid=None):
    P = np.asarray(corners, float)[[0, 2, 3, 1]]  #Converts the list in usable decimals in the following order: UL,BL,UR,BR -> UL,UR,BR,BL
    A = polygon_area(P) #Area of the whole box
    s = sum(np.linalg.norm(P[(i + 1) % 4] - P[i]) / t[i] for i in range(4)) #Calculate the corner vectors length divided by the thickness and adds them together
    if t_mid is None:
        return 4.0 * A ** 2 / s #Output torsion constant, one cell

    #Two cells: split the box with the middle spar
    UL, UR, BR, BL = P
    MT = UL + f_mid * (UR - UL) #Top of the middle spar (on the straight top skin)
    MB = BL + f_mid * (BR - BL) #Bottom of the middle spar (on the straight bottom skin)
    A1 = polygon_area(np.array([UL, MT, MB, BL])) #Area of the front cell
    A2 = polygon_area(np.array([MT, UR, BR, MB])) #Area of the rear cell
    L = lambda p, q: np.linalg.norm(q - p) #Wall length
    s1 = L(UL, MT) / t[0] + L(MB, BL) / t[2] + L(BL, UL) / t[3] #Front cell walls without the middle spar
    s2 = L(MT, UR) / t[0] + L(UR, BR) / t[1] + L(BR, MB) / t[2] #Rear cell walls without the middle spar
    sm = L(MT, MB) / t_mid #Middle spar, shared by both cells

    #Unknowns: shear flow q1, q2 and G*dtheta/dy for a unit torque
    M = np.array([[s1 + sm, -sm, -2 * A1],  #Front cell: twist rate compatibility
                  [-sm, s2 + sm, -2 * A2],  #Rear cell: twist rate compatibility
                  [2 * A1, 2 * A2, 0.0]])   #Torque balance: T = 2*A1*q1 + 2*A2*q2 = 1
    sol = np.linalg.solve(M, np.array([0.0, 0.0, 1.0]))
    return 1.0 / sol[2] #Output torsion constant, two cells: J = T / (G*dtheta/dy)

#Torsion constant at the y of Geometry_and_Bending
if y <= y_mid_end:
    J = torsion_constant(corners, t, t_mid) #With middle spar
else:
    J = torsion_constant(corners, t) #Without middle spar
print(J)
