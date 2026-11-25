#imports
#import astropy.units as n
import numpy as np
import math
#import scipy as sp

from geometry import spar_height
#because we don't know the position of the centroid, 
#the initial position will be given as a function of x_ref amd z_ref where x_ref starts at the leading edge and z_ref at the chord line
#wingbox dimension parameters

#Inputs
#chord length as a function of y
y = 
c= 3.866 - 0.19798*y 
# y position at which the third spar
y_third_spar = 
#thickness of spars
t_frontspar = 
t_rearspar = 
t_thirdspar = 
t_upskin = #thickness of the upper part of the trapezoid
t_lowskin = 
A_stringer_up = #area of the stringer on the upper skin
A_stringer_low = # same but for lower side
n_stringer_up = # number of stringer on the upper side of the wing box
n_stringer_low = # same but for lower side


#Important values needed
h_frontspar = 0.1092*c #fron spar height
h_rearspar = 0.0732*c
xref_frontspar = 0.2*c
zref_frontspar = - 0.0001*c
xref_rearspar = 0.7*c
zref_rearspar = 0.009*c
xref_thirdspar = 0.45*c


#calculating the position of the centroid
#function to calculate the moment of area over the centroid
def wingboxdimension(zref_frontspar, zref_rearspar, h_frontspar, h_rearspar):
  #here the zref coordinate of the 4 corners of the wing box is calculated, here zref_f_top if for the z position of the front top corner
  zref_f_up = zref_frontspar + 0.5*h_frontspar
  zref_f_low = zref_frontspar - 0.5*h_frontspar
  zref_r_up = zref_rearspar + 0.5*h_rearspar
  zref_r_low = zref_rearspar - 0.5*h_rearspar
  wingbox_zref_dimension = [zref_f_up,zref_f_low,zref_r_up,zref_r_low]
  return(wingbox_zref_dimension)

#wingbox_zref_dimension = wingboxdimension(zref_frontspar, zref_rearspar, h_frontspar, h_rearspar)

def positionUPstringers(xref_frontspar, xref_rearspar, xref_thirdspar, wingbox_zref_dimension, y_third_spar, n_stringer_up): #function to calculate the position of the stringers from their known x-position
  xref_stringer = []
  for i in range(n_stringer_up) :
    x = xref_frontspar + (xref_frontspar - xref_rearspar)/n_stringer_up * i
    xref_stringer.append(x)
    
  
  zref_r_up = wingbox_zref_dimension[2]
  zref_f_up = wingbox_zref_dimension[0]
  zref_Up_stringer = []
  for i in range(len(xref_stringer)):
    a = zref_f_up + (zref_r_up - zref_f_up)/(xref_rearspar-xref_frontspar)*(xref_stringer[i]-xref_frontspar)
    zref_Up_stringer.append(a)
  return(zref_Up_stringer)


def zpositionLOWstringers(xref_frontspar, xref_rearspar, wingbox_zref_dimension, xref_stringer): #function to calculate the z-position of the stringers from their known x-position
  zref_r_low = wingbox_zref_dimension[3]
  zref_f_low = wingbox_zref_dimension[1]
  zref_Low_stringer = []
  for i in range(len(xref_stringer)):
    a = zref_f_low + (zref_r_low - zref_f_low)/(xref_rearspar-xref_frontspar)*(xref_stringer[i]-xref_frontspar)
    zref_Low_stringer.append(a)
  return(zref_Low_stringer)

def lengthSkinWingbox(wingbox_zref_dimension, xref_frontspar, xref_rearspar): #calculate the length of the up or the low part of the trapezoid (skin section)
  L_upskin = math.sqrt((xref_rearspar-xref_frontspar)**2+(wingbox_zref_dimension[2]-wingbox_zref_dimension[0])**2)
  L_lowskin = math.sqrt((xref_rearspar-xref_frontspar)**2+(wingbox_zref_dimension[3]-wingbox_zref_dimension[1])**2)
  return[L_upskin, L_lowskin]

def HeightThirdSpar(wingbox_zref_dimension, xref_thirdspar, xref_rearspar, xref_frontspar): #the height of the middle spar 
  zref_r_up = wingbox_zref_dimension[2]
  zref_f_up = wingbox_zref_dimension[0]
  zref_r_low = wingbox_zref_dimension[3]
  zref_f_low = wingbox_zref_dimension[1]
  zref_third_up = zref_f_up + (zref_r_up - zref_f_up)/(xref_rearspar-xref_frontspar)*(xref_thirdspar-xref_frontspar)
  zref_third_low = zref_f_low + (zref_r_low - zref_f_low)/(xref_rearspar-xref_frontspar)*(xref_thirdspar-xref_frontspar)
  h_thirdspar = zref_third_up - zref_third_low
  zref_third = (zref_third_up + zref_third_low)/2
  return[h_thirdspar, zref_third]

wingbox_zref_dimension = wingboxdimension(zref_frontspar, zref_rearspar, h_frontspar, h_rearspar)
print(wingbox_zref_dimension)
print(zpositionUPstringers(xref_frontspar, xref_rearspar, wingbox_zref_dimension, xref_up_stringer))
print(zpositionLOWstringers(xref_frontspar, xref_rearspar, wingbox_zref_dimension, xref_low_stringer))

A_f_spar = t_frontspar * h_frontspar #calculating the Area of the spars
A_r_spar = t_rearspar * h_rearspar
A_thrid_spar = t_thirdspar * HeightThirdSpar(wingbox_zref_dimension, xref_thirdspar, xref_rearspar, xref_frontspar)[0]

Length_Skin = lengthSkinWingbox(wingbox_zref_dimension, xref_frontspar, xref_rearspar):
A_up_skin = t_upskin * Length_Skin[0]
A_low_skin = t_lowskin * Length_Skin[1]

if y =< y_third_spar :

if y > y_third_spar :
  #total surface area
  A_total = A_up_skin + A_low_skin + A_f_spar + A_r_spar + len(xref_up_stringer)*A_stringer + len(xref_low_stringer)*A_stringer
  #x-centroid position from the leading edge
  x_c = (A_f_spar*xref_frontspar + A_r_spar*xref_rearspar + (A_up_skin + A_low_skin)*(xref_rearspar - xref_frontspar))/A_total
  #z-centroid position from the chord
  z_c = (A_f_spar*zref_frontspar + A_r_spar*zref_rearspar + (A_up_skin + A_low_skin)*(zref_rearspar - zref_frontspar))/A_total
  #the coordinate system is x from leading edge to trailing edge (0 at centroid)



corners = [(0,1),(0,0),(1,1),(1,0)]


