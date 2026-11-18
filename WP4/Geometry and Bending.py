#imports
import astropy.units as n
import numpy as np
import scipy as sp

#because we don't know the position of the centroid, 
#the initial position will be given as a function of x_ref amd z_ref where x_ref starts at the leading edge and z_ref at the chord line
#wingbox dimension parameters

h_frontspar =
h_rearspar = 
xref_frontspar =
zref_frontspar =
xref_rearspar =
zref_rearspar = 
stringer area =
#all functions needed
#calculating the position of the centroid
#function to calculate the moment of area over the centroid
def wingboxdimension(zref_frontspar, zref_rearspar, h_frontspar, h_rearspar):
  #here the zref coordinate of the 4 corners of the wing box is calculated, here zref_f_top if for the z position of the front top corner
  zref_f_top = zref_frontspar + 0.5*h_frontspar
  zref_f_bottom = zref_frontspar - 0.5*h_frontspar
  zref_r_top = zref_rearspar + 0.5*h_rearspar
  zref_r_bottom = zref_rearspar + 0.5*h_rearspar

