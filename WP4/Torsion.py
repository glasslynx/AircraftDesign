#Imports
import numpy as np
from scipy import integrate
from scipy.interpolate import interp1d

#Shear Modulus
G = 28e9 #[Pa]

#Torsion constant calculation
#Uses list of corners as inputs for corners and a thickness t
#Input corner sequence : UL, BL, UR, BR

#Example inputs:
#corners = [(-0.25,  0.05),   # upper left
#           (-0.25, -0.05),   # bottom left
#           ( 0.25,  0.05),   # upper right
#           ( 0.25, -0.05)]   # bottom right
#t = [0.003, 0.003, 0.003, 0.003]   # top, right, bottom, left
#If different corner sequence change the [[0, 2, 3, 1]]

def torsion_constant(corners, t):
    P = np.asarray(corners, float)[[0, 2, 3, 1]]  #Converts the list in usable decimals in the following order: UL,BL,UR,BR -> UL,UR,BR,BL
    x, z = P[:, 0], P[:, 1] #Splits the coordinates in two columns with either containing one of the coordinates
    A = 0.5 * abs(np.dot(x, np.roll(z, -1)) - np.dot(z, np.roll(x, -1))) #Shoelace formula for the area of a polygon
    s = sum(np.linalg.norm(P[(i + 1) % 4] - P[i]) / t[i] for i in range(4)) 
    return 4.0 * A ** 2 / s #Output torsion constant

J = torsion_constant(corners, t)  
print(J)
