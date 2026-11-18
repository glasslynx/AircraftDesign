#imports
#import astropy.units as n
import numpy as np
#import scipy as sp

#because we don't know the position of the centroid, 
#the initial position will be given as a function of x_ref amd z_ref where x_ref starts at the leading edge and z_ref at the chord line
#wingbox dimension parameters

h_frontspar =
h_rearspar = 
xref_frontspar =
zref_frontspar =
xref_rearspar =
zref_rearspar = 
stringer_area =
xref_up_stringer = []
xref_low_stringer = []
#all functions needed
#calculating the position of the centroid
#function to calculate the moment of area over the centroid
#all functions needed
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

def zpositionUPstringers(xref_frontspar, xref_rearspar, wingbox_zref_dimension, xref_stringer): #function to calculate the z-position of the stringers from their known x-position
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


wingbox_zref_dimension = wingboxdimension(zref_frontspar, zref_rearspar, h_frontspar, h_rearspar)
print(wingbox_zref_dimension)
print(zpositionUPstringers(xref_frontspar, xref_rearspar, wingbox_zref_dimension, xref_up_stringer))
print(zpositionLOWstringers(xref_frontspar, xref_rearspar, wingbox_zref_dimension, xref_low_stringer))

