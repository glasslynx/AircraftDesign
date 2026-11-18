#imports
#import astropy.units as n
import numpy as np
import math
#import scipy as sp

#because we don't know the position of the centroid, 
#the initial position will be given as a function of x_ref amd z_ref where x_ref starts at the leading edge and z_ref at the chord line
#wingbox dimension parameters

y=[]
c= 3.866 - 0.19798y #chord length as a function of y

t_frontspar = #thickness of spar
t_rearspar = 
t_upskin = #thickness of the upper part of the trapezoid
t_lowskin = 
h_frontspar = 
h_rearspar = 
xref_frontspar = 0.2*c
zref_frontspar =
xref_rearspar = 0.7*c
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

def lengthSkinWingbox(wingbox_zref_dimension, xref_frontspar, xref_rearspar): #calculate the length of the up or the low part of the trapezoid (skin section)
  L_upskin = math.sqrt((xref_rearspar-xref_frontspar)**2+(wingbox_zref_dimension[2]-wingbox_zref_dimension[0])**2)
  L_lowskin = math.sqrt((xref_rearspar-xref_frontspar)**2+(wingbox_zref_dimension[3]-wingbox_zref_dimension[1])**2)
  return[L_upskin, L_lowskin]

wingbox_zref_dimension = wingboxdimension(zref_frontspar, zref_rearspar, h_frontspar, h_rearspar)
print(wingbox_zref_dimension)
print(zpositionUPstringers(xref_frontspar, xref_rearspar, wingbox_zref_dimension, xref_up_stringer))
print(zpositionLOWstringers(xref_frontspar, xref_rearspar, wingbox_zref_dimension, xref_low_stringer))

A_f_spar = t_frontspar * h_frontspar #calculating the Area
A_r_spar = t_rearspar * h_rearspar

Length_Skin=lengthSkingWingbox(wingbox_zref_dimension, xref_frontspar, xref_rearspar):
A_up_skin = t_upskin * Length_Skin[0]
A_low_skin = t_lowskin * Length_Skin[1]




corners = [(0,1),(0,0),(1,1),(1,0)]


